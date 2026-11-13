import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

/**
 * Modern Source Cards and Citation Drawer component.
 * Distinguishes Web Sources, Document Sources, and Image Sources.
 */
export default function SourceCards({
  sources = [],
  onImageClick,
  defaultExpanded = false,
}) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  if (!sources || sources.length === 0) return null;

  return (
    <div className="mt-3.5 pt-3 border-t border-[var(--border-subtle)] w-full">
      {/* Header / Expand Toggle */}
      <button
        type="button"
        onClick={() => setIsExpanded((prev) => !prev)}
        className="flex items-center gap-2 py-1 px-2.5 rounded-lg hover:bg-[var(--surface-hover)] transition-colors text-xs font-medium text-[var(--text-secondary)] hover:text-[var(--text-main)] w-fit"
        aria-expanded={isExpanded}
        aria-label="Toggle sources list"
      >
        <svg className="h-3.5 w-3.5 text-[var(--accent-amber)]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M4 19.5A2.5 2.5 0 016.5 17H20" />
          <path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z" />
        </svg>
        <span>
          {sources.length} Source{sources.length === 1 ? '' : 's'} Referenced
        </span>
        <svg
          className={`h-3 w-3 text-[var(--text-muted)] transform transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>

      {/* Sources Grid */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
            className="overflow-hidden"
          >
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2.5 mt-2.5 pt-1">
              {sources.map((src, idx) => {
                const isImage = Boolean(src.is_image || /\.(png|jpe?g|webp|gif)$/i.test(src.filename || src.title || ''));
                const isDoc = Boolean(src.is_document || src.page || src.section || src.source_file);
                const title = src.title || src.filename || src.source || `Source ${idx + 1}`;
                const domain = src.domain || (src.url ? src.url.replace(/^https?:\/\//, '').split('/')[0] : (isDoc ? 'Document' : isImage ? 'Image' : 'Web'));
                const downloadUrl = src.id ? `/api/files/${src.id}/download` : src.url;

                return (
                  <div
                    key={src.id || src.url || idx}
                    className="flex flex-col justify-between p-3 rounded-xl border border-[var(--border-subtle)] bg-[var(--surface)] hover:border-[var(--border-emphasis)] hover:shadow-xs transition-all text-xs"
                  >
                    <div>
                      {/* Top Badges */}
                      <div className="flex items-center justify-between gap-1.5 mb-1.5">
                        <span className="flex items-center gap-1.5 font-medium text-[11px] text-[var(--text-secondary)] truncate">
                          {isImage ? (
                            <span className="text-xs">🖼️</span>
                          ) : isDoc ? (
                            <span className="text-xs">📄</span>
                          ) : (
                            <span className="h-2 w-2 rounded-full bg-[var(--accent-amber)]" />
                          )}
                          <span className="truncate max-w-[120px]">{domain}</span>
                        </span>

                        <span className="text-[10px] text-[var(--text-muted)] font-mono bg-[var(--surface-alt)] px-1.5 py-0.5 rounded">
                          [{idx + 1}]
                        </span>
                      </div>

                      {/* Title */}
                      <h4 className="font-semibold text-[var(--text-main)] line-clamp-1 mb-1" title={title}>
                        {title}
                      </h4>

                      {/* Snippet / Excerpt */}
                      {(src.snippet || src.excerpt || src.content) && (
                        <p className="text-[11px] text-[var(--text-secondary)] line-clamp-2 leading-relaxed mb-2">
                          {(() => {
                            const val = src.snippet || src.excerpt || src.content;
                            return typeof val === 'string' ? val : (typeof val === 'object' ? (val?.text || JSON.stringify(val)) : String(val));
                          })()}
                        </p>
                      )}
                    </div>

                    {/* Bottom Metadata & Link */}
                    <div className="flex items-center justify-between gap-2 pt-2 border-t border-[var(--border-subtle)]/60 text-[11px]">
                      {src.date ? (
                        <span className="text-[var(--text-muted)]">{src.date}</span>
                      ) : src.page ? (
                        <span className="text-[var(--text-muted)]">Page {src.page}</span>
                      ) : (
                        <span className="text-[var(--text-muted)]">Verified</span>
                      )}

                      {isImage ? (
                        <button
                          type="button"
                          onClick={() => onImageClick?.(src)}
                          className="text-[var(--accent-amber)] hover:underline font-medium cursor-pointer"
                        >
                          View Image ↗
                        </button>
                      ) : downloadUrl ? (
                        <a
                          href={downloadUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-[var(--accent-amber)] hover:underline font-medium inline-flex items-center gap-0.5"
                        >
                          {isDoc ? 'View Document ↗' : 'Visit Link ↗'}
                        </a>
                      ) : null}
                    </div>
                  </div>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
