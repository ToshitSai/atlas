import React from 'react';

/**
 * Left Navigation Column (~210px wide on desktop).
 * Palette: #050505 background, #242424 borders, #FF6500 orange accent.
 * Destinations: Research, Experiments, Sources, Hypotheses, Reports, History, Research Settings.
 */
export default function Sidebar({
  activeNav = 'research',
  onSelectNav,
  onNewQuestion,
  onOpenSettings,
  isMobileOpen = false,
  onMobileClose,
  backendConnected = true,
}) {
  const navItems = [
    {
      id: 'research',
      label: 'Research',
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="12" cy="12" r="3" />
          <path d="M12 3a9 9 0 0 1 9 9" />
          <path d="M3 12a9 9 0 0 1 9-9" />
          <path d="M12 21a9 9 0 0 1-9-9" />
        </svg>
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
      <div className="p-3 border-b border-[#242424] space-y-3">
        {/* Brand Mark & Title */}
        <div className="flex items-center justify-between gap-2 px-1 pt-1">
          <div className="flex items-center gap-2 min-w-0">
            {/* Small orange scientific mark */}
            <div className="w-6 h-6 rounded bg-[#FF6500]/10 border border-[#FF6500]/40 flex items-center justify-center shrink-0">
              <svg className="w-3.5 h-3.5 text-[#FF6500]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <circle cx="12" cy="12" r="3" className="fill-[#FF6500]/20" />
                <path d="M12 3a9 9 0 0 1 9 9" />
                <path d="M3 12a9 9 0 0 1 9-9" />
                <path d="M12 21a9 9 0 0 1-9-9" />
              </svg>
            </div>
            <div className="min-w-0">
              <span className="font-semibold text-sm tracking-tight text-[#F4F4F6] block leading-none truncate">
                AI Scientist
              </span>
              <span className="text-[10px] font-mono text-[#8A8F98] tracking-wider block mt-0.5 uppercase">
                {backendConnected ? 'Connected' : 'Offline'}
              </span>
            </div>
          </div>

          {/* Close drawer button for mobile */}
          {onMobileClose && (
            <button
              type="button"
              onClick={onMobileClose}
              aria-label="Close navigation"
              className="lg:hidden p-1.5 rounded text-[#8A8F98] hover:text-[#F4F4F6] hover:bg-[#141416] transition-colors"
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
          className="w-full py-2 px-3 rounded bg-[#FF6500] hover:bg-[#FF302A] text-white text-xs font-semibold flex items-center justify-center gap-1.5 btn-transition cursor-pointer shadow-sm"
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
      <nav className="flex-1 overflow-y-auto px-2 py-3 space-y-1" aria-label="Primary navigation">
        <div className="px-2 text-[10px] font-mono uppercase tracking-wider text-[#8A8F98] mb-1 font-semibold">
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
                  ? 'bg-[#141416] text-[#F4F4F6] font-medium border-l-2 border-[#FF6500]'
                  : 'text-[#8A8F98] hover:text-[#F4F4F6] hover:bg-[#101012]'
              }`}
            >
              <span className={isActive ? 'text-[#FF6500]' : 'text-[#8A8F98]'}>
                {item.icon}
              </span>
              <span className="truncate min-w-0">{item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Research Settings at Bottom */}
      <div className="p-2 border-t border-[#242424] bg-[#030303]">
        <button
          type="button"
          onClick={() => {
            onOpenSettings();
            onMobileClose?.();
          }}
          className="w-full flex items-center justify-between px-2.5 py-2 rounded text-xs text-[#8A8F98] hover:text-[#F4F4F6] hover:bg-[#141416] nav-item-transition"
          aria-label="Research Settings"
        >
          <span className="flex items-center gap-2 font-medium">
            <svg className="w-4 h-4 text-[#8A8F98]" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" aria-hidden="true">
              <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.38a2 2 0 0 0-.73-2.73l-.15-.09a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
              <circle cx="12" cy="12" r="3" />
            </svg>
            Research Settings
          </span>
          <span className="text-[10px] font-mono text-[#8A8F98]">v2.0</span>
        </button>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop Fixed Left Rail (~210px) */}
      <aside className="hidden lg:block w-[210px] shrink-0 h-screen bg-[#050505] border-r border-[#242424] z-20">
        {content}
      </aside>

      {/* Mobile Drawer Slide-in (<1024px) */}
      {isMobileOpen && (
        <div className="lg:hidden fixed inset-0 z-50 flex" role="dialog" aria-modal="true" aria-label="Navigation drawer">
          <div className="fixed inset-0 bg-black/75" onClick={onMobileClose} aria-hidden="true" />
          <aside className="relative w-[210px] max-w-[80vw] h-full bg-[#050505] border-r border-[#242424] shadow-2xl z-10">
            {content}
          </aside>
        </div>
      )}
    </>
  );
}
