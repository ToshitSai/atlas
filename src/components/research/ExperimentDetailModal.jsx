import React, { useEffect } from 'react';
import { orderedMetrics, formatMetricValue, metricLabel, statusTone, experimentLabel } from './format';

// Experiment detail / logs modal (brief §6). Shows the full real record of one
// experiment: identity, model, dataset, features, preprocessing, hyperparameters,
// validation strategy, metrics, runtime, seed, code/version, results, the study's
// error analysis, "why this experiment was selected", and the sandbox stdout/stderr.

export default function ExperimentDetailModal({ node, index, errorAnalysis, initialTab = 'details', onClose }) {
  const [tab, setTab] = React.useState(initialTab);

  useEffect(() => { setTab(initialTab); }, [initialTab, node?.id]);

  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose && onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  if (!node) return null;
  const tone = statusTone(node.status);
  const metrics = orderedMetrics(node.allMetrics || {});
  const isBaseline = node.parentId === null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/70 backdrop-blur-sm p-0 sm:p-6"
      role="dialog"
      aria-modal="true"
      aria-label={`Experiment ${experimentLabel(node, index)} details`}
      onClick={onClose}
    >
      <div
        className="w-full sm:max-w-3xl max-h-[92vh] bg-[#0D111A] border border-[#212B3B] rounded-t-2xl sm:rounded-2xl shadow-2xl flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="shrink-0 px-4 sm:px-6 py-4 border-b border-[#1E293B] flex items-start justify-between gap-3">
          <div className="min-w-0 space-y-1.5">
            <div className="flex items-center gap-2 flex-wrap">
              <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${isBaseline ? 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30' : 'bg-[#0B0F17] text-slate-400 border-[#212B3B]'}`}>
                {experimentLabel(node, index)}
              </span>
              <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${tone.chip}`}>{node.status || 'UNKNOWN'}</span>
              {node.metricValue != null && (
                <span className="text-[11px] font-mono text-emerald-400">
                  {node.metricName || 'score'}: {typeof node.metricValue === 'number' ? Number(node.metricValue.toFixed(4)) : node.metricValue}
                </span>
              )}
            </div>
            <h3 className="text-base font-bold text-slate-100 break-words overflow-wrap-anywhere">{node.title}</h3>
          </div>
          <button
            onClick={onClose}
            aria-label="Close"
            className="shrink-0 w-9 h-9 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-[#161B26] transition-colors cursor-pointer flex items-center justify-center text-lg"
          >
            ✕
          </button>
        </div>

        {/* Tabs */}
        <div className="shrink-0 px-4 sm:px-6 pt-3 flex items-center gap-1 border-b border-[#1E293B]">
          {['details', 'logs'].map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-3 py-2 text-[11px] font-semibold rounded-t-lg border-b-2 transition-colors cursor-pointer capitalize ${
                tab === t ? 'text-cyan-400 border-cyan-400' : 'text-slate-500 border-transparent hover:text-slate-300'
              }`}
            >
              {t === 'details' ? 'Details' : 'Logs'}
            </button>
          ))}
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto overscroll-contain px-4 sm:px-6 py-4 space-y-4 min-w-0">
          {tab === 'details' ? (
            <>
              <Section title="Why this experiment was selected">
                <p className="text-xs text-slate-300 leading-relaxed italic break-words overflow-wrap-anywhere">
                  “{node.hypothesis || 'No hypothesis recorded.'}”
                </p>
              </Section>

              <Section title="Configuration">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-2 text-[11px]">
                  <Row label="Experiment ID" value={node.experimentId || node.id} mono />
                  <Row label="Model" value={node.model} />
                  <Row label="Dataset" value={node.dataset} />
                  <Row label="Version / code" value={node.datasetVersion} mono />
                  <Row label="Random seed" value={node.seed} mono />
                  <Row label="Runtime" value={node.executionTime} mono />
                  <Row label="Features" value={node.featureCount != null ? `${node.featureCount} features` : null} />
                  <Row label="Sandbox" value={node.sandboxMode} />
                </div>
              </Section>

              {(node.preprocessing || node.splitStrategy) && (
                <Section title="Preprocessing & Validation">
                  <div className="space-y-2 text-[11px]">
                    {node.preprocessing && <Row label="Preprocessing" value={node.preprocessing} block />}
                    {node.splitStrategy && <Row label="Validation" value={node.splitStrategy} block />}
                  </div>
                </Section>
              )}

              {node.hyperparams && (
                <Section title="Hyperparameters">
                  <p className="text-[11px] font-mono text-purple-300 bg-[#0B0F17] border border-[#1E293B] rounded-lg p-3 break-words overflow-wrap-anywhere whitespace-pre-wrap">
                    {node.hyperparams}
                  </p>
                </Section>
              )}

              {Array.isArray(node.features) && node.features.length > 0 && (
                <Section title={`Features (${node.features.length})`}>
                  <div className="flex flex-wrap gap-1.5">
                    {node.features.slice(0, 60).map((f) => (
                      <span key={f} className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#0B0F17] border border-[#212B3B] text-slate-400 break-all">
                        {f}
                      </span>
                    ))}
                    {node.features.length > 60 && (
                      <span className="text-[10px] text-slate-500">+{node.features.length - 60} more</span>
                    )}
                  </div>
                </Section>
              )}

              {metrics.length > 0 && (
                <Section title="Metrics">
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                    {metrics.map(([k, v]) => (
                      <div key={k} className="p-2 rounded-lg bg-[#0B0F17] border border-[#212B3B] min-w-0">
                        <div className="text-[9px] text-slate-500 uppercase truncate" title={metricLabel(k)}>{metricLabel(k)}</div>
                        <div className="text-sm font-bold text-slate-100 font-mono">{formatMetricValue(k, v)}</div>
                      </div>
                    ))}
                  </div>
                </Section>
              )}

              {node.conclusion && (
                <Section title="Result">
                  <p className="text-xs text-slate-300 leading-relaxed break-words overflow-wrap-anywhere">{node.conclusion}</p>
                </Section>
              )}

              {errorAnalysis && (
                <Section title="Study Error Analysis">
                  <div className="space-y-2 text-[11px] text-slate-300">
                    <div className="flex flex-wrap gap-3">
                      <span>False positives: <b className="text-amber-400 font-mono">{errorAnalysis.falsePositivesCount ?? '—'}</b></span>
                      <span>False negatives: <b className="text-rose-400 font-mono">{errorAnalysis.falseNegativesCount ?? '—'}</b></span>
                      {errorAnalysis.bootstrapCI && (
                        <span>
                          95% CI: <b className="text-cyan-400 font-mono">[{errorAnalysis.bootstrapCI.ci_lower} – {errorAnalysis.bootstrapCI.ci_upper}]</b>
                        </span>
                      )}
                    </div>
                    {errorAnalysis.failureDiagnosis && (
                      <p className="text-slate-400 leading-relaxed break-words overflow-wrap-anywhere">{errorAnalysis.failureDiagnosis}</p>
                    )}
                  </div>
                </Section>
              )}
            </>
          ) : (
            <>
              <Section title="Standard output">
                <LogBox content={node.stdout} placeholder="No stdout captured for this experiment." />
              </Section>
              <Section title="Standard error">
                <LogBox content={node.stderr} placeholder="No stderr captured." tone="rose" />
              </Section>
              {node.artifacts?.script && (
                <Section title="Artifact paths">
                  <div className="space-y-1 text-[10px] font-mono text-slate-500 break-all">
                    {Object.entries(node.artifacts).map(([k, v]) => (
                      <div key={k}><span className="text-slate-600">{k}:</span> {v}</div>
                    ))}
                  </div>
                </Section>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <section className="min-w-0">
      <h4 className="text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-2">{title}</h4>
      {children}
    </section>
  );
}

function Row({ label, value, mono, block }) {
  if (value == null || value === '') return null;
  return (
    <div className={block ? 'min-w-0' : 'min-w-0 flex gap-1.5'}>
      <span className="text-slate-500 shrink-0">{label}:{block ? '' : ''}</span>
      <span className={`${mono ? 'font-mono' : ''} text-slate-300 break-words overflow-wrap-anywhere ${block ? 'block mt-0.5' : ''}`}>
        {value}
      </span>
    </div>
  );
}

function LogBox({ content, placeholder, tone = 'slate' }) {
  const empty = !content || !String(content).trim();
  return (
    <pre
      className={`text-[11px] font-mono bg-[#080C14] border border-[#1E293B] rounded-lg p-3 max-h-64 overflow-auto overscroll-contain whitespace-pre-wrap break-words ${
        empty ? 'text-slate-600 italic' : tone === 'rose' ? 'text-rose-200/90' : 'text-slate-300'
      }`}
    >
      {empty ? placeholder : String(content)}
    </pre>
  );
}
