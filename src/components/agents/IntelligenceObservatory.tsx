/**
 * πX Intelligence Observatory — Enterprise observability dashboard.
 * 4 views: CEO, CTO, CFO, CISO. Dark #050816, titanium/silver accents, 8px grid.
 */
import React, { useEffect, useState, useCallback } from 'react';

type ViewType = 'ceo' | 'cto' | 'cfo' | 'ciso';

interface MetricCard {
  label: string;
  value: string | number;
  unit?: string;
  trend?: 'up' | 'down' | 'stable';
}

export const IntelligenceObservatory: React.FC<{ orgId: string; apiUrl?: string }> = ({
  orgId,
  apiUrl = '/api/v1/agents',
}) => {
  const [view, setView] = useState<ViewType>('ceo');
  const [data, setData] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(false);
  const [events, setEvents] = useState<any[]>([]);

  const fetchDashboard = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${apiUrl}/observatory/dashboard?org_id=${orgId}&view=${view}`);
      const json = await res.json();
      setData(json);
    } catch (e) {
      // Fallback mock data for development
      setData(getMockData(view));
    }
    setLoading(false);
  }, [orgId, apiUrl, view]);

  const fetchEvents = useCallback(async () => {
    try {
      const res = await fetch(`${apiUrl}/observatory/events?org_id=${orgId}&limit=20`);
      const json = await res.json();
      setEvents(json.events || []);
    } catch (e) {
      setEvents([]);
    }
  }, [orgId, apiUrl]);

  useEffect(() => {
    fetchDashboard();
    fetchEvents();
  }, [fetchDashboard, fetchEvents]);

  const viewTabs: { key: ViewType; label: string; icon: string }[] = [
    { key: 'ceo', label: 'CEO', icon: '◆' },
    { key: 'cto', label: 'CTO', icon: '⚙' },
    { key: 'cfo', label: 'CFO', icon: '◆' },
    { key: 'ciso', label: 'CISO', icon: '🛡' },
  ];

  const renderView = () => {
    switch (view) {
      case 'ceo':
        return (
          <div className="grid grid-cols-4 gap-4">
            <MetricCard label="Total AI Cost" value={`$${(data.total_ai_cost || 0).toFixed(2)}`} />
            <MetricCard label="Active Agents" value={data.agent_count || 0} />
            <MetricCard label="Agent Performance" value={`${((data.avg_agent_performance || 0) * 100).toFixed(0)}%`} />
            <MetricCard label="Decision Accuracy" value={`${((data.decision_accuracy || 0) * 100).toFixed(0)}%`} />
            <div className="col-span-4 rounded-lg border border-zinc-800 p-4 bg-zinc-900/30">
              <h3 className="text-sm font-medium text-zinc-200 mb-2">Security Incidents</h3>
              <p className="text-2xl font-semibold text-zinc-100">{data.security_incidents || 0}</p>
              <p className="text-xs text-zinc-500 mt-1">High/critical severity in last 30 days</p>
            </div>
          </div>
        );
      case 'cto':
        return (
          <div className="grid grid-cols-4 gap-4">
            <MetricCard label="Avg Latency" value={`${data.avg_latency_ms || 0}`} unit="ms" />
            <MetricCard label="Total Errors" value={data.total_errors || 0} trend="down" />
            <MetricCard label="Total API Calls" value={data.total_calls || 0} />
            <MetricCard label="Security Alerts" value={data.security_alerts || 0} />
            <div className="col-span-4 rounded-lg border border-zinc-800 p-4 bg-zinc-900/30">
              <h3 className="text-sm font-medium text-zinc-200 mb-3">Model Performance</h3>
              <div className="space-y-2">
                {Object.entries(data.model_performance || {}).map(([model, score]) => (
                  <div key={model} className="flex items-center justify-between text-sm">
                    <span className="text-zinc-400">{model}</span>
                    <div className="flex items-center gap-2">
                      <div className="w-32 h-2 bg-zinc-800 rounded-full overflow-hidden">
                        <div className="h-full bg-[#C0C8D0] rounded-full" style={{ width: `${(Number(score) * 100)}%` }} />
                      </div>
                      <span className="text-zinc-300 tabular-nums">{(Number(score) * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        );
      case 'cfo':
        return (
          <div className="grid grid-cols-4 gap-4">
            <MetricCard label="Total AI Cost" value={`$${(data.total_ai_cost || 0).toFixed(2)}`} />
            <MetricCard label="Total Tokens" value={data.total_tokens || 0} />
            <MetricCard label="Cost/Call" value={`$${(data.cost_per_call || 0).toFixed(4)}`} />
            <MetricCard label="Projected Monthly" value={`$${(data.projected_monthly_cost || 0).toFixed(2)}`} />
            <div className="col-span-4 rounded-lg border border-zinc-800 p-4 bg-zinc-900/30">
              <h3 className="text-sm font-medium text-zinc-200 mb-3">Cost by Model</h3>
              <div className="space-y-2">
                {Object.entries(data.cost_by_model || {}).map(([model, cost]) => (
                  <div key={model} className="flex items-center justify-between text-sm">
                    <span className="text-zinc-400">{model}</span>
                    <span className="text-zinc-300 tabular-nums">${Number(cost).toFixed(4)}</span>
                  </div>
                ))}
                {Object.keys(data.cost_by_model || {}).length === 0 && (
                  <p className="text-zinc-600 text-sm">No cost data yet</p>
                )}
              </div>
            </div>
          </div>
        );
      case 'ciso':
        return (
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-4">
              <MetricCard label="Total Security Events" value={data.total_security_events || 0} />
              <MetricCard label="Critical Events" value={data.critical_events || 0} />
              <MetricCard label="High Severity" value={data.high_events || 0} />
            </div>
            <div className="rounded-lg border border-zinc-800 p-4 bg-zinc-900/30">
              <h3 className="text-sm font-medium text-zinc-200 mb-3">Recent Security Events</h3>
              <div className="space-y-2">
                {(data.recent_events || []).map((event: any, i: number) => (
                  <div key={i} className="flex items-center gap-3 text-sm py-2 border-b border-zinc-800/50">
                    <span className={`px-2 py-0.5 rounded text-xs ${
                      event.severity === 'critical' ? 'bg-red-900/50 text-red-400' :
                      event.severity === 'high' ? 'bg-amber-900/50 text-amber-400' :
                      'bg-zinc-800 text-zinc-400'
                    }`}>{event.severity}</span>
                    <span className="text-zinc-300 flex-1">{event.description}</span>
                    <span className="text-zinc-600 text-xs">{event.type}</span>
                  </div>
                ))}
                {(!data.recent_events || data.recent_events.length === 0) && (
                  <p className="text-zinc-600 text-sm">No security events</p>
                )}
              </div>
            </div>
          </div>
        );
    }
  };

  return (
    <div className="min-h-screen bg-[#050816] text-zinc-200" style={{ fontFamily: 'system-ui, -apple-system, sans-serif' }}>
      <header className="border-b border-zinc-800/50 px-8 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg border border-zinc-700 flex items-center justify-center">
            <span className="text-[#C0C8D0] text-sm font-bold">πX</span>
          </div>
          <h1 className="text-base font-semibold text-zinc-100">Intelligence Observatory</h1>
        </div>
        <div className="flex items-center gap-1">
          {viewTabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setView(tab.key)}
              className={`px-4 py-2 text-sm rounded-lg transition-colors ${
                view === tab.key
                  ? 'bg-zinc-900 text-[#C0C8D0] border border-zinc-700'
                  : 'text-zinc-500 hover:text-zinc-300 border border-transparent'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </header>

      <main className="p-8">
        {loading ? (
          <div className="text-center text-zinc-600 py-16 animate-pulse">Loading observatory data…</div>
        ) : (
          <>
            {renderView()}
            <div className="mt-6 rounded-lg border border-zinc-800 p-4 bg-zinc-900/30">
              <h3 className="text-sm font-medium text-zinc-200 mb-3">Event Feed</h3>
              <div className="space-y-1 max-h-64 overflow-y-auto">
                {events.map((event: any, i: number) => (
                  <div key={i} className="flex items-center gap-3 text-xs py-1.5">
                    <span className="text-zinc-600 tabular-nums">{new Date(event.timestamp).toLocaleTimeString()}</span>
                    <span className="px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400">{event.event_type}</span>
                    <span className="text-zinc-500 flex-1 truncate">{JSON.stringify(event.payload || {}).slice(0, 80)}</span>
                  </div>
                ))}
                {events.length === 0 && <p className="text-zinc-600 text-sm">No events</p>}
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
};

const MetricCard: React.FC<MetricCard> = ({ label, value, unit, trend }) => (
  <div className="rounded-lg border border-zinc-800 p-4 bg-zinc-900/30">
    <div className="text-xs text-zinc-500 uppercase tracking-wider">{label}</div>
    <div className="text-2xl font-semibold text-zinc-100 mt-2">
      {value}
      {unit && <span className="text-sm text-zinc-500 ml-1">{unit}</span>}
    </div>
    {trend && (
      <div className={`text-xs mt-1 ${trend === 'up' ? 'text-emerald-400' : trend === 'down' ? 'text-red-400' : 'text-zinc-500'}`}>
        {trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→'} {trend}
      </div>
    )}
  </div>
);

function getMockData(view: ViewType): Record<string, any> {
  switch (view) {
    case 'ceo':
      return { total_ai_cost: 0, agent_count: 0, avg_agent_performance: 0, decision_accuracy: 0, security_incidents: 0 };
    case 'cto':
      return { avg_latency_ms: 0, total_errors: 0, total_calls: 0, security_alerts: 0, model_performance: {} };
    case 'cfo':
      return { total_ai_cost: 0, total_tokens: 0, cost_per_call: 0, projected_monthly_cost: 0, cost_by_model: {} };
    case 'ciso':
      return { total_security_events: 0, critical_events: 0, high_events: 0, recent_events: [] };
  }
}
