import { Button, Card, Layout, Space, Typography } from 'antd';
import { GoogleOutlined } from '@ant-design/icons';
import { useAuth } from '../auth/AuthContext';

const { Content } = Layout;
const { Title, Text } = Typography;

export default function Login() {
  const { login, loginLoading } = useAuth();

  return (
    <Layout style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%)' }}>
      <Content style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
        <Card
          style={{ maxWidth: 420, width: '100%', boxShadow: '0 4px 24px rgba(0,0,0,0.08)', borderRadius: 12 }}
          variant="borderless"
        >
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <div style={{ textAlign: 'center' }}>
              <Title level={3} style={{ marginBottom: 8 }}>RAG - Asistente Documental</Title>
              <Text type="secondary">Inicia sesión con tu cuenta de Google para consultar documentos.</Text>
            </div>
            <Button
              type="primary"
              size="large"
              icon={<GoogleOutlined />}
              onClick={() => void login()}
              loading={loginLoading}
              disabled={loginLoading}
              block
              style={{ height: 48, fontSize: 16 }}
            >
              Continuar con Google
            </Button>
          </Space>
        </Card>
      </Content>
    </Layout>
  );
}
