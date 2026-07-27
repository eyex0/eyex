import { useState, useRef, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { ChatService } from "@/services/chat.service";
import {
  Search,
  CheckCircle2,
  Settings2,
  Clock,
  ArrowRight,
  FileText,
  CloudDownload,
  Terminal,
  Loader2,
  Send,
} from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";

interface ChatMessage {
  role: "user" | "assistant";
  text: string;
}

export function AiCopilotPage() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [history, setHistory] = useState<{ role: string; text: string }[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight);
  }, [messages]);

  interface CopilotResult {
    success: boolean;
    text?: string;
    error?: string;
  }

  const mutation = useMutation({
    mutationFn: (message: string) =>
      ChatService.sendMessage(message, history) as Promise<CopilotResult>,
    onSuccess: (result: CopilotResult) => {
      if (result?.success) {
        const assistantMsg: ChatMessage = { role: "assistant", text: result.text ?? "" };
        setMessages((prev) => [...prev, assistantMsg]);
        setHistory((prev) => [...prev, { role: "assistant", text: result.text ?? "" }]);
      } else {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", text: `Error: ${result?.error ?? "Unknown error"}` },
        ]);
      }
    },
    onError: (error: Error) => {
      setMessages((prev) => [...prev, { role: "assistant", text: `Error: ${error.message}` }]);
    },
  });

  const handleSubmit = () => {
    const trimmed = input.trim();
    if (!trimmed || mutation.isPending) return;
    const userMsg: ChatMessage = { role: "user", text: trimmed };
    setMessages((prev) => [...prev, userMsg]);
    setHistory((prev) => [...prev, { role: "user", text: trimmed }]);
    setInput("");
    mutation.mutate(trimmed);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <AppShell title="AI Copilot" subtitle="Analytic Engine">
      <div className="min-h-[calc(100vh-80px)] w-full flex flex-col items-center justify-center p-6 relative">
        <div className="absolute inset-0 overflow-hidden pointer-events-none -z-10">
          <div className="absolute top-1/4 left-1/4 w-[400px] h-[400px] bg-primary-brand opacity-[0.03] blur-[120px] rounded-full" />
          <div className="absolute bottom-1/4 right-1/4 w-[500px] h-[500px] bg-primary-brand opacity-[0.05] blur-[150px] rounded-full" />
        </div>

        <div className="w-full max-w-[600px] bg-eye-bg border border-eye-border rounded-xl flex flex-col overflow-hidden relative z-50 shadow-[0_0_0_1px_rgba(26,26,28,1),0_24px_48px_-12px_rgba(0,0,0,0.8),0_0_120px_rgba(56,189,248,0.05)] mt-12 mb-24">
        <div className="flex items-center px-5 h-16 border-b border-eye-border group focus-within:border-primary-brand/50 transition-colors">
          <Search className="text-eye-text mr-4 w-5 h-5" />
          <input
            className="flex-1 bg-transparent border-none focus:ring-0 text-on-background placeholder:text-eye-text text-base"
            placeholder="Command πX..."
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button
            onClick={handleSubmit}
            disabled={!input.trim() || mutation.isPending}
            className="ml-2 p-2 rounded-lg hover:bg-surface-container-high/40 transition disabled:opacity-30"
          >
            {mutation.isPending ? (
              <Loader2 className="w-4 h-4 text-primary-brand animate-spin" />
            ) : (
              <Send className="w-4 h-4 text-primary-brand" />
            )}
          </button>
          <div className="flex items-center gap-1.5 px-2 py-1 bg-surface-container-high border border-eye-border rounded-lg ml-2">
            <span className="font-mono text-xs text-eye-text opacity-70">CMD</span>
            <span className="font-mono text-xs text-eye-text opacity-70">+</span>
            <span className="font-mono text-xs text-eye-text opacity-70">K</span>
          </div>
        </div>

        <div
          ref={scrollRef}
          className="max-h-[480px] overflow-y-auto custom-scrollbar p-2 flex flex-col gap-6"
        >
          {messages.length === 0 ? (
            <>
              <section className="px-3 pt-4">
                <h3 className="font-mono text-xs text-eye-text mb-4 uppercase">
                  Agent Step Visualization
                </h3>
                <div className="grid grid-cols-1 gap-2">
                  <div className="flex items-center justify-between p-3 bg-eye-surface/50 border border-eye-border rounded-lg group">
                    <div className="flex items-center gap-3">
                      <CheckCircle2 className="text-primary-brand text-xl w-5 h-5" />
                      <span className="text-sm text-on-surface">Data Scraper</span>
                    </div>
                    <span className="text-[10px] text-primary-brand/60 uppercase font-mono">
                      Completed
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-eye-surface/50 border border-primary-brand/20 rounded-lg group">
                    <div className="flex items-center gap-3">
                      <Settings2
                        className="text-primary-brand text-xl w-5 h-5 animate-spin"
                        style={{ animationDuration: "3s" }}
                      />
                      <span className="text-sm text-on-background font-medium">
                        Analytic Engine
                      </span>
                    </div>
                    <span className="text-[10px] text-primary-brand uppercase font-mono animate-pulse">
                      Processing...
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-transparent border border-eye-border/50 rounded-lg group opacity-50">
                    <div className="flex items-center gap-3">
                      <Clock className="text-eye-text text-xl w-5 h-5" />
                      <span className="text-sm text-eye-text">Strategy Builder</span>
                    </div>
                    <span className="text-[10px] text-eye-text uppercase font-mono">Waiting</span>
                  </div>
                </div>
              </section>

              <section className="px-3">
                <div className="mb-6">
                  <h3 className="font-mono text-xs text-eye-text mb-3 uppercase flex items-center gap-2">
                    <span className="w-1 h-1 bg-primary-brand rounded-full" /> Analytics
                  </h3>
                  <div className="space-y-1">
                    <button
                      onClick={() => {
                        setInput("Revenue Cluster Analysis");
                      }}
                      className="w-full flex items-center justify-between p-3 hover:bg-surface-container-high/40 rounded-lg transition-all group text-left border border-transparent hover:border-eye-border"
                    >
                      <div className="flex flex-col">
                        <span className="text-base text-on-background group-hover:text-primary-brand transition-colors">
                          Revenue Cluster Analysis
                        </span>
                        <span className="text-sm text-eye-text">
                          Execute deep-scan on quarterly financials.
                        </span>
                      </div>
                      <ArrowRight className="text-eye-text opacity-0 group-hover:opacity-100 transition-opacity w-4 h-4" />
                    </button>
                  </div>
                </div>

                <div className="mb-6">
                  <h3 className="font-mono text-xs text-eye-text mb-3 uppercase flex items-center gap-2">
                    <span className="w-1 h-1 bg-[#f89f36] rounded-full" /> Reports
                  </h3>
                  <div className="space-y-1">
                    <button
                      onClick={() => {
                        setInput("Generate Q3 Summary");
                      }}
                      className="w-full flex items-center justify-between p-3 hover:bg-surface-container-high/40 rounded-lg transition-all group text-left border border-transparent hover:border-eye-border"
                    >
                      <div className="flex flex-col">
                        <span className="text-base text-on-background group-hover:text-primary-brand transition-colors">
                          Generate Q3 Summary
                        </span>
                        <span className="text-sm text-eye-text">
                          Compile all active insights into PDF.
                        </span>
                      </div>
                      <FileText className="text-eye-text opacity-0 group-hover:opacity-100 transition-opacity w-4 h-4" />
                    </button>
                  </div>
                </div>

                <div className="mb-2">
                  <h3 className="font-mono text-xs text-eye-text mb-3 uppercase flex items-center gap-2">
                    <span className="w-1 h-1 bg-on-surface-variant rounded-full" /> Data
                  </h3>
                  <div className="space-y-1">
                    <button
                      onClick={() => {
                        setInput("Import Raw Cluster");
                      }}
                      className="w-full flex items-center justify-between p-3 hover:bg-surface-container-high/40 rounded-lg transition-all group text-left border border-transparent hover:border-eye-border"
                    >
                      <div className="flex flex-col">
                        <span className="text-base text-on-background group-hover:text-primary-brand transition-colors">
                          Import Raw Cluster
                        </span>
                        <span className="text-sm text-eye-text">
                          Connect external AWS/Azure datasets.
                        </span>
                      </div>
                      <CloudDownload className="text-eye-text opacity-0 group-hover:opacity-100 transition-opacity w-4 h-4" />
                    </button>
                  </div>
                </div>
              </section>
            </>
          ) : (
            <div className="px-3 py-4 space-y-4">
              {messages.map((msg, i) => (
                <div
                  key={i}
                  className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[85%] rounded-lg px-4 py-3 text-sm ${
                      msg.role === "user"
                        ? "bg-primary-brand/10 border border-primary-brand/20 text-on-background"
                        : "bg-eye-surface border border-eye-border text-on-surface"
                    }`}
                  >
                    <div className="whitespace-pre-wrap">{msg.text}</div>
                  </div>
                </div>
              ))}
              {mutation.isPending && (
                <div className="flex justify-start">
                  <div className="bg-eye-surface border border-eye-border rounded-lg px-4 py-3 text-sm flex items-center gap-2">
                    <Loader2 className="w-4 h-4 text-primary-brand animate-spin" />
                    <span className="text-on-surface-variant">Thinking...</span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="h-12 bg-eye-surface border-t border-eye-border px-5 flex items-center justify-between">
          <div className="flex gap-6">
            <div className="flex items-center gap-2">
              <span className="font-mono text-[10px] text-eye-text bg-eye-border px-1.5 py-0.5 rounded">
                ↑↓
              </span>
              <span className="text-[11px] text-eye-text">Navigate</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-[10px] text-eye-text bg-eye-border px-1.5 py-0.5 rounded">
                ENTER
              </span>
              <span className="text-[11px] text-eye-text">Execute</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-[10px] text-eye-text bg-eye-border px-1.5 py-0.5 rounded">
                ESC
              </span>
              <span className="text-[11px] text-eye-text">Close</span>
            </div>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="font-mono text-[10px] text-primary-brand/80">πX CORE v2.4.0</span>
            <div className="w-1.5 h-1.5 bg-primary-brand rounded-full shadow-[0_0_8px_#38BDF8]" />
          </div>
        </div>
      </div>

      <div className="fixed bottom-0 left-0 right-0 z-50 flex justify-center pb-8 pointer-events-none">
        <div className="rounded-full mb-8 max-w-2xl mx-auto border border-surface-container-high/30 shadow-[0_0_30px_rgba(56,189,248,0.1)] bg-surface-container-high/90 backdrop-blur-xl flex justify-center py-3 px-8 pointer-events-auto cursor-pointer hover:shadow-[0_0_20px_rgba(56,189,248,0.2)] hover:border-primary-brand transition-all">
          <div className="flex items-center gap-3">
            <Terminal className="text-primary-brand w-5 h-5" />
            <span className="font-mono text-primary-brand">Command AI</span>
          </div>
        </div>
      </div>
      </div>
    </AppShell>
  );
}
