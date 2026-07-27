/**
 * πX Dashboard Runtime — Main entry point for dynamic dashboard rendering.
 *
 * Fetches dashboard definition from backend and renders widgets from JSON.
 * No hardcoded layout — everything comes from the Dashboard Composition Engine.
 */
import React, { useEffect, useState, useCallback } from 'react';
import { DynamicWidgetRenderer } from './DynamicWidgetRenderer';
import { WidgetContainer } from './WidgetContainer';

interface WidgetDef {
  id: string;
  type: string;
  label: string;
  config: Record<string, any>;
  position: [number, number];
  size: [number, number];
  data_keys: string[];
  category: string;
  component: string;
  custom?: boolean;
}

interface DashboardData {
  dashboard_id: string;
  dashboard_type: string;
  title: string;
  subtitle: string;
  industry: string;
  role: string;
  layout: WidgetDef[];
  metadata: Record<string, any>;
}

interface DashboardRuntimeProps {
  orgId: string;
  role: string;
  userId: string;
  apiUrl?: string;
}

export const DashboardRuntime: React.FC<DashboardRuntimeProps> = ({
  orgId,
  role,
  userId,
  apiUrl = '/api/v1/dashboard',
}) => {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [events, setEvents] = useState<any[]>([]);

  const fetchDashboard = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${apiUrl}/${orgId}/generate?role=${role}`);
      const data = await res.json();
      setDashboard(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  }, [orgId, role, apiUrl]);

  useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard]);

  // SSE for live updates
  useEffect(() => {
    const eventSource = new EventSource(`${apiUrl}/${orgId}/events`);
    eventSource.onmessage = (e) => {
      const event = JSON.parse(e.data);
      setEvents((prev) => [...prev.slice(-99), event]);
      // Trigger dashboard refresh on relevant events
      if (['KPI_CHANGED', 'DATA_UPDATED', 'PROFILE_UPDATED'].includes(event.event_type)) {
        fetchDashboard();
      }
    };
    return () => eventSource.close();
  }, [orgId, apiUrl, fetchDashboard]);

  if (loading) return <div className="flex items-center justify-center h-96 text-muted-foreground">Generating dashboard…</div>;
  if (error) return <div className="text-destructive">Error: {error}</div>;
  if (!dashboard) return null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-foreground">{dashboard.title}</h1>
        <p className="text-sm text-muted-foreground mt-1">{dashboard.subtitle}</p>
      </div>

      {/* Widget Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {dashboard.layout.map((widget) => (
          <WidgetContainer
            key={widget.id}
            widget={widget}
            span={widget.size}
          >
            <DynamicWidgetRenderer
              widget={widget}
              orgId={orgId}
              events={events.filter((e) => widget.data_keys.some((k) => e.payload?.[k] !== undefined))}
            />
          </WidgetContainer>
        ))}
      </div>

      {/* Live event indicator */}
      {events.length > 0 && (
        <div className="text-xs text-muted-foreground">
          ● Live · {events.length} events
        </div>
      )}
    </div>
  );
};
