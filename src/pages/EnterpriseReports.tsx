import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/layout/AppShell";
import { Card, Badge } from "@/components/common/primitives";
import { Loader2, FileText, TrendingUp, Shield, Lightbulb, Activity, Download } from "lucide-react";

const BASE = "http://eyex-api:8000/api/v1/enterprise";

interface Risk {
  title: string;
  description: string;
  severity?: string;
}

interface Opportunity {
  title: string;
  description: string;
}

async function fetchJson(path: string) {
  const resp = await fetch(`${BASE}${path}`);
  if (!resp.ok) throw new Error(`Fetch failed: ${resp.status}`);
  return resp.json();
}

const REPORT_TYPES = [
  {
    key: "weekly-executive",
    label: "Weekly Executive",
    icon: TrendingUp,
    description: "Strategic overview with key metrics and priorities",
  },
  {
    key: "risk",
    label: "Risk Assessment",
    icon: Shield,
    description: "Risk scoring, identified risks, and mitigation strategies",
  },
  {
    key: "opportunity",
    label: "Opportunity Analysis",
    icon: Lightbulb,
    description: "Growth opportunities and market insights",
  },
  {
    key: "performance",
    label: "Performance Summary",
    icon: Activity,
    description: "Agent analytics, trends, and recommendation velocity",
  },
];

export function EnterpriseReportsPage() {
  const [orgId] = useState("default");
  const [activeReport, setActiveReport] = useState("weekly-executive");

  const { data, isLoading, error } = useQuery({
    queryKey: ["enterprise", "report", activeReport, orgId],
    queryFn: () => fetchJson(`/reports/${activeReport}/${orgId}`),
    refetchInterval: 60000,
  });

  const activeConfig = REPORT_TYPES.find((r) => r.key === activeReport);

  return (
    <AppShell title="Business Intelligence Reports" subtitle="AI-generated executive reports">
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Sidebar */}
        <div className="space-y-2">
          {REPORT_TYPES.map((report) => (
            <button
              key={report.key}
              onClick={() => setActiveReport(report.key)}
              className={`w-full text-left px-4 py-3 rounded-md text-xs transition-colors ${
                activeReport === report.key
                  ? "bg-white/10 border border-white/20 text-white"
                  : "text-muted-foreground hover:text-white hover:bg-white/5"
              }`}
            >
              <div className="flex items-center gap-2">
                <report.icon size={14} />
                <span className="font-medium">{report.label}</span>
              </div>
              <div className="text-[10px] mt-1 opacity-60">{report.description}</div>
            </button>
          ))}
        </div>

        {/* Report Content */}
        <div className="lg:col-span-3">
          <Card title={activeConfig?.label || "Report"}>
            {isLoading ? (
              <div className="p-12 flex justify-center">
                <Loader2 className="animate-spin" size={24} />
              </div>
            ) : error ? (
              <div className="p-8 text-center text-xs text-muted-foreground">
                <p>Error loading report.</p>
                <p className="mt-2">Please try again later or contact support.</p>
              </div>
            ) : data ? (
              <div className="p-6 space-y-4">
                {/* Header */}
                <div className="flex items-start justify-between border-b border-border pb-4">
                  <div>
                    <div className="text-sm font-medium text-white">
                      {data.report_type?.replace(/_/g, " ")}
                    </div>
                    <div className="text-[10px] text-muted-foreground font-mono mt-1">
                      Generated:{" "}
                      {data.generated_at ? new Date(data.generated_at).toLocaleString() : "—"}
                    </div>
                    {data.company && (
                      <div className="text-xs text-muted-foreground mt-1">{data.company}</div>
                    )}
                  </div>
                  <Badge tone="neutral">{data.org_id}</Badge>
                </div>

                {/* Executive Summary */}
                {data.executive_summary && (
                  <div className="bg-white/5 border border-border rounded-lg p-4">
                    <div className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">
                      Executive Summary
                    </div>
                    <div className="text-xs text-white leading-relaxed">
                      {data.executive_summary}
                    </div>
                  </div>
                )}

                {/* Key Metrics */}
                {data.key_metrics && Object.keys(data.key_metrics).length > 0 && (
                  <div>
                    <div className="text-[10px] uppercase tracking-wider text-muted-foreground mb-2">
                      Key Metrics
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                      {Object.entries(data.key_metrics)
                        .slice(0, 12)
                        .map(([k, v]) => (
                          <div key={k} className="border border-border rounded p-2">
                            <div className="text-[10px] text-muted-foreground truncate">
                              {k.replace(/_/g, " ")}
                            </div>
                            <div className="text-xs text-white font-mono">{String(v)}</div>
                          </div>
                        ))}
                    </div>
                  </div>
                )}

                {/* Top Priorities */}
                {data.top_priorities && data.top_priorities.length > 0 && (
                  <div>
                    <div className="text-[10px] uppercase tracking-wider text-muted-foreground mb-2">
                      Top Priorities
                    </div>
                    <div className="space-y-2">
                      {data.top_priorities.map((p: string, i: number) => (
                        <div key={i} className="flex items-center gap-2 text-xs">
                          <span className="w-5 h-5 rounded-full bg-white/10 text-white flex items-center justify-center text-[10px] shrink-0">
                            {i + 1}
                          </span>
                          <span className="text-muted-foreground">{p}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Risk Breakdown */}
                {data.risk_breakdown && (
                  <div>
                    <div className="text-[10px] uppercase tracking-wider text-muted-foreground mb-2">
                      Risk Breakdown
                    </div>
                    <div className="grid grid-cols-4 gap-2">
                      {Object.entries(data.risk_breakdown).map(([k, v]) => (
                        <div key={k} className="border border-border rounded p-2 text-center">
                          <div className="text-lg font-bold text-white">{String(v)}</div>
                          <div className="text-[9px] text-muted-foreground uppercase">{k}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Identified Risks */}
                {data.identified_risks && data.identified_risks.length > 0 && (
                  <div>
                    <div className="text-[10px] uppercase tracking-wider text-muted-foreground mb-2">
                      Identified Risks
                    </div>
                    <div className="space-y-2">
                      {data.identified_risks.map((r: Risk, i: number) => (
                        <div
                          key={i}
                          className="flex items-start gap-2 text-xs border border-border rounded p-3"
                        >
                          <Shield
                            size={12}
                            className={`mt-0.5 shrink-0 ${
                              r.severity === "critical" || r.severity === "high"
                                ? "text-red-400"
                                : "text-amber-400"
                            }`}
                          />
                          <div>
                            <div className="text-white font-medium">{r.title}</div>
                            <div className="text-muted-foreground mt-0.5">{r.description}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Opportunities */}
                {data.ai_detected_opportunities && data.ai_detected_opportunities.length > 0 && (
                  <div>
                    <div className="text-[10px] uppercase tracking-wider text-muted-foreground mb-2">
                      Detected Opportunities
                    </div>
                    <div className="space-y-2">
                      {data.ai_detected_opportunities.map((o: Opportunity, i: number) => (
                        <div
                          key={i}
                          className="flex items-start gap-2 text-xs border border-border rounded p-3"
                        >
                          <Lightbulb size={12} className="text-amber-400 mt-0.5 shrink-0" />
                          <div>
                            <div className="text-white font-medium">{o.title}</div>
                            <div className="text-muted-foreground mt-0.5">{o.description}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Analytics Snapshot */}
                {data.analytics_snapshot && (
                  <div className="border-t border-border pt-4">
                    <div className="text-[10px] uppercase tracking-wider text-muted-foreground mb-2">
                      Analytics Snapshot
                    </div>
                    <div className="grid grid-cols-5 gap-2">
                      {Object.entries(data.analytics_snapshot).map(([k, v]) => (
                        <div key={k} className="text-center">
                          <div className="text-sm font-bold text-white">{String(v)}</div>
                          <div className="text-[9px] text-muted-foreground uppercase">
                            {k.replace(/_/g, " ")}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="p-8 text-center text-xs text-muted-foreground">No data available</div>
            )}
          </Card>
        </div>
      </div>
    </AppShell>
  );
}
