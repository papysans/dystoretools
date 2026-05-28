import { api, getJSON, postJSON } from "./client";

export interface UserAgent {
  id: number;
  name: string;
  description: string | null;
  system_prompt: string;
  provider_id: number | null;
  model_name: string | null;
  tools: string[];
  enabled: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface AgentSchedule {
  id: number;
  agent_id: number;
  name: string;
  prompt: string;
  cron: string;
  timezone: string;
  enabled: boolean;
  last_run_at: string | null;
  next_run_at: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface AgentRun {
  id: number;
  agent_id: number;
  schedule_id: number | null;
  conversation_id: number | null;
  trigger_kind: string;
  prompt: string;
  status: string;
  result_text: string | null;
  error_msg: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string | null;
}

export interface AgentPayload {
  name: string;
  description?: string | null;
  system_prompt?: string | null;
  provider_id?: number | null;
  model_name?: string | null;
  tools?: string[];
  enabled?: boolean;
}

export interface SchedulePayload {
  agent_id: number;
  name: string;
  prompt: string;
  cron: string;
  timezone?: string;
  enabled?: boolean;
}

export function listAgents() {
  return getJSON<{ items: UserAgent[] }>("/agents");
}

export function createAgent(body: AgentPayload) {
  return postJSON<UserAgent>("/agents", body);
}

export async function updateAgent(id: number, body: Partial<AgentPayload>) {
  const r = await api.patch<UserAgent>(`/agents/${id}`, body);
  return r.data;
}

export async function deleteAgent(id: number) {
  const r = await api.delete<{ deleted: number }>(`/agents/${id}`);
  return r.data;
}

export function runAgent(id: number, prompt: string) {
  return postJSON<AgentRun>(`/agents/${id}/runs`, { prompt });
}

export function listAgentRuns(agentId?: number) {
  return getJSON<{ items: AgentRun[] }>("/agents/runs/recent", agentId ? { agent_id: agentId, limit: 100 } : { limit: 100 });
}

export function listSchedules(agentId?: number) {
  return getJSON<{ items: AgentSchedule[] }>("/agents/schedules/all", agentId ? { agent_id: agentId } : undefined);
}

export function createSchedule(body: SchedulePayload) {
  return postJSON<AgentSchedule>("/agents/schedules", body);
}

export async function updateSchedule(id: number, body: Partial<SchedulePayload>) {
  const r = await api.patch<AgentSchedule>(`/agents/schedules/${id}`, body);
  return r.data;
}

export async function deleteSchedule(id: number) {
  const r = await api.delete<{ deleted: number }>(`/agents/schedules/${id}`);
  return r.data;
}
