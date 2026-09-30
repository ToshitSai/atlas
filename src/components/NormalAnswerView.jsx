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
      <div className="bg-[#0B0B0B] border border-[#242424] rounded-xl p-4 space-y-1.5 font-sans">
        <div className="text-xs font-medium text-[#FF6500] font-sans">
          Question
        </div>
        <h2 className="text-base font-semibold text-[#F4F4F6] font-sans leading-relaxed break-words overflow-wrap-anywhere">
          {userQuestion}
        </h2>
      </div>

      {/* Answer Body Card */}
      <div className="bg-[#0B0B0B] border border-[#242424] rounded-xl p-4 sm:p-5 space-y-4 font-sans">
        <div className="flex items-center justify-between border-b border-[#242424] pb-2.5 font-sans">
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 rounded bg-[#FF6500]/10 border border-[#FF6500]/30 flex items-center justify-center shrink-0">
              <svg className="w-3 h-3 text-[#FF6500]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" aria-hidden="true">
                <circle cx="12" cy="12" r="3" />
                <path d="M12 3a9 9 0 0 1 9 9" />
              </svg>
            </div>
            <h3 className="text-sm font-semibold text-[#F4F4F6] font-sans">
              Answer
            </h3>
          </div>

          {/* Honest Disclosure if built-in explanation */}
          {isBuiltInExplanation && (
            <span className="text-xs font-normal text-[#8A8F98] bg-[#141416] border border-[#242424] px-2.5 py-0.5 rounded-full font-sans">
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
          <div className="pt-3 border-t border-[#242424] space-y-2 font-sans">
            <div className="text-xs font-medium text-[#8A8F98] font-sans">
              Sources
            </div>
            <div className="space-y-1 font-sans">
              {sources.map((src, idx) => (
                <div key={idx} className="text-xs flex items-center gap-2 font-sans">
                  <span className="text-[#FF6500] font-sans text-xs">•</span>
                  <a
                    href={src.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[#F4F4F6] hover:text-[#FF6500] underline text-xs transition-colors truncate font-sans"
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
