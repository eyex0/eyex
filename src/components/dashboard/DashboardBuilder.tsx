/**
 * DashboardBuilder — User customization interface.
 * Lets users add/remove/rearrange widgets and save preferences.
 */
import React, { useState, useCallback } from 'react';
import { WidgetContainer } from './WidgetContainer';
import { DynamicWidgetRenderer } from './DynamicWidgetRenderer';

interface WidgetDef {
  id: string;
  type: string;
  label: string;
  config: Record<string, any>;
  position: [number, number];
  size: [number, number];
  component: string;
  data_keys: string[];
  category: string;
}

interface Props {
  orgId: string;
  userId: string;
  role: string;
  apiUrl?: string;
}

export const DashboardBuilder: React.FC<Props> = ({ orgId, userId, role, apiUrl = '/api/v1/dashboard' }) => {
  const [widgets, setWidgets] = useState<WidgetDef[]>([]);
  const [availableWidgets, setAvailableWidgets] = useState<any[]>([]);
  const [showPalette, setShowPalette] = useState(false);
  const [saving, setSaving] = useState(false);

  const fetchWidgets = useCallback(async () => {
    const res = await fetch(`${apiUrl}/${orgId}/generate?role=${role}`);
    const data = await res.json();
    setWidgets(data.layout);
  }, [orgId, role, apiUrl]);

  const fetchAvailable = useCallback(async () => {
    const res = await fetch(`${apiUrl}/${orgId}/widgets`);
    const data = await res.json();
    setAvailableWidgets(data.widgets);
  }, [orgId, apiUrl]);

  React.useEffect(() => {
    fetchWidgets();
    fetchAvailable();
  }, [fetchWidgets, fetchAvailable]);

  const removeWidget = async (id: string) => {
    await fetch(`${apiUrl}/${orgId}/widgets/${id}?user_id=${userId}`, { method: 'DELETE' });
    setWidgets((prev) => prev.filter((w) => w.id !== id));
  };

  const addWidget = async (widgetType: string, label: string, config: any = {}) => {
    const res = await fetch(`${apiUrl}/${orgId}/widgets/add?user_id=${userId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ widget_type: widgetType, label, config }),
    });
    const widget = await res.json();
    setWidgets((prev) => [...prev, widget]);
    setShowPalette(false);
  };

  const saveLayout = async () => {
    setSaving(true);
    const positions: Record<string, [number, number]> = {};
    widgets.forEach((w, i) => { positions[w.id] = [Math.floor(i / 4), i % 4]; });
    await fetch(`${apiUrl}/${orgId}/layout?user_id=${userId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ positions }),
    });
    setSaving(false);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Dashboard Builder</h2>
        <div className="flex gap-2">
          <button
            onClick={() => setShowPalette(!showPalette)}
            className="px-3 py-1.5 text-sm rounded-md border bg-secondary text-secondary-foreground hover:bg-accent"
          >
            {showPalette ? 'Close' : '+ Add Widget'}
          </button>
          <button
            onClick={saveLayout}
            disabled={saving}
            className="px-3 py-1.5 text-sm rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {saving ? 'Saving…' : 'Save Layout'}
          </button>
        </div>
      </div>

      {showPalette && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 p-4 rounded-lg border bg-muted/50">
          {availableWidgets.map((w) => (
            <button
              key={w.type}
              onClick={() => addWidget(w.type, w.label, {})}
              className="p-3 rounded-md border bg-card hover:bg-accent text-left"
            >
              <div className="text-sm font-medium">{w.label}</div>
              <div className="text-xs text-muted-foreground mt-1">{w.description}</div>
            </button>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {widgets.map((widget) => (
          <WidgetContainer key={widget.id} widget={widget} span={widget.size} onRemove={removeWidget}>
            <DynamicWidgetRenderer widget={widget} orgId={orgId} />
          </WidgetContainer>
        ))}
      </div>
    </div>
  );
};
