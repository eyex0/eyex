import { useState, useRef } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { BackendApi } from "@/services/backend-api.service";
import { AppShell } from "@/components/layout/AppShell";
import { Card, Badge } from "@/components/common/primitives";
import { toast } from "sonner";
import { Loader2, Upload, Brain, FileText, Lightbulb, Activity, ChevronRight } from "lucide-react";

type Step = { node: string; output?: string; status?: string; duration_ms?: number };

interface KnowledgeRecord {
  key?: string;
  value?: string;
}

interface IntelligenceDocument {
  name?: string;
  filename?: string;
  file_type?: string;
  created_at?: string;
  chunks?: number;
}

export function IntelligenceHubPage() {
  const [query, setQuery] = useState("");
  const [context, setContext] = useState("");
  const [sessionId, setSessionId] = useState("session-" + Date.now());
  const [result, setResult] = useState<string | null>(null);
  const [steps, setSteps] = useState<Step[]>([]);
  const [knowledgeKey, setKnowledgeKey] = useState("");
  const [knowledgeValue, setKnowledgeValue] = useState("");
  const [activeTab, setActiveTab] = useState<"analyze" | "knowledge" | "documents" | "reports">(
    "analyze",
  );

  const analyzeMutation = useMutation({
    mutationFn: async (data: { query: string; context?: string; session_id: string }) => {
      const formData = new FormData();
      formData.append("query", data.query);
      if (data.context) formData.append("context", data.context);
      formData.append("session_id", data.session_id);
      const resp = await fetch("http://eyex-api:8000/api/v1/intelligence/analyze", {
        method: "POST",
        body: formData,
      });
      if (!resp.ok) throw new Error(`Analysis failed: ${resp.status}`);
      return resp.json();
    },
    onSuccess: (data) => {
      setResult(data.output);
      setSteps(data.steps || []);
      setSessionId(data.session_id || sessionId);
      toast.success("Analysis complete");
    },
    onError: (err) => toast.error(err instanceof Error ? err.message : "Analysis failed"),
  });

  const knowledgeMutation = useMutation({
    mutationFn: (data: { key: string; value: string }) => {
      const formData = new FormData();
      formData.append("key", data.key);
      formData.append("value", data.value);
      formData.append("session_id", sessionId);
      return fetch("http://eyex-api:8000/api/v1/intelligence/knowledge", {
        method: "POST",
        body: formData,
      });
    },
    onSuccess: () => {
      toast.success("Knowledge stored");
      setKnowledgeKey("");
      setKnowledgeValue("");
    },
    onError: (err) => toast.error(err instanceof Error ? err.message : "Failed to store"),
  });

  const { data: knowledge } = useQuery<{ records?: KnowledgeRecord[] }>({
    queryKey: ["knowledge", sessionId],
    queryFn: () => BackendApi.getKnowledgeData(sessionId) as Promise<{ records?: KnowledgeRecord[] }>,
    enabled: activeTab === "knowledge",
  });

  const { data: documents } = useQuery<{ documents?: IntelligenceDocument[] }>({
    queryKey: ["documents", sessionId],
    queryFn: () => BackendApi.listDocuments(sessionId) as Promise<{ documents?: IntelligenceDocument[] }>,
    enabled: activeTab === "documents",
  });

  const handleAnalyze = () => {
    if (!query.trim()) return;
    analyzeMutation.mutate({ query, context, session_id: sessionId });
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);
    formData.append("session_id", sessionId);
    try {
      const resp = await fetch("http://eyex-api:8000/api/v1/intelligence/documents/upload", {
        method: "POST",
        body: formData,
      });
      if (resp.ok) toast.success(`Uploaded ${file.name}`);
      else toast.error("Upload failed");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Upload failed");
    }
  };

  const isAnalyzing = analyzeMutation.isPending;

  return (
    <AppShell title="Intelligence Hub" subtitle="AI-powered business decision intelligence">
      {/* Tab Navigation */}
      <div className="flex gap-1 border-b border-border mb-6">
        {(
          [
            { key: "analyze", label: "Analyze", icon: Brain },
            { key: "knowledge", label: "Knowledge", icon: Lightbulb },
            { key: "documents", label: "Documents", icon: FileText },
            { key: "reports", label: "Reports", icon: Activity },
          ] as const
        ).map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`flex items-center gap-2 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors ${
              activeTab === key
                ? "text-white border-white"
                : "text-muted-foreground border-transparent hover:text-white"
            }`}
          >
            <Icon size={14} /> {label}
          </button>
        ))}
      </div>

      {/* Analyze Tab */}
      {activeTab === "analyze" && (
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          <div className="lg:col-span-2 space-y-4">
            <Card title="Business Query">
              <div className="p-5 space-y-4">
                <textarea
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="e.g., Analyze our revenue decline and recommend actions..."
                  className="w-full h-32 bg-background border border-border rounded-md px-4 py-3 text-sm text-white font-mono resize-none outline-none focus:border-white/40"
                />
                <textarea
                  value={context}
                  onChange={(e) => setContext(e.target.value)}
                  placeholder="Optional company context (revenue, metrics, challenges)..."
                  className="w-full h-24 bg-background border border-border rounded-md px-4 py-3 text-sm text-white font-mono resize-none outline-none focus:border-white/40"
                />
                <button
                  onClick={handleAnalyze}
                  disabled={isAnalyzing || !query.trim()}
                  className="w-full bg-white text-black text-xs font-bold uppercase tracking-widest py-3 rounded-md flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  {isAnalyzing ? (
                    <Loader2 className="animate-spin" size={14} />
                  ) : (
                    <Brain size={14} />
                  )}
                  {isAnalyzing ? "Analyzing..." : "Run Intelligence Analysis"}
                </button>
              </div>
            </Card>

            {/* Agent Activity */}
            {steps.length > 0 && (
              <Card title="Agent Activity">
                <div className="divide-y divide-border">
                  {steps.map((step, i) => (
                    <div key={i} className="px-5 py-3 flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2">
                        <div
                          className={`w-2 h-2 rounded-sm ${step.status === "completed" ? "bg-emerald-400" : "bg-amber-400"}`}
                        />
                        <span className="text-white font-medium capitalize">{step.node}</span>
                      </div>
                      <span className="text-muted-foreground font-mono">
                        {step.duration_ms ? `${Math.round(step.duration_ms)}ms` : ""}
                      </span>
                    </div>
                  ))}
                </div>
              </Card>
            )}
          </div>

          {/* Results */}
          <div className="lg:col-span-3">
            <Card title={result ? "Intelligence Report" : "AI Analysis Output"}>
              {isAnalyzing ? (
                <div className="p-12 flex flex-col items-center justify-center gap-3">
                  <Loader2 className="animate-spin text-white" size={32} />
                  <p className="text-sm text-muted-foreground">
                    Running Analyst → Strategist → Decision pipeline...
                  </p>
                </div>
              ) : result ? (
                <div className="p-6">
                  <div className="prose prose-invert max-w-none text-sm whitespace-pre-wrap font-mono text-muted-foreground leading-relaxed">
                    {result}
                  </div>
                </div>
              ) : (
                <div className="p-12 text-center text-muted-foreground text-sm">
                  <Brain size={40} className="mx-auto mb-3 opacity-30" />
                  <p>Enter a business question above to run the full intelligence pipeline</p>
                  <p className="text-[10px] mt-2 font-mono">Analyst → Strategist → Decision</p>
                </div>
              )}
            </Card>
          </div>
        </div>
      )}

      {/* Knowledge Tab */}
      {activeTab === "knowledge" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card title="Store Company Knowledge">
            <div className="p-5 space-y-4">
              <input
                value={knowledgeKey}
                onChange={(e) => setKnowledgeKey(e.target.value)}
                placeholder="e.g., annual_revenue_2024"
                className="w-full bg-background border border-border rounded-md px-4 py-2.5 text-sm text-white outline-none focus:border-white/40"
              />
              <textarea
                value={knowledgeValue}
                onChange={(e) => setKnowledgeValue(e.target.value)}
                placeholder="e.g., $12.5M revenue, 23% growth YoY..."
                className="w-full h-24 bg-background border border-border rounded-md px-4 py-3 text-sm text-white font-mono resize-none outline-none focus:border-white/40"
              />
              <button
                onClick={() =>
                  knowledgeMutation.mutate({ key: knowledgeKey, value: knowledgeValue })
                }
                disabled={!knowledgeKey || !knowledgeValue}
                className="bg-white text-black text-xs font-bold uppercase tracking-widest px-4 py-2 rounded-md disabled:opacity-50"
              >
                Store Knowledge
              </button>
            </div>
          </Card>
          <Card title="Stored Knowledge">
            {knowledge?.records && knowledge.records.length > 0 ? (
              <div className="divide-y divide-border">
                {knowledge.records.map((r: KnowledgeRecord, i: number) => (
                  <div key={i} className="px-5 py-3">
                    <div className="text-xs font-mono text-primary-brand">
                      {r.key?.replace("knowledge:", "")}
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      {r.value?.slice(0, 200)}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-8 text-center text-muted-foreground text-sm">
                No knowledge stored yet
              </div>
            )}
          </Card>
        </div>
      )}

      {/* Documents Tab */}
      {activeTab === "documents" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card title="Upload Document">
            <div className="p-5">
              <label className="flex flex-col items-center justify-center border-2 border-dashed border-border rounded-lg p-8 cursor-pointer hover:border-white/30 transition-colors">
                <Upload size={32} className="text-muted-foreground mb-2" />
                <span className="text-sm text-muted-foreground">
                  Upload company data (CSV, TXT, JSON)
                </span>
                <span className="text-[10px] font-mono text-muted-foreground mt-1">
                  Documents are chunked and stored in company memory
                </span>
                <input
                  type="file"
                  className="hidden"
                  accept=".csv,.txt,.json,.md"
                  onChange={handleFileUpload}
                />
              </label>
            </div>
          </Card>
          <Card title="Uploaded Documents">
            {documents?.documents && documents.documents.length > 0 ? (
              <div className="divide-y divide-border">
                {documents.documents.map((d: IntelligenceDocument, i: number) => (
                  <div key={i} className="px-5 py-3 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <FileText size={14} className="text-muted-foreground" />
                      <span className="text-xs text-white">{d.filename ?? d.name ?? "Document"}</span>
                    </div>
                    <Badge tone="neutral">{d.chunks ?? 0} chunks</Badge>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-8 text-center text-muted-foreground text-sm">
                No documents uploaded
              </div>
            )}
          </Card>
        </div>
      )}

      {/* Reports Tab */}
      {activeTab === "reports" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card title="Analysis History">
            {result ? (
              <div className="p-5">
                <div className="flex items-center justify-between border-b border-border pb-3 mb-3">
                  <div className="flex items-center gap-2">
                    <Activity size={14} className="text-emerald-400" />
                    <span className="text-xs text-white font-medium">
                      Session: {sessionId.slice(0, 16)}...
                    </span>
                  </div>
                  <Badge tone="success">Completed</Badge>
                </div>
                <div className="text-xs text-muted-foreground max-h-60 overflow-y-auto whitespace-pre-wrap">
                  {result.slice(0, 1000)}...
                </div>
              </div>
            ) : (
              <div className="p-8 text-center text-muted-foreground text-sm">
                Run an analysis to see reports here
              </div>
            )}
          </Card>
          <Card title="Pipeline Summary">
            <div className="p-5 space-y-3 text-xs">
              <div className="flex justify-between border-b border-border pb-2">
                <span className="text-muted-foreground">Pipeline</span>
                <span className="text-white">Analyst → Strategist → Decision</span>
              </div>
              <div className="flex justify-between border-b border-border pb-2">
                <span className="text-muted-foreground">Agents</span>
                <span className="text-white">13 total (8 engineering + 3 BI + 2 routing)</span>
              </div>
              <div className="flex justify-between border-b border-border pb-2">
                <span className="text-muted-foreground">Memory Layers</span>
                <span className="text-white">
                  5 (conversation, long-term, agent, short-term, vector)
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Knowledge Entries</span>
                <span className="text-white">{knowledge?.records?.length ?? 0}</span>
              </div>
            </div>
          </Card>
        </div>
      )}
    </AppShell>
  );
}
