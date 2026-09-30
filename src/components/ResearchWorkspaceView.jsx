import React, { useState } from 'react';
import ScientificInquiryCard from './ScientificInquiryCard';
import ChatMarkdown from './ChatMarkdown';

/**
 * Research Workspace View (Center Column):
 * Handles complex research questions with the signature Scientific Inquiry card,
 * experiment cards, measured metrics, report view with working Markdown download,
 * and collapsible experiment history.
 */
export default function ResearchWorkspaceView({
  userQuestion = '',
  routingMode = 'AUTO (Deep Research)',
  sessionState = 'IDLE', // 'QUEUED' | 'IN_PROGRESS' | 'COMPLETE' | 'FAILED' | 'CANCELLED' | 'IDLE'
  stageEvents = [],
  experiments = [], // Real experiments array
  currentExperiment = null,
  latestFinding = null,
  reportMd = null,
  backendConnected = false,
  onRetryStage,
  canRetry = false,
  onDownloadReport,
}) {
  const [historyOpen, setHistoryOpen] = useState(false);
  const [expandedExpId, setExpandedExpId] = useState(null);
  const [activeTab, setActiveTab] = useState('workspace'); // 'workspace' | 'report'

  const toggleExpExpand = (id) => {
    setExpandedExpId(expandedExpId === id ? null : id);
  };

  return (
    <div className="flex-1 overflow-y-auto p-3 sm:p-5 space-y-4 animate-panel-entrance select-none font-sans min-w-0 pb-32">
      
      {/* 1. Current User Question (Strongest textual element on screen - Req §6) */}
      <div className="bg-[#0B0B0B] border border-[#242424] rounded-xl p-4 sm:p-5 space-y-1.5 font-sans">
        <div className="text-xs font-medium text-[#FF6500] font-sans">
          Research Question
        </div>
        <h2 className="text-base sm:text-lg font-semibold text-[#F4F4F6] font-sans leading-relaxed break-words overflow-wrap-anywhere">
          {userQuestion}
        </h2>
      </div>

      {/* 2. Signature Scientific Inquiry Activity Card */}
      <ScientificInquiryCard
        sessionState={sessionState}
        stageEvents={stageEvents}
        onRetry={onRetryStage}
        canRetry={canRetry}
      />

      {/* Disconnected Backend Warning Banner */}
      {!backendConnected && (
        <div className="p-3.5 rounded-xl bg-[#F87171]/10 border border-[#F87171]/30 text-xs text-[#F87171] font-sans flex items-center gap-2">
          <svg className="w-4 h-4 text-[#F87171] shrink-0" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <span className="font-sans">Research service not configured. No investigation or experiment has started.</span>
        </div>
      )}

      {/* Tab Controls: Research Results vs Report */}
      <div className="flex items-center justify-between border-b border-[#242424] pb-2 pt-1 font-sans">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setActiveTab('workspace')}
            className={`px-3 py-1.5 rounded text-xs font-medium font-sans transition-colors cursor-pointer ${
              activeTab === 'workspace'
                ? 'bg-[#141416] text-[#FF6500] font-semibold border-b-2 border-[#FF6500]'
                : 'text-[#8A8F98] hover:text-[#F4F4F6]'
            }`}
          >
            Research Results
          </button>
          {reportMd && (
            <button
              type="button"
              onClick={() => setActiveTab('report')}
              className={`px-3 py-1.5 rounded text-xs font-medium font-sans transition-colors flex items-center gap-1.5 cursor-pointer ${
                activeTab === 'report'
                  ? 'bg-[#141416] text-[#FF6500] font-semibold border-b-2 border-[#FF6500]'
                  : 'text-[#8A8F98] hover:text-[#F4F4F6]'
              }`}
            >
              <span>📄 Report</span>
            </button>
          )}
        </div>

        {reportMd && onDownloadReport && (
          <button
            type="button"
            onClick={onDownloadReport}
            className="px-3 py-1 rounded bg-[#FF6500]/10 border border-[#FF6500]/30 text-[#FF6500] hover:bg-[#FF6500]/20 text-xs font-medium btn-transition flex items-center gap-1 cursor-pointer font-sans"
          >
            <span>↓ Markdown (.md)</span>
          </button>
        )}
      </div>

      {/* 3. Research Workspace Content */}
      {activeTab === 'workspace' && (
        <div className="space-y-4 font-sans">
          {/* Current Experiment Details & Metrics */}
          {currentExperiment ? (
            <div className="bg-[#0B0B0B] border border-[#242424] rounded-xl p-4 space-y-3 font-sans">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#242424] pb-2.5">
                <div>
                  <div className="text-xs text-[#8A8F98] font-sans flex items-center gap-2">
                    <span>Current Experiment</span>
                    <span className="font-mono text-[11px] text-[#8A8F98]">({currentExperiment.id || 'EXP-001'})</span>
                  </div>
                  <h3 className="text-base font-semibold text-[#F4F4F6] font-sans mt-0.5">
                    {currentExperiment.name || 'Baseline Model'}
                  </h3>
                </div>
                <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-[#141416] border border-[#242424] text-[#FF6500] font-sans">
                  {currentExperiment.status || 'Running'}
                </span>
              </div>

              {/* Experiment Specs Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 text-xs font-sans">
                <SpecBox label="Dataset" value={currentExperiment.dataset || 'Not specified'} />
                <SpecBox label="Validation" value={currentExperiment.validation || 'Stratified K-Fold'} />
                <SpecBox label="Configuration" value={currentExperiment.config || 'Standard parameters'} />
              </div>

              {/* Measured Metrics (Req §11: Instrument Sans semibold for values, regular/medium for labels) */}
              {currentExperiment.metrics && Object.keys(currentExperiment.metrics).length > 0 && (
                <div className="space-y-2 pt-1 font-sans">
                  <div className="text-xs font-medium text-[#8A8F98] font-sans">
                    Measured Metrics
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                    {Object.entries(currentExperiment.metrics).map(([k, v]) => (
                      <div key={k} className="p-3 rounded-lg bg-[#101012] border border-[#242424] text-center font-sans">
                        <div className="text-xs font-medium text-[#8A8F98] font-sans">{k}</div>
                        <div className="text-base font-semibold text-[#F4F4F6] font-sans mt-1">
                          {typeof v === 'number' ? v.toFixed(4) : String(v)}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Safe error details if applicable */}
              {currentExperiment.errorDetail && (
                <div className="p-3 rounded-lg bg-[#F87171]/10 border border-[#F87171]/30 text-xs font-sans text-[#F87171] break-words">
                  Error: {currentExperiment.errorDetail}
                </div>
              )}
            </div>
          ) : (
            <div className="bg-[#0B0B0B] border border-[#242424] rounded-xl p-6 text-center font-sans">
              <p className="text-xs text-[#8A8F98] italic font-sans">
                Research results will appear here as the investigation progresses.
              </p>
            </div>
          )}

          {/* Collapsible Experiment History Section */}
          <div className="bg-[#0B0B0B] border border-[#242424] rounded-xl p-4 space-y-2.5 font-sans">
            <button
              type="button"
              onClick={() => setHistoryOpen(!historyOpen)}
              className="w-full flex items-center justify-between text-xs font-semibold text-[#F4F4F6] font-sans cursor-pointer"
            >
              <span className="flex items-center gap-2">
                <span>Experiment History</span>
                <span className="text-xs font-normal text-[#8A8F98]">({experiments.length} runs)</span>
              </span>
              <span className="text-[#8A8F98] text-xs">{historyOpen ? '▲' : '▼'}</span>
            </button>

            {historyOpen && (
              <div className="pt-2.5 space-y-2 border-t border-[#242424] max-h-72 overflow-y-auto font-sans">
                {experiments.length === 0 ? (
                  <p className="text-xs text-[#8A8F98] italic text-center py-2 font-sans">
                    No past experiment runs recorded.
                  </p>
                ) : (
                  experiments.map((exp, idx) => {
                    const isExpanded = expandedExpId === (exp.id || idx);
                    return (
                      <div key={exp.id || idx} className="bg-[#101012] border border-[#242424] rounded-lg p-3 space-y-2 text-xs font-sans">
                        <div
                          onClick={() => toggleExpExpand(exp.id || idx)}
                          className="flex items-center justify-between cursor-pointer"
                        >
                          <div className="flex items-center gap-2 min-w-0 font-sans">
                            <span className="text-[#FF6500] font-mono font-medium">#{exp.id || idx + 1}</span>
                            <span className="text-[#F4F4F6] font-medium truncate font-sans">{exp.name || 'Experiment Run'}</span>
                          </div>
                          <div className="flex items-center gap-2 font-sans">
                            <span className="text-xs text-[#8A8F98]">{exp.status || 'DONE'}</span>
                            <span className="text-[#8A8F98] text-xs">{isExpanded ? 'Hide' : 'Details'}</span>
                          </div>
                        </div>

                        {/* Expandable Details */}
                        {isExpanded && (
                          <div className="pt-2 border-t border-[#242424] space-y-1.5 text-xs text-[#8A8F98] font-sans">
                            <div><span className="text-[#F4F4F6] font-medium">Dataset:</span> {exp.dataset || 'N/A'}</div>
                            <div><span className="text-[#F4F4F6] font-medium">Validation Strategy:</span> {exp.validation || 'N/A'}</div>
                            <div><span className="text-[#F4F4F6] font-medium">Configuration:</span> {exp.config || 'N/A'}</div>
                            {exp.metrics && (
                              <div>
                                <span className="text-[#F4F4F6] font-medium">Results:</span>{' '}
                                {Object.entries(exp.metrics).map(([mk, mv]) => `${mk.toUpperCase()}: ${mv}`).join(', ')}
                              </div>
                            )}
                            {exp.errorDetail && (
                              <div className="text-[#F87171]"><span className="text-[#F87171] font-medium">Error:</span> {exp.errorDetail}</div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* 4. Scientific Report Tab */}
      {activeTab === 'report' && reportMd && (
        <div className="bg-[#0B0B0B] border border-[#242424] rounded-xl p-4 sm:p-6 space-y-4 font-sans">
          <div className="flex items-center justify-between border-b border-[#242424] pb-3 font-sans">
            <h3 className="text-sm font-semibold text-[#F4F4F6] font-sans flex items-center gap-2">
              <span>📄</span> Scientific Research Report
            </h3>
            {onDownloadReport && (
              <button
                type="button"
                onClick={onDownloadReport}
                className="px-3.5 py-1.5 rounded-lg bg-[#FF6500] hover:bg-[#FF302A] text-white text-xs font-semibold btn-transition cursor-pointer font-sans"
              >
                Download Markdown (.md)
              </button>
            )}
          </div>

          <div className="bg-[#080808] border border-[#242424] rounded-xl p-5 text-sm text-[#F4F4F6] font-sans leading-relaxed whitespace-pre-wrap break-words overflow-wrap-anywhere">
            <ChatMarkdown content={reportMd} />
          </div>
        </div>
      )}
    </div>
  );
}

function SpecBox({ label, value }) {
  return (
    <div className="p-3 rounded-lg bg-[#101012] border border-[#242424] min-w-0 font-sans">
      <div className="text-xs font-medium text-[#8A8F98] font-sans truncate">{label}</div>
      <div className="text-xs font-medium text-[#F4F4F6] truncate mt-1 font-sans">{value}</div>
    </div>
  );
}
