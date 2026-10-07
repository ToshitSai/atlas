import React from 'react';
import AtlasLogo from './AtlasLogo';

/**
 * Sidebar Navigation:
 * Fixed 262px left column. Dark/muted canvas with active accent orange #F15A3A.
 */
export default function Sidebar({
  activeNav = 'research',
  onSelectNav,
  onNewQuestion,
  onOpenSettings,
  isMobileOpen = false,
  onMobileClose,
  backendConnected = true,
  connectionState = 'CONNECTED',
  theme = 'system',
  onThemeChange,
}) {
  const navItems = [
    {
      id: 'research',
      label: 'Research',
      icon: (
        <AtlasLogo className="w-4 h-4" />
      ),
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
    <div className="flex flex-col h-full justify-between select-none">
      {/* Top Header & New Question Action */}
      <div className="p-3 border-b border-[#E9E7E1] space-y-3">
        {/* Brand Mark & Title */}
        <div className="flex items-center justify-between gap-2 px-1 pt-1">
          <div className="flex items-center gap-2 min-w-0">
            <AtlasLogo className="w-6 h-6 shrink-0" />
            <div className="min-w-0">
              <span className="font-bold text-[15px] tracking-normal text-[#0D0C0A] block leading-none truncate font-sans">
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
              className="lg:hidden p-1.5 rounded text-[#8A8884] hover:text-[#E8E5DF] hover:bg-[#1B1B1B] transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>

        {/* New Question Control */}
        <button
          type="button"
          onClick={() => {
            onNewQuestion();
            onMobileClose?.();
          }}
          className="w-full py-2.5 px-3 rounded-xl bg-white hover:bg-[#fffefb] border border-[#E9E7E1] text-[#44403B] text-[13.5px] font-semibold flex items-center justify-center gap-1.5 btn-transition cursor-pointer shadow-sm font-sans"
          aria-label="New question"
        >
          <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          New question
        </button>
      </div>

      {/* Navigation List */}
      <nav className="flex-1 overflow-y-auto px-2 py-3 space-y-1 font-sans" aria-label="Primary navigation">
        <div className="px-2 text-xs font-medium text-[#8A8884] mb-1.5 font-sans">
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
              className={`w-full flex items-center gap-2.5 px-2.5 py-2 rounded text-xs text-left nav-item-transition ${
                isActive
                  ? 'bg-white text-[#0D0C0A] font-medium border-l-2 border-[#FFD800]'
                  : 'text-[#44403B] hover:text-[#0D0C0A] hover:bg-black/[0.035] font-normal'
              }`}
            >
              <span className={isActive ? 'text-[#F15A3A]' : 'text-[#8A8884]'}>
                {item.icon}
              </span>
              <span className="truncate min-w-0">{item.label}</span>
            </button>
          );
        })}

        {onOpenSettings && (
          <button
            type="button"
            onClick={() => {
              onOpenSettings();
              onMobileClose?.();
            }}
            className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded text-xs text-left text-[#44403B] hover:text-[#0D0C0A] hover:bg-black/[0.035] font-normal font-sans"
          >
            <span className="text-[#8A8884]">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.38a2 2 0 0 0-.73-2.73l-.15-.09a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
                <circle cx="12" cy="12" r="3" />
              </svg>
            </span>
            <span className="truncate min-w-0">Settings</span>
          </button>
        )}
      </nav>

      {onThemeChange && (
        <div className="border-t border-[var(--border-subtle)] px-3 py-3">
          <button
            type="button"
            onClick={onThemeChange}
            className="w-full flex items-center justify-between gap-2 rounded px-2.5 py-2 text-xs text-[var(--text-secondary)] hover:text-[var(--text-main)] hover:bg-[var(--surface-hover)] transition-colors"
            aria-label={`Theme: ${theme}. Switch theme`}
            title="Switch theme"
          >
            <span className="flex items-center gap-2">
              <span className="theme-toggle-icon" aria-hidden="true">{theme === 'dark' ? '☾' : theme === 'light' ? '☀' : '◐'}</span>
              <span>{theme[0].toUpperCase() + theme.slice(1)} theme</span>
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
          <div className="fixed inset-0 bg-black/75" onClick={onMobileClose} aria-hidden="true" />
          <aside className="relative w-[262px] max-w-[80vw] h-full bg-[var(--bg-left-nav)] border-r border-[var(--border-subtle)] shadow-2xl z-10">
            {content}
          </aside>
        </div>
      )}
    </>
  );
}
