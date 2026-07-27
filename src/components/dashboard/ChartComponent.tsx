/** ChartComponent — Renders trend, distribution, and forecast charts from JSON config. */
import React, { useEffect, useRef } from 'react';

interface Props {
  widget: { config: Record<string, any>; label: string };
  orgId: string;
  events?: any[];
}

export const ChartComponent: React.FC<Props> = ({ widget }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { metric, chart_type = 'line', period = 'monthly' } = widget.config;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Placeholder chart — production uses recharts/chart.js
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.strokeStyle = '#C0C8D0';
    ctx.lineWidth = 2;
    ctx.beginPath();
    for (let i = 0; i < 12; i++) {
      const x = (i / 11) * canvas.width;
      const y = canvas.height - Math.random() * canvas.height * 0.8 - canvas.height * 0.1;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
  }, [metric]);

  return (
    <div className="space-y-2">
      <div className="text-xs text-muted-foreground">{metric} · {period}</div>
      <canvas ref={canvasRef} width={400} height={150} className="w-full" />
    </div>
  );
};
