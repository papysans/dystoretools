import axios from "axios";

export const api = axios.create({ baseURL: "/api/v1", timeout: 30_000 });

export async function getJSON<T>(path: string, params?: Record<string, unknown>): Promise<T> {
  const r = await api.get<T>(path, { params });
  return r.data;
}

export async function postJSON<T>(path: string, body?: unknown): Promise<T> {
  const r = await api.post<T>(path, body);
  return r.data;
}
