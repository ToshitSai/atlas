import React, { useState } from 'react';

/**
 * Assistant Response Actions Toolbar (Section 11).
 * Features: Copy, Regenerate, Feedback (thumbs up/down), Toggle Sources, Toggle Activity, Export.
 */
export default function ResponseActions({
  text = '',
  onRegenerate,
  hasSources = false,
  sourcesCount = 0,
  hasActivities = false,
  activitiesCount = 0,
  onToggleSources,
  onToggleActivities,
  isDeepResearch = false,
}) {
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState(null); // 'helpful' | 'unhelpful' | null

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const textarea = document.createElement('textarea');
      textarea.value = text;
      textarea.style.position = 'fixed';
      textarea.style.opacity = '0';
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      textarea.remove();
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    if (!text) return;
    const blob = new Blob([text], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `Atlas_Response_${Date.now()}.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex items-center gap-1 mt-3 pt-2 text-xs text-[var(--text-secondary)] select-none">
      {/* Copy Button */}
      <button
        type="button"
        onClick={handleCopy}
        className="h-7 w-7 rounded-md hover:bg-[var(--surface-hover)] hover:text-[var(--text-main)] transition-colors flex items-center justify-center cursor-pointer"
        title={copied ? "Copied" : "Copy response"}
        aria-label={copied ? "Copied to clipboard" : "Copy response"}
      >
        {copied ? (
          <svg className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="20 6 9 17 4 12" />
          </svg>
        ) : (
          <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
            <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012-2v1" />
          </svg>
        )}
      </button>

      {/* Regenerate Button */}
      {onRegenerate && (
        <button
          type="button"
          onClick={onRegenerate}
          className="h-7 w-7 rounded-md hover:bg-[var(--surface-hover)] hover:text-[var(--text-main)] transition-colors flex items-center justify-center cursor-pointer"
          title="Regenerate response"
          aria-label="Regenerate response"
        >
          <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="23 4 23 10 17 10" />
            <path d="M20.49 15a9 9 0 11-2.12-9.36L23 10" />
          </svg>
        </button>
      )}

      {/* Helpful / Thumbs Up */}
      <button
        type="button"
        onClick={() => setFeedback(feedback === 'helpful' ? null : 'helpful')}
        className={`h-7 w-7 rounded-md flex items-center justify-center transition-colors cursor-pointer ${
          feedback === 'helpful'
            ? 'bg-emerald-50 text-emerald-600 dark:bg-emerald-950/40 dark:text-emerald-400 font-bold'
            : 'hover:bg-[var(--surface-hover)] hover:text-[var(--text-main)]'
        }`}
        title="Good response"
        aria-label="Good response"
        aria-pressed={feedback === 'helpful'}
      >
        <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d="M14 9V5a3 3 0 00-3-3l-4 9v11h11.28a2 2 0 002-1.7l1.38-9a2 2 0 00-2-2.3zM7 22H4a2 2 0 01-2-2v-7a2 2 0 012-2h3" />
        </svg>
      </button>

      {/* Unhelpful / Thumbs Down */}
      <button
        type="button"
        onClick={() => setFeedback(feedback === 'unhelpful' ? null : 'unhelpful')}
        className={`h-7 w-7 rounded-md flex items-center justify-center transition-colors cursor-pointer ${
          feedback === 'unhelpful'
            ? 'bg-rose-50 text-rose-600 dark:bg-rose-950/40 dark:text-rose-400 font-bold'
            : 'hover:bg-[var(--surface-hover)] hover:text-[var(--text-main)]'
        }`}
        title="Poor response"
        aria-label="Poor response"
        aria-pressed={feedback === 'unhelpful'}
      >
        <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d="M10 15v4a3 3 0 003 3l4-9V2H5.72a2 2 0 00-2 1.7l-1.38 9a2 2 0 002 2.3zm7-13h3a2 2 0 012 2v7a2 2 0 01-2 2h-3" />
        </svg>
      </button>

      {/* Export Report (if deep research or long response) */}
      {(isDeepResearch || text.length > 500) && (
        <button
          type="button"
          onClick={handleDownload}
          className="h-7 w-7 rounded-md hover:bg-[var(--surface-hover)] hover:text-[var(--text-main)] transition-colors flex items-center justify-center cursor-pointer ml-auto"
          title="Export Markdown report"
          aria-label="Export Markdown report"
        >
          <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
            <polyline points="7 10 12 15 17 10" />
            <line x1="12" y1="15" x2="12" y2="3" />
          </svg>
        </button>
      )}
    </div>
  );
}
