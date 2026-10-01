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
      <div className="border-b border-[#303030] pb-3 flex items-center justify-between flex-wrap gap-2 font-sans">
        <div>
          <h2 className="text-base font-semibold text-[#E8E5DF] font-sans flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#F15A3A]" />
            Research Reports
          </h2>
          <p className="text-xs text-[#8A8884] mt-0.5 font-sans">
            Structured synthesis connecting methods, literature, experiments, and limitations
          </p>
        </div>

        {reportMd && onDownloadReport && (
          <button
            type="button"
            onClick={onDownloadReport}
            className="px-3.5 py-1.5 rounded-lg bg-[#F15A3A] hover:bg-[#E44D31] text-white text-xs font-semibold btn-transition flex items-center gap-1.5 cursor-pointer font-sans"
          >
            <span>↓ Download Markdown (.md)</span>
          </button>
        )}
      </div>

      {!reportMd ? (
        <div className="bg-[#181818] border border-[#303030] rounded-xl p-8 text-center space-y-2 font-sans">
          <p className="text-xs text-[#8A8884] font-sans">
            No research report generated yet.
          </p>
          <p className="text-xs text-[#8A8884] font-sans">
            Complete a research session to compile a full scientific paper / report.
          </p>
        </div>
      ) : (
        <div className="bg-[#181818] border border-[#303030] rounded-xl p-5 space-y-4 font-sans">
          <div className="text-xs font-medium text-[#8A8884] border-b border-[#303030] pb-2 flex items-center justify-between font-sans">
            <span>Question → Method → Sources → Experiments → Results → Limitations → Next steps</span>
            <span className="text-[#F15A3A] font-semibold">Compiled</span>
          </div>

          <div className="bg-[#121212] border border-[#303030] rounded-xl p-5 text-sm text-[#E8E5DF] font-sans leading-relaxed whitespace-pre-wrap break-words overflow-wrap-anywhere">
            <ChatMarkdown content={reportMd} />
          </div>
        </div>
      )}
    </div>
  );
}
