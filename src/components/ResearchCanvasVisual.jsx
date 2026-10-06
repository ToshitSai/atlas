import React, { useEffect, useRef } from 'react';

export default function ResearchCanvasVisual({ className = "" }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    // Some restricted/browser contexts can expose a canvas element without a
    // 2D context. The auth shell must still render in that case.
    if (!ctx) return;
    let animationFrameId;

    let width = (canvas.width = canvas.offsetWidth);
    let height = (canvas.height = canvas.offsetHeight);

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = canvas.offsetWidth;
      height = canvas.height = canvas.offsetHeight;
    };

    window.addEventListener('resize', handleResize);

    // Create research nodes
    const nodeCount = 38;
    const nodes = Array.from({ length: nodeCount }, () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      vx: (Math.random() - 0.5) * 0.35,
      vy: (Math.random() - 0.5) * 0.35,
      radius: Math.random() * 1.8 + 1,
      alpha: Math.random() * 0.5 + 0.3,
      pulse: Math.random() * Math.PI * 2,
    }));

    // Create trajectory pulses
    const pulseLines = [
      { start: 0, end: 5, progress: 0, speed: 0.005 },
      { start: 5, end: 12, progress: 0.3, speed: 0.007 },
      { start: 12, end: 20, progress: 0.6, speed: 0.004 },
      { start: 20, end: 28, progress: 0.1, speed: 0.006 },
    ];

    const render = () => {
      ctx.clearRect(0, 0, width, height);

      // Draw faint background orbital grid lines
      ctx.lineWidth = 0.5;
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.03)';
      const centerX = width * 0.5;
      const centerY = height * 0.5;

      [120, 240, 360, 480].forEach((r) => {
        ctx.beginPath();
        ctx.arc(centerX, centerY, r, 0, Math.PI * 2);
        ctx.stroke();
      });

      // Update & draw nodes
      nodes.forEach((node, i) => {
        node.x += node.vx;
        node.y += node.vy;
        node.pulse += 0.02;

        if (node.x < 0 || node.x > width) node.vx *= -1;
        if (node.y < 0 || node.y > height) node.vy *= -1;

        // Draw connections
        for (let j = i + 1; j < nodes.length; j++) {
          const other = nodes[j];
          const dx = other.x - node.x;
          const dy = other.y - node.y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < 140) {
            const lineAlpha = (1 - dist / 140) * 0.12;
            ctx.strokeStyle = `rgba(241, 90, 58, ${lineAlpha})`;
            ctx.lineWidth = 0.8;
            ctx.beginPath();
            ctx.moveTo(node.x, node.y);
            ctx.lineTo(other.x, other.y);
            ctx.stroke();
          }
        }

        // Draw node point
        const pulseAlpha = node.alpha + Math.sin(node.pulse) * 0.15;
        ctx.fillStyle = `rgba(241, 90, 58, ${pulseAlpha})`;
        ctx.beginPath();
        ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2);
        ctx.fill();
      });

      // Animate trajectory signal pulses
      pulseLines.forEach((p) => {
        p.progress += p.speed;
        if (p.progress > 1) p.progress = 0;

        const n1 = nodes[p.start % nodes.length];
        const n2 = nodes[p.end % nodes.length];
        if (n1 && n2) {
          const px = n1.x + (n2.x - n1.x) * p.progress;
          const py = n1.y + (n2.y - n1.y) * p.progress;

          ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
          ctx.beginPath();
          ctx.arc(px, py, 2.2, 0, Math.PI * 2);
          ctx.fill();

          // Subtle glow
          ctx.fillStyle = 'rgba(241, 90, 58, 0.25)';
          ctx.beginPath();
          ctx.arc(px, py, 6, 0, Math.PI * 2);
          ctx.fill();
        }
      });

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return (
    <div className={`relative w-full h-full overflow-hidden bg-[#070707] ${className}`}>
      <canvas ref={canvasRef} className="absolute inset-0 w-full h-full block" />
      <div className="absolute inset-0 bg-[radial-gradient(#1A1A1A_1px,transparent_1px)] [background-size:20px_20px] opacity-30 pointer-events-none" />
      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-transparent to-[#0A0A0A] pointer-events-none" />
    </div>
  );
}
