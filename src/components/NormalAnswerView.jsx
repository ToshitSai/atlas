import React from 'react';
import ChatMarkdown from './ChatMarkdown';
import ConfidenceBlock from './ConfidenceBlock';
import AtlasLogo from './AtlasLogo';

/** Focused direct-answer thread, without document-style Question/Answer cards. */
export default function NormalAnswerView({ userQuestion = '', answer = '', sources = [], confidence = null, isLoading = false, turns = [] }) {
  const visibleTurns = turns.length ? turns : [{ id: 'current', question: userQuestion, answer, sources, confidence, isLoading }];
  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 max-w-3xl lg:max-w-4xl mx-auto w-full space-y-8 animate-panel-entrance select-none font-sans pb-32 text-[#19324A]">
      {visibleTurns.map((turn) => {
        const loading = Boolean(turn.isLoading);
        return <React.Fragment key={turn.id}>
          <article className="ml-auto max-w-[90%] sm:max-w-[78%] flex justify-end gap-2.5">
            <div className="bg-[#F1F0EB] rounded-2xl rounded-tr-md px-4 py-3 text-sm text-[#19324A] leading-relaxed break-words overflow-wrap-anywhere">{turn.question}</div>
            <div className="mt-0.5 w-7 h-7 rounded-full border border-[#E3E0D8] bg-[#FAF9F6] text-[10px] font-sans text-[#7A8794] flex items-center justify-center shrink-0" aria-label="You">Y</div>
          </article>
          <article className="flex items-start gap-3">
            <div className="mt-0.5 w-8 h-8 rounded-xl bg-[#FACC00] flex items-center justify-center shrink-0" aria-label="Atlas">
              <AtlasLogo className="w-5 h-5" />
            </div>
            <div className="min-w-0 flex-1 pt-0.5 text-[15px] text-[#19324A] leading-7 break-words overflow-wrap-anywhere">
              <div className="mb-3 flex items-center gap-2 text-sm">
                <span className="font-semibold text-[#19324A]">Atlas</span>
              </div>
              {loading ? <AnswerSkeleton /> : <ChatMarkdown content={turn.answer || ''} />}
              {!loading && <ConfidenceBlock confidence={turn.confidence || null} />}
              {turn.sources?.length > 0 && !loading && (
            <section className="mt-5 pt-4 border-t border-[#E3E0D8] space-y-2">
              <div className="text-[11px] font-sans uppercase tracking-wide text-[#7A8794]">Sources</div>
              <div className="space-y-1.5">
                  {turn.sources.map((src, idx) => (
                  <div key={idx} className="text-xs flex items-center gap-2"><span className="text-[#EAB308]">•</span><a href={src.url} target="_blank" rel="noopener noreferrer" className="text-[#19324A] hover:text-[#B8890A] underline underline-offset-2 transition-colors truncate">{src.title || src.url}</a></div>
                ))}
              </div>
            </section>
              )}
            </div>
          </article>
        </React.Fragment>;
      })}
    </div>
  );
}

function AnswerSkeleton() {
  return (
    <div className="space-y-3 py-1" role="status" aria-label="Atlas is thinking">
      <div className="flex items-center gap-2 text-xs text-[#4B5563]"><span className="w-3.5 h-3.5 rounded-full border-2 border-[#B8890A] border-t-transparent animate-spin" />Preparing a verified answer…</div>
      <div className="h-3 rounded bg-[#E8E5DE] animate-pulse w-[92%]" />
      <div className="h-3 rounded bg-[#EEECE6] animate-pulse w-[78%]" />
      <div className="h-3 rounded bg-[#F3F1EC] animate-pulse w-[64%]" />
    </div>
  );
}
