import { useState, useCallback, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Button, Input, Layout, List, message as antMessage, Popconfirm, Select, Space, Typography } from 'antd';
import { SendOutlined, LogoutOutlined, UserOutlined, PlusOutlined, MessageOutlined, DeleteOutlined, SettingOutlined } from '@ant-design/icons';
import { useAuth } from '../auth/AuthContext';
import { chatQuery, listAgents, createAgent, getAgent, deleteAgent } from '../api/client';
import type { Agent, AgentWithMessages, ChatMessage as ChatMessageType } from '../types';
import MessageList from '../components/MessageList';

const { Header, Content, Sider } = Layout;
const { TextArea } = Input;
const { Title, Text } = Typography;

function toChatMessages(ms: { role: string; content: string; sources?: unknown[] }[] | null | undefined): ChatMessageType[] {
  const list = Array.isArray(ms) ? ms : [];
  return list.map((x) => ({
    role: (x?.role ?? 'user') as 'user' | 'assistant',
    content: String(x?.content ?? ''),
    sources: (x?.sources as ChatMessageType['sources']) ?? undefined,
  }));
}

export default function Chat() {
  const { user, logout } = useAuth();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [agentsLoading, setAgentsLoading] = useState(true);
  const [currentAgentId, setCurrentAgentId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [llmProvider, setLlmProvider] = useState<'gemini' | 'ollama'>('gemini');

  const fetchAgents = useCallback(async () => {
    setAgentsLoading(true);
    try {
      const list = await listAgents();
      setAgents(list);
      return list;
    } catch (e) {
      antMessage.error('No se pudo cargar el historial de agentes.');
      return [];
    } finally {
      setAgentsLoading(false);
    }
  }, []);

  const loadAgent = useCallback(async (agentId: string) => {
    setHistoryLoading(true);
    setCurrentAgentId(agentId);
    try {
      const a: AgentWithMessages = await getAgent(agentId);
      setMessages(toChatMessages(a?.messages));
    } catch (e) {
      antMessage.error('No se pudo cargar el historial del agente.');
      setMessages([]);
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const list = await fetchAgents();
      if (cancelled) return;
      if (list.length > 0) loadAgent(list[0].id);
    })();
    return () => { cancelled = true; };
  }, [fetchAgents, loadAgent]);

  const handleNewAgent = useCallback(async () => {
    try {
      const created = await createAgent();
      setAgents((prev) => [created, ...prev]);
      setCurrentAgentId(created.id);
      setMessages([]);
    } catch (e) {
      antMessage.error('No se pudo crear un nuevo agente.');
    }
  }, []);

  const handleDeleteAgent = useCallback(
    async (agentId: string) => {
      try {
        await deleteAgent(agentId);
        setAgents((prev) => prev.filter((a) => a.id !== agentId));
        if (currentAgentId === agentId) {
          setCurrentAgentId(null);
          setMessages([]);
        }
        antMessage.success('Conversación eliminada.');
      } catch (e) {
        antMessage.error('No se pudo eliminar la conversación.');
      }
    },
    [currentAgentId]
  );

  const sendMessage = useCallback(async () => {
    const text = input.trim();
    if (!text || loading) return;

    let agentId = currentAgentId;
    if (!agentId) {
      try {
        const created = await createAgent();
        setAgents((prev) => [created, ...prev]);
        setCurrentAgentId(created.id);
        agentId = created.id;
      } catch (e) {
        antMessage.error('No se pudo crear un agente. Intenta de nuevo.');
        return;
      }
    }

    setInput('');
    const userMsg: ChatMessageType = { role: 'user', content: text };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const res = await chatQuery(text, agentId, undefined, llmProvider);
      const assistantMsg: ChatMessageType = {
        role: 'assistant',
        content: res.response,
        sources: res.sources,
      };
      setMessages((prev) => [...prev, assistantMsg]);
      setAgents((prev) => {
        const updated = prev.map((a) => {
          if (a.id !== agentId) return a;
          const next = { ...a, updated_at: new Date().toISOString() };
          if (res.agent_name != null) next.name = res.agent_name;
          return next;
        });
        return [...updated].sort(
          (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
        );
      });
    } catch (err: unknown) {
      const msg =
        err && typeof err === 'object' && 'message' in err
          ? String((err as Error).message)
          : 'Error al procesar la consulta.';
      if (msg.includes('timeout') || msg.includes('Timeout')) {
        antMessage.error('La solicitud tardó demasiado. Intenta de nuevo o aumenta el timeout.');
      } else {
        antMessage.error(msg || 'Error inesperado. Intenta de nuevo.');
      }
      setMessages((prev) => prev.slice(0, -1));
    } finally {
      setLoading(false);
    }
  }, [input, loading, currentAgentId, llmProvider]);

  return (
    <Layout style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Header
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 24px',
          background: '#001529',
          color: '#fff',
        }}
      >
        <Space>
          <Title level={4} style={{ margin: 0, color: '#fff' }}>
            RAG - Asistente Documental
          </Title>
          {user?.role === 'admin' && (
            <Link to="/admin" style={{ color: 'rgba(255,255,255,0.85)', marginLeft: 16 }}>
              <SettingOutlined /> Administración
            </Link>
          )}
        </Space>
        <Space>
          <Text style={{ color: 'rgba(255,255,255,0.85)' }}>
            <UserOutlined /> {user?.email ?? user?.name ?? 'Usuario'}
          </Text>
          <Button type="primary" ghost icon={<LogoutOutlined />} onClick={logout}>
            Cerrar sesión
          </Button>
        </Space>
      </Header>
      <Layout style={{ flex: 1, minHeight: 0, display: 'flex' }}>
        <Sider
          width={280}
          style={{
            background: '#fafafa',
            borderRight: '1px solid #f0f0f0',
            overflow: 'auto',
          }}
        >
          <div style={{ padding: 16 }}>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              block
              onClick={handleNewAgent}
            >
              Nueva conversación
            </Button>
          </div>
          <List
            loading={agentsLoading}
            dataSource={agents}
            style={{ padding: '0 12px 16px' }}
            renderItem={(a) => (
              <List.Item
                key={a.id}
                style={{
                  cursor: 'pointer',
                  borderRadius: 8,
                  padding: '10px 12px',
                  height: 64,
                  minHeight: 64,
                  maxHeight: 64,
                  overflow: 'hidden',
                  marginBottom: 8,
                  background: currentAgentId === a.id ? '#e6f4ff' : 'transparent',
                  border: currentAgentId === a.id ? '1px solid #91caff' : '1px solid transparent',
                  display: 'flex',
                  alignItems: 'center',
                }}
                onClick={() => loadAgent(a.id)}
              >
                <div style={{ flex: 1, minWidth: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
                  <MessageOutlined style={{ flexShrink: 0 }} />
                  <div style={{ flex: 1, minWidth: 0, overflow: 'hidden' }}>
                    <div
                      title={a.name}
                      style={{
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                        fontWeight: 600,
                        fontSize: 13,
                      }}
                    >
                      {a.name}
                    </div>
                    <Text type="secondary" style={{ fontSize: 11, display: 'block' }}>
                      {new Date(a.updated_at).toLocaleDateString('es-CO', {
                        day: 'numeric',
                        month: 'short',
                        year: 'numeric',
                      })}
                    </Text>
                  </div>
                  {(user?.role === 'admin' || (user?.permissions ?? []).includes('delete_own_agents')) && (
                    <Popconfirm
                      title="¿Eliminar esta conversación?"
                      onConfirm={() => handleDeleteAgent(a.id)}
                    >
                      <Button
                        type="text"
                        size="small"
                        danger
                        icon={<DeleteOutlined />}
                        onClick={(e) => e.stopPropagation()}
                        style={{ flexShrink: 0 }}
                      />
                    </Popconfirm>
                  )}
                </div>
              </List.Item>
            )}
          />
        </Sider>
        <Content
          style={{
            flex: 1,
            minHeight: 0,
            padding: 24,
            maxWidth: 900,
            margin: '0 auto',
            width: '100%',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'auto',
          }}
        >
          {historyLoading && (
            <div style={{ textAlign: 'center', padding: 24, color: '#8c8c8c' }}>
              Cargando historial…
            </div>
          )}
          {!historyLoading && messages.length === 0 && (
            <div style={{ textAlign: 'center', padding: '48px 0', color: '#8c8c8c' }}>
              <Title level={5}>¡Hola! Soy tu asistente.</Title>
              <Text>Escribe tu pregunta sobre los documentos o crea una nueva conversación.</Text>
            </div>
          )}
          {!historyLoading && <MessageList messages={messages} />}
          <Space.Compact style={{ width: '100%', marginTop: 16 }}>
            <TextArea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onPressEnter={(e) => {
                if (!e.shiftKey) {
                  e.preventDefault();
                  sendMessage();
                }
              }}
              placeholder="Escribe tu pregunta..."
              autoSize={{ minRows: 2, maxRows: 4 }}
              disabled={loading}
              style={{ resize: 'none' }}
            />
            <Select
              value={llmProvider}
              onChange={(v) => setLlmProvider(v)}
              options={[
                { value: 'gemini', label: 'Gemini' },
                { value: 'ollama', label: 'Ollama' },
              ]}
              style={{ width: 120 }}
              disabled={loading}
              size="large"
            />
            <Button
              type="primary"
              icon={<SendOutlined />}
              loading={loading}
              onClick={sendMessage}
              size="large"
            >
              Enviar
            </Button>
          </Space.Compact>
        </Content>
      </Layout>
    </Layout>
  );
}
