import { useState, useCallback, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Button,
  DatePicker,
  Form,
  Input,
  Layout,
  message as antMessage,
  Modal,
  Select,
  Space,
  Switch,
  Table,
  Tabs,
  Tag,
  Typography,
} from 'antd';
import {
  LogoutOutlined,
  UserOutlined,
  SettingOutlined,
  SearchOutlined,
  KeyOutlined,
  EditOutlined,
  MessageOutlined,
} from '@ant-design/icons';
import { useAuth } from '../auth/AuthContext';
import {
  adminListUsers,
  adminUpdateUser,
  adminListUserPermissions,
  adminAddPermission,
  adminRevokePermission,
  adminAuditQueries,
  adminStats,
  type AuditFilters,
} from '../api/client';
import type { AdminUser, AuditEntry } from '../types';

const { Header, Content } = Layout;
const { Title, Text } = Typography;

const PERM_OPTIONS = [
  { value: 'delete_own_agents', label: 'Eliminar sus propios agentes' },
  { value: 'delete_own_history', label: 'Eliminar su propio historial' },
];

export default function Admin() {
  const { user, logout } = useAuth();
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [usersLoading, setUsersLoading] = useState(true);
  const [audit, setAudit] = useState<AuditEntry[]>([]);
  const [auditLoading, setAuditLoading] = useState(false);
  const [stats, setStats] = useState<{ total_users: number; total_agents: number; total_queries: number } | null>(null);
  const [editModal, setEditModal] = useState<AdminUser | null>(null);
  const [editForm] = Form.useForm();
  const [permsModal, setPermsModal] = useState<AdminUser | null>(null);
  const [perms, setPerms] = useState<string[]>([]);
  const [permsLoading, setPermsLoading] = useState(false);
  const [auditFilters, setAuditFilters] = useState<AuditFilters>({ limit: 100 });

  const fetchUsers = useCallback(async () => {
    setUsersLoading(true);
    try {
      const list = await adminListUsers();
      setUsers(list);
    } catch (e) {
      antMessage.error('No se pudo cargar la lista de usuarios.');
    } finally {
      setUsersLoading(false);
    }
  }, []);

  const fetchStats = useCallback(async () => {
    try {
      const s = await adminStats();
      setStats(s);
    } catch {
      setStats(null);
    }
  }, []);

  const fetchAudit = useCallback(async () => {
    setAuditLoading(true);
    try {
      const list = await adminAuditQueries(auditFilters);
      setAudit(list);
    } catch (e) {
      antMessage.error('No se pudo cargar la trazabilidad.');
    } finally {
      setAuditLoading(false);
    }
  }, [auditFilters]);

  useEffect(() => {
    fetchUsers();
    fetchStats();
  }, [fetchUsers, fetchStats]);

  const openEdit = (u: AdminUser) => {
    setEditModal(u);
    editForm.setFieldsValue({ role: u.role, is_active: u.is_active });
  };

  const handleEditOk = async () => {
    if (!editModal) return;
    try {
      const v = await editForm.validateFields();
      await adminUpdateUser(editModal.email, { role: v.role, is_active: v.is_active });
      antMessage.success('Usuario actualizado.');
      setEditModal(null);
      fetchUsers();
      fetchStats();
    } catch (e) {
      if (e && typeof e === 'object' && 'errorFields' in e) return;
      antMessage.error('No se pudo actualizar el usuario.');
    }
  };

  const openPerms = async (u: AdminUser) => {
    setPermsModal(u);
    setPermsLoading(true);
    try {
      const { permissions } = await adminListUserPermissions(u.email);
      setPerms(permissions);
    } catch {
      antMessage.error('No se pudieron cargar los permisos.');
      setPerms([]);
    } finally {
      setPermsLoading(false);
    }
  };

  const handleAddPerm = async (key: string) => {
    if (!permsModal) return;
    try {
      await adminAddPermission(permsModal.email, key);
      setPerms((prev) => (prev.includes(key) ? prev : [...prev, key]));
      antMessage.success('Permiso asignado.');
    } catch {
      antMessage.error('No se pudo asignar el permiso.');
    }
  };

  const handleRevokePerm = async (key: string) => {
    if (!permsModal) return;
    try {
      await adminRevokePermission(permsModal.email, key);
      setPerms((prev) => prev.filter((p) => p !== key));
      antMessage.success('Permiso revocado.');
    } catch {
      antMessage.error('No se pudo revocar el permiso.');
    }
  };

  const runAuditSearch = () => fetchAudit();

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          width: '100%',
          padding: '0 24px',
          background: '#001529',
        }}
      >
        <Space>
          <Link to="/" style={{ color: 'rgba(255,255,255,0.85)' }}>
            <MessageOutlined /> Chat
          </Link>
          <Text style={{ color: 'rgba(255,255,255,0.5)' }}>|</Text>
          <SettingOutlined style={{ color: 'rgba(255,255,255,0.85)' }} />
          <Title level={5} style={{ margin: 0, color: 'rgba(255,255,255,0.85)' }}>
            Administración
          </Title>
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
      <Content style={{ padding: 24, maxWidth: 1200, margin: '0 auto', width: '100%' }}>
        {stats && (
          <Space style={{ marginBottom: 16 }} wrap>
            <Tag color="blue">Usuarios: {stats.total_users}</Tag>
            <Tag color="green">Agentes: {stats.total_agents}</Tag>
            <Tag color="orange">Consultas: {stats.total_queries}</Tag>
          </Space>
        )}
        <Tabs
          onChange={(k) => { if (k === 'audit') fetchAudit(); }}
          items={[
            {
              key: 'users',
              label: 'Usuarios y permisos',
              children: (
                <Table<AdminUser>
                  loading={usersLoading}
                  dataSource={users}
                  rowKey="email"
                  columns={[
                    {
                      title: 'Email',
                      dataIndex: 'email',
                      key: 'email',
                      render: (v) => <Text strong>{v}</Text>,
                    },
                    {
                      title: 'Nombre',
                      dataIndex: 'name',
                      key: 'name',
                    },
                    {
                      title: 'Rol',
                      dataIndex: 'role',
                      key: 'role',
                      render: (v) => (
                        <Tag color={v === 'admin' ? 'red' : 'default'}>{v === 'admin' ? 'Admin' : 'Usuario'}</Tag>
                      ),
                    },
                    {
                      title: 'Activo',
                      dataIndex: 'is_active',
                      key: 'is_active',
                      render: (v) => (v ? <Tag color="green">Sí</Tag> : <Tag color="red">Bloqueado</Tag>),
                    },
                    {
                      title: 'Acciones',
                      key: 'actions',
                      render: (_, r) => (
                        <Space>
                          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>
                            Editar
                          </Button>
                          <Button type="link" size="small" icon={<KeyOutlined />} onClick={() => openPerms(r)}>
                            Permisos
                          </Button>
                        </Space>
                      ),
                    },
                  ]}
                  pagination={{ pageSize: 20 }}
                />
              ),
            },
            {
              key: 'audit',
              label: 'Trazabilidad',
              children: (
                <>
                  <Space style={{ marginBottom: 16 }} wrap>
                    <Input
                      placeholder="Filtrar por usuario (email)"
                      value={auditFilters.user_email ?? ''}
                      onChange={(e) => setAuditFilters((f) => ({ ...f, user_email: e.target.value || undefined }))}
                      style={{ width: 220 }}
                    />
                    <Input
                      placeholder="Filtrar por agent_id"
                      value={auditFilters.agent_id ?? ''}
                      onChange={(e) => setAuditFilters((f) => ({ ...f, agent_id: e.target.value || undefined }))}
                      style={{ width: 180 }}
                    />
                    <DatePicker.RangePicker
                      showTime
                      placeholder={['Desde', 'Hasta']}
                      onChange={(dates) => {
                        if (!dates || !dates[0] || !dates[1]) {
                          setAuditFilters((f) => ({ ...f, since: undefined, until: undefined }));
                        } else {
                          setAuditFilters((f) => ({
                            ...f,
                            since: dates[0]!.toISOString(),
                            until: dates[1]!.toISOString(),
                          }));
                        }
                      }}
                    />
                    <Select
                      placeholder="Límite"
                      value={auditFilters.limit ?? 100}
                      onChange={(v) => setAuditFilters((f) => ({ ...f, limit: v }))}
                      style={{ width: 100 }}
                      options={[
                        { value: 50, label: '50' },
                        { value: 100, label: '100' },
                        { value: 200, label: '200' },
                        { value: 500, label: '500' },
                      ]}
                    />
                    <Button type="primary" icon={<SearchOutlined />} onClick={runAuditSearch} loading={auditLoading}>
                      Buscar
                    </Button>
                  </Space>
                  <Table<AuditEntry>
                    loading={auditLoading}
                    dataSource={audit}
                    rowKey="id"
                    columns={[
                      { title: 'Usuario', dataIndex: 'user_email', key: 'user_email', width: 200 },
                      { title: 'Agent ID', dataIndex: 'agent_id', key: 'agent_id', width: 280, ellipsis: true },
                      {
                        title: 'Consulta',
                        dataIndex: 'user_input',
                        key: 'user_input',
                        ellipsis: true,
                        render: (v: string) => (v && v.length > 120 ? `${v.slice(0, 120)}…` : v),
                      },
                      {
                        title: 'Fecha',
                        dataIndex: 'created_at',
                        key: 'created_at',
                        width: 180,
                        render: (v: string) => new Date(v).toLocaleString('es-CO'),
                      },
                    ]}
                    pagination={{ pageSize: 20 }}
                  />
                </>
              ),
            },
          ]}
        />
        <Modal
          title="Editar usuario"
          open={!!editModal}
          onCancel={() => setEditModal(null)}
          onOk={handleEditOk}
          okText="Guardar"
        >
          {editModal && (
            <Form form={editForm} layout="vertical">
              <Form.Item label="Email">
                <Text>{editModal.email}</Text>
              </Form.Item>
              <Form.Item name="role" label="Rol" rules={[{ required: true }]}>
                <Select
                  options={[
                    { value: 'admin', label: 'Administrador' },
                    { value: 'user', label: 'Usuario' },
                  ]}
                />
              </Form.Item>
              <Form.Item name="is_active" label="Activo" valuePropName="checked">
                <Switch checkedChildren="Sí" unCheckedChildren="Bloqueado" />
              </Form.Item>
            </Form>
          )}
        </Modal>
        <Modal
          title={`Permisos: ${permsModal?.email ?? ''}`}
          open={!!permsModal}
          onCancel={() => setPermsModal(null)}
          footer={null}
        >
          {permsModal && (
            <div>
              <div style={{ marginBottom: 12 }}>
                <Text type="secondary">Asignados:</Text>
                {permsLoading ? (
                  <div>Cargando…</div>
                ) : (
                  <div style={{ marginTop: 8 }}>
                    {perms.length === 0 ? (
                      <Text type="secondary">Ninguno</Text>
                    ) : (
                      perms.map((p) => (
                        <Tag
                          key={p}
                          closable
                          onClose={() => handleRevokePerm(p)}
                          style={{ marginBottom: 4 }}
                        >
                          {PERM_OPTIONS.find((o) => o.value === p)?.label ?? p}
                        </Tag>
                      ))
                    )}
                  </div>
                )}
              </div>
              <div>
                <Text type="secondary">Añadir:</Text>
                <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {PERM_OPTIONS.filter((o) => !perms.includes(o.value)).map((o) => (
                    <Button
                      key={o.value}
                      size="small"
                      onClick={() => handleAddPerm(o.value)}
                    >
                      + {o.label}
                    </Button>
                  ))}
                  {PERM_OPTIONS.every((o) => perms.includes(o.value)) && (
                    <Text type="secondary">Todos asignados</Text>
                  )}
                </div>
              </div>
            </div>
          )}
        </Modal>
      </Content>
    </Layout>
  );
}
