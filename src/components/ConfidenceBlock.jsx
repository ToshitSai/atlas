import React, { useState } from 'react';

/** Concise evidence disclosure, never a chain-of-thought or fake precision score. */
export default function ConfidenceBlock({ confidence, checking = false }) {
  const [open, setOpen] = useState(false);
  if (checking && !confidence) return <section className="mt-5 min-h-[104px] rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-alt)] px-4 py-3 text-[var(--text-main)]" aria-label="Confidence assessment"><div className="text-[13px] font-semibold">Confidence</div><div className="mt-3 text-sm text-[var(--text-secondary)]">Checking sources...</div><div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-[var(--border-subtle)]"><div className="h-full w-1/3 rounded-full bg-[var(--accent-amber)] animate-pulse" /></div></section>;
  if (!confidence?.overall?.level) return null;
  const level = confidence.overall.level;
  const claim = confidence.claims?.[0];
  const isHypothesis = claim?.kind === 'hypothesis';
  const percentage = Number.isFinite(Number(confidence.overall.percentage)) ? Math.round(Number(confidence.overall.percentage)) : null;
  const label = 'Confidence';
  return <section className="mt-5 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-alt)] px-4 py-3 text-[var(--text-main)]" aria-label="Confidence assessment">
    <div className="flex items-center justify-between gap-3"><span className="text-[13px] font-semibold">{label}</span><button type="button" title="Evidence strength based on sources and checks. Not a guarantee of correctness." aria-expanded={open} onClick={() => setOpen(!open)} className="text-sm text-[var(--text-secondary)] hover:text-[var(--text-main)] underline underline-offset-2">{open ? 'Hide details' : 'Why this score?'}</button></div>
    {isHypothesis ? <span className="mt-2 inline-flex rounded-full border border-[var(--border-subtle)] px-2 py-1 text-sm text-[var(--text-secondary)]">Hypothesis: proposed</span> : <div className="mt-2 text-2xl font-semibold leading-none">{percentage !== null ? `${percentage}%` : level} <span className="text-base font-medium text-[var(--text-secondary)]">{percentage !== null ? level : ''}</span></div>}
    {!isHypothesis && percentage !== null && <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-[var(--border-subtle)]"><div className="h-full rounded-full bg-[var(--accent-amber)]" style={{ width: `${percentage}%` }} /></div>}
    {(level !== 'high' || open) && confidence.basis?.length > 0 && <p className="mt-2 text-sm text-[var(--text-secondary)]">Because: {confidence.basis.join('; ').replace(/\.+$/, '')}.</p>}
    {confidence.math_check && <p className="mt-2 text-sm text-[var(--text-secondary)]">Numerically checked: {confidence.math_check.status === 'passed' ? 'passed' : 'failed'}</p>}
    {open && confidence.verification?.length > 0 && <p className="mt-2 text-sm text-[var(--text-secondary)]">To verify: {confidence.verification[0]}</p>}
    {open && confidence.unknown && <p className="mt-2 text-sm text-[var(--text-secondary)]">{confidence.unknown}</p>}
    {open && confidence.components && <div className="mt-3 space-y-1 text-sm text-[var(--text-secondary)]">{Object.entries(confidence.components).map(([key, value]) => <div key={key} className="flex justify-between gap-3"><span>{({ source_coverage: 'Sources found', source_quality: 'Source quality', agreement: 'Sources agree', claim_verification: 'Claims verified', relevance_recency: 'Freshness' }[key] || key.replaceAll('_', ' '))}</span><span>{value == null ? 'Not applicable' : `${Math.round(Number(value) * 100)}%`}</span></div>)}{confidence.claims?.length > 0 && <div className="mt-2">Claims checked: {confidence.claims.filter((claim) => claim.verified).length} of {confidence.claims.length}</div>}{confidence.caps?.length > 0 && <div className="mt-2">Caps applied: {confidence.caps.map((cap) => cap.reason.replaceAll('_', ' ')).join(', ')}.</div>}</div>}
    {open && confidence.caps?.length > 0 && <div className="mt-2 text-sm text-[var(--text-secondary)]">Caps applied: {confidence.caps.map((cap) => cap.reason.replaceAll('_', ' ')).join(', ')}.</div>}
  </section>;
}
