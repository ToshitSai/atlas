import React, { useState, useEffect } from 'react';
import { useAuth } from '@clerk/react';
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
import AuthScreen from './components/AuthScreen';

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
  setAuthTokenProvider,
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

// Stage mapping to 13 Scientific Inquiry stages
const STAGE_NAME_MAP = {
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
};

export default function App() {
  const { isLoaded: authLoaded, isSignedIn, getToken } = useAuth();
  // Navigation & Active View
  const [activeNav, setActiveNav] = useState('research'); // 'research' | 'experiments' | 'sources' | 'hypotheses' | 'reports' | 'history'
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  // System & Connection State
  const [backendConnected, setBackendConnected] = useState(false);
  const [sysSettings, setSysSettings] = useState({});

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

  useEffect(() => {
    if (!authLoaded) return undefined;
    setAuthTokenProvider(isSignedIn ? getToken : null);
    return () => setAuthTokenProvider(null);
  }, [authLoaded, isSignedIn, getToken]);

  // Check Backend Connection on Mount & Periodically
  const checkBackend = async () => {
    try {
      const health = await fetchHealth();
      setBackendConnected(health && health.status === 'healthy');
      const settings = await fetchSettings();
      setSysSettings(settings);
    } catch (e) {
      setBackendConnected(false);
    }
  };

  useEffect(() => {
    if (!authLoaded || !isSignedIn) return undefined;
    checkBackend();
    const interval = setInterval(checkBackend, 5000);
    return () => clearInterval(interval);
  }, [authLoaded, isSignedIn]);

  if (!authLoaded) return <div className="grid min-h-screen place-items-center bg-[#09070a] text-orange-400">Loading secure workspace…</div>;
  if (!isSignedIn) return <AuthScreen />;

  // Handle New Question / Reset State
  const handleNewQuestion = () => {
    setUserQuestion('');
    setNormalAnswer('');
    setNormalSources([]);
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

    // Disconnected Backend Guard (Req §1 & §15)
    if (!backendConnected) {
      setIsPending(false);
      setSessionState('FAILED');
      setErrorFeedback('Research service not configured. No investigation or experiment has started.');
      return;
    }

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
          // Complete stage 1 & 13
          setStageEvents((prev) => [
            { stageIndex: 1, status: 'completed', detail: 'Research problem analyzed and scoped', timestamp: new Date().toLocaleTimeString() },
            ...prev.filter((e) => e.stageIndex !== 1 && e.stageIndex !== 13),
            { stageIndex: 13, status: 'completed', detail: 'Final research report compiled', timestamp: new Date().toLocaleTimeString() },
          ]);

          if (res.response) {
            setReportMd(res.response);
            setLatestInsight(res.response.slice(0, 240) + '…');
          }

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

  // Download Report as Markdown (.md) file
  const handleDownloadReport = () => {
    if (!reportMd) return;
    const blob = new Blob([reportMd], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `AI_Scientist_Research_Report_${Date.now()}.md`;
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
    <div className="flex h-screen w-screen bg-[#080808] text-[#F4F4F6] font-sans overflow-hidden select-none">
      
      {/* 1. Left Navigation Column (~210px wide) */}
      <Sidebar
        activeNav={activeNav}
        onSelectNav={setActiveNav}
        onNewQuestion={handleNewQuestion}
        onOpenSettings={() => setIsSettingsOpen(true)}
        isMobileOpen={isMobileNavOpen}
        onMobileClose={() => setIsMobileNavOpen(false)}
        backendConnected={backendConnected}
      />

      {/* Main Workspace Stack (Center Column + Right Context Sidebar) */}
      <div className="flex-1 min-w-0 flex flex-col h-screen overflow-hidden">
        
        {/* Compact Top Header */}
        <Header
          sessionStatus={sessionState}
          routingMode={routingMode}
          backendConnected={backendConnected}
          onOpenMobileNav={() => setIsMobileNavOpen(true)}
          activeNavTitle={navTitles[activeNav] || 'Research Workspace'}
        />

        {/* 3-Column Content Body */}
        <div className="flex-1 min-w-0 flex overflow-hidden relative">
          
          {/* 2. Center Workspace Area (Flexible width) */}
          <main className="flex-1 min-w-0 flex flex-col h-full overflow-hidden relative bg-[#080808]">
            
            {/* View Switching based on activeNav destination */}
            {activeNav === 'research' && (
              <>
                {!userQuestion && sessionState === 'IDLE' ? (
                  // Initial Welcome / Guidance View
                  <div className="flex-1 flex flex-col items-center justify-center p-6 text-center max-w-xl mx-auto space-y-4 animate-panel-entrance">
                    <div className="w-12 h-12 rounded-xl bg-[#FF6500]/10 border border-[#FF6500]/40 flex items-center justify-center">
                      <svg className="w-6 h-6 text-[#FF6500]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <circle cx="12" cy="12" r="3" />
                        <path d="M12 3a9 9 0 0 1 9 9" />
                        <path d="M3 12a9 9 0 0 1 9-9" />
                        <path d="M12 21a9 9 0 0 1-9-9" />
                      </svg>
                    </div>
                    <div className="space-y-1 font-sans">
                      <h2 className="text-base font-semibold text-[#F4F4F6] font-sans tracking-normal">
                        AI Scientist Workspace
                      </h2>
                      <p className="text-xs text-[#8A8F98] leading-relaxed font-sans">
                        Ask a simple question for a concise explanation, or enter a complex machine learning query to trigger an autonomous scientific research pipeline.
                      </p>
                    </div>

                    {!backendConnected && (
                      <div className="p-3 rounded-xl bg-[#F87171]/10 border border-[#F87171]/30 text-xs font-sans text-[#F87171] w-full">
                        Research service not configured. No investigation or experiment has started.
                      </div>
                    )}
                  </div>
                ) : !isDeepResearch ? (
                  // Simple Question Normal Answer View
                  <NormalAnswerView
                    userQuestion={userQuestion}
                    answer={normalAnswer}
                    routingMode={routingMode}
                    isBuiltInExplanation={isBuiltInExplanation}
                    sources={normalSources}
                  />
                ) : (
                  // Deep Research Workspace View (Activity Card, Experiments, Report)
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
                    canRetry={sessionState === 'FAILED'}
                    onRetryStage={() => handleSendQuestion(userQuestion)}
                    onDownloadReport={handleDownloadReport}
                  />
                )}
              </>
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

            {/* Anchored Bottom Command Composer (Reserved padding prevents covering content) */}
            <div className="absolute bottom-0 left-0 right-0 p-3 sm:p-4 bg-gradient-to-t from-[#080808] via-[#080808]/95 to-transparent z-20">
              <div className="max-w-3xl mx-auto w-full">
                <QuestionComposer
                  onSubmit={handleSendQuestion}
                  isPending={isPending}
                  backendConnected={backendConnected}
                  errorFeedback={errorFeedback}
                />
              </div>
            </div>
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
