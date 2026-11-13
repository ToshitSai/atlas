import React, { useState, useEffect, useRef, useCallback } from 'react';
import { uploadRagDocument } from '../api';

/**
 * Question Composer:
 * Features:
 * - Single rounded pill container (`rounded-2xl`) with dark surface `#1C1C20`
 * - File attachment button (+) triggering file picker for documents & images
 * - Drag-and-drop file ingestion support
 * - Real-time attachment status chips (UPLOADING, INDEXING, READY, FAILED)
 * - Keyboard shortcuts: Enter to send (Shift+Enter for newline), Cmd/Ctrl+K to focus
 * - Speech-to-text via Web Speech API with full lifecycle & error handling
 * - Right action button:
 *   - When empty: Microphone toggle with listening animation state
 *   - When text typed or files attached: Send button
 */
export default function QuestionComposer({
  onSubmit,
  isPending = false,
  backendConnected = false,
  connectionState = 'CONNECTING',
  errorFeedback = null,
  onStop = null,
  onRetry = null,
  placeholder = null,
  isEmptyState = false,
}) {
  const [text, setText] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [speechError, setSpeechError] = useState(null);
  const [attachments, setAttachments] = useState([]);
  const [isDragging, setIsDragging] = useState(false);

  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);
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

    try {
      const recog = new SpeechRecognition();
      recog.continuous = true;
      recog.interimResults = true;
      recog.lang = 'en-US';

      baseTextRef.current = text ? (text.endsWith(' ') ? text : text + ' ') : '';

      recog.onstart = () => {
        setIsListening(true);
        setSpeechError(null);
      };

      recog.onresult = (event) => {
        let interim = '';
        let final = '';

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            final += event.results[i][0].transcript;
          } else {
            interim += event.results[i][0].transcript;
          }
        }

        if (final) {
          baseTextRef.current += final + ' ';
        }

        setText(baseTextRef.current + interim);
      };

      recog.onerror = (event) => {
        console.warn('Speech recognition error:', event.error);
        if (event.error === 'not-allowed') {
          setSpeechError('Microphone permission denied. Please allow microphone access in browser settings.');
        } else if (event.error === 'no-speech') {
          // ignore no-speech
        } else {
          setSpeechError(`Voice input error (${event.error}). Please type your question.`);
        }
        stopListening();
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

  // Upload and process files with granular lifecycle states
  const processFiles = async (fileList) => {
    if (!fileList || fileList.length === 0) return;

    const files = Array.from(fileList);
    for (const file of files) {
      const tempId = `temp-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      const ext = file.name.split('.').pop().toLowerCase();
      const isImg = ['png', 'jpg', 'jpeg', 'webp', 'gif'].includes(ext);

      // Pre-validation: Check for unsupported videos or legacy binary formats
      const isVideo = ['mp4', 'mov', 'avi', 'mkv', 'webm', 'wmv', 'm4v', 'flv'].includes(ext);
      const isLegacyOffice = ['doc', 'xls', 'ppt'].includes(ext);
      const MAX_CLIENT_BYTES = 4.5 * 1024 * 1024; // 4.5 MB Vercel Serverless payload ceiling

      if (isVideo) {
        setAttachments((prev) => [...prev, {
          tempId,
          rawFile: file,
          id: null,
          filename: file.name,
          size: file.size,
          doc_type: ext,
          is_image: false,
          status: 'FAILED',
          stage: 'extracting',
          category: 'unsupported_video',
          error: `Video files (.${ext}) are not supported. Please attach a document or still image.`,
        }]);
        continue;
      }

      if (isLegacyOffice) {
        const modernExt = ext === 'doc' ? 'docx' : (ext === 'xls' ? 'xlsx' : 'pptx');
        setAttachments((prev) => [...prev, {
          tempId,
          rawFile: file,
          id: null,
          filename: file.name,
          size: file.size,
          doc_type: ext,
          is_image: false,
          status: 'FAILED',
          stage: 'extracting',
          category: 'legacy_format',
          error: `Legacy .${ext} is not supported. Please save as modern .${modernExt} and re-upload.`,
        }]);
        continue;
      }

      if (file.size > MAX_CLIENT_BYTES) {
        const sizeMb = (file.size / (1024 * 1024)).toFixed(1);
        setAttachments((prev) => [...prev, {
          tempId,
          rawFile: file,
          id: null,
          filename: file.name,
          size: file.size,
          doc_type: ext,
          is_image: isImg,
          status: 'FAILED',
          stage: 'uploading',
          category: 'oversized_file',
          error: `File size (${sizeMb} MB) exceeds maximum upload limit of 4.5 MB.`,
        }]);
        continue;
      }

      const newAttachment = {
        tempId,
        rawFile: file,
        id: null,
        filename: file.name,
        size: file.size,
        doc_type: ext,
        is_image: isImg,
        status: 'UPLOADING',
        stage: 'uploading',
        error: null,
      };

      setAttachments((prev) => [...prev, newAttachment]);

      // Lifecycle status progression: UPLOADING -> EXTRACTING -> INDEXING -> STORING -> READY
      const tExtract = setTimeout(() => {
        setAttachments((prev) => prev.map((a) => a.tempId === tempId && a.status === 'UPLOADING' ? { ...a, status: 'EXTRACTING', stage: 'extracting' } : a));
      }, 400);
      const tIndex = setTimeout(() => {
        setAttachments((prev) => prev.map((a) => a.tempId === tempId && a.status === 'EXTRACTING' ? { ...a, status: 'INDEXING', stage: 'indexing' } : a));
      }, 950);
      const tStore = setTimeout(() => {
        setAttachments((prev) => prev.map((a) => a.tempId === tempId && a.status === 'INDEXING' ? { ...a, status: 'STORING', stage: 'storing' } : a));
      }, 1600);

      try {
        // Upload as chat_attachment workflow
        const res = await uploadRagDocument(file, 'chat_attachment');
        clearTimeout(tExtract); clearTimeout(tIndex); clearTimeout(tStore);
        setAttachments((prev) => prev.map((a) => {
          if (a.tempId === tempId) {
            return {
              ...a,
              id: res.id,
              status: 'READY',
              stage: 'ready',
              chunks: res.chunks,
              is_image: res.is_image,
              ocr_text: res.ocr_text,
              visual_description: res.visual_description,
              image_type: res.image_type,
            };
          }
          return a;
        }));
      } catch (err) {
        clearTimeout(tExtract); clearTimeout(tIndex); clearTimeout(tStore);
        const stage = err.stage || 'uploading';
        const errorMsg = err.detail || err.message || 'Upload failed';
        setAttachments((prev) => prev.map((a) => {
          if (a.tempId === tempId) {
            return {
              ...a,
              status: 'FAILED',
              stage,
              category: err.category || 'upload_error',
              error: errorMsg,
            };
          }
          return a;
        }));
      }
    }
  };

  const retryAttachment = async (tempId) => {
    const att = attachments.find((a) => a.tempId === tempId);
    if (!att || !att.rawFile) return;

    const ext = att.filename.split('.').pop().toLowerCase();
    if (['mp4', 'mov', 'avi', 'mkv', 'webm', 'wmv'].includes(ext)) return;
    if (['doc', 'xls', 'ppt'].includes(ext)) return;

    setAttachments((prev) => prev.map((a) => a.tempId === tempId ? { ...a, status: 'UPLOADING', stage: 'uploading', error: null } : a));

    const tExtract = setTimeout(() => {
      setAttachments((prev) => prev.map((a) => a.tempId === tempId && a.status === 'UPLOADING' ? { ...a, status: 'EXTRACTING', stage: 'extracting' } : a));
    }, 400);
    const tIndex = setTimeout(() => {
      setAttachments((prev) => prev.map((a) => a.tempId === tempId && a.status === 'EXTRACTING' ? { ...a, status: 'INDEXING', stage: 'indexing' } : a));
    }, 950);
    const tStore = setTimeout(() => {
      setAttachments((prev) => prev.map((a) => a.tempId === tempId && a.status === 'INDEXING' ? { ...a, status: 'STORING', stage: 'storing' } : a));
    }, 1600);

    try {
      const res = await uploadRagDocument(att.rawFile, 'chat_attachment');
      clearTimeout(tExtract); clearTimeout(tIndex); clearTimeout(tStore);
      setAttachments((prev) => prev.map((a) => {
        if (a.tempId === tempId) {
          return {
            ...a,
            id: res.id,
            status: 'READY',
            stage: 'ready',
            chunks: res.chunks,
            is_image: res.is_image,
            ocr_text: res.ocr_text,
            visual_description: res.visual_description,
            image_type: res.image_type,
          };
        }
        return a;
      }));
    } catch (err) {
      clearTimeout(tExtract); clearTimeout(tIndex); clearTimeout(tStore);
      const stage = err.stage || 'uploading';
      const errorMsg = err.detail || err.message || 'Retry failed';
      setAttachments((prev) => prev.map((a) => {
        if (a.tempId === tempId) {
          return {
            ...a,
            status: 'FAILED',
            stage,
            category: err.category || 'upload_error',
            error: errorMsg,
          };
        }
        return a;
      }));
    }
  };

  const handleFileSelect = (e) => {
    if (e.target.files) {
      processFiles(e.target.files);
      e.target.value = '';
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer?.files) {
      processFiles(e.dataTransfer.files);
    }
  };

  const removeAttachment = (tempId) => {
    setAttachments((prev) => prev.filter((a) => a.tempId !== tempId));
  };

  const handleSubmit = (e) => {
    if (e) e.preventDefault();
    const trimmed = text.trim();
    const readyAttachments = attachments.filter((a) => a.status === 'READY');
    if ((!trimmed && readyAttachments.length === 0) || isPending) return;

    if (isListening) {
      stopListening();
    }

    const finalMessage = trimmed || (readyAttachments.length > 0
      ? `Analyze attached ${readyAttachments.map((a) => a.filename).join(', ')}`
      : '');

    onSubmit(
      finalMessage,
      () => {
        setText('');
        setAttachments([]);
        if (textareaRef.current) {
          textareaRef.current.style.height = 'auto';
        }
      },
      { attachments: readyAttachments }
    );
  };

  const handleKeyDown = (e) => {
    if (e.nativeEvent?.isComposing || e.isComposing || e.keyCode === 229) return;
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const formatSize = (bytes) => {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
  };

  return (
    <div className="w-full font-sans select-none space-y-1.5">
      {/* Feedback alerts if disconnected, failed, or speech error */}
      {errorFeedback ? (
        <div className="text-xs font-sans text-[var(--text-failure)] px-3 pb-0.5 flex items-center justify-between gap-2">
          {typeof errorFeedback === 'string' ? errorFeedback : (errorFeedback?.detail || errorFeedback?.message || JSON.stringify(errorFeedback))}
          {onRetry && (
            <button type="button" onClick={onRetry} className="text-[var(--text-secondary)] underline underline-offset-2">
              Retry
            </button>
          )}
        </div>
      ) : connectionState === 'OFFLINE' && !backendConnected ? (
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

      {/* Hidden File Picker Input */}
      <input
        type="file"
        ref={fileInputRef}
        multiple
        accept=".pdf,.docx,.txt,.md,.json,.csv,.tsv,.xlsx,.pptx,.png,.jpg,.jpeg,.webp,.gif,.py,.js,.ts,.html,.xml"
        style={{ display: 'none' }}
        onChange={handleFileSelect}
      />

      {/* Attachment Chips Bar (renders when files are attached) */}
      {attachments.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 px-3 py-1 bg-[var(--surface-alt)]/60 rounded-xl border border-[var(--border-subtle)] backdrop-blur-sm">
          {attachments.map((att) => (
            <div
              key={att.tempId}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium bg-[var(--surface)] border border-[var(--border-subtle)] text-[var(--text-main)] shadow-sm max-w-[280px]"
            >
              <span className="text-sm">
                {att.is_image ? '🖼️' : att.doc_type?.includes('xls') || att.doc_type === 'csv' || att.doc_type === 'tsv' ? '📊' : att.doc_type?.includes('ppt') ? '📑' : '📄'}
              </span>
              <span className="truncate max-w-[110px]" title={att.filename}>{att.filename}</span>
              <span className="text-[10px] text-[var(--text-muted)]">({formatSize(att.size)})</span>

              {att.status === 'UPLOADING' && (
                <span className="text-[10px] text-amber-500 font-semibold animate-pulse">Uploading…</span>
              )}
              {att.status === 'EXTRACTING' && (
                <span className="text-[10px] text-sky-400 font-semibold animate-pulse">Extracting…</span>
              )}
              {att.status === 'INDEXING' && (
                <span className="text-[10px] text-indigo-400 font-semibold animate-pulse">Indexing…</span>
              )}
              {att.status === 'STORING' && (
                <span className="text-[10px] text-purple-400 font-semibold animate-pulse">Storing…</span>
              )}
              {att.status === 'READY' && (
                <span className="text-[10px] text-emerald-500 font-bold" title="Ready for analysis">✓ Ready</span>
              )}
              {att.status === 'FAILED' && (
                <div className="flex items-center gap-1.5 max-w-[210px]" title={att.error}>
                  <span className="text-[10px] text-red-500 font-semibold truncate">
                    Failed{att.stage ? ` (${att.stage})` : ''}: {att.error}
                  </span>
                  {att.category !== 'unsupported_video' && att.category !== 'legacy_format' && att.category !== 'oversized_file' && (
                    <button
                      type="button"
                      onClick={() => retryAttachment(att.tempId)}
                      className="text-[10px] text-amber-400 hover:text-amber-300 underline font-semibold shrink-0 cursor-pointer"
                    >
                      Retry
                    </button>
                  )}
                </div>
              )}

              <button
                type="button"
                onClick={() => removeAttachment(att.tempId)}
                className="ml-1 text-[var(--text-muted)] hover:text-red-500 text-sm font-bold leading-none cursor-pointer"
                title="Remove attachment"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Main Single Pill Bar Container with Drag-and-Drop */}
      <form
        onSubmit={handleSubmit}
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={(e) => {
          if (e.target !== textareaRef.current && !e.target.closest('button')) {
            textareaRef.current?.focus();
          }
        }}
        className={`w-full bg-[var(--surface)] hover:bg-[var(--surface-hover)] border ${
          isDragging
            ? 'border-indigo-500 bg-indigo-50/10 ring-2 ring-indigo-500/30'
            : isListening
            ? 'border-[var(--accent-yellow)]'
            : 'border-[var(--border-subtle)] focus-within:border-[var(--focus-ring)]'
        } rounded-full px-3.5 py-1 flex items-center gap-2.5 shadow-[0_4px_20px_rgba(20,18,10,.06)] transition-all duration-300 ease-in-out min-h-[50px]`}
      >
        {/* Left "+" Icon / Attachment Trigger */}
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          className="text-[var(--text-main)] hover:text-indigo-400 text-xl font-light leading-none shrink-0 transition-colors cursor-pointer px-1"
          title="Attach files or images (PDF, DOCX, XLSX, PPTX, Images, etc.)"
          aria-label="Attach files"
        >
          +
        </button>

        {/* Input Textarea */}
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            placeholder ||
            (isDragging
              ? 'Drop files to attach…'
              : isListening
              ? 'Listening… Speak your question'
              : attachments.length > 0
              ? 'Ask anything about the attached files…'
              : 'Ask Atlas')
          }
          rows={1}
          disabled={isPending}
          aria-label="Research question input"
          className="flex-1 bg-transparent text-[15px] text-[var(--text-main)] placeholder-[var(--text-secondary)] focus:outline-none resize-none font-sans leading-relaxed min-h-[22px] py-1"
        />

        {/* Right Action Stack */}
        <div className="flex items-center gap-2 shrink-0">
          {/* Microphone Toggle Button */}
          <button
            type="button"
            onClick={toggleListening}
            disabled={isPending}
            aria-label={isListening ? 'Stop listening' : 'Start voice recognition'}
            title={isListening ? 'Stop listening' : 'Click to speak'}
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
            type={isPending ? 'button' : 'submit'}
            onClick={isPending ? onStop : undefined}
            disabled={!isPending && !text.trim() && attachments.filter((a) => a.status === 'READY').length === 0}
            aria-label={isPending ? 'Stop response' : 'Send question'}
            title={isPending ? 'Stop response' : 'Send question (Enter)'}
            className="w-9.5 h-9.5 rounded-full bg-[var(--text-main)] hover:scale-105 text-[var(--bg-main)] flex items-center justify-center transition-all duration-200 shrink-0 cursor-pointer disabled:opacity-60"
          >
            {isPending ? (
              <span className="w-3.5 h-3.5 rounded-sm bg-current" />
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
