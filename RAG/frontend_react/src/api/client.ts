import axios, { type AxiosInstance } from 'axios';
import { BACKEND_URL, CHAT_REQUEST_TIMEOUT_MS } from '../config';
import type { Agent, AgentWithMessages, ChatResponse, AdminUser, AuditEntry } from '../types';

const api: AxiosInstance = axios.create({
  baseURL: BACKEND_URL,
  timeout: 60000,
  headers: { 'Content-Type': 'application/json' },
});

export function setAuthToken(token: string | null) {
  if (token) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  } else {
    delete api.defaults.headers.common['Authorization'];
  }
}

export async function getAuthUrl(): Promise<{ auth_url: string }> {
  const { data } = await api.get<{ auth_url: string }>('/auth/login');
  return data;
}

export async function getMe(): Promise<{ email: string; name?: string; picture?: string }> {
  const { data } = await api.get('/auth/me');
  return data;
}

export async function listAgents(): Promise<Agent[]> {
  const { data } = await api.get<Agent[]>('/chat/agents');
  return data;
}

export async function createAgent(name?: string): Promise<Agent> {
  const { data } = await api.post<Agent>('/chat/agents', { name: name || 'Nueva conversación' });
  return data;
}

export async function getAgent(agentId: string): Promise<AgentWithMessages> {
  const { data } = await api.get<AgentWithMessages>(`/chat/agents/${agentId}`);
  return data;
}

export async function deleteAgent(agentId: string): Promise<void> {
  await api.delete(`/chat/agents/${agentId}`);
}

export async function chatQuery(
  message: string,
  agentId: string | null,
  _history?: Array<{ role: string; content: string }>,
  llmProvider?: 'gemini' | 'ollama'
): Promise<ChatResponse> {
  const { data } = await api.post<ChatResponse>(
    '/chat/query',
    { message, agent_id: agentId, llm_provider: llmProvider ?? 'gemini' },
    { timeout: CHAT_REQUEST_TIMEOUT_MS }
  );
  return data;
}

export async function getPdfBlob(signedUrl: string): Promise<Blob> {
  const { data } = await api.post<Blob>(
    '/docs/pdf-proxy',
    { signed_url: signedUrl },
    { responseType: 'blob', timeout: 60000 }
  );
  return data;
}

// --- Admin (solo rol admin) ---

export async function adminListUsers(): Promise<AdminUser[]> {
  const { data } = await api.get<AdminUser[]>('/admin/users');
  return data;
}

export async function adminGetUser(email: string): Promise<AdminUser> {
  const { data } = await api.get<AdminUser>(`/admin/users/${encodeURIComponent(email)}`);
  return data;
}

export async function adminUpdateUser(
  email: string,
  body: { name?: string; picture?: string; role?: string; is_active?: boolean }
): Promise<AdminUser> {
  const { data } = await api.patch<AdminUser>(`/admin/users/${encodeURIComponent(email)}`, body);
  return data;
}

export async function adminListUserPermissions(email: string): Promise<{ permissions: string[] }> {
  const { data } = await api.get<{ permissions: string[] }>(
    `/admin/users/${encodeURIComponent(email)}/permissions`
  );
  return data;
}

export async function adminAddPermission(email: string, permission_key: string): Promise<void> {
  await api.post(`/admin/users/${encodeURIComponent(email)}/permissions`, { permission_key });
}

export async function adminRevokePermission(email: string, permission_key: string): Promise<void> {
  await api.delete(
    `/admin/users/${encodeURIComponent(email)}/permissions/${encodeURIComponent(permission_key)}`
  );
}

export interface AuditFilters {
  user_email?: string;
  agent_id?: string;
  since?: string;
  until?: string;
  limit?: number;
}

export async function adminAuditQueries(filters?: AuditFilters): Promise<AuditEntry[]> {
  const params = new URLSearchParams();
  if (filters?.user_email) params.set('user_email', filters.user_email);
  if (filters?.agent_id) params.set('agent_id', filters.agent_id);
  if (filters?.since) params.set('since', filters.since);
  if (filters?.until) params.set('until', filters.until);
  if (filters?.limit != null) params.set('limit', String(filters.limit));
  const { data } = await api.get<AuditEntry[]>(`/admin/audit/queries?${params.toString()}`);
  return data;
}

export async function adminStats(): Promise<{
  total_users: number;
  total_agents: number;
  total_queries: number;
}> {
  const { data } = await api.get('/admin/stats');
  return data;
}

export default api;
