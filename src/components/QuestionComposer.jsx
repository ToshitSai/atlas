import React, { useState, useEffect, useRef } from 'react';

/**
 * Question Composer:
 * Redesigned to match the clean, single-bar capsule design (Image 2 reference).
 * Features:
 * - Single rounded pill container (`rounded-2xl`) with dark surface `#1C1C20`
 * - Left `+` quick access trigger button
 * - Clean borderless auto-resizing text field
 * - Right action button:
 *   - When empty: Microphone toggle with Web Speech API voice-to-text recognition
 *   - When text typed: Orange send button (`#FF6500`)
 * - Live active recording pulse state and error feedback
 * - Cmd/Ctrl+K keyboard shortcut focus support
 */
export default function QuestionComposer({
  onSubmit,
  isPending = false,
  backendConnected = false,
  errorFeedback = null,
}) {
  const [text, setText] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [speechError, setSpeechError] = useState(null);
  const textareaRef = useRef(null);
  const recognitionRef = useRef(null);

  // Initialize Web Speech API for smooth voice input without external libraries
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recog = new SpeechRecognition();
      recog.continuous = true;
      recog.interimResults = true;
      recog.lang = 'en-US';

      recog.onresult = (event) => {
        let transcript = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
          transcript += event.results[i][0].transcript;
        }
        if (transcript.trim()) {
          setText(transcript);
        }
      };

      recog.onerror = (event) => {
        console.warn('Speech recognition error:', event.error);
        setIsListening(false);
        if (event.error === 'not-allowed') {
          setSpeechError('Microphone permission denied. Please enable microphone access in browser settings.');
        } else if (event.error === 'no-speech') {
          // Silence timeout, reset state quietly
          setSpeechError(null);
        } else {
          setSpeechError(`Voice input error (${event.error})`);
        }
      };

      recog.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recog;
    }

    return () => {
      if (recognitionRef.current) {
        try { recognitionRef.current.stop(); } catch (e) {}
      }
    };
  }, []);

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

  // Auto-adjust textarea height
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

    if (isListening) {
      try { recognitionRef.current?.stop(); } catch (err) {}
      setIsListening(false);
    }

    onSubmit(trimmed, () => setText(''));
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const toggleListening = (e) => {
    if (e) e.preventDefault();
    setSpeechError(null);
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setSpeechError('Voice recognition is not supported in this browser. Please type your question.');
      return;
    }

    if (isListening) {
      try { recognitionRef.current?.stop(); } catch (err) {}
      setIsListening(false);
    } else {
      try {
        recognitionRef.current?.start();
        setIsListening(true);
        textareaRef.current?.focus();
      } catch (err) {
        console.warn('Speech start error:', err);
        setIsListening(false);
      }
    }
  };

  return (
    <div className="w-full font-sans select-none space-y-1.5">
      {/* Feedback alerts if disconnected, failed, or speech error */}
      {!backendConnected && (
        <div className="text-xs font-sans text-[#F87171] px-3 pb-0.5 flex items-center justify-between">
          <span>Research service not configured. No investigation or experiment has started.</span>
        </div>
      )}

      {errorFeedback && (
        <div className="text-xs font-sans text-[#F87171] px-3 pb-0.5">
          {errorFeedback}
        </div>
      )}

      {speechError && (
        <div className="text-xs font-sans text-[#FF6500] px-3 pb-0.5 flex items-center justify-between">
          <span>{speechError}</span>
          <button
            type="button"
            onClick={() => setSpeechError(null)}
            className="text-xs text-[#8A8F98] hover:text-[#F4F4F6] underline ml-2 font-sans"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Main Single Pill Bar Container (Image 2 style) */}
      <form
        onSubmit={handleSubmit}
        className={`w-full bg-[#1C1C20] hover:bg-[#202025] border ${
          isListening ? 'border-[#FF6500] ring-1 ring-[#FF6500]/50' : 'border-[#2E2E34]'
        } focus-within:border-[#FF6500] focus-within:ring-1 focus-within:ring-[#FF6500]/30 rounded-2xl px-4 py-2.5 shadow-2xl flex items-center gap-3 transition-all`}
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
          placeholder={isListening ? "Listening... Speak your research question" : "Type / for quick access or ask a research question..."}
          rows={1}
          disabled={isPending}
          aria-label="Research question input"
          className="flex-1 bg-transparent text-sm text-[#F4F4F6] placeholder-[#71717A] focus:outline-none resize-none overflow-y-auto font-sans leading-relaxed min-h-[24px] max-h-[120px] py-0.5"
        />

        {/* Right Action Stack: Microphone or Send Button */}
        <div className="flex items-center gap-2 shrink-0">
          {text.trim() ? (
            /* Send Button (when text is entered) */
            <button
              type="submit"
              disabled={isPending}
              aria-label="Send question"
              title="Send question (Enter)"
              className="w-9 h-9 rounded-xl bg-[#FF6500] hover:bg-[#FF302A] text-white flex items-center justify-center transition-all shrink-0 cursor-pointer shadow-md scale-105"
            >
              {isPending ? (
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2.2" viewBox="0 0 24 24" aria-hidden="true">
                  <line x1="22" y1="2" x2="11" y2="13" />
                  <polygon points="22 2 15 22 11 13 2 9 22 2" />
                </svg>
              )}
            </button>
          ) : (
            /* Microphone Toggle Button (when empty) */
            <button
              type="button"
              onClick={toggleListening}
              disabled={isPending}
              aria-label={isListening ? "Stop listening" : "Start voice recognition"}
              title={isListening ? "Stop listening" : "Click to speak"}
              className={`w-9 h-9 rounded-xl flex items-center justify-center transition-all shrink-0 ${
                isListening
                  ? 'bg-[#FF6500] text-white shadow-lg animate-pulse ring-2 ring-[#FF6500]/50 cursor-pointer'
                  : 'bg-white hover:bg-slate-200 cursor-pointer shadow'
              }`}
            >
              {isListening ? (
                /* Stop icon during active recording */
                <span className="w-3.5 h-3.5 bg-white rounded-sm" />
              ) : (
                /* Orange microphone icon (#FF6500) */
                <svg className="w-4.5 h-4.5 text-[#FF6500]" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z" />
                  <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                  <line x1="12" y1="19" x2="12" y2="22" />
                </svg>
              )}
            </button>
          )}
        </div>
      </form>
    </div>
  );
}
