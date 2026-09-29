import React from 'react';

// Error-analysis panel (brief §9 "Error Analysis" and the diagnostics that drive
// the next hypothesis). Renders the real failure-mode breakdown: false
// positives/negatives, the autonomous diagnosis, top failing features,
// slice-level performance, and the bootstrap confidence interval.

export default function ErrorAnalysisPanel({ analysis, stageState }) {
  if (!analysis) {
    const msg =
      stageState === 'RUNNING'
        ? 'Running error diagnostics and slice analysis…'
        : stageState === 'FAILED'
          ? 'Error analysis failed for this run.'
          : 'Error analysis has not been executed yet.';
    return (
      <div className="bg-[#121722] border border-[#1E293B] rounded-2xl p-6 text-center">
        <p className="text-xs text-slate-500 italic">{msg}</p>
      </div>
    );
  }

  const { falsePositivesCount, falseNegativesCount, topFailingFeatures, sliceAnalysis, bootstrapCI, failureDiagnosis } = analysis;

  return (
    <div className="space-y-4 min-w-0">
      <div className="grid grid-cols-2 gap-3">
        <Count label="False positives" value={falsePositivesCount} tone="amber" hint="predicted positive, actually negative" />
        <Count label="False negatives" value={falseNegativesCount} tone="rose" hint="missed actual positives" />
      </div>

      {failureDiagnosis && (
        <div className="bg-amber-500/5 border border-amber-500/30 rounded-2xl p-4 min-w-0">
          <h4 className="text-[10px] font-bold uppercase tracking-wider text-amber-400 mb-2">Why did the model fail?</h4>
          <p className="text-xs text-amber-100/90 leading-relaxed break-words overflow-wrap-anywhere">{failureDiagnosis}</p>
        </div>
      )}

      {bootstrapCI && (
        <div className="bg-[#121722] border border-[#1E293B] rounded-2xl p-4 min-w-0">
          <h4 className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-2">Statistical confidence (bootstrap)</h4>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-300">
            {bootstrapCI.mean != null && <span>Mean: <b className="font-mono text-cyan-400">{bootstrapCI.mean}</b></span>}
            <span>
              95% CI: <b className="font-mono text-cyan-400">[{bootstrapCI.ci_lower} – {bootstrapCI.ci_upper}]</b>
            </span>
          </div>
        </div>
      )}

      {Array.isArray(topFailingFeatures) && topFailingFeatures.length > 0 && (
        <div className="bg-[#121722] border border-[#1E293B] rounded-2xl p-4 min-w-0">
          <h4 className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-3">Top failing features</h4>
          <div className="space-y-2 min-w-0">
            {topFailingFeatures.map((f, i) => (
              <div key={i} className="flex items-start gap-3 min-w-0">
                <span className="shrink-0 text-[10px] font-mono font-bold text-amber-400 bg-[#0B0F17] border border-[#212B3B] rounded px-2 py-0.5">
                  {f.importanceScore}
                </span>
                <div className="min-w-0">
                  <span className="text-[11px] font-semibold text-slate-200 break-all">{f.feature}</span>
                  {f.message && <p className="text-[11px] text-slate-500 leading-relaxed break-words overflow-wrap-anywhere">{f.message}</p>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {Array.isArray(sliceAnalysis) && sliceAnalysis.length > 0 && (
        <div className="bg-[#121722] border border-[#1E293B] rounded-2xl p-4 min-w-0">
          <h4 className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-3">Slice-level performance</h4>
          <div className="space-y-2 min-w-0">
            {sliceAnalysis.map((s, i) => (
              <div key={i} className="p-3 rounded-xl bg-[#0B0F17] border border-[#1E293B] min-w-0">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-[11px] font-semibold text-slate-200 break-words overflow-wrap-anywhere">{s.slice}</span>
                  {s.recall != null && (
                    <span className="shrink-0 text-[10px] font-mono text-emerald-400 bg-[#0D111A] border border-[#212B3B] rounded px-2 py-0.5">
                      recall {s.recall}
                    </span>
                  )}
                </div>
                {s.note && <p className="text-[11px] text-slate-500 mt-1 break-words overflow-wrap-anywhere">{s.note}</p>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function Count({ label, value, tone, hint }) {
  const color = tone === 'rose' ? 'text-rose-400' : tone === 'amber' ? 'text-amber-400' : 'text-slate-100';
  return (
    <div className="bg-[#121722] border border-[#1E293B] rounded-2xl p-4 min-w-0">
      <div className="text-[10px] text-slate-500 uppercase tracking-wide truncate" title={label}>{label}</div>
      <div className={`text-3xl font-bold font-mono ${color}`}>{value ?? '—'}</div>
      {hint && <div className="text-[10px] text-slate-600 mt-1 break-words">{hint}</div>}
    </div>
  );
}
