import React, { useState, useEffect, useRef } from 'react';

const MODEL_OPTIONS = [
  {
    id: 'Atlas Research (Gen-4 Local)',
    modelKey: 'qwen3-1.7b-gen4-qlora',
    name: 'Atlas Research (Gen-4)',
    provider: 'Local model',
    desc: 'Specialized scientific planning and experiment analysis.',
    contextLabel: 'Compact context',
    isLocal: true,
    badge: 'LOCAL',
  },
  {
    id: 'Atlas Large',
    modelKey: 'claude-sonnet-4-6',
    name: 'Atlas Large (Frontier)',
    provider: 'Anthropic Cloud',
    desc: 'Advanced reasoning, coding and complex tasks.',
    contextLabel: 'Extended context',
    isLocal: false,
    badge: 'CLOUD',
  },
  {
    id: 'Atlas Balanced',
    modelKey: 'gpt-4o-mini',
    name: 'Atlas Balanced (Frontier)',
    provider: 'OpenAI Cloud',
    desc: 'General-purpose intelligence and multimodal tasks.',
    contextLabel: 'Long context',
    isLocal: false,
    badge: 'CLOUD',
  },
  {
    id: 'Atlas Fast',
    modelKey: 'gemini-2.5-flash-lite',
    name: 'Atlas Fast (Frontier)',
    provider: 'Google Cloud',
    desc: 'Fast responses and everyday assistance.',
    contextLabel: 'Very long context',
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
        title={`Current model: ${currentOption.name}`}
      >
        <span className={`h-2 w-2 rounded-full flex-shrink-0 ${currentOption.isLocal ? 'bg-emerald-400' : 'bg-neutral-400'}`} />
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
          aria-label="Available AI models"
          className="absolute left-0 bottom-full mb-2 w-[340px] max-w-[calc(100vw-32px)] rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface)] shadow-2xl p-2 z-50 text-xs overflow-hidden"
        >
          {/* Subtle Clean Header - No Hardware Specs */}
          <div className="px-2.5 py-1.5 text-[11px] font-medium text-[var(--text-muted)] border-b border-[var(--border-subtle)]/50 mb-1 flex items-center justify-between">
            <span>Select Model</span>
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
                  className={`w-full text-left p-2.5 rounded-xl transition-all cursor-pointer group border ${
                    isSelected
                      ? 'border-[var(--border-subtle)]/80 bg-[var(--surface-hover)]/40 text-[var(--text-main)]'
                      : 'border-transparent hover:bg-[var(--surface-hover)] text-[var(--text-body)]'
                  }`}
                >
                  {/* Top Row: Model Name, checkmark, Badge & Context */}
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <div className="flex items-center gap-1.5 min-w-0">
                      <span className={`text-[12.5px] tracking-tight ${isSelected ? 'font-semibold text-[var(--text-main)]' : 'font-medium text-[var(--text-main)]'}`}>
                        {opt.name}
                      </span>
                      {isSelected && (
                        <svg className="h-3.5 w-3.5 text-[var(--text-main)] shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                          <polyline points="20 6 9 17 4 12" />
                        </svg>
                      )}
                    </div>

                    <div className="flex items-center gap-1.5 flex-shrink-0 text-[10.5px]">
                      <span className={`text-[9.5px] uppercase tracking-wider px-1.5 py-0.5 rounded font-medium ${
                        opt.isLocal
                          ? 'bg-emerald-500/10 text-emerald-400'
                          : 'bg-[var(--surface-hover)] text-[var(--text-muted)]'
                      }`}>
                        {opt.badge}
                      </span>
                      <span className="text-[10.5px] text-[var(--text-muted)]">
                        {opt.contextLabel}
                      </span>
                    </div>
                  </div>

                  {/* Natural Model Description */}
                  <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed mb-1">
                    {opt.desc}
                  </p>

                  {/* Provider Info */}
                  <div className="text-[10px] text-[var(--text-muted)] font-normal">
                    {opt.provider}
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
