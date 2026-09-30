import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

function safeHttpUrl(value) {
  try {
    const url = new URL(value);
    return url.protocol === 'https:' || url.protocol === 'http:' ? url.href : null;
  } catch {
    return null;
  }
}

/**
 * Renders assistant output with a standards-compliant Markdown parser.
 * Raw HTML is deliberately not enabled; links are limited to http(s) and open
 * in a separate tab, so generated or sourced content cannot inject markup.
 */
export default function ChatMarkdown({ content }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      skipHtml
      components={{
        h1: ({ children }) => <h2 className="text-lg font-bold text-slate-100 mt-1 mb-3">{children}</h2>,
        h2: ({ children }) => <h3 className="text-base font-semibold text-slate-100 mt-4 mb-2">{children}</h3>,
        h3: ({ children }) => <h4 className="text-sm font-semibold text-slate-100 mt-3 mb-1.5">{children}</h4>,
        p: ({ children }) => <p className="my-2 first:mt-0 last:mb-0">{children}</p>,
        ul: ({ children }) => <ul className="list-disc pl-5 my-2 space-y-1.5">{children}</ul>,
        ol: ({ children }) => <ol className="list-decimal pl-5 my-2 space-y-1.5">{children}</ol>,
        strong: ({ children }) => <strong className="font-semibold text-slate-100">{children}</strong>,
        em: ({ children }) => <em className="italic text-slate-300">{children}</em>,
        a: ({ href, children }) => {
          const safeHref = safeHttpUrl(href || '');
          return safeHref ? (
            <a href={safeHref} target="_blank" rel="noopener noreferrer" className="text-cyan-400 underline underline-offset-2 hover:text-cyan-300 break-words">
              {children}
            </a>
          ) : <span>{children}</span>;
        },
        code: ({ children, className }) => <code className={className ? `block overflow-x-auto rounded-lg bg-[#0B1018] p-3 text-xs ${className}` : 'rounded bg-[#0B1018] px-1.5 py-0.5 text-xs text-cyan-200'}>{children}</code>,
        blockquote: ({ children }) => <blockquote className="border-l-2 border-cyan-500/60 pl-3 text-slate-400 italic my-3">{children}</blockquote>,
        hr: () => <hr className="my-4 border-slate-700" />,
      }}
    >
      {String(content || '')}
    </ReactMarkdown>
  );
}
