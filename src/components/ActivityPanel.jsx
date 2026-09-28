import React, { useState } from 'react';

/** Safe, high-level work status only. Never renders prompts, reasoning, or tool inputs. */
export default function ActivityPanel({ activities = [], running = false, startedAt }) {
  const [expanded, setExpanded] = useState(running);
  const elapsed = startedAt ? Math.max(1, Math.round((Date.now() - startedAt) / 1000)) : null;
  const shown = running
    ? [{ id: 'understanding', label: 'Understanding your question', status: 'running' }]
    : activities;
  if (!shown.length) return null;

  const icon = (status) => status === 'completed' ? '✓' : status === 'failed' ? '!' : '●';
  const color = (status) => status === 'completed' ? 'text-emerald-400' : status === 'failed' ? 'text-rose-400' : 'text-cyan-400 animate-pulse';

  return (
    <section className="rounded-xl border border-[#1E293B] bg-[#0B0F17] px-3 py-2.5 text-xs" aria-live="polite" aria-label="Assistant activity">
      <button type="button" onClick={() => setExpanded(value => !value)} className="w-full flex items-center justify-between gap-3 text-left text-slate-300">
        <span className="font-medium">{running ? 'Working…' : `Worked${elapsed ? ` for ${elapsed}s` : ''} · ${shown.length} step${shown.length === 1 ? '' : 's'}`}</span>
        <span className="text-slate-500">{expanded ? 'Hide' : 'Show'} activity</span>
      </button>
      {expanded && <div className="mt-2 space-y-1.5">
        {shown.map(step => <div className="flex items-center gap-2" key={step.id || step.label}>
          <span className={`font-bold ${color(step.status)}`}>{icon(step.status)}</span>
          <span className={step.status === 'running' ? 'text-cyan-300' : step.status === 'failed' ? 'text-rose-300' : 'text-slate-300'}>{step.label}</span>
        </div>)}
      </div>}
    </section>
  );
}
