import React from 'react';

/**
 * Header Component:
 * Compact header with product name and actual session status.
 * Palette: #121212 background, #303030 bottom border.
 */
export default function Header({
  sessionStatus = 'DISCONNECTED',
  routingMode = 'AUTO',
  backendConnected = false,
  connectionState = 'CONNECTING',
  onOpenMobileNav,
  activeNavTitle = 'Research Workspace',
}) {
  const statusConfig = {
    DISCONNECTED: { label: 'Disconnected', color: 'text-[#F87171]', bg: 'bg-[#F87171]/10', border: 'border-[#F87171]/30', dot: 'bg-[#F87171]' },
    CONNECTING: { label: 'Connecting…', color: 'text-[#8A8884]', bg: 'bg-[#1B1B1B]', border: 'border-[#303030]', dot: 'bg-[#8A8884] animate-pulse' },
    IDLE: { label: 'Idle', color: 'text-[#8A8884]', bg: 'bg-[#1B1B1B]', border: 'border-[#303030]', dot: 'bg-[#8A8884]' },
    QUEUED: { label: 'Queued', color: 'text-[#F15A3A]', bg: 'bg-[#F15A3A]/10', border: 'border-[#F15A3A]/30', dot: 'bg-[#F15A3A] animate-pulse' },
    IN_PROGRESS: { label: 'In Progress', color: 'text-[#F15A3A]', bg: 'bg-[#F15A3A]/10', border: 'border-[#F15A3A]/30', dot: 'bg-[#F15A3A] animate-running-pulse' },
    COMPLETE: { label: 'Complete', color: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/30', dot: 'bg-emerald-400' },
    FAILED: { label: 'Failed', color: 'text-[#F87171]', bg: 'bg-[#F87171]/10', border: 'border-[#F87171]/30', dot: 'bg-[#F87171]' },
    CANCELLED: { label: 'Cancelled', color: 'text-[#8A8884]', bg: 'bg-[#1B1B1B]', border: 'border-[#303030]', dot: 'bg-[#8A8884]' },
  };

  const currentStatusKey = connectionState === 'CONNECTING'
    ? 'CONNECTING'
    : !backendConnected ? 'DISCONNECTED' : (sessionStatus || 'IDLE');
  const st = statusConfig[currentStatusKey] || statusConfig.IDLE;

  return (
    <header className="h-12 border-b border-[#303030] bg-[#121212] px-3 sm:px-5 flex items-center justify-between gap-3 shrink-0 select-none z-10">
      <div className="flex items-center gap-2.5 min-w-0">
        {/* Mobile menu hamburger toggle */}
        <button
          type="button"
          onClick={onOpenMobileNav}
          aria-label="Open navigation menu"
          className="lg:hidden p-1.5 rounded text-[#8A8884] hover:text-[#E8E5DF] hover:bg-[#1B1B1B] transition-colors"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>

        {/* Product Title Breadcrumb */}
        <div className="flex items-center gap-2 min-w-0 font-sans">
          <h1 className="text-sm font-semibold text-[#E8E5DF] truncate tracking-normal font-sans">
            Atlas
          </h1>
        </div>
      </div>

    </header>
  );
}
