import React from 'react';
import ChatMarkdown from './ChatMarkdown';

/**
 * Normal Answer View:
 * For simple questions ("What is overfitting?"), shows a concise, readable answer
 * without the large research activity card or context sidebar.
 */
export default function NormalAnswerView({
  userQuestion = '',
  answer = '',
  routingMode = 'AUTO (Normal Answer)',
  isBuiltInExplanation = false,
  sources = [],
}) {
  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6 max-w-3xl mx-auto w-full space-y-5 animate-panel-entrance select-none font-sans">
      {/* User Question Header Card */}
      <div className="bg-[#0B0B0B] border border-[#242424] rounded-lg p-3.5 space-y-1">
        <div className="flex items-center justify-between text-[11px] font-mono text-[#8A8F98]">
          <span className="uppercase tracking-wider font-semibold text-[#FF6500]">User Question</span>
          <span className="px-2 py-0.5 rounded bg-[#141416] border border-[#242424] text-[10px]">
            {routingMode}
          </span>
        </div>
        <p className="text-sm font-medium text-[#F4F4F6] break-words overflow-wrap-anywhere">
          {userQuestion}
        </p>
      </div>

      {/* Answer Body Card */}
      <div className="bg-[#0B0B0B] border border-[#242424] rounded-lg p-4 sm:p-5 space-y-4">
        <div className="flex items-center justify-between border-b border-[#242424] pb-2.5">
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 rounded bg-[#FF6500]/10 border border-[#FF6500]/30 flex items-center justify-center shrink-0">
              <svg className="w-3 h-3 text-[#FF6500]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" aria-hidden="true">
                <circle cx="12" cy="12" r="3" />
                <path d="M12 3a9 9 0 0 1 9 9" />
              </svg>
            </div>
            <h3 className="text-xs font-mono font-bold text-[#F4F4F6] uppercase">
              Answer
            </h3>
          </div>

          {/* Honest Disclosure if built-in explanation */}
          {isBuiltInExplanation && (
            <span className="text-[10px] font-mono text-[#8A8F98] bg-[#141416] border border-[#242424] px-2 py-0.5 rounded">
              Built-in Knowledge Engine
            </span>
          )}
        </div>

        {/* Answer Content */}
        <div className="text-sm text-[#F4F4F6] leading-relaxed break-words overflow-wrap-anywhere space-y-3 font-sans">
          <ChatMarkdown content={answer} />
        </div>

        {/* Source citations if web search */}
        {sources && sources.length > 0 && (
          <div className="pt-3 border-t border-[#242424] space-y-1.5">
            <div className="text-[10px] font-mono uppercase tracking-wider text-[#8A8F98]">
              Sources
            </div>
            <div className="space-y-1">
              {sources.map((src, idx) => (
                <div key={idx} className="text-xs flex items-center gap-2">
                  <span className="text-[#FF6500] font-mono text-[10px]">•</span>
                  <a
                    href={src.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[#F4F4F6] hover:text-[#FF6500] underline text-xs transition-colors truncate"
                  >
                    {src.title || src.url}
                  </a>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
