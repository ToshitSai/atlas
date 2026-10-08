import React, { useEffect, useMemo, useState } from 'react';
import AtlasLogo from './AtlasLogo';

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

  const headingText = (() => {
    const base = headingMap[sessionState] || 'Autonomous Research Pipeline';
    // A "Complete" header must never contradict the step list: if any stage was
    // explicitly skipped as not applicable, say so honestly.
    if (sessionState === 'COMPLETE' && stageEvents.some((e) => e.status === 'skipped')) {
      return 'Completed with Limited Scope';
    }
    return base;
  })();
  const activeEvent = [...stageEvents].reverse().find((event) => event.status === 'running') || stageEvents[stageEvents.length - 1];
  const liveStatus = activeEvent?.detail || (sessionState === 'COMPLETE' ? 'Research complete' : 'Waiting for research activity');

  const [startedAt, setStartedAt] = useState(null);
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    if (sessionState === 'IN_PROGRESS' || sessionState === 'QUEUED') setStartedAt((value) => value || Date.now());
    if (sessionState === 'IDLE') setStartedAt(null);
  }, [sessionState]);
  useEffect(() => {
    if (!startedAt || sessionState !== 'IN_PROGRESS') return undefined;
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [startedAt, sessionState]);

  const liveSteps = useMemo(() => stageEvents.filter((event) => event && event.stage), [stageEvents]);

  const renderStatusSymbol = (status) => {
    switch (status) {
      case 'completed':
        return <span className="status-check" aria-label="Completed" />;
      case 'running':
        return <span className="inline-block w-3.5 h-3.5 rounded-full border-2 border-[var(--accent)] border-t-transparent animate-spin" aria-label="In progress" />;
      case 'failed':
        return <span className="status-warning" aria-label="Failed" />;
      case 'skipped':
        return <span className="text-[var(--text-muted)]" title="Skipped">Skipped</span>;
      case 'pending':
      default:
        return <span className="inline-block w-2 h-2 rounded-full bg-[var(--text-muted)]" aria-label="Pending" />;
    }
  };

  return (
    <div className="bg-[var(--surface)] border border-[var(--border-subtle)] border-l-4 border-l-[#DF223A] rounded p-3.5 sm:p-4 shadow-sm animate-panel-entrance select-none font-sans text-[var(--text-body)]">
      {/* Card Header */}
      <div className="flex items-center justify-between gap-3 border-b border-[var(--border-subtle)] pb-2.5 mb-3">
        <div className="flex items-center gap-2 min-w-0">
          {/* Small orange icon */}
          <div className={`w-7 h-7 rounded-lg bg-[var(--accent-yellow)] flex items-center justify-center shrink-0 ${sessionState === 'IN_PROGRESS' ? 'animate-running-pulse' : ''}`}>
            <AtlasLogo className="w-4 h-4" />
          </div>
          <div className="min-w-0" aria-live="polite">
            <h2 className="text-xs sm:text-sm font-semibold tracking-normal text-[var(--text-main)] truncate font-sans">{headingText}</h2>
            <p className="text-[11px] text-[var(--text-secondary)] truncate" aria-live="polite">{liveStatus}{startedAt ? ` · ${Math.max(0, Math.floor((now - startedAt) / 1000))}s` : ''}</p>
          </div>
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

      {/* Only stages emitted by the backend are shown. */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-2 text-xs font-sans">
        {liveSteps.map((stage, index) => {
          const { status, detail, timestamp } = stage;
          return (
            <div key={stage.id} className="flex flex-col min-w-0 py-0.5">
              <div className="flex items-center gap-2 min-w-0">
                <span className="w-4 text-center shrink-0 text-xs font-sans">
                  {renderStatusSymbol(status)}
                </span>
                <span className="text-[var(--text-muted)] text-[11px] shrink-0 font-mono w-5">
                  {String(index + 1).padStart(2, '0')}.
                </span>
                <span className={`truncate text-xs font-sans ${
                  status === 'completed' ? 'text-[var(--text-main)] font-medium' :
                  status === 'running' ? 'text-[var(--accent)] font-medium' :
                  status === 'failed' ? 'text-[var(--danger)] font-medium' :
                  status === 'skipped' ? 'text-[var(--text-muted)] font-normal' : 'text-[var(--text-secondary)] font-normal'
                }`}>
                  {stage.label || stage.name || stage.stage}
                </span>
              </div>

              {/* Event detail and timestamp if supplied */}
              {(detail || timestamp) && (status === 'completed' || status === 'running' || status === 'failed' || status === 'skipped') && (
                <div className="ml-11 mt-0.5 text-[11px] text-[var(--text-muted)] font-sans leading-tight break-words overflow-wrap-anywhere">
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
