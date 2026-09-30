import React from 'react';

/**
 * Functional Experiments View displaying actual recorded experiments with clean typography.
 */
export default function ExperimentsView({ experiments = [], currentExperiment = null }) {
  const allExps = currentExperiment ? [currentExperiment, ...experiments.filter(e => e.id !== currentExperiment.id)] : experiments;

  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4 max-w-4xl mx-auto w-full select-none font-sans min-w-0 pb-32 animate-panel-entrance">
      <div className="border-b border-[#242424] pb-3 flex items-center justify-between font-sans">
        <div>
          <h2 className="text-base font-semibold text-[#F4F4F6] font-sans flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#FF6500]" />
            Experiments Directory
          </h2>
          <p className="text-xs text-[#8A8F98] mt-0.5 font-sans">
            Recorded model evaluation runs and configuration details
          </p>
        </div>
        <span className="text-xs font-medium text-[#8A8F98] px-2.5 py-1 bg-[#141416] border border-[#242424] rounded-full font-sans">
          Total: {allExps.length}
        </span>
      </div>

      {allExps.length === 0 ? (
        <div className="bg-[#0B0B0B] border border-[#242424] rounded-xl p-8 text-center space-y-2 font-sans">
          <p className="text-xs text-[#8A8F98] font-sans">
            No experiment runs have been recorded in this session yet.
          </p>
          <p className="text-xs text-[#8A8F98] font-sans">
            Submit a research request to launch automated experiments.
          </p>
        </div>
      ) : (
        <div className="space-y-3 font-sans">
          {allExps.map((exp, idx) => (
            <div key={exp.id || idx} className="bg-[#0B0B0B] border border-[#242424] rounded-xl p-4 space-y-3 font-sans">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#242424] pb-2.5 font-sans">
                <div className="flex items-center gap-2 font-sans">
                  <span className="text-xs font-mono font-medium text-[#FF6500]">#{exp.id || `EXP-${idx + 1}`}</span>
                  <span className="text-sm font-semibold text-[#F4F4F6] font-sans">{exp.name || 'Model Training Run'}</span>
                </div>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-[#141416] border border-[#242424] text-[#FF6500] font-sans">
                  {exp.status || 'Completed'}
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 text-xs font-sans">
                <div className="p-3 rounded-lg bg-[#101012] border border-[#242424] font-sans">
                  <span className="text-[#8A8F98] text-xs font-medium block">Dataset</span>
                  <span className="text-[#F4F4F6] truncate block font-medium mt-0.5">{exp.dataset || 'N/A'}</span>
                </div>
                <div className="p-3 rounded-lg bg-[#101012] border border-[#242424] font-sans">
                  <span className="text-[#8A8F98] text-xs font-medium block">Validation</span>
                  <span className="text-[#F4F4F6] truncate block font-medium mt-0.5">{exp.validation || 'N/A'}</span>
                </div>
                <div className="p-3 rounded-lg bg-[#101012] border border-[#242424] font-sans">
                  <span className="text-[#8A8F98] text-xs font-medium block">Configuration</span>
                  <span className="text-[#F4F4F6] truncate block font-medium mt-0.5">{exp.config || 'Default'}</span>
                </div>
              </div>

              {exp.metrics && (
                <div className="space-y-1.5 font-sans pt-1">
                  <span className="text-xs text-[#8A8F98] font-medium block font-sans">Measured Metrics</span>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-sans">
                    {Object.entries(exp.metrics).map(([k, v]) => (
                      <div key={k} className="p-2.5 rounded-lg bg-[#101012] border border-[#242424] text-center font-sans">
                        <div className="text-xs text-[#8A8F98] font-medium font-sans">{k}</div>
                        <div className="text-sm font-semibold text-[#F4F4F6] font-sans mt-0.5">
                          {typeof v === 'number' ? v.toFixed(4) : String(v)}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
