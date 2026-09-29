import React from 'react';

// Hypothesis panel (brief §8): CURRENT FINDING → HYPOTHESIS → NEXT EXPERIMENT,
// wired to the real research engine state. The finding comes from the actual
// error-analysis diagnosis; the hypothesis is the latest one the orchestrator
// generated; "next experiment" reflects the real loop position. No fabricated
// results — when a piece is not available yet it says so honestly.

export default function HypothesisPanel({ model, project, onResume, canResume }) {
  const { errorAnalysis, expNodes, loopExhausted, experimentsCount, maxExperiments, status } = model;
  const latest = expNodes.length ? expNodes[expNodes.length - 1] : null;
  const running = status === 'RUNNING' || status === 'IN_PROGRESS' || status === 'QUEUED';

  const finding = errorAnalysis?.failureDiagnosis || null;
  const hypothesis = latest?.hypothesis || null;

  let nextLabel = 'Waiting for the first experiment…';
  let nextTone = 'text-slate-500';
  if (loopExhausted) {
    nextLabel = `Research loop complete — ${experimentsCount} experiment${experimentsCount === 1 ? '' : 's'} executed.`;
    nextTone = 'text-emerald-400';
  } else if (running) {
    nextLabel = `Experiment ${experimentsCount + 1} of ${maxExperiments} — running autonomously…`;
    nextTone = 'text-cyan-400';
  } else if (latest) {
    nextLabel = `Next: experiment ${experimentsCount + 1} of ${maxExperiments}.`;
    nextTone = 'text-slate-300';
  }

  return (
    <div className="bg-[#121722] border border-[#1E293B] rounded-2xl p-4 sm:p-5 space-y-4 min-w-0">
      <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 border-b border-[#1E293B]/70 pb-3">
        Hypothesis &amp; Next Step
      </h3>

      <Block label="Current finding" tone="amber">
        {finding ? (
          <p className="text-xs text-slate-300 leading-relaxed break-words overflow-wrap-anywhere">{finding}</p>
        ) : (
          <p className="text-xs text-slate-500 italic">
            {errorAnalysis ? 'No failure diagnosis recorded.' : 'Waiting for error analysis…'}
          </p>
        )}
      </Block>

      <Block label="Hypothesis" tone="purple">
        {hypothesis ? (
          <p className="text-xs text-slate-300 leading-relaxed italic break-words overflow-wrap-anywhere">“{hypothesis}”</p>
        ) : (
          <p className="text-xs text-slate-500 italic">Waiting for the first experiment to be designed…</p>
        )}
      </Block>

      <Block label="Next experiment" tone="cyan">
        <p className={`text-xs leading-relaxed ${nextTone}`}>{nextLabel}</p>
        {latest && (
          <p className="text-[11px] text-slate-500 mt-1 break-words overflow-wrap-anywhere">
            Most recent: {latest.title} · {latest.metricName || 'score'} {typeof latest.metricValue === 'number' ? Number(latest.metricValue.toFixed(4)) : latest.metricValue}
          </p>
        )}
      </Block>

      {/* The research loop is autonomous; the only real user action mid-run is
          pause/stop (header) or resume a paused/interrupted run. We never render
          a "Run Experiment" button that isn't wired to the engine. */}
      {canResume && onResume && (
        <button
          onClick={onResume}
          className="w-full sm:w-auto px-4 py-2 min-h-[38px] rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs shadow-md transition-colors cursor-pointer"
        >
          ▶ Resume research
        </button>
      )}
    </div>
  );
}

const TONE = {
  amber: 'border-amber-500/30 bg-amber-500/5',
  purple: 'border-purple-500/30 bg-purple-500/5',
  cyan: 'border-cyan-500/30 bg-cyan-500/5',
};

function Block({ label, tone = 'cyan', children }) {
  return (
    <div className={`rounded-xl border p-3 min-w-0 ${TONE[tone] || TONE.cyan}`}>
      <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">{label}</div>
      {children}
    </div>
  );
}
