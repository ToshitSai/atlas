import React from 'react';
import AtlasLogo from './AtlasLogo';

/**
 * Sidebar Navigation & Mobile Drawer:
 * Fixed 262px left rail on desktop, 82vw slide-in drawer on mobile.
 */
export default function Sidebar({
  activeNav = 'research',
  onSelectNav,
  onNewQuestion,
  onOpenSettings,
  isMobileOpen = false,
  onMobileClose,
  historyItems = [],
  onSelectHistoryItem,
  theme = 'system',
  onThemeChange,
}) {
  const navItems = [
    {
      id: 'research',
      label: 'Research',
      icon: <AtlasLogo className="w-4 h-4" />,
    },
    {
      id: 'experiments',
      label: 'Experiments',
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M9 3v2m6-2v2M9 19v2m6-2v2M3 9h2m-2 6h2m14-6h2m-2 6h2" />
          <rect x="7" y="7" width="10" height="10" rx="2" />
        </svg>
      ),
    },
    {
      id: 'sources',
      label: 'Sources',
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
          <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
        </svg>
      ),
    },
    {
      id: 'hypotheses',
      label: 'Hypotheses',
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 1 1 7.072 0l-.548.547A3.374 3.374 0 0 0 14 18.469V19a2 2 0 1 1-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
        </svg>
      ),
    },
    {
      id: 'reports',
      label: 'Reports',
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="16" y1="13" x2="8" y2="13" />
          <line x1="16" y1="17" x2="8" y2="17" />
          <polyline points="10 9 9 9 8 9" />
        </svg>
      ),
    },
    {
      id: 'history',
      label: 'History',
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="12" cy="12" r="10" />
          <polyline points="12 6 12 12 16 14" />
        </svg>
      ),
    },
  ];

  const content = (
    <div className="flex flex-col h-full justify-between select-none bg-[var(--bg-left-nav)]">
      {/* Top Header & New Chat Action */}
      <div className="p-3 border-b border-[var(--border-subtle)] space-y-3 shrink-0">
        {/* Brand Mark & Title */}
        <div className="flex items-center justify-between gap-2 px-1 pt-1">
          <div className="flex items-center gap-2 min-w-0">
            <AtlasLogo className="w-6 h-6 text-[var(--accent-yellow)] shrink-0" />
            <div className="min-w-0">
              <span className="font-bold text-[15px] tracking-normal text-[var(--text-main)] block leading-none truncate font-sans">
                Atlas
              </span>
            </div>
          </div>

          {/* Close drawer button for mobile */}
          {onMobileClose && (
            <button
              type="button"
              onClick={onMobileClose}
              aria-label="Close navigation"
              className="lg:hidden p-1.5 rounded-lg text-[var(--text-secondary)] hover:text-[var(--text-main)] hover:bg-[var(--surface-hover)] transition-colors cursor-pointer"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>

        {/* New Chat Control */}
        <button
          type="button"
          onClick={() => {
            onNewQuestion();
            onMobileClose?.();
          }}
          className="w-full py-2.5 px-3 rounded-xl bg-[var(--surface)] hover:bg-[var(--surface-hover)] border border-[var(--border-subtle)] text-[var(--text-main)] text-[13.5px] font-semibold flex items-center justify-center gap-1.5 btn-transition cursor-pointer shadow-sm font-sans"
          aria-label="New chat"
        >
          <svg className="w-4 h-4 text-[var(--text-main)]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" aria-hidden="true">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          New chat
        </button>
      </div>

      {/* Navigation & History List */}
      <nav className="sidebar-scroll-area flex-1 overflow-y-auto px-2 py-3 space-y-1 font-sans" aria-label="Primary navigation">
        <div className="px-2 text-xs font-medium text-[var(--text-muted)] mb-1.5 font-sans">
          Workspace
        </div>
        {navItems.map((item) => {
          const isActive = activeNav === item.id;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => {
                onSelectNav(item.id);
                onMobileClose?.();
              }}
              aria-current={isActive ? 'page' : undefined}
              className={`w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-xs text-left nav-item-transition cursor-pointer ${
                isActive
                  ? 'bg-[var(--surface)] text-[var(--text-main)] font-semibold shadow-xs border-l-2 border-[var(--accent-yellow)]'
                  : 'text-[var(--text-body)] hover:text-[var(--text-main)] hover:bg-[var(--surface-hover)] font-normal'
              }`}
            >
              <span className={isActive ? 'text-[var(--accent-amber)]' : 'text-[var(--text-muted)]'}>
                {item.icon}
              </span>
              <span className="truncate min-w-0">{item.label}</span>
            </button>
          );
        })}

        {/* Recent Chat History Items if available */}
        {historyItems && historyItems.length > 0 && (
          <div className="pt-4 space-y-1">
            <div className="px-2 text-xs font-medium text-[var(--text-muted)] mb-1 font-sans">
              Recent Chats
            </div>
            {historyItems.slice(0, 10).map((chat, idx) => (
              <button
                key={chat.id || chat.conversationId || idx}
                type="button"
                onClick={() => {
                  onSelectHistoryItem?.(chat);
                  onMobileClose?.();
                }}
                className="w-full text-left px-2.5 py-1.5 rounded-lg text-[12px] text-[var(--text-body)] hover:text-[var(--text-main)] hover:bg-[var(--surface-hover)] truncate transition-colors cursor-pointer flex items-center justify-between"
              >
                <span className="truncate pr-1">{chat.title || chat.question || 'Untitled chat'}</span>
              </button>
            ))}
          </div>
        )}

        {onOpenSettings && (
          <div className="pt-2">
            <button
              type="button"
              onClick={() => {
                onOpenSettings();
                onMobileClose?.();
              }}
              className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-xs text-left text-[var(--text-body)] hover:text-[var(--text-main)] hover:bg-[var(--surface-hover)] font-normal font-sans cursor-pointer"
            >
              <span className="text-[var(--text-muted)]">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.38a2 2 0 0 0-.73-2.73l-.15-.09a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
              </span>
              <span className="truncate min-w-0">Settings</span>
            </button>
          </div>
        )}
      </nav>

      {/* Theme switch button */}
      {onThemeChange && (
        <div className="border-t border-[var(--border-subtle)] px-3 py-3 shrink-0">
          <button
            type="button"
            onClick={onThemeChange}
            className="w-full flex items-center justify-between gap-2 rounded-lg px-2.5 py-2 text-xs text-[var(--text-secondary)] hover:text-[var(--text-main)] hover:bg-[var(--surface-hover)] transition-colors cursor-pointer"
            aria-label={`Theme: ${theme}. Switch theme`}
            title="Switch theme"
          >
            <span className="flex items-center gap-2">
              <span className="theme-toggle-icon" aria-hidden="true">{theme === 'dark' ? '☾' : theme === 'light' ? '☀' : '◐'}</span>
              <span className="capitalize">{theme} theme</span>
            </span>
          </button>
        </div>
      )}
    </div>
  );

  return (
    <>
      {/* Desktop Fixed Left Rail (~262px) */}
      <aside className="hidden lg:block w-[262px] shrink-0 h-screen bg-[var(--bg-left-nav)] border-r border-[var(--border-subtle)] z-20">
        {content}
      </aside>

      {/* Mobile Drawer Slide-in (<1024px) */}
      {isMobileOpen && (
        <div className="lg:hidden fixed inset-0 z-50 flex" role="dialog" aria-modal="true" aria-label="Navigation drawer">
          <div className="fixed inset-0 bg-black/60 backdrop-blur-xs" onClick={onMobileClose} aria-hidden="true" />
          <aside className="relative w-[280px] max-w-[82vw] h-full bg-[var(--bg-left-nav)] border-r border-[var(--border-subtle)] shadow-2xl z-10">
            {content}
          </aside>
        </div>
      )}
    </>
  );
}

