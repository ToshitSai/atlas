import React, { useState, useEffect, useRef } from 'react';

const MODEL_OPTIONS = [
  {
    id: 'Atlas Research (Gen-4 Local)',
    modelKey: 'qwen3-1.7b-gen4-qlora',
    name: 'Atlas Research (Gen-4)',
    provider: 'Local RTX 5050 GPU',
    tag: 'Qwen3-1.7B QLoRA',
    desc: 'Specialized scientific planning, experiment critique & evidence ledger',
    context: '32k',
    isLocal: true,
    badge: 'LOCAL',
    recommended: true,
  },
  {
    id: 'Atlas Large',
    modelKey: 'claude-sonnet-4-6',
    name: 'Atlas Large (Frontier)',
    provider: 'Anthropic Cloud',
    tag: 'Sonnet 3.5',
    desc: 'Deep reasoning, coding & massive context synthesis',
    context: '200k',
    isLocal: false,
    badge: 'CLOUD',
  },
  {
    id: 'Atlas Balanced',
    modelKey: 'gpt-4o-mini',
    name: 'Atlas Balanced (Frontier)',
    provider: 'OpenAI Cloud',
    tag: 'GPT-4o Mini',
    desc: 'Fast general intelligence & multimodal queries',
    context: '128k',
    isLocal: false,
    badge: 'CLOUD',
  },
  {
    id: 'Atlas Fast',
    modelKey: 'gemini-2.5-flash-lite',
    name: 'Atlas Fast (Frontier)',
    provider: 'Google Cloud',
    tag: 'Gemini 2.5 Flash',
    desc: 'Ultra-fast, lowest latency, 1M context window',
    context: '1M',
    isLocal: false,
    badge: 'CLOUD',
  },
];

export default function ModelSelectorDropdown({
  selectedModel = 'Atlas Research (Gen-4 Local)',
  onSelectModel,
  disabled = false,
}) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  const currentOption = (Array.isArray(MODEL_OPTIONS) && MODEL_OPTIONS.find((m) => m.id === selectedModel || m.name === selectedModel)) || MODEL_OPTIONS[0] || {};

  return (
    <div className="relative inline-block" ref={dropdownRef}>
      {/* Trigger Button: ● Atlas Research (Gen-4) ▾ */}
      <button
        type="button"
        disabled={disabled}
        onClick={() => setIsOpen((prev) => !prev)}
        className="atlas-model-trigger h-[32px] px-2.5 rounded-full border border-[var(--border-subtle)] bg-[var(--surface)] hover:bg-[var(--surface-hover)] text-xs font-medium text-[var(--text-body)] flex items-center gap-1.5 transition-all disabled:opacity-50 cursor-pointer shadow-sm select-none"
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-label="Select AI Model"
        title={`Current model: ${currentOption.name} (${currentOption.provider})`}
      >
        <span className={`h-2 w-2 rounded-full flex-shrink-0 ${currentOption.isLocal ? 'bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.6)]' : 'bg-amber-400'}`} />
        <span className="font-semibold text-[var(--text-main)] truncate max-w-[130px] sm:max-w-[160px]">
          {currentOption.name}
        </span>
        <svg
          className="h-3 w-3 text-[var(--text-muted)] flex-shrink-0 transition-transform duration-200"
          style={{ transform: isOpen ? 'rotate(180deg)' : 'none' }}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div
          role="listbox"
          className="absolute left-0 bottom-full mb-2 w-80 rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface)] shadow-2xl p-1.5 z-50 text-xs overflow-hidden"
        >
          <div className="px-2.5 py-1.5 text-[11px] font-semibold text-[var(--text-muted)] uppercase tracking-wider border-b border-[var(--border-subtle)]/60 mb-1 flex justify-between items-center">
            <span>Model Provenance & Architecture</span>
            <span className="text-[10px] text-emerald-400 font-mono">RTX 5050 Ready</span>
          </div>

          <div className="space-y-1">
            {MODEL_OPTIONS.map((opt) => {
              const isSelected = opt.id === selectedModel;
              return (
                <button
                  key={opt.id}
                  type="button"
                  role="option"
                  aria-selected={isSelected}
                  onClick={() => {
                    onSelectModel(opt.id);
                    setIsOpen(false);
                  }}
                  className={`w-full text-left p-2.5 rounded-xl flex items-start justify-between gap-2 transition-colors cursor-pointer ${
                    isSelected
                      ? 'bg-[var(--surface-alt)] text-[var(--text-main)] font-medium border border-[var(--border-emphasis)]/50'
                      : 'hover:bg-[var(--surface-hover)] text-[var(--text-body)]'
                  }`}
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5 mb-0.5">
                      <span className="font-semibold text-xs text-[var(--text-main)]">{opt.name}</span>
                      <span className={`text-[9px] px-1.5 py-0.2 rounded font-bold font-mono ${
                        opt.isLocal ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-indigo-500/20 text-indigo-300'
                      }`}>
                        {opt.badge}
                      </span>
                    </div>
                    <p className="text-[11px] text-[var(--text-muted)] line-clamp-1">{opt.desc}</p>
                    <div className="mt-1 text-[10px] text-[var(--text-secondary)] font-mono">
                      {opt.provider} · {opt.tag}
                    </div>
                  </div>

                  <div className="flex flex-col items-end gap-1 flex-shrink-0 pt-0.5">
                    <span className="text-[10px] text-[var(--text-muted)] font-mono">{opt.context}</span>
                    {isSelected && (
                      <svg className="h-3.5 w-3.5 text-amber-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
