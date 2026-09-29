import React, { useState } from 'react';

/** Safe, high-level work status only. Never renders prompts, reasoning, or tool inputs. */
export default function ActivityPanel({ activities = [], running = false, startedAt }) {
  // Keep real completed activity visible by default. Collapsing is purely a
  // presentation choice and never clears or interrupts the underlying work.
  const [expanded, setExpanded] = useState(true);
  const elapsed = startedAt ? Math.max(1, Math.round((Date.now() - startedAt) / 1000)) : null;
  // While a request is genuinely in flight, the UI can truthfully show its
  // current client-side stage. Once it completes, only server-produced
  // pipeline/router events remain — never a fabricated completed history.
  const shown = running
    ? (activities.length
      ? activities
      : [{ id: 'request-understanding', label: 'Understanding your question', status: 'running', detail: 'Classifying the request before starting research.' }])
    : activities;
  if (!shown.length) return null;

  const icon = (status) => status === 'completed' ? '✓' : status === 'failed' ? '✕' : status === 'skipped' ? '—' : status === 'pending' ? '○' : '●';
  const color = (status) => status === 'completed' ? 'text-emerald-400' : status === 'failed' ? 'text-rose-400' : status === 'skipped' ? 'text-slate-500' : status === 'pending' ? 'text-slate-500' : 'text-cyan-400 animate-pulse';

  return (
    <section className="rounded-xl border border-[#1E293B] bg-[#0B0F17] px-3 py-2.5 text-xs" aria-live="polite" aria-label="Assistant activity">
      <button type="button" onClick={() => setExpanded(value => !value)} className="w-full flex items-center justify-between gap-3 text-left text-slate-300">
        <span className="font-medium">{running ? 'Working…' : `Worked${elapsed ? ` for ${elapsed}s` : ''} · ${shown.length} step${shown.length === 1 ? '' : 's'}`}</span>
        <span className="text-slate-500">{expanded ? 'Hide' : 'Show'} activity</span>
      </button>
      {expanded && <div className="mt-2 space-y-2 max-h-64 overflow-y-auto pr-1">
        {shown.map(step => <div className="flex items-start gap-2" key={step.id || `${step.stage}-${step.label}`}>
          <span className={`font-bold mt-px ${color(step.status)}`}>{icon(step.status)}</span>
          <div className="min-w-0">
            <div className={step.status === 'running' ? 'text-cyan-300' : step.status === 'failed' ? 'text-rose-300' : 'text-slate-300'}>{step.label}</div>
            {step.detail && <div className="mt-0.5 text-[11px] leading-relaxed text-slate-500">{step.detail}</div>}
          </div>
        </div>)}
      </div>}
    </section>
  );
}
