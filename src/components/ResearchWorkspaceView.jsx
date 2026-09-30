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
      
      {/* 1. Current User Question & Routing Mode */}
      <div className="bg-[#0B0B0B] border border-[#242424] rounded p-3 space-y-1">
        <div className="flex items-center justify-between text-[11px] font-mono text-[#8A8F98]">
          <span className="uppercase tracking-wider font-semibold text-[#FF6500]">Research Question</span>
          <span className="px-2 py-0.5 rounded bg-[#141416] border border-[#242424] text-[10px]">
            {routingMode}
          </span>
        </div>
        <p className="text-xs sm:text-sm font-medium text-[#F4F4F6] break-words overflow-wrap-anywhere">
          {userQuestion}
        </p>
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
        <div className="p-3 rounded bg-[#F87171]/10 border border-[#F87171]/30 text-xs text-[#F87171] font-mono flex items-center gap-2">
          <svg className="w-4 h-4 text-[#F87171] shrink-0" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <span>Research service not configured. No investigation or experiment has started.</span>
        </div>
      )}

      {/* Tab Controls: Research Results vs Report */}
      <div className="flex items-center justify-between border-b border-[#242424] pb-2 pt-1">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setActiveTab('workspace')}
            className={`px-3 py-1.5 rounded text-xs font-mono transition-colors ${
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
              className={`px-3 py-1.5 rounded text-xs font-mono transition-colors flex items-center gap-1.5 ${
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
            className="px-2.5 py-1 rounded bg-[#FF6500]/10 border border-[#FF6500]/30 text-[#FF6500] hover:bg-[#FF6500]/20 text-[11px] font-mono btn-transition flex items-center gap-1 cursor-pointer"
          >
            <span>↓ Markdown (.md)</span>
          </button>
        )}
      </div>

      {/* 3. Research Workspace Content */}
      {activeTab === 'workspace' && (
        <div className="space-y-4">
          {/* Current Experiment Details & Metrics */}
          {currentExperiment ? (
            <div className="bg-[#0B0B0B] border border-[#242424] rounded p-3.5 space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#242424] pb-2">
                <div>
                  <div className="text-[10px] font-mono text-[#8A8F98] uppercase">
                    Current Experiment: {currentExperiment.id || 'EXP-001'}
                  </div>
                  <h3 className="text-sm font-semibold text-[#F4F4F6] font-mono">
                    {currentExperiment.name || 'Baseline Model'}
                  </h3>
                </div>
                <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-[#141416] border border-[#242424] text-[#FF6500]">
                  {currentExperiment.status || 'RUNNING'}
                </span>
              </div>

              {/* Experiment Specs Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs font-mono">
                <SpecBox label="Dataset" value={currentExperiment.dataset || 'Not specified'} />
                <SpecBox label="Validation" value={currentExperiment.validation || 'Stratified K-Fold'} />
                <SpecBox label="Configuration" value={currentExperiment.config || 'Standard parameters'} />
              </div>

              {/* Actual Measured Metrics */}
              {currentExperiment.metrics && Object.keys(currentExperiment.metrics).length > 0 && (
                <div className="space-y-1.5 pt-1">
                  <div className="text-[10px] font-mono uppercase tracking-wider text-[#8A8F98]">
                    Measured Metrics
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                    {Object.entries(currentExperiment.metrics).map(([k, v]) => (
                      <div key={k} className="p-2 rounded bg-[#101012] border border-[#242424] text-center">
                        <div className="text-[10px] font-mono uppercase text-[#8A8F98]">{k}</div>
                        <div className="text-sm font-mono font-bold text-[#F4F4F6]">
                          {typeof v === 'number' ? v.toFixed(4) : String(v)}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Safe error details if applicable */}
              {currentExperiment.errorDetail && (
                <div className="p-2.5 rounded bg-[#F87171]/10 border border-[#F87171]/30 text-xs font-mono text-[#F87171] break-words">
                  Error: {currentExperiment.errorDetail}
                </div>
              )}
            </div>
          ) : (
            <div className="bg-[#0B0B0B] border border-[#242424] rounded p-6 text-center">
              <p className="text-xs text-[#8A8F98] italic font-mono">
                Research results will appear here as the investigation progresses.
              </p>
            </div>
          )}

          {/* Collapsible Experiment History Section */}
          <div className="bg-[#0B0B0B] border border-[#242424] rounded p-3 space-y-2">
            <button
              type="button"
              onClick={() => setHistoryOpen(!historyOpen)}
              className="w-full flex items-center justify-between text-xs font-mono font-bold text-[#F4F4F6] uppercase cursor-pointer"
            >
              <span className="flex items-center gap-2">
                <span>Collapsible Experiment History</span>
                <span className="text-[10px] font-normal text-[#8A8F98]">({experiments.length} runs)</span>
              </span>
              <span className="text-[#8A8F98]">{historyOpen ? '▲' : '▼'}</span>
            </button>

            {historyOpen && (
              <div className="pt-2 space-y-2 border-t border-[#242424] max-h-72 overflow-y-auto">
                {experiments.length === 0 ? (
                  <p className="text-xs text-[#8A8F98] italic text-center py-2">
                    No past experiment runs recorded.
                  </p>
                ) : (
                  experiments.map((exp, idx) => {
                    const isExpanded = expandedExpId === (exp.id || idx);
                    return (
                      <div key={exp.id || idx} className="bg-[#101012] border border-[#242424] rounded p-2.5 space-y-2 text-xs font-mono">
                        <div
                          onClick={() => toggleExpExpand(exp.id || idx)}
                          className="flex items-center justify-between cursor-pointer"
                        >
                          <div className="flex items-center gap-2 min-w-0">
                            <span className="text-[#FF6500] font-bold">#{exp.id || idx + 1}</span>
                            <span className="text-[#F4F4F6] font-medium truncate">{exp.name || 'Experiment Run'}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-[10px] text-[#8A8F98]">{exp.status || 'DONE'}</span>
                            <span className="text-[#8A8F98] text-[10px]">{isExpanded ? 'Hide' : 'Details'}</span>
                          </div>
                        </div>

                        {/* Expandable Details */}
                        {isExpanded && (
                          <div className="pt-2 border-t border-[#242424] space-y-2 text-[11px] text-[#8A8F98]">
                            <div><span className="text-[#F4F4F6]">Dataset:</span> {exp.dataset || 'N/A'}</div>
                            <div><span className="text-[#F4F4F6]">Validation Strategy:</span> {exp.validation || 'N/A'}</div>
                            <div><span className="text-[#F4F4F6]">Configuration:</span> {exp.config || 'N/A'}</div>
                            {exp.metrics && (
                              <div>
                                <span className="text-[#F4F4F6]">Results:</span>{' '}
                                {Object.entries(exp.metrics).map(([mk, mv]) => `${mk.toUpperCase()}: ${mv}`).join(', ')}
                              </div>
                            )}
                            {exp.errorDetail && (
                              <div className="text-[#F87171]"><span className="text-[#F87171]">Error:</span> {exp.errorDetail}</div>
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
        <div className="bg-[#0B0B0B] border border-[#242424] rounded p-4 sm:p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-[#242424] pb-3">
            <h3 className="text-sm font-mono font-bold text-[#F4F4F6] uppercase flex items-center gap-2">
              <span>📄</span> Scientific Research Report
            </h3>
            {onDownloadReport && (
              <button
                type="button"
                onClick={onDownloadReport}
                className="px-3 py-1.5 rounded bg-[#FF6500] hover:bg-[#FF302A] text-white text-xs font-semibold btn-transition cursor-pointer"
              >
                Download Markdown (.md)
              </button>
            )}
          </div>

          <div className="bg-[#080808] border border-[#242424] rounded p-4 text-xs sm:text-sm text-[#F4F4F6] font-sans leading-relaxed whitespace-pre-wrap break-words overflow-wrap-anywhere">
            <ChatMarkdown content={reportMd} />
          </div>
        </div>
      )}
    </div>
  );
}

function SpecBox({ label, value }) {
  return (
    <div className="p-2 rounded bg-[#101012] border border-[#242424] min-w-0">
      <div className="text-[10px] font-mono text-[#8A8F98] uppercase truncate">{label}</div>
      <div className="text-xs font-mono text-[#F4F4F6] truncate mt-0.5">{value}</div>
    </div>
  );
}
