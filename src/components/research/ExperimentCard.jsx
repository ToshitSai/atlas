import React from 'react';
import { orderedMetrics, formatMetricValue, metricLabel, statusTone, experimentLabel } from './format';

// Experiment card (brief §5). Renders one real experiment/baseline tree node:
// model, dataset, validation strategy, key metrics, status, runtime, and
// [View Details] / [View Logs] actions. Failed experiments show the real status
// (never a success-looking card) — see statusTone + the failure note below.

export default function ExperimentCard({ node, index, onViewDetails, onViewLogs }) {
  if (!node) return null;
  const isBaseline = node.parentId === null;
  const tone = statusTone(node.status);
  const metrics = orderedMetrics(node.allMetrics || {});
  const topMetrics = metrics.slice(0, 4);
  const failed = String(node.status).toUpperCase() === 'FAILED';
  const hasLogs = Boolean(node.stdout || node.stderr);

  return (
    <div
      className={`rounded-2xl border p-4 space-y-3 min-w-0 transition-colors ${
        isBaseline ? 'bg-[#0D1A20] border-cyan-500/30' : failed ? 'bg-[#160F12] border-rose-500/30' : 'bg-[#121722] border-[#1E293B]'
      }`}
    >
      <div className="flex items-start justify-between gap-3 min-w-0">
        <div className="min-w-0 space-y-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${isBaseline ? 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30' : 'bg-[#0B0F17] text-slate-400 border-[#212B3B]'}`}>
              {experimentLabel(node, index)}
            </span>
            <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${tone.chip}`}>
              {node.status || 'UNKNOWN'}
            </span>
          </div>
          <h4 className="text-sm font-semibold text-slate-100 leading-snug break-words overflow-wrap-anywhere">
            {node.title || (isBaseline ? 'Baseline model' : 'Experiment')}
          </h4>
        </div>
        {node.metricValue != null && (
          <div className="shrink-0 text-right">
            <div className="text-[10px] text-slate-500 font-mono uppercase">{node.metricName || 'score'}</div>
            <div className={`text-lg font-bold font-mono ${failed ? 'text-rose-400' : 'text-emerald-400'}`}>
              {typeof node.metricValue === 'number' ? Number(node.metricValue.toFixed(4)) : node.metricValue}
            </div>
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px] min-w-0">
        <Field label="Model" value={node.model || (isBaseline ? node.title : '—')} />
        <Field label="Dataset" value={node.dataset || '—'} />
        <Field label="Validation" value={node.splitStrategy || '—'} />
        <Field label="Runtime" value={node.executionTime || '—'} />
      </div>

      {topMetrics.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {topMetrics.map(([k, v]) => (
            <div key={k} className="p-2 rounded-lg bg-[#0B0F17] border border-[#212B3B] min-w-0">
              <div className="text-[9px] text-slate-500 uppercase truncate" title={metricLabel(k)}>{metricLabel(k)}</div>
              <div className="text-xs font-bold text-slate-100 font-mono">{formatMetricValue(k, v)}</div>
            </div>
          ))}
        </div>
      )}

      {failed && (
        <p className="text-[11px] text-rose-300/90 break-words overflow-wrap-anywhere">
          {node.conclusion || 'Experiment failed to run. Open logs for the actual error.'}
        </p>
      )}

      <div className="flex flex-wrap items-center gap-2 pt-1">
        <button
          onClick={() => onViewDetails && onViewDetails(node)}
          className="px-3 py-1.5 min-h-[34px] rounded-lg bg-[#1A2232] hover:bg-[#253147] text-slate-200 border border-[#2B364A] text-[11px] font-semibold transition-colors cursor-pointer"
        >
          View Details
        </button>
        <button
          onClick={() => onViewLogs && onViewLogs(node)}
          disabled={!hasLogs}
          className={`px-3 py-1.5 min-h-[34px] rounded-lg text-[11px] font-semibold transition-colors border ${
            hasLogs
              ? 'bg-[#131822] hover:bg-[#1C2536] text-slate-300 border-[#212B3B] cursor-pointer'
              : 'bg-[#0F1420] text-slate-600 border-[#1E293B] cursor-not-allowed'
          }`}
        >
          View Logs
        </button>
        {node.sandboxMode && (
          <span className="text-[10px] text-slate-500 font-mono ml-auto truncate">{node.sandboxMode}</span>
        )}
      </div>
    </div>
  );
}

function Field({ label, value }) {
  return (
    <div className="min-w-0">
      <span className="text-slate-500">{label}: </span>
      <span className="text-slate-300 break-words overflow-wrap-anywhere">{value}</span>
    </div>
  );
}
