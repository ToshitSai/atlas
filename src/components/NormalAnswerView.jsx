import React, { useEffect, useRef, useState } from 'react';
import ProgressiveMarkdown from './ProgressiveMarkdown';

/** Focused direct-answer thread, without document-style Question/Answer cards. */
export default function NormalAnswerView({ userQuestion = '', answer = '', sources = [], confidence = null, isLoading = false, turns = [], onRetry }) {
  const scrollRef = useRef(null);
  const previousAnswerLength = useRef(0);
  const [showJump, setShowJump] = useState(false);
  const visibleTurns = turns.length ? turns : [{ id: 'current', question: userQuestion, answer, sources, confidence, isLoading }];
  useEffect(() => {
    const node = scrollRef.current;
    if (!node) return;
    const nearBottom = node.scrollHeight - node.scrollTop - node.clientHeight <= 80;
    if (previousAnswerLength.current > 0 && answer.length > previousAnswerLength.current && nearBottom) {
      node.scrollTop = node.scrollHeight;
    }
    previousAnswerLength.current = answer.length;
    const onScroll = () => setShowJump(node.scrollHeight - node.scrollTop - node.clientHeight > 80);
    node.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
    return () => node.removeEventListener('scroll', onScroll);
  }, [answer, turns.length]);
  return (
    <div ref={scrollRef} className="chat-scroll-area relative flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 max-w-3xl lg:max-w-4xl mx-auto w-full space-y-8 animate-panel-entrance select-none font-sans pb-[calc(8rem+24px)] text-[var(--text-body)]">
      {visibleTurns.map((turn) => {
        const loading = Boolean(turn.isLoading);
        return <React.Fragment key={turn.id}>
          <article className="ml-auto max-w-[90%] sm:max-w-[78%] flex justify-end gap-2.5">
            <div className="bg-[var(--surface-alt)] rounded-2xl rounded-tr-md px-4 py-3 text-sm text-[var(--text-body)] leading-relaxed break-words overflow-wrap-anywhere">{turn.question}</div>
            <div className="mt-0.5 w-7 h-7 rounded-full border border-[#E3E0D8] bg-[#FAF9F6] text-[10px] font-sans text-[#7A8794] flex items-center justify-center shrink-0" aria-label="You">Y</div>
          </article>
      <article className="flex items-start" style={{ overflowAnchor: 'none' }}>
            <div className="min-w-0 flex-1 pt-0.5 text-[15px] text-[var(--text-body)] leading-7 break-words overflow-wrap-anywhere">
              <div className="mb-3 flex items-center gap-2 text-sm">
                <span className="font-semibold text-[var(--text-main)]">Atlas</span>
              </div>
              {loading && !turn.answer ? <AnswerSkeleton /> : <ProgressiveMarkdown content={turn.answer || ''} streaming={loading} instant={Boolean(turn.loadedFromHistory)} deliveryPath={turn.loadedFromHistory ? 'loaded from history' : 'new answer'} />}
              {turn.stopped && <p className="mt-2 text-sm text-[var(--text-secondary)]" role="status">Stopped</p>}
              {!loading && turn.answer && <div className="mt-2 text-[11px] text-[var(--text-muted)]">{turn.sources?.length ? `Live web search - ${turn.sources.length} source${turn.sources.length === 1 ? '' : 's'}` : 'From general knowledge'}</div>}
              {turn.error && <div className="mt-2 flex items-center gap-2 text-sm text-[var(--text-secondary)]"><span>Unable to finish this answer: {turn.error}</span>{onRetry && <button type="button" onClick={() => onRetry(turn.question)} className="rounded-md border border-[var(--border-subtle)] px-2 py-1 text-xs hover:bg-[var(--surface-hover)]">Retry</button>}</div>}
              {turn.sources?.length > 0 && !loading && (
              <section className="mt-5 pt-4 border-t border-[var(--border-subtle)] space-y-2">
              <div className="text-[11px] font-sans uppercase tracking-wide text-[var(--text-secondary)]">Sources</div>
                  <div className="space-y-1.5">
                  {turn.sources.map((src, idx) => (
                  <div key={idx} className="text-xs flex items-center gap-2"><span className="source-status-dot" aria-hidden="true" /><a href={src.url} target="_blank" rel="noopener noreferrer" className="text-[var(--accent-amber)] underline underline-offset-2 transition-colors truncate">{src.title || src.url}</a><span className="text-[var(--text-muted)] shrink-0">{src.publishedAt || src.year ? `Published ${src.publishedAt || src.year}` : ''}{src.retrievedAt ? ` · Retrieved ${src.retrievedAt}` : ''}</span></div>
                ))}
              </div>
            </section>
              )}
            </div>
          </article>
        </React.Fragment>;
      })}
      {showJump && <button type="button" onClick={() => { scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' }); setShowJump(false); }} className="sticky bottom-4 left-1/2 -translate-x-1/2 rounded-full border border-[var(--border-subtle)] bg-[var(--surface)] px-3 py-1.5 text-sm text-[var(--text-secondary)] shadow-sm">Jump to latest</button>}
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
