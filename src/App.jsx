import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import QuestionComposer from './components/QuestionComposer';
import NormalAnswerView from './components/NormalAnswerView';
import ResearchWorkspaceView from './components/ResearchWorkspaceView';
import ExperimentsView from './components/ExperimentsView';
import SourcesView from './components/SourcesView';
import HypothesesView from './components/HypothesesView';
import ReportsView from './components/ReportsView';
import HistoryView from './components/HistoryView';
import SettingsModal from './components/SettingsModal';
import AtlasLanding from './components/AtlasLanding';
import { getDynamicGreeting, ROTATING_PLACEHOLDERS } from './utils/greeting';
import { supabase } from './lib/supabase';

import {
  fetchHealth,
  fetchSettings,
  fetchConversations,
  fetchConversationMessages,
  sendDeepResearchStream,
  sendChatStream,
} from './api';

function createConversationId() {
  return 'conv-' + (globalThis.crypto?.randomUUID?.() || Math.random().toString(36).slice(2));
}

function isLikelyDeepResearch(text) {
  const value = String(text || '').toLowerCase();
  return (
    !/\b(just answer briefly|brief answer|don't research|do not research)\b/.test(value) &&
    (/\b(deep research|investigate|literature review|research gap|analyze multiple papers|recent papers|design experiments|run experiments|error analysis|reproduce|benchmark|autonomous ml research|determine whether|statistically significant|significantly improve|performance degradation|experimentally|try several)\b/.test(value) ||
      /\b(improve|optimi[sz]e|diagnose|figure out|find out)\b.*\b(model|fraud|recall|minority.class|detection|performance|overfitting|features?)\b/.test(value) ||
      (/\b(dataset|datasets)\b.*\b(evaluate|experiment|test|benchmark)\b/.test(value) || /\bcompare\b.*\b(xgboost|random forest|models?|dataset|approach)\b/.test(value)))
  );
}

// Stage mapping to the 13 Scientific Inquiry stages.
// Keys cover BOTH emitters: the orchestrator path (uppercase stages from
// agents/orchestrator.py) and the deep-research path (lowercase stages from
// backend/step_trace.py Stages). Without the lowercase keys every deep-research
// event collapsed onto step 2, so steps 03/04/09 never lit up even though the
// literature search, source evaluation and synthesis really ran.
const STAGE_NAME_MAP = {
  // Orchestrator (dataset + experiment) path — uppercase
  PLANNING: 2,
  DATASET_SEARCH: 5,
  DATASET_EVALUATION: 5,
  DATASET_SELECTED: 5,
  WAITING_FOR_USER: 6,
  HYPOTHESIS_GEN: 11,
  EXPERIMENT_DESIGN: 7,
  EXPERIMENT_EXEC: 8,
  ERROR_ANALYSIS: 10,
  REPORT_GEN: 13,
  // Deep-research (literature) path — lowercase step_trace.Stages
  research_question: 1,
  planning: 2,
  web_search: 3,
  literature_search: 3,
  source_reading: 4,
  verification: 4,
  cross_checking: 11,
  synthesis: 9,
  dataset_search: 5,
  dataset_inspection: 5,
  dataset_ranking: 5,
  dataset_selection: 5,
  dataset_analysis: 6,
  baseline_training: 6,
  hypothesis_generation: 7,
  experiment_execution: 8,
  error_analysis: 10,
  report_generation: 13,
  report: 13,
};

// Experiment/dataset stages that require an attached dataset target. On the
// literature-only deep-research path they legitimately never execute, so they
// are marked "skipped — not applicable" rather than left as ambiguous unchecked
// circles next to a completion header.
const DATASET_DEPENDENT_STAGES = [5, 6, 7, 8, 10, 11, 12];

function WorkspaceApp({ onSignOut }) {
  const [theme, setTheme] = useState(() => {
    try { return localStorage.getItem('atlas-theme') || 'system'; } catch { return 'system'; }
  });

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try { localStorage.setItem('atlas-theme', theme); } catch { /* storage may be unavailable */ }
  }, [theme]);

  // Dynamic Time-Based Greeting & Placeholder States
  const [greeting, setGreeting] = useState(() => getDynamicGreeting());
  const [placeholderIdx, setPlaceholderIdx] = useState(0);

  // Rotate input placeholders when in empty state
  useEffect(() => {
    const timer = setInterval(() => {
      setPlaceholderIdx((prev) => (prev + 1) % ROTATING_PLACEHOLDERS.length);
    }, 8000);
    return () => clearInterval(timer);
  }, []);

  // Navigation & Active View
  const [activeNav, setActiveNav] = useState('research'); // 'research' | 'experiments' | 'sources' | 'hypotheses' | 'reports' | 'history'
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  // System & Connection State
  const [backendConnected, setBackendConnected] = useState(false);
  const [connectionState, setConnectionState] = useState('CONNECTING');
  const [sysSettings, setSysSettings] = useState({});
  const connectionFailureTimer = useRef(null);

  // Active Session & Research State
  const [conversationId, setConversationId] = useState(createConversationId());
  const [activeProject, setActiveProject] = useState(null);
  const [userQuestion, setUserQuestion] = useState('');
  const [routingMode, setRoutingMode] = useState('AUTO');
  const [isDeepResearch, setIsDeepResearch] = useState(false);
  const [sessionState, setSessionState] = useState('IDLE'); // 'IDLE' | 'QUEUED' | 'IN_PROGRESS' | 'COMPLETE' | 'FAILED' | 'CANCELLED'
  const [isPending, setIsPending] = useState(false);
  const [errorFeedback, setErrorFeedback] = useState(null);

  // Answer & Data Payload
  const [normalAnswer, setNormalAnswer] = useState('');
  const [normalSources, setNormalSources] = useState([]);
  const [isBuiltInExplanation, setIsBuiltInExplanation] = useState(false);
  const [responseConfidence, setResponseConfidence] = useState(null);

  // Deep Research Workspace Data
  const [stageEvents, setStageEvents] = useState([]);
  const [experiments, setExperiments] = useState([]);
  const [currentExperiment, setCurrentExperiment] = useState(null);
  const [validatedSources, setValidatedSources] = useState([]);
  const [latestInsight, setLatestInsight] = useState(null);
  const [nextHypothesis, setNextHypothesis] = useState(null);
  const [nextExperiment, setNextExperiment] = useState(null);
  const [reportMd, setReportMd] = useState(null);

  // Session History List
  const [historyItems, setHistoryItems] = useState([]);
  // Keep every exchange in the visible session thread; the current response
  // payload below is only the active turn's workspace state.
  const [conversationTurns, setConversationTurns] = useState([]);

  // Check Backend Connection on Mount & Periodically
  const checkBackend = async () => {
    try {
      const health = await fetchHealth();
      if (!health || health.status !== 'healthy') throw new Error('Health check failed');

      if (connectionFailureTimer.current) {
        clearTimeout(connectionFailureTimer.current);
        connectionFailureTimer.current = null;
      }
      setBackendConnected(true);
      setConnectionState('CONNECTED');

      try {
        const settings = await fetchSettings();
        setSysSettings(settings);
      } catch {
        // Health is authoritative for the connection status.
      }
    } catch (e) {
      if (connectionFailureTimer.current) clearTimeout(connectionFailureTimer.current);
      connectionFailureTimer.current = setTimeout(() => {
        setBackendConnected(false);
        setConnectionState('OFFLINE');
      }, 1500);
    }
  };

  useEffect(() => {
    checkBackend();
    const interval = setInterval(checkBackend, 5000);
    return () => {
      clearInterval(interval);
      if (connectionFailureTimer.current) clearTimeout(connectionFailureTimer.current);
    };
  }, []);

  // Hydrate the real authenticated conversation list on startup. This is
  // intentionally separate from the active turn state so a refresh cannot
  // erase previously persisted conversations from the sidebar.
  useEffect(() => {
    let cancelled = false;
    fetchConversations().then((items) => {
      if (cancelled || !Array.isArray(items)) return;
      setHistoryItems(items.map((item) => ({
        id: item.id || item.conversationId,
        conversationId: item.id || item.conversationId,
        question: item.title || item.question || 'Conversation',
        timestamp: item.updatedAt || item.createdAt || 'Recent',
        isDeep: Boolean(item.isDeep || item.mode === 'deep_research'),
      })));
    }).catch(() => {});
    return () => { cancelled = true; };
  }, []);

  // Handle New Question / Reset State
  const handleNewQuestion = () => {
    setGreeting(getDynamicGreeting());
    setUserQuestion('');
    setNormalAnswer('');
    setNormalSources([]);
    setResponseConfidence(null);
    setIsDeepResearch(false);
    setSessionState('IDLE');
    setErrorFeedback(null);
    setStageEvents([]);
    setExperiments([]);
    setCurrentExperiment(null);
    setValidatedSources([]);
    setLatestInsight(null);
    setNextHypothesis(null);
    setNextExperiment(null);
    setReportMd(null);
    setActiveProject(null);
    setConversationTurns([]);
    setConversationId(createConversationId());
    setActiveNav('research');
  };

  // Main Question Submission Handler
  const handleSendQuestion = async (queryText, onSuccess) => {
    if (!queryText.trim()) return;

    setUserQuestion(queryText);
    setIsPending(true);
    setErrorFeedback(null);
    setActiveNav('research');
    const deepCheck = isLikelyDeepResearch(queryText);
    const turnId = `${conversationId}:${Date.now()}`;
    const requestId = createConversationId();
    const messageId = turnId;
    const priorHistory = conversationTurns.flatMap((turn) => [
      { role: 'user', content: turn.question },
      ...(turn.answer ? [{ role: 'assistant', content: turn.answer }] : []),
    ]).slice(-20);

    // A submitted turn owns the response area immediately. Clearing every
    // previous response payload prevents one question's answer from being
    // displayed under another question while the next request is running.
    setNormalAnswer('');
    setNormalSources([]);
    setIsBuiltInExplanation(false);
    setResponseConfidence(null);
    setReportMd(null);
    setLatestInsight(null);
    setStageEvents([]);

    // Do not discard a real user request while the startup health probe is
    // still catching up with Supabase session restoration. The chat request
    // carries its own token and is the authoritative connectivity check;
    // failures are surfaced by the request error handler below.

    if (onSuccess) onSuccess();

    setConversationTurns((prev) => [...prev, {
      id: turnId, question: queryText, answer: '', sources: [], confidence: null,
      mode: deepCheck ? 'deep' : 'normal', isLoading: true,
    }]);

    // Determine initial routing intention
    setIsDeepResearch(deepCheck);
    setRoutingMode(deepCheck ? 'AUTO: Deep Research' : 'AUTO: Normal Answer');
    setSessionState(deepCheck ? 'QUEUED' : 'IN_PROGRESS');

    // Create history item entry
    const newHistoryEntry = {
      id: conversationId,
      conversationId,
      question: queryText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      isDeep: deepCheck,
    };
    setHistoryItems((prev) => [newHistoryEntry, ...prev]);

    // Initial Stage 1 Event: Understanding research problem
    const initialEvents = [
      { stageIndex: 1, status: 'running', detail: 'Analyzing research inquiry and routing requirement', timestamp: new Date().toLocaleTimeString() },
    ];
    setStageEvents(initialEvents);

    try {
      if (deepCheck) {
        // Deep Research Path - Stream activities
        setSessionState('IN_PROGRESS');
        
        const onActivity = (activity) => {
          const idx = STAGE_NAME_MAP[activity.stage] || 2;
          setStageEvents((prev) => {
            const updated = [...prev];
            const existing = updated.findIndex((e) => e.stageIndex === idx);
            const evtObj = {
              stageIndex: idx,
              status: activity.status === 'completed' ? 'completed' : activity.status === 'failed' ? 'failed' : 'running',
              detail: activity.detail || activity.label,
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
            };
            if (existing >= 0) updated[existing] = evtObj;
            else updated.push(evtObj);
            // The backend trace is ordered, but browser/event delivery can
            // batch frames. When a later stage arrives, close any earlier
            // stage that is still shown as running so the timeline can never
            // claim stage 09 is active while stage 01 is unfinished.
            for (let prior = 1; prior < idx; prior += 1) {
              const priorIndex = updated.findIndex((e) => e.stageIndex === prior);
              if (priorIndex >= 0 && ['running', 'pending'].includes(updated[priorIndex].status)) {
                updated[priorIndex] = {
                  ...updated[priorIndex],
                  status: 'completed',
                  detail: updated[priorIndex].detail || 'Completed before the next research stage began',
                };
              }
            }
            return updated;
          });
        };

        const res = await sendDeepResearchStream(
          queryText,
          activeProject?.id,
          conversationId,
          null,
          null,
          { requestId, messageId },
          priorHistory,
          onActivity
        );

        if (res) {
          setSessionState('COMPLETE');
          const reportText = res.report || res.response || '';
          if (reportText) {
            setReportMd(reportText);
            setLatestInsight(reportText.slice(0, 300) + '…');
          }
          setConversationTurns((prev) => prev.map((turn) => turn.id === turnId
            ? { ...turn, answer: reportText, sources: res.sources || [], confidence: res.confidence || null, isLoading: false }
            : turn));
          if (res.sources && Array.isArray(res.sources)) {
            setValidatedSources(res.sources);
          }
          setResponseConfidence(res.confidence || null);

          // Reconcile the 13-step list against what actually executed:
          // Ensure EVERY stage from 1 to 13 reaches a terminal state (completed, skipped, or failed).
          const ranExperiments = !!res.project;
          setStageEvents((prev) => {
            const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
            const existingMap = new Map(prev.map((e) => [e.stageIndex, e]));
            const ALL_STAGES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13];
            
            return ALL_STAGES.map((s) => {
              const existing = existingMap.get(s);
              if (existing) {
                return {
                  ...existing,
                  status: existing.status === 'failed' ? 'failed' : 'completed',
                  timestamp: existing.timestamp || now,
                };
              }
              if (s === 1) {
                return { stageIndex: 1, status: 'completed', detail: 'Research problem analyzed and scoped', timestamp: now };
              }
              if (s === 13) {
                return { stageIndex: 13, status: 'completed', detail: 'Final research report compiled', timestamp: now };
              }
              if (!ranExperiments && DATASET_DEPENDENT_STAGES.includes(s)) {
                return {
                  stageIndex: s,
                  status: 'skipped',
                  detail: 'Skipped — not applicable: literature investigation (no dataset attached)',
                  timestamp: now,
                };
              }
              return {
                stageIndex: s,
                status: 'skipped',
                detail: 'Skipped — not applicable to query scope',
                timestamp: now,
              };
            });
          });

          if (res.project) {
            setActiveProject(res.project);
          }

          if (onSuccess) onSuccess();
        }
      } else {
        // Simple Question / Normal Answer Path — stream real answer tokens so
        // text renders incrementally instead of a skeleton followed by the whole
        // answer at once. The final frame carries the authoritative,
        // post-processed response, which reconciles any raw-token drift.
        let streamed = '';
        const res = await sendChatStream(queryText, activeProject?.id, conversationId, {
          onToken: (delta) => {
            streamed += delta;
            console.debug('[Atlas raw stream chunk]', delta);
            setNormalAnswer((prev) => prev + delta);
            setConversationTurns((prev) => prev.map((turn) => turn.id === turnId ? { ...turn, answer: `${turn.answer || ''}${delta}` } : turn));
          },
          conversationHistory: priorHistory,
          correlation: { requestId, messageId },
        });

        setSessionState('COMPLETE');
        console.debug('[Atlas raw stream final]', res.response || streamed || '');
        setNormalAnswer(res.response || streamed || 'No response returned.');
        setResponseConfidence(res.confidence || null);
        setConversationTurns((prev) => prev.map((turn) => turn.id === turnId
          ? { ...turn, answer: res.response || streamed || 'No response returned.', sources: res.sources || [], confidence: res.confidence || null, isLoading: false }
          : turn));
        setIsBuiltInExplanation(res.action === 'NONE' || !sysSettings.apiKeySet);

        if (res.citationPolicy === 'required' && res.sources) {
          setNormalSources(res.sources);
        }

        if (onSuccess) onSuccess();
      }
    } catch (err) {
      setConversationTurns((prev) => prev.map((turn) => turn.id === turnId
        ? { ...turn, isLoading: false, error: err.message }
        : turn));
      setSessionState('FAILED');
      setErrorFeedback(`Submission failed: ${err.message}`);
    } finally {
      setIsPending(false);
    }
  };

  const handleSelectConversation = async (item) => {
    const selectedId = item?.conversationId || item?.id;
    if (!selectedId) return;
    const messages = await fetchConversationMessages(selectedId);
    const rows = Array.isArray(messages) ? messages : (messages?.messages || []);
    const turns = [];
    let current = null;
    for (const message of rows) {
      if (message.role === 'user') {
        current = { id: message.id || `${selectedId}:${turns.length}`, question: message.content || '', answer: '', sources: [], confidence: null, isLoading: false, mode: 'normal' };
        turns.push(current);
      } else if (message.role === 'assistant' && current) {
        current.answer = message.content || '';
      }
    }
    setConversationId(selectedId);
    setConversationTurns(turns);
    setUserQuestion(turns.at(-1)?.question || '');
    setNormalAnswer(turns.at(-1)?.answer || '');
    setIsDeepResearch(false);
    setSessionState(turns.length ? 'COMPLETE' : 'IDLE');
    setErrorFeedback(null);
    setActiveNav('research');
  };

  // Initialize and synchronize URL path (/atlas, /atlas/experiments, etc.)
  useEffect(() => {
    const path = window.location.pathname;
    if (path.startsWith('/atlas')) {
      const sub = path.replace(/^\/atlas\/?/, '');
      if (['research', 'experiments', 'sources', 'hypotheses', 'reports', 'history'].includes(sub)) {
        setActiveNav(sub);
      }
    } else {
      window.history.replaceState(null, '', '/atlas');
    }

    const handlePopState = () => {
      const p = window.location.pathname;
      if (p.startsWith('/atlas')) {
        const sub = p.replace(/^\/atlas\/?/, '');
        if (['research', 'experiments', 'sources', 'hypotheses', 'reports', 'history'].includes(sub)) {
          setActiveNav(sub);
          return;
        }
      }
      setActiveNav('research');
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const handleSelectNav = (nav) => {
    setActiveNav(nav);
    const targetPath = nav === 'research' ? '/atlas' : `/atlas/${nav}`;
    if (window.location.pathname !== targetPath) {
      window.history.pushState(null, '', targetPath);
    }
  };

  // Download Report as Markdown (.md) file
  const handleDownloadReport = () => {
    if (!reportMd) return;
    const blob = new Blob([reportMd], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `Atlas_Research_Report_${Date.now()}.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // Title for top header based on active navigation item
  const navTitles = {
    research: 'Research Workspace',
    experiments: 'Experiments Directory',
    sources: 'Primary Sources',
    hypotheses: 'Scientific Hypotheses',
    reports: 'Scientific Reports',
    history: 'Session History',
  };

  if (activeNav === 'research') {
    return (
      <AtlasLanding 
        greeting={greeting}
        onSendMessage={handleSendQuestion}
        conversationTurns={conversationTurns}
        isPending={isPending}
        onNewChat={handleNewQuestion}
        historyItems={historyItems}
        onSelectHistoryItem={handleSelectConversation}
        theme={theme}
        onThemeChange={() => setTheme((current) => current === 'system' ? 'light' : current === 'light' ? 'dark' : 'system')}
        backendConnected={backendConnected}
        connectionState={connectionState}
        errorFeedback={errorFeedback}
      />
    );
  }

  return (
    <div className="flex h-screen w-screen bg-[var(--bg-main)] text-[var(--text-main)] font-sans overflow-hidden select-none">
      
      {/* 1. Left Navigation Column (~210px wide) */}
      <Sidebar
        activeNav={activeNav}
        onSelectNav={handleSelectNav}
        onNewQuestion={handleNewQuestion}
        onOpenSettings={() => setIsSettingsOpen(true)}
        isMobileOpen={isMobileNavOpen}
        onMobileClose={() => setIsMobileNavOpen(false)}
        backendConnected={backendConnected}
        connectionState={connectionState}
        theme={theme}
        onThemeChange={() => setTheme((current) => current === 'system' ? 'light' : current === 'light' ? 'dark' : 'system')}
      />

      {/* Main Workspace Stack (Center Column + Right Context Sidebar) */}
      <div className="flex-1 min-w-0 flex flex-col h-screen overflow-hidden">
        
        {/* Compact Top Header */}
        <Header
          sessionStatus={sessionState}
          routingMode={routingMode}
          backendConnected={backendConnected}
          connectionState={connectionState}
          onOpenMobileNav={() => setIsMobileNavOpen(true)}
          activeNavTitle={navTitles[activeNav] || 'Research Workspace'}
        />

        {/* 3-Column Content Body */}
        <div className="flex-1 min-w-0 flex overflow-hidden relative">
          
          {/* 2. Center Workspace Area (Flexible width) */}
          <main className="flex-1 min-w-0 flex flex-col h-full overflow-hidden relative bg-[var(--bg-main)]">
            
            {/* View Switching based on activeNav destination */}
            {activeNav === 'research' && (
              <AnimatePresence mode="wait">
                {!userQuestion && sessionState === 'IDLE' ? (
                  // Initial Atlas Landing Screen View
                  <motion.div
                    key="start-screen"
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -20, transition: { duration: 0.35, ease: [0.16, 1, 0.3, 1] } }}
                    className="flex-1 w-full h-full min-h-0"
                  >
                    <AtlasLanding 
                      greeting={greeting}
                      onSendMessage={handleSendQuestion}
                      backendConnected={backendConnected}
                      connectionState={connectionState}
                      errorFeedback={errorFeedback}
                      onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
                      onOpenSettings={() => setIsSettingsOpen(true)}
                      historyItems={historyItems}
                      onSelectHistoryItem={handleSelectConversation}
                    />
                  </motion.div>
                ) : (
                  // Conversation Workspace View
                  <motion.div
                    key="conversation-view"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
                    className="flex-1 flex flex-col w-full h-full min-h-0"
                  >
                    {!isDeepResearch ? (
                      // Simple Question Normal Answer View
                      <NormalAnswerView
                        userQuestion={userQuestion}
                        answer={normalAnswer}
                        sources={normalSources}
                        confidence={responseConfidence}
                        isLoading={isPending && !normalAnswer}
                        turns={conversationTurns}
                      />
                    ) : (
                      // Deep Research Workspace View
                      <ResearchWorkspaceView
                        userQuestion={userQuestion}
                        routingMode={routingMode}
                        sessionState={sessionState}
                        stageEvents={stageEvents}
                        experiments={experiments}
                        currentExperiment={currentExperiment}
                        latestFinding={latestInsight}
                        reportMd={reportMd}
                        backendConnected={backendConnected}
                        connectionState={connectionState}
                        confidence={responseConfidence}
                        priorTurns={conversationTurns.slice(0, -1)}
                        canRetry={sessionState === 'FAILED'}
                        onRetryStage={() => handleSendQuestion(userQuestion)}
                        onDownloadReport={handleDownloadReport}
                      />
                    )}
                  </motion.div>
                )}
              </AnimatePresence>
            )}

            {activeNav === 'experiments' && (
              <ExperimentsView
                experiments={experiments}
                currentExperiment={currentExperiment}
              />
            )}

            {activeNav === 'sources' && (
              <SourcesView sources={validatedSources} />
            )}

            {activeNav === 'hypotheses' && (
              <HypothesesView
                hypotheses={[]}
                nextHypothesis={nextHypothesis}
                nextExperiment={nextExperiment}
                hasRealRunAction={false}
              />
            )}

            {activeNav === 'reports' && (
              <ReportsView
                reportMd={reportMd}
                onDownloadReport={handleDownloadReport}
                userQuestion={userQuestion}
              />
            )}

            {activeNav === 'history' && (
              <HistoryView
                historyItems={historyItems}
                onSelectHistoryItem={handleSelectConversation}
              />
            )}

            {/* Anchored Bottom Command Composer (shown only when in active conversation view) */}
            {activeNav === 'research' && (userQuestion || sessionState !== 'IDLE') && (
              <motion.div
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
                className="atlas-prompt-dock absolute bottom-0 left-0 right-0 p-3 sm:p-4 bg-gradient-to-t from-[#121212] via-[#121212]/95 to-transparent z-20"
              >
                <div className={isDeepResearch ? "max-w-4xl lg:max-w-5xl xl:max-w-6xl 2xl:max-w-7xl mx-auto w-full" : "max-w-3xl lg:max-w-4xl xl:max-w-5xl 2xl:max-w-6xl mx-auto w-full"}>
                  <QuestionComposer
                    onSubmit={handleSendQuestion}
                    isPending={isPending}
                    backendConnected={backendConnected}
                    connectionState={connectionState}
                    errorFeedback={errorFeedback}
                    isEmptyState={false}
                  />
                </div>
              </motion.div>
            )}
          </main>
        </div>
      </div>

      {/* Research Settings & Telemetry Modal */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        settings={sysSettings}
        onSignOut={onSignOut}
      />
    </div>
  );
}

export default function App() {
  const [currentPath, setCurrentPath] = useState(window.location.pathname);
  const [session, setSession] = useState(null);
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setIsLoaded(true);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
      setIsLoaded(true);
    });

    return () => {
      subscription?.unsubscribe();
    };
  }, []);

  useEffect(() => {
    const handlePopState = () => setCurrentPath(window.location.pathname);
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  useEffect(() => {
    if (window.location.pathname === '/login' || window.location.pathname === '/auth' || window.location.pathname.startsWith('/sso-callback')) {
      window.history.replaceState({}, '', '/atlas');
      setCurrentPath('/atlas');
    }
  }, [currentPath]);

  const handleSignOut = async () => {
    try {
      await supabase.auth.signOut();
    } catch (err) {
      console.warn('[SIGN OUT NOTICE]', err);
    }
    setSession(null);
    window.history.pushState({}, '', '/atlas');
    setCurrentPath('/atlas');
  };

  if (!isLoaded) return null;

  return (
    <WorkspaceApp
      onSignOut={handleSignOut}
    />
  );
}
