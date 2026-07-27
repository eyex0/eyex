/**
 * πX Agent Command Center — Autonomous AI workforce interface.
 * Dark-first #050816 with titanium/silver accents. 8px grid.
 * Shows active agents, conversations, tasks, decisions, performance, memory timeline.
 */
import React, { useEffect, useState, useCallback } from 'react';

interface AgentInstance {
  agent_id: string;
  type: string;
  label: string;
  purpose: string;
  status: 'active' | 'paused' | 'stopped' | 'error';
  conversations: number;
  decisions: number;
  performance_score: number;
  last_active: string;
}

interface AgentMessage {
  role: 'user' | 'agent';
  content: string;
  timestamp: string;
}

interface AgentTask {
  id: string;
  agent_label: string;
  query: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  result?: string;
  confidence?: number;
}

interface MemoryEntry {
  id: string;
  memory_type: 'short_term' | 'long_term' | 'experience' | 'decision_history';
  content: string;
  importance: number;
  created_at: string;
}

const STATUS_COLORS: Record<string, string> = {
  active: 'text-emerald-400',
  paused: 'text-amber-400',
  stopped: 'text-zinc-500',
  error: 'text-red-400',
};

const STATUS_DOT: Record<string, string> = {
  active: 'bg-emerald-400',
  paused: 'bg-amber-400',
  stopped: 'bg-zinc-600',
  error: 'bg-red-400',
};

export const AgentCommandCenter: React.FC<{ orgId: string; apiUrl?: string }> = ({
  orgId,
  apiUrl = '/api/v1/agents',
}) => {
  const [agents, setAgents] = useState<AgentInstance[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [tasks, setTasks] = useState<AgentTask[]>([]);
  const [memory, setMemory] = useState<MemoryEntry[]>([]);
  const [performance, setPerformance] = useState<any>(null);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState<'conversation' | 'tasks' | 'memory' | 'performance'>('conversation');

  const fetchAgents = useCallback(async () => {
    try {
      const res = await fetch(`${apiUrl}?org_id=${orgId}`);
      const data = await res.json();
      setAgents(data.agents || []);
    } catch (e) {
      console.error('Failed to fetch agents:', e);
    }
  }, [orgId, apiUrl]);

  useEffect(() => {
    fetchAgents();
  }, [fetchAgents]);

  const executeQuery = async () => {
    if (!selectedAgent || !query.trim()) return;
    setLoading(true);
    const userMsg: AgentMessage = { role: 'user', content: query, timestamp: new Date().toISOString() };
    setMessages((prev) => [...prev, userMsg]);
    try {
      const res = await fetch(`${apiUrl}/${selectedAgent}/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      });
      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        { role: 'agent', content: data.response, timestamp: new Date().toISOString() },
      ]);
      setTasks((prev) => [
        ...prev,
        {
          id: `task_${Date.now()}`,
          agent_label: agents.find((a) => a.agent_id === selectedAgent)?.label || 'Agent',
          query,
          status: 'completed',
          result: data.response,
          confidence: data.confidence,
        },
      ]);
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        { role: 'agent', content: 'Error executing query', timestamp: new Date().toISOString() },
      ]);
    }
    setQuery('');
    setLoading(false);
  };

  const fetchMemory = async () => {
    if (!selectedAgent) return;
    try {
      const res = await fetch(`${apiUrl}/${selectedAgent}/memory?limit=20`);
      const data = await res.json();
      setMemory(data.memory || []);
    } catch (e) {
      console.error('Failed to fetch memory:', e);
    }
  };

  const fetchPerformance = async () => {
    if (!selectedAgent) return;
    try {
      const res = await fetch(`${apiUrl}/${selectedAgent}/performance`);
      const data = await res.json();
      setPerformance(data);
    } catch (e) {
      console.error('Failed to fetch performance:', e);
    }
  };

  useEffect(() => {
    if (tab === 'memory') fetchMemory();
    if (tab === 'performance') fetchPerformance();
  }, [tab, selectedAgent]);

  return (
    <div className="min-h-screen bg-[#050816] text-zinc-200" style={{ fontFamily: 'system-ui, -apple-system, sans-serif' }}>
      {/* Header */}
      <header className="border-b border-zinc-800/50 px-8 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg border border-zinc-700 flex items-center justify-center">
            <span className="text-[#C0C8D0] text-sm font-bold">πX</span>
          </div>
          <h1 className="text-base font-semibold text-zinc-100">Agent Command Center</h1>
          <span className="text-xs text-zinc-500 ml-2">{agents.length} agents · {agents.filter(a => a.status === 'active').length} active</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchAgents}
            className="px-3 py-1.5 text-xs rounded-lg border border-zinc-800 text-zinc-400 hover:bg-zinc-900"
          >
            Refresh
          </button>
        </div>
      </header>

      <div className="flex" style={{ minHeight: 'calc(100vh - 65px)' }}>
        {/* Agent List Sidebar */}
        <aside className="w-72 border-r border-zinc-800/50 p-4 space-y-2 overflow-y-auto">
          <h2 className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-3">Active Agents</h2>
          {agents.length === 0 && (
            <div className="text-sm text-zinc-600 py-8 text-center">No agents created</div>
          )}
          {agents.map((agent) => (
            <button
              key={agent.agent_id}
              onClick={() => {
                setSelectedAgent(agent.agent_id);
                setMessages([]);
                setTab('conversation');
              }}
              className={`w-full text-left p-3 rounded-lg border transition-colors ${
                selectedAgent === agent.agent_id
                  ? 'border-zinc-700 bg-zinc-900/50'
                  : 'border-zinc-800/50 hover:border-zinc-700'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-zinc-200">{agent.label}</span>
                <div className={`w-2 h-2 rounded-full ${STATUS_DOT[agent.status] || 'bg-zinc-600'}`} />
              </div>
              <div className="text-xs text-zinc-500 mt-1 truncate">{agent.purpose}</div>
              <div className="flex items-center gap-3 mt-2 text-xs text-zinc-600">
                <span>{agent.conversations} chats</span>
                <span>{agent.decisions} decisions</span>
                <span className={STATUS_COLORS[agent.status] || 'text-zinc-600'}>{agent.status}</span>
              </div>
            </button>
          ))}
        </aside>

        {/* Main Panel */}
        <main className="flex-1 flex flex-col">
          {selectedAgent ? (
            <>
              {/* Tab Bar */}
              <div className="border-b border-zinc-800/50 px-8 py-2 flex gap-1">
                {(['conversation', 'tasks', 'memory', 'performance'] as const).map((t) => (
                  <button
                    key={t}
                    onClick={() => setTab(t)}
                    className={`px-4 py-2 text-sm rounded-t-lg transition-colors ${
                      tab === t
                        ? 'text-[#C0C8D0] border-b-2 border-[#C0C8D0]'
                        : 'text-zinc-500 hover:text-zinc-300'
                    }`}
                  >
                    {t.charAt(0).toUpperCase() + t.slice(1)}
                  </button>
                ))}
              </div>

              {/* Conversation Tab */}
              {tab === 'conversation' && (
                <div className="flex-1 flex flex-col">
                  <div className="flex-1 overflow-y-auto p-8 space-y-4">
                    {messages.length === 0 && (
                      <div className="text-center text-zinc-600 py-16">
                        Send a query to the selected agent.
                      </div>
                    )}
                    {messages.map((msg, i) => (
                      <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                        <div
                          className={`max-w-2xl rounded-lg px-4 py-3 ${
                            msg.role === 'user'
                              ? 'bg-zinc-900 text-zinc-200'
                              : 'bg-zinc-900/50 border border-zinc-800 text-zinc-300'
                          }`}
                        >
                          <div className="text-xs text-zinc-600 mb-1">{msg.role === 'user' ? 'You' : 'Agent'}</div>
                          <div className="text-sm whitespace-pre-wrap">{msg.content}</div>
                        </div>
                      </div>
                    ))}
                    {loading && (
                      <div className="text-center text-zinc-600 text-sm animate-pulse">Agent is thinking…</div>
                    )}
                  </div>
                  <div className="border-t border-zinc-800/50 p-4 flex gap-2">
                    <input
                      type="text"
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && !loading && executeQuery()}
                      placeholder="Ask the agent…"
                      className="flex-1 bg-zinc-900 border border-zinc-800 rounded-lg px-4 py-2 text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-zinc-700"
                    />
                    <button
                      onClick={executeQuery}
                      disabled={loading || !query.trim()}
                      className="px-4 py-2 text-sm rounded-lg bg-zinc-800 text-[#C0C8D0] hover:bg-zinc-700 disabled:opacity-40"
                    >
                      Send
                    </button>
                  </div>
                </div>
              )}

              {/* Tasks Tab */}
              {tab === 'tasks' && (
                <div className="flex-1 overflow-y-auto p-8 space-y-3">
                  {tasks.length === 0 && <div className="text-center text-zinc-600 py-16">No tasks yet.</div>}
                  {tasks.map((task) => (
                    <div key={task.id} className="rounded-lg border border-zinc-800 p-4 bg-zinc-900/30">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-zinc-200">{task.agent_label}</span>
                        <span className="text-xs text-zinc-500">{task.status}</span>
                      </div>
                      <div className="text-sm text-zinc-400 mb-2">{task.query}</div>
                      {task.confidence !== undefined && (
                        <div className="text-xs text-zinc-600">Confidence: {(task.confidence * 100).toFixed(0)}%</div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Memory Tab */}
              {tab === 'memory' && (
                <div className="flex-1 overflow-y-auto p-8 space-y-2">
                  {memory.length === 0 && <div className="text-center text-zinc-600 py-16">No memory entries.</div>}
                  {memory.map((m) => (
                    <div key={m.id} className="rounded-lg border border-zinc-800/50 p-3 bg-zinc-900/20">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs px-2 py-0.5 rounded bg-zinc-800 text-zinc-400">{m.memory_type}</span>
                        <span className="text-xs text-zinc-600">Importance: {(m.importance * 100).toFixed(0)}%</span>
                      </div>
                      <div className="text-sm text-zinc-300">{m.content}</div>
                    </div>
                  ))}
                </div>
              )}

              {/* Performance Tab */}
              {tab === 'performance' && (
                <div className="flex-1 overflow-y-auto p-8">
                  {performance ? (
                    <div className="space-y-4">
                      <div className="grid grid-cols-4 gap-4">
                        {[
                          { label: 'Conversations', value: performance.conversations || 0 },
                          { label: 'Decisions', value: performance.decisions || 0 },
                          { label: 'Performance', value: `${((performance.performance_score || 0) * 100).toFixed(0)}%` },
                          { label: 'Memory Items', value: performance.memory_stats?.total || 0 },
                        ].map((stat) => (
                          <div key={stat.label} className="rounded-lg border border-zinc-800 p-4 bg-zinc-900/30">
                            <div className="text-xs text-zinc-500">{stat.label}</div>
                            <div className="text-2xl font-semibold text-zinc-100 mt-1">{stat.value}</div>
                          </div>
                        ))}
                      </div>
                      {performance.evaluation && (
                        <div className="rounded-lg border border-zinc-800 p-4 bg-zinc-900/30">
                          <h3 className="text-sm font-medium text-zinc-200 mb-3">Evaluation Metrics</h3>
                          <div className="grid grid-cols-3 gap-4 text-sm">
                            <div>
                              <span className="text-zinc-500">Avg Score:</span>{' '}
                              <span className="text-zinc-200">{(performance.evaluation.avg_score * 100).toFixed(0)}%</span>
                            </div>
                            <div>
                              <span className="text-zinc-500">Avg Accuracy:</span>{' '}
                              <span className="text-zinc-200">{(performance.evaluation.avg_accuracy * 100).toFixed(0)}%</span>
                            </div>
                            <div>
                              <span className="text-zinc-500">Trend:</span>{' '}
                              <span className="text-[#C0C8D0]">{performance.evaluation.trend}</span>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="text-center text-zinc-600 py-16">Loading performance…</div>
                  )}
                </div>
              )}
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-zinc-600">
              Select an agent to begin
            </div>
          )}
        </main>
      </div>
    </div>
  );
};
