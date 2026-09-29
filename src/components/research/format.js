// Shared formatting helpers for the research workspace panels.

export const METRIC_LABELS = {
  precision: 'Precision',
  recall: 'Recall',
  f1: 'F1',
  pr_auc: 'PR-AUC',
  roc_auc: 'ROC-AUC',
  fpr: 'FPR',
  fnr: 'FNR',
  accuracy: 'Accuracy',
  r2: 'R²',
  mse: 'MSE',
  mae: 'MAE',
  rmse: 'RMSE',
  metric_value: 'Score',
};

// Metrics the orchestrator ranks on / users care about most, in display order.
const PREFERRED = ['pr_auc', 'f1', 'recall', 'precision', 'roc_auc', 'r2', 'accuracy', 'fpr', 'fnr'];

export function isRateMetric(key) {
  return !['r2', 'mse', 'mae', 'rmse', 'metric_value'].includes(key);
}

export function formatMetricValue(key, value) {
  if (typeof value !== 'number' || Number.isNaN(value)) return '—';
  if (isRateMetric(key)) return `${(value * 100).toFixed(1)}%`;
  return Number(value.toFixed(4)).toString();
}

export function metricLabel(key) {
  return METRIC_LABELS[key] || String(key).toUpperCase();
}

// Order a metrics dict for display: preferred keys first, then any extras.
export function orderedMetrics(metrics = {}) {
  const entries = Object.entries(metrics || {}).filter(([, v]) => typeof v === 'number');
  const seen = new Set();
  const out = [];
  for (const k of PREFERRED) {
    if (k in metrics && typeof metrics[k] === 'number') {
      out.push([k, metrics[k]]);
      seen.add(k);
    }
  }
  for (const [k, v] of entries) {
    if (!seen.has(k)) out.push([k, v]);
  }
  return out;
}

export function statusTone(status) {
  switch (String(status || '').toUpperCase()) {
    case 'IMPROVED':
    case 'SUCCESS':
    case 'COMPLETED':
      return { text: 'text-emerald-400', chip: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30', dot: 'bg-emerald-400' };
    case 'PLATEAUED':
      return { text: 'text-amber-400', chip: 'bg-amber-500/10 text-amber-400 border-amber-500/30', dot: 'bg-amber-400' };
    case 'RUNNING':
    case 'IN_PROGRESS':
      return { text: 'text-cyan-400', chip: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30', dot: 'bg-cyan-400' };
    case 'FAILED':
    case 'ERROR':
      return { text: 'text-rose-400', chip: 'bg-rose-500/10 text-rose-400 border-rose-500/30', dot: 'bg-rose-400' };
    default:
      return { text: 'text-slate-400', chip: 'bg-slate-500/10 text-slate-400 border-slate-500/30', dot: 'bg-slate-500' };
  }
}

export function experimentLabel(node, index) {
  if (!node) return '';
  if (node.parentId === null) return 'BASELINE';
  const id = node.experimentId || node.id || `exp-${index + 1}`;
  return String(id).replace(/^exp-?/i, 'EXP-').toUpperCase();
}
