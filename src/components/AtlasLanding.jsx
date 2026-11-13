import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ProgressiveMarkdown from './ProgressiveMarkdown';
import AtlasLogo from './AtlasLogo';
import { uploadRagDocument } from '../api';
import ImageLightbox from './ImageLightbox';
import AttachmentArea from './AttachmentArea';
import ActivityTimeline from './ActivityTimeline';
import SourceCards from './SourceCards';
import ResponseActions from './ResponseActions';
import ModelSelectorDropdown from './ModelSelectorDropdown';

// ============================================================================
// DESIGN SYSTEM TOKENS
// ============================================================================
const TOKENS = {
  fonts: {
    sans: '"Inter", "Segoe UI", -apple-system, system-ui, sans-serif',
    mono: '"SF Mono", ui-monospace, Menlo, monospace',
  },
  colors: {
    bg: 'var(--bg-main)',
    sidebar: 'var(--bg-left-nav)',
    ink: 'var(--text-main)',
    body: 'var(--text-body)',
    muted: 'var(--text-secondary)',
    line: 'var(--border-subtle)',
    yellow: 'var(--accent-yellow)',
    amber: 'var(--accent-amber)',
    orange: 'var(--accent-orange)',
    card: 'var(--surface)',
    hover: 'var(--surface-hover)',
    bubble: 'var(--surface-alt)',
    chip: 'var(--surface-alt)',
    amberChip: 'color-mix(in srgb, var(--accent-yellow) 18%, var(--surface))',
    amberBorder: 'var(--border-emphasis)',
  }
};

// ============================================================================
// INLINE ICONS
// ============================================================================
function IconPaperPlane2({ size = 15, style = {} }) {
  return (
    <svg width={size} height={size} style={style} viewBox="0 0 24 24" fill="currentColor">
      <path d="M3.4 20.4l17.45-7.48a1 1 0 000-1.84L3.4 3.6a.996.996 0 00-1.37 1.14L4.2 11.5h9.3a.5.5 0 010 1H4.2l-2.17 6.76a1 1 0 001.37 1.14z" />
    </svg>
  );
}

function IconPlus({ size = 16, style = {} }) {
  return (
    <svg width={size} height={size} style={style} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  );
}

function IconArrowUp({ size = 16, style = {} }) {
  return (
    <svg width={size} height={size} style={style} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" y1="19" x2="12" y2="5" />
      <polyline points="5 12 12 5 19 12" />
    </svg>
  );
}

function IconAtom({ size = 16, style = {} }) {
  return (
    <svg width={size} height={size} style={style} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="2" fill="currentColor" />
      <path d="M12 2v2M12 20v2M2 12h2M20 12h2" />
      <ellipse cx="12" cy="12" rx="9" ry="4.5" transform="rotate(30 12 12)" />
      <ellipse cx="12" cy="12" rx="9" ry="4.5" transform="rotate(150 12 12)" />
    </svg>
  );
}

function IconMicroscope({ size = 16, style = {} }) {
  return (
    <svg width={size} height={size} style={style} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M6 18h12M12 18v3M9 14a5 5 0 0010 0v-4H9v4z" />
      <path d="M12 6l3 3M10 4l5 5" />
      <circle cx="8" cy="18" r="2" />
    </svg>
  );
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================
export default function AtlasLanding({
  onSendMessage,
  onStop,
  onOpenAuth,
  onOpenSettings,
  conversationTurns = [],
  isPending = false,
  onNewChat,
  historyItems = [],
  onSelectHistoryItem,
  theme = 'system',
  onThemeChange,
  sidebarOpen = true,
  onToggleSidebar,
  historyLoadState = 'ready',
  activeConversationId,
  confidenceChecking = false,
  onEditMessage,
  onRetry,
  backendConnected,
  connectionState,
  errorFeedback,
  greeting
}) {
  const greetingMain = typeof greeting === 'string'
    ? greeting
    : (typeof greeting === 'object' && greeting?.main ? greeting.main : 'How can Atlas help you today?');
  const greetingSub = typeof greeting === 'object' && greeting?.sub ? greeting.sub : null;

  const [inputText, setInputText] = useState('');
  const [isDeepResearch, setIsDeepResearch] = useState(() => {
    try { return localStorage.getItem('atlas-deep-research') === '1'; } catch { return false; }
  });
  const [selectedModel, setSelectedModel] = useState(() => {
    try {
      const saved = localStorage.getItem('atlas-model');
      if (saved && saved !== 'Atlas Large') return saved;
      return 'Atlas Research (Gen-4 Local)';
    } catch {
      return 'Atlas Research (Gen-4 Local)';
    }
  });
  const [attachments, setAttachments] = useState([]);
  const [isDragging, setIsDragging] = useState(false);
  const [previewImage, setPreviewImage] = useState(null);

  useEffect(() => {
    try { localStorage.setItem('atlas-model', selectedModel); } catch {}
  }, [selectedModel]);

  useEffect(() => {
    try { localStorage.setItem('atlas-deep-research', isDeepResearch ? '1' : '0'); } catch {}
  }, [isDeepResearch]);

  const hasConversation = conversationTurns.length > 0;
  const scrollRef = useRef(null);
  const inputRef = useRef(null);
  const fileInputRef = useRef(null);

  // Auto-grow input textarea height
  useEffect(() => {
    const input = inputRef.current;
    if (!input) return;
    const mobile = typeof window !== 'undefined' && typeof window.matchMedia === 'function' ? window.matchMedia('(max-width: 640px)').matches : false;
    const maxHeight = Math.min(window.innerHeight * 0.4, mobile ? 240 : 360);
    input.style.height = 'auto';
    input.style.height = `${Math.min(input.scrollHeight, maxHeight)}px`;
    input.style.overflowY = input.scrollHeight > maxHeight ? 'auto' : 'hidden';
  }, [inputText]);

  // Auto-scroll on conversation update
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  }, [conversationTurns, isPending]);

  const processFiles = async (fileList) => {
    if (!fileList || fileList.length === 0) return;
    const files = Array.from(fileList);
    for (const file of files) {
      const tempId = `temp-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      const ext = file.name.split('.').pop().toLowerCase();
      const isImg = ['png', 'jpg', 'jpeg', 'webp', 'gif', 'bmp', 'tiff'].includes(ext);
      const previewUrl = isImg ? URL.createObjectURL(file) : null;

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
          previewUrl: null,
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
          previewUrl: null,
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
          previewUrl,
          status: 'FAILED',
          stage: 'uploading',
          category: 'oversized_file',
          error: `File size (${sizeMb} MB) exceeds maximum upload limit of 4.5 MB.`,
        }]);
        continue;
      }

      setAttachments((prev) => [...prev, {
        tempId,
        rawFile: file,
        id: null,
        filename: file.name,
        size: file.size,
        doc_type: ext,
        is_image: isImg,
        previewUrl,
        status: 'UPLOADING',
        stage: 'uploading',
        error: null,
      }]);

      const tExtract = setTimeout(() => {
        setAttachments((prev) => prev.map((a) => a.tempId === tempId && a.status === 'UPLOADING' ? { ...a, status: 'EXTRACTING', stage: 'extracting' } : a));
      }, 350);
      const tIndex = setTimeout(() => {
        setAttachments((prev) => prev.map((a) => a.tempId === tempId && a.status === 'EXTRACTING' ? { ...a, status: 'INDEXING', stage: 'indexing' } : a));
      }, 850);
      const tStore = setTimeout(() => {
        setAttachments((prev) => prev.map((a) => a.tempId === tempId && a.status === 'INDEXING' ? { ...a, status: 'STORING', stage: 'storing' } : a));
      }, 1500);

      try {
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
    }, 350);
    const tIndex = setTimeout(() => {
      setAttachments((prev) => prev.map((a) => a.tempId === tempId && a.status === 'EXTRACTING' ? { ...a, status: 'INDEXING', stage: 'indexing' } : a));
    }, 850);
    const tStore = setTimeout(() => {
      setAttachments((prev) => prev.map((a) => a.tempId === tempId && a.status === 'INDEXING' ? { ...a, status: 'STORING', stage: 'storing' } : a));
    }, 1500);

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

  const handleSend = (text) => {
    const prompt = (text || inputText).trim();
    const readyAttachments = attachments.filter((a) => a.status === 'READY');
    if (!prompt && readyAttachments.length === 0) return;

    const finalPrompt = prompt || (readyAttachments.length > 0
      ? `Analyze attached ${readyAttachments.map((a) => a.filename).join(', ')}`
      : '');

    const cleanAttachments = readyAttachments.map((a) => ({
      document_id: a.id || a.document_id,
      id: a.id || a.document_id,
      filename: a.filename || a.name || 'document',
      doc_type: a.doc_type,
      is_image: Boolean(a.is_image),
      workflow: a.workflow || 'chat_attachment',
    }));

    if (onSendMessage) {
      onSendMessage(
        finalPrompt,
        () => {
          setInputText('');
          setAttachments([]);
        },
        { deepResearch: isDeepResearch, model: selectedModel, attachments: cleanAttachments }
      );
    }
    setInputText('');
    setAttachments([]);
  };

  return (
    <div
      className="atlas-shell"
      style={{
        height: '100%',
        width: '100%',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        position: 'relative',
        backgroundColor: TOKENS.colors.bg,
        fontFamily: TOKENS.fonts.sans,
        color: TOKENS.colors.ink,
        WebkitFontSmoothing: 'antialiased'
      }}
    >
      {/* MAIN WORKSPACE SURFACE */}
      <main
        style={{
          flex: '1 1 auto',
          minWidth: 0,
          position: 'relative',
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
          overflow: 'hidden',
          backgroundColor: TOKENS.colors.bg,
          justifyContent: hasConversation ? 'flex-start' : 'center'
        }}
      >
        {/* Scroll Area */}
        <div
          ref={scrollRef}
          className="scroll-fade"
          style={{
            flex: hasConversation ? 1 : '0 0 auto',
            overflowY: 'auto',
            display: 'flex',
            flexDirection: 'column',
            position: 'relative',
            width: '100%',
            alignItems: 'center',
            overflowX: 'hidden'
          }}
        >
          {conversationTurns.length > 0 ? (
            <ConversationThread
              turns={conversationTurns}
              isPending={isPending}
              confidenceChecking={confidenceChecking}
              onEditMessage={onEditMessage}
              onRetry={onRetry}
              onPreviewImage={setPreviewImage}
            />
          ) : (
            <div
              style={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                paddingBottom: 0,
                minHeight: hasConversation ? 'auto' : '0'
              }}
            >
              <AnimatePresence mode="wait">
                <motion.div
                  key="idle-hero"
                  initial={{ opacity: 0, y: 18, scale: 0.97 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -14, transition: { duration: 0.25 } }}
                  transition={{ type: 'spring', stiffness: 90, damping: 16 }}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    textAlign: 'center',
                    width: 'min(100%, 1024px)',
                    gap: '40px'
                  }}
                >
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '10px' }}>
                    <h1
                      className="atlas-hero-heading"
                      style={{
                        fontSize: 'clamp(24px, 5.5vw, 42px)',
                        fontWeight: 400,
                        letterSpacing: '-0.02em',
                        color: 'var(--text-main)',
                        margin: 0,
                        padding: '0 16px',
                        lineHeight: '1.25'
                      }}
                    >
                      {greetingMain}
                    </h1>
                    {greetingSub && (
                      <p
                        style={{
                          fontSize: 'clamp(14px, 2.5vw, 16px)',
                          color: 'var(--text-secondary)',
                          margin: 0,
                          padding: '0 16px',
                          lineHeight: '1.4',
                          maxWidth: '620px'
                        }}
                      >
                        {greetingSub}
                      </p>
                    )}
                  </div>
                  <div className="atlas-onboarding-prompts" aria-label="Example prompts">
                    {[
                      'Explain a research paper clearly',
                      'Search for the latest ML developments',
                      'Help me design an experiment',
                      'Analyze multiple uploaded images and compare them',
                    ].map((prompt) => (
                      <button key={prompt} type="button" onClick={() => setInputText(prompt)}>
                        {prompt}
                      </button>
                    ))}
                  </div>
                </motion.div>
              </AnimatePresence>
            </div>
          )}
        </div>

        {/* PROMPT DOCK */}
        <div
          style={{
            position: hasConversation ? 'absolute' : 'static',
            ...(hasConversation ? { bottom: 0, left: 0, right: 0 } : {}),
            pointerEvents: 'none',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            background: hasConversation ? 'linear-gradient(to top, var(--bg-main) 65%, transparent)' : 'transparent',
            width: '100%',
            padding: hasConversation ? '0 16px 16px 16px' : '0 24px 16px',
            zIndex: 10
          }}
          className={`atlas-prompt-dock ${hasConversation ? 'is-chat' : 'is-home'}`}
        >
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            style={{
              width: 'min(100%, 760px)',
              maxWidth: '760px',
              minHeight: '0',
              height: 'auto',
              backgroundColor: TOKENS.colors.card,
              border: `1px solid ${isDragging ? TOKENS.colors.amber : TOKENS.colors.line}`,
              borderRadius: '28px',
              boxShadow: isDragging ? '0 8px 30px rgba(245, 158, 11, 0.15)' : '0 4px 20px rgba(0,0,0,0.06)',
              padding: '14px 18px',
              pointerEvents: 'auto',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '8px'
            }}
          >
            {/* Hidden File Picker Input */}
            <input
              type="file"
              ref={fileInputRef}
              multiple
              accept=".pdf,.docx,.txt,.md,.json,.csv,.tsv,.xlsx,.pptx,.png,.jpg,.jpeg,.webp,.gif,.py,.js,.ts,.html,.xml"
              style={{ display: 'none' }}
              onChange={handleFileSelect}
            />

            {/* Modern Attachment Area with Thumbnails */}
            {attachments.length > 0 && (
              <AttachmentArea
                attachments={attachments}
                onRemove={removeAttachment}
                onRetry={retryAttachment}
                onImageClick={setPreviewImage}
              />
            )}

            {/* Input Textarea */}
            <textarea
              className="atlas-composer-input"
              ref={inputRef}
              rows={1}
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={(e) => {
                if (e.nativeEvent?.isComposing || e.isComposing || e.keyCode === 229) return;
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder={isDragging ? 'Drop files to attach…' : attachments.length > 0 ? 'Ask anything about the attached files…' : 'Ask Atlas…'}
              style={{
                flex: 'none',
                width: '100%',
                backgroundColor: 'transparent',
                border: 'none',
                outline: 'none',
                resize: 'none',
                fontFamily: TOKENS.fonts.sans,
                fontSize: '15px',
                color: TOKENS.colors.ink,
                lineHeight: '1.45',
                paddingTop: '2px',
                minHeight: '26px',
                overflowY: 'auto'
              }}
            />

            {/* Action Bar: [ + ] [ ● Atlas Research (Gen-4) ▾ ] [ ✧ Deep Research ] ... [ Send/Stop ] */}
            <div className="atlas-composer-controls" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px', width: '100%', flexShrink: 0, position: 'relative' }}>
              <div className="atlas-composer-actions-left" style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0, flexWrap: 'wrap' }}>
                {/* 1. Attachment Button: circular/softly rounded, plus icon only, tooltip "Attach files" */}
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isPending}
                  className="atlas-attach-btn"
                  title="Attach files"
                  aria-label="Attach files"
                  style={{
                    width: '32px',
                    height: '32px',
                    minWidth: '32px',
                    minHeight: '32px',
                    borderRadius: '50%',
                    border: `1px solid ${TOKENS.colors.line}`,
                    backgroundColor: 'var(--surface, transparent)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    cursor: isPending ? 'not-allowed' : 'pointer',
                    opacity: isPending ? 0.5 : 1,
                    transition: 'all 0.15s ease',
                    flexShrink: 0,
                    padding: 0,
                    color: 'var(--text-body, #c0c2cb)',
                  }}
                >
                  <IconPlus size={16} style={{ color: 'inherit' }} />
                </button>

                {/* 2. Model Selector Dropdown: [ ● Atlas Research (Gen-4) ▾ ] */}
                <ModelSelectorDropdown
                  selectedModel={selectedModel}
                  onSelectModel={setSelectedModel}
                  disabled={isPending}
                />

                {/* 3. Deep Research Toggle Button: [ ✧ Deep Research ] */}
                <button
                  type="button"
                  onClick={() => setIsDeepResearch(!isDeepResearch)}
                  aria-label="Deep Research"
                  aria-pressed={isDeepResearch}
                  title={isDeepResearch ? "Deep Research active (multi-step evidence synthesis)" : "Enable Deep Research"}
                  disabled={isPending}
                  className={`atlas-deep-research-btn ${isDeepResearch ? 'active' : ''}`}
                  style={{
                    height: '32px',
                    borderRadius: '999px',
                    padding: '0 11px',
                    border: `1px solid ${isDeepResearch ? 'rgba(245, 158, 11, 0.45)' : TOKENS.colors.line}`,
                    backgroundColor: isDeepResearch ? 'rgba(245, 158, 11, 0.12)' : 'var(--surface, transparent)',
                    color: isDeepResearch ? '#fbbf24' : 'var(--text-body, #c0c2cb)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '5px',
                    cursor: isPending ? 'not-allowed' : 'pointer',
                    transition: 'all 0.15s ease',
                    opacity: isPending ? 0.5 : 1,
                    fontSize: '12px',
                    fontWeight: 500,
                    flexShrink: 0,
                  }}
                >
                  <span style={{ fontSize: '13px', lineHeight: 1, color: isDeepResearch ? '#fbbf24' : 'var(--text-muted, #8b8d96)' }}>✧</span>
                  <span className="atlas-research-label">Deep Research</span>
                </button>
              </div>

              {/* Right: Send / Stop Button */}
              {isPending ? (
                <motion.button
                  type="button"
                  className="atlas-stop-button"
                  onClick={onStop}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  style={{
                    width: '32px',
                    height: '32px',
                    minWidth: '32px',
                    minHeight: '32px',
                    borderRadius: '50%',
                    backgroundColor: 'var(--surface-alt)',
                    border: `1px solid ${TOKENS.colors.line}`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: TOKENS.colors.ink,
                    cursor: 'pointer',
                    flexShrink: 0,
                    marginLeft: 'auto',
                    padding: 0,
                  }}
                  title="Stop generating"
                  aria-label="Stop generating"
                >
                  <span style={{ width: '10px', height: '10px', backgroundColor: 'var(--accent-orange, #f97316)', borderRadius: '2px' }} />
                </motion.button>
              ) : (
                <motion.button
                  type="button"
                  className="atlas-send-button"
                  onClick={() => handleSend()}
                  disabled={!inputText.trim() && attachments.filter((a) => a.status === 'READY').length === 0}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  style={{
                    width: '32px',
                    height: '32px',
                    minWidth: '32px',
                    minHeight: '32px',
                    borderRadius: '50%',
                    backgroundColor: TOKENS.colors.ink,
                    border: 'none',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'var(--surface)',
                    cursor: inputText.trim() || attachments.filter((a) => a.status === 'READY').length > 0 ? 'pointer' : 'default',
                    opacity: inputText.trim() || attachments.filter((a) => a.status === 'READY').length > 0 ? 1 : 0.35,
                    flexShrink: 0,
                    marginLeft: 'auto',
                    padding: 0,
                  }}
                  title="Send (Enter)"
                  aria-label="Send"
                >
                  <IconArrowUp size={16} />
                </motion.button>
              )}
            </div>
          </div>

          <div
            style={{
              fontSize: '11px',
              color: TOKENS.colors.muted,
              marginTop: hasConversation ? '8px' : '12px',
              textAlign: 'center',
              pointerEvents: 'auto',
              ...(hasConversation ? {} : { marginBottom: '0' })
            }}
          >
            Atlas can run experiments and cite sources. Verify important results.
          </div>
        </div>
      </main>

      {/* LIGHTBOX MODAL FOR IMAGE PREVIEW */}
      <ImageLightbox image={previewImage} onClose={() => setPreviewImage(null)} />
    </div>
  );
}

// ============================================================================
// CONVERSATION THREAD
// ============================================================================
function ConversationThread({
  turns,
  isPending,
  confidenceChecking = false,
  onEditMessage,
  onRetry,
  onPreviewImage
}) {
  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: '42px 24px calc(176px + 24px)', width: '100%', maxWidth: '900px', margin: '0 auto' }}>
      {turns.map((turn, turnIdx) => (
        <motion.div
          key={turn.id || turnIdx}
          className="atlas-message-enter"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2, ease: 'easeOut' }}
          style={{ marginBottom: '34px' }}
        >
          {/* USER MESSAGE ROW */}
          <div className="atlas-user-message-wrap" style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '22px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', maxWidth: '80%' }}>
              {turn.attachments && turn.attachments.length > 0 && (
                <div style={{ marginBottom: '8px', display: 'flex', justifyContent: 'flex-end', width: '100%' }}>
                  <AttachmentArea
                    attachments={turn.attachments}
                    compact={true}
                    onImageClick={onPreviewImage}
                  />
                </div>
              )}
              <div
                style={{
                  background: TOKENS.colors.bubble,
                  borderRadius: '18px 18px 4px 18px',
                  padding: '14px 18px',
                  color: TOKENS.colors.ink,
                  fontSize: '15px',
                  lineHeight: 1.5,
                  overflowWrap: 'anywhere'
                }}
              >
                {typeof turn.question === 'string' ? turn.question : JSON.stringify(turn.question || '')}
              </div>
              <MessageActions text={typeof turn.question === 'string' ? turn.question : JSON.stringify(turn.question || '')} onEdit={(value) => onEditMessage?.(turns.indexOf(turn), value)} />
            </div>
          </div>

          {/* ASSISTANT MESSAGE ROW */}
          <div className="atlas-assistant-message-row" style={{ display: 'flex', alignItems: 'flex-start', width: '100%' }}>
            <div style={{ flex: 1, color: TOKENS.colors.body, fontSize: '15.5px', lineHeight: 1.7, minWidth: 0 }}>
              {/* OPERATIONAL ACTIVITY TIMELINE (Intelligent 3-Tier Routing) */}
              {(() => {
                const isDeep = Boolean(turn.isDeepResearch || turn.mode === 'deep' || turn.activityTier === 'full');
                const hasActivities = Boolean(turn.activities && turn.activities.length > 0);
                const isCompact = Boolean(turn.activityTier === 'compact' || (!isDeep && hasActivities && turn.activityTier !== 'none'));
                const isHidden = turn.activityTier === 'none' || (!isDeep && !isCompact);

                if (isHidden) return null;

                const tier = isDeep ? 'full' : 'compact';

                return (
                  <ActivityTimeline
                    activities={turn.activities || []}
                    isLoading={Boolean(turn.isLoading)}
                    mode={isDeep ? 'deep' : 'normal'}
                    tier={tier}
                  />
                );
              })()}

              {/* STREAMING / ANSWER CONTENT */}
              {turn.isLoading && !turn.answer ? (
                <div className="flex items-center gap-2 py-3 text-sm text-[var(--text-muted)]">
                  <span className="inline-block h-2 w-2 rounded-full bg-[var(--accent-yellow)] animate-pulse" />
                  <span>Synthesizing verified response…</span>
                </div>
              ) : (
                <ProgressiveMarkdown
                  content={typeof turn.answer === 'string' ? turn.answer : JSON.stringify(turn.answer || '')}
                  streaming={Boolean(turn.isLoading)}
                  instant={Boolean(turn.loadedFromHistory)}
                  deliveryPath={turn.loadedFromHistory ? 'loaded from history' : 'new answer'}
                />
              )}

              {turn.fallbackNotice && (
                <div style={{ fontSize: '12px', color: TOKENS.colors.muted, marginTop: '6px', fontStyle: 'italic' }}>
                  {typeof turn.fallbackNotice === 'string' ? turn.fallbackNotice : JSON.stringify(turn.fallbackNotice)}
                </div>
              )}

              {turn.error && (
                <div role="alert" style={{ marginTop: '12px', display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                  <div style={{ color: '#B42318', fontSize: '13.5px', background: 'rgba(180, 35, 24, 0.08)', padding: '8px 12px', borderRadius: '8px', border: '1px solid rgba(180, 35, 24, 0.2)' }}>
                    {typeof turn.error === 'string' ? turn.error : (turn.error?.detail || turn.error?.message || JSON.stringify(turn.error))}
                  </div>
                  {onRetry && (
                    <button
                      type="button"
                      onClick={() => onRetry(turn.question)}
                      style={{
                        padding: '6px 12px',
                        fontSize: '12.5px',
                        fontWeight: 500,
                        borderRadius: '6px',
                        border: `1px solid ${TOKENS.colors.line}`,
                        background: TOKENS.colors.card,
                        color: TOKENS.colors.ink,
                        cursor: 'pointer'
                      }}
                    >
                      Retry
                    </button>
                  )}
                </div>
              )}

              {/* SOURCES & CITATIONS DRAWER */}
              {((turn.sources && turn.sources.length > 0) || (turn.citations && turn.citations.length > 0)) && !turn.isLoading && (
                <SourceCards
                  sources={turn.sources?.length ? turn.sources : turn.citations}
                  onImageClick={onPreviewImage}
                />
              )}

              {/* RESPONSE ACTIONS (COPY, RETRY, FEEDBACK, EXPORT) */}
              {!turn.isLoading && turn.answer && (
                <ResponseActions
                  text={typeof turn.answer === 'string' ? turn.answer : JSON.stringify(turn.answer)}
                  onRegenerate={onRetry ? () => onRetry(turn.question) : null}
                  hasSources={Boolean(turn.sources?.length || turn.citations?.length)}
                  sourcesCount={turn.sources?.length || turn.citations?.length || 0}
                  hasActivities={Boolean(turn.activities?.length)}
                  activitiesCount={turn.activities?.length || 0}
                  isDeepResearch={turn.mode === 'deep' || turn.isDeepResearch}
                />
              )}
            </div>
          </div>
        </motion.div>
      ))}
    </div>
  );
}

// ============================================================================
// USER MESSAGE ACTIONS
// ============================================================================
function MessageActions({ text, onEdit }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(text);
  const [copied, setCopied] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (editing) {
      ref.current?.focus();
      ref.current?.setSelectionRange(draft.length, draft.length);
    }
  }, [editing, draft.length]);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const a = document.createElement('textarea');
      a.value = text;
      a.style.position = 'fixed';
      a.style.opacity = '0';
      document.body.appendChild(a);
      a.select();
      document.execCommand('copy');
      a.remove();
    }
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  };

  if (editing) {
    return (
      <div className="mt-2 w-full rounded-xl border border-[var(--border-subtle)] bg-[var(--surface)] p-2">
        <textarea
          ref={ref}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Escape') {
              setDraft(text);
              setEditing(false);
            }
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter' && !e.nativeEvent.isComposing && draft.trim() && draft.trim() !== text.trim()) {
              setEditing(false);
              onEdit(draft.trim());
            }
          }}
          className="w-full resize-y bg-transparent p-2 text-sm outline-none"
          aria-label="Edit message"
        />
        <div className="flex justify-end gap-2">
          <button
            type="button"
            className="message-edit-secondary"
            onClick={() => {
              setDraft(text);
              setEditing(false);
            }}
          >
            Cancel
          </button>
          <button
            type="button"
            className="message-edit-primary"
            disabled={!draft.trim() || draft.trim() === text.trim()}
            onClick={() => {
              setEditing(false);
              onEdit(draft.trim());
            }}
          >
            Send
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="message-actions atlas-message-actions" aria-live="polite">
      <button
        type="button"
        className="message-action-button"
        aria-label="Copy message"
        title={copied ? 'Copied' : 'Copy message'}
        onClick={copy}
      >
        <CopyGlyph checked={copied} />
      </button>
      <button
        type="button"
        className="message-action-button"
        aria-label="Edit message"
        title="Edit message"
        onClick={() => {
          setDraft(text);
          setEditing(true);
        }}
      >
        <EditGlyph />
      </button>
      {copied && <span className="sr-only">Copied</span>}
    </div>
  );
}

function CopyGlyph({ checked }) {
  return checked ? (
    <svg aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="m5 12 4 4L19 6"/>
    </svg>
  ) : (
    <svg aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <rect x="9" y="9" width="11" height="11" rx="2"/>
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
    </svg>
  );
}

function EditGlyph() {
  return (
    <svg aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M12 20h9"/>
      <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4Z"/>
    </svg>
  );
}
