import React from 'react';

/**
 * Mobile-only menu toggle (Desktop top header bar removed as requested).
 */
export default function Header({ onOpenMobileNav }) {
  return (
    <div className="lg:hidden absolute top-3 left-3 z-30">
      <button
        type="button"
        onClick={onOpenMobileNav}
        aria-label="Open navigation menu"
        className="p-2 rounded-lg bg-[#181818] border border-[#303030] text-[#8A8884] hover:text-[#E8E5DF] transition-colors shadow-md"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>
    </div>
  );
}
