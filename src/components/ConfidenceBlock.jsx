import React, { useState } from 'react';

const tones = {
  high: 'text-emerald-300 border-emerald-500/25 bg-emerald-500/5',
  medium: 'text-[#E8E5DF] border-[#F15A3A]/30 bg-[#F15A3A]/5',
  low: 'text-amber-300 border-amber-500/25 bg-amber-500/5',
};

/** Concise evidence disclosure, never a chain-of-thought or fake precision score. */
export default function ConfidenceBlock({ confidence }) {
  const [open, setOpen] = useState(false);
  if (!confidence?.overall?.level) return null;
  const level = confidence.overall.level;
  const claim = confidence.claims?.[0];
  const isHypothesis = claim?.kind === 'hypothesis';
  const label = isHypothesis ? 'Hypothesis status: proposed' : `Confidence: ${level[0].toUpperCase()}${level.slice(1)}${confidence.overall.band ? ` (${confidence.overall.band})` : ''}`;
  return <section className={`mt-5 rounded-lg border px-3 py-2.5 text-xs ${tones[level] || tones.medium}`} aria-label="Confidence assessment">
    <div className="flex items-center justify-between gap-3"><span className="font-mono font-medium">{label}</span><button type="button" onClick={() => setOpen(!open)} className="text-[#8A8884] hover:text-[#E8E5DF] underline underline-offset-2">{open ? 'Hide details' : 'Why this confidence?'}</button></div>
    {(level !== 'high' || open) && confidence.basis?.length > 0 && <p className="mt-1.5 text-[#8A8884]">Because: {confidence.basis.join('; ')}.</p>}
    {open && confidence.verification?.length > 0 && <p className="mt-1.5 text-[#8A8884]">To verify: {confidence.verification[0]}</p>}
    {open && confidence.unknown && <p className="mt-1.5 text-[#8A8884]">{confidence.unknown}</p>}
  </section>;
}
