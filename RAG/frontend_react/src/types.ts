export interface User {
  email: string;
  name?: string;
  picture?: string;
  role?: 'admin' | 'user';
  is_active?: boolean;
  permissions?: string[];
}

export interface Source {
  document_id: string;
  document_name: string;
  page_number?: number;
  snippet: string;
  score?: number;
  signed_url?: string;
  pdf_path?: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
}

export interface ChatResponse {
  response: string;
  sources: Source[];
  conversation_id: string;
  agent_id: string;
  agent_name?: string;
}

export interface Agent {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
}

export interface MessageOut {
  role: string;
  content: string;
  sources?: Source[];
}

export interface AgentWithMessages {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  messages: MessageOut[];
}

export interface AdminUser {
  email: string;
  name?: string;
  picture?: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface AuditEntry {
  id: string;
  user_email: string;
  agent_id: string;
  user_input: string;
  created_at: string;
  request_id?: string;
  session_id?: string;
}
