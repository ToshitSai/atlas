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

import {
  fetchHealth,
  fetchSettings,
  fetchConversations,
  fetchConversationMessages,
  saveLocalConversation,
  sendDeepResearchStream,
  sendChatStream,
  checkAnswerConfidence,
} from './api';

function createConversationId() {
  return 'conv-' + (globalThis.crypto?.randomUUID?.() || Math.random().toString(36).slice(2));
}

function mergeConversationHistory(items) {
  const byId = new Map();
  (Array.isArray(items) ? items : []).forEach((item) => {
    const id = item?.conversationId || item?.id;
    if (!id || byId.has(id)) return;
    byId.set(id, { ...item, id, conversationId: id });
  });
  return [...byId.values()].sort((a, b) => String(b.updatedAt || b.timestamp || '').localeCompare(String(a.updatedAt || a.timestamp || '')));
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
  useEffect(() => {
    if (globalThis.__ATLAS_BUILD_VERSION_LOGGED__) return;
    globalThis.__ATLAS_BUILD_VERSION_LOGGED__ = true;
    console.info('[Atlas build]', typeof __ATLAS_BUILD_VERSION__ !== 'undefined' ? __ATLAS_BUILD_VERSION__ : { commit: 'unknown' });
  }, []);
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
  const [sidebarOpen, setSidebarOpen] = useState(() => {
    try {
      if (typeof window !== 'undefined' && window.innerWidth < 768) return false;
      return localStorage.getItem('atlas-sidebar-open') !== '0';
    } catch { return true; }
  });
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
  const [confidenceChecking, setConfidenceChecking] = useState(false);

  // Deep Research Workspace Data
  const [stageEvents, setStageEvents] = useState([]);
  const [experiments, setExperiments] = useState([]);
  const [currentExperiment, setCurrentExperiment] = useState(null);
  const [validatedSources, setValidatedSources] = useState([]);
  const [latestInsight, setLatestInsight] = useState(null);
  const [nextHypothesis, setNextHypothesis] = useState(null);
  const [nextExperiment, setNextExperiment] = useState(null);
  const [reportMd, setReportMd] = useState(null);
  const [streamedResearchAnswer, setStreamedResearchAnswer] = useState('');

  // Session History List
  const [historyItems, setHistoryItems] = useState([]);
  const [historyLoadState, setHistoryLoadState] = useState('idle');
  // Keep every exchange in the visible session thread; the current response
  // payload below is only the active turn's workspace state.
  const [conversationTurns, setConversationTurns] = useState([]);
  const requestControllerRef = useRef(null);
  const sendingRef = useRef(false);

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
    setHistoryLoadState('loading');
    fetchConversations().then((items) => {
      if (cancelled || !Array.isArray(items)) return;
      setHistoryItems(mergeConversationHistory(items).map((item) => ({
        id: item.id || item.conversationId,
        conversationId: item.id || item.conversationId,
        question: item.title || item.question || 'Conversation',
        timestamp: item.updatedAt || item.createdAt || 'Recent',
        isDeep: Boolean(item.isDeep || item.mode === 'deep_research'),
      })));
      setHistoryLoadState('ready');
    }).catch(() => setHistoryLoadState('ready'));
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    try { localStorage.setItem('atlas-sidebar-open', sidebarOpen ? '1' : '0'); } catch { /* unavailable */ }
  }, [sidebarOpen]);
  useEffect(() => {
    const toggle = (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'b') {
        event.preventDefault();
        setSidebarOpen((open) => !open);
      }
    };
    window.addEventListener('keydown', toggle);
    return () => window.removeEventListener('keydown', toggle);
  }, []);

  // Handle New Question / Reset State
  const handleNewQuestion = () => {
    if (window.location.pathname !== '/') window.history.pushState({}, '', '/');
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
    setStreamedResearchAnswer('');
    setActiveProject(null);
    setConversationTurns([]);
    setConversationId(createConversationId());
    setActiveNav('research');
  };

  // Main Question Submission Handler
  const handleSendQuestion = async (queryText, onSuccess, options = {}) => {
    if (!queryText.trim() || sendingRef.current) return;
    sendingRef.current = true;

    setUserQuestion(queryText);
    setIsPending(true);
    requestControllerRef.current?.abort();
    const requestController = new AbortController();
    requestControllerRef.current = requestController;
    setErrorFeedback(null);
    setActiveNav('research');
    const deepCheck = typeof options.deepResearch === 'boolean' ? options.deepResearch : isLikelyDeepResearch(queryText);
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
    setStreamedResearchAnswer('');
    setLatestInsight(null);
    setStageEvents([]);

    // Do not discard a real user request while the startup health probe is
    // The chat request is the authoritative connectivity check; failures are
    // surfaced by the request error handler below.

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
    setHistoryItems((prev) => mergeConversationHistory([newHistoryEntry, ...prev]));
    saveLocalConversation({ ...newHistoryEntry, messages: [{ role: 'user', content: queryText, created_at: new Date().toISOString() }] }).catch(() => {});

    // The timeline starts in a queued state.  A synthetic "running" stage
    // here used to remain stuck while later backend stages completed.  Only
    // backend activity is allowed to mark a stage in progress now.
    // The research panel is driven exclusively by backend lifecycle events;
    // do not fabricate pending stages before the server has emitted one.
    setStageEvents([]);

    try {
      if (deepCheck) {
        // Deep Research Path - Stream activities
        setSessionState('IN_PROGRESS');
        
        const onActivity = (activity) => {
          const idx = STAGE_NAME_MAP[activity.stage] || 2;
          setStageEvents((prev) => {
            const updated = [...prev];
            const eventKey = activity.id || `${activity.stage || idx}`;
            const existing = updated.findIndex((e) => e.eventKey === eventKey);
            const evtObj = {
              eventKey,
              stage: activity.stage,
              label: activity.label,
              metadata: activity.metadata,
              stageIndex: idx,
              status: activity.status === 'completed' ? 'completed' : activity.status === 'failed' ? 'failed' : 'running',
              detail: activity.detail || activity.label,
              timestamp: activity.timestamp || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
            };
            if (existing >= 0) updated[existing] = evtObj;
            else updated.push(evtObj);
            // The backend trace is ordered, but browser/event delivery can
            // batch frames. A later stage is not allowed to coexist with an
            // earlier pending/running stage: close those earlier stages at
            // the moment the backend proves that the pipeline advanced.
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

        const onResearchToken = (delta) => {
          setStreamedResearchAnswer((prev) => prev + delta);
          setConversationTurns((prev) => prev.map((turn) => turn.id === turnId
            ? { ...turn, answer: `${turn.answer || ''}${delta}` }
            : turn));
        };

        const res = await sendDeepResearchStream(
          queryText,
          activeProject?.id,
          conversationId,
          null,
          null,
          { requestId, messageId },
          priorHistory,
          onActivity,
          onResearchToken,
          requestController.signal
        );

        if (res) {
          setSessionState('COMPLETE');
          const reportText = res.report || res.response || '';
          if (reportText) {
            setReportMd(reportText);
            setStreamedResearchAnswer(reportText);
            setLatestInsight(reportText.slice(0, 300) + '…');
          }
          setConversationTurns((prev) => prev.map((turn) => turn.id === turnId
            ? { ...turn, answer: reportText, sources: res.sources || [], confidence: res.confidence || null, isLoading: false }
            : turn));
          if (res.sources && Array.isArray(res.sources)) {
            setValidatedSources(res.sources);
          }
          setResponseConfidence(res.confidence || null);
          setConfidenceChecking(true);
          checkAnswerConfidence(reportText, res.sources || [], queryText).then((checked) => {
            const confidence = checked?.confidence;
            if (!confidence) return;
            setResponseConfidence(confidence);
            setConversationTurns((prev) => prev.map((turn) => turn.id === turnId ? { ...turn, confidence } : turn));
            saveLocalConversation({ ...newHistoryEntry, updatedAt: new Date().toISOString(), messages: [{ role: 'user', content: queryText }, { role: 'assistant', content: reportText, sources: res.sources || [], confidence }] }).catch(() => {});
          }).catch((error) => console.warn('[confidence check failed]', error.message)).finally(() => setConfidenceChecking(false));
          saveLocalConversation({ ...newHistoryEntry, updatedAt: new Date().toISOString(), messages: [
            { role: 'user', content: queryText, created_at: new Date().toISOString() },
            { role: 'assistant', content: reportText, sources: res.sources || [], confidence: res.confidence || null, created_at: new Date().toISOString() },
          ] }).catch(() => {});

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
          signal: requestController.signal,
        });

        setSessionState('COMPLETE');
        console.debug('[Atlas raw stream final]', res.response || streamed || '');
        setNormalAnswer(res.response || streamed || 'No response returned.');
        setResponseConfidence(res.confidence || null);
        setConfidenceChecking(true);
        checkAnswerConfidence(res.response || streamed || '', res.sources || [], queryText).then((checked) => {
          const confidence = checked?.confidence;
          if (!confidence) return;
          setResponseConfidence(confidence);
          setConversationTurns((prev) => prev.map((turn) => turn.id === turnId ? { ...turn, confidence } : turn));
          saveLocalConversation({ ...newHistoryEntry, updatedAt: new Date().toISOString(), messages: [{ role: 'user', content: queryText }, { role: 'assistant', content: res.response || streamed || '', sources: res.sources || [], confidence }] }).catch(() => {});
        }).catch((error) => console.warn('[confidence check failed]', error.message)).finally(() => setConfidenceChecking(false));
        saveLocalConversation({ ...newHistoryEntry, updatedAt: new Date().toISOString(), messages: [
          { role: 'user', content: queryText, created_at: new Date().toISOString() },
          { role: 'assistant', content: res.response || streamed || '', sources: res.sources || [], confidence: res.confidence || null, created_at: new Date().toISOString() },
        ] }).catch(() => {});
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
      if (err?.name === 'AbortError' || requestController.signal.aborted) {
        setConversationTurns((prev) => prev.map((turn) => turn.id === turnId ? { ...turn, isLoading: false, stopped: true } : turn));
        setErrorFeedback('Stopped');
        return;
      }
      setConversationTurns((prev) => prev.map((turn) => turn.id === turnId
        ? { ...turn, isLoading: false, error: err.message }
        : turn));
      setSessionState('FAILED');
      setErrorFeedback(err?.name === 'TypeError' ? 'Connection lost' : `Submission failed: ${err.message}`);
    } finally {
      setIsPending(false);
      if (requestControllerRef.current === requestController) requestControllerRef.current = null;
      sendingRef.current = false;
    }
  };

  const handleStopRequest = () => requestControllerRef.current?.abort();

  const handleSelectConversation = async (item, updateUrl = true) => {
    const selectedId = item?.conversationId || item?.id;
    if (!selectedId) return;
    setSidebarOpen(false);
    if (updateUrl) window.history.pushState({ chatId: selectedId }, '', `/chat/${encodeURIComponent(selectedId)}`);
    setHistoryLoadState('loading');
    const messages = await fetchConversationMessages(selectedId);
    const rows = Array.isArray(messages) ? messages : (messages?.messages || []);
    const turns = [];
    let current = null;
    for (const message of rows) {
      if (message.role === 'user') {
        current = { id: message.id || `${selectedId}:${turns.length}`, question: message.content || '', answer: '', sources: [], confidence: null, activity: [], isLoading: false, mode: 'normal' };
        turns.push(current);
      } else if (message.role === 'assistant' && current) {
        current.answer = message.content || '';
        current.sources = message.sources || message.metadata?.sources || [];
        current.confidence = message.confidence || message.metadata?.confidence || null;
        current.activity = message.activity || message.research_steps || message.metadata?.activity || [];
      }
    }
    if (!turns.length) {
      setHistoryLoadState('not_found');
      setErrorFeedback('Conversation not found');
      return;
    }
    setHistoryLoadState('ready');
    setConversationId(selectedId);
    setConversationTurns(turns);
    setUserQuestion(turns.at(-1)?.question || '');
    setNormalAnswer(turns.at(-1)?.answer || '');
    setIsDeepResearch(false);
    setSessionState(turns.length ? 'COMPLETE' : 'IDLE');
    setErrorFeedback(null);
    setActiveNav('research');
  };

  useEffect(() => {
    const onPopState = () => {
      const match = window.location.pathname.match(/^\/chat\/([^/]+)/);
      if (!match) {
        handleNewQuestion();
        return;
      }
      const item = historyItems.find((entry) => String(entry.conversationId || entry.id) === decodeURIComponent(match[1]));
      if (item) handleSelectConversation(item, false);
    };
    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, [historyItems]);

  useEffect(() => {
    if (!historyItems.length) return;
    const match = window.location.pathname.match(/^\/chat\/([^/]+)/);
    if (match && !conversationTurns.length) {
      const id = decodeURIComponent(match[1]);
      const item = historyItems.find((entry) => String(entry.conversationId || entry.id) === id);
      if (item) handleSelectConversation(item, false);
      else setHistoryLoadState('not_found');
    }
  }, [historyItems]);

  // Initialize and synchronize URL path (/atlas, /atlas/experiments, etc.)
  useEffect(() => {
    const path = window.location.pathname;
    if (path.startsWith('/atlas')) {
      const sub = path.replace(/^\/atlas\/?/, '');
      if (['research', 'experiments', 'sources', 'hypotheses', 'reports', 'history'].includes(sub)) {
        setActiveNav(sub);
      }
    } else if (!path.startsWith('/chat/')) {
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
        sidebarOpen={sidebarOpen}
        onToggleSidebar={() => setSidebarOpen((open) => !open)}
        historyLoadState={historyLoadState}
        activeConversationId={conversationId}
        confidenceChecking={confidenceChecking}
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
        historyItems={historyItems}
        onSelectHistoryItem={handleSelectConversation}
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
          onNewQuestion={handleNewQuestion}
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
                        confidenceChecking={confidenceChecking}
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
                        reportMd={reportMd || streamedResearchAnswer}
                        backendConnected={backendConnected}
                        connectionState={connectionState}
                        confidence={responseConfidence}
                        confidenceChecking={confidenceChecking}
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
                <div className="max-w-xl mx-auto w-full">
                  <QuestionComposer
                    onSubmit={handleSendQuestion}
                    isPending={isPending}
                    backendConnected={backendConnected}
                    connectionState={connectionState}
                    errorFeedback={errorFeedback}
                    onStop={handleStopRequest}
                    onRetry={() => userQuestion && handleSendQuestion(userQuestion)}
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

  const handleSignOut = () => {
    window.history.pushState({}, '', '/atlas');
    setCurrentPath('/atlas');
  };

  return (
    <WorkspaceApp
      onSignOut={handleSignOut}
    />
  );
}
