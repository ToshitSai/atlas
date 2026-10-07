import React, { useState } from 'react';

const tones = {
  high: 'text-[#17633A] border-[#9AD7B3] bg-[#F0FAF3]',
  medium: 'text-[#7A4B00] border-[#E7C77A] bg-[#FFF9E8]',
  low: 'text-[#8A3B12] border-[#E8B39A] bg-[#FFF3EC]',
};

/** Concise evidence disclosure, never a chain-of-thought or fake precision score. */
export default function ConfidenceBlock({ confidence }) {
  const [open, setOpen] = useState(false);
  if (!confidence?.overall?.level) return null;
  const level = confidence.overall.level;
  const claim = confidence.claims?.[0];
  const isHypothesis = claim?.kind === 'hypothesis';
  const percentage = Number.isFinite(Number(confidence.overall.percentage)) ? Math.round(Number(confidence.overall.percentage)) : null;
  const label = isHypothesis ? 'Hypothesis status: proposed' : `Confidence: ${level[0].toUpperCase()}${level.slice(1)}`;
  return <section className={`mt-5 rounded-lg border px-3 py-2.5 text-xs ${tones[level] || tones.medium}`} aria-label="Confidence assessment">
    <div className="flex items-center justify-between gap-3"><span className="font-mono font-medium">{label}</span><button type="button" onClick={() => setOpen(!open)} className="text-[#8A8884] hover:text-[#E8E5DF] underline underline-offset-2">{open ? 'Hide details' : 'Why this confidence?'}</button></div>
    {!isHypothesis && percentage !== null && <div className="mt-2 text-2xl font-semibold leading-none">{percentage}% <span className="text-sm font-normal">{level} confidence</span></div>}
    {(level !== 'high' || open) && confidence.basis?.length > 0 && <p className="mt-1.5 text-[#4B5563]">Because: {confidence.basis.join('; ')}.</p>}
    {open && confidence.verification?.length > 0 && <p className="mt-1.5 text-[#4B5563]">To verify: {confidence.verification[0]}</p>}
    {open && confidence.unknown && <p className="mt-1.5 text-[#4B5563]">{confidence.unknown}</p>}
  </section>;
}
