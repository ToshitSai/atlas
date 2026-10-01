import React from 'react';
import ChatMarkdown from './ChatMarkdown';
import ConfidenceBlock from './ConfidenceBlock';
import AtlasLogo from './AtlasLogo';

/** Focused direct-answer thread, without document-style Question/Answer cards. */
export default function NormalAnswerView({ userQuestion = '', answer = '', sources = [], confidence = null, isLoading = false }) {
  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6 max-w-3xl mx-auto w-full space-y-7 animate-panel-entrance select-none font-sans pb-32">
      <article className="ml-auto max-w-[90%] sm:max-w-[78%] flex justify-end gap-2.5">
        <div className="bg-[#1B1B1B] rounded-2xl rounded-tr-md px-4 py-3 text-sm text-[#E8E5DF] leading-relaxed break-words overflow-wrap-anywhere">
          {userQuestion}
        </div>
        <div className="mt-0.5 w-7 h-7 rounded-full border border-[#353535] bg-[#181818] text-[10px] font-mono text-[#8A8884] flex items-center justify-center shrink-0" aria-label="You">Y</div>
      </article>

      <article className="flex items-start gap-3">
        <AtlasLogo className="mt-0.5 w-6 h-6 shrink-0" aria-label="Atlas" />
        <div className="min-w-0 flex-1 pt-0.5 text-sm text-[#E8E5DF] leading-relaxed break-words overflow-wrap-anywhere">
          {isLoading ? <AnswerSkeleton /> : <ChatMarkdown content={answer} />}
          {!isLoading && <ConfidenceBlock confidence={confidence} />}
          {sources.length > 0 && !isLoading && (
            <section className="mt-5 pt-4 border-t border-[#303030] space-y-2">
              <div className="text-[11px] font-mono uppercase tracking-wide text-[#8A8884]">Sources</div>
              <div className="space-y-1.5">
                {sources.map((src, idx) => (
                  <div key={idx} className="text-xs flex items-center gap-2"><span className="text-[#F15A3A]">•</span><a href={src.url} target="_blank" rel="noopener noreferrer" className="text-[#E8E5DF] hover:text-[#F15A3A] underline underline-offset-2 transition-colors truncate">{src.title || src.url}</a></div>
                ))}
              </div>
            </section>
          )}
        </div>
      </article>
    </div>
  );
}

function AnswerSkeleton() {
  return (
    <div className="space-y-3 py-1" role="status" aria-label="Atlas is thinking">
      <div className="flex items-center gap-2 text-xs text-[#8A8884] font-mono"><span className="w-1.5 h-1.5 rounded-full bg-[#F15A3A] animate-pulse" />Analyzing the question…</div>
      <div className="h-3 rounded bg-[#303030]/75 animate-pulse w-[92%]" />
      <div className="h-3 rounded bg-[#303030]/60 animate-pulse w-[78%]" />
      <div className="h-3 rounded bg-[#303030]/45 animate-pulse w-[64%]" />
    </div>
  );
}
