import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ProgressiveMarkdown from './ProgressiveMarkdown';
import AtlasLogo from './AtlasLogo';

// ============================================================================
// DESIGN SYSTEM TOKENS (Section 1)
// ============================================================================
const TOKENS = {
  fonts: {
    sans: '"Inter", "Segoe UI", -apple-system, system-ui, sans-serif',
    mono: '"SF Mono", ui-monospace, Menlo, monospace',
  },
  colors: {
    bg: 'var(--bg-main)', sidebar: 'var(--bg-left-nav)', ink: 'var(--text-main)', body: 'var(--text-body)',
    muted: 'var(--text-secondary)', line: 'var(--border-subtle)', yellow: 'var(--accent-yellow)',
    yellowDeep: 'var(--accent-yellow)', amber: 'var(--accent-amber)', orange: 'var(--accent-orange)',
    card: 'var(--surface)', hover: 'var(--surface-hover)', bubble: 'var(--surface-alt)', chip: 'var(--surface-alt)',
    amberChip: 'color-mix(in srgb, var(--accent-yellow) 18%, var(--surface))', amberBorder: 'var(--border-emphasis)',
  }
};

// ============================================================================
// INLINE NUCLEO-SHARP ICONS
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

function IconMenu({ size = 18, style = {} }) {
  return <svg width={size} height={size} style={style} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M4 6h16M4 12h16M4 18h16" /></svg>;
}

function IconUser({ size = 16, style = {} }) {
  return (
    <svg width={size} height={size} style={style} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" />
      <circle cx="12" cy="7" r="4" />
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

function IconSearch({ size = 16, style = {} }) {
  return (
    <svg width={size} height={size} style={style} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  );
}

function IconLayers({ size = 16, style = {} }) {
  return (
    <svg width={size} height={size} style={style} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="12 2 2 7 12 12 22 7 12 2" />
      <polyline points="2 17 12 22 22 17" />
      <polyline points="2 12 12 17 22 12" />
    </svg>
  );
}

function IconBook({ size = 16, style = {} }) {
  return (
    <svg width={size} height={size} style={style} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 19.5A2.5 2.5 0 016.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z" />
    </svg>
  );
}

function IconSparkle({ size = 14, style = {} }) {
  return (
    <svg width={size} height={size} style={style} viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 2l2.4 6.6L21 11l-6.6 2.4L12 20l-2.4-6.6L3 11l6.6-2.4z" />
    </svg>
  );
}

function IconChevronDown({ size = 14, style = {} }) {
  return (
    <svg width={size} height={size} style={style} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );
}

function IconCopy({ size = 16, style = {} }) {
  return (
    <svg width={size} height={size} style={style} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
      <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 v1" />
    </svg>
  );
}

function IconRotate({ size = 16, style = {} }) {
  return (
    <svg width={size} height={size} style={style} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="23 4 23 10 17 10" />
      <path d="M20.49 15a9 9 0 11-2.12-9.36L23 10" />
    </svg>
  );
}

function IconCheck({ size = 16, style = {} }) {
  return (
    <svg width={size} height={size} style={style} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

function IconGrid({ size = 16, style = {} }) {
  return (
    <svg width={size} height={size} style={style} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="7" height="7" />
      <rect x="14" y="3" width="7" height="7" />
      <rect x="14" y="14" width="7" height="7" />
      <rect x="3" y="14" width="7" height="7" />
    </svg>
  );
}

function IconFileExport({ size = 16, style = {} }) {
  return (
    <svg width={size} height={size} style={style} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="12" y1="18" x2="12" y2="12" />
      <polyline points="9 15 12 12 15 15" />
    </svg>
  );
}

function IconClock({ size = 14, style = {} }) {
  return (
    <svg width={size} height={size} style={style} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </svg>
  );
}

function IconMic({ size = 16, style = {} }) {
  return (
    <svg width={size} height={size} style={style} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2a3 3 0 00-3 3v7a3 3 0 006 0V5a3 3 0 00-3-3z" />
      <path d="M19 10v2a7 7 0 01-14 0v-2" />
      <line x1="12" y1="19" x2="12" y2="22" />
    </svg>
  );
}

// ============================================================================
// 2x3 PIXEL GRID LOGO
// ============================================================================
function AtlasPixelGrid({ cellSize = 7, gap = 2, heroMode = false }) {
  const pixelSize = heroMode ? 10 : cellSize;
  const gridGap = heroMode ? 3 : gap;
  const pixelColors = [
    ['#FFB000', TOKENS.colors.ink, '#FFB000'],
    ['#FFD800', '#FFD800', '#FFD800']
  ];

  return (
    <motion.div
      animate={{ y: [0, -3, 0] }}
      transition={{
        duration: 3.2,
        repeat: Infinity,
        repeatType: 'mirror',
        ease: 'easeInOut'
      }}
      style={{
        display: 'inline-grid',
        gridTemplateColumns: `repeat(3, ${pixelSize}px)`,
        gridTemplateRows: `repeat(2, ${pixelSize}px)`,
        gap: `${gridGap}px`,
        flexShrink: 0,
        userSelect: 'none'
      }}
    >
      {pixelColors.map((row, rIdx) =>
        row.map((color, cIdx) => {
          const idx = rIdx * 3 + cIdx;
          return (
            <motion.div
              key={`${rIdx}-${cIdx}`}
              initial={{ opacity: 0, scale: 0 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{
                delay: 0.15 + idx * 0.06,
                type: 'spring',
                stiffness: 300,
                damping: 18
              }}
              style={{
                width: `${pixelSize}px`,
                height: `${pixelSize}px`,
                backgroundColor: color,
                borderRadius: heroMode ? '2px' : '1px'
              }}
            />
          );
        })
      )}
    </motion.div>
  );
}

const THINKING_STEPS = [
  'Reading 42 sources',
  'Comparing 3 setups',
  'Checking for leakage',
  'Composing answer'
];

const RAW_ANSWER_CONTENT = {
  block1: `Good question — here's the short version, then the evidence.\n\n**Short answer.** Yes, but only when fine-tuning preserves the contrastive alignment. Zero-shot CLIP stays well-calibrated on in-domain data (ECE ≈ 0.06), while linear probing alone degrades confidence sharply (ECE ≈ 0.11).`,
  table: [
    { setup: 'Zero-shot CLIP', accuracy: '71.4%', ece: '0.060' },
    { setup: 'Linear probe', accuracy: '74.9%', ece: '0.112' },
    { setup: 'Contrastive + attention pooling', accuracy: '84.2%', ece: '0.041' }
  ],
  block3: `**Why it happens.** Linear probing optimizes the logit scale without touching the embedding geometry, so confidence and accuracy drift apart. Temperature scaling fixes most of it post-hoc, but a contrastive objective keeps calibration intact *during* training.\n\n**Caveat.** Under severe covariate shift, all methods overconfidence — the ECE gap narrows to noise. I'd treat the 63% improvement as in-domain only.\n\nWant me to escalate this into a full deep-research run with experiments?`
};

// ============================================================================
// MAIN COMPONENT
// ============================================================================
export default function AtlasLanding({ onSendMessage, onOpenAuth, onOpenSettings, conversationTurns = [], isPending = false, onNewChat, historyItems = [], onSelectHistoryItem, theme = 'system', onThemeChange, sidebarOpen = true, onToggleSidebar, historyLoadState = 'ready', activeConversationId, confidenceChecking = false, onEditMessage }) {
  // Step state: 0 (idle) -> 1 (thinking) -> 2 (streaming) -> 3 (done)
  const [step, setStep] = useState(0);
  const [inputText, setInputText] = useState('');
  const [userQuestion, setUserQuestion] = useState('');
  const [isDeepResearch, setIsDeepResearch] = useState(false);
  const [modelDropdownOpen, setModelDropdownOpen] = useState(false);
  const [selectedModel, setSelectedModel] = useState('Atlas Large');
  
  // Thinking state
  const [thinkingIndex, setThinkingIndex] = useState(0);
  
  // Typewriter state
  const [streamIndex, setStreamIndex] = useState(0);
  const [copied, setCopied] = useState(false);
  const hasConversation = conversationTurns.length > 0;

  const scrollRef = useRef(null);
  const inputRef = useRef(null);
  const fullTextLength = RAW_ANSWER_CONTENT.block1.length + RAW_ANSWER_CONTENT.block3.length + 80;

  useEffect(() => {
    const input = inputRef.current;
    if (!input) return;
    const mobile = window.matchMedia('(max-width: 640px)').matches;
    const maxHeight = Math.min(window.innerHeight * 0.4, mobile ? 240 : 360);
    input.style.height = 'auto';
    input.style.height = `${Math.min(input.scrollHeight, maxHeight)}px`;
    input.style.overflowY = input.scrollHeight > maxHeight ? 'auto' : 'hidden';
  }, [inputText]);

  // Auto-scroll on step / streaming change
  const scrollToBottom = () => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [step, thinkingIndex, streamIndex]);

  // STEP 1: Thinking timer (auto-advances after 1.7s)
  useEffect(() => {
    let intervalId;
    let transitionTimer;

    if (step === 1) {
      setThinkingIndex(0);
      intervalId = setInterval(() => {
        setThinkingIndex((prev) => (prev < THINKING_STEPS.length - 1 ? prev + 1 : prev));
      }, 380);

      transitionTimer = setTimeout(() => {
        setStep(2);
      }, 1700);
    }

    return () => {
      if (intervalId) clearInterval(intervalId);
      if (transitionTimer) clearTimeout(transitionTimer);
    };
  }, [step]);

  // STEP 2: Typewriter text streaming (3 chars per 12ms tick)
  useEffect(() => {
    let streamInterval;

    if (step === 2) {
      setStreamIndex(0);
      streamInterval = setInterval(() => {
        setStreamIndex((prev) => {
          if (prev < fullTextLength) {
            return prev + 3;
          } else {
            clearInterval(streamInterval);
            setStep(3);
            return prev;
          }
        });
      }, 12);
    }

    return () => {
      if (streamInterval) clearInterval(streamInterval);
    };
  }, [step, fullTextLength]);

  const handleSend = (text) => {
    const prompt = (text || inputText).trim();
    if (!prompt) return;

    if (onSendMessage) {
      onSendMessage(prompt, () => setInputText(''), { deepResearch: isDeepResearch, model: selectedModel });
    }
    // The landing component is input-only. Conversation state and the real
    // response stream belong to WorkspaceApp; keeping a local demo response
    // here caused the old CLIP/ECE fixture to appear for unrelated questions.
    setInputText('');
    return;
  };

  const handleCopy = () => {
    const textToCopy = `${RAW_ANSWER_CONTENT.block1}\n\n${RAW_ANSWER_CONTENT.block3}`;
    if (navigator.clipboard) {
      navigator.clipboard.writeText(textToCopy);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const renderFormattedText = (rawText, maxLen) => {
    const sliced = rawText.slice(0, maxLen);
    const parts = sliced.split(/(\*\*.*?\*\*)/g);
    return parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return (
          <strong key={i} style={{ color: TOKENS.colors.ink, fontWeight: 600 }}>
            {part.slice(2, -2)}
          </strong>
        );
      }
      return part;
    });
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
          {/* =================================================================== */}
          {/* SECTION 5: IDLE HERO */}
          {/* =================================================================== */}
          {conversationTurns.length > 0 ? (
            <ConversationThread turns={conversationTurns} isPending={isPending} confidenceChecking={confidenceChecking} onEditMessage={onEditMessage} />
          ) : step === 0 && (
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
                  <h1
                    style={{
                      fontSize: 'clamp(24px, 5.5vw, 42px)',
                      fontWeight: 400,
                      letterSpacing: '-0.02em',
                      color: TOKENS.colors.ink,
                      margin: 0,
                      padding: '0 16px',
                      lineHeight: '1.25'
                    }}
                  >
                    How can Atlas help you today?
                  </h1>

                </motion.div>
              </AnimatePresence>
            </div>
          )}

          {/* STEP ≥ 1: ACTIVE THREAD CONTENT */}
          {step >= 1 && (
            <div
              style={{
                width: '100%',
                maxWidth: '720px',
                margin: '0 auto',
                padding: '28px 24px 180px 24px',
                display: 'flex',
                flexDirection: 'column',
                gap: '24px'
              }}
            >
              {/* User Bubble */}
              <motion.div
                initial={{ opacity: 0, y: 14, scale: 0.96 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                transition={{ type: 'spring', stiffness: 260, damping: 22 }}
                style={{
                  alignSelf: 'flex-end',
                  maxWidth: '80%',
                  backgroundColor: TOKENS.colors.bubble,
                  color: TOKENS.colors.ink,
                  fontSize: '15px',
                  lineHeight: '1.5',
                  padding: '12px 18px',
                  borderRadius: '18px 18px 4px 18px'
                }}
              >
                {userQuestion || 'Do vision-language models stay calibrated under distribution shift?'}
              </motion.div>

              {/* Assistant Header & Response Container */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                {/* Avatar Tile + Header */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <div
                    style={{
                      width: '24px',
                      height: '24px',
                      borderRadius: '8px',
                      backgroundColor: TOKENS.colors.yellow,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: TOKENS.colors.ink
                    }}
                  >
                    <IconAtom size={14} style={{ color: TOKENS.colors.ink }} />
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ fontSize: '13px', fontWeight: 600, color: TOKENS.colors.ink }}>
                      Atlas
                    </span>
                    <span style={{ color: TOKENS.colors.muted, fontSize: '12px' }}>·</span>
                    <span
                      style={{
                        fontSize: '12px',
                        fontWeight: 500,
                        fontFamily: step === 1 ? TOKENS.fonts.mono : TOKENS.fonts.sans,
                        color: step === 1 ? TOKENS.colors.amber : TOKENS.colors.muted
                      }}
                    >
                      {step === 1 ? 'researching…' : ''}
                    </span>
                  </div>
                </div>

                {/* SECTION 8: THINKING STATE (step 1) */}
                {step === 1 && (
                  <div
                    style={{
                      paddingLeft: '34px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '12px',
                      maxWidth: '480px'
                    }}
                  >
                    <div
                      style={{
                        width: '100%',
                        height: '3px',
                        backgroundColor: TOKENS.colors.line,
                        borderRadius: '999px',
                        overflow: 'hidden',
                        position: 'relative'
                      }}
                    >
                      <motion.div
                        initial={{ width: '0%' }}
                        animate={{ width: '100%' }}
                        transition={{ duration: 1.7, ease: 'easeInOut' }}
                        style={{
                          height: '100%',
                          background: `linear-gradient(90deg, ${TOKENS.colors.yellow} 0%, ${TOKENS.colors.amber} 100%)`,
                          borderRadius: '999px'
                        }}
                      />
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {THINKING_STEPS.map((stepText, idx) => {
                        if (idx > thinkingIndex) return null;
                        const isActive = idx === thinkingIndex;

                        return (
                          <motion.div
                            key={stepText}
                            initial={{ opacity: 0, x: -10, filter: 'blur(3px)' }}
                            animate={{ opacity: 1, x: 0, filter: 'blur(0px)' }}
                            transition={{ type: 'spring', stiffness: 220, damping: 20 }}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: '10px',
                              fontSize: '13px'
                            }}
                          >
                            {isActive ? (
                              <div
                                style={{
                                  width: '12px',
                                  height: '12px',
                                  borderRadius: '50%',
                                  border: `2px solid ${TOKENS.colors.amber}`,
                                  borderTopColor: 'transparent',
                                  animation: 'spin 0.85s linear infinite',
                                  flexShrink: 0
                                }}
                              />
                            ) : (
                              <IconCheck size={14} style={{ color: TOKENS.colors.amber, flexShrink: 0 }} />
                            )}
                            <span
                              style={{
                                color: isActive ? TOKENS.colors.ink : TOKENS.colors.muted,
                                fontWeight: isActive ? 500 : 400
                              }}
                            >
                              {stepText}
                            </span>
                          </motion.div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* SECTION 9 & 10: STREAMING & DONE ANSWER */}
                {step >= 2 && (
                  <div
                    style={{
                      paddingLeft: '34px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '16px',
                      fontSize: '15px',
                      color: TOKENS.colors.body,
                      lineHeight: '1.6'
                    }}
                  >
                    {/* Block 1 */}
                    <div>
                      {renderFormattedText(RAW_ANSWER_CONTENT.block1, streamIndex)}
                      {streamIndex < RAW_ANSWER_CONTENT.block1.length && (
                        <span
                          style={{
                            display: 'inline-block',
                            width: '8px',
                            height: '16px',
                            backgroundColor: TOKENS.colors.yellowDeep,
                            marginLeft: '2px',
                            verticalAlign: 'middle',
                            animation: 'blink 0.9s infinite'
                          }}
                        />
                      )}
                    </div>

                    {/* Results Table (Cascading Rows & Hover Highlight) */}
                    {streamIndex >= RAW_ANSWER_CONTENT.block1.length && (
                      <motion.div
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.35, ease: 'easeOut' }}
                        style={{
                          border: `1px solid ${TOKENS.colors.line}`,
                          borderRadius: '12px',
                          overflow: 'hidden',
                          backgroundColor: TOKENS.colors.card,
                          margin: '6px 0',
                          boxShadow: '0 2px 8px rgba(0,0,0,0.02)'
                        }}
                      >
                        <div
                          style={{
                            display: 'flex',
                            backgroundColor: 'var(--surface)',
                            borderBottom: `1px solid ${TOKENS.colors.line}`,
                            padding: '9px 14px',
                            fontSize: '13px',
                            fontWeight: 600,
                            color: TOKENS.colors.ink
                          }}
                        >
                          <div style={{ flex: 2, textAlign: 'left' }}>Setup</div>
                          <div style={{ flex: 1, textAlign: 'right' }}>Accuracy</div>
                          <div style={{ flex: 1, textAlign: 'right' }}>ECE</div>
                        </div>

                        {RAW_ANSWER_CONTENT.table.map((row, rIdx) => (
                          <motion.div
                            key={row.setup}
                            initial={{ opacity: 0, y: 6 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: rIdx * 0.1, duration: 0.25 }}
                            whileHover={{ backgroundColor: TOKENS.colors.hover }}
                            style={{
                              display: 'flex',
                              padding: '9px 14px',
                              fontSize: '13px',
                              color: TOKENS.colors.body,
                              borderTop: rIdx > 0 ? `1px solid ${TOKENS.colors.line}99` : 'none',
                              transition: 'background-color 0.15s ease'
                            }}
                          >
                            <div style={{ flex: 2, textAlign: 'left', fontWeight: 500, color: TOKENS.colors.ink }}>
                              {row.setup}
                            </div>
                            <div style={{ flex: 1, textAlign: 'right', fontFamily: TOKENS.fonts.mono, fontSize: '12px' }}>
                              {row.accuracy}
                            </div>
                            <div style={{ flex: 1, textAlign: 'right', fontFamily: TOKENS.fonts.mono, fontSize: '12px' }}>
                              {row.ece}
                            </div>
                          </motion.div>
                        ))}
                      </motion.div>
                    )}

                    {/* Block 3 Text Streaming After Table */}
                    {streamIndex >= RAW_ANSWER_CONTENT.block1.length && (
                      <div>
                        {renderFormattedText(
                          RAW_ANSWER_CONTENT.block3,
                          Math.max(0, streamIndex - RAW_ANSWER_CONTENT.block1.length)
                        )}
                        {streamIndex < fullTextLength && (
                          <span
                            style={{
                              display: 'inline-block',
                              width: '8px',
                              height: '16px',
                              backgroundColor: TOKENS.colors.yellowDeep,
                              marginLeft: '2px',
                              verticalAlign: 'middle',
                              animation: 'blink 0.9s infinite'
                            }}
                          />
                        )}
                      </div>
                    )}

                    {/* =================================================================== */}
                    {/* SECTION 10: DONE STATE (step 3) */}
                    {/* Action dock under answer: copy / retry (spins 180° hover) / microscope / export */}
                    {/* =================================================================== */}
                    {step === 3 && (
                      <motion.div
                        initial={{ opacity: 0, y: 6 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.25 }}
                        style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '14px' }}
                      >
                        {/* Copy Button */}
                        <motion.button
                          type="button"
                          onClick={handleCopy}
                          initial={{ scale: 0, opacity: 0 }}
                          animate={{ scale: 1, opacity: 1 }}
                          whileHover={{ scale: 1.15, y: -2 }}
                          transition={{ delay: 0.05, type: 'spring', stiffness: 350, damping: 20 }}
                          style={{
                            width: '32px',
                            height: '32px',
                            borderRadius: '8px',
                            border: `1px solid ${TOKENS.colors.line}`,
                            backgroundColor: TOKENS.colors.card,
                            color: copied ? TOKENS.colors.amber : TOKENS.colors.muted,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            cursor: 'pointer',
                            boxShadow: '0 1px 4px rgba(0,0,0,0.03)'
                          }}
                          title="Copy response"
                        >
                          {copied ? <IconCheck size={14} style={{ color: TOKENS.colors.amber }} /> : <IconCopy size={14} />}
                        </motion.button>

                        {/* Retry Button (Spins 180° on Hover) */}
                        <motion.button
                          type="button"
                          onClick={() => setStep(1)}
                          initial={{ scale: 0, opacity: 0 }}
                          animate={{ scale: 1, opacity: 1 }}
                          whileHover={{ rotate: 180, scale: 1.15, y: -2 }}
                          transition={{ delay: 0.1, type: 'spring', stiffness: 350, damping: 20 }}
                          style={{
                            width: '32px',
                            height: '32px',
                            borderRadius: '8px',
                            border: `1px solid ${TOKENS.colors.line}`,
                            backgroundColor: TOKENS.colors.card,
                            color: TOKENS.colors.muted,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            cursor: 'pointer',
                            boxShadow: '0 1px 4px rgba(0,0,0,0.03)'
                          }}
                          title="Regenerate"
                        >
                          <IconRotate size={14} />
                        </motion.button>

                        {/* Microscope / Deep Research Button */}
                        <motion.button
                          type="button"
                          onClick={() => setIsDeepResearch(true)}
                          initial={{ scale: 0, opacity: 0 }}
                          animate={{ scale: 1, opacity: 1 }}
                          whileHover={{ scale: 1.15, y: -2 }}
                          transition={{ delay: 0.15, type: 'spring', stiffness: 350, damping: 20 }}
                          style={{
                            width: '32px',
                            height: '32px',
                            borderRadius: '8px',
                            border: `1px solid ${TOKENS.colors.amberBorder}`,
                            backgroundColor: TOKENS.colors.amberChip,
                            color: TOKENS.colors.amber,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            cursor: 'pointer',
                            boxShadow: '0 1px 4px rgba(0,0,0,0.03)'
                          }}
                          title="Escalate to Deep Research"
                        >
                          <IconMicroscope size={14} style={{ color: TOKENS.colors.amber }} />
                        </motion.button>

                        {/* Export Report Button */}
                        <motion.button
                          type="button"
                          initial={{ scale: 0, opacity: 0 }}
                          animate={{ scale: 1, opacity: 1 }}
                          whileHover={{ scale: 1.15, y: -2 }}
                          transition={{ delay: 0.2, type: 'spring', stiffness: 350, damping: 20 }}
                          style={{
                            width: '32px',
                            height: '32px',
                            borderRadius: '8px',
                            border: `1px solid ${TOKENS.colors.line}`,
                            backgroundColor: TOKENS.colors.card,
                            color: TOKENS.colors.muted,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            cursor: 'pointer',
                            boxShadow: '0 1px 4px rgba(0,0,0,0.03)'
                          }}
                          title="Export structured report"
                        >
                          <IconFileExport size={14} />
                        </motion.button>
                      </motion.div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* =================================================================== */}
        {/* SECTION 7: PROMPT DOCK */}
        {/* =================================================================== */}
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
            style={{
              width: 'min(100%, 760px)',
              maxWidth: '760px',
              minHeight: '0',
              height: 'auto',
              backgroundColor: TOKENS.colors.card,
              border: `1px solid ${TOKENS.colors.line}`,
              borderRadius: '28px',
              boxShadow: '0 4px 20px rgba(0,0,0,0.06)',
              padding: '16px 20px',
              pointerEvents: 'auto',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '10px'
            }}
          >
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
              placeholder="Ask Atlas"
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
                lineHeight: '1.4',
                paddingTop: '2px',
                minHeight: '26px',
                overflowY: 'auto'
              }}
            />

            {/* Right Action Stack: Dropdown + Mic + Send */}
            <div className="atlas-composer-controls" style={{ display: 'flex', alignItems: 'center', gap: '6px', width: '100%', flexShrink: 0, position: 'relative' }}>
              {/* Model Dropdown */}
              <div style={{ position: 'relative' }}>
                <button
                  type="button"
                  onClick={() => setModelDropdownOpen(!modelDropdownOpen)}
                  style={{
                    height: '34px',
                    padding: '0 10px',
                    borderRadius: '999px',
                    border: `1px solid ${TOKENS.colors.line}`,
                    backgroundColor: 'transparent',
                    fontSize: '12.5px',
                    fontWeight: 500,
                    color: TOKENS.colors.body,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    cursor: 'pointer'
                  }}
                >
                  <IconSparkle size={13} style={{ color: TOKENS.colors.amber }} />
                  <span className="atlas-model-label">{selectedModel}</span>
                  <IconChevronDown size={13} style={{ color: TOKENS.colors.muted }} />
                </button>

                {modelDropdownOpen && (
                  <div
                    style={{
                      position: 'absolute',
                      left: 0,
                      bottom: '38px',
                      width: '150px',
                      backgroundColor: TOKENS.colors.card,
                      border: `1px solid ${TOKENS.colors.line}`,
                      borderRadius: '12px',
                      boxShadow: '0 8px 24px rgba(0,0,0,0.1)',
                      padding: '4px 0',
                      zIndex: 50
                    }}
                  >
                    {['Atlas Large', 'Atlas Fast', 'Atlas Reasoning'].map((m) => (
                      <button
                        key={m}
                        type="button"
                        onClick={() => {
                          setSelectedModel(m);
                          setModelDropdownOpen(false);
                        }}
                        style={{
                          width: '100%',
                          textAlign: 'left',
                          padding: '6px 12px',
                          border: 'none',
                          backgroundColor: 'transparent',
                          fontSize: '12px',
                          fontWeight: selectedModel === m ? 600 : 400,
                          color: TOKENS.colors.ink,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          cursor: 'pointer'
                        }}
                      >
                        <span>{m}</span>
                        {selectedModel === m && <IconCheck size={12} style={{ color: TOKENS.colors.amber }} />}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Deep Research chip */}
              <button
                type="button"
                onClick={() => setIsDeepResearch(!isDeepResearch)}
                aria-label="Deep research"
                aria-pressed={isDeepResearch}
                title="Deep research"
                style={{
                  height: '34px',
                  borderRadius: '999px',
                  padding: '0 10px',
                  border: `1px solid ${isDeepResearch ? TOKENS.colors.amberBorder : TOKENS.colors.line}`,
                  backgroundColor: isDeepResearch ? TOKENS.colors.amberChip : TOKENS.colors.card,
                  color: isDeepResearch ? TOKENS.colors.amber : TOKENS.colors.body,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  cursor: 'pointer'
                }}
              >
                <IconMicroscope size={13} style={{ color: isDeepResearch ? TOKENS.colors.amber : TOKENS.colors.body }} />
                <span className="atlas-research-label" style={{ fontSize: '12.5px' }}>Deep research</span>
              </button>

              {/* Solid Black Circular Send Button */}
              <motion.button
                type="button"
                className="atlas-send-button"
                onClick={() => handleSend()}
                disabled={!inputText.trim()}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                style={{
                  width: '36px',
                  height: '36px',
                  borderRadius: '50%',
                  backgroundColor: TOKENS.colors.ink,
                  border: 'none',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'var(--surface)',
                  cursor: inputText.trim() ? 'pointer' : 'default',
                  opacity: inputText.trim() ? 1 : 0.35,
                  flexShrink: 0,
                  marginLeft: 'auto'
                }}
              >
                <IconPaperPlane2 size={16} style={{ color: 'var(--surface)' }} />
              </motion.button>
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

      {/* Global CSS keyframes for spinner and blinking cursor */}
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
        @keyframes blink {
          0%, 100% { opacity: 1; }
          50% { opacity: 0; }
        }
      `}</style>
    </div>
  );
}

function ConversationThread({ turns, isPending, confidenceChecking = false, onEditMessage }) {
  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: '42px 24px calc(176px + 24px)', width: '100%', maxWidth: '900px', margin: '0 auto' }}>
      {turns.map((turn) => (
          <motion.div
            key={turn.id}
            className="atlas-message-enter"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
            style={{ marginBottom: '34px' }}
          >
          <div className="atlas-user-message-wrap" style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '22px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', maxWidth: '78%' }}>
              <div style={{ background: TOKENS.colors.bubble, borderRadius: '16px 16px 4px 16px', padding: '14px 18px', color: TOKENS.colors.ink, fontSize: '15px', lineHeight: 1.5, overflowWrap: 'anywhere' }}>{turn.question}</div>
              <MessageActions text={turn.question || ''} onEdit={(value) => onEditMessage?.(turns.indexOf(turn), value)} />
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'flex-start' }}>
            <div style={{ flex: 1, color: TOKENS.colors.body, fontSize: '16px', lineHeight: 1.7, minWidth: 0 }}>
              {turn.isLoading && !turn.answer ? <div style={{ color: TOKENS.colors.muted }}>Preparing a verified answer…</div> : <ProgressiveMarkdown content={turn.answer || ''} streaming={Boolean(turn.isLoading)} instant={Boolean(turn.loadedFromHistory)} deliveryPath={turn.loadedFromHistory ? 'loaded from history' : 'new answer'} />}
              {turn.error ? <div role="alert" style={{ color: '#B42318', marginTop: '8px' }}>{turn.error}</div> : null}
            </div>
          </div>
        </motion.div>
      ))}
    </div>
  );
}

function MessageActions({ text, onEdit }) {
  const [editing, setEditing] = useState(false); const [draft, setDraft] = useState(text); const [copied, setCopied] = useState(false); const ref = useRef(null);
  useEffect(() => { if (editing) { ref.current?.focus(); ref.current?.setSelectionRange(draft.length, draft.length); } }, [editing]);
  const copy = async () => { try { await navigator.clipboard.writeText(text); } catch { const a = document.createElement('textarea'); a.value = text; a.style.position = 'fixed'; a.style.opacity = '0'; document.body.appendChild(a); a.select(); document.execCommand('copy'); a.remove(); } setCopied(true); window.setTimeout(() => setCopied(false), 1500); };
  if (editing) return <div className="mt-2 w-full rounded-xl border border-[var(--border-subtle)] bg-[var(--surface)] p-2"><textarea ref={ref} value={draft} onChange={(e) => setDraft(e.target.value)} onKeyDown={(e) => { if (e.key === 'Escape') { setDraft(text); setEditing(false); } if ((e.ctrlKey || e.metaKey) && e.key === 'Enter' && !e.nativeEvent.isComposing && draft.trim() && draft.trim() !== text.trim()) { setEditing(false); onEdit(draft.trim()); } }} className="w-full resize-y bg-transparent p-2 text-sm outline-none" aria-label="Edit message" /><div className="flex justify-end gap-2"><button type="button" className="message-edit-secondary" onClick={() => { setDraft(text); setEditing(false); }}>Cancel</button><button type="button" className="message-edit-primary" disabled={!draft.trim() || draft.trim() === text.trim()} onClick={() => { setEditing(false); onEdit(draft.trim()); }}>Send</button></div></div>;
  return <div className="message-actions atlas-message-actions" aria-live="polite"><button type="button" className="message-action-button" aria-label="Copy message" title={copied ? 'Copied' : 'Copy message'} onClick={copy}><CopyGlyph checked={copied} /></button><button type="button" className="message-action-button" aria-label="Edit message" title="Edit message" onClick={() => { setDraft(text); setEditing(true); }}><EditGlyph /></button>{copied && <span className="sr-only">Copied</span>}</div>;
}
function CopyGlyph({ checked }) { return checked ? <svg aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="m5 12 4 4L19 6"/></svg> : <svg aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>; }
function EditGlyph() { return <svg aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4Z"/></svg>; }
