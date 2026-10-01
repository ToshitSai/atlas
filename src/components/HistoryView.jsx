import React from 'react';

/**
 * Functional History View displaying actual available records with clean typography.
 */
export default function HistoryView({
  historyItems = [],
  onSelectHistoryItem,
}) {
  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4 max-w-4xl mx-auto w-full select-none font-sans min-w-0 pb-32 animate-panel-entrance">
      <div className="border-b border-[#303030] pb-3 flex items-center justify-between font-sans">
        <div>
          <h2 className="text-base font-semibold text-[#E8E5DF] font-sans flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#F15A3A]" />
            Session History
          </h2>
          <p className="text-xs text-[#8A8884] mt-0.5 font-sans">
            Recorded queries and research sessions in this environment
          </p>
        </div>
        <span className="text-xs font-medium text-[#8A8884] px-2.5 py-1 bg-[#1B1B1B] border border-[#303030] rounded-full font-sans">
          Total: {historyItems.length}
        </span>
      </div>

      {/* Disclose storage limitation */}
      <div className="bg-[#1B1B1B] border border-[#303030] rounded-xl p-3 text-xs text-[#8A8884] font-sans flex items-center gap-2">
        <svg className="w-4 h-4 text-[#F15A3A] shrink-0" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="16" x2="12" y2="12" />
          <line x1="12" y1="8" x2="12.01" y2="8" />
        </svg>
        <span className="font-sans">
          Note: Session history is maintained within this browser session context.
        </span>
      </div>

      {historyItems.length === 0 ? (
        <div className="bg-[#181818] border border-[#303030] rounded-xl p-8 text-center space-y-2 font-sans">
          <p className="text-xs text-[#8A8884] font-sans">
            No research history recorded yet.
          </p>
          <p className="text-xs text-[#8A8884] font-sans">
            Your submitted questions and research sessions will appear here.
          </p>
        </div>
      ) : (
        <div className="space-y-2.5 font-sans">
          {historyItems.map((item, idx) => (
            <button
              key={item.id || idx}
              type="button"
              onClick={() => onSelectHistoryItem && onSelectHistoryItem(item)}
              className="w-full text-left bg-[#181818] hover:bg-[#1B1B1B] border border-[#303030] hover:border-[#353535] rounded-xl p-3.5 space-y-1 nav-item-transition cursor-pointer font-sans"
            >
              <div className="flex items-center justify-between text-xs font-sans">
                <span className="font-semibold text-[#E8E5DF] truncate max-w-[80%] font-sans">
                  {item.title || item.question || 'Research Session'}
                </span>
                <span className="text-xs font-normal text-[#8A8884] font-sans">
                  {item.timestamp || 'Recent'}
                </span>
              </div>
              {item.summary && (
                <p className="text-xs text-[#8A8884] line-clamp-2 font-sans">
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
