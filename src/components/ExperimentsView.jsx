import React from 'react';

/**
 * Functional Experiments View displaying actual recorded experiments.
 */
export default function ExperimentsView({ experiments = [], currentExperiment = null }) {
  const allExps = currentExperiment ? [currentExperiment, ...experiments.filter(e => e.id !== currentExperiment.id)] : experiments;

  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4 max-w-4xl mx-auto w-full select-none font-sans min-w-0 pb-32 animate-panel-entrance">
      <div className="border-b border-[#242424] pb-3 flex items-center justify-between">
        <div>
          <h2 className="text-base font-mono font-bold text-[#F4F4F6] uppercase flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#FF6500]" />
            Experiments Directory
          </h2>
          <p className="text-xs text-[#8A8F98] mt-0.5">
            Recorded model evaluation runs and configuration details
          </p>
        </div>
        <span className="text-xs font-mono text-[#8A8F98] px-2 py-1 bg-[#141416] border border-[#242424] rounded">
          Total: {allExps.length}
        </span>
      </div>

      {allExps.length === 0 ? (
        <div className="bg-[#0B0B0B] border border-[#242424] rounded p-8 text-center space-y-2">
          <p className="text-xs text-[#8A8F98] italic font-mono">
            No experiment runs have been recorded in this session yet.
          </p>
          <p className="text-xs text-[#8A8F98]">
            Submit a research request to launch automated experiments.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {allExps.map((exp, idx) => (
            <div key={exp.id || idx} className="bg-[#0B0B0B] border border-[#242424] rounded p-4 space-y-3 font-mono">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#242424] pb-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-[#FF6500]">#{exp.id || `EXP-${idx + 1}`}</span>
                  <span className="text-sm font-semibold text-[#F4F4F6]">{exp.name || 'Model Training Run'}</span>
                </div>
                <span className="px-2 py-0.5 rounded text-[10px] bg-[#141416] border border-[#242424] text-[#FF6500]">
                  {exp.status || 'COMPLETED'}
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
                <div className="p-2 rounded bg-[#101012] border border-[#242424]">
                  <span className="text-[#8A8F98] text-[10px] block uppercase">Dataset</span>
                  <span className="text-[#F4F4F6] truncate block">{exp.dataset || 'N/A'}</span>
                </div>
                <div className="p-2 rounded bg-[#101012] border border-[#242424]">
                  <span className="text-[#8A8F98] text-[10px] block uppercase">Validation</span>
                  <span className="text-[#F4F4F6] truncate block">{exp.validation || 'N/A'}</span>
                </div>
                <div className="p-2 rounded bg-[#101012] border border-[#242424]">
                  <span className="text-[#8A8F98] text-[10px] block uppercase">Configuration</span>
                  <span className="text-[#F4F4F6] truncate block">{exp.config || 'Default'}</span>
                </div>
              </div>

              {exp.metrics && (
                <div className="space-y-1">
                  <span className="text-[10px] text-[#8A8F98] uppercase">Measured Metrics</span>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                    {Object.entries(exp.metrics).map(([k, v]) => (
                      <div key={k} className="p-1.5 rounded bg-[#101012] border border-[#242424] text-center">
                        <div className="text-[9px] text-[#8A8F98] uppercase">{k}</div>
                        <div className="text-xs font-bold text-[#F4F4F6]">
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
