import { GoogleGenAI } from "@google/genai";

const DEFAULT_MODEL = "gemini-2.5-flash";
const DEFAULT_TIMEOUT_MS = 30_000;
const MAX_RETRIES = 3;
const INITIAL_RETRY_DELAY_MS = 1_000;

let client: GoogleGenAI | null = null;

function getClient(): GoogleGenAI {
  if (!client) {
    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey) {
      throw new Error("GEMINI_API_KEY is not set. Configure it in .env or environment variables.");
    }
    client = new GoogleGenAI({
      apiKey,
      httpOptions: { headers: { "User-Agent": "pix-agents" } },
    });
  }
  return client;
}

function validateModel(model: string): void {
  const validPrefixes = ["gemini-2.5-", "gemini-2.0-", "gemini-1.5-"];
  const isValid = validPrefixes.some((p) => model.startsWith(p));
  if (!isValid) {
    console.warn(`Unknown model "${model}" — falling back to ${DEFAULT_MODEL}`);
  }
}

async function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export interface LLMConfig {
  model?: string;
  temperature?: number;
  maxOutputTokens?: number;
  systemInstruction?: string;
  responseSchema?: Record<string, unknown>;
}

export async function generateText(prompt: string, config: LLMConfig = {}): Promise<string> {
  const model = config.model || DEFAULT_MODEL;
  validateModel(model);

  const ai = getClient();
  let lastError: Error | null = null;

  for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS);

      const response = await ai.models.generateContent({
        model,
        contents: prompt,
        config: {
          temperature: config.temperature ?? 0.3,
          maxOutputTokens: config.maxOutputTokens ?? 4096,
          systemInstruction: config.systemInstruction,
          responseMimeType: config.responseSchema ? "application/json" : undefined,
          responseSchema: config.responseSchema,
        },
      });

      clearTimeout(timeout);

      if (!response.text) {
        if (attempt < MAX_RETRIES - 1) {
          const delay = INITIAL_RETRY_DELAY_MS * Math.pow(2, attempt);
          await sleep(delay);
          continue;
        }
        return "";
      }

      return response.text.trim();
    } catch (err: unknown) {
      lastError = err instanceof Error ? err : new Error(String(err));
      const isRetryable =
        lastError.message.includes("429") ||
        lastError.message.includes("500") ||
        lastError.message.includes("503") ||
        lastError.message.includes("timeout") ||
        lastError.message.includes("abort");

      if (isRetryable && attempt < MAX_RETRIES - 1) {
        const delay = INITIAL_RETRY_DELAY_MS * Math.pow(2, attempt);
        await sleep(delay);
        continue;
      }

      throw lastError;
    }
  }

  throw lastError ?? new Error("LLM call failed after retries");
}

export async function generateStructured<T>(
  prompt: string,
  schema: Record<string, unknown>,
  config: LLMConfig = {},
): Promise<T> {
  const text = await generateText(prompt, { ...config, responseSchema: schema });
  try {
    return JSON.parse(text) as T;
  } catch {
    throw new Error(`Failed to parse structured output: ${text.slice(0, 200)}`);
  }
}
