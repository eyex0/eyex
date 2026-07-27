/**
 * πX Memory Intelligence Service — Frontend integration for memory + ingestion APIs.
 * Extends the existing backend-api.service with vector search and ingestion.
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

export interface IngestionResult {
  document_id: string;
  chunks_created: number;
  embeddings_generated: number;
  processing_time_ms: number;
  errors: string[];
}

export interface MemoryChunk {
  id: string;
  text: string;
  score: number;
  metadata: Record<string, unknown>;
}

export const MemoryIntelligenceService = {
  async ingestText(
    text: string,
    metadata?: Record<string, unknown>,
  ): Promise<IngestionResult> {
    return apiFetch("/intelligence/ingest", {
      method: "POST",
      body: JSON.stringify({ text, metadata }),
    });
  },

  async ingestFile(
    file: File,
    metadata?: Record<string, unknown>,
  ): Promise<IngestionResult> {
    const token = await getAuthToken();
    const formData = new FormData();
    formData.append("file", file);
    if (metadata) {
      formData.append("metadata", JSON.stringify(metadata));
    }
    const res = await fetch(`${BASE_URL}/intelligence/ingest-file`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    });
    if (!res.ok) throw new Error(`Ingestion failed: ${res.status}`);
    return res.json();
  },

  async semanticSearch(
    query: string,
    limit: number = 10,
  ): Promise<MemoryChunk[]> {
    return apiFetch("/intelligence/search", {
      method: "POST",
      body: JSON.stringify({ query, limit }),
    });
  },

  async hybridSearch(
    query: string,
    limit: number = 10,
  ): Promise<MemoryChunk[]> {
    return apiFetch("/intelligence/hybrid-search", {
      method: "POST",
      body: JSON.stringify({ query, limit }),
    });
  },
};
