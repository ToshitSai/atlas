import React from 'react';

/**
 * Header Component:
 * Compact header with product name and actual session status.
 * Palette: #080808 background, #242424 bottom border.
 */
export default function Header({
  sessionStatus = 'DISCONNECTED',
  routingMode = 'AUTO',
  backendConnected = false,
  onOpenMobileNav,
  activeNavTitle = 'Research Workspace',
}) {
  const statusConfig = {
    DISCONNECTED: { label: 'Disconnected', color: 'text-[#F87171]', bg: 'bg-[#F87171]/10', border: 'border-[#F87171]/30', dot: 'bg-[#F87171]' },
    IDLE: { label: 'Idle', color: 'text-[#8A8F98]', bg: 'bg-[#101012]', border: 'border-[#242424]', dot: 'bg-[#8A8F98]' },
    QUEUED: { label: 'Queued', color: 'text-[#FF6500]', bg: 'bg-[#FF6500]/10', border: 'border-[#FF6500]/30', dot: 'bg-[#FF6500] animate-pulse' },
    IN_PROGRESS: { label: 'In Progress', color: 'text-[#FF6500]', bg: 'bg-[#FF6500]/10', border: 'border-[#FF6500]/30', dot: 'bg-[#FF6500] animate-running-pulse' },
    COMPLETE: { label: 'Complete', color: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/30', dot: 'bg-emerald-400' },
    FAILED: { label: 'Failed', color: 'text-[#F87171]', bg: 'bg-[#F87171]/10', border: 'border-[#F87171]/30', dot: 'bg-[#F87171]' },
    CANCELLED: { label: 'Cancelled', color: 'text-[#8A8F98]', bg: 'bg-[#101012]', border: 'border-[#242424]', dot: 'bg-[#8A8F98]' },
  };

  const currentStatusKey = !backendConnected ? 'DISCONNECTED' : (sessionStatus || 'IDLE');
  const st = statusConfig[currentStatusKey] || statusConfig.IDLE;

  return (
    <header className="h-12 border-b border-[#242424] bg-[#080808] px-3 sm:px-5 flex items-center justify-between gap-3 shrink-0 select-none z-10">
      <div className="flex items-center gap-2.5 min-w-0">
        {/* Mobile menu hamburger toggle */}
        <button
          type="button"
          onClick={onOpenMobileNav}
          aria-label="Open navigation menu"
          className="lg:hidden p-1.5 rounded text-[#8A8F98] hover:text-[#F4F4F6] hover:bg-[#141416] transition-colors"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>

        {/* Product Title Breadcrumb */}
        <div className="flex items-center gap-2 min-w-0 font-sans">
          <h1 className="text-sm font-semibold text-[#F4F4F6] truncate tracking-normal font-sans">
            AI Scientist
          </h1>
          <span className="hidden sm:inline text-xs text-[#8A8F98]">/</span>
          <span className="hidden sm:inline text-sm font-normal text-[#8A8F98] truncate font-sans">
            {activeNavTitle}
          </span>
        </div>
      </div>

    </header>
  );
}
