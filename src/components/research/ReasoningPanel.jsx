import React, { useEffect, useRef, useState } from 'react';

// "Research Reasoning" panel (brief §4): a concise, user-safe narrative of what
// the system is currently doing, built ONLY from real agentLogs the orchestrator
// emitted. No hidden chain-of-thought is exposed — these are the same short
// status/decision lines the backend already produces.

const STATUS_DOT = {
  COMPLETED: 'bg-emerald-400',
  IN_PROGRESS: 'bg-cyan-400',
  RUNNING: 'bg-cyan-400',
  WARNING: 'bg-amber-400',
  FAILED: 'bg-rose-400',
  STOPPED: 'bg-slate-400',
};

// Friendly labels for the backend agent identifiers.
const AGENT_LABEL = {
  RESEARCH_AGENT: 'Research',
  RESEARCH_ORCHESTRATOR: 'Orchestrator',
  DATASET_AGENT: 'Dataset',
  BASELINE_AGENT: 'Baseline',
  HYPOTHESIS_AGENT: 'Hypothesis',
  CRITIC_AGENT: 'Peer Critic',
  CODING_AGENT: 'Coding',
  EXECUTION_MANAGER: 'Execution',
  ERROR_ANALYSIS_AGENT: 'Error Analysis',
  REPORT_AGENT: 'Report',
};

function timeOf(ts) {
  if (!ts) return '';
  try {
    return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch {
    return '';
  }
}

export default function ReasoningPanel({ logs = [], running = false, limit = 40 }) {
  const [expanded, setExpanded] = useState(false);
  const scrollRef = useRef(null);

  const recent = (logs || []).slice(-limit);
  const visible = expanded ? recent : recent.slice(-6);

  useEffect(() => {
    if (scrollRef.current && expanded) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [recent.length, expanded]);

  return (
    <div className="bg-[#121722] border border-[#1E293B] rounded-2xl p-4 sm:p-5">
      <div className="flex items-center justify-between border-b border-[#1E293B]/70 pb-3 mb-3">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
          <span className={running ? 'w-2 h-2 rounded-full bg-cyan-400 animate-ping' : 'w-2 h-2 rounded-full bg-slate-600'} />
          Research Reasoning
        </h3>
        <span className="text-[10px] text-slate-500 font-mono">{(logs || []).length} steps</span>
      </div>

      {visible.length === 0 ? (
        <p className="text-[11px] text-slate-500 italic">
          {running ? 'Preparing the study…' : 'No research activity yet.'}
        </p>
      ) : (
        <div
          ref={scrollRef}
          className={`space-y-2.5 min-w-0 ${expanded ? 'max-h-72 overflow-y-auto overscroll-contain pr-1' : ''}`}
        >
          {visible.map((log, i) => (
            <div key={i} className="flex gap-2.5 min-w-0">
              <span
                className={`mt-1.5 shrink-0 w-1.5 h-1.5 rounded-full ${STATUS_DOT[log.status] || 'bg-slate-500'}`}
                aria-hidden="true"
              />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-[10px] font-semibold uppercase tracking-wide text-cyan-400/90">
                    {AGENT_LABEL[log.agent] || log.agent || 'Agent'}
                  </span>
                  <span className="text-[9px] font-mono text-slate-600">{timeOf(log.timestamp)}</span>
                </div>
                <p className="text-[11px] text-slate-300 leading-relaxed break-words overflow-wrap-anywhere">
                  {log.message}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}

      {(logs || []).length > 6 && (
        <button
          onClick={() => setExpanded((v) => !v)}
          className="mt-3 text-[11px] font-medium text-cyan-400 hover:text-cyan-300 transition-colors cursor-pointer"
        >
          {expanded ? 'Show less' : `Show all ${Math.min((logs || []).length, limit)} reasoning steps`}
        </button>
      )}
    </div>
  );
}
