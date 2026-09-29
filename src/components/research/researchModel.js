// Derives a structured, UI-agnostic research view-model from the raw backend
// state (brief §14: separate RESEARCH STATE from UI PRESENTATION).
//
// Every value here is bound to real persisted data produced by the orchestrator
// (stageStates, runState, agentLogs, literature, datasetReport, baselines,
// tree_nodes, errorAnalysis, report). Nothing is invented: when a number is not
// available yet the caller renders an honest fallback ("Searching…", "Waiting
// for results…", "Not available yet") instead of a fabricated value.

export const STAGE = {
  PENDING: 'PENDING',
  RUNNING: 'RUNNING',
  COMPLETED: 'COMPLETED',
  FAILED: 'FAILED',
  UNAVAILABLE: 'UNAVAILABLE', // real backend state NOT_CONFIGURED (e.g. no literature API)
};

function mapStageState(s) {
  switch (s) {
    case 'COMPLETED': return STAGE.COMPLETED;
    case 'RUNNING': return STAGE.RUNNING;
    case 'FAILED': return STAGE.FAILED;
    case 'NOT_CONFIGURED': return STAGE.UNAVAILABLE;
    default: return STAGE.PENDING;
  }
}

const pct = (v) => (typeof v === 'number' ? `${(v * 100).toFixed(1)}%` : null);
const num = (v, d = 4) => (typeof v === 'number' ? Number(v.toFixed(d)) : null);

// Pick the strongest completed baseline by the metric the orchestrator ranked on
// (PR-AUC under imbalance, else F1 / R2). Mirrors the backend selection rule.
export function pickBestBaseline(baselines) {
  const completed = (baselines || []).filter((b) => b.status === 'COMPLETED');
  if (!completed.length) return null;
  return completed.reduce((a, b) => {
    const av = (a.metrics && (a.metrics.pr_auc ?? a.metrics.f1 ?? a.metrics.r2)) || 0;
    const bv = (b.metrics && (b.metrics.pr_auc ?? b.metrics.f1 ?? b.metrics.r2)) || 0;
    return bv > av ? b : a;
  });
}

export function buildResearchModel(props) {
  const {
    project,
    datasetReport,
    baselines,
    treeNodes,
    errorAnalysis,
    literature,
    reportMd,
  } = props;

  const stageStates = project?.stageStates || {};
  const runState = project?.runState || null;
  const status = project?.status || null;
  const terminal = ['COMPLETED', 'FAILED', 'STOPPED'].includes(status);

  const rootNode = (treeNodes || []).find((n) => n.parentId === null) || null;
  const expNodes = (treeNodes || []).filter((n) => n.parentId !== null);
  const completedBaselines = (baselines || []).filter((b) => b.status === 'COMPLETED');
  const bestBaseline = pickBestBaseline(baselines);
  const literatureCount = (literature || []).length;

  const maxExperiments = project?.maxExperiments ?? 5;
  const experimentsCount = project?.experimentsCount ?? expNodes.length;

  const reportDone = Boolean(reportMd) || stageStates.research_report === 'COMPLETED';
  const reportRunning = stageStates.research_report === 'RUNNING';

  // The experiment loop is the last research step; "next experiment" is done when
  // the budget is exhausted, the report is generated, or the run went terminal.
  const loopExhausted = experimentsCount >= maxExperiments || reportDone || terminal;

  const bestExp = expNodes.length
    ? expNodes.reduce((a, b) => ((b.metricValue ?? -Infinity) > (a.metricValue ?? -Infinity) ? b : a))
    : null;

  // ---- Pipeline stages (the user-facing 12-step research timeline) --------
  const stages = [
    {
      key: 'understand-goal',
      label: 'Understand Research Goal',
      state: mapStageState(stageStates.research_question),
      detail: project?.researchQuestion || project?.objective || 'Parsing the research objective…',
    },
    {
      key: 'planning',
      label: 'Research Planning',
      // Planning produces the research question + strategy; it is done once the
      // question stage completed, running while it runs.
      state: mapStageState(stageStates.research_question),
      detail:
        datasetReport?.taskType
          ? `Task type: ${datasetReport.taskType}${rootNode?.metricName ? ` · primary metric: ${rootNode.metricName}` : ''}`
          : project?.researchQuestion
            ? 'Research strategy set.'
            : 'Planning the study…',
    },
    {
      key: 'literature',
      label: 'Literature Search',
      state: mapStageState(stageStates.literature_search),
      count: literatureCount > 0 ? `${literatureCount} paper${literatureCount === 1 ? '' : 's'}` : null,
      detail:
        literatureCount > 0
          ? `${literatureCount} relevant paper${literatureCount === 1 ? '' : 's'} analyzed`
          : mapStageState(stageStates.literature_search) === STAGE.UNAVAILABLE
            ? 'Literature API not configured'
            : mapStageState(stageStates.literature_search) === STAGE.RUNNING
              ? 'Searching literature…'
              : 'Waiting for results…',
    },
    {
      key: 'dataset',
      label: 'Dataset Discovery',
      state: mapStageState(stageStates.dataset_eda),
      count: datasetReport ? '1 dataset' : null,
      detail: datasetReport
        ? `${datasetReport.repoId || datasetReport.filename} · ${(datasetReport.rowCount || 0).toLocaleString()} rows · ${Math.max((datasetReport.columnCount || 0) - 1, 0)} features · target ${datasetReport.targetCandidate || '—'}`
        : mapStageState(stageStates.dataset_eda) === STAGE.RUNNING
          ? 'Profiling dataset…'
          : 'Waiting for dataset…',
    },
    {
      key: 'baseline',
      label: 'Baseline Selection',
      state: mapStageState(stageStates.baseline_training),
      count: completedBaselines.length ? `${completedBaselines.length} models` : null,
      detail: completedBaselines.length
        ? `${completedBaselines.length} baseline${completedBaselines.length === 1 ? '' : 's'} evaluated · best: ${bestBaseline?.name || project?.bestModel || '—'}${project?.bestMetric ? ` (${project.bestMetric})` : ''}`
        : mapStageState(stageStates.baseline_training) === STAGE.RUNNING
          ? 'Training baseline models…'
          : 'Waiting for baselines…',
    },
    {
      key: 'exp-design',
      label: 'Experiment Design',
      state:
        expNodes.length >= 1
          ? STAGE.COMPLETED
          : stageStates.hypothesis_generation === 'RUNNING'
            ? STAGE.RUNNING
            : stageStates.hypothesis_generation === 'FAILED'
              ? STAGE.FAILED
              : STAGE.PENDING,
      detail: expNodes[0]?.title || (stageStates.hypothesis_generation === 'RUNNING' ? 'Designing the first experiment…' : 'Waiting for baseline…'),
    },
    {
      key: 'exp-exec',
      label: 'Experiment Execution',
      state:
        expNodes.length >= 1
          ? STAGE.COMPLETED
          : stageStates.sandboxed_execution === 'RUNNING'
            ? STAGE.RUNNING
            : stageStates.sandboxed_execution === 'FAILED'
              ? STAGE.FAILED
              : mapStageState(stageStates.sandboxed_execution) === STAGE.UNAVAILABLE
                ? STAGE.UNAVAILABLE
                : STAGE.PENDING,
      count: expNodes.length ? `${expNodes.length}/${maxExperiments}` : null,
      detail: `${expNodes.length} of ${maxExperiments} experiment${maxExperiments === 1 ? '' : 's'} executed`,
    },
    {
      key: 'evaluation',
      label: 'Evaluation',
      // Evaluation = metrics computed for the baselines/experiments. Real once a
      // completed baseline carries metrics.
      state: completedBaselines.length ? STAGE.COMPLETED : mapStageState(stageStates.baseline_training) === STAGE.RUNNING ? STAGE.RUNNING : STAGE.PENDING,
      detail: bestBaseline?.metrics
        ? `Primary metric ${rootNode?.metricName || 'score'}: ${num(bestBaseline.metrics[rootNode?.metricName?.toLowerCase?.()] ?? bestBaseline.metrics.pr_auc ?? bestBaseline.metrics.f1 ?? bestBaseline.metrics.r2) ?? '—'}`
        : 'Waiting for results…',
    },
    {
      key: 'error-analysis',
      label: 'Error Analysis',
      state: mapStageState(stageStates.error_diagnostics),
      detail: errorAnalysis
        ? `${errorAnalysis.falsePositivesCount ?? 0} false positives · ${errorAnalysis.falseNegativesCount ?? 0} false negatives`
        : mapStageState(stageStates.error_diagnostics) === STAGE.RUNNING
          ? 'Analyzing errors…'
          : 'Waiting for results…',
    },
    {
      key: 'hypothesis',
      label: 'Hypothesis Generation',
      // A follow-up hypothesis (informed by error analysis) exists once a second
      // experiment node was generated.
      state:
        expNodes.length >= 2
          ? STAGE.COMPLETED
          : expNodes.length === 1 && !loopExhausted
            ? STAGE.RUNNING
            : expNodes.length === 1
              ? STAGE.COMPLETED
              : STAGE.PENDING,
      detail: expNodes.length ? expNodes[expNodes.length - 1].title : 'Waiting for the first experiment…',
    },
    {
      key: 'next-experiment',
      label: 'Next Experiment',
      state: loopExhausted
        ? STAGE.COMPLETED
        : stageStates.sandboxed_execution === 'RUNNING' || stageStates.hypothesis_generation === 'RUNNING'
          ? STAGE.RUNNING
          : STAGE.PENDING,
      count: `${Math.min(experimentsCount, maxExperiments)}/${maxExperiments}`,
      detail: loopExhausted
        ? `Research loop finished (${experimentsCount} experiment${experimentsCount === 1 ? '' : 's'}).`
        : `Iteration ${experimentsCount} of ${maxExperiments}`,
    },
    {
      key: 'report',
      label: 'Research Report',
      state: reportDone ? STAGE.COMPLETED : reportRunning ? STAGE.RUNNING : mapStageState(stageStates.research_report) === STAGE.FAILED ? STAGE.FAILED : STAGE.PENDING,
      detail: reportDone ? 'Report generated from verified results.' : reportRunning ? 'Compiling report…' : 'Waiting for experiments…',
    },
  ];

  // Overall run status for the header badge.
  let overall = 'IDLE';
  if (status === 'COMPLETED') overall = 'COMPLETED';
  else if (status === 'FAILED') overall = 'FAILED';
  else if (status === 'STOPPED') overall = 'STOPPED';
  else if (status === 'RUNNING' || status === 'IN_PROGRESS' || status === 'QUEUED') overall = 'RESEARCHING';

  const failedStage = stages.find((s) => s.state === STAGE.FAILED) || null;

  return {
    stages,
    overall,
    runState,
    status,
    terminal,
    failedStage,
    rootNode,
    expNodes,
    bestExp,
    completedBaselines,
    bestBaseline,
    literatureCount,
    literature,
    errorAnalysis,
    datasetReport,
    reportMd,
    reportDone,
    maxExperiments,
    experimentsCount,
    loopExhausted,
    pct,
    num,
  };
}

export { pct, num };
