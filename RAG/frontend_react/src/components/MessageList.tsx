import { List, Typography } from 'antd';
import { UserOutlined, RobotOutlined } from '@ant-design/icons';
import type { ChatMessage as ChatMessageType } from '../types';
import SourceList from './SourceList';

const { Text } = Typography;

interface MessageListProps {
  messages: ChatMessageType[];
}

export default function MessageList({ messages }: MessageListProps) {
  if (!messages.length) return null;

  return (
    <List
      dataSource={messages}
      itemLayout="vertical"
      style={{ paddingBottom: 16 }}
      renderItem={(msg, index) => (
        <List.Item
          key={`msg-${index}`}
          style={{
            padding: '12px 16px',
            background: msg.role === 'user' ? '#f0f5ff' : '#fafafa',
            borderRadius: 8,
            marginBottom: 8,
            border: '1px solid #e8e8e8',
          }}
        >
          <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
            <div style={{ marginTop: 2 }}>
              {msg.role === 'user' ? (
                <UserOutlined style={{ fontSize: 18, color: '#1890ff' }} />
              ) : (
                <RobotOutlined style={{ fontSize: 18, color: '#52c41a' }} />
              )}
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <Text strong style={{ display: 'block', marginBottom: 4 }}>
                {msg.role === 'user' ? 'Tú' : 'Asistente'}
              </Text>
              <div style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{msg.content}</div>
              {msg.role === 'assistant' && msg.sources && msg.sources.length > 0 && (
                <div style={{ marginTop: 12 }}>
                  <SourceList sources={msg.sources} messageIndex={index} />
                </div>
              )}
            </div>
          </div>
        </List.Item>
      )}
    />
  );
}
