import React, { useMemo, useState } from 'react';
import { buildResearchModel, STAGE } from './researchModel';
import ResearchPipeline from './ResearchPipeline';
import ReasoningPanel from './ReasoningPanel';
import ExperimentCard from './ExperimentCard';
import ExperimentDetailModal from './ExperimentDetailModal';
import HypothesisPanel from './HypothesisPanel';
import ResultsPanel from './ResultsPanel';
import LiteraturePanel from './LiteraturePanel';
import ErrorAnalysisPanel from './ErrorAnalysisPanel';

// ResearchWorkspace (brief §2–§10): the structured, non-chat research experience.
// It renders entirely from the real backend research state (projects/stageStates/
// runState/agentLogs/events, literature, dataset report, baselines, experiment
// tree nodes, error analysis, report) — never from invented values. The chat is
// kept as a separate tab in the shell so the research output is not one giant
// chat bubble.

const SECTIONS = [
  { key: 'overview', label: 'Overview' },
  { key: 'experiments', label: 'Experiments' },
  { key: 'analysis', label: 'Error Analysis' },
  { key: 'literature', label: 'Literature' },
];

const STATUS_BADGE = {
  RESEARCHING: { text: '● Researching…', cls: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30 animate-pulse' },
  COMPLETED: { text: '✓ Research Complete', cls: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' },
  FAILED: { text: '✕ Failed', cls: 'bg-rose-500/10 text-rose-400 border-rose-500/30' },
  STOPPED: { text: '■ Stopped', cls: 'bg-slate-500/10 text-slate-400 border-slate-500/30' },
  IDLE: { text: '○ Idle', cls: 'bg-slate-500/10 text-slate-400 border-slate-500/30' },
};

export default function ResearchWorkspace({
  project,
  datasetReport,
  baselines,
  treeNodes,
  errorAnalysis,
  literature,
  reportMd,
  onControl,
}) {
  const [section, setSection] = useState('overview');
  const [selected, setSelected] = useState(null); // { node, index, tab }
  const [railOpen, setRailOpen] = useState(false); // mobile pipeline drawer

  const model = useMemo(
    () =>
      buildResearchModel({ project, datasetReport, baselines, treeNodes, errorAnalysis, literature, reportMd }),
    [project, datasetReport, baselines, treeNodes, errorAnalysis, literature, reportMd]
  );

  if (!project) return null;

  const badge = STATUS_BADGE[model.overall] || STATUS_BADGE.IDLE;
  const running = model.overall === 'RESEARCHING';
  const canResume = ['STOPPED', 'FAILED', 'PAUSED'].includes(project.status) || project.controlSignal === 'PAUSE';
  const allNodes = [model.rootNode, ...model.expNodes].filter(Boolean);
  const failedStage = model.failedStage;

  const openDetails = (node, index) => setSelected({ node, index, tab: 'details' });
  const openLogs = (node, index) => setSelected({ node, index, tab: 'logs' });

  return (
    <div className="flex-1 min-w-0 flex flex-col overflow-hidden">
      {/* Goal + status banner (brief §2) */}
      <div className="shrink-0 border-b border-[#1E293B] bg-[#0D111A] px-3 sm:px-6 py-4 min-w-0">
        <div className="max-w-7xl mx-auto min-w-0 space-y-2">
          <div className="flex items-center gap-2 text-[10px] font-mono uppercase tracking-wider text-cyan-400">
            <span className={running ? 'w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping' : 'w-1.5 h-1.5 rounded-full bg-cyan-400/50'} />
            Atlas · Autonomous ML Research
          </div>
          <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 min-w-0">
            <div className="min-w-0 space-y-1">
              <div className="text-[10px] text-slate-500 uppercase tracking-wide">Research Goal</div>
              <h2 className="text-base sm:text-lg font-bold text-slate-100 leading-snug break-words overflow-wrap-anywhere">
                {project.objective || project.name}
              </h2>
              {project.researchQuestion && project.researchQuestion !== project.objective && (
                <p className="text-[11px] text-slate-400 leading-relaxed break-words overflow-wrap-anywhere">
                  {project.researchQuestion}
                </p>
              )}
            </div>
            <div className="shrink-0 flex flex-col items-start sm:items-end gap-2">
              <span className={`text-[11px] font-semibold px-3 py-1 rounded-full border ${badge.cls}`}>{badge.text}</span>
              <div className="flex flex-wrap items-center gap-1.5">
                {running && onControl && (
                  <>
                    <ControlBtn onClick={() => onControl('PAUSE')}>❚❚ Pause</ControlBtn>
                    <ControlBtn onClick={() => onControl('STOP')} danger>■ Stop</ControlBtn>
                  </>
                )}
                {canResume && onControl && (
                  <ControlBtn onClick={() => onControl('RUN')} primary>▶ Resume</ControlBtn>
                )}
              </div>
            </div>
          </div>

          {/* Meta strip — all real values */}
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-slate-500 pt-1 min-w-0">
            {project.bestModel && project.bestModel !== 'Not trained' && (
              <span>Best: <b className="text-slate-300 font-medium">{project.bestModel}</b>{project.bestMetric && project.bestMetric !== 'N/A' ? ` · ${project.bestMetric}` : ''}</span>
            )}
            <span>Experiments: <b className="text-slate-300 font-mono">{model.experimentsCount}/{model.maxExperiments}</b></span>
            {project.computeUsed && <span>Compute: <b className="text-slate-300 font-mono">{project.computeUsed}</b></span>}
            {project.engineState && <span>Engine: <b className="text-slate-300">{project.engineState}</b></span>}
          </div>

          {/* Honest failure banner (brief §12) */}
          {(failedStage || project.errorDetail) && (
            <div className="mt-2 p-3 rounded-xl bg-rose-500/5 border border-rose-500/30 min-w-0">
              <div className="text-[11px] font-semibold text-rose-300 flex items-center gap-2">
                <span>✕</span>
                {failedStage ? `${failedStage.label} failed` : 'Research failed'}
              </div>
              <p className="text-[11px] text-rose-200/80 mt-1 break-words overflow-wrap-anywhere">
                {project.errorDetail || failedStage?.detail || 'See the reasoning log for the actual error.'}
              </p>
              {canResume && onControl && (
                <button
                  onClick={() => onControl('RUN')}
                  className="mt-2 px-3 py-1.5 min-h-[32px] rounded-lg bg-rose-500/15 hover:bg-rose-500/25 text-rose-200 border border-rose-500/40 text-[11px] font-semibold transition-colors cursor-pointer"
                >
                  ↻ Retry / Resume
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Mobile pipeline toggle */}
      <div className="lg:hidden shrink-0 px-3 sm:px-6 pt-3">
        <button
          onClick={() => setRailOpen((v) => !v)}
          className="w-full flex items-center justify-between px-3 py-2 rounded-xl bg-[#121722] border border-[#1E293B] text-xs font-semibold text-slate-300 cursor-pointer"
          aria-expanded={railOpen}
        >
          <span>Research Pipeline ({model.stages.filter((s) => s.state === STAGE.COMPLETED).length}/{model.stages.length})</span>
          <span className="text-slate-500">{railOpen ? '▲' : '▼'}</span>
        </button>
      </div>

      {/* Body: left rail (pipeline + reasoning) + main (sections) */}
      <div className="flex-1 overflow-y-auto overscroll-contain min-w-0">
        <div className="max-w-7xl mx-auto px-3 sm:px-6 py-4 grid grid-cols-1 lg:grid-cols-12 gap-4 min-w-0">
          {/* Left rail */}
          <aside className={`lg:col-span-4 xl:col-span-3 space-y-4 min-w-0 ${railOpen ? 'block' : 'hidden lg:block'}`}>
            <div className="lg:sticky lg:top-0 space-y-4">
              <ResearchPipeline stages={model.stages} />
              <ReasoningPanel logs={project.agentLogs || []} running={running} />
            </div>
          </aside>

          {/* Main */}
          <main className="lg:col-span-8 xl:col-span-9 min-w-0 space-y-4">
            {/* Section nav */}
            <div className="flex items-center gap-1 overflow-x-auto overscroll-x-contain pb-1 -mx-1 px-1 min-w-0">
              {SECTIONS.map((s) => (
                <button
                  key={s.key}
                  onClick={() => setSection(s.key)}
                  className={`shrink-0 px-3 py-1.5 rounded-lg text-[11px] font-semibold border transition-colors cursor-pointer ${
                    section === s.key
                      ? 'bg-[#1E293B] text-cyan-400 border-[#2B364A]'
                      : 'bg-[#121722] text-slate-400 border-[#1E293B] hover:text-slate-200'
                  }`}
                >
                  {s.label}
                  {s.key === 'experiments' && model.expNodes.length > 0 && (
                    <span className="ml-1.5 font-mono text-[10px] text-slate-500">{allNodes.length}</span>
                  )}
                  {s.key === 'literature' && model.literatureCount > 0 && (
                    <span className="ml-1.5 font-mono text-[10px] text-slate-500">{model.literatureCount}</span>
                  )}
                  {s.key === 'report' && reportMd && <span className="ml-1.5 text-[10px]">📄</span>}
                </button>
              ))}
            </div>

            {section === 'overview' && (
              <div className="space-y-4 min-w-0">
                <DatasetSummary report={datasetReport} stageState={project.stageStates?.dataset_eda} />
                <ResultsPanel model={model} onSelect={openDetails} />
                <HypothesisPanel model={model} project={project} canResume={canResume} onResume={() => onControl && onControl('RUN')} />
              </div>
            )}

            {section === 'experiments' && (
              <div className="space-y-3 min-w-0">
                {allNodes.length === 0 ? (
                  <EmptyCard>
                    {running ? 'Designing the first experiment…' : 'No experiments yet.'}
                  </EmptyCard>
                ) : (
                  allNodes.map((n, i) => (
                    <ExperimentCard key={n.id} node={n} index={i} onViewDetails={() => openDetails(n, i)} onViewLogs={() => openLogs(n, i)} />
                  ))
                )}
              </div>
            )}

            {section === 'analysis' && (
              <ErrorAnalysisPanel analysis={errorAnalysis} stageState={project.stageStates?.error_diagnostics} />
            )}

            {section === 'literature' && (
              <LiteraturePanel literature={literature} stageState={project.stageStates?.literature_search} />
            )}
          </main>
        </div>
      </div>

      {selected && (
        <ExperimentDetailModal
          node={selected.node}
          index={selected.index}
          errorAnalysis={errorAnalysis}
          initialTab={selected.tab}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  );
}

function ControlBtn({ children, onClick, danger, primary }) {
  const cls = primary
    ? 'bg-cyan-500 hover:bg-cyan-400 text-slate-950 border-cyan-500'
    : danger
      ? 'bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border-rose-500/40'
      : 'bg-[#131822] hover:bg-[#1C2536] text-slate-300 border-[#212B3B]';
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1.5 min-h-[32px] rounded-lg border text-[11px] font-semibold transition-colors cursor-pointer ${cls}`}
    >
      {children}
    </button>
  );
}

function DatasetSummary({ report, stageState }) {
  if (!report) {
    return (
      <EmptyCard>
        {stageState === 'RUNNING' ? 'Profiling the dataset…' : 'Waiting for dataset analysis…'}
      </EmptyCard>
    );
  }
  const features = Math.max((report.columnCount || 0) - 1, 0);
  return (
    <div className="bg-[#121722] border border-[#1E293B] rounded-2xl p-4 sm:p-5 min-w-0">
      <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 border-b border-[#1E293B]/70 pb-3 mb-3">
        Dataset
      </h3>
      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1 mb-3 min-w-0">
        <span className="text-sm font-semibold text-slate-100 break-all">{report.repoId || report.filename}</span>
        {report.license && <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#0B0F17] border border-[#212B3B] text-slate-400">{report.license}</span>}
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center">
        <Tile label="Rows" value={(report.rowCount || 0).toLocaleString()} />
        <Tile label="Features" value={features} />
        <Tile label="Target" value={report.targetCandidate || '—'} small />
        <Tile label="Task" value={report.taskType || '—'} small />
      </div>
      {report.isImbalanced && report.minorityClassPct != null && (
        <p className="text-[11px] text-amber-300/90 mt-3 break-words">
          Highly imbalanced — the minority class is only {report.minorityClassPct}% of records, so the study ranks models on PR-AUC / recall rather than accuracy.
        </p>
      )}
      {Array.isArray(report.classDistribution) && report.classDistribution.length > 0 && (
        <div className="mt-3 space-y-1.5">
          <div className="text-[10px] uppercase tracking-wide text-slate-500">Class distribution</div>
          {report.classDistribution.slice(0, 6).map((c, i) => (
            <div key={i} className="flex items-center gap-2 text-[11px] min-w-0">
              <span className="text-slate-400 w-28 truncate" title={c.label}>{c.label}</span>
              <span className="flex-1 h-1.5 rounded-full bg-[#0B0F17] overflow-hidden min-w-0">
                <span className="block h-full bg-cyan-500/60" style={{ width: `${Math.min(c.percentage || 0, 100)}%` }} />
              </span>
              <span className="text-slate-500 font-mono shrink-0">{c.percentage != null ? `${c.percentage}%` : c.count}</span>
            </div>
          ))}
        </div>
      )}
      {(report.source || report.sourceUrl) && (
        <p className="text-[10px] text-slate-600 mt-3 break-all">
          Source: {report.source || 'dataset'}
          {report.revision ? ` · version ${String(report.revision).slice(0, 8)}` : ''}
        </p>
      )}
    </div>
  );
}

function Tile({ label, value, small }) {
  return (
    <div className="p-2.5 rounded-lg bg-[#0B0F17] border border-[#212B3B] min-w-0">
      <div className="text-[9px] text-slate-500 uppercase truncate" title={label}>{label}</div>
      <div className={`font-bold text-slate-100 truncate ${small ? 'text-[11px]' : 'text-sm font-mono'}`} title={String(value)}>{value}</div>
    </div>
  );
}

function EmptyCard({ children }) {
  return (
    <div className="bg-[#121722] border border-[#1E293B] rounded-2xl p-6 text-center">
      <p className="text-xs text-slate-500 italic">{children}</p>
    </div>
  );
}
