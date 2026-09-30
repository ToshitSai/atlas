import React from 'react';

/**
 * Functional Sources View displaying validated primary research sources.
 */
export default function SourcesView({ sources = [] }) {
  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4 max-w-4xl mx-auto w-full select-none font-sans min-w-0 pb-32 animate-panel-entrance">
      <div className="border-b border-[#242424] pb-3 flex items-center justify-between">
        <div>
          <h2 className="text-base font-mono font-bold text-[#F4F4F6] uppercase flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#FF6500]" />
            Validated Primary Sources
          </h2>
          <p className="text-xs text-[#8A8F98] mt-0.5">
            Literature, benchmark repositories, and domain papers validated by research pipeline
          </p>
        </div>
        <span className="text-xs font-mono text-[#8A8F98] px-2 py-1 bg-[#141416] border border-[#242424] rounded">
          Total: {sources.length}
        </span>
      </div>

      {sources.length === 0 ? (
        <div className="bg-[#0B0B0B] border border-[#242424] rounded p-8 text-center space-y-2">
          <p className="text-xs text-[#8A8F98] italic font-mono">
            No validated sources yet.
          </p>
          <p className="text-xs text-[#8A8F98]">
            Source links will appear when a deep research session retrieves and validates academic literature.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {sources.map((src, idx) => (
            <div key={src.id || idx} className="bg-[#0B0B0B] border border-[#242424] rounded p-4 space-y-2 card-hover-lift">
              <div className="flex items-start justify-between gap-3">
                <a
                  href={src.url || '#'}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm font-semibold text-[#F4F4F6] hover:text-[#FF6500] leading-snug transition-colors"
                >
                  {src.title || 'Untitled Source'}
                </a>
                <a
                  href={src.url || '#'}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="shrink-0 text-xs font-mono text-[#FF6500] hover:underline flex items-center gap-1"
                >
                  Open Link ↗
                </a>
              </div>

              {src.authors && (
                <div className="text-xs text-[#8A8F98]">
                  Authors: {src.authors} {src.year ? `(${src.year})` : ''}
                </div>
              )}

              {src.publisher && (
                <div className="text-xs font-mono text-[#8A8F98]">
                  Publisher / Platform: {src.publisher}
                </div>
              )}

              {src.relevance && (
                <div className="text-xs text-[#8A8F98] leading-relaxed pt-1 border-t border-[#242424]/60">
                  <span className="text-[#F4F4F6] font-medium">Relevance:</span> {src.relevance}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
