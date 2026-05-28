import { api, getJSON, postJSON } from "./client";

export interface LocalUser {
  id: number;
  username: string;
  display_name: string | null;
  role: "admin" | "operator" | "viewer";
  permissions: string[];
  enabled: boolean;
  last_login_at: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface AuthResult {
  user: LocalUser;
}

export function bootstrapAuth() {
  return getJSON<{ has_users: boolean }>("/local-auth/bootstrap");
}

export function currentUser() {
  return getJSON<AuthResult>("/local-auth/me");
}

export function login(body: { username: string; password: string }) {
  return postJSON<AuthResult>("/local-auth/login", body);
}

export function register(body: { username: string; password: string; display_name?: string }) {
  return postJSON<AuthResult>("/local-auth/register", body);
}

export function logout() {
  return postJSON<{ status: string }>("/local-auth/logout");
}

export function listUsers() {
  return getJSON<{ items: LocalUser[] }>("/local-auth/users");
}

export async function updateUser(id: number, body: Partial<Pick<LocalUser, "display_name" | "role" | "permissions" | "enabled">> & { password?: string }) {
  const r = await api.patch<LocalUser>(`/local-auth/users/${id}`, body);
  return r.data;
}

export async function deleteUser(id: number) {
  const r = await api.delete<{ deleted: number }>(`/local-auth/users/${id}`);
  return r.data;
}
