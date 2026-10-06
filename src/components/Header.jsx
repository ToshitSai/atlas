import React from 'react';

export default function Header({ onOpenMobileNav }) {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-white/[0.08] bg-[#0f0f10] px-4 text-[#f5f5f5]">
      <div className="flex items-center gap-3">
      <button
        type="button"
        onClick={onOpenMobileNav}
        aria-label="Open navigation menu"
        className="rounded-md border border-white/[0.08] p-2 text-[#9a9ca4] transition-colors hover:text-white lg:hidden"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>
        <span className="text-sm font-semibold">Atlas</span>
      </div>
      <span className="text-xs text-[#9a9ca4]">Research workspace</span>
    </header>
  );
}
