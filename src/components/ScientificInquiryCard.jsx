import React from 'react';

/**
 * Scientific Inquiry Card:
 * Signature visual element.
 * Dark bordered card with narrow crimson accent along left edge (#DF223A),
 * small orange technical icon, compact heading reflecting actual session state.
 * Includes all 13 required stages with status symbols (✓, ●, ○, ✕).
 * Compact 2-column on desktop, single-column on mobile.
 */
export default function ScientificInquiryCard({
  sessionState = 'IDLE', // 'QUEUED' | 'IN_PROGRESS' | 'COMPLETE' | 'FAILED' | 'CANCELLED' | 'IDLE'
  stageEvents = [], // [{ stageIndex: 1-13, status: 'completed'|'running'|'pending'|'failed', detail: '...', timestamp: '...' }]
  onRetry,
  canRetry = false,
}) {
  // Heading based strictly on actual session state, in normal title case (Instrument Sans)
  const headingMap = {
    QUEUED: 'Investigation Queued',
    IN_PROGRESS: 'Research Investigation in Progress',
    COMPLETE: 'Investigation Complete',
    FAILED: 'Investigation Interrupted',
    CANCELLED: 'Investigation Cancelled',
    IDLE: 'Autonomous Research Pipeline',
  };

  const headingText = headingMap[sessionState] || 'Autonomous Research Pipeline';

  // 13 Required Stages (1-indexed)
  const STAGES = [
    { id: 1, name: 'Understanding the research question' },
    { id: 2, name: 'Planning the investigation' },
    { id: 3, name: 'Searching the literature' },
    { id: 4, name: 'Evaluating sources' },
    { id: 5, name: 'Finding datasets' },
    { id: 6, name: 'Establishing baseline' },
    { id: 7, name: 'Designing experiment' },
    { id: 8, name: 'Executing experiment' },
    { id: 9, name: 'Analyzing findings' },
    { id: 10, name: 'Error analysis' },
    { id: 11, name: 'Testing competing explanations' },
    { id: 12, name: 'Next experiment' },
    { id: 13, name: 'Preparing research report' },
  ];

  // Map events to stage indices
  const eventsByStage = {};
  stageEvents.forEach((evt) => {
    if (evt.stageIndex) {
      eventsByStage[evt.stageIndex] = evt;
    }
  });

  const getStageState = (stageId) => {
    const evt = eventsByStage[stageId];
    if (evt) {
      return {
        status: evt.status, // 'completed' | 'running' | 'failed' | 'pending'
        detail: evt.detail,
        timestamp: evt.timestamp,
      };
    }
    if (sessionState === 'IDLE') return { status: 'pending' };
    return { status: 'pending' };
  };

  const renderStatusSymbol = (status) => {
    switch (status) {
      case 'completed':
        return <span className="text-emerald-400 font-bold">✓</span>;
      case 'running':
        return <span className="text-[#F15A3A] font-bold animate-running-pulse">●</span>;
      case 'failed':
        return <span className="text-[#F87171] font-bold">✕</span>;
      case 'pending':
      default:
        return <span className="text-[#8A8884]">○</span>;
    }
  };

  return (
    <div className="bg-[#181818] border border-[#303030] border-l-4 border-l-[#DF223A] rounded p-3.5 sm:p-4 shadow-sm animate-panel-entrance select-none font-sans">
      {/* Card Header */}
      <div className="flex items-center justify-between gap-3 border-b border-[#303030] pb-2.5 mb-3">
        <div className="flex items-center gap-2 min-w-0">
          {/* Small orange icon */}
          <div className="w-5 h-5 rounded bg-[#F15A3A]/10 border border-[#F15A3A]/30 flex items-center justify-center shrink-0">
            <svg className="w-3 h-3 text-[#F15A3A]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
              <circle cx="12" cy="12" r="3" />
              <path d="M12 2v3M12 19v3M2 12h3M19 12h3" />
            </svg>
          </div>
          <h2 className="text-xs sm:text-sm font-semibold tracking-normal text-[#E8E5DF] truncate font-sans">
            {headingText}
          </h2>
        </div>

        {/* Retry button only when a real retry operation exists */}
        {sessionState === 'FAILED' && canRetry && onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="px-2.5 py-1 rounded bg-[#E44D31]/10 border border-[#E44D31]/40 text-[#F87171] text-[11px] font-medium hover:bg-[#E44D31]/20 btn-transition cursor-pointer font-sans"
          >
            ↻ Retry Stage
          </button>
        )}
      </div>

      {/* 13 Stages List (Desktop: 2-column, Mobile: 1-column) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-2 text-xs font-sans">
        {STAGES.map((stage) => {
          const { status, detail, timestamp } = getStageState(stage.id);
          return (
            <div key={stage.id} className="flex flex-col min-w-0 py-0.5">
              <div className="flex items-center gap-2 min-w-0">
                <span className="w-4 text-center shrink-0 text-xs font-sans">
                  {renderStatusSymbol(status)}
                </span>
                <span className="text-[#8A8884] text-[11px] shrink-0 font-mono w-5">
                  {String(stage.id).padStart(2, '0')}.
                </span>
                <span className={`truncate text-xs font-sans ${
                  status === 'completed' ? 'text-[#E8E5DF] font-medium' :
                  status === 'running' ? 'text-[#F15A3A] font-medium' :
                  status === 'failed' ? 'text-[#F87171] font-medium' : 'text-[#8A8884] font-normal'
                }`}>
                  {stage.name}
                </span>
              </div>

              {/* Event detail and timestamp if supplied */}
              {(detail || timestamp) && (status === 'completed' || status === 'running' || status === 'failed') && (
                <div className="ml-11 mt-0.5 text-[11px] text-[#8A8884] font-sans leading-tight break-words overflow-wrap-anywhere">
                  {detail}
                  {timestamp && <span className="ml-1.5 text-[10px] font-mono opacity-70">[{timestamp}]</span>}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
