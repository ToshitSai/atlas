import React from 'react';

function inlineMarkdown(text) {
  const parts = String(text || '').split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, index) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong className="font-semibold text-slate-100" key={index}>{part.slice(2, -2)}</strong>;
    }
    return part;
  });
}

/** Small safe Markdown subset for assistant messages: headings, bold, bullets, and paragraphs. */
export default function ChatMarkdown({ content }) {
  const lines = String(content || '').split('\n');
  const nodes = [];
  let bullets = [];
  const flushBullets = () => {
    if (!bullets.length) return;
    nodes.push(<ul className="list-disc pl-5 space-y-1.5" key={`list-${nodes.length}`}>
      {bullets.map((item, index) => <li key={index}>{inlineMarkdown(item)}</li>)}
    </ul>);
    bullets = [];
  };

  lines.forEach((line, index) => {
    const bullet = line.match(/^\s*[-*]\s+(.+)$/);
    if (bullet) {
      bullets.push(bullet[1]);
      return;
    }
    flushBullets();
    if (!line.trim()) {
      nodes.push(<div className="h-2" key={`space-${index}`} />);
    } else if (line.startsWith('### ')) {
      nodes.push(<h5 className="font-semibold text-slate-100" key={index}>{inlineMarkdown(line.slice(4))}</h5>);
    } else if (line.startsWith('## ')) {
      nodes.push(<h4 className="font-semibold text-slate-100" key={index}>{inlineMarkdown(line.slice(3))}</h4>);
    } else if (/^-{3,}\s*$/.test(line)) {
      nodes.push(<hr className="my-3 border-slate-700" key={index} />);
    } else {
      nodes.push(<p key={index}>{inlineMarkdown(line)}</p>);
    }
  });
  flushBullets();
  return <div className="space-y-1.5">{nodes}</div>;
}
