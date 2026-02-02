import { Button, Space, Typography } from 'antd';
import { FileTextOutlined, LinkOutlined } from '@ant-design/icons';
import { useState } from 'react';
import type { Source } from '../types';
import PdfViewerModal from './PdfViewerModal';

const { Text } = Typography;

const MAX_SOURCE_LABEL_LENGTH = 60; // caracteres antes de truncar con ellipsis

function truncateLabel(name: string, pageNumber?: number): string {
  const suffix = pageNumber != null ? ` (pág. ${pageNumber})` : '';
  const maxNameLen = MAX_SOURCE_LABEL_LENGTH - suffix.length;
  if (name.length <= maxNameLen) return name + suffix;
  return name.slice(0, maxNameLen).trim() + '…' + suffix;
}

export default function SourceList({ sources, messageIndex }: SourceListProps) {
  const [modalSource, setModalSource] = useState<Source | null>(null);

  if (!sources.length) return null;

  return (
    <>
      <div style={{ marginTop: 8 }}>
        <Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>
          📚 Fuentes documentales ({sources.length})
        </Text>
        <Space wrap size="small">
          {sources.map((source, i) => (
            <Space key={`${messageIndex}-${i}-${source.document_id}`} wrap>
              <Button
                type="default"
                size="small"
                icon={<FileTextOutlined />}
                onClick={() => setModalSource(source)}
                title={source.document_name + (source.page_number ? ` (pág. ${source.page_number})` : '')}
                style={{
                  maxWidth: 320,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                }}
              >
                <span
                  style={{
                    display: 'inline-block',
                    maxWidth: 260,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                    verticalAlign: 'bottom',
                  }}
                >
                  {truncateLabel(source.document_name, source.page_number)}
                </span>
              </Button>
              {source.score != null && (
                <Text type="secondary" style={{ fontSize: 12 }}>
                  🎯 {typeof source.score === 'number' ? `${Math.round(source.score * 100)}%` : source.score}
                </Text>
              )}
              {source.signed_url && (
                <Button
                  type="link"
                  size="small"
                  icon={<LinkOutlined />}
                  href={source.signed_url}
                  target="_blank"
                  rel="noopener noreferrer"
                />
              )}
            </Space>
          ))}
        </Space>
      </div>
      {modalSource && (
        <PdfViewerModal
          source={modalSource}
          open={!!modalSource}
          onClose={() => setModalSource(null)}
        />
      )}
    </>
  );
}
