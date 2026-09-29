import React from 'react';
import { statusTone, experimentLabel, formatMetricValue } from './format';

// Results + research memory (brief §7 and the "experiment comparison" UX goal).
// Shows the real baseline-vs-experiments comparison and the running research
// history the engine uses to decide what to try next. Every number is a stored
// result; clicking a row opens the full experiment record.

export default function ResultsPanel({ model, onSelect }) {
  const { rootNode, expNodes, bestExp, bestBaseline, completedBaselines } = model;
  const allNodes = [rootNode, ...expNodes].filter(Boolean);

  if (!allNodes.length) {
    return (
      <div className="bg-[#121722] border border-[#1E293B] rounded-2xl p-6 text-center">
        <p className="text-xs text-slate-500 italic">
          {completedBaselines.length ? 'Loading results…' : 'No results yet — waiting for the first models to finish training.'}
        </p>
      </div>
    );
  }

  const metricName = rootNode?.metricName || bestExp?.metricName || 'score';
  const baseVal = typeof rootNode?.metricValue === 'number' ? rootNode.metricValue : null;
  const bestVal = typeof bestExp?.metricValue === 'number' ? bestExp.metricValue : null;
  const improved = baseVal != null && bestVal != null && bestVal > baseVal;
  const delta = baseVal != null && bestVal != null ? Number((bestVal - baseVal).toFixed(4)) : null;

  return (
    <div className="space-y-4 min-w-0">
      {/* Headline result */}
      <div className="bg-[#121722] border border-[#1E293B] rounded-2xl p-4 sm:p-5 min-w-0">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 border-b border-[#1E293B]/70 pb-3 mb-4">
          Results
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <Stat
            label={`Baseline (${rootNode?.model || bestBaseline?.name || '—'})`}
            value={baseVal != null ? Number(baseVal.toFixed(4)) : '—'}
            unit={metricName}
          />
          <Stat
            label={`Best experiment${bestExp ? ` (${bestExp.title})` : ''}`}
            value={bestVal != null ? Number(bestVal.toFixed(4)) : '—'}
            unit={metricName}
            tone={improved ? 'emerald' : 'slate'}
          />
          <Stat
            label="Improvement"
            value={delta != null ? `${delta > 0 ? '+' : ''}${delta}` : '—'}
            unit={delta != null ? metricName : ''}
            tone={improved ? 'emerald' : delta != null ? 'amber' : 'slate'}
          />
        </div>
        <p className="text-[11px] text-slate-500 mt-3 leading-relaxed break-words overflow-wrap-anywhere">
          {improved
            ? `The best approach improved ${metricName} over the baseline.`
            : bestVal != null
              ? `No experiment beat the baseline on ${metricName}; the baseline stands as the strongest model.`
              : 'Waiting for experiment results.'}
        </p>
      </div>

      {/* Research history / memory */}
      <div className="bg-[#121722] border border-[#1E293B] rounded-2xl p-4 sm:p-5 min-w-0">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 border-b border-[#1E293B]/70 pb-3 mb-3">
          Research History
        </h3>
        <div className="flex flex-wrap gap-2">
          {allNodes.map((n, i) => {
            const tone = statusTone(n.status);
            return (
              <button
                key={n.id}
                onClick={() => onSelect && onSelect(n, i)}
                className="px-2.5 py-1.5 rounded-lg bg-[#0B0F17] border border-[#212B3B] hover:border-cyan-500/40 transition-colors cursor-pointer text-left min-w-0"
                title={n.title}
              >
                <span className="text-[10px] font-mono text-slate-500">{experimentLabel(n, i)}</span>
                <span className={`ml-2 text-[11px] font-mono font-bold ${tone.text}`}>
                  {n.metricName || metricName}: {typeof n.metricValue === 'number' ? Number(n.metricValue.toFixed(4)) : n.metricValue}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Comparison table */}
      <div className="bg-[#121722] border border-[#1E293B] rounded-2xl p-4 sm:p-5 min-w-0">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 border-b border-[#1E293B]/70 pb-3 mb-3">
          Experiment Comparison
        </h3>
        <div className="table-responsive">
          <table className="w-full text-[11px] border-collapse min-w-[520px]">
            <thead>
              <tr className="text-slate-500 uppercase text-[9px] tracking-wider">
                <th className="text-left font-semibold py-2 pr-3">Experiment</th>
                <th className="text-left font-semibold py-2 pr-3">Model</th>
                <th className="text-left font-semibold py-2 pr-3">Validation</th>
                <th className="text-right font-semibold py-2 pr-3">{metricName}</th>
                <th className="text-left font-semibold py-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {allNodes.map((n, i) => {
                const tone = statusTone(n.status);
                const isBest = bestExp && n.id === bestExp.id;
                return (
                  <tr
                    key={n.id}
                    onClick={() => onSelect && onSelect(n, i)}
                    className="border-t border-[#1E293B] hover:bg-[#0F1420] cursor-pointer transition-colors"
                  >
                    <td className="py-2 pr-3">
                      <span className="font-mono text-slate-400">{experimentLabel(n, i)}</span>
                      <span className="block text-slate-300 truncate max-w-[180px]" title={n.title}>{n.title}</span>
                    </td>
                    <td className="py-2 pr-3 text-slate-300 max-w-[140px] truncate" title={n.model}>{n.model || '—'}</td>
                    <td className="py-2 pr-3 text-slate-500 max-w-[140px] truncate" title={n.splitStrategy}>{n.splitStrategy || '—'}</td>
                    <td className={`py-2 pr-3 text-right font-mono font-bold ${isBest ? 'text-emerald-400' : 'text-slate-200'}`}>
                      {typeof n.metricValue === 'number' ? Number(n.metricValue.toFixed(4)) : n.metricValue ?? '—'}
                    </td>
                    <td className="py-2">
                      <span className={`inline-flex items-center gap-1.5 ${tone.text}`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${tone.dot}`} />
                        {n.status}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value, unit, tone = 'slate' }) {
  const color = tone === 'emerald' ? 'text-emerald-400' : tone === 'amber' ? 'text-amber-400' : 'text-slate-100';
  return (
    <div className="p-3 rounded-xl bg-[#0B0F17] border border-[#212B3B] min-w-0">
      <div className="text-[10px] text-slate-500 truncate" title={label}>{label}</div>
      <div className={`text-xl font-bold font-mono ${color} truncate`}>
        {value}
        {unit && <span className="text-[10px] text-slate-500 ml-1 font-sans">{unit}</span>}
      </div>
    </div>
  );
}
