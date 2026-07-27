/**
 * WidgetContainer — Wraps widgets with consistent styling and grid placement.
 */
import React from 'react';

interface WidgetDef {
  id: string;
  type: string;
  label: string;
  config: Record<string, any>;
  position: [number, number];
  size: [number, number];
  category: string;
}

interface Props {
  widget: WidgetDef;
  span?: [number, number];
  onRemove?: (id: string) => void;
  onMove?: (id: string, direction: 'up' | 'down' | 'left' | 'right') => void;
  children: React.ReactNode;
}

export const WidgetContainer: React.FC<Props> = ({ widget, span = [1, 1], onRemove, onMove, children }) => {
  const colSpan = `md:col-span-${Math.min(span[0], 4)}`;
  const rowSpan = span[1] > 1 ? `md:row-span-${span[1]}` : '';

  return (
    <div
      data-widget-id={widget.id}
      data-widget-type={widget.type}
      data-widget-category={widget.category}
      className={`rounded-lg border bg-card text-card-foreground p-4 ${colSpan} ${rowSpan}`}
    >
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium text-foreground">{widget.label}</h3>
        {onRemove && (
          <button
            onClick={() => onRemove(widget.id)}
            className="text-xs text-muted-foreground hover:text-destructive"
            aria-label="Remove widget"
          >
            ✕
          </button>
        )}
      </div>
      <div className="widget-content">{children}</div>
    </div>
  );
};
