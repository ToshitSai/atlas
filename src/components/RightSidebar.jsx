import React from 'react';

/**
 * Right Sidebar Component (~290px wide).
 * Palette: #111111 background, #303030 borders.
 * Includes Research Context, Primary Sources, Latest Insight, Next Hypothesis, Next Experiment.
 */
export default function RightSidebar({
  context = {},
  sources = [],
  latestInsight = null,
  nextHypothesis = null,
  nextExperiment = null,
  onViewExperiment,
  onRunExperiment,
  hasRealRunAction = false,
}) {
  const {
    researchType,
    domain,
    complexity,
    validatedSourcesCount,
    experimentsCount,
    currentStage,
  } = context;

  return (
    <aside className="w-[290px] shrink-0 bg-[#111111] border-l border-[#303030] flex flex-col h-full overflow-y-auto p-3 space-y-4 select-none font-sans text-xs">
      
      {/* 1. Research Context Card */}
      <section className="bg-[#181818] border border-[#303030] rounded p-3 space-y-2.5">
        <h3 className="text-[11px] font-mono font-bold tracking-wider text-[#E8E5DF] uppercase border-b border-[#303030] pb-1.5 flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-[#F15A3A]" />
          Research Context
        </h3>
        <div className="space-y-1.5 text-xs">
          <ContextRow label="Research Type" value={researchType || 'Not available yet'} />
          <ContextRow label="Domain" value={domain || 'Not configured'} />
          <ContextRow label="Complexity" value={complexity || 'Not available yet'} />
          <ContextRow
            label="Validated Sources"
            value={validatedSourcesCount != null ? String(validatedSourcesCount) : 'Waiting for results'}
          />
          <ContextRow
            label="Experiments"
            value={experimentsCount != null ? String(experimentsCount) : 'Waiting for results'}
          />
          <ContextRow label="Current Stage" value={currentStage || 'Not started'} highlight />
        </div>
      </section>

      {/* 2. Primary Sources */}
      <section className="bg-[#181818] border border-[#303030] rounded p-3 space-y-2.5">
        <h3 className="text-[11px] font-mono font-bold tracking-wider text-[#E8E5DF] uppercase border-b border-[#303030] pb-1.5 flex items-center justify-between">
          <span>Primary Sources</span>
          {sources.length > 0 && <span className="font-mono text-[10px] text-[#8A8884]">({sources.length})</span>}
        </h3>

        {sources.length === 0 ? (
          <p className="text-xs text-[#8A8884] italic py-1">
            No validated sources yet.
          </p>
        ) : (
          <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
            {sources.map((src, i) => (
              <div key={src.id || i} className="p-2 rounded bg-[#1B1B1B] border border-[#303030] space-y-1 card-hover-lift">
                <a
                  href={src.url || '#'}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-medium text-[#E8E5DF] hover:text-[#F15A3A] text-xs block leading-snug line-clamp-2 transition-colors"
                >
                  {src.title || 'Untitled Source'}
                </a>
                {src.authors && (
                  <div className="text-[10px] text-[#8A8884] truncate">
                    {src.authors} {src.year ? `(${src.year})` : ''}
                  </div>
                )}
                {src.publisher && (
                  <div className="text-[10px] font-mono text-[#8A8884] truncate">
                    {src.publisher}
                  </div>
                )}
                {src.relevance && (
                  <div className="text-[11px] text-[#8A8884] leading-tight line-clamp-2 mt-0.5">
                    {src.relevance}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      {/* 3. Latest Insight */}
      <section className="bg-[#181818] border border-[#303030] rounded p-3 space-y-2">
        <h3 className="text-[11px] font-mono font-bold tracking-wider text-[#E8E5DF] uppercase border-b border-[#303030] pb-1.5">
          Latest Insight
        </h3>
        {latestInsight ? (
          <p className="text-xs text-[#E8E5DF] leading-relaxed break-words overflow-wrap-anywhere">
            {latestInsight}
          </p>
        ) : (
          <p className="text-xs text-[#8A8884] italic py-1">
            No research finding available yet.
          </p>
        )}
      </section>

      {/* 4. Next Hypothesis */}
      {nextHypothesis && (
        <section className="bg-[#181818] border border-[#303030] rounded p-3 space-y-2">
          <div className="flex items-center justify-between border-b border-[#303030] pb-1.5">
            <h3 className="text-[11px] font-mono font-bold tracking-wider text-[#E8E5DF] uppercase">
              Next Hypothesis
            </h3>
            <span className="text-[9px] font-mono uppercase px-1.5 py-0.5 rounded bg-[#F15A3A]/10 border border-[#F15A3A]/30 text-[#F15A3A]">
              Untested
            </span>
          </div>
          <p className="text-xs text-[#E8E5DF] leading-relaxed break-words overflow-wrap-anywhere">
            {nextHypothesis}
          </p>
        </section>
      )}

      {/* 5. Next Experiment */}
      {nextExperiment && (
        <section className="bg-[#181818] border border-[#303030] rounded p-3 space-y-2.5">
          <h3 className="text-[11px] font-mono font-bold tracking-wider text-[#E8E5DF] uppercase border-b border-[#303030] pb-1.5">
            Next Experiment
          </h3>
          <div className="text-xs text-[#E8E5DF] font-mono truncate">
            {nextExperiment.id || nextExperiment.name || 'Proposed Run'}
          </div>
          {nextExperiment.description && (
            <p className="text-[11px] text-[#8A8884] leading-tight">
              {nextExperiment.description}
            </p>
          )}

          <div className="flex items-center gap-2 pt-1">
            {onViewExperiment && (
              <button
                type="button"
                onClick={() => onViewExperiment(nextExperiment)}
                className="flex-1 py-1.5 px-2 rounded bg-[#1B1B1B] border border-[#303030] text-[#E8E5DF] text-[11px] hover:border-[#353535] btn-transition text-center"
              >
                View Experiment
              </button>
            )}

            {/* Run Experiment button ONLY when a real execution operation is available */}
            {hasRealRunAction && onRunExperiment && (
              <button
                type="button"
                onClick={() => onRunExperiment(nextExperiment)}
                className="flex-1 py-1.5 px-2 rounded bg-[#F15A3A] hover:bg-[#E44D31] text-white text-[11px] font-semibold btn-transition text-center cursor-pointer"
              >
                Run Experiment
              </button>
            )}
          </div>
        </section>
      )}

    </aside>
  );
}

function ContextRow({ label, value, highlight }) {
  return (
    <div className="flex items-center justify-between gap-2 text-xs">
      <span className="text-[#8A8884] shrink-0">{label}:</span>
      <span className={`font-mono text-right truncate ${highlight ? 'text-[#F15A3A] font-medium' : 'text-[#E8E5DF]'}`}>
        {value}
      </span>
    </div>
  );
}
