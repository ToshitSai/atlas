import React from 'react';
import ChatMarkdown from './ChatMarkdown';

/**
 * Functional Reports View connecting Question -> Method -> Sources -> Experiments -> Results -> Limitations -> Next steps.
 * Provides working Markdown download button.
 */
export default function ReportsView({
  reportMd = null,
  onDownloadReport,
  userQuestion = '',
}) {
  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4 max-w-4xl mx-auto w-full select-none font-sans min-w-0 pb-32 animate-panel-entrance">
      <div className="border-b border-[#242424] pb-3 flex items-center justify-between flex-wrap gap-2">
        <div>
          <h2 className="text-base font-mono font-bold text-[#F4F4F6] uppercase flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#FF6500]" />
            Scientific Research Reports
          </h2>
          <p className="text-xs text-[#8A8F98] mt-0.5">
            Structured synthesis connecting methods, literature, experiments, and limitations
          </p>
        </div>

        {reportMd && onDownloadReport && (
          <button
            type="button"
            onClick={onDownloadReport}
            className="px-3 py-1.5 rounded bg-[#FF6500] hover:bg-[#FF302A] text-white text-xs font-semibold btn-transition flex items-center gap-1.5 cursor-pointer"
          >
            <span>↓ Download Markdown (.md)</span>
          </button>
        )}
      </div>

      {!reportMd ? (
        <div className="bg-[#0B0B0B] border border-[#242424] rounded p-8 text-center space-y-2">
          <p className="text-xs text-[#8A8F98] italic font-mono">
            No research report generated yet.
          </p>
          <p className="text-xs text-[#8A8F98]">
            Complete a research session to compile a full scientific paper / report.
          </p>
        </div>
      ) : (
        <div className="bg-[#0B0B0B] border border-[#242424] rounded p-5 space-y-4">
          <div className="text-xs font-mono text-[#8A8F98] border-b border-[#242424] pb-2 flex items-center justify-between">
            <span>Flow: Question → Method → Sources → Experiments → Results → Limitations → Next steps</span>
            <span className="text-[#FF6500]">STATUS: COMPILED</span>
          </div>

          <div className="bg-[#080808] border border-[#242424] rounded p-4 text-xs sm:text-sm text-[#F4F4F6] font-sans leading-relaxed whitespace-pre-wrap break-words overflow-wrap-anywhere">
            <ChatMarkdown content={reportMd} />
          </div>
        </div>
      )}
    </div>
  );
}
