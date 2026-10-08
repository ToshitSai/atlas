import React from 'react';
import AtlasLogo from './AtlasLogo';

export default function Header({
  onOpenMobileNav,
  activeNavTitle,
  onNewQuestion,
  sessionStatus = 'IDLE',
  backendConnected = true
}) {
  return (
    <header className="flex h-[52px] min-h-[52px] shrink-0 items-center justify-between border-b border-[var(--border-subtle)] bg-[var(--bg-main)] px-3.5 text-[var(--text-main)] select-none z-30">
      {/* Left: Mobile Hamburger Toggle + Branding / Title */}
      <div className="flex items-center gap-2.5 min-w-0">
        {/* Mobile Hamburger Menu Icon */}
        <button
          type="button"
          onClick={onOpenMobileNav}
          aria-label="Open navigation menu"
          className="flex lg:hidden items-center justify-center rounded-lg border border-[var(--border-subtle)] p-2 text-[var(--text-main)] bg-[var(--surface)] hover:bg-[var(--surface-hover)] transition-colors shrink-0 cursor-pointer"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>

        {/* Mobile Logo Brand */}
        <div className="flex lg:hidden items-center gap-1.5 font-bold text-sm text-[var(--text-main)]">
          <AtlasLogo className="w-4 h-4 text-[var(--accent-yellow)] shrink-0" />
          <span className="truncate">Atlas</span>
        </div>

        {/* Desktop Active Nav Title */}
        <span className="hidden lg:block text-sm font-semibold text-[var(--text-main)] truncate">
          {activeNavTitle || 'Atlas'}
        </span>
      </div>

      {/* Right: Mobile New Chat Action & Desktop Status Label */}
      <div className="flex items-center gap-2 shrink-0">
        {/* Mobile New Chat Action Button */}
        {onNewQuestion && (
          <button
            type="button"
            onClick={onNewQuestion}
            aria-label="New chat"
            title="New chat"
            className="flex lg:hidden items-center justify-center rounded-lg border border-[var(--border-subtle)] p-2 text-[var(--text-main)] bg-[var(--surface)] hover:bg-[var(--surface-hover)] transition-colors cursor-pointer"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2.2" viewBox="0 0 24 24" aria-hidden="true">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
          </button>
        )}

        {/* Desktop Status Label */}
        <span className="hidden lg:inline text-xs text-[var(--text-secondary)] font-mono">
          {sessionStatus === 'IN_PROGRESS' ? 'Researching…' : 'Research workspace'}
        </span>
      </div>
    </header>
  );
}


