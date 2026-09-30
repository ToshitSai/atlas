import React, { useState, useEffect, useRef } from 'react';

/**
 * Question Composer:
 * Redesigned to match the clean, single-bar capsule design (Image 2 reference).
 * Features:
 * - Rounded pill container (`rounded-2xl`) with dark surface `#1C1C20`
 * - Left `+` quick access trigger button
 * - Clean borderless auto-resizing text field
 * - Right rounded action button (white pill button with icon like Image 2 reference)
 * - Quiet `AUTO` routing badge inside the bar
 * - Cmd/Ctrl+K keyboard shortcut focus support
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

  // Auto-adjust textarea height up to a max
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  }, [text]);

  const handleSubmit = (e) => {
    if (e) e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || isPending) return;

    onSubmit(trimmed, () => setText(''));
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="w-full font-sans select-none space-y-1.5">
      {/* Feedback alerts if disconnected or failed */}
      {!backendConnected && (
        <div className="text-[11px] font-mono text-[#F87171] px-3 pb-0.5 flex items-center justify-between">
          <span>Research service not configured. No investigation or experiment has started.</span>
        </div>
      )}

      {errorFeedback && (
        <div className="text-[11px] font-mono text-[#F87171] px-3 pb-0.5">
          {errorFeedback}
        </div>
      )}

      {/* Main Single Pill Bar Container (Image 2 style) */}
      <form
        onSubmit={handleSubmit}
        className="w-full bg-[#1C1C20] hover:bg-[#202025] border border-[#2E2E34] focus-within:border-[#FF6500] focus-within:ring-1 focus-within:ring-[#FF6500]/30 rounded-2xl px-4 py-2.5 shadow-2xl flex items-center gap-3 transition-all"
      >
        {/* Left "+" Icon / Quick Access Trigger */}
        <button
          type="button"
          onClick={() => textareaRef.current?.focus()}
          className="text-[#8A8F98] hover:text-[#F4F4F6] text-xl font-light leading-none shrink-0 transition-colors cursor-pointer p-0.5"
          title="Quick access commands"
          aria-label="Quick access"
        >
          +
        </button>

        {/* Input Textarea */}
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type / for quick access or ask a research question..."
          rows={1}
          disabled={isPending}
          aria-label="Research question input"
          className="flex-1 bg-transparent text-sm text-[#F4F4F6] placeholder-[#71717A] focus:outline-none resize-none overflow-y-auto font-sans leading-relaxed min-h-[24px] max-h-[120px] py-0.5"
        />

        {/* Right Stack: Action Button (Image 2 style) */}
        <div className="flex items-center gap-2 shrink-0">
          {/* Action Button (Image 2 style: clean rounded white button with orange mic icon) */}
          <button
            type="submit"
            disabled={!text.trim() || isPending}
            aria-label="Send question"
            title="Send question (Enter)"
            className={`w-9 h-9 rounded-xl flex items-center justify-center transition-all shrink-0 ${
              text.trim() && !isPending
                ? 'bg-[#FF6500] hover:bg-[#FF302A] text-white cursor-pointer shadow-md scale-105'
                : 'bg-white hover:bg-slate-200 cursor-pointer shadow'
            }`}
          >
            {isPending ? (
              <span className="w-4 h-4 border-2 border-black border-t-transparent rounded-full animate-spin" />
            ) : text.trim() ? (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2.2" viewBox="0 0 24 24" aria-hidden="true">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            ) : (
              /* Microphone icon in orange (#FF6500) */
              <svg className="w-4.5 h-4.5 text-[#FF6500]" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z" />
                <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                <line x1="12" y1="19" x2="12" y2="22" />
              </svg>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
