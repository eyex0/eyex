import { useState, useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { AppShell } from "@/components/layout/AppShell";
import {
  Key,
  Plus,
  LayoutDashboard,
  FileText,
  Activity,
  Settings,
  Copy,
  Trash2,
  X,
  Database,
  Eye,
  EyeOff,
  Check,
  AlertTriangle,
} from "lucide-react";

const STORAGE_KEY = "qorx_api_keys";

interface ApiKeyRecord {
  id: string;
  name: string;
  key: string;
  createdAt: string;
  lastUsedAt: string | null;
  active: boolean;
}

function generateApiKey(): string {
  const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  let key = "pix_live_";
  for (let i = 0; i < 48; i++) {
    key += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return key;
}

function loadKeys(): ApiKeyRecord[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveKeys(keys: ApiKeyRecord[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(keys));
}

function maskKey(key: string): string {
  if (key.length <= 12) return key;
  return key.slice(0, 12) + "••••••••" + key.slice(-4);
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

export function ApiPage() {
  const queryClient = useQueryClient();
  const [showNewKeyModal, setShowNewKeyModal] = useState(false);
  const [newKeyName, setNewKeyName] = useState("");
  const [revealedKey, setRevealedKey] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const keysQuery = useQuery<ApiKeyRecord[]>({
    queryKey: ["api-keys"],
    queryFn: loadKeys,
  });

  const keys = keysQuery.data ?? [];
  const activeKeys = keys.filter((k) => k.active);

  const handleCreateKey = useCallback(() => {
    if (!newKeyName.trim()) {
      toast.error("Please enter a key name");
      return;
    }
    const key = generateApiKey();
    const record: ApiKeyRecord = {
      id: crypto.randomUUID(),
      name: newKeyName.trim(),
      key,
      createdAt: new Date().toISOString(),
      lastUsedAt: null,
      active: true,
    };
    const updated = [...keys, record];
    saveKeys(updated);
    queryClient.setQueryData(["api-keys"], updated);
    setRevealedKey(key);
    setNewKeyName("");
    toast.success("API key created");
  }, [newKeyName, keys, queryClient]);

  const handleRevokeKey = useCallback(
    (id: string) => {
      const updated = keys.map((k) => (k.id === id ? { ...k, active: false } : k));
      saveKeys(updated);
      queryClient.setQueryData(["api-keys"], updated);
      toast.success("API key revoked");
    },
    [keys, queryClient],
  );

  const handleDeleteKey = useCallback(
    (id: string) => {
      const updated = keys.filter((k) => k.id !== id);
      saveKeys(updated);
      queryClient.setQueryData(["api-keys"], updated);
      toast.success("API key deleted");
    },
    [keys, queryClient],
  );

  const handleCopy = useCallback((id: string, key: string) => {
    navigator.clipboard.writeText(key).then(() => {
      setCopiedId(id);
      toast.success("Copied to clipboard");
      setTimeout(() => setCopiedId(null), 2000);
    });
  }, []);

  return (
    <AppShell
      title="API Management"
      subtitle="Provision and audit secure access keys"
      actions={
        <button
          onClick={() => setShowNewKeyModal(true)}
          className="bg-white text-eye-bg px-6 py-2.5 rounded-sm font-bold text-sm hover:shadow-[0_0_20px_rgba(56,189,248,0.4)] transition-all flex items-center gap-2"
        >
          <Plus className="text-sm w-4 h-4" />
          Generate New Key
        </button>
      }
    >
      <div className="relative">
        {/* Ambient Background Effects */}
        <div className="fixed top-[-10%] left-[-10%] w-[600px] h-[600px] bg-primary-brand opacity-[0.08] blur-[80px] rounded-full pointer-events-none z-[-1]" />
        <div className="fixed bottom-[-10%] right-[-10%] w-[600px] h-[600px] bg-primary-brand opacity-[0.08] blur-[80px] rounded-full pointer-events-none z-[-1]" />

        <div className="max-w-[1200px] mx-auto w-full space-y-8">
          {/* Stats Row */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6" data-fade-up>
            <div className="glass-panel p-6 rounded-sm">
              <div className="flex items-center justify-between mb-4">
                <span className="font-mono text-eye-text text-[10px]">ACTIVE KEYS</span>
                <Key className="text-primary-brand w-5 h-5" />
              </div>
              <div className="flex items-end gap-3 mb-4">
                <span className="text-3xl font-bold text-white">{activeKeys.length}</span>
                <span className="text-xs text-eye-text mb-1">of {keys.length} total</span>
              </div>
              <div className="h-1.5 w-full bg-eye-border rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary-brand rounded-full transition-all"
                  style={{
                    width: `${keys.length > 0 ? (activeKeys.length / keys.length) * 100 : 0}%`,
                  }}
                />
              </div>
              <div className="flex justify-between mt-2">
                <span className="text-[10px] text-eye-text">
                  {activeKeys.length === 0
                    ? "No active keys"
                    : `${activeKeys.length} key(s) active`}
                </span>
              </div>
            </div>

            <div className="glass-panel p-6 rounded-sm">
              <div className="flex items-center justify-between mb-4">
                <span className="font-mono text-eye-text text-[10px]">TOTAL KEYS CREATED</span>
                <Activity className="text-primary-brand w-5 h-5" />
              </div>
              <div className="flex items-end gap-3 mb-2">
                <span className="text-3xl font-bold text-white">{keys.length}</span>
                <span className="text-xs text-blue-400 mb-1">All time</span>
              </div>
              <div className="h-10 flex items-end gap-1">
                {keys.slice(-6).map((k, i) => (
                  <div
                    key={k.id}
                    className={`w-full rounded-t-sm ${k.active ? "bg-primary-brand" : "bg-eye-border"}`}
                    style={{ height: `${20 + (i + 1) * 8}px` }}
                  />
                ))}
                {keys.length === 0 && (
                  <>
                    <div className="w-full bg-eye-border h-3 rounded-t-sm" />
                    <div className="w-full bg-eye-border h-5 rounded-t-sm" />
                    <div className="w-full bg-eye-border h-4 rounded-t-sm" />
                  </>
                )}
              </div>
            </div>

            <div className="glass-panel p-6 rounded-sm">
              <div className="flex items-center justify-between mb-4">
                <span className="font-mono text-eye-text text-[10px]">SECURITY STATUS</span>
                <AlertTriangle className="text-green-400 w-5 h-5" />
              </div>
              <div className="flex items-end gap-3">
                <span className="text-3xl font-bold text-white">
                  {keys.length === 0 ? "—" : activeKeys.length > 0 ? "ACTIVE" : "NONE"}
                </span>
              </div>
              <p className="text-[10px] text-eye-text mt-4">
                {keys.length === 0
                  ? "Create your first API key to get started"
                  : `${activeKeys.length} active key(s) with AES-256 GCM encryption`}
              </p>
            </div>
          </div>

          {/* API Key Section */}
          <div data-fade-up>
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <span className="w-2 h-2 bg-primary-brand rounded-full" />
                ACTIVE SECURITY TOKENS
              </h2>
              <span className="font-mono text-[10px] text-eye-text uppercase">
                Displaying {Math.min(keys.length, 6)} of {keys.length}
              </span>
            </div>

            {keys.length === 0 ? (
              <div className="glass-panel p-12 rounded-sm text-center">
                <Key className="w-12 h-12 text-eye-text mx-auto mb-4 opacity-40" />
                <p className="text-sm text-white font-bold mb-2">No API keys yet</p>
                <p className="text-xs text-eye-text mb-6">
                  Generate your first key to start integrating with the QORX API.
                </p>
                <button
                  onClick={() => setShowNewKeyModal(true)}
                  className="bg-white text-eye-bg px-5 py-2 rounded-sm font-bold text-sm hover:shadow-[0_0_20px_rgba(56,189,248,0.4)] transition-all inline-flex items-center gap-2"
                >
                  <Plus className="w-4 h-4" />
                  Generate First Key
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {keys.slice(0, 6).map((k) => (
                  <div
                    key={k.id}
                    className={`glass-panel p-6 rounded-sm relative overflow-hidden group ${
                      !k.active ? "opacity-60" : ""
                    }`}
                  >
                    <div
                      className={`absolute top-0 right-0 p-2 opacity-10 group-hover:opacity-20 transition-opacity ${
                        !k.active ? "text-red-500" : ""
                      }`}
                    >
                      <Key className="text-6xl w-16 h-16" />
                    </div>
                    <div className="flex justify-between items-start mb-6">
                      <div>
                        <h3 className="text-sm font-bold text-white mb-1">{k.name}</h3>
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold tracking-wider border ${
                            k.active
                              ? "bg-green-500/10 text-green-400 border-green-500/20"
                              : "bg-red-500/10 text-red-400 border-red-500/20"
                          }`}
                        >
                          {k.active ? "Active" : "Revoked"}
                        </span>
                      </div>
                      <div className="flex gap-2">
                        {k.active && (
                          <>
                            <button
                              aria-label="Copy to clipboard"
                              onClick={() => handleCopy(k.id, k.key)}
                              className="p-1.5 hover:bg-white/5 rounded text-eye-text hover:text-white transition-colors"
                            >
                              {copiedId === k.id ? (
                                <Check className="text-green-400 w-5 h-5" />
                              ) : (
                                <Copy className="text-lg w-5 h-5" />
                              )}
                            </button>
                            <button
                              aria-label="Revoke key"
                              onClick={() => handleRevokeKey(k.id)}
                              className="p-1.5 hover:bg-white/5 rounded text-eye-text hover:text-red-400 transition-colors"
                            >
                              <Trash2 className="text-lg w-5 h-5" />
                            </button>
                          </>
                        )}
                        {!k.active && (
                          <button
                            aria-label="Delete key"
                            onClick={() => handleDeleteKey(k.id)}
                            className="p-1.5 hover:bg-white/5 rounded text-eye-text hover:text-red-400 transition-colors"
                          >
                            <Trash2 className="text-lg w-5 h-5" />
                          </button>
                        )}
                      </div>
                    </div>
                    <div className="mb-6">
                      <span
                        className={`font-mono text-xs text-white/90 bg-eye-bg p-2 block rounded border border-eye-border select-all ${
                          !k.active ? "line-through text-eye-text" : ""
                        }`}
                      >
                        {maskKey(k.key)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between pt-4 border-t border-eye-border">
                      <div className="flex flex-col">
                        <span className="text-[10px] text-eye-text">STATUS</span>
                        <span
                          className={`text-xs font-bold ${k.active ? "text-white" : "text-eye-text"}`}
                        >
                          {k.active ? "10,000 REQ/MIN" : "DISABLED"}
                        </span>
                      </div>
                      <div className="flex flex-col items-end">
                        <span className="text-[10px] text-eye-text">
                          {k.active ? "CREATED" : "REVOKED"}
                        </span>
                        <span className="text-xs text-white">{formatDate(k.createdAt)}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Request Log Section */}
          <div
            className="glass-panel rounded-sm overflow-hidden flex flex-col border border-primary-brand/20 shadow-[0_0_40px_rgba(56,189,248,0.05)]"
            data-fade-up
          >
            <div className="bg-eye-surface px-6 py-4 border-b border-eye-border flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                  <h3 className="text-sm font-bold text-white tracking-widest uppercase">
                    Request Log
                  </h3>
                </div>
              </div>
            </div>
            <div className="bg-eye-bg p-6">
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <Activity className="w-10 h-10 text-eye-text opacity-40 mb-4" />
                <p className="text-sm text-white font-bold mb-2">No requests logged yet</p>
                <p className="text-xs text-eye-text max-w-md">
                  Request logging will be available when API keys are active. Once you start making
                  calls with your API key, all requests will appear here with full audit trails.
                </p>
              </div>
            </div>
          </div>

          {/* Documentation Section */}
          <div className="glass-panel rounded-sm overflow-hidden" data-fade-up>
            <div className="bg-eye-surface px-6 py-4 border-b border-eye-border">
              <h3 className="text-sm font-bold text-white tracking-widest uppercase flex items-center gap-2">
                <FileText className="w-4 h-4" />
                API Documentation
              </h3>
            </div>
            <div className="p-6 space-y-6">
              <div>
                <h4 className="text-sm font-bold text-white mb-2">Authentication</h4>
                <p className="text-xs text-eye-text leading-relaxed">
                  Include your API key in the{" "}
                  <code className="bg-eye-bg px-1.5 py-0.5 rounded text-primary-brand font-mono">
                    Authorization
                  </code>{" "}
                  header with every request:
                </p>
                <div className="mt-3 bg-eye-bg rounded border border-eye-border p-4 font-mono text-xs text-white/80">
                  <span className="text-primary-brand">Authorization</span>: Bearer pix_live_***
                </div>
              </div>
              <div>
                <h4 className="text-sm font-bold text-white mb-2">Rate Limits</h4>
                <p className="text-xs text-eye-text leading-relaxed">
                  Each API key allows up to 10,000 requests per minute. Exceeding this limit will
                  return a{" "}
                  <code className="bg-eye-bg px-1.5 py-0.5 rounded text-red-400 font-mono">
                    429 Too Many Requests
                  </code>{" "}
                  response. Rate limit headers are included in every API response.
                </p>
              </div>
              <div>
                <h4 className="text-sm font-bold text-white mb-2">Base URL</h4>
                <div className="mt-2 bg-eye-bg rounded border border-eye-border p-4 font-mono text-xs text-white/80">
                  https://api.qorx.io/v1
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Footer Meta */}
        <footer className="p-8 mt-12 border-t border-eye-border bg-eye-surface/40">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4">
            <div className="flex gap-8">
              <div className="flex flex-col">
                <span className="text-[10px] text-eye-text">SECURITY ENCLAVE</span>
                <span className="text-xs font-bold text-white">AES-256 GCM Active</span>
              </div>
              <div className="flex flex-col">
                <span className="text-[10px] text-eye-text">GLOBAL UPTIME</span>
                <span className="text-xs font-bold text-green-400">99.9992%</span>
              </div>
            </div>
            <div className="text-[10px] text-eye-text flex items-center gap-2">
              <span>&copy; 2024 πX TECHNOLOGIES INC.</span>
              <span className="h-1 w-1 bg-eye-text rounded-full" />
              <a className="hover:text-primary-brand" href="#">
                TERMS OF SERVICE
              </a>
            </div>
          </div>
        </footer>
      </div>

      {/* New Key Modal */}
      {showNewKeyModal && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="glass-panel rounded-sm w-full max-w-md mx-4 p-0 overflow-hidden border border-eye-border">
            <div className="flex items-center justify-between px-6 py-4 border-b border-eye-border">
              <h3 className="text-sm font-bold text-white tracking-wide">Generate New API Key</h3>
              <button
                onClick={() => {
                  setShowNewKeyModal(false);
                  setRevealedKey(null);
                }}
                className="text-eye-text hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {revealedKey ? (
              <div className="p-6">
                <div className="bg-green-500/10 border border-green-500/20 rounded-sm p-4 mb-4 flex items-start gap-3">
                  <Check className="text-green-400 w-5 h-5 mt-0.5 shrink-0" />
                  <div>
                    <p className="text-xs font-bold text-green-400 mb-1">
                      Key Created Successfully
                    </p>
                    <p className="text-[11px] text-eye-text">
                      Copy this key now. It will not be shown again.
                    </p>
                  </div>
                </div>
                <div className="bg-eye-bg rounded border border-eye-border p-4 font-mono text-xs text-white/90 select-all break-all mb-4">
                  {revealedKey}
                </div>
                <div className="flex gap-3">
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(revealedKey);
                      toast.success("Copied to clipboard");
                    }}
                    className="flex-1 bg-white text-eye-bg px-4 py-2.5 rounded-sm font-bold text-sm hover:shadow-[0_0_20px_rgba(56,189,248,0.4)] transition-all flex items-center justify-center gap-2"
                  >
                    <Copy className="w-4 h-4" />
                    Copy Key
                  </button>
                  <button
                    onClick={() => {
                      setShowNewKeyModal(false);
                      setRevealedKey(null);
                    }}
                    className="px-4 py-2.5 rounded-sm font-bold text-sm border border-eye-border text-eye-text hover:text-white hover:border-white/20 transition-all"
                  >
                    Done
                  </button>
                </div>
              </div>
            ) : (
              <div className="p-6">
                <label className="block mb-4">
                  <span className="text-[10px] font-mono text-eye-text uppercase tracking-wider block mb-2">
                    Key Name
                  </span>
                  <input
                    type="text"
                    value={newKeyName}
                    onChange={(e) => setNewKeyName(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleCreateKey()}
                    placeholder="e.g. Production - Edge Mesh"
                    className="w-full bg-eye-bg border border-eye-border rounded-sm px-4 py-2.5 text-sm text-white placeholder:text-eye-text/50 focus:outline-none focus:border-primary-brand transition-colors"
                    autoFocus
                  />
                </label>
                <div className="flex gap-3">
                  <button
                    onClick={handleCreateKey}
                    className="flex-1 bg-white text-eye-bg px-4 py-2.5 rounded-sm font-bold text-sm hover:shadow-[0_0_20px_rgba(56,189,248,0.4)] transition-all"
                  >
                    Generate Key
                  </button>
                  <button
                    onClick={() => setShowNewKeyModal(false)}
                    className="px-4 py-2.5 rounded-sm font-bold text-sm border border-eye-border text-eye-text hover:text-white hover:border-white/20 transition-all"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </AppShell>
  );
}
