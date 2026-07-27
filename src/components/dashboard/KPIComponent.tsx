/** KPIComponent — Renders a single KPI card with value, delta, and target. */
import React, { useEffect, useState } from 'react';

interface Props {
  widget: { config: Record<string, any>; label: string };
  orgId: string;
  events?: any[];
}

export const KPIComponent: React.FC<Props> = ({ widget, events = [] }) => {
  const { metric, format = 'number', target, unit = '' } = widget.config;
  const [value, setValue] = useState<number | null>(null);
  const [delta, setDelta] = useState<number | null>(null);

  // In production, fetch from dashboard data service
  // For now, render from events or placeholder
  useEffect(() => {
    const kpiEvent = events.find((e) => e.payload?.kpi === metric);
    if (kpiEvent) {
      setValue(kpiEvent.payload.new_value);
      if (kpiEvent.payload.old_value) {
        setDelta(((kpiEvent.payload.new_value - kpiEvent.payload.old_value) / kpiEvent.payload.old_value) * 100);
      }
    }
  }, [events, metric]);

  const formatValue = (v: number) => {
    if (format === 'currency') return `$${v.toLocaleString()}`;
    if (format === 'percentage') return `${v.toFixed(1)}%`;
    return v.toLocaleString();
  };

  return (
    <div className="space-y-2">
      <div className="text-3xl font-semibold text-foreground">
        {value !== null ? formatValue(value) : '—'}
        {unit && <span className="text-lg text-muted-foreground ml-1">{unit}</span>}
      </div>
      {delta !== null && (
        <div className={`text-sm ${delta >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-destructive'}`}>
          {delta >= 0 ? '↑' : '↓'} {Math.abs(delta).toFixed(1)}%
        </div>
      )}
      {target && (
        <div className="text-xs text-muted-foreground">
          Target: {formatValue(target)}
        </div>
      )}
    </div>
  );
};
