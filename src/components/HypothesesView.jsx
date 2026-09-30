import React from 'react';

/**
 * Functional Hypotheses View displaying proposed explanations or improvements (marked as untested).
 */
export default function HypothesesView({
  hypotheses = [],
  nextHypothesis = null,
  nextExperiment = null,
  onRunExperiment,
  hasRealRunAction = false,
}) {
  const allHypotheses = nextHypothesis
    ? [{ id: 'hyp-next', text: nextHypothesis, experiment: nextExperiment, isNext: true }, ...hypotheses]
    : hypotheses;

  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4 max-w-4xl mx-auto w-full select-none font-sans min-w-0 pb-32 animate-panel-entrance">
      <div className="border-b border-[#242424] pb-3 flex items-center justify-between">
        <div>
          <h2 className="text-base font-mono font-bold text-[#F4F4F6] uppercase flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#FF6500]" />
            Scientific Hypotheses
          </h2>
          <p className="text-xs text-[#8A8F98] mt-0.5">
            Proposed explanations and model improvement strategies (clearly marked as untested)
          </p>
        </div>
        <span className="text-xs font-mono text-[#8A8F98] px-2 py-1 bg-[#141416] border border-[#242424] rounded">
          Total: {allHypotheses.length}
        </span>
      </div>

      {allHypotheses.length === 0 ? (
        <div className="bg-[#0B0B0B] border border-[#242424] rounded p-8 text-center space-y-2">
          <p className="text-xs text-[#8A8F98] italic font-mono">
            No scientific hypothesis available yet.
          </p>
          <p className="text-xs text-[#8A8F98]">
            Hypotheses are generated during error analysis and baseline evaluation stages.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {allHypotheses.map((item, idx) => (
            <div key={item.id || idx} className="bg-[#0B0B0B] border border-[#242424] rounded p-4 space-y-2.5">
              <div className="flex items-center justify-between border-b border-[#242424] pb-2">
                <span className="text-xs font-mono font-semibold text-[#F4F4F6] uppercase flex items-center gap-2">
                  <span>HYPOTHESIS #{idx + 1}</span>
                  {item.isNext && (
                    <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-[#FF6500]/10 border border-[#FF6500]/30 text-[#FF6500]">
                      Active Candidate
                    </span>
                  )}
                </span>
                <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-[#141416] border border-[#242424] text-[#8A8F98]">
                  UNTESTED
                </span>
              </div>

              <p className="text-xs text-[#F4F4F6] leading-relaxed break-words overflow-wrap-anywhere">
                {typeof item === 'string' ? item : item.text}
              </p>

              {item.experiment && (
                <div className="pt-2 border-t border-[#242424]/60 flex items-center justify-between text-xs font-mono">
                  <span className="text-[#8A8F98]">
                    Proposed Test: <b className="text-[#F4F4F6]">{item.experiment.name || item.experiment.id}</b>
                  </span>

                  {hasRealRunAction && onRunExperiment && (
                    <button
                      type="button"
                      onClick={() => onRunExperiment(item.experiment)}
                      className="px-2.5 py-1 rounded bg-[#FF6500] hover:bg-[#FF302A] text-white text-[11px] font-semibold btn-transition cursor-pointer"
                    >
                      Run Experiment
                    </button>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
