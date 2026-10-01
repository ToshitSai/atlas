import React from 'react';

/**
 * Functional Sources View displaying validated primary research sources with clean typography.
 */
export default function SourcesView({ sources = [] }) {
  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4 max-w-4xl mx-auto w-full select-none font-sans min-w-0 pb-32 animate-panel-entrance">
      <div className="border-b border-[#303030] pb-3 flex items-center justify-between font-sans">
        <div>
          <h2 className="text-base font-semibold text-[#E8E5DF] font-sans flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#F15A3A]" />
            Research Sources
          </h2>
          <p className="text-xs text-[#8A8884] mt-0.5 font-sans">
            Literature, benchmark repositories, and domain papers validated by research pipeline
          </p>
        </div>
        <span className="text-xs font-medium text-[#8A8884] px-2.5 py-1 bg-[#1B1B1B] border border-[#303030] rounded-full font-sans">
          Total: {sources.length}
        </span>
      </div>

      {sources.length === 0 ? (
        <div className="bg-[#181818] border border-[#303030] rounded-xl p-8 text-center space-y-2 font-sans">
          <p className="text-xs text-[#8A8884] font-sans">
            No validated sources yet.
          </p>
          <p className="text-xs text-[#8A8884] font-sans">
            Source links will appear when a deep research session retrieves and validates academic literature.
          </p>
        </div>
      ) : (
        <div className="space-y-3 font-sans">
          {sources.map((src, idx) => (
            <div key={src.id || idx} className="bg-[#181818] border border-[#303030] rounded-xl p-4 space-y-2 card-hover-lift font-sans">
              <div className="flex items-start justify-between gap-3 font-sans">
                <a
                  href={src.url || '#'}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm font-semibold text-[#E8E5DF] hover:text-[#F15A3A] leading-snug transition-colors font-sans"
                >
                  {src.title || 'Untitled Source'}
                </a>
                <a
                  href={src.url || '#'}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="shrink-0 text-xs font-medium text-[#F15A3A] hover:underline flex items-center gap-1 font-sans"
                >
                  Open Link ↗
                </a>
              </div>

              {src.authors && (
                <div className="text-xs text-[#8A8884] font-sans">
                  Authors: {src.authors} {src.year ? `(${src.year})` : ''}
                </div>
              )}

              {src.publisher && (
                <div className="text-xs text-[#8A8884] font-sans">
                  Publisher / Platform: {src.publisher}
                </div>
              )}

              {src.relevance && (
                <div className="text-xs text-[#8A8884] leading-relaxed pt-2 border-t border-[#303030]/60 font-sans">
                  <span className="text-[#E8E5DF] font-medium font-sans">Relevance:</span> {src.relevance}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
