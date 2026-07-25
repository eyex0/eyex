import { useQuery } from "@tanstack/react-query";
import { BackendApi } from "@/services/backend-api.service";
import { AppShell } from "@/components/layout/AppShell";
import { useAuth } from "@/components/providers/auth-provider";

export function DashboardPage() {
  const { user } = useAuth();
  const name = user?.user_metadata?.full_name ?? user?.email ?? "User";

  const { data: stats } = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: () => BackendApi.getDashboardStats(),
    refetchInterval: 15000,
  });

  return (
    <AppShell title={`Welcome, ${name}`} subtitle="CORE_VISION_DASHBOARD">
      <div className="grid grid-cols-12 gap-6 pb-20">
        {/* Left Side: Live Feed */}
        <section className="col-span-12 xl:col-span-8 flex flex-col gap-6">
          <div className="relative w-full aspect-video rounded overflow-hidden glass-panel group border border-white/10">
            {/* Background Feed */}
            <div className="absolute inset-0 z-0">
              <img className="w-full h-full object-cover opacity-60" alt="Vision Feed" src="https://lh3.googleusercontent.com/aida-public/AB6AXuA73DLEcQ8ReVNMKWu1ZcRIxQ57HgSh60Xy5p8BKFHFcK8oG3MsT1NUaDo0xD6nCt4WX25XU6ZyeTG-X2WC5jTMW75Sbd94VtByCw8WXfA0fWHRUXJnxk3O9z_ylRFpp0SyIFxHDlKVSv-KV9v5aLO6CXt8BxQ_o-QpY17BuO8SnJtR2JSZrchCQh2JSmjOO502jyyhBc86kqu0GppmOgttXatGNrLMs53WkKopWJDLgf1bFGpLBREwAEB46QJtyWFJfgcEAZIg208B"/>
            </div>
            {/* HUD Overlays */}
            <div className="absolute inset-0 z-10 p-6 pointer-events-none flex flex-col justify-between">
              <div className="flex justify-between items-start">
                <div className="flex flex-col gap-2">
                  <div className="font-mono-data text-[12px] bg-black/60 px-3 py-1 border-l-2 border-secondary-fixed-dim">CAM_01 // SEC_SECTOR_7G</div>
                  <div className="font-mono-data text-[10px] text-on-surface-variant">UTC 2024-05-24 14:22:01.045</div>
                </div>
                <div className="flex gap-2">
                  <span className="material-symbols-outlined text-secondary-fixed-dim text-sm" style={{ fontVariationSettings: "'FILL' 1" }}>videocam</span>
                  <span className="font-mono-data text-[12px] text-primary">RECORDING_HD</span>
                </div>
              </div>
              {/* Bounding Boxes (Visual effects) */}
              <div className="absolute top-[30%] left-[25%] w-32 h-48 border border-secondary-fixed-dim bg-secondary-fixed-dim/10">
                <div className="bg-secondary-fixed-dim text-black font-mono-data text-[8px] px-1 inline-block">OBJECT_HUMAN_01: 99.4%</div>
              </div>
              <div className="absolute top-[50%] left-[60%] w-40 h-24 border border-secondary-fixed-dim bg-secondary-fixed-dim/10">
                <div className="bg-secondary-fixed-dim text-black font-mono-data text-[8px] px-1 inline-block">ASSET_ROBOT_A4: 98.2%</div>
              </div>
              <div className="flex justify-between items-end">
                <div className="flex flex-col gap-1">
                  <div className="h-1 w-48 bg-white/10">
                    <div className="h-full bg-secondary-fixed-dim w-3/4"></div>
                  </div>
                  <span className="font-mono-data text-[10px] text-on-surface-variant uppercase">Buffer Capacity</span>
                </div>
                <div className="flex gap-4">
                  <button className="pointer-events-auto px-4 py-2 bg-white text-black font-label-caps text-label-caps rounded-sm hover:opacity-80 transition-all">ZOOM_OPTIC</button>
                  <button className="pointer-events-auto px-4 py-2 border border-white/20 text-white font-label-caps text-label-caps rounded-sm hover:bg-white/5 transition-all">THERMAL_TOGGLE</button>
                </div>
              </div>
            </div>
          </div>
          
          {/* Bottom Section: System Performance */}
          <div className="glass-panel p-6 rounded-lg flex flex-col gap-4 border border-white/10">
            <div className="flex justify-between items-center">
              <h3 className="font-label-caps text-label-caps text-primary tracking-widest flex items-center gap-2">
                <span className="material-symbols-outlined text-sm">show_chart</span>
                SYSTEM_PERFORMANCE
              </h3>
              <div className="flex gap-4 font-mono-data text-[10px] text-on-surface-variant">
                <span className="flex items-center gap-1"><span className="w-2 h-2 bg-secondary-fixed-dim rounded-full"></span> GPU LOAD</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 bg-white rounded-full"></span> INF_TPS</span>
              </div>
            </div>
            <div className="h-48 w-full relative border border-white/10 bg-white/5">
              <div className="absolute inset-0 grid grid-cols-6 grid-rows-4 pointer-events-none opacity-10">
                {Array.from({ length: 24 }).map((_, i) => (
                  <div key={i} className="border-r border-b border-white"></div>
                ))}
              </div>
              <div className="absolute inset-0 flex items-end px-2 opacity-50">
              </div>
            </div>
          </div>
        </section>

        {/* Right Side: KPIs and Alerts */}
        <section className="col-span-12 xl:col-span-4 flex flex-col gap-6">
          {/* KPI Cards */}
          <div className="grid grid-cols-1 gap-4">
            <div className="glass-panel p-5 rounded-lg border border-white/10">
              <div className="font-label-caps text-[10px] text-on-surface-variant mb-1">TOTAL TASKS</div>
              <div className="flex items-end justify-between">
                <span className="font-mono-data text-4xl text-primary">{stats?.total_tasks ?? '—'}</span>
                <span className="font-mono-data text-[12px] text-secondary-fixed-dim">+{stats?.tasks_today ?? 0}</span>
              </div>
            </div>
            <div className="glass-panel p-5 rounded-lg border border-white/10">
              <div className="font-label-caps text-[10px] text-on-surface-variant mb-1">SUCCESS RATE</div>
              <div className="flex items-end justify-between">
                <span className="font-mono-data text-4xl text-primary">{stats?.success_rate ?? '—'}%</span>
                <span className="font-mono-data text-[12px] text-secondary-fixed-dim">STABLE</span>
              </div>
            </div>
            <div className="glass-panel p-5 rounded-lg border border-white/10">
              <div className="font-label-caps text-[10px] text-on-surface-variant mb-1">ACTIVE AGENTS</div>
              <div className="flex items-end justify-between">
                <span className="font-mono-data text-4xl text-primary">{stats?.active_agents_count ?? '—'}</span>
                <span className="font-mono-data text-[12px] text-secondary-fixed-dim">ONLINE</span>
              </div>
            </div>
          </div>

          {/* Real-time Alerts List */}
          <div className="glass-panel rounded-lg flex-1 flex flex-col overflow-hidden border border-white/10 min-h-[400px]">
            <div className="p-4 border-b border-white/5 flex justify-between items-center bg-white/5">
              <h3 className="font-label-caps text-label-caps text-primary">RECENT_TASKS</h3>
              <span className="px-2 py-0.5 bg-secondary-fixed-dim text-[10px] font-mono-data rounded text-black">LOGS</span>
            </div>
            <div className="flex-1 overflow-y-auto">
              {(stats?.recent_tasks ?? []).slice(0, 5).map((task: any) => (
                <div key={task.id} className="p-4 border-b border-white/5 hover:bg-white/5 transition-colors cursor-pointer group">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-mono-data text-[10px] text-secondary-fixed-dim">{task.status}</span>
                    <span className="font-mono-data text-[10px] text-on-surface-variant">{task.created_at ? new Date(task.created_at).toLocaleTimeString() : '—'}</span>
                  </div>
                  <p className="font-body-md text-sm text-primary mb-1 truncate">{task.agent_role ?? "Task"}</p>
                  <span className="font-label-caps text-[9px] text-on-surface-variant group-hover:text-secondary-fixed-dim">VIEW_DETAILS →</span>
                </div>
              ))}
              {(!stats?.recent_tasks || stats.recent_tasks.length === 0) && (
                <div className="p-8 text-center font-mono-data text-xs text-on-surface-variant">NO_TASKS_DETECTED</div>
              )}
            </div>
          </div>
        </section>
      </div>
    </AppShell>
  );
}
