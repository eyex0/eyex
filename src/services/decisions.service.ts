/**
 * πX Decisions Service — Frontend integration with the decision intelligence API.
 * Connects to /api/v1/decisions/* endpoints.
 */
import { supabase } from "@/lib/supabase/client";

const BASE_URL = import.meta.env.VITE_PYTHON_BACKEND_URL || "/api/v1";

async function getAuthToken(): Promise<string | null> {
  if (typeof window === "undefined") return null;
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? null;
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const token = await getAuthToken();
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  });
  if (!res.ok) throw new Error(`API error: ${res.status} ${res.statusText}`);
  return res.json();
}

export interface DecisionEvidence {
  source: string;
  key: string;
  content: string;
  confidence: number;
}

export interface DecisionRisk {
  id: string;
  description: string;
  probability: number;
  impact: number;
  risk_score: number;
  category: string;
  mitigation: string;
}

export interface DecisionAlternative {
  id: string;
  title: string;
  description: string;
  pros: string[];
  cons: string[];
  estimated_cost: string;
  estimated_impact: string;
  feasibility: number;
}

export interface DecisionResult {
  decision_id: string;
  question: string;
  context_summary: string;
  evidence: DecisionEvidence[];
  reasoning_chain: string[];
  risks: DecisionRisk[];
  overall_risk_level: string;
  recommendation: string;
  confidence: number;
  alternatives: DecisionAlternative[];
  created_at: string;
}

export interface DecisionListItem {
  id: string;
  title: string;
  category: string;
  status: "pending" | "approved" | "rejected" | "reviewed";
  confidence_score: number;
  recommendation: string;
  created_at: string;
}

export interface DecisionAnalytics {
  total: number;
  approved: number;
  rejected: number;
  pending: number;
  avg_confidence: number;
  by_category: Record<string, number>;
}

export const DecisionsService = {
  async createDecision(body: {
    question: string;
    context?: Record<string, unknown>;
    category?: string;
  }): Promise<DecisionResult> {
    return apiFetch("/decisions/", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  async listDecisions(params?: {
    status?: string;
    category?: string;
    limit?: number;
    offset?: number;
  }): Promise<{ decisions: DecisionListItem[]; total: number }> {
    const query = new URLSearchParams();
    if (params?.status) query.set("status", params.status);
    if (params?.category) query.set("category", params.category);
    if (params?.limit) query.set("limit", String(params.limit));
    if (params?.offset) query.set("offset", String(params.offset));
    return apiFetch(`/decisions/?${query.toString()}`);
  },

  async getDecision(decisionId: string): Promise<DecisionResult> {
    return apiFetch(`/decisions/${decisionId}`);
  },

  async updateStatus(
    decisionId: string,
    body: { status: string; approved_by?: string },
  ): Promise<DecisionResult> {
    return apiFetch(`/decisions/${decisionId}/status`, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  },

  async getAnalytics(): Promise<DecisionAnalytics> {
    return apiFetch("/decisions/analytics/summary");
  },
};
