import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import QuestionComposer from './components/QuestionComposer';
import ScientificInquiryCard from './components/ScientificInquiryCard';
import RightSidebar from './components/RightSidebar';
import NormalAnswerView from './components/NormalAnswerView';
import ResearchWorkspaceView from './components/ResearchWorkspaceView';
import ExperimentsView from './components/ExperimentsView';
import SourcesView from './components/SourcesView';
import HypothesesView from './components/HypothesesView';
import ReportsView from './components/ReportsView';
import HistoryView from './components/HistoryView';
import SettingsModal from './components/SettingsModal';
import AtlasLogo from './components/AtlasLogo';
import { getDynamicGreeting, ROTATING_PLACEHOLDERS } from './utils/greeting';

import {
  fetchHealth,
  fetchSettings,
  fetchProjects,
  fetchProjectDetails,
  sendDeepResearchStream,
  sendChatMessage,
  fetchProjectReport,
  fetchProjectBaselines,
  fetchProjectLiterature,
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

export default function App() {
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

    // Disconnected Backend Guard (Req §1 & §15)
    if (connectionState === 'CONNECTING') {
      setIsPending(false);
      return;
    }
    if (!backendConnected) {
      setIsPending(false);
      setSessionState('FAILED');
      setErrorFeedback('Research service not configured. No investigation or experiment has started.');
      return;
    }

    if (onSuccess) onSuccess();

    // Determine initial routing intention
    const deepCheck = isLikelyDeepResearch(queryText);
    setIsDeepResearch(deepCheck);
    setRoutingMode(deepCheck ? 'AUTO: Deep Research' : 'AUTO: Normal Answer');
    setSessionState(deepCheck ? 'QUEUED' : 'IN_PROGRESS');

    // Create history item entry
    const newHistoryEntry = {
      id: Date.now(),
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
            return updated;
          });
        };

        const res = await sendDeepResearchStream(
          queryText,
          activeProject?.id,
          conversationId,
          null,
          null,
          { requestId: createConversationId() },
          [],
          onActivity
        );

        if (res) {
          setSessionState('COMPLETE');
          // Reconcile the 13-step list against what actually executed:
          //  - Step 1 (scoping) and step 13 (report) always complete here.
          //  - Dataset/experiment stages that never ran AND had no dataset
          //    target are marked "skipped — not applicable" with a reason, so
          //    the header can honestly read "Completed with Limited Scope"
          //    instead of showing unchecked circles next to "Complete".
          const ranExperiments = !!res.project;
          setStageEvents((prev) => {
            const ranIndices = new Set(prev.map((e) => e.stageIndex));
            const kept = prev.filter((e) => e.stageIndex !== 1 && e.stageIndex !== 13);
            const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
            const next = [
              { stageIndex: 1, status: 'completed', detail: 'Research problem analyzed and scoped', timestamp: now },
              ...kept,
              { stageIndex: 13, status: 'completed', detail: 'Final research report compiled', timestamp: now },
            ];
            if (!ranExperiments) {
              for (const s of DATASET_DEPENDENT_STAGES) {
                if (!ranIndices.has(s)) {
                  next.push({
                    stageIndex: s,
                    status: 'skipped',
                    detail: 'Skipped — not applicable: no dataset attached, so experiment stages did not run',
                    timestamp: now,
                  });
                }
              }
            }
            return next;
          });

          if (res.response) {
            setReportMd(res.response);
            setLatestInsight(res.response.slice(0, 240) + '…');
          }
          setResponseConfidence(res.confidence || null);

          if (res.project) {
            setActiveProject(res.project);
          }

          if (onSuccess) onSuccess();
        }
      } else {
        // Simple Question / Normal Answer Path
        const res = await sendChatMessage(
          queryText,
          activeProject?.id,
          conversationId
        );

        setSessionState('COMPLETE');
        setNormalAnswer(res.response || 'No response returned.');
        setResponseConfidence(res.confidence || null);
        setIsBuiltInExplanation(res.action === 'NONE' || !sysSettings.apiKeySet);

        if (res.citationPolicy === 'required' && res.sources) {
          setNormalSources(res.sources);
        }

        if (onSuccess) onSuccess();
      }
    } catch (err) {
      setSessionState('FAILED');
      setErrorFeedback(`Submission failed: ${err.message}`);
    } finally {
      setIsPending(false);
    }
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

  return (
    <div className="flex h-screen w-screen bg-[#121212] text-[#E8E5DF] font-sans overflow-hidden select-none">
      
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
          <main className="flex-1 min-w-0 flex flex-col h-full overflow-hidden relative bg-[#121212]">
            
            {/* View Switching based on activeNav destination */}
            {activeNav === 'research' && (
              <AnimatePresence mode="wait">
                {!userQuestion && sessionState === 'IDLE' ? (
                  // Initial Centered Start Screen View
                  <motion.div
                    key="start-screen"
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -20, transition: { duration: 0.35, ease: [0.16, 1, 0.3, 1] } }}
                    className="flex-1 flex flex-col items-center justify-center p-6 text-center max-w-2xl mx-auto space-y-6 my-auto select-none"
                  >
                    <motion.div
                      initial={{ scale: 0.9, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      transition={{ duration: 0.4 }}
                      className="flex flex-col items-center space-y-3"
                    >
                      <AtlasLogo className="w-12 h-12 shrink-0" />
                      <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-[#E8E5DF] font-sans">
                        {greeting.main}
                      </h1>
                      <p className="text-sm text-[#8A8884] font-sans max-w-md">
                        {greeting.sub}
                      </p>
                    </motion.div>

                    {/* Centered Command Search Bar */}
                    <div className="w-full max-w-xl">
                      <QuestionComposer
                        onSubmit={handleSendQuestion}
                        isPending={isPending}
                        backendConnected={backendConnected}
                        connectionState={connectionState}
                        errorFeedback={errorFeedback}
                        placeholder={ROTATING_PLACEHOLDERS[placeholderIdx]}
                        isEmptyState={true}
                      />
                    </div>

                    {/* Quick Research Suggestions */}
                    <div className="flex flex-wrap items-center justify-center gap-2 pt-2 text-xs">
                      {[
                        "Improve credit card fraud detection recall",
                        "Compare XGBoost vs Random Forest",
                        "Explain overfitting remedies",
                      ].map((promptText, i) => (
                        <button
                          key={i}
                          type="button"
                          onClick={() => handleSendQuestion(promptText)}
                          className="px-3.5 py-1.5 rounded-xl bg-[#1B1B1C] hover:bg-[#252528] border border-[#2E2E34] text-[#A1A1AA] hover:text-[#E8E5DF] transition-all cursor-pointer font-sans"
                        >
                          {promptText}
                        </button>
                      ))}
                    </div>
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
                        isLoading={isPending}
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
                onSelectHistoryItem={(item) => handleSendQuestion(item.question)}
              />
            )}

            {/* Anchored Bottom Command Composer (shown only when in active conversation view) */}
            {activeNav === 'research' && (userQuestion || sessionState !== 'IDLE') && (
              <motion.div
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
                className="absolute bottom-0 left-0 right-0 p-3 sm:p-4 bg-gradient-to-t from-[#121212] via-[#121212]/95 to-transparent z-20"
              >
                <div className="max-w-3xl mx-auto w-full">
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
      />
    </div>
  );
}
