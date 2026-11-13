import React from 'react';

/**
 * Returns a format-specific glyph/icon based on filename and type.
 */
function getFileBadge(filename = '', isImage = false, docType = '') {
  if (isImage) return { icon: '🖼️', label: 'IMG' };
  const ext = filename.split('.').pop()?.toLowerCase();
  switch (ext) {
    case 'pdf':
      return { icon: '📄', label: 'PDF', bg: 'rgba(239, 68, 68, 0.1)', color: '#EF4444' };
    case 'docx':
    case 'doc':
      return { icon: '📝', label: 'DOCX', bg: 'rgba(59, 130, 246, 0.1)', color: '#3B82F6' };
    case 'xlsx':
    case 'xls':
    case 'csv':
    case 'tsv':
      return { icon: '📊', label: 'SHEET', bg: 'rgba(16, 185, 129, 0.1)', color: '#10B981' };
    case 'pptx':
    case 'ppt':
      return { icon: '📑', label: 'SLIDES', bg: 'rgba(249, 115, 22, 0.1)', color: '#F97316' };
    case 'json':
    case 'xml':
    case 'yaml':
    case 'py':
    case 'js':
    case 'ts':
    case 'html':
      return { icon: '💻', label: 'CODE', bg: 'rgba(139, 92, 246, 0.1)', color: '#8B5CF6' };
    default:
      return { icon: '📄', label: 'TXT', bg: 'rgba(107, 114, 128, 0.1)', color: '#6B7280' };
  }
}

/**
 * Modern attachment preview area supporting image thumbnails and document cards.
 */
export default function AttachmentArea({
  attachments = [],
  onRemove,
  onRetry,
  onImageClick,
  compact = false,
}) {
  if (!attachments || attachments.length === 0) return null;

  return (
    <div className={`flex flex-wrap gap-2.5 w-full ${compact ? 'py-1' : 'py-2'}`} role="list" aria-label="Attachments">
      {attachments.map((att) => {
        const isImage = Boolean(att.is_image || /\.(png|jpe?g|webp|gif|bmp|tiff)$/i.test(att.filename || ''));
        const badge = getFileBadge(att.filename, isImage, att.doc_type);
        const imgSrc = att.previewUrl || att.url || (att.id ? `/api/files/${att.id}/download` : null);

        return (
          <div
            key={att.tempId || att.id || att.filename}
            role="listitem"
            className="group relative flex items-center gap-2 p-1.5 pr-2.5 rounded-xl border border-[var(--border-subtle)] bg-[var(--surface)] shadow-xs transition-all hover:border-[var(--border-emphasis)] hover:shadow-sm"
          >
            {/* Visual Thumbnail for Images */}
            {isImage && imgSrc ? (
              <button
                type="button"
                onClick={() => onImageClick?.(att)}
                title="Click to expand preview"
                className="relative h-11 w-11 rounded-lg overflow-hidden border border-[var(--border-subtle)] bg-[var(--surface-alt)] flex-shrink-0 cursor-zoom-in"
              >
                <img
                  src={imgSrc}
                  alt={att.filename || 'thumbnail'}
                  className="h-full w-full object-cover transition-transform duration-200 group-hover:scale-105"
                />
              </button>
            ) : (
              <div
                className="h-11 w-11 rounded-lg flex items-center justify-center font-bold text-xs flex-shrink-0"
                style={{ backgroundColor: badge.bg, color: badge.color }}
              >
                <span className="text-base select-none">{badge.icon}</span>
              </div>
            )}

            {/* File Metadata & Status */}
            <div className="flex flex-col min-w-0 pr-1">
              <span
                className="text-xs font-medium text-[var(--text-main)] truncate max-w-[130px]"
                title={att.filename}
              >
                {att.filename}
              </span>

              {/* Status indicators */}
              <div className="flex items-center gap-1.5 text-[11px]">
                {att.status === 'UPLOADING' && (
                  <span className="text-[var(--accent-orange)] flex items-center gap-1">
                    <span className="inline-block h-2 w-2 rounded-full border-2 border-current border-t-transparent animate-spin" />
                    Uploading…
                  </span>
                )}
                {att.status === 'EXTRACTING' && (
                  <span className="text-sky-600 dark:text-sky-400 flex items-center gap-1">
                    <span className="inline-block h-2 w-2 rounded-full border-2 border-current border-t-transparent animate-spin" />
                    Extracting…
                  </span>
                )}
                {att.status === 'INDEXING' && (
                  <span className="text-indigo-600 dark:text-indigo-400 flex items-center gap-1">
                    <span className="inline-block h-2 w-2 rounded-full border-2 border-current border-t-transparent animate-spin" />
                    Indexing…
                  </span>
                )}
                {att.status === 'STORING' && (
                  <span className="text-purple-600 dark:text-purple-400 flex items-center gap-1">
                    <span className="inline-block h-2 w-2 rounded-full border-2 border-current border-t-transparent animate-spin" />
                    Storing…
                  </span>
                )}
                {att.status === 'READY' && (
                  <span className="text-emerald-600 dark:text-emerald-400 font-semibold flex items-center gap-1">
                    <svg className="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                    Ready
                  </span>
                )}
                {att.status === 'FAILED' && (
                  <span className="text-rose-600 dark:text-rose-400 font-medium flex items-center gap-1" title={att.error}>
                    <span className="truncate max-w-[110px]">
                      Failed{att.stage ? ` (${att.stage})` : ''}
                    </span>
                    {att.category !== 'unsupported_video' &&
                      att.category !== 'legacy_format' &&
                      att.category !== 'oversized_file' &&
                      onRetry && (
                        <button
                          type="button"
                          onClick={() => onRetry(att.tempId || att.id)}
                          className="underline hover:text-[var(--text-main)] ml-0.5 cursor-pointer font-semibold"
                        >
                          Retry
                        </button>
                      )}
                  </span>
                )}
                {!att.status && att.byte_size && (
                  <span className="text-[var(--text-muted)]">
                    {(att.byte_size / (1024 * 1024)).toFixed(1)} MB
                  </span>
                )}
              </div>
            </div>

            {/* Remove Button */}
            {onRemove && (
              <button
                type="button"
                onClick={() => onRemove(att.tempId || att.id)}
                className="h-6 w-6 rounded-md flex items-center justify-center text-[var(--text-muted)] hover:text-[var(--text-main)] hover:bg-[var(--surface-hover)] transition-colors"
                title="Remove attachment"
                aria-label={`Remove ${att.filename}`}
              >
                <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            )}
          </div>
        );
      })}
    </div>
  );
}
