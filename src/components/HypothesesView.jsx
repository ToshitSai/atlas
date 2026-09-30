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
      <div className="border-b border-[#242424] pb-3 flex items-center justify-between font-sans">
        <div>
          <h2 className="text-base font-semibold text-[#F4F4F6] font-sans flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#FF6500]" />
            Scientific Hypotheses
          </h2>
          <p className="text-xs text-[#8A8F98] mt-0.5 font-sans">
            Proposed explanations and model improvement strategies (clearly marked as untested)
          </p>
        </div>
        <span className="text-xs font-medium text-[#8A8F98] px-2.5 py-1 bg-[#141416] border border-[#242424] rounded-full font-sans">
          Total: {allHypotheses.length}
        </span>
      </div>

      {allHypotheses.length === 0 ? (
        <div className="bg-[#0B0B0B] border border-[#242424] rounded-xl p-8 text-center space-y-2 font-sans">
          <p className="text-xs text-[#8A8F98] font-sans">
            No scientific hypothesis available yet.
          </p>
          <p className="text-xs text-[#8A8F98] font-sans">
            Hypotheses are generated during error analysis and baseline evaluation stages.
          </p>
        </div>
      ) : (
        <div className="space-y-3 font-sans">
          {allHypotheses.map((item, idx) => (
            <div key={item.id || idx} className="bg-[#0B0B0B] border border-[#242424] rounded-xl p-4 space-y-2.5 font-sans">
              <div className="flex items-center justify-between border-b border-[#242424] pb-2 font-sans">
                <span className="text-xs font-semibold text-[#F4F4F6] flex items-center gap-2 font-sans">
                  <span>Hypothesis #{idx + 1}</span>
                  {item.isNext && (
                    <span className="text-xs font-medium px-2.5 py-0.5 rounded-full bg-[#FF6500]/10 border border-[#FF6500]/30 text-[#FF6500] font-sans">
                      Active Candidate
                    </span>
                  )}
                </span>
                <span className="text-xs font-medium px-2.5 py-0.5 rounded-full bg-[#141416] border border-[#242424] text-[#8A8F98] font-sans">
                  Untested
                </span>
              </div>

              <p className="text-sm text-[#F4F4F6] leading-relaxed break-words overflow-wrap-anywhere font-sans">
                {typeof item === 'string' ? item : item.text}
              </p>

              {item.experiment && (
                <div className="pt-2 border-t border-[#242424]/60 flex items-center justify-between text-xs font-sans">
                  <span className="text-[#8A8F98] font-sans">
                    Proposed Test: <b className="text-[#F4F4F6] font-medium">{item.experiment.name || item.experiment.id}</b>
                  </span>

                  {hasRealRunAction && onRunExperiment && (
                    <button
                      type="button"
                      onClick={() => onRunExperiment(item.experiment)}
                      className="px-3 py-1 rounded-lg bg-[#FF6500] hover:bg-[#FF302A] text-white text-xs font-semibold btn-transition cursor-pointer font-sans"
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
