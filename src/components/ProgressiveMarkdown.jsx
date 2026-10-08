import React, { useEffect, useRef, useState } from 'react';
import ChatMarkdown from './ChatMarkdown';

// Queues streamed deltas and reveals them on animation frames. This keeps the
// markdown renderer stable while still making the response feel live.
export default function ProgressiveMarkdown({ content = '', streaming = false, onRevealAll }) {
  const [visible, setVisible] = useState(content);
  const visibleRef = useRef(content);
  const queueRef = useRef('');
  const frameRef = useRef(null);
  const lastRef = useRef(0);
  const targetRef = useRef(content);
  useEffect(() => {
    targetRef.current = content;
    if (!streaming && visibleRef.current.length === 0) {
      visibleRef.current = content;
      queueRef.current = '';
      setVisible(content);
      return undefined;
    }
    if (content.length < visibleRef.current.length) {
      queueRef.current = '';
      visibleRef.current = content;
      setVisible(content);
      return undefined;
    }
    queueRef.current = content.slice(visibleRef.current.length);
    const tick = (now) => {
      const backlog = queueRef.current.length;
      if (backlog) {
        const elapsed = lastRef.current ? now - lastRef.current : 16;
        const rate = Math.min(420, 120 + Math.max(0, backlog - 240) * 0.45);
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
  }, [content, streaming]);
  const reveal = () => {
    queueRef.current = '';
    visibleRef.current = content;
    setVisible(content);
    onRevealAll?.();
  };
  return <div className={streaming ? 'progressive-answer is-streaming' : 'progressive-answer'} onClick={reveal} onKeyDown={(event) => { if (event.key === 'Escape') reveal(); }} tabIndex={streaming ? 0 : undefined}>
    <ChatMarkdown content={visible} />
  </div>;
}
