import React from 'react';
import { STAGE } from './researchModel';

// Vertical research pipeline timeline. Renders the 12 research stages with real
// per-stage state (○ pending · ● running · ✓ completed · ✕ failed · — unavailable)
// and honest detail lines derived from persisted backend results only.

const ICON = {
  [STAGE.COMPLETED]: { glyph: '✓', cls: 'text-emerald-400', ring: 'border-emerald-500/40 bg-emerald-500/10', label: 'Completed' },
  [STAGE.RUNNING]: { glyph: '●', cls: 'text-cyan-400', ring: 'border-cyan-500/50 bg-cyan-500/10', label: 'Running' },
  [STAGE.FAILED]: { glyph: '✕', cls: 'text-rose-400', ring: 'border-rose-500/40 bg-rose-500/10', label: 'Failed' },
  [STAGE.UNAVAILABLE]: { glyph: '—', cls: 'text-slate-500', ring: 'border-slate-700 bg-slate-800/40', label: 'Not configured' },
  [STAGE.PENDING]: { glyph: '○', cls: 'text-slate-600', ring: 'border-slate-800 bg-slate-900/40', label: 'Pending' },
};

export default function ResearchPipeline({ stages }) {
  return (
    <div className="bg-[#121722] border border-[#1E293B] rounded-2xl p-4 sm:p-5">
      <div className="flex items-center justify-between border-b border-[#1E293B]/70 pb-3 mb-3">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">Research Pipeline</h3>
        <span className="text-[10px] text-slate-500 font-mono">
          {stages.filter((s) => s.state === STAGE.COMPLETED).length}/{stages.length}
        </span>
      </div>

      <ol className="relative space-y-0" aria-label="Research pipeline progress">
        {stages.map((stage, i) => {
          const meta = ICON[stage.state] || ICON[STAGE.PENDING];
          const isLast = i === stages.length - 1;
          const active = stage.state === STAGE.RUNNING;
          return (
            <li key={stage.key} className="relative flex gap-3 min-w-0">
              {/* connector line */}
              {!isLast && (
                <span
                  aria-hidden="true"
                  className={`absolute left-[13px] top-7 w-px h-[calc(100%-1.25rem)] ${
                    stage.state === STAGE.COMPLETED ? 'bg-emerald-500/30' : 'bg-[#1E293B]'
                  }`}
                />
              )}
              {/* state marker */}
              <span
                className={`relative z-10 mt-0.5 shrink-0 w-7 h-7 rounded-full border flex items-center justify-center text-xs font-bold ${meta.ring} ${meta.cls} ${
                  active ? 'animate-pulse-slow' : ''
                }`}
                aria-label={meta.label}
                title={meta.label}
              >
                {active ? (
                  <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-ping" />
                ) : (
                  meta.glyph
                )}
              </span>

              <div className={`flex-1 min-w-0 pb-4 ${isLast ? 'pb-0' : ''}`}>
                <div className="flex items-center gap-2 flex-wrap min-w-0">
                  <span
                    className={`text-[13px] font-semibold truncate ${
                      stage.state === STAGE.COMPLETED
                        ? 'text-slate-200'
                        : active
                          ? 'text-cyan-300'
                          : stage.state === STAGE.FAILED
                            ? 'text-rose-300'
                            : 'text-slate-500'
                    }`}
                  >
                    {stage.label}
                  </span>
                  {stage.count && (
                    <span className="shrink-0 text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#0B0F17] border border-[#212B3B] text-cyan-400">
                      {stage.count}
                    </span>
                  )}
                </div>
                {stage.detail && (
                  <p
                    className={`text-[11px] mt-0.5 leading-relaxed break-words overflow-wrap-anywhere ${
                      active ? 'text-slate-400' : stage.state === STAGE.FAILED ? 'text-rose-400/80' : 'text-slate-500'
                    }`}
                  >
                    {stage.detail}
                  </p>
                )}
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
