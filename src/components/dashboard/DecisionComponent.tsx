/** DecisionComponent — Renders the decision queue widget from the Decision Engine. */
import React, { useEffect, useState } from 'react';

interface Props {
  widget: { config: Record<string, any>; label: string };
  orgId: string;
  events?: any[];
}

export const DecisionComponent: React.FC<Props> = ({ widget, events = [] }) => {
  const { status_filter = 'pending', max_items = 10 } = widget.config;
  const [decisions, setDecisions] = useState<any[]>([]);

  useEffect(() => {
    // Add decisions from events
    const newDecisions = events
      .filter((e) => e.event_type === 'DECISION_CREATED')
      .map((e) => e.payload);
    if (newDecisions.length) {
      setDecisions((prev) => [...newDecisions, ...prev].slice(0, max_items));
    }
  }, [events, max_items]);

  return (
    <div className="space-y-2 max-h-48 overflow-y-auto">
      {decisions.length === 0 ? (
        <div className="text-sm text-muted-foreground">No {status_filter} decisions</div>
      ) : (
        decisions.map((d, i) => (
          <div key={i} className="flex items-center justify-between p-2 rounded border bg-muted/50">
            <div>
              <div className="text-sm font-medium">{d.title || d.decision_id}</div>
              <div className="text-xs text-muted-foreground">{d.status || 'pending'}</div>
            </div>
            <div className={`text-xs px-2 py-0.5 rounded ${d.priority === 'high' ? 'bg-destructive/10 text-destructive' : 'bg-muted text-muted-foreground'}`}>
              {d.priority || 'normal'}
            </div>
          </div>
        ))
      )}
    </div>
  );
};
