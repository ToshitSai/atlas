import React, { useState, useEffect, useRef, useCallback } from 'react';

/**
 * Question Composer:
 * Features:
 * - Single rounded pill container (`rounded-2xl`) with dark surface `#1C1C20`
 * - Smooth GPU-friendly focus/blur border transition (250-400ms easing)
 * - Focus activation on direct click, tabbing, or container click
 * - Left `+` quick access trigger button
 * - Clean borderless auto-resizing text field
 * - Keyboard shortcuts: Enter to send (Shift+Enter for newline), Cmd/Ctrl+K to focus
 * - Speech-to-text via Web Speech API with full lifecycle & error handling
 * - Right action button:
 *   - When empty: Microphone toggle with listening animation state
 *   - When text typed: Orange send button (`#F15A3A`)
 */
export default function QuestionComposer({
  onSubmit,
  isPending = false,
  backendConnected = false,
  connectionState = 'CONNECTING',
  errorFeedback = null,
  placeholder = null,
  isEmptyState = false,
}) {
  const [text, setText] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [speechError, setSpeechError] = useState(null);

  const textareaRef = useRef(null);
  const recognitionRef = useRef(null);
  const baseTextRef = useRef('');

  // Clean up SpeechRecognition on unmount
  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch (e) {
          // ignore cleanup errors
        }
        recognitionRef.current = null;
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

  // Auto-adjust textarea height dynamically
  useEffect(() => {
    if (textareaRef.current) {
      const mobile = window.matchMedia('(max-width: 640px)').matches;
      const maxHeight = Math.min(window.innerHeight * 0.4, mobile ? 240 : 360);
      textareaRef.current.style.height = 'auto';
      const nextHeight = Math.min(textareaRef.current.scrollHeight, maxHeight);
      textareaRef.current.style.height = `${nextHeight}px`;
      textareaRef.current.style.overflowY = textareaRef.current.scrollHeight > maxHeight ? 'auto' : 'hidden';
    }
  }, [text]);

  // Stop active speech recognition safely
  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (e) {
        try { recognitionRef.current.abort(); } catch (err) {}
      }
      recognitionRef.current = null;
    }
    setIsListening(false);
  }, []);

  // Toggle speech recognition session with proper event lifecycle
  const toggleListening = (e) => {
    if (e) e.preventDefault();
    setSpeechError(null);

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setSpeechError('Voice recognition is not supported in this browser. Please type your question.');
      return;
    }

    if (isListening) {
      stopListening();
      return;
    }

    // Stop any stale instance before starting a new session
    if (recognitionRef.current) {
      stopListening();
    }

    try {
      const recog = new SpeechRecognition();
      recog.continuous = true;
      recog.interimResults = true;
      recog.lang = 'en-US';

      // Store current text before speech begins so recognized text is appended cleanly
      baseTextRef.current = text ? (text.trim() + ' ') : '';

      recog.onstart = () => {
        setIsListening(true);
        setSpeechError(null);
      };

      recog.onresult = (event) => {
        let sessionTranscript = '';
        for (let i = 0; i < event.results.length; i++) {
          sessionTranscript += event.results[i][0].transcript;
        }
        const updatedText = baseTextRef.current + sessionTranscript;
        setText(updatedText);
      };

      recog.onerror = (event) => {
        console.warn('Speech recognition error event:', event.error);
        setIsListening(false);
        recognitionRef.current = null;

        if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
          setSpeechError('Microphone permission denied. Please enable microphone access in browser settings.');
        } else if (event.error === 'no-speech') {
          // Quiet timeout, no intrusive toast
        } else if (event.error === 'audio-capture') {
          setSpeechError('No microphone detected. Please connect a microphone and try again.');
        } else if (event.error !== 'aborted') {
          setSpeechError(`Voice input error (${event.error})`);
        }
      };

      recog.onend = () => {
        setIsListening(false);
        recognitionRef.current = null;
      };

      recognitionRef.current = recog;
      recog.start();
      textareaRef.current?.focus();
    } catch (err) {
      console.warn('Failed to start speech recognition:', err);
      setIsListening(false);
      recognitionRef.current = null;
      if (err.name === 'NotAllowedError') {
        setSpeechError('Microphone permission denied. Please enable microphone access in browser settings.');
      } else {
        setSpeechError('Could not start voice recognition. Please try again.');
      }
    }
  };

  const handleSubmit = (e) => {
    if (e) e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || isPending) return;

    if (isListening) {
      stopListening();
    }

    onSubmit(trimmed, () => {
      setText('');
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    });
  };

  const handleKeyDown = (e) => {
    if (e.nativeEvent?.isComposing || e.isComposing || e.keyCode === 229) return;
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="w-full font-sans select-none space-y-1.5">
      {/* Feedback alerts if disconnected, failed, or speech error */}
      {errorFeedback ? (
        <div className="text-xs font-sans text-[var(--text-failure)] px-3 pb-0.5">
          {errorFeedback}
        </div>
      ) : (connectionState === 'OFFLINE' && !backendConnected) ? (
        <div className="text-xs font-sans text-[var(--text-failure)] px-3 pb-0.5 flex items-center justify-between">
          <span>Research service not configured. No investigation or experiment has started.</span>
        </div>
      ) : null}

      {speechError && (
        <div className="text-xs font-sans text-[var(--accent-orange)] px-3 pb-0.5 flex items-center justify-between transition-opacity duration-200">
          <span>{speechError}</span>
          <button
            type="button"
            onClick={() => setSpeechError(null)}
            className="text-xs text-[var(--text-secondary)] hover:text-[var(--text-main)] underline ml-2 font-sans cursor-pointer"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Main Single Pill Bar Container */}
      <form
        onSubmit={handleSubmit}
        onClick={(e) => {
          if (e.target !== textareaRef.current && !e.target.closest('button')) {
            textareaRef.current?.focus();
          }
        }}
        className={`w-full bg-[var(--surface)] hover:bg-[var(--surface-hover)] border ${
          isListening
            ? 'border-[var(--accent-yellow)]'
            : 'border-[var(--border-subtle)] focus-within:border-[var(--focus-ring)]'
        } rounded-full px-3.5 py-1 flex items-center gap-2.5 shadow-[0_4px_20px_rgba(20,18,10,.06)] transition-all duration-300 ease-in-out h-[50px]`}
      >
        {/* Left "+" Icon / Quick Access Trigger */}
        <button
          type="button"
          onClick={() => textareaRef.current?.focus()}
          className="text-[var(--text-main)] text-xl font-light leading-none shrink-0 transition-colors cursor-pointer px-1"
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
          placeholder={placeholder || (isListening ? "Listening… Speak your question" : "Ask Atlas")}
          rows={1}
          disabled={isPending}
          aria-label="Research question input"
          className="flex-1 bg-transparent text-[15px] text-[var(--text-main)] placeholder-[var(--text-secondary)] focus:outline-none resize-none font-sans leading-relaxed min-h-[22px] py-1"
        />

        {/* Right Action Stack */}
        <div className="flex items-center gap-2 shrink-0">
          <button
            type="button"
            className="text-[13.5px] font-medium text-[var(--text-body)] hover:text-[var(--text-main)] flex items-center gap-1 cursor-pointer bg-transparent border-none px-1"
          >
            <span>Thinking</span>
            <svg className="w-3.5 h-3.5 text-[var(--text-muted)]" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" /></svg>
          </button>

          {/* Microphone Toggle Button */}
          <button
            type="button"
            onClick={toggleListening}
            disabled={isPending}
            aria-label={isListening ? "Stop listening" : "Start voice recognition"}
            title={isListening ? "Stop listening" : "Click to speak"}
            className={`w-9 h-9 rounded-full flex items-center justify-center transition-all duration-300 shrink-0 ${
              isListening
                ? 'bg-[#F15A3A] text-white shadow-md ring-2 ring-[#F15A3A]/40 animate-pulse cursor-pointer'
                : 'bg-[var(--surface-alt)] hover:bg-slate-200 text-[var(--text-main)] cursor-pointer'
            }`}
          >
            {isListening ? (
              <span className="w-3 h-3 bg-white rounded-sm" />
            ) : (
              <svg className="w-4 h-4 text-[var(--text-main)]" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z" />
                <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                <line x1="12" y1="19" x2="12" y2="22" />
              </svg>
            )}
          </button>

          {/* Solid Black Send Button */}
          <button
            type="submit"
            disabled={isPending || !text.trim()}
            aria-label="Send question"
            title="Send question (Enter)"
            className="w-9.5 h-9.5 rounded-full bg-[var(--text-main)] hover:scale-105 text-[var(--bg-main)] flex items-center justify-center transition-all duration-200 shrink-0 cursor-pointer disabled:opacity-60"
          >
            {isPending ? (
              <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              <svg className="w-4 h-4 fill-current text-[var(--bg-main)]" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M3.4 20.4l17.45-7.48a1 1 0 000-1.84L3.4 3.6a.996.996 0 00-1.37 1.14L4.2 11.5h9.3a.5.5 0 010 1H4.2l-2.17 6.76a1 1 0 001.37 1.14z" />
              </svg>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}

