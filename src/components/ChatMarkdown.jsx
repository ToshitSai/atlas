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
        pre: ({ children }) => <>{children}</>,
        code: ({ children, className }) => <CodeBlock className={className}>{children}</CodeBlock>,
        blockquote: ({ children }) => <blockquote className="border-l-2 border-cyan-500/60 pl-3 text-slate-400 italic my-3">{children}</blockquote>,
        hr: () => <hr className="my-4 border-slate-700" />,
        table: ({ children }) => <div className="table-responsive my-4 rounded-lg border border-slate-700"><table className="w-full border-collapse text-xs">{children}</table></div>,
        thead: ({ children }) => <thead className="bg-slate-800/90 text-slate-100">{children}</thead>,
        th: ({ children }) => <th className="border-b border-slate-700 px-3 py-2 text-left font-semibold">{children}</th>,
        td: ({ children }) => <td className="border-b border-slate-800 px-3 py-2 align-top">{children}</td>,
        tr: ({ children }) => <tr className="odd:bg-slate-900/30 even:bg-slate-800/25">{children}</tr>,
      }}
    >
      {String(content || '')}
    </ReactMarkdown>
  );
}

function CodeBlock({ children, className }) {
  const raw = String(children || '').replace(/\n$/, '');
  const language = (className || '').match(/language-([\w+-]+)/)?.[1];
  if (!language) return <code className="rounded bg-[#0B1018] px-1.5 py-0.5 text-xs text-cyan-200">{children}</code>;
  let highlighted = '';
  try {
    highlighted = hljs.getLanguage(language)
      ? hljs.highlight(raw, { language }).value
      : hljs.highlightAuto(raw).value;
  } catch { highlighted = raw; }
  const copy = async () => {
    try { await navigator.clipboard.writeText(raw); } catch { /* Clipboard may be unavailable. */ }
  };
  return <div className="my-3 overflow-hidden rounded-xl border border-slate-700 bg-[#0B1018] shadow-inner">
    <div className="flex items-center justify-between border-b border-slate-700 bg-slate-900/80 px-3 py-1.5 text-[11px]">
      <span className="font-mono uppercase tracking-wide text-slate-400">{language}</span>
      <button type="button" onClick={copy} className="rounded px-2 py-1 text-slate-300 hover:bg-slate-700 hover:text-white">Copy</button>
    </div>
    <pre className="overflow-x-auto p-3 text-xs leading-relaxed"><code className={`hljs language-${language}`} dangerouslySetInnerHTML={{ __html: highlighted }} /></pre>
  </div>;
}
