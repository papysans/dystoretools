import { getJSON, postJSON, api } from "./client";

export interface LlmProvider {
  id: number;
  name: string;
  adapter_kind: "openai_compat" | "anthropic";
  base_url: string;
  enabled: boolean;
  key_set: boolean;
  key_fingerprint: string | null;
  default_headers: Record<string, string> | null;
  model_count: number;
}

export interface LlmModel {
  id: number;
  provider_id: number;
  model_name: string;
  display_name: string | null;
  context_window: number | null;
  capabilities: string[];
  enabled: boolean;
  is_default_for_chat: boolean;
}

export async function listProviders() {
  return getJSON<{ items: LlmProvider[] }>("/llm/providers");
}

export async function saveProvider(values: Partial<LlmProvider> & { api_key?: string; id?: number }) {
  if (values.id) {
    const { id, ...body } = values;
    const r = await api.patch<LlmProvider>(`/llm/providers/${id}`, body);
    return r.data;
  }
  return postJSON<LlmProvider>("/llm/providers", values);
}

export async function testProvider(providerId: number) {
  return postJSON<{ ok: boolean; error?: string; latency_ms?: number }>(`/llm/providers/${providerId}/test`);
}

export async function discoverProviderModels(providerId: number) {
  return getJSON<{ ok: boolean; models?: { id: string }[]; error?: string }>(`/llm/providers/${providerId}/models:discover`);
}

export async function listModels(providerId?: number, chatCapable = false) {
  return getJSON<{ items: LlmModel[] }>("/llm/models", {
    provider_id: providerId,
    chat_capable: chatCapable,
  });
}

export async function saveModel(values: Partial<LlmModel> & { id?: number; capabilities?: string[] }) {
  if (values.id) {
    const { id, ...body } = values;
    const r = await api.patch<LlmModel>(`/llm/models/${id}`, body);
    return r.data;
  }
  return postJSON<LlmModel>("/llm/models", values);
}
