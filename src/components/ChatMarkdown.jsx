import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import hljs from 'highlight.js';
import 'highlight.js/styles/github-dark.css';

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
        h1: ({ children }) => <h2 className="text-lg font-bold text-[#E8E5DF] mt-1 mb-3">{children}</h2>,
        h2: ({ children }) => <h3 className="text-base font-semibold text-[#E8E5DF] mt-4 mb-2">{children}</h3>,
        h3: ({ children }) => <h4 className="text-sm font-semibold text-[#E8E5DF] mt-3 mb-1.5">{children}</h4>,
        p: ({ children }) => <p className="my-2 first:mt-0 last:mb-0">{children}</p>,
        ul: ({ children }) => <ul className="list-disc pl-5 my-2 space-y-1.5">{children}</ul>,
        ol: ({ children }) => <ol className="list-decimal pl-5 my-2 space-y-1.5">{children}</ol>,
        strong: ({ children }) => <strong className="font-semibold text-[#E8E5DF]">{children}</strong>,
        em: ({ children }) => <em className="italic text-[#8A8884]">{children}</em>,
        a: ({ href, children }) => {
          const safeHref = safeHttpUrl(href || '');
          return safeHref ? (
            <a href={safeHref} target="_blank" rel="noopener noreferrer" className="text-[#F15A3A] underline underline-offset-2 hover:text-[#E44D31] break-words">
              {children}
            </a>
          ) : <span>{children}</span>;
        },
        pre: ({ children }) => <>{children}</>,
        code: ({ children, className }) => <CodeBlock className={className}>{children}</CodeBlock>,
        blockquote: ({ children }) => <blockquote className="border-l-2 border-[#F15A3A]/60 pl-3 text-[#8A8884] italic my-3">{children}</blockquote>,
        hr: () => <hr className="my-4 border-[#303030]" />,
        table: ({ children }) => <div className="table-responsive my-4 rounded-lg border border-[#303030]"><table className="w-full border-collapse text-xs">{children}</table></div>,
        thead: ({ children }) => <thead className="bg-[#1B1B1B] text-[#E8E5DF]">{children}</thead>,
        th: ({ children }) => <th className="border-b border-[#303030] px-3 py-2 text-left font-semibold">{children}</th>,
        td: ({ children }) => <td className="border-b border-[#303030] px-3 py-2 align-top">{children}</td>,
        tr: ({ children }) => <tr className="odd:bg-[#181818] even:bg-[#1B1B1B]">{children}</tr>,
      }}
    >
      {String(content || '')}
    </ReactMarkdown>
  );
}

function CodeBlock({ children, className }) {
  const raw = String(children || '').replace(/\n$/, '');
  const language = (className || '').match(/language-([\w+-]+)/)?.[1];
  if (!language) return <code className="rounded bg-[#1B1B1B] px-1.5 py-0.5 text-xs text-[#E8E5DF]">{children}</code>;
  let highlighted = '';
  try {
    highlighted = hljs.getLanguage(language)
      ? hljs.highlight(raw, { language }).value
      : hljs.highlightAuto(raw).value;
  } catch { highlighted = raw; }
  const copy = async () => {
    try { await navigator.clipboard.writeText(raw); } catch { /* Clipboard may be unavailable. */ }
  };
  return <div className="my-3 overflow-hidden rounded-xl border border-[#303030] bg-[#181818] shadow-inner">
    <div className="flex items-center justify-between border-b border-[#303030] bg-[#1B1B1B] px-3 py-1.5 text-[11px]">
      <span className="font-mono uppercase tracking-wide text-[#8A8884]">{language}</span>
      <button type="button" onClick={copy} className="rounded px-2 py-1 text-[#8A8884] hover:bg-[#303030] hover:text-[#E8E5DF]">Copy</button>
    </div>
    <pre className="overflow-x-auto p-3 text-xs leading-relaxed"><code className={`hljs language-${language}`} dangerouslySetInnerHTML={{ __html: highlighted }} /></pre>
  </div>;
}
