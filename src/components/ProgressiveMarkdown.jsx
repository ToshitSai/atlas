import React, { useEffect, useRef, useState } from 'react';
import ChatMarkdown from './ChatMarkdown';

// Queues streamed deltas and reveals them on animation frames. This keeps the
// markdown renderer stable while still making the response feel live.
export default function ProgressiveMarkdown({ content = '', streaming = false, onRevealAll, instant = false, deliveryPath = 'unknown' }) {
  const safeContent = typeof content === 'string'
    ? content
    : (content ? (typeof content === 'object' ? JSON.stringify(content, null, 2) : String(content)) : '');
  const [visible, setVisible] = useState(instant ? safeContent : '');
  const visibleRef = useRef(instant ? safeContent : '');
  const queueRef = useRef('');
  const frameRef = useRef(null);
  const lastRef = useRef(0);
  const targetRef = useRef(safeContent);
  useEffect(() => {
    targetRef.current = safeContent;
    if (instant) {
      visibleRef.current = safeContent;
      queueRef.current = '';
      setVisible(safeContent);
      return undefined;
    }
    if (safeContent.length < visibleRef.current.length) {
      queueRef.current = '';
      visibleRef.current = safeContent;
      setVisible(safeContent);
      return undefined;
    }
    queueRef.current = safeContent.slice(visibleRef.current.length);
    const tick = (now) => {
      const backlog = queueRef.current.length;
      if (backlog) {
        const elapsed = lastRef.current ? now - lastRef.current : 16;
        const rate = Math.min(450, 200 + Math.max(0, backlog - 400) * 0.2);
        const count = Math.max(1, Math.round(rate * Math.min(elapsed, 40) / 1000));
        const next = queueRef.current.slice(0, count);
        queueRef.current = queueRef.current.slice(next.length);
        visibleRef.current += next;
        setVisible(visibleRef.current);
      }
      lastRef.current = now;
      if (queueRef.current.length || streaming) frameRef.current = requestAnimationFrame(tick);
      else frameRef.current = null;
    };
    if (!frameRef.current) frameRef.current = requestAnimationFrame(tick);
    return () => { if (frameRef.current) cancelAnimationFrame(frameRef.current); frameRef.current = null; };
  }, [safeContent, streaming, instant, deliveryPath]);
  const reveal = () => {
    queueRef.current = '';
    visibleRef.current = safeContent;
    setVisible(safeContent);
    onRevealAll?.();
  };
  return <div className={streaming ? 'progressive-answer is-streaming' : 'progressive-answer'} onClick={reveal} onKeyDown={(event) => { if (event.key === 'Escape') reveal(); }} tabIndex={streaming ? 0 : undefined}>
    <ChatMarkdown content={visible} />
    {!instant && queueRef.current.length > 0 && <button type="button" className="progressive-skip" onClick={(event) => { event.stopPropagation(); reveal(); }}>Skip</button>}
  </div>;
}
