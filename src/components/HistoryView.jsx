import React from 'react';

/**
 * Functional History View displaying actual available records.
 * Explicitly discloses browser-tab storage limitation as required by spec §12.
 */
export default function HistoryView({
  historyItems = [],
  onSelectHistoryItem,
}) {
  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4 max-w-4xl mx-auto w-full select-none font-sans min-w-0 pb-32 animate-panel-entrance">
      <div className="border-b border-[#242424] pb-3 flex items-center justify-between">
        <div>
          <h2 className="text-base font-mono font-bold text-[#F4F4F6] uppercase flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#FF6500]" />
            Session History
          </h2>
          <p className="text-xs text-[#8A8F98] mt-0.5">
            Recorded queries and research sessions in this environment
          </p>
        </div>
        <span className="text-xs font-mono text-[#8A8F98] px-2 py-1 bg-[#141416] border border-[#242424] rounded">
          Total: {historyItems.length}
        </span>
      </div>

      {/* Disclose storage limitation as per spec §12 */}
      <div className="bg-[#141416] border border-[#242424] rounded p-3 text-xs text-[#8A8F98] font-mono flex items-center gap-2">
        <svg className="w-4 h-4 text-[#FF6500] shrink-0" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="16" x2="12" y2="12" />
          <line x1="12" y1="8" x2="12.01" y2="8" />
        </svg>
        <span>
          Note: Session history is maintained within this browser session context.
        </span>
      </div>

      {historyItems.length === 0 ? (
        <div className="bg-[#0B0B0B] border border-[#242424] rounded p-8 text-center space-y-2">
          <p className="text-xs text-[#8A8F98] italic font-mono">
            No research history recorded yet.
          </p>
          <p className="text-xs text-[#8A8F98]">
            Your submitted questions and research sessions will appear here.
          </p>
        </div>
      ) : (
        <div className="space-y-2.5">
          {historyItems.map((item, idx) => (
            <button
              key={item.id || idx}
              type="button"
              onClick={() => onSelectHistoryItem && onSelectHistoryItem(item)}
              className="w-full text-left bg-[#0B0B0B] hover:bg-[#101012] border border-[#242424] hover:border-[#343434] rounded p-3 space-y-1 nav-item-transition cursor-pointer"
            >
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-[#F4F4F6] truncate max-w-[80%]">
                  {item.title || item.question || 'Research Session'}
                </span>
                <span className="text-[10px] font-mono text-[#8A8F98]">
                  {item.timestamp || 'Recent'}
                </span>
              </div>
              {item.summary && (
                <p className="text-xs text-[#8A8F98] line-clamp-2">
                  {item.summary}
                </p>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
