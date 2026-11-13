import React, { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

/**
 * Image Lightbox Modal for high-resolution inspection of uploaded or cited images.
 */
export default function ImageLightbox({ image, onClose }) {
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose?.();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!image) return null;

  const src = image.previewUrl || image.url || (image.id ? `/api/files/${image.id}/download` : null);

  return (
    <AnimatePresence>
      <div
        role="dialog"
        aria-modal="true"
        aria-label={`Preview of ${image.filename || 'image'}`}
        className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm"
        onClick={onClose}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          transition={{ duration: 0.18, ease: 'easeOut' }}
          className="relative max-w-4xl max-h-[90vh] bg-[var(--surface)] border border-[var(--border-subtle)] rounded-2xl shadow-2xl overflow-hidden flex flex-col"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header bar */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--border-subtle)] bg-[var(--surface-alt)]">
            <div className="flex items-center gap-2 min-w-0">
              <span className="text-base">🖼️</span>
              <span className="font-medium text-sm text-[var(--text-main)] truncate max-w-md">
                {image.filename || 'Image Preview'}
              </span>
              {image.byte_size && (
                <span className="text-xs text-[var(--text-muted)]">
                  ({(image.byte_size / (1024 * 1024)).toFixed(2)} MB)
                </span>
              )}
            </div>
            <button
              type="button"
              onClick={onClose}
              className="w-8 h-8 rounded-lg flex items-center justify-center text-[var(--text-secondary)] hover:text-[var(--text-main)] hover:bg-[var(--surface-hover)] transition-colors"
              aria-label="Close image preview"
              title="Close (Esc)"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>

          {/* Image Display */}
          <div className="relative flex-1 min-h-[300px] max-h-[78vh] flex items-center justify-center bg-[var(--bg-main)] overflow-auto p-4">
            {src ? (
              <img
                src={src}
                alt={image.filename || 'Full image preview'}
                className="max-h-full max-w-full object-contain rounded-lg shadow-sm select-none"
              />
            ) : (
              <div className="text-[var(--text-muted)] text-sm">Image preview unavailable.</div>
            )}
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
