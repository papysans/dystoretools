import { getJSON, postJSON } from "./client";

export interface ChatConversation {
  id: number;
  title: string;
  provider_id: number | null;
  model_name: string | null;
  last_message_preview: string | null;
  total_tokens_in: number;
  total_tokens_out: number;
  total_cost_cny: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface ChatMessage {
  id: number;
  conversation_id: number;
  role: "user" | "assistant" | "tool";
  kind: string;
  content: string | null;
  provider_id: number | null;
  model_name: string | null;
  tool_calls?: unknown;
  tool_results?: unknown;
  render_spec?: any;
  source_sql?: string | null;
  status: string;
  created_at: string | null;
}

export async function listConversations() {
  return getJSON<{ items: ChatConversation[] }>("/chat/conversations");
}

export async function createConversation(body: Partial<ChatConversation>) {
  return postJSON<ChatConversation>("/chat/conversations", body);
}

export async function listMessages(conversationId: number) {
  return getJSON<{ items: ChatMessage[] }>(`/chat/conversations/${conversationId}/messages`);
}

export async function streamChatMessage(
  conversationId: number,
  body: { content: string; provider_id?: number; model_name?: string },
  onEvent: (event: string, data: any) => void,
) {
  const res = await fetch(`/api/v1/chat/conversations/${conversationId}/messages:stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok || !res.body) throw new Error(await res.text());
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";
    for (const chunk of chunks) {
      const event = chunk.match(/^event:\s*(.+)$/m)?.[1] ?? "message";
      const raw = chunk.match(/^data:\s*(.+)$/m)?.[1] ?? "{}";
      onEvent(event, JSON.parse(raw));
    }
  }
}
