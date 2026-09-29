import React from 'react';

// Literature panel (brief §3 "42 relevant papers analyzed" — but only real ones).
// Renders the actual papers the Semantic Scholar / OpenAlex search returned, with
// links. Honest empty/unavailable states when the search found nothing or the
// literature API is not configured.

export default function LiteraturePanel({ literature = [], stageState }) {
  const count = (literature || []).length;

  if (!count) {
    const msg =
      stageState === 'NOT_CONFIGURED'
        ? 'Literature search API is not configured, so no papers were retrieved for this study.'
        : stageState === 'RUNNING'
          ? 'Searching literature…'
          : stageState === 'FAILED'
            ? 'Literature search failed. No papers were retrieved.'
            : 'No papers retrieved for this research goal.';
    return (
      <div className="bg-[#121722] border border-[#1E293B] rounded-2xl p-6 text-center">
        <p className="text-xs text-slate-500 italic">{msg}</p>
      </div>
    );
  }

  return (
    <div className="bg-[#121722] border border-[#1E293B] rounded-2xl p-4 sm:p-5 min-w-0">
      <div className="flex items-center justify-between border-b border-[#1E293B]/70 pb-3 mb-3">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">Literature Review</h3>
        <span className="text-[10px] font-mono text-cyan-400">{count} paper{count === 1 ? '' : 's'}</span>
      </div>
      <div className="space-y-2.5 min-w-0">
        {literature.map((p, i) => (
          <article key={p.paperId || i} className="p-3 rounded-xl bg-[#0B0F17] border border-[#1E293B] min-w-0 space-y-1">
            <div className="flex items-start justify-between gap-3">
              <h4 className="text-xs font-semibold text-slate-100 leading-snug break-words overflow-wrap-anywhere">
                {p.url ? (
                  <a href={p.url} target="_blank" rel="noopener noreferrer" className="hover:text-cyan-400 transition-colors">
                    {p.title}
                  </a>
                ) : (
                  p.title
                )}
              </h4>
              {p.year && <span className="shrink-0 text-[10px] font-mono text-slate-500">{p.year}</span>}
            </div>
            <p className="text-[10px] text-slate-500 break-words overflow-wrap-anywhere">
              {p.authors}{p.venue ? ` · ${p.venue}` : ''}
            </p>
            {p.abstract && (
              <p className="text-[11px] text-slate-400 leading-relaxed line-clamp-3 break-words overflow-wrap-anywhere">
                {p.abstract}
              </p>
            )}
          </article>
        ))}
      </div>
    </div>
  );
}
