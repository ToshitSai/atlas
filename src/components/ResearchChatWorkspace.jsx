import React, { useState, useEffect, useRef } from 'react';
import {
  fetchProjectDataset,
  fetchProjectBaselines,
  fetchProjectTree,
  fetchProjectErrorAnalysis,
  fetchProjectLiterature,
  fetchProjectReport,
  sendControlSignal,
  sendChatMessage
} from '../api';
import ActivityPanel from './ActivityPanel';
import ChatMarkdown from './ChatMarkdown';
import ResearchWorkspace from './research/ResearchWorkspace';
import { API_ORIGIN } from '../api';

export default function ResearchChatWorkspace({
  activeProject,
  setActiveProject,
  onNewResearch,
  onOpenSettings,
  chatMessages,
  setChatMessages,
  onApproveDataset,
  isApproving,
  conversationId: propsConversationId,
  onConversationUpdated,
  initialRequestStartedAt,
  onOpenMenu
}) {
  const [activeTab, setActiveTab] = useState('chat'); // 'workspace' | 'chat' | 'report'
  const [datasetReport, setDatasetReport] = useState(null);
  const [baselines, setBaselines] = useState([]);
  const [treeNodes, setTreeNodes] = useState([]);
  const [errorAnalysis, setErrorAnalysis] = useState(null);
  const [literature, setLiterature] = useState([]);
  const [reportMd, setReportMd] = useState(null);
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);
  const [chatInput, setChatInput] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [pendingAction, setPendingAction] = useState(null);
  const [lastTopic, setLastTopic] = useState(null);
  const inFlightRequests = useRef(new Set());
  const [localConversationId] = useState(() => 'conv-' + (globalThis.crypto?.randomUUID?.() || Math.random().toString(36).slice(2)));
  const [processingCount, setProcessingCount] = useState(0);
  const [activeRequests, setActiveRequests] = useState({});
  // Prefer the app-level conversation (shared with the first message) so the
  // whole chat shares one server-side memory.
  const conversationId = propsConversationId || localConversationId;
  const chatBottomRef = useRef(null);

  const projectId = activeProject?.id;
  const isRunning = activeProject?.status === 'IN_PROGRESS' || activeProject?.status === 'QUEUED';
  const isCompleted = activeProject?.status === 'COMPLETED';

  // When a research project becomes active, lead with the structured research
  // workspace instead of the chat bubble. The user can still switch to the Chat
  // or Report tabs; this only sets the initial view when the project changes.
  useEffect(() => {
    if (projectId) setActiveTab('workspace');
  }, [projectId]);

  // Real run-control action wired to the backend control signal (pause/stop/resume).
  const handleControl = async (signal) => {
    if (!projectId) return;
    try {
      await sendControlSignal(projectId, signal);
    } catch (err) {
      console.error('Control signal failed:', err);
    }
  };

  useEffect(() => {
    if (!projectId) return;

    const loadData = async () => {
      try {
        const [dData, bData, tData, eData, lData, rData] = await Promise.all([
          fetchProjectDataset(projectId),
          fetchProjectBaselines(projectId),
          fetchProjectTree(projectId),
          fetchProjectErrorAnalysis(projectId),
          fetchProjectLiterature(projectId),
          fetchProjectReport(projectId)
        ]);

        setDatasetReport(dData);
        setBaselines(bData);
        setTreeNodes(tData);
        setErrorAnalysis(eData);
        setLiterature(lData);
        setReportMd(rData);
      } catch (err) {
        console.error("Error loading workspace details:", err);
      }
    };

    loadData();
    const interval = setInterval(loadData, 2000);
    return () => clearInterval(interval);
  }, [projectId]);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [activeProject, treeNodes, chatMessages, activeTab]);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!chatInput.trim()) return;

    const userText = chatInput.trim();
    const requestId = globalThis.crypto?.randomUUID?.() || `request-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    const userMessageId = globalThis.crypto?.randomUUID?.() || `message-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    setChatInput('');
    inFlightRequests.current.add(requestId);
    setProcessingCount(inFlightRequests.current.size);
    setIsProcessing(true);
    setActiveRequests(previous => ({ ...previous, [requestId]: { requestId, startedAt: Date.now() } }));

    // The response carries this id back; it is the stable UI/API association.
    const userMsg = { id: userMessageId, requestId, role: 'user', content: userText };
    setChatMessages(prev => [...prev, userMsg]);

    try {
      // 2. Call backend Intent Router endpoint
      const res = await sendChatMessage(userText, projectId, conversationId, pendingAction, lastTopic, {
        requestId,
        messageId: userMessageId
      }, [...chatMessages, userMsg]);
      if (res.requestId !== requestId || res.responseToMessageId !== userMessageId) {
        throw new Error('The response could not be matched to the submitted message. Please retry.');
      }
      if (!inFlightRequests.current.has(requestId)) return;

      if (res.pendingAction !== undefined) {
        setPendingAction(res.pendingAction);
      }
      if (res.lastTopic) {
        setLastTopic(res.lastTopic);
      }

      const assistantMsg = {
        id: res.messageId,
        conversationId: res.conversationId,
        requestId,
        responseToMessageId: res.responseToMessageId,
        role: 'assistant',
        content: res.response,
        intent: res.intent,
        action: res.action,
        datasets: res.candidates || null,
        recommendation: res.recommendation || null,
        researchQuery: res.researchQuery || null,
        selectionMode: res.selectionMode || null,
        selectedDataset: res.selectedDataset || null,
        activity: res.activity || []
      };

      setChatMessages(prev => [...prev, assistantMsg]);

      // 3. Handle actions returned by Intent Router
      if (res.action === 'START_RESEARCH' && res.project) {
        setActiveProject(res.project);
      } else if (res.action === 'STOP_RESEARCH' && projectId) {
        await sendControlSignal(projectId, 'STOP');
      } else if (res.action === 'RESUME_RESEARCH' && projectId) {
        await sendControlSignal(projectId, 'RUN');
      } else if (res.action === 'SHOW_REPORT') {
        setActiveTab('report');
      } else if (res.action === 'SHOW_TECHNICAL') {
        setShowTechnicalDetails(true);
      }
    } catch (err) {
      setChatMessages(prev => [
        ...prev,
        { id: `${userMessageId}-error`, requestId, responseToMessageId: userMessageId, role: 'assistant', content: `Sorry, I ran into an error: ${err.message}` }
      ]);
    } finally {
      await onConversationUpdated?.();
      inFlightRequests.current.delete(requestId);
      setActiveRequests(previous => {
        const next = { ...previous };
        delete next[requestId];
        return next;
      });
      setProcessingCount(inFlightRequests.current.size);
      setIsProcessing(inFlightRequests.current.size > 0);
    }
  };

  const stageStates = activeProject?.stageStates || {};

  // Honest completion summary built ONLY from real stored results: compare the
  // best follow-up experiment against the baseline instead of claiming a win.
  const expNodes = treeNodes.filter(n => n.parentId !== null && n.metricValue != null);
  const metricName = (treeNodes[0] && treeNodes[0].metricName) || (expNodes[0] && expNodes[0].metricName) || 'metric';
  let completionSummary = "I've prepared the research report for you.";
  if (expNodes.length > 0) {
    const bestExp = expNodes.reduce((a, b) => ((b.metricValue ?? 0) > (a.metricValue ?? 0) ? b : a));
    const baseVal = (treeNodes.find(n => n.parentId === null) || {}).metricValue;
    const fmt = (v) => (typeof v === 'number' ? v.toFixed(4) : v);
    if (typeof baseVal === 'number' && bestExp.metricValue > baseVal) {
      completionSummary = `The best approach (${bestExp.title}) reached ${metricName} ${fmt(bestExp.metricValue)}, improving on the baseline's ${fmt(baseVal)}.`;
    } else if (typeof baseVal === 'number') {
      completionSummary = `None of the ${expNodes.length} additional approach${expNodes.length > 1 ? 'es' : ''} beat the baseline (${metricName} ${fmt(baseVal)}), so the baseline stands as the strongest model.`;
    } else {
      completionSummary = `The best approach reached ${metricName} ${fmt(bestExp.metricValue)}.`;
    }
  }

  return (
    <div className="flex-1 min-w-0 flex flex-col h-screen bg-[#0B0F17] overflow-hidden select-none">

      {/* Top Header — compact on mobile: [menu] [title] [actions] */}
      <header
        className="h-14 border-b border-[#1E293B] bg-[#0D111A] px-2 sm:px-6 flex items-center justify-between gap-2 shrink-0 min-w-0"
        style={{ paddingTop: 0 }}
      >
        <div className="flex items-center gap-1 sm:gap-3 min-w-0">
          {/* Hamburger on mobile / back-to-start on desktop */}
          {onOpenMenu ? (
            <button
              onClick={onOpenMenu}
              aria-label="Open menu"
              aria-expanded="false"
              className="lg:hidden w-11 h-11 flex items-center justify-center rounded-lg text-slate-400 hover:text-slate-100 hover:bg-[#161B26] transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
          ) : null}
          <button
            onClick={onNewResearch}
            className="hidden lg:block text-slate-400 hover:text-slate-200 transition-colors p-2.5 rounded-lg hover:bg-[#161B26]"
            title="New Research Chat"
            aria-label="New research chat"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" aria-hidden="true">
              <path d="M19 12H5M12 19l-7-7 7-7" />
            </svg>
          </button>

          <div className="flex items-center gap-2 min-w-0">
            <h2 className="text-sm font-semibold text-slate-100 flex items-center gap-2 font-sans min-w-0">
              <span className="shrink-0">AI Scientist</span>
              {activeProject && (
                <span className={`hidden sm:inline-flex text-[11px] font-medium px-2.5 py-0.5 rounded-full border shrink-0 ${
                  isCompleted
                    ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                    : 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30 animate-pulse'
                }`}>
                  {isCompleted ? '✓ Research Complete' : '● Active Study'}
                </span>
              )}
            </h2>
          </div>
        </div>

        {/* Header Actions */}
        <div className="flex items-center gap-1.5 sm:gap-3 shrink-0">
          {activeProject && (
            <div className="flex items-center gap-1 bg-[#131822] p-1 rounded-xl border border-[#212B3B] text-xs font-medium">
              {[
                { key: 'workspace', label: 'Workspace', short: 'Lab' },
                { key: 'chat', label: 'Chat', short: 'Chat' },
                { key: 'report', label: 'Report', short: 'Report', icon: reportMd ? '📄' : '' },
              ].map((t) => (
                <button
                  key={t.key}
                  onClick={() => setActiveTab(t.key)}
                  aria-pressed={activeTab === t.key}
                  className={`px-2 sm:px-3 py-1 rounded-lg transition-all min-h-[32px] whitespace-nowrap ${
                    activeTab === t.key
                      ? 'bg-[#1E293B] text-cyan-400 font-semibold shadow-sm'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <span className="hidden sm:inline">{t.label}</span>
                  <span className="sm:hidden">{t.short}</span>
                  {t.icon ? ` ${t.icon}` : ''}
                </button>
              ))}
            </div>
          )}

          <button
            onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
            aria-expanded={showTechnicalDetails}
            className="text-xs font-medium px-2.5 sm:px-3 min-h-[36px] rounded-xl bg-[#131822] border border-[#212B3B] text-slate-300 hover:text-cyan-400 transition-all flex items-center gap-1.5 cursor-pointer"
          >
            <span className="hidden sm:inline">{showTechnicalDetails ? '⚙ Hide Details' : '⚙ View Details'}</span>
            <span className="sm:hidden">{showTechnicalDetails ? '⚙' : '⚙'}</span>
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">

        {/* COLLAPSIBLE TECHNICAL DETAILS PANEL */}
        {showTechnicalDetails && (
          <div className="bg-[#090D14] border-b border-[#1E293B] p-3 sm:p-4 max-h-72 overflow-y-auto overscroll-contain space-y-4 font-mono text-xs text-slate-300 min-w-0">
            <div className="flex items-center justify-between gap-2 border-b border-[#1E293B] pb-2">
              <span className="font-bold text-cyan-400 uppercase text-[11px] shrink-0">Telemetry</span>
              <span className="text-slate-500 text-[10px] truncate">Project ID: {projectId || 'None'}</span>
            </div>

            {activeProject ? (
              <>
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2 text-[11px] min-w-0">
                  {Object.entries(stageStates).map(([k, status]) => (
                    <div key={k} className="p-2 rounded bg-[#0F1420] border border-[#1E293B] min-w-0">
                      <div className="text-slate-500 text-[9px] uppercase truncate" title={k}>{k}</div>
                      <div className={status === 'COMPLETED' ? 'text-emerald-400 font-bold' : status === 'RUNNING' ? 'text-cyan-400 font-bold' : 'text-slate-400'}>
                        {status}
                      </div>
                    </div>
                  ))}
                </div>

                {baselines.length > 0 && (
                  <div className="space-y-1 min-w-0">
                    <div className="text-[10px] text-slate-400 font-semibold uppercase">Evaluated Model Architectures</div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px]">
                      {baselines.map(b => (
                        <div key={b.id} className="p-2 rounded bg-[#0F1420] border border-[#1E293B] flex flex-wrap justify-between gap-x-2 gap-y-0.5 min-w-0">
                          <span className="text-slate-200 font-semibold break-all min-w-0">{b.name} ({b.type})</span>
                          <span className="text-cyan-400 break-all min-w-0">{Object.entries(b.metrics || {}).map(([mk, mv]) => `${mk.toUpperCase()}: ${mv}`).join(' ')}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="text-slate-500 italic text-center py-2">
                No active project telemetry to display.
              </div>
            )}
          </div>
        )}

        {/* STRUCTURED RESEARCH WORKSPACE — primary view for an active study */}
        {activeTab === 'workspace' && activeProject && (
          <ResearchWorkspace
            project={activeProject}
            datasetReport={datasetReport}
            baselines={baselines}
            treeNodes={treeNodes}
            errorAnalysis={errorAnalysis}
            literature={literature}
            reportMd={reportMd}
            onControl={handleControl}
          />
        )}

        {/* CONVERSATIONAL CHAT FEED (intake + follow-ups) */}
        {activeTab === 'chat' && (
          <div className="flex-1 overflow-y-auto overscroll-contain px-3 py-4 sm:p-6 space-y-6 max-w-3xl mx-auto w-full min-w-0 font-sans">

            {/* INITIAL WELCOME MESSAGE IF BRAND NEW CHAT */}
            {chatMessages.length === 0 && !activeProject && (
              <div className="flex justify-start">
                <div className="w-full min-w-0 bg-[#121722] border border-[#1E293B] rounded-2xl p-4 sm:p-6 shadow-xl space-y-4">
                  <div className="flex items-center gap-3 border-b border-[#1E293B]/70 pb-3">
                    <div className="w-8 h-8 rounded-xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 shrink-0">
                      <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                        <circle cx="12" cy="12" r="3" />
                        <path d="M12 3a9 9 0 0 1 9 9" />
                        <path d="M12 21a9 9 0 0 1-9-9" />
                      </svg>
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-slate-100">AI Scientist</h3>
                      <p className="text-xs text-slate-400">Autonomous Machine Learning Assistant</p>
                    </div>
                  </div>
                  <p className="text-sm text-slate-200 leading-relaxed">
                    Hi! 👋 I'm AI Scientist, your autonomous research assistant.
                    What machine learning problem or dataset would you like me to investigate?
                  </p>
                </div>
              </div>
            )}

            {/* RENDER DYNAMIC CHAT MESSAGES */}
            {chatMessages.map((msg) => (
              <div key={msg.id} className={`flex min-w-0 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                {msg.role === 'user' ? (
                  // max-w-xl is the DESKTOP cap; on mobile the bubble simply
                  // fills the available width (max-w-[85%]) and wraps.
                  <div className="max-w-[85%] sm:max-w-xl bg-[#161D2A] border border-[#263347] rounded-2xl p-3.5 sm:p-4 shadow-md space-y-1 min-w-0 overflow-wrap-anywhere">
                    <div className="text-[10px] font-semibold text-cyan-400 uppercase tracking-wider">You</div>
                    <p className="text-sm text-slate-100 font-sans leading-relaxed">{msg.content}</p>
                  </div>
                ) : (
                  <div className="w-full min-w-0 bg-[#121722] border border-[#1E293B] rounded-2xl p-4 sm:p-5 shadow-xl space-y-4 overflow-wrap-anywhere">
                    <div className="flex items-center gap-3 border-b border-[#1E293B]/70 pb-3">
                      <div className="w-7 h-7 rounded-xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 shrink-0">
                        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                          <circle cx="12" cy="12" r="3" />
                          <path d="M12 3a9 9 0 0 1 9 9" />
                        </svg>
                      </div>
                      <h4 className="text-xs font-bold text-slate-100">AI Scientist</h4>
                    </div>

                    <div className="text-sm text-slate-200 leading-relaxed min-w-0">
                      <ChatMarkdown content={msg.content} />
                    </div>

                    <ActivityPanel activities={msg.activity} />

                    {msg.datasets && msg.datasets.length > 0 && (
                    <DatasetCards
                      datasets={msg.datasets}
                      recommendation={msg.recommendation}
                      researchQuery={msg.researchQuery}
                      selectionMode={msg.selectionMode}
                      selectedDataset={msg.selectedDataset}
                      onApprove={onApproveDataset}
                      isApproving={isApproving}
                    />
                    )}
                  </div>
                )}
              </div>
            ))}

            {Object.values(activeRequests).map(request => (
              <div key={request.requestId} className="w-full">
                <ActivityPanel running startedAt={request.startedAt} />
              </div>
            ))}

            {initialRequestStartedAt && (
              <div className="w-full">
                <ActivityPanel running startedAt={initialRequestStartedAt} />
              </div>
            )}

            {/* SLIM POINTER TO THE STRUCTURED WORKSPACE. The full pipeline,
                experiment cards, analysis and report live in the Workspace tab
                (ResearchWorkspace) — not in a giant chat bubble. */}
            {activeProject && (
              <div className="w-full min-w-0 bg-[#121722] border border-[#1E293B] rounded-2xl p-4 shadow-xl flex flex-wrap items-center justify-between gap-3 overflow-wrap-anywhere">
                <div className="flex items-center gap-2.5 min-w-0">
                  <span className="text-lg shrink-0">🔬</span>
                  <div className="min-w-0">
                    <div className="text-xs font-semibold text-slate-200">
                      {isCompleted ? 'Research complete' : isRunning ? 'Research in progress…' : 'Research paused'}
                    </div>
                    <div className="text-[11px] text-slate-500 break-words overflow-wrap-anywhere">
                      {completionSummary}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => setActiveTab('workspace')}
                    className="px-3.5 py-2 min-h-[38px] rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs shadow-md transition-all cursor-pointer"
                  >
                    Open workspace
                  </button>
                  {isCompleted && (
                    <button
                      onClick={() => setActiveTab('report')}
                      className="px-3.5 py-2 min-h-[38px] rounded-xl bg-[#1A2232] hover:bg-[#253147] text-slate-200 border border-[#2B364A] font-semibold text-xs transition-all cursor-pointer"
                    >
                      📄 Report
                    </button>
                  )}
                </div>
              </div>
            )}

            <div ref={chatBottomRef} />
          </div>
        )}

        {/* TAB 2: REPORT VIEW */}
        {activeTab === 'report' && (
          <div className="flex-1 overflow-y-auto overscroll-contain px-3 py-4 sm:p-6 max-w-3xl mx-auto w-full min-w-0">
            <div className="bg-[#131824] border border-[#212B3B] rounded-2xl p-4 sm:p-6 space-y-4 shadow-xl min-w-0">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#212B3B] pb-3">
                <h3 className="text-base font-bold text-slate-100 flex items-center gap-2 font-sans">
                  <span>📄</span> Scientific Research Report
                </h3>
                {reportMd && (
                  <a
                    href={`${API_ORIGIN}/api/projects/${projectId}/report/download?fmt=md`}
                    download={`Research_Report_${projectId}.md`}
                    className="px-3 py-2 min-h-[36px] rounded-lg bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 text-xs font-medium transition-all inline-flex items-center"
                  >
                    Download Markdown (.md)
                  </a>
                )}
              </div>

              {reportMd ? (
                // Report text wraps instead of stretching the page; long
                // tokens break so the page never scrolls horizontally.
                <div className="prose prose-invert max-w-none text-xs text-slate-300 font-sans leading-relaxed bg-[#080C14] p-4 sm:p-5 rounded-xl border border-[#1E293B] whitespace-pre-wrap break-words min-w-0 overflow-wrap-anywhere">
                  {reportMd}
                </div>
              ) : (
                <div className="text-slate-500 italic text-xs py-8 text-center">
                  Compiling research report...
                </div>
              )}
            </div>
          </div>
        )}

        {/* BOTTOM CHAT INPUT BAR — available in both the Workspace and Chat tabs
            so follow-up questions never require leaving the research view. */}
        {(activeTab === 'chat' || activeTab === 'workspace') && (
          <div
            className="px-3 py-3 sm:p-4 border-t border-[#1E293B] bg-[#0D111A] shrink-0 min-w-0"
            style={{ paddingBottom: 'max(0.75rem, env(safe-area-inset-bottom))' }}
          >
            <form onSubmit={handleSendMessage} className="max-w-3xl mx-auto flex items-center gap-2 min-w-0">
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                placeholder="Ask AI Scientist anything..."
                className="flex-1 min-w-0 bg-[#131822] border border-[#212B3B] focus:border-cyan-500/50 rounded-xl px-3.5 sm:px-4 py-2.5 min-h-[44px] text-xs sm:text-sm text-slate-100 placeholder-slate-500 focus:outline-none font-sans"
              />
              <button
                type="submit"
                disabled={!chatInput.trim() || isProcessing}
                aria-label="Send message"
                className={`shrink-0 px-4 sm:px-5 py-2.5 min-h-[44px] rounded-xl text-xs font-semibold transition-all ${
                  chatInput.trim() && !isProcessing
                    ? 'bg-cyan-500 text-slate-950 hover:bg-cyan-400 cursor-pointer'
                    : 'bg-[#1C2536] text-slate-600 cursor-not-allowed'
                }`}
              >
                {processingCount > 0 ? `Sending (${processingCount})...` : 'Send'}
              </button>
            </form>
          </div>
        )}

      </div>
    </div>
  );
}

function DatasetCards({ datasets, recommendation, researchQuery, selectionMode, selectedDataset, onApprove, isApproving }) {
  const recId = recommendation?.repoId;
  const autonomous = selectionMode === 'AUTONOMOUS' && !!selectedDataset;
  const fmtRows = (n) => (typeof n === 'number' ? n.toLocaleString() : null);

  return (
    <div className="space-y-3 pt-1 min-w-0">
      {autonomous && (
        <p className="text-[11px] text-slate-400">
          These cards are informational — the highlighted dataset was selected automatically.
          Pick a different one any time and I'll continue the research from there.
        </p>
      )}
      {datasets.map((d) => {
        const isRec = d.repoId === recId;
        const rows = fmtRows(d.rowCountPreview);
        const unknown = 'Not detected yet';
        const rowsValue = d.sizeCategory
          ? `${d.sizeCategory}${rows ? ` · preview ${rows}` : ''}`
          : rows ? `Preview ${rows}` : unknown;
        const licenseIsUnclear = !d.license || ['other', 'unknown', 'unspecified'].includes(String(d.license).toLowerCase());
        return (
          <div
            key={d.repoId}
            className={`rounded-xl border p-3 sm:p-4 space-y-2.5 transition-all min-w-0 overflow-wrap-anywhere ${
              isRec
                ? 'bg-[#0D1A20] border-cyan-500/40 shadow-md'
                : 'bg-[#0B0F17] border-[#1E293B]'
            }`}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-semibold text-slate-100 break-all min-w-0">{d.repoId}</span>
                  {isRec && (
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-cyan-500/15 text-cyan-400 border border-cyan-500/30 shrink-0">
                      ★ Recommended
                    </span>
                  )}
                  {d.userSelected && (
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 shrink-0">
                      You linked this
                    </span>
                  )}
                </div>
                {d.description && (
                  <p className="text-[11px] text-slate-400 mt-1 line-clamp-2">{d.description}</p>
                )}
              </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-[11px]">
              <Meta label="Rows" value={rowsValue} />
              <Meta label="Features" value={d.featureCount != null ? d.featureCount : unknown} />
              <Meta label="Target" value={d.targetColumn || unknown} />
              <Meta label="License" value={licenseIsUnclear ? 'Unclear — verify' : d.license} />
              <Meta label="Format" value={d.format || unknown} />
              <Meta label="Splits" value={(d.splits && d.splits.length) ? d.splits.join(', ') : unknown} />
            </div>

            {d.samplingPlan && (
              <div className="text-[11px] text-amber-300/90">{d.samplingPlan}</div>
            )}

            {licenseIsUnclear && (
              <div className="text-[11px] text-amber-300/90">License terms are unclear; verify them before use.</div>
            )}

            {d.minorityClassPct != null && (
              <div className="text-[11px] text-amber-300/90">
                Imbalanced: the positive class is only {d.minorityClassPct}% of records.
              </div>
            )}

            {d.reasons && d.reasons.length > 0 && (
              <ul className="space-y-0.5 min-w-0">
                {d.reasons.slice(0, 4).map((r, i) => (
                  <li key={i} className="text-[11px] text-slate-400 flex gap-1.5 min-w-0">
                    <span className="text-cyan-500 shrink-0">•</span>
                    <span className="min-w-0">{r}</span>
                  </li>
                ))}
              </ul>
            )}

            <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
              <span className="text-[10px] text-slate-500">
                {(d.downloads != null) && `${d.downloads.toLocaleString()} downloads`}
                {(d.likes != null && d.likes > 0) && ` · ${d.likes} likes`}
              </span>
              <button
                onClick={() => onApprove && onApprove(d.repoId, researchQuery)}
                disabled={isApproving}
                className={`px-3.5 py-2 min-h-[38px] rounded-lg text-xs font-semibold transition-all ${
                  isApproving
                    ? 'bg-[#1C2536] text-slate-500 cursor-not-allowed'
                    : isRec
                      ? 'bg-cyan-500 hover:bg-cyan-400 text-slate-950 cursor-pointer shadow-md'
                      : 'bg-[#1A2232] hover:bg-[#253147] text-slate-200 border border-[#2B364A] cursor-pointer'
                }`}
              >
                {isApproving ? 'Loading…' : 'Use this dataset'}
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function Meta({ label, value }) {
  return (
    <div className="p-2 rounded-lg bg-[#121722] border border-[#212B3B] min-w-0">
      <div className="text-slate-500 text-[9px] uppercase tracking-wide">{label}</div>
      <div className="text-slate-200 font-medium truncate" title={String(value)}>{value}</div>
    </div>
  );
}
