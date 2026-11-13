import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

/**
 * Transparent AI Activity Timeline.
 * Communicates what Atlas is genuinely doing without exposing private chain-of-thought.
 */
export default function ActivityTimeline({
  activities = [],
  isLoading = false,
  mode = 'normal', // 'normal' | 'deep'
}) {
  const [isExpanded, setIsExpanded] = useState(isLoading);

  if (!activities || activities.length === 0) {
    if (!isLoading) return null;
    return (
      <div className="flex items-center gap-2 py-1.5 px-3 rounded-lg bg-[var(--surface-alt)] text-xs text-[var(--text-secondary)] border border-[var(--border-subtle)] my-2 w-fit">
        <span className="inline-block h-2 w-2 rounded-full bg-[var(--accent-yellow)] animate-pulse" />
        <span>Thinking…</span>
      </div>
    );
  }

  // Identify latest or active step
  const activeStep = activities.find((a) => a.status === 'running') || activities[activities.length - 1];
  const completedCount = activities.filter((a) => a.status === 'completed').length;
  const isAllComplete = !isLoading && activities.every((a) => a.status === 'completed');

  return (
    <div className="my-2.5 w-full max-w-xl">
      {/* Compact Status Pill (Click to toggle timeline) */}
      <button
        type="button"
        onClick={() => setIsExpanded((prev) => !prev)}
        className="group flex items-center justify-between w-full max-w-md py-1.5 px-3 rounded-xl border border-[var(--border-subtle)] bg-[var(--surface-alt)] hover:bg-[var(--surface-hover)] transition-all text-xs"
        aria-expanded={isExpanded}
        aria-label="Toggle agent activity details"
      >
        <div className="flex items-center gap-2 min-w-0">
          {isLoading ? (
            <span className="inline-block h-2 w-2 rounded-full bg-[var(--accent-yellow)] animate-ping flex-shrink-0" />
          ) : isAllComplete ? (
            <svg className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <polyline points="20 6 9 17 4 12" />
            </svg>
          ) : (
            <span className="inline-block h-2 w-2 rounded-full bg-[var(--text-muted)] flex-shrink-0" />
          )}

          <span className="font-medium text-[var(--text-main)] truncate">
            {isLoading
              ? (typeof activeStep?.label === 'string' ? activeStep.label : (activeStep?.label ? JSON.stringify(activeStep.label) : 'Processing…'))
              : `${completedCount} operational step${completedCount === 1 ? '' : 's'} completed`}
          </span>

          {activeStep?.detail && isLoading && (
            <span className="text-[var(--text-muted)] truncate hidden sm:inline">
              — {typeof activeStep.detail === 'string' ? activeStep.detail : JSON.stringify(activeStep.detail)}
            </span>
          )}
        </div>

        <div className="flex items-center gap-1 text-[var(--text-muted)] group-hover:text-[var(--text-main)] transition-colors pl-2">
          <span className="text-[11px]">{isExpanded ? 'Hide' : 'Details'}</span>
          <svg
            className={`h-3.5 w-3.5 transform transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </div>
      </button>

      {/* Expanded Chronological Timeline */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
            className="overflow-hidden"
          >
            <div className="mt-2 pl-3 py-2 pr-2 border-l-2 border-[var(--border-subtle)] space-y-2.5 text-xs">
              {activities.map((act, idx) => {
                const isRunning = act.status === 'running';
                const isFailed = act.status === 'failed';
                const isComplete = act.status === 'completed';

                return (
                  <div key={act.id || idx} className="flex items-start gap-2.5">
                    {/* Status Glyph */}
                    <div className="pt-0.5 flex-shrink-0">
                      {isRunning ? (
                        <div className="h-3.5 w-3.5 rounded-full border-2 border-[var(--accent-amber)] border-t-transparent animate-spin" />
                      ) : isFailed ? (
                        <svg className="h-3.5 w-3.5 text-rose-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                          <line x1="18" y1="6" x2="6" y2="18" />
                          <line x1="6" y1="6" x2="18" y2="18" />
                        </svg>
                      ) : (
                        <svg className="h-3.5 w-3.5 text-emerald-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                          <polyline points="20 6 9 17 4 12" />
                        </svg>
                      )}
                    </div>

                    {/* Step Content */}
                    <div className="min-w-0 flex-1">
                      <div className="flex items-baseline justify-between gap-2">
                        <span className={`font-medium ${isRunning ? 'text-[var(--text-main)] font-semibold' : isFailed ? 'text-rose-500' : 'text-[var(--text-body)]'}`}>
                          {typeof act.label === 'string' ? act.label : JSON.stringify(act.label || '')}
                        </span>
                        {act.timestamp && (
                          <span className="text-[10px] text-[var(--text-muted)] flex-shrink-0">
                            {typeof act.timestamp === 'number'
                              ? new Date(act.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
                              : String(act.timestamp)}
                          </span>
                        )}
                      </div>

                      {act.detail && act.detail !== act.label && (
                        <p className="text-[11px] text-[var(--text-muted)] mt-0.5 break-words">
                          {typeof act.detail === 'string' ? act.detail : JSON.stringify(act.detail)}
                        </p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
