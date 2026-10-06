import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ChatMarkdown from './ChatMarkdown';
import ConfidenceBlock from './ConfidenceBlock';

// ============================================================================
// DESIGN SYSTEM TOKENS (Section 1)
// ============================================================================
const TOKENS = {
  fonts: {
    sans: '"Inter", "Segoe UI", -apple-system, system-ui, sans-serif',
    mono: '"SF Mono", ui-monospace, Menlo, monospace',
  },
  colors: {
    bg: '#FAFAF9',
    sidebar: '#F4F4F2',
    ink: '#0D0C0A',
    body: '#44403B',
    muted: '#A8A29E',
    line: '#E9E7E1',
    yellow: '#FFD800',
    yellowDeep: '#F5C900',
    amber: '#B8890A',
    orange: '#FA500F',
    card: '#FFFFFF',
    hover: 'rgba(0,0,0,0.035)',
    bubble: '#F0EFEB',
    chip: '#E8E3D8',
    amberChip: '#FCF7DF',
    amberBorder: '#F0E2A8',
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

// ============================================================================
// SECTION 6 & 10: SUGGESTION CARDS DATA & COMPONENT
// ============================================================================
const SUGGESTION_CARDS = [
  {
    id: 'deep-research',
    title: 'Run deep research',
    sub: 'on distribution shifts',
    prompt: 'Do vision-language models stay calibrated under distribution shift?',
    icon: IconMicroscope
  },
  {
    id: 'literature-search',
    title: 'Search literature',
    sub: 'arXiv & Semantic Scholar',
    prompt: 'Search arXiv literature for recent vision transformer calibration papers',
    icon: IconSearch
  },
  {
    id: 'benchmark-leakage',
    title: 'Audit benchmark leakage',
    sub: 'tabular & vision tasks',
    prompt: 'Check for data leakage risks in open ML benchmark evaluations',
    icon: IconLayers
  },
  {
    id: 'synthesize-findings',
    title: 'Synthesize findings',
    sub: 'generate structured report',
    prompt: 'Synthesize a formal research report comparing contrastive vs linear probing calibration',
    icon: IconBook
  }
];

function SuggestionCardGrid({ onSelectPrompt }) {
  const [hoveredId, setHoveredId] = useState(null);

  return (
    <div className="grid grid-cols-2 sm:grid-cols-2 md:grid-cols-4 gap-3 max-w-2xl mx-auto mt-6 px-3 sm:px-0">
      {SUGGESTION_CARDS.map((card, idx) => {
        const IconComponent = card.icon;
        const isHovered = hoveredId === card.id;

        return (
          <motion.button
            key={card.id}
            type="button"
            onClick={() => onSelectPrompt(card.prompt)}
            onHoverStart={() => setHoveredId(card.id)}
            onHoverEnd={() => setHoveredId(null)}
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            whileHover={{ y: -4, boxShadow: '0 8px 20px rgba(20,18,10,0.08)' }}
            transition={{
              delay: 0.1 + idx * 0.06,
              type: 'spring',
              stiffness: 300,
              damping: 22
            }}
            className="w-full bg-white border border-[#E9E7E1] rounded-2xl p-3 flex flex-col items-start text-left gap-2 sm:gap-2.5 cursor-pointer shadow-sm hover:border-[#FFD800] transition-colors"
          >
            <motion.div
              animate={isHovered ? { scale: 1.1, rotate: [-3, 3, 0] } : { scale: 1, rotate: 0 }}
              transition={{ type: 'spring', stiffness: 400, damping: 18 }}
              className="w-7 h-7 rounded-lg bg-[#FCF7DF] border border-[#F0E2A8] flex items-center justify-center text-[#B8890A] shrink-0"
            >
              <IconComponent size={14} style={{ color: TOKENS.colors.amber }} />
            </motion.div>

            <div className="flex flex-col gap-0.5 min-w-0 w-full">
              <span className="text-xs font-semibold text-[#0D0C0A] leading-tight truncate w-full">
                {card.title}
              </span>
              <span className="text-[10.5px] text-[#A8A29E] leading-tight truncate w-full">
                {card.sub}
              </span>
            </div>
          </motion.button>
        );
      })}
    </div>
  );
}

// ============================================================================
// MOCK DATA & CONSTANTS
// ============================================================================
const MOCK_HISTORY = [
  {
    group: 'Today',
    items: [
      { id: '1', title: 'Calibration under distribution shift', type: 'Deep research' },
      { id: '2', title: 'Explain diffusion schedulers simply', type: 'Chat' }
    ]
  },
  {
    group: 'Yesterday',
    items: [
      { id: '3', title: 'Leakage in tabular benchmarks', type: 'Deep research' },
      { id: '4', title: 'Summarize attention paper', type: 'Chat' }
    ]
  },
  {
    group: '3 days ago',
    items: [
      { id: '5', title: 'LoRA rank ablation plan', type: 'Experiments' }
    ]
  },
  {
    group: 'Last week',
    items: [
      { id: '6', title: 'Dataset recommendations for OOD eval', type: 'Chat' }
    ]
  }
];

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

function getInitials(name) {
  if (!name || typeof name !== 'string') return 'US';
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================
export default function AtlasLanding({ onSendMessage, onOpenAuth, onOpenSettings, conversationTurns = [], isPending = false, onNewChat, userProfile = {} }) {
  // Step state: 0 (idle) -> 1 (thinking) -> 2 (streaming) -> 3 (done)
  const [step, setStep] = useState(0);
  const [inputText, setInputText] = useState('');
  const [userQuestion, setUserQuestion] = useState('');
  const [isDeepResearch, setIsDeepResearch] = useState(true);
  const [modelDropdownOpen, setModelDropdownOpen] = useState(false);
  const [selectedModel, setSelectedModel] = useState('Atlas Large');
  
  // Thinking state
  const [thinkingIndex, setThinkingIndex] = useState(0);
  
  // Typewriter state
  const [streamIndex, setStreamIndex] = useState(0);
  const [copied, setCopied] = useState(false);

  const scrollRef = useRef(null);
  const fullTextLength = RAW_ANSWER_CONTENT.block1.length + RAW_ANSWER_CONTENT.block3.length + 80;

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
      onSendMessage(prompt, () => setInputText(''));
    }
    // The landing component is input-only. Conversation state and the real
    // response stream belong to WorkspaceApp; keeping a local demo response
    // here caused the old CLIP/ECE fixture to appear for unrelated questions.
    setInputText('');
    return;
  };

  const handleNewChat = () => {
    if (onNewChat) onNewChat();
    setStep(0);
    setUserQuestion('');
    setInputText('');
    setThinkingIndex(0);
    setStreamIndex(0);
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
      style={{
        height: '100vh',
        width: '100vw',
        display: 'flex',
        flexDirection: 'row',
        overflow: 'hidden',
        backgroundColor: TOKENS.colors.bg,
        fontFamily: TOKENS.fonts.sans,
        color: TOKENS.colors.ink,
        WebkitFontSmoothing: 'antialiased'
      }}
    >
      {/* =================================================================== */}
      {/* SECTION 3: SIDEBAR */}
      {/* =================================================================== */}
      <aside
        style={{
          width: '262px',
          backgroundColor: TOKENS.colors.sidebar,
          borderRight: `1px solid ${TOKENS.colors.line}`,
          display: 'flex',
          flexDirection: 'column',
          flexShrink: 0,
          height: '100%'
        }}
      >
        {/* Top Header Row */}
        <div
          style={{
            height: '52px',
            padding: '0 16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexShrink: 0
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AtlasPixelGrid cellSize={7} gap={2} />
            <span style={{ fontSize: '15px', fontWeight: 700, letterSpacing: '-0.01em', color: TOKENS.colors.ink }}>
              Atlas
            </span>
          </div>
          <IconGrid size={16} style={{ color: TOKENS.colors.muted, cursor: 'pointer' }} />
        </div>

        {/* "New Chat" White Pill Button */}
        <div style={{ padding: '4px 14px 12px 14px', flexShrink: 0 }}>
          <motion.button
            type="button"
            onClick={handleNewChat}
            whileHover={{ scale: 1.01 }}
            whileTap={{ scale: 0.98 }}
            transition={{ type: 'spring', stiffness: 400, damping: 22 }}
            style={{
              width: '100%',
              height: '42px',
              backgroundColor: TOKENS.colors.card,
              border: `1px solid ${TOKENS.colors.line}`,
              borderRadius: '12px',
              boxShadow: '0 2px 6px rgba(0,0,0,0.03)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              fontSize: '13.5px',
              fontWeight: 600,
              color: TOKENS.colors.ink,
              cursor: 'pointer'
            }}
          >
            <IconPlus size={15} style={{ color: TOKENS.colors.ink }} />
            <span>New chat</span>
          </motion.button>
        </div>

        {/* History Grouped by Date */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '0 10px 12px 10px',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px'
          }}
        >
          {MOCK_HISTORY.map((group, groupIdx) => (
            <motion.div
              key={group.group}
              initial={{ opacity: 0, x: -12 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.1 + groupIdx * 0.08, type: 'spring', stiffness: 300, damping: 22 }}
            >
              <div
                style={{
                  fontSize: '11px',
                  fontWeight: 600,
                  color: TOKENS.colors.muted,
                  padding: '0 8px 6px 8px'
                }}
              >
                {group.group}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                {group.items.map((chat) => (
                  <motion.button
                    key={chat.id}
                    type="button"
                    onClick={() => handleSend(chat.title)}
                    whileHover={{ x: 4, backgroundColor: TOKENS.colors.hover }}
                    transition={{ type: 'spring', stiffness: 400, damping: 22 }}
                    style={{
                      width: '100%',
                      textAlign: 'left',
                      padding: '7px 8px',
                      borderRadius: '9px',
                      border: 'none',
                      backgroundColor: 'transparent',
                      fontSize: '12.5px',
                      color: TOKENS.colors.body,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      cursor: 'pointer'
                    }}
                  >
                    <span
                      style={{
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        paddingRight: '6px'
                      }}
                    >
                      {chat.title}
                    </span>
                    {chat.type === 'Deep research' && (
                      <IconMicroscope size={13} style={{ color: TOKENS.colors.amber, flexShrink: 0 }} />
                    )}
                  </motion.button>
                ))}
              </div>
            </motion.div>
          ))}
        </div>

        {/* Bottom Profile Row */}
        <div
          onClick={() => (onOpenSettings ? onOpenSettings() : onOpenAuth && onOpenAuth())}
          style={{
            padding: '12px 14px',
            borderTop: `1px solid ${TOKENS.colors.line}`,
            backgroundColor: TOKENS.colors.sidebar,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexShrink: 0,
            cursor: 'pointer'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '26px',
                height: '26px',
                borderRadius: '50%',
                backgroundColor: TOKENS.colors.chip,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '11px',
                fontWeight: 700,
                color: TOKENS.colors.ink
              }}
            >
              {getInitials(userProfile?.name || 'Toshit Sai Galam')}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontSize: '13px', fontWeight: 600, color: TOKENS.colors.ink, lineHeight: 1.2 }}>
                {userProfile?.name || 'Toshit Sai Galam'}
              </span>
              <span style={{ fontSize: '11px', color: TOKENS.colors.muted, lineHeight: 1.2 }}>
                {userProfile?.role || 'Pro · Research'}
              </span>
            </div>
          </div>
          <IconUser size={15} style={{ color: TOKENS.colors.muted }} />
        </div>
      </aside>

      {/* =================================================================== */}
      {/* MAIN WORKSPACE */}
      {/* =================================================================== */}
      <main
        style={{
          flex: 1,
          position: 'relative',
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
          overflow: 'hidden',
          backgroundColor: TOKENS.colors.bg
        }}
      >
        {/* =================================================================== */}
        {/* SECTION 4: HEADER */}
        {/* =================================================================== */}
        <header
          style={{
            height: '52px',
            padding: '0 24px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: step >= 1 ? `1px solid ${TOKENS.colors.line}` : 'none',
            flexShrink: 0,
            transition: 'border-color 0.3s ease'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0, paddingRight: '16px' }}>
            {step >= 1 && (
              <motion.span
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
                style={{
                  fontSize: '13.5px',
                  fontWeight: 600,
                  color: TOKENS.colors.ink,
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis'
                }}
              >
                {userQuestion || 'Do vision-language models stay calibrated under distribution shift?'}
              </motion.span>
            )}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexShrink: 0 }}>
            {step === 1 ? (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '5px',
                  fontSize: '11px',
                  fontFamily: TOKENS.fonts.mono,
                  color: TOKENS.colors.amber
                }}
              >
                <IconClock size={13} style={{ color: TOKENS.colors.amber }} />
                <span>researching…</span>
              </motion.div>
            ) : step >= 2 ? (
              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                style={{
                  fontSize: '11px',
                  fontFamily: TOKENS.fonts.mono,
                  color: TOKENS.colors.muted
                }}
              >
                working
              </motion.span>
            ) : null}
          </div>
        </header>

        {/* Scroll Area */}
        <div
          ref={scrollRef}
          style={{
            flex: 1,
            overflowY: 'auto',
            display: 'flex',
            flexDirection: 'column',
            position: 'relative'
          }}
        >
          {/* =================================================================== */}
          {/* SECTION 5: IDLE HERO */}
          {/* =================================================================== */}
          {conversationTurns.length > 0 ? (
            <ConversationThread turns={conversationTurns} isPending={isPending} />
          ) : step === 0 && (
            <div
              style={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                paddingBottom: '140px'
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
                    textAlign: 'center'
                  }}
                >
                  <div style={{ marginBottom: '16px' }}>
                    <AtlasPixelGrid cellSize={10} gap={3} heroMode={true} />
                  </div>

                  <h1
                    style={{
                      fontSize: '30px',
                      fontWeight: 700,
                      letterSpacing: '-0.02em',
                      color: TOKENS.colors.ink,
                      margin: 0
                    }}
                  >
                    Hello, {(userProfile?.name || 'Toshit Sai Galam').split(' ')[0]}.
                  </h1>

                  <p
                    style={{
                      fontSize: '15px',
                      color: TOKENS.colors.muted,
                      marginTop: '6px',
                      marginBottom: 0
                    }}
                  >
                    What can Atlas research for you today?
                  </p>

                  <SuggestionCardGrid onSelectPrompt={handleSend} />
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
                            backgroundColor: '#FBFAF7',
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
            position: 'absolute',
            bottom: 0,
            left: 0,
            right: 0,
            pointerEvents: 'none',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            background: 'linear-gradient(to top, #FAFAF9 65%, transparent)',
            padding: '0 24px 20px 24px',
            zIndex: 10
          }}
        >
          <div
            style={{
              width: '100%',
              maxWidth: '720px',
              backgroundColor: TOKENS.colors.card,
              border: `1px solid ${TOKENS.colors.line}`,
              borderRadius: '22px',
              boxShadow: '0 8px 30px rgba(20,18,10,0.07)',
              padding: '10px 12px 8px 12px',
              pointerEvents: 'auto',
              display: 'flex',
              flexDirection: 'column',
              gap: '8px'
            }}
          >
            <textarea
              rows={step === 0 ? 2 : 1}
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder="Ask Atlas anything — research, code, experiments..."
              style={{
                width: '100%',
                backgroundColor: 'transparent',
                border: 'none',
                outline: 'none',
                resize: 'none',
                fontFamily: TOKENS.fonts.sans,
                fontSize: '15px',
                color: TOKENS.colors.ink,
                lineHeight: '1.4'
              }}
            />

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', position: 'relative' }}>
                <div style={{ position: 'relative' }}>
                  <button
                    type="button"
                    onClick={() => setModelDropdownOpen(!modelDropdownOpen)}
                    style={{
                      height: '28px',
                      padding: '0 10px',
                      borderRadius: '999px',
                      border: `1px solid ${TOKENS.colors.line}`,
                      backgroundColor: TOKENS.colors.card,
                      fontSize: '12px',
                      fontWeight: 500,
                      color: TOKENS.colors.ink,
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      cursor: 'pointer'
                    }}
                  >
                    <IconSparkle size={13} style={{ color: TOKENS.colors.amber }} />
                    <span>{selectedModel}</span>
                    <IconChevronDown size={13} style={{ color: TOKENS.colors.muted }} />
                  </button>

                  {modelDropdownOpen && (
                    <div
                      style={{
                        position: 'absolute',
                        left: 0,
                        bottom: '34px',
                        width: '160px',
                        backgroundColor: TOKENS.colors.card,
                        border: `1px solid ${TOKENS.colors.line}`,
                        borderRadius: '12px',
                        boxShadow: '0 8px 20px rgba(0,0,0,0.08)',
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

                <button
                  type="button"
                  onClick={() => setIsDeepResearch(!isDeepResearch)}
                  style={{
                    height: '28px',
                    padding: '0 10px',
                    borderRadius: '999px',
                    border: isDeepResearch ? `1px solid ${TOKENS.colors.amberBorder}` : `1px solid ${TOKENS.colors.line}`,
                    backgroundColor: isDeepResearch ? TOKENS.colors.amberChip : 'transparent',
                    fontSize: '12px',
                    fontWeight: 500,
                    color: isDeepResearch ? TOKENS.colors.amber : TOKENS.colors.muted,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease'
                  }}
                >
                  {isDeepResearch && (
                    <motion.span
                      initial={{ scale: 0 }}
                      animate={{ scale: [1, 1.3, 1] }}
                      transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
                      style={{
                        width: '5px',
                        height: '5px',
                        borderRadius: '50%',
                        backgroundColor: TOKENS.colors.amber,
                        display: 'inline-block'
                      }}
                    />
                  )}
                  <IconMicroscope size={13} style={{ color: isDeepResearch ? TOKENS.colors.amber : TOKENS.colors.muted }} />
                  <span>Deep research</span>
                </button>
              </div>

              <motion.button
                type="button"
                onClick={() => handleSend()}
                animate={inputText.trim().length > 0 ? { scale: [1, 1.06, 1] } : { scale: 1 }}
                transition={
                  inputText.trim().length > 0
                    ? { duration: 1.6, repeat: Infinity, ease: 'easeInOut' }
                    : { type: 'spring', stiffness: 400, damping: 17 }
                }
                whileHover={{ scale: 1.1, rotate: -8 }}
                whileTap={{ scale: 0.9 }}
                style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  backgroundColor: TOKENS.colors.ink,
                  border: 'none',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: TOKENS.colors.yellow,
                  cursor: 'pointer',
                  flexShrink: 0
                }}
              >
                <IconPaperPlane2 size={15} style={{ color: TOKENS.colors.yellow }} />
              </motion.button>
            </div>
          </div>

          <div
            style={{
              fontSize: '11px',
              color: TOKENS.colors.muted,
              marginTop: '8px',
              textAlign: 'center',
              pointerEvents: 'auto'
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

function ConversationThread({ turns, isPending }) {
  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: '42px 24px 150px', width: '100%', maxWidth: '900px', margin: '0 auto' }}>
      {turns.map((turn) => (
        <div key={turn.id} style={{ marginBottom: '34px' }}>
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '22px' }}>
            <div style={{ background: TOKENS.colors.bubble, borderRadius: '16px 16px 4px 16px', padding: '14px 18px', color: TOKENS.colors.ink, maxWidth: '78%', fontSize: '15px', lineHeight: 1.5 }}>
              {turn.question}
            </div>
          </div>
          <div style={{ display: 'flex', gap: '14px', alignItems: 'flex-start' }}>
            <div style={{ width: '34px', height: '34px', borderRadius: '10px', background: TOKENS.colors.yellow, display: 'grid', placeItems: 'center', flexShrink: 0 }}><IconAtom size={17} /></div>
            <div style={{ flex: 1, color: TOKENS.colors.body, fontSize: '16px', lineHeight: 1.7, minWidth: 0 }}>
              {turn.isLoading && !turn.answer ? <div style={{ color: TOKENS.colors.muted }}>Analyzing the question…</div> : <ChatMarkdown content={turn.answer || ''} />}
              {!turn.isLoading && turn.confidence ? <ConfidenceBlock confidence={turn.confidence} /> : null}
              {turn.error ? <div role="alert" style={{ color: '#B42318', marginTop: '8px' }}>{turn.error}</div> : null}
            </div>
          </div>
        </div>
      ))}
      {isPending && turns.at(-1)?.answer ? <div style={{ color: TOKENS.colors.muted, fontSize: '13px', paddingLeft: '48px' }}>Updating…</div> : null}
    </div>
  );
}
