/**
 * πX Knowledge Graph Service — Frontend integration with the knowledge graph API.
 * Connects to /api/v1/knowledge/* endpoints.
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

export interface KnowledgeNode {
  id: string;
  label: string;
  type: string;
  properties: Record<string, unknown>;
  neighbors?: KnowledgeRelation[];
}

export interface KnowledgeRelation {
  id: string;
  source: string;
  target: string;
  relation_type: string;
  weight: number;
}

export interface GraphData {
  nodes: KnowledgeNode[];
  edges: KnowledgeRelation[];
}

export interface GraphStats {
  node_count: number;
  edge_count: number;
  type_distribution: Record<string, number>;
}

export interface ExtractedEntity {
  name: string;
  entity_type: string;
  properties: Record<string, unknown>;
  confidence: number;
}

export interface ExtractedRelation {
  source: string;
  target: string;
  relation_type: string;
  confidence: number;
}

export interface ExtractionResult {
  entities: ExtractedEntity[];
  relationships: ExtractedRelation[];
}

export interface BuildResult {
  document_id: string;
  nodes_created: number;
  relations_created: number;
  entities: string[];
}

export const KnowledgeGraphService = {
  async listNodes(params?: {
    node_type?: string;
    search?: string;
    limit?: number;
    offset?: number;
  }): Promise<{ nodes: KnowledgeNode[]; total: number }> {
    const query = new URLSearchParams();
    if (params?.node_type) query.set("node_type", params.node_type);
    if (params?.search) query.set("search", params.search);
    if (params?.limit) query.set("limit", String(params.limit));
    if (params?.offset) query.set("offset", String(params.offset));
    return apiFetch(`/knowledge/nodes?${query.toString()}`);
  },

  async createNode(body: { label: string; type: string; properties?: Record<string, unknown> }): Promise<KnowledgeNode> {
    return apiFetch("/knowledge/nodes", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  async getNode(nodeId: string): Promise<KnowledgeNode & { neighbors: KnowledgeRelation[] }> {
    return apiFetch(`/knowledge/nodes/${nodeId}`);
  },

  async deleteNode(nodeId: string): Promise<{ deleted: boolean }> {
    return apiFetch(`/knowledge/nodes/${nodeId}`, { method: "DELETE" });
  },

  async createRelation(body: {
    source_id: string;
    target_id: string;
    relation_type: string;
    properties?: Record<string, unknown>;
    weight?: number;
  }): Promise<{ id: string }> {
    return apiFetch("/knowledge/relations", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  async getGraph(params?: { limit?: number; offset?: number }): Promise<GraphData> {
    const query = new URLSearchParams();
    if (params?.limit) query.set("limit", String(params.limit));
    if (params?.offset) query.set("offset", String(params.offset));
    return apiFetch(`/knowledge/graph?${query.toString()}`);
  },

  async extractEntities(text: string): Promise<ExtractionResult> {
    return apiFetch("/knowledge/extract", {
      method: "POST",
      body: JSON.stringify({ text }),
    });
  },

  async buildFromDocument(documentId: string, text: string): Promise<BuildResult> {
    return apiFetch("/knowledge/build", {
      method: "POST",
      body: JSON.stringify({ document_id: documentId, text }),
    });
  },

  async getStats(): Promise<GraphStats> {
    return apiFetch("/knowledge/stats");
  },
};
