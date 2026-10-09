import React, { useEffect, useRef, useState } from 'react';
import ProgressiveMarkdown from './ProgressiveMarkdown';

/** Focused direct-answer thread, without document-style Question/Answer cards. */
export default function NormalAnswerView({ userQuestion = '', answer = '', sources = [], confidence = null, isLoading = false, turns = [], onRetry, onEdit, onRegenerate }) {
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
      {visibleTurns.map((turn, turnIndex) => {
        const loading = Boolean(turn.isLoading);
        return <React.Fragment key={turn.id}>
          <UserMessage turn={turn} turnIndex={turnIndex} onEdit={onEdit} />
      <article className="flex items-start" style={{ overflowAnchor: 'none' }}>
            <div className="min-w-0 flex-1 pt-0.5 text-[15px] text-[var(--text-body)] leading-7 break-words overflow-wrap-anywhere">
              <div className="mb-3 flex items-center gap-2 text-sm">
                <span className="font-semibold text-[var(--text-main)]">Atlas</span>
              </div>
              {loading && !turn.answer ? <AnswerSkeleton /> : <ProgressiveMarkdown content={turn.answer || ''} streaming={loading} instant={Boolean(turn.loadedFromHistory)} deliveryPath={turn.loadedFromHistory ? 'loaded from history' : 'new answer'} />}
              {turn.stopped && <p className="mt-2 text-sm text-[var(--text-secondary)]" role="status">Stopped</p>}
              {!loading && turn.answer && <><div className="mt-2 text-[11px] text-[var(--text-muted)]">{turn.sources?.length ? `Live web search - ${turn.sources.length} source${turn.sources.length === 1 ? '' : 's'}` : 'From general knowledge'}</div>{onRegenerate && <button type="button" className="mt-2 message-regenerate-button" onClick={() => onRegenerate(turn.question, turn.answer)} aria-label="Regenerate answer" title="Regenerate answer">Regenerate</button>}</>}
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

function CopyIcon({ check = false }) { return check ? <svg aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="m5 12 4 4L19 6"/></svg> : <svg aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>; }
function EditIcon() { return <svg aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4Z"/></svg>; }

function UserMessage({ turn, turnIndex, onEdit }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(turn.question || '');
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState(false);
  const editRef = useRef(null);
  const editButtonRef = useRef(null);
  useEffect(() => { if (editing) { editRef.current?.focus(); editRef.current?.setSelectionRange(draft.length, draft.length); } }, [editing]);
  const copy = async () => {
    try { if (navigator.clipboard?.writeText) await navigator.clipboard.writeText(turn.question || ''); else throw new Error('clipboard unavailable'); }
    catch { try { const area = document.createElement('textarea'); area.value = turn.question || ''; area.style.position = 'fixed'; area.style.opacity = '0'; document.body.appendChild(area); area.focus(); area.select(); if (!document.execCommand('copy')) throw new Error('copy failed'); area.remove(); } catch { setCopyError(true); window.setTimeout(() => setCopyError(false), 2000); return; } }
    setCopied(true); window.setTimeout(() => setCopied(false), 1500);
  };
  const cancel = () => { setDraft(turn.question || ''); setEditing(false); window.setTimeout(() => editButtonRef.current?.focus(), 0); };
  const send = () => { const value = draft.trim(); if (!value || value === turn.question?.trim()) return; setEditing(false); onEdit?.(turnIndex, value); };
  return <article className="user-message-row ml-auto max-w-[90%] sm:max-w-[78%] flex justify-end gap-2.5">
    <div className="min-w-0 flex flex-col items-end">
      {editing ? <div className="w-full rounded-2xl bg-[var(--surface-alt)] p-3"><textarea ref={editRef} value={draft} onChange={(e) => setDraft(e.target.value)} onKeyDown={(e) => { if (e.key === 'Escape') cancel(); if ((e.ctrlKey || e.metaKey) && e.key === 'Enter' && !e.nativeEvent.isComposing) send(); }} onCompositionStart={(e) => { e.currentTarget.dataset.composing = '1'; }} onCompositionEnd={(e) => { delete e.currentTarget.dataset.composing; }} className="w-full resize-y bg-transparent text-sm leading-relaxed outline-none" style={{ maxHeight: '40dvh' }} aria-label="Edit message" /> <div className="mt-2 flex justify-end gap-2"><button type="button" onClick={cancel} className="message-edit-secondary">Cancel</button><button type="button" disabled={!draft.trim() || draft.trim() === turn.question?.trim()} onClick={send} className="message-edit-primary">Send</button></div></div> : <div className="bg-[var(--surface-alt)] rounded-2xl rounded-tr-md px-4 py-3 text-sm text-[var(--text-body)] leading-relaxed break-words overflow-wrap-anywhere">{turn.question}</div>}
      {!editing && <div className="message-actions" aria-live="polite"><button type="button" className="message-action-button" onClick={copy} aria-label="Copy message" title={copied ? 'Copied' : copyError ? "Couldn't copy" : 'Copy message'}><CopyIcon check={copied} /></button><button ref={editButtonRef} type="button" className="message-action-button" onClick={() => { if (turn.isLoading) onEdit?.(turnIndex, turn.question); else { setDraft(turn.question || ''); setEditing(true); } }} aria-label="Edit message" title="Edit message"><EditIcon /></button>{copied && <span className="sr-only">Copied</span>}{copyError && <span className="sr-only">Couldn't copy</span>}</div>}
    </div>
    <div className="mt-0.5 w-7 h-7 rounded-full border border-[#E3E0D8] bg-[#FAF9F6] text-[10px] font-sans text-[#7A8794] flex items-center justify-center shrink-0" aria-label="You">Y</div>
  </article>;
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
