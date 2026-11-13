import React, { useState, useEffect, useRef } from 'react';

const MODEL_OPTIONS = [
  {
    id: 'Atlas Large',
    modelKey: 'claude-3-5-sonnet-latest',
    name: 'Atlas Large',
    provider: 'Anthropic',
    tag: 'Sonnet 3.5',
    desc: 'Deep reasoning, coding & complex analysis',
    context: '200k',
    recommended: true,
  },
  {
    id: 'Atlas Balanced',
    modelKey: 'gpt-4o-mini',
    name: 'Atlas Balanced',
    provider: 'OpenAI',
    tag: 'GPT-4o Mini',
    desc: 'Fast multimodal & general intelligence',
    context: '128k',
  },
  {
    id: 'Atlas Fast',
    modelKey: 'gemini-2.5-flash-lite',
    name: 'Atlas Fast',
    provider: 'Google',
    tag: 'Gemini 2.5 Flash',
    desc: 'Ultra-fast, lowest latency, massive context',
    context: '1M',
  },
  {
    id: 'Atlas Reasoning',
    modelKey: 'claude-3-5-sonnet-latest',
    name: 'Atlas Reasoning',
    provider: 'Anthropic',
    tag: 'Scientific',
    desc: 'Structured hypothesis and literature review',
    context: '200k',
  },
];

export default function ModelSelectorDropdown({
  selectedModel = 'Atlas Large',
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

  const currentOption = MODEL_OPTIONS.find((m) => m.id === selectedModel) || MODEL_OPTIONS[0];

  return (
    <div className="relative inline-block" ref={dropdownRef}>
      {/* Trigger Button */}
      <button
        type="button"
        disabled={disabled}
        onClick={() => setIsOpen((prev) => !prev)}
        className="h-[34px] px-2.5 rounded-full border border-[var(--border-subtle)] bg-[var(--surface)] hover:bg-[var(--surface-hover)] text-xs font-medium text-[var(--text-body)] flex items-center gap-1.5 transition-colors disabled:opacity-50"
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-label="Select AI Model"
      >
        <span className="h-2 w-2 rounded-full bg-[var(--accent-yellow)] flex-shrink-0" />
        <span className="font-semibold text-[var(--text-main)] truncate max-w-[90px] sm:max-w-[120px]">
          {currentOption.name}
        </span>
        <svg className="h-3 w-3 text-[var(--text-muted)] flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div
          role="listbox"
          className="absolute left-0 bottom-full mb-2 w-72 rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface)] shadow-xl p-1.5 z-50 text-xs overflow-hidden"
        >
          <div className="px-2.5 py-1.5 text-[11px] font-semibold text-[var(--text-muted)] uppercase tracking-wider border-b border-[var(--border-subtle)]/60 mb-1">
            Available Models
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
                      <span className="text-[10px] px-1.5 py-0.2 rounded bg-[var(--surface-hover)] text-[var(--text-secondary)] font-mono">
                        {opt.provider}
                      </span>
                      {opt.recommended && (
                        <span className="text-[9px] px-1 py-0.2 rounded bg-[var(--accent-yellow)] text-[var(--text-main)] font-bold">
                          PRO
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-[var(--text-muted)] line-clamp-1">{opt.desc}</p>
                  </div>

                  <div className="flex flex-col items-end gap-1 flex-shrink-0">
                    <span className="text-[10px] text-[var(--text-muted)] font-mono">{opt.context}</span>
                    {isSelected && (
                      <svg className="h-3.5 w-3.5 text-[var(--accent-amber)]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
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
