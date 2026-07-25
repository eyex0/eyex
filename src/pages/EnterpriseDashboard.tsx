import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/layout/AppShell";
import { Card, Badge } from "@/components/common/primitives";
import {
  Loader2,
  Building2,
  TrendingUp,
  Shield,
  Lightbulb,
  Activity,
  BarChart3,
  Users,
  Database,
  FileText,
} from "lucide-react";

const BASE = "http://eyex-api:8000/api/v1/enterprise";

interface Insight {
  title: string;
  severity: string;
  type: string;
}

interface CompanyProfile {
  name?: string;
  industry?: string;
  key_people?: string[];
  products?: string[];
  competitors?: string[];
  risks?: string[];
  metrics?: Record<string, string | number>;
}

async function fetchJson(path: string) {
  const resp = await fetch(`${BASE}${path}`);
  if (!resp.ok) throw new Error(`Fetch failed: ${resp.status}`);
  return resp.json();
}

export function EnterpriseDashboardPage() {
  const [orgId] = useState("default");

  const { data: insights, isLoading: loadingInsights } = useQuery({
    queryKey: ["enterprise", "insights", orgId],
    queryFn: () => fetchJson(`/proactive-insights/${orgId}`),
    refetchInterval: 30000,
  });

  const { data: connectors } = useQuery({
    queryKey: ["enterprise", "connectors"],
    queryFn: () => fetchJson("/connectors"),
  });

  const { data: kgData, isLoading: loadingKG } = useQuery({
    queryKey: ["enterprise", "kg", orgId],
    queryFn: () => fetchJson(`/knowledge-graph/${orgId}`),
  });

  const nodes = kgData?.nodes || [];
  const profile = kgData?.company_profile || {};

  const metricCards = [
    {
      label: "Proactive Insights",
      value: insights?.total || 0,
      icon: Activity,
      color: "text-emerald-400",
    },
    {
      label: "Critical Alerts",
      value: insights?.critical_count || 0,
      icon: Shield,
      color: "text-red-400",
    },
    {
      label: "Opportunities",
      value: insights?.by_type?.opportunity || 0,
      icon: Lightbulb,
      color: "text-amber-400",
    },
    { label: "Knowledge Nodes", value: nodes.length, icon: Database, color: "text-blue-400" },
    {
      label: "Data Connectors",
      value: connectors?.count || 0,
      icon: FileText,
      color: "text-purple-400",
    },
    {
      label: "Metrics Tracked",
      value: Object.keys(profile.metrics || {}).length,
      icon: BarChart3,
      color: "text-white",
    },
  ];

  return (
    <AppShell title="Enterprise Console" subtitle="Multi-company AI intelligence platform">
      {/* Metric Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
        {metricCards.map((card) => (
          <div key={card.label} className="border border-border rounded-lg p-4">
            <card.icon size={18} className={`${card.color} mb-2`} />
            <div className="text-lg font-bold text-white">{card.value}</div>
            <div className="text-[10px] text-muted-foreground uppercase tracking-wider">
              {card.label}
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Proactive Insights */}
        <Card title="Proactive Intelligence">
          {loadingInsights ? (
            <div className="p-8 flex justify-center">
              <Loader2 className="animate-spin" size={20} />
            </div>
          ) : (
            <div className="divide-y divide-border">
              {insights?.insights?.slice(0, 8).map((i: Insight, idx: number) => (
                <div key={idx} className="px-5 py-3 flex items-start gap-3">
                  <div
                    className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${
                      i.severity === "critical" || i.severity === "high"
                        ? "bg-red-400"
                        : i.severity === "medium"
                          ? "bg-amber-400"
                          : "bg-emerald-400"
                    }`}
                  />
                  <div className="min-w-0">
                    <div className="text-xs text-white truncate">{i.title}</div>
                    <div className="text-[10px] text-muted-foreground mt-0.5">
                      {i.type} · {i.severity}
                    </div>
                  </div>
                </div>
              ))}
              {(!insights?.insights || insights.insights.length === 0) && (
                <div className="p-8 text-center text-xs text-muted-foreground">
                  No insights yet. Add company data to begin.
                </div>
              )}
            </div>
          )}
        </Card>

        {/* Company Profile */}
        <Card title="Company Knowledge Graph">
          {loadingKG ? (
            <div className="p-8 flex justify-center">
              <Loader2 className="animate-spin" size={20} />
            </div>
          ) : (
            <div className="p-5 space-y-3">
              <div className="flex items-center gap-2">
                <Building2 size={16} className="text-primary-brand" />
                <span className="text-sm font-medium text-white">{profile.name || "Unknown"}</span>
              </div>
              {profile.industry && (
                <div className="text-xs text-muted-foreground">Industry: {profile.industry}</div>
              )}
              <div className="grid grid-cols-2 gap-3 pt-3 border-t border-border">
                <div>
                  <div className="text-[10px] text-muted-foreground uppercase tracking-wider">
                    People
                  </div>
                  <div className="text-sm font-medium text-white">
                    {profile.key_people?.length || 0}
                  </div>
                </div>
                <div>
                  <div className="text-[10px] text-muted-foreground uppercase tracking-wider">
                    Products
                  </div>
                  <div className="text-sm font-medium text-white">
                    {profile.products?.length || 0}
                  </div>
                </div>
                <div>
                  <div className="text-[10px] text-muted-foreground uppercase tracking-wider">
                    Competitors
                  </div>
                  <div className="text-sm font-medium text-white">
                    {profile.competitors?.length || 0}
                  </div>
                </div>
                <div>
                  <div className="text-[10px] text-muted-foreground uppercase tracking-wider">
                    Risks
                  </div>
                  <div className="text-sm font-medium text-white">{profile.risks?.length || 0}</div>
                </div>
              </div>
              {Object.keys(profile.metrics || {}).length > 0 && (
                <div className="pt-3 border-t border-border">
                  <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-2">
                    Key Metrics
                  </div>
                  {Object.entries(profile.metrics as Record<string, string | number>)
                    .slice(0, 5)
                    .map(([k, v]) => (
                      <div key={k} className="flex justify-between text-[11px] py-1">
                        <span className="text-muted-foreground">{k.replace(/_/g, " ")}</span>
                        <span className="text-white font-mono">{v}</span>
                      </div>
                    ))}
                </div>
              )}
            </div>
          )}
        </Card>

        {/* Agent Analytics */}
        <Card title="Analytics Overview">
          <div className="p-5 space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="text-center p-3 border border-border rounded-lg">
                <div className="text-lg font-bold text-white">{insights?.by_type?.risk || 0}</div>
                <div className="text-[10px] text-muted-foreground">Risks</div>
              </div>
              <div className="text-center p-3 border border-border rounded-lg">
                <div className="text-lg font-bold text-white">
                  {insights?.by_type?.opportunity || 0}
                </div>
                <div className="text-[10px] text-muted-foreground">Opportunities</div>
              </div>
            </div>
            <div className="text-xs text-muted-foreground">
              <div className="flex justify-between py-1">
                <span>Data Sources</span>
                <span className="text-white">{connectors?.connectors?.join(", ") || "—"}</span>
              </div>
              <div className="flex justify-between py-1">
                <span>Knowledge Graph Nodes</span>
                <span className="text-white">{nodes.length}</span>
              </div>
              <div className="flex justify-between py-1">
                <span>Organization ID</span>
                <span className="text-white font-mono text-[10px]">{orgId}</span>
              </div>
            </div>
          </div>
        </Card>

        {/* Quick Actions */}
        <Card title="Enterprise Actions">
          <div className="p-5 space-y-3">
            {[
              { label: "View Reports", path: "/enterprise-reports", icon: TrendingUp },
              { label: "Connect Data Sources", path: "/data-sources", icon: Database },
            ].map((action) => (
              <a
                key={action.label}
                href={action.path}
                className="flex items-center gap-3 px-4 py-3 border border-border rounded-lg hover:bg-white/5 transition-colors text-xs"
              >
                <action.icon size={16} className="text-primary-brand" />
                <span className="text-white font-medium">{action.label}</span>
              </a>
            ))}
          </div>
        </Card>
      </div>
    </AppShell>
  );
}
