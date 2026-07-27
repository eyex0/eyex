import { useState, useRef, useEffect } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { AgentService } from "@/services/agent-unified.service";
import { BackendApi } from "@/services/backend-api.service";
import {
  Send,
  Plus,
  Search,
  User,
  Settings,
  Shield,
  Share,
  Paperclip,
  FileText,
  History,
  Trash2,
  Copy,
  Terminal,
} from "lucide-react";

interface ChatMessage {
  role: "user" | "assistant";
  text: string;
  timestamp: string;
  source?: "python-backend" | "node-orchestrator";
}

interface ChatThread {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export function AiChatPage() {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [currentThreadId, setCurrentThreadId] = useState<string | null>(null);
  const [threadTitle, setThreadTitle] = useState("");
  const [ragContexts, setRagContexts] = useState<Array<{key: string, value: string}>>([]);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    toast.info(`Chunking and vectorizing ${file.name}...`);
    // Simulating RAG document chunking to vector memory
    setTimeout(() => {
      setRagContexts(prev => [...prev, { key: file.name, value: `Vectorized contents of ${file.name} (14 chunks)` }]);
      toast.success(`${file.name} added to vector memory`);
    }, 1500);
  };

  // Fetch chat threads
  const { data: threads = [], isLoading: threadsLoading } = useQuery({
    queryKey: ["chat_threads"],
    queryFn: async () => {
      try {
        const conversations = await BackendApi.getConversation(currentThreadId || "default");
        // Convert to thread format
        return [{
          id: currentThreadId || "default",
          title: threadTitle || "New Analysis",
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          message_count: messages.length,
        }];
      } catch (error) {
        console.error("Failed to fetch threads:", error);
        return [];
      }
    },
  });

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const chatMutation = useMutation({
    mutationFn: async ({
      message,
      history,
      threadId,
    }: {
      message: string;
      history: { role: string; text: string }[];
      threadId?: string;
    }) => {
      // Generate thread ID if this is a new conversation
      const effectiveThreadId = threadId || `thread_${Date.now()}`;
      if (!currentThreadId) {
        setCurrentThreadId(effectiveThreadId);
        // Generate a title from the first message
        setThreadTitle(message.substring(0, 50) + (message.length > 50 ? "..." : ""));
      }

      // Store important information in long-term memory
      try {
        // Extract key entities and facts from the conversation
        const entities = extractEntities(message);
        if (entities.length > 0) {
          await BackendApi.storeLongTermMemory(
            effectiveThreadId,
            "entities",
            JSON.stringify(entities)
          );
        }
      } catch (error) {
        console.error("Failed to store in long-term memory:", error);
      }

      return AgentService.chat(message, history);
    },
    onSuccess: (result) => {
      if (result.text) {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            text: result.text,
            timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            source: result.source,
          },
        ]);
        if (result.steps.length > 0) {
          const agents = [...new Set(result.steps.map((s) => s.agent))].join(", ");
          console.debug(
            `[${result.source}] Agents used: ${agents} in ${result.steps.length} steps`,
          );
        }
      } else {
        toast.error("Failed to get response");
      }
    },
    onError: (error: Error) => {
      toast.error(error.message || "Connection failed. Please try again.");
    },
  });

  const extractEntities = (text: string): string[] => {
    // Simple entity extraction - in production, use NLP
    const entities: string[] = [];
    const patterns = [
      /[A-Z][a-z]+ [A-Z][a-z]+/g, // Proper names
      /\b[A-Z]{2,}\b/g, // Acronyms
      /\$\d+[\d,]*/g, // Money
      /\d+%/g, // Percentages
    ];
    
    patterns.forEach(pattern => {
      const matches = text.match(pattern);
      if (matches) {
        entities.push(...matches);
      }
    });
    
    return [...new Set(entities)];
  };

  const startNewThread = () => {
    setMessages([]);
    setMessage("");
    setCurrentThreadId(null);
    setThreadTitle("");
    setRagContexts([]);
  };

  const loadThread = async (threadId: string) => {
    try {
      const conversation = await BackendApi.getConversation(threadId) as { messages: Array<{ role: string; content: string; created_at: string }> };
      const loadedMessages: ChatMessage[] = conversation.messages.map((msg) => ({
        role: msg.role as "user" | "assistant",
        text: msg.content,
        timestamp: new Date(msg.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        source: "python-backend",
      }));
      
      setMessages(loadedMessages);
      setCurrentThreadId(threadId);
      setThreadTitle(loadedMessages[0]?.text.substring(0, 50) + "..." || "Thread");

      // Load RAG context for this thread
      try {
        const memorySummary = await BackendApi.getMemorySummary(threadId);
        if (memorySummary.long_term && Object.keys(memorySummary.long_term).length > 0) {
          const contexts = Object.entries(memorySummary.long_term).map(([k, v]) => ({ key: k, value: v as string }));
          setRagContexts(contexts);
        } else {
          setRagContexts([]);
        }
      } catch (memoryError) {
        console.error("Failed to load RAG context:", memoryError);
        setRagContexts([]);
      }
    } catch (error) {
      toast.error("Failed to load thread");
      console.error(error);
    }
  };

  const deleteThread = async (threadId: string) => {
    try {
      await BackendApi.deleteConversation(threadId);
      toast.success("Thread deleted");
      if (currentThreadId === threadId) {
        startNewThread();
      }
    } catch (error) {
      toast.error("Failed to delete thread");
      console.error(error);
    }
  };

  const handleSend = () => {
    const trimmed = message.trim();
    if (!trimmed || chatMutation.isPending) return;

    const now = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    const userMsg: ChatMessage = { role: "user", text: trimmed, timestamp: now };
    const newMessages = [...messages, userMsg];
    setMessages(newMessages);

    chatMutation.mutate({
      message: trimmed,
      history: messages.map((m) => ({ role: m.role, text: m.text })),
      threadId: currentThreadId || undefined,
    });

    setMessage("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success("Copied to clipboard");
  };

  return (
    <div className="h-screen flex text-eye-white overflow-hidden relative">
      {/* Ambient Background Glow */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-primary-brand/10 blur-[120px] rounded-full" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[30%] h-[30%] bg-primary-brand/5 blur-[100px] rounded-full" />
      </div>

      {/* Sidebar */}
      <aside className="w-[280px] h-screen bg-eye-surface border-r border-eye-border flex flex-col z-20 relative">
        <div className="p-6 flex items-center gap-3">
          <div className="w-8 h-8 bg-primary-brand rounded-sm flex items-center justify-center">
            <Terminal className="text-eye-bg text-xl w-5 h-5" />
          </div>
          <div>
            <h1 className="text-[18px] font-bold tracking-tight text-white">QORX</h1>
            <p className="text-[10px] text-eye-text uppercase tracking-[0.2em] font-mono">
              Analytic Core
            </p>
          </div>
        </div>
        <div className="px-4 mb-6">
          <button
            onClick={startNewThread}
            className="w-full py-3 px-4 bg-white hover:shadow-[0_0_20px_rgba(56,189,248,0.3)] transition-all duration-300 rounded flex items-center justify-center gap-2 text-background font-bold text-sm"
          >
            <Plus className="text-lg w-5 h-5" />
            New Analysis
          </button>
        </div>
        <div className="px-4 mb-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-eye-text text-sm w-4 h-4" />
            <input
              className="w-full bg-eye-bg border border-eye-border rounded py-2 pl-10 pr-4 text-xs font-mono focus:border-primary-brand outline-none transition-colors"
              placeholder="Search threads..."
              type="text"
            />
          </div>
        </div>
        <nav className="flex-1 overflow-y-auto px-2 space-y-1">
          <div className="px-4 py-2">
            <span className="text-[10px] text-eye-text/50 uppercase tracking-widest font-mono">
              Recent Threads
            </span>
          </div>
          
          {threadsLoading ? (
            <div className="px-4 py-3 text-xs text-muted-foreground">Loading threads...</div>
          ) : threads.length === 0 ? (
            <div className="px-4 py-3 text-xs text-muted-foreground">No conversations yet</div>
          ) : (
            threads.map((thread) => (
              <div
                key={thread.id}
                className={`flex flex-col p-3 rounded border-l-2 group transition-all cursor-pointer ${
                  currentThreadId === thread.id
                    ? "bg-surface-container-high border-primary-brand"
                    : "hover:bg-eye-border-hover border-transparent"
                }`}
                onClick={() => loadThread(thread.id)}
              >
                <div className="flex items-start justify-between">
                  <span className="text-sm font-medium text-white truncate flex-1">
                    {thread.title}
                  </span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteThread(thread.id);
                    }}
                    className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-red-400 transition-opacity"
                  >
                    <Trash2 className="h-3 w-3" />
                  </button>
                </div>
                <span className="text-[10px] text-primary-brand mt-1 font-mono">
                  {new Date(thread.updated_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  &bull; {thread.message_count} messages
                </span>
              </div>
            ))
          )}
        </nav>
        <div className="p-4 border-t border-eye-border flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-surface-container-high border border-eye-border overflow-hidden">
              <img
                className="w-full h-full object-cover"
                src="https://lh3.googleusercontent.com/aida-public/AB6AXuBoX1QcUCNe0fxY85lYyp70drYA-Xs3TNXYnpBTC07yHxRtWvwHpomfitx_Pu-SMrG2FHRe60c2dLWrp6OD5pF05bcqXICZtWTcax8cbZXDBrqEqN_7d6fk_cX0EDNhEK6tvhzA35otCsYWBNdsHBKhf2GvVIBBWVUUmC2JZBrNTJCOpqJsAx2d22BZzyYwQB3nzgX2sJbp1wlWZbdx9YK4RgFzWH6hrS96gCihF5GqSVHgQXz9O0DofVfGOleu3dCTwC-3c5usglo"
                alt="Administrator avatar"
              />
            </div>
            <div className="flex flex-col">
              <span className="text-xs font-medium text-white">Administrator</span>
              <span className="text-[9px] text-eye-text font-mono">L7-CLEARANCE</span>
            </div>
          </div>
          <button
            aria-label="Settings"
            className="text-eye-text hover:text-white transition-colors"
          >
            <Settings className="text-lg w-5 h-5" />
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col relative z-10 bg-eye-bg/40 backdrop-blur-sm">
        {/* Header */}
        <header className="h-16 glass-panel border-t-0 border-x-0 flex items-center justify-between px-8 z-30">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-primary-brand shadow-[0_0_8px_#38BDF8]" />
              <h2 className="text-sm font-bold tracking-tight text-white uppercase">
                Analytic Core v4.2
              </h2>
            </div>
            <div className="h-4 w-[1px] bg-eye-border" />
            <div className="flex items-center gap-1 bg-surface-container-high px-2 py-1 rounded text-[10px] font-mono text-primary-brand border border-primary-brand/20">
              <Shield className="w-3 h-3" />
              QUANTUM ENCRYPTED
            </div>
          </div>
          <div className="flex items-center gap-4">
            <button className="flex items-center gap-2 text-eye-text hover:text-white transition-colors">
              <Share className="text-lg w-5 h-5" />
              <span className="text-xs font-mono">EXPORT</span>
            </button>
            <button
              aria-label="User profile"
              className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-eye-border-hover transition-colors"
            >
              <User className="text-xl w-6 h-6" />
            </button>
          </div>
        </header>

        {/* Chat History */}
        <section className="flex-1 overflow-y-auto p-8 space-y-8 max-w-4xl mx-auto w-full pb-32">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="w-16 h-16 bg-primary-brand/10 rounded-full flex items-center justify-center mb-6">
                <Terminal className="text-primary-brand w-8 h-8" />
              </div>
              <h3 className="text-lg font-bold text-white mb-2">QORX Analytic Core</h3>
              <p className="text-sm text-eye-text max-w-md">
                Issue a command to begin analysis. The orchestrator will route your request to the
                appropriate specialist agent.
              </p>
            </div>
          )}

          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex flex-col gap-3 group ${msg.role === "user" ? "items-end" : ""}`}
              data-fade-up
            >
              <div className="flex items-center gap-2">
                {msg.role === "assistant" && (
                  <span className="text-[10px] text-primary-brand uppercase tracking-widest font-mono">
                    QORX ANALYTIC
                  </span>
                )}
                <span className="text-[10px] text-eye-text/40 font-mono">{msg.timestamp}</span>
                {msg.role === "user" && (
                  <span className="text-[10px] text-eye-text uppercase tracking-widest font-mono">
                    ADMINISTRATOR
                  </span>
                )}
              </div>
              {msg.role === "assistant" ? (
                <div className="pl-6 border-l-2 border-primary-brand py-2 relative message-gradient">
                  <p className="text-eye-white leading-relaxed text-[16px] whitespace-pre-wrap">
                    {msg.text}
                  </p>
                  <button
                    onClick={() => copyToClipboard(msg.text)}
                    className="absolute top-2 right-2 text-eye-text/30 hover:text-white transition-all opacity-0 group-hover:opacity-100"
                    aria-label="Copy response"
                  >
                    <Copy className="w-4 h-4" />
                  </button>
                </div>
              ) : (
                <div className="bg-surface-container-high border border-eye-border px-6 py-4 rounded-xl max-w-[85%]">
                  <p className="text-eye-white leading-relaxed text-[15px] whitespace-pre-wrap">
                    {msg.text}
                  </p>
                </div>
              )}
            </div>
          ))}

          {chatMutation.isPending && (
            <div className="flex flex-col gap-3" data-fade-up>
              <div className="flex items-center gap-2">
                 <span className="text-[10px] text-primary-brand uppercase tracking-widest font-mono">
                  QORX ANALYTIC
                </span>
              </div>
              <div className="flex items-center gap-4 bg-eye-surface/40 border border-primary-brand/10 rounded-full px-5 py-3 w-fit backdrop-blur-md">
                <div className="flex gap-1.5">
                  <div className="w-1.5 h-1.5 rounded-full bg-primary-brand thinking-dot" />
                  <div
                    className="w-1.5 h-1.5 rounded-full bg-primary-brand thinking-dot"
                    style={{ animationDelay: "0.2s" }}
                  />
                  <div
                    className="w-1.5 h-1.5 rounded-full bg-primary-brand thinking-dot"
                    style={{ animationDelay: "0.4s" }}
                  />
                </div>
                <span className="text-[10px] text-eye-text uppercase tracking-widest font-mono">
                  Thinking
                </span>
              </div>
            </div>
          )}

          <div ref={chatEndRef} />
        </section>

        {/* Input Area */}
        <footer className="absolute bottom-0 left-0 right-0 p-8 pt-0 pointer-events-none">
          <div className="max-w-4xl mx-auto w-full pointer-events-auto">
            <div className="glass-panel rounded-2xl p-2 relative overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-tr from-primary-brand/5 via-transparent to-transparent pointer-events-none" />
              <div className="flex flex-col gap-2">
                <div className="flex items-center gap-2 px-3 py-1 border-b border-eye-border/50">
                  <select className="bg-transparent border-none text-[10px] font-mono text-eye-text focus:ring-0 cursor-pointer hover:text-white transition-colors p-0 pr-6">
                    <option>AGENT: QORX-CORE</option>
                    <option>AGENT: VISION-PRO</option>
                    <option>AGENT: INFRA-V3</option>
                  </select>
                  <div className="h-3 w-[1px] bg-eye-border" />
                  <input type="file" ref={fileInputRef} className="hidden" onChange={handleFileUpload} />
                  <button 
                    onClick={() => fileInputRef.current?.click()}
                    className="flex items-center gap-1.5 text-[10px] font-mono text-eye-text hover:text-white transition-colors"
                  >
                    <Paperclip className="w-3.5 h-3.5" />
                    ATTACH
                  </button>
                </div>
                <div className="flex items-end gap-3 px-3 py-2">
                  <textarea
                    ref={textareaRef}
                    className="w-full bg-transparent border-none focus:ring-0 text-[15px] leading-relaxed resize-none py-1 max-h-48 min-h-[44px]"
                    placeholder={
                      chatMutation.isPending
                        ? "Analytic Core processing..."
                        : "Issue command to Analytic Core..."
                    }
                    rows={1}
                    value={message}
                    disabled={chatMutation.isPending}
                    onChange={(e) => {
                      setMessage(e.target.value);
                      e.currentTarget.style.height = "";
                      e.currentTarget.style.height = e.currentTarget.scrollHeight + "px";
                    }}
                    onKeyDown={handleKeyDown}
                  />
                  <button
                    aria-label="Send message"
                    onClick={handleSend}
                    disabled={chatMutation.isPending || !message.trim()}
                    className="w-10 h-10 flex-shrink-0 bg-white rounded-xl flex items-center justify-center text-background hover:shadow-[0_0_15px_rgba(56,189,248,0.4)] hover:bg-primary-brand transition-all group disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    <Send className="text-xl w-5 h-5 transition-transform group-active:scale-90" />
                  </button>
                </div>
              </div>
            </div>
            <div className="text-center mt-3">
              <p className="text-[9px] text-eye-text/30 uppercase tracking-[0.3em] font-mono">
                πX Technologies Unified Intelligence Interface &bull; Authorized Personnel Only
              </p>
            </div>
          </div>
        </footer>
      </main>

      {/* Right Detail Sidebar */}
      <aside className="w-[320px] h-screen bg-eye-surface border-l border-eye-border hidden xl:flex flex-col z-20">
        <div className="p-6">
          <h3 className="text-[10px] text-eye-text uppercase tracking-widest mb-6 font-mono">
            Agent Diagnostics
          </h3>
          <div className="space-y-6">
            {/* Status Card */}
            <div className="bg-surface-container border border-eye-border rounded-lg p-4">
              <div className="flex items-center justify-between mb-4">
                <span className="text-xs text-eye-text">Core Load</span>
                <span className="font-mono text-xs text-primary-brand">24.2%</span>
              </div>
              <div className="w-full bg-eye-border h-[2px] rounded-full overflow-hidden">
                <div className="bg-primary-brand h-full w-[24%] shadow-[0_0_8px_#38BDF8]" />
              </div>
              <div className="mt-4 grid grid-cols-2 gap-4">
                <div>
                  <span className="block text-[10px] text-eye-text/50 uppercase font-mono">
                    Uptime
                  </span>
                  <span className="font-mono text-xs text-white">412d 14h</span>
                </div>
                <div>
                  <span className="block text-[10px] text-eye-text/50 uppercase font-mono">
                    Tokens/sec
                  </span>
                  <span className="font-mono text-xs text-white">124.8</span>
                </div>
              </div>
            </div>

            {/* Abstract Visual for Agent */}
            <div className="aspect-square bg-black border border-eye-border rounded-lg relative overflow-hidden group">
              <div className="absolute inset-0 flex flex-col items-center justify-center text-center p-4">
                <div className="w-16 h-16 border-2 border-primary-brand/20 rounded-full flex items-center justify-center animate-pulse">
                  <div className="w-12 h-12 border border-primary-brand/40 rounded-full flex items-center justify-center">
                    <div className="w-4 h-4 bg-primary-brand rounded-full shadow-[0_0_15px_#38BDF8]" />
                  </div>
                </div>
                <span className="mt-4 text-[10px] text-primary-brand uppercase tracking-[0.2em] opacity-80 font-mono">
                  Syncing Intelligence
                </span>
              </div>
            </div>

            {/* Knowledge Base Snippet */}
            <div className="space-y-3">
              <span className="block text-[10px] text-eye-text uppercase tracking-widest font-mono">
                Active Context
              </span>
              {ragContexts.length === 0 ? (
                <div className="p-3 bg-eye-surface/50 border border-eye-border/50 rounded-md text-center">
                  <span className="text-[10px] text-eye-text font-mono">No context loaded</span>
                </div>
              ) : (
                ragContexts.map((ctx, idx) => (
                  <div key={idx} className="p-3 bg-eye-surface border border-eye-border rounded-md group hover:border-primary-brand/40 transition-colors">
                    <div className="flex items-center gap-2 mb-1">
                      <FileText className="text-primary-brand text-sm w-4 h-4" />
                      <span className="text-xs font-medium text-white truncate max-w-[200px]">{ctx.key}</span>
                    </div>
                    <p className="text-[10px] text-eye-text leading-relaxed line-clamp-2">
                      {ctx.value}
                    </p>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
        <div className="mt-auto p-6 space-y-4">
          <button className="w-full py-2.5 border border-eye-border hover:border-primary-brand/50 text-eye-text hover:text-white text-xs font-mono rounded transition-all flex items-center justify-center gap-2">
            <History className="text-sm w-4 h-4" />
            FULL CONTEXT LOGS
          </button>
          <button
            onClick={() => {
              setMessages([]);
              setMessage("");
              toast.success("Session purged");
            }}
            className="w-full py-2.5 border border-eye-border hover:border-red-500/50 text-eye-text hover:text-red-400 text-xs font-mono rounded transition-all flex items-center justify-center gap-2"
          >
            <Trash2 className="text-sm w-4 h-4" />
            PURGE SESSION
          </button>
        </div>
      </aside>
    </div>
  );
}
