import React, { useState, useEffect, useRef } from 'react';

/**
 * Question Composer:
 * Compact, polished command area anchored near the bottom of the center column.
 * Palette: #141416 composer background, #242424 borders, #FF6500 small send button (28px x 30px with 16px icon).
 * Features: Cmd/Ctrl+K focus, AUTO mode badge, preserving text on error, preventing duplicate sends.
 */
export default function QuestionComposer({
  onSubmit,
  isPending = false,
  backendConnected = false,
  errorFeedback = null,
}) {
  const [text, setText] = useState('');
  const textareaRef = useRef(null);

  // Cmd/Ctrl+K keyboard shortcut to focus the input
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        textareaRef.current?.focus();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleSubmit = (e) => {
    if (e) e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || isPending) return;

    // Send the query. Entered text is preserved in `text` if submission fails;
    // onSubmit caller handles clearing on success.
    onSubmit(trimmed, () => setText(''));
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="w-full bg-[#141416] border border-[#242424] rounded-lg p-2.5 shadow-lg select-none">
      <form onSubmit={handleSubmit} className="flex flex-col gap-2">
        {/* Connection & Error Feedback */}
        {!backendConnected && (
          <div className="text-[11px] font-mono text-[#F87171] px-1 pb-1 flex items-center justify-between">
            <span>Research service not configured. No investigation or experiment has started.</span>
          </div>
        )}

        {errorFeedback && (
          <div className="text-[11px] font-mono text-[#F87171] px-1 pb-1">
            {errorFeedback}
          </div>
        )}

        {/* Input Area + Action Row */}
        <div className="relative flex items-start gap-2">
          <textarea
            ref={textareaRef}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Investigate why my model has low recall…"
            rows={2}
            disabled={isPending}
            aria-label="Research question input"
            className="flex-1 bg-[#080808] border border-[#242424] rounded px-3 py-2 text-sm text-[#F4F4F6] placeholder-[#8A8F98] resize-none focus:outline-none input-focus-orange font-sans leading-relaxed disabled:opacity-50"
          />

          {/* Right Action Stack (AUTO badge + Small Send Button) */}
          <div className="flex flex-col items-end gap-1.5 shrink-0 pt-0.5">
            {/* Subtle AUTO mode indicator */}
            <span
              title="Automatic routing mode enabled"
              className="text-[10px] font-mono text-[#8A8F98] bg-[#080808] border border-[#242424] px-1.5 py-0.5 rounded flex items-center gap-1 shrink-0"
            >
              <span className="w-1.5 h-1.5 rounded-full bg-[#FF6500]" />
              AUTO
            </span>

            {/* Small Orange Send Button (approx 28px wide × 30px high, 16px icon) */}
            <button
              type="submit"
              disabled={!text.trim() || isPending}
              aria-label="Send question"
              title="Send question (Enter)"
              className={`w-[28px] h-[30px] rounded flex items-center justify-center btn-transition shrink-0 ${
                text.trim() && !isPending
                  ? 'bg-[#FF6500] hover:bg-[#FF302A] text-white cursor-pointer shadow-sm'
                  : 'bg-[#242424] text-[#8A8F98] cursor-not-allowed'
              }`}
            >
              {isPending ? (
                <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                <svg className="w-[16px] h-[16px]" fill="none" stroke="currentColor" strokeWidth="2.2" viewBox="0 0 24 24" aria-hidden="true">
                  <line x1="22" y1="2" x2="11" y2="13" />
                  <polygon points="22 2 15 22 11 13 2 9 22 2" />
                </svg>
              )}
            </button>
          </div>
        </div>

        {/* Keyboard Focus Hint & Submission Note */}
        <div className="flex items-center justify-between text-[10px] text-[#8A8F98] px-1 pt-0.5 font-mono">
          <span>Press <kbd className="px-1 py-0.2 rounded bg-[#080808] border border-[#242424]">Cmd/Ctrl+K</kbd> to focus</span>
          <span>Shift+Enter for newline</span>
        </div>
      </form>
    </div>
  );
}
