import type React from "react";
import { useQuery } from "@tanstack/react-query";
import { BackendApi, type AdminStats, type SystemStatus } from "@/services/backend-api.service";
import {
  Server,
  Activity,
  Users,
  MessageSquare,
  CheckCircle2,
  XCircle,
  Clock,
  BarChart3,
} from "lucide-react";

interface DetailedHealth {
  services: Record<string, { status: string; latency_ms: number; last_check: string }>;
  agents: Record<string, { status: string; tools_count: number; enabled: boolean }>;
}

function StatCard({
  title,
  value,
  icon: Icon,
  subtitle,
}: {
  title: string;
  value: string | number;
  icon: React.ComponentType<{ className?: string }>;
  subtitle?: string;
}) {
  return (
    <div className="glass-panel p-5 relative overflow-hidden">
      <div className="flex justify-between items-start mb-4">
        <p className="text-outline text-[12px] uppercase font-mono">{title}</p>
        <Icon className="w-5 h-5 text-primary-brand" />
      </div>
      <h3 className="text-3xl font-bold text-on-surface">{value}</h3>
      {subtitle && <p className="text-[10px] text-outline font-mono mt-1">{subtitle}</p>}
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="glass-panel p-5 animate-pulse">
      <div className="h-3 w-24 bg-surface-container-highest rounded mb-4" />
      <div className="h-8 w-20 bg-surface-container-highest rounded" />
    </div>
  );
}

export function AdminPage() {
  const stats = useQuery<AdminStats>({
    queryKey: ["admin-stats"],
    queryFn: () => BackendApi.getAdminStats(),
    refetchInterval: 15000,
  });

  const health = useQuery<DetailedHealth>({
    queryKey: ["admin-health-detailed"],
    queryFn: () => BackendApi.getDetailedHealth() as Promise<DetailedHealth>,
    refetchInterval: 10000,
  });

  const isLoading = stats.isLoading || health.isLoading;

  return (
    <div className="dark bg-eye-bg min-h-screen">
      <main className="relative min-h-screen pb-16">
        <div className="absolute top-[-10%] right-[-5%] w-[600px] h-[600px] bg-primary-brand opacity-[0.08] blur-[80px] rounded-full pointer-events-none z-[-1]" />

        <div className="px-8 pt-8 max-w-[1400px] mx-auto">
          {/* Header */}
          <div className="flex items-center gap-3 mb-10">
            <Server className="w-8 h-8 text-primary-brand" />
            <div>
              <h1 className="text-2xl font-bold text-on-surface">System Admin</h1>
              <p className="text-sm text-outline font-mono">πX Backend — Python API Gateway</p>
            </div>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-10">
            {isLoading ? (
              <>
                <SkeletonCard />
                <SkeletonCard />
                <SkeletonCard />
                <SkeletonCard />
              </>
            ) : (
              <>
                <StatCard
                  title="Total Sessions"
                  value={stats.data?.total_sessions ?? 0}
                  icon={Users}
                />
                <StatCard
                  title="Total Messages"
                  value={stats.data?.total_messages ?? 0}
                  icon={MessageSquare}
                />
                <StatCard
                  title="Workflows"
                  value={`${stats.data?.workflows_completed ?? 0}/${(stats.data?.workflows_completed ?? 0) + (stats.data?.workflows_failed ?? 0)}`}
                  icon={Activity}
                  subtitle={`${stats.data?.workflows_failed ?? 0} failed`}
                />
                <StatCard
                  title="Uptime"
                  value={stats.data ? `${Math.round(stats.data.uptime_hours)}h` : "--"}
                  icon={Clock}
                />
              </>
            )}
          </div>

          {/* Health Status & Agents */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-10">
            {/* Service Health */}
            <div className="glass-panel p-6">
              <h2 className="text-base font-bold text-on-surface mb-6 flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-primary-brand" />
                Service Health
              </h2>
              <div className="space-y-4">
                {health.isLoading ? (
                  <div className="animate-pulse space-y-4">
                    {[...Array(3)].map((_, i) => (
                      <div key={i} className="h-10 bg-surface-container-highest rounded" />
                    ))}
                  </div>
                ) : health.data?.services ? (
                  Object.entries(health.data.services).map(([name, svc]) => (
                    <div
                      key={name}
                      className="flex items-center justify-between py-2 border-b border-outline-variant/20 last:border-0"
                    >
                      <div className="flex items-center gap-3">
                        {svc.status === "healthy" || svc.status === "ok" ? (
                          <CheckCircle2 className="w-4 h-4 text-green-400" />
                        ) : (
                          <XCircle className="w-4 h-4 text-red-400" />
                        )}
                        <span className="text-sm font-bold text-on-surface capitalize">{name}</span>
                      </div>
                      <span className="text-[11px] font-mono text-outline">{svc.latency_ms}ms</span>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-outline">No health data available</p>
                )}
              </div>
            </div>

            {/* Agents */}
            <div className="glass-panel p-6">
              <h2 className="text-base font-bold text-on-surface mb-6 flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-primary-brand" />
                Agent Status
              </h2>
              <div className="space-y-4">
                {health.isLoading ? (
                  <div className="animate-pulse space-y-4">
                    {[...Array(3)].map((_, i) => (
                      <div key={i} className="h-10 bg-surface-container-highest rounded" />
                    ))}
                  </div>
                ) : health.data?.agents ? (
                  Object.entries(health.data.agents).map(([name, agent]) => (
                    <div
                      key={name}
                      className="flex items-center justify-between py-2 border-b border-outline-variant/20 last:border-0"
                    >
                      <div className="flex items-center gap-3">
                        {agent.enabled ? (
                          <CheckCircle2 className="w-4 h-4 text-green-400" />
                        ) : (
                          <XCircle className="w-4 h-4 text-red-400" />
                        )}
                        <div>
                          <span className="text-sm font-bold text-on-surface capitalize">
                            {name}
                          </span>
                          <p className="text-[10px] font-mono text-outline">
                            {agent.tools_count} tools
                          </p>
                        </div>
                      </div>
                      <span
                        className={`text-[10px] font-mono px-2 py-0.5 border ${agent.enabled ? "text-green-400 border-green-400/20 bg-green-400/10" : "text-red-400 border-red-400/20 bg-red-400/10"}`}
                      >
                        {agent.enabled ? "ACTIVE" : "DISABLED"}
                      </span>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-outline">No agent data available</p>
                )}
              </div>
            </div>
          </div>

          {/* Tools Used Summary */}
          {stats.data?.tools_used && Object.keys(stats.data.tools_used).length > 0 && (
            <div className="glass-panel p-6 mb-10">
              <h2 className="text-base font-bold text-on-surface mb-6">Tools Usage</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {Object.entries(stats.data.tools_used).map(([tool, count]) => (
                  <div
                    key={tool}
                    className="flex justify-between items-center p-3 bg-surface-container-low border border-outline-variant/20"
                  >
                    <span className="text-sm font-mono text-on-surface">{tool}</span>
                    <span className="text-sm font-bold text-primary-brand">{count}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Average Response Time */}
          {stats.data && (
            <div className="glass-panel p-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Clock className="w-5 h-5 text-primary-brand" />
                  <span className="text-sm font-bold text-on-surface">Avg Response Time</span>
                </div>
                <span className="text-2xl font-bold text-primary-brand font-mono">
                  {stats.data.average_response_time_ms.toFixed(0)}ms
                </span>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
