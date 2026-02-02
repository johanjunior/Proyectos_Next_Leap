import { useEffect, useState } from 'react';
import { Col, Modal, Row, Spin, Typography } from 'antd';
import { getPdfBlob } from '../api/client';
import type { Source } from '../types';

const { Text } = Typography;

interface PdfViewerModalProps {
  source: Source;
  open: boolean;
  onClose: () => void;
}

export default function PdfViewerModal({ source, open, onClose }: PdfViewerModalProps) {
  const [pdfBlobUrl, setPdfBlobUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch PDF via backend proxy (temp file on server, then stream) so the browser
  // displays it in the iframe without triggering a download. Download only when
  // user clicks "Abrir en nueva pestaña" or the link icon next to the button.
  useEffect(() => {
    if (!open || !source.signed_url) {
      setPdfBlobUrl(null);
      setError(null);
      return;
    }
    let revoked = false;
    setLoading(true);
    setError(null);
    getPdfBlob(source.signed_url)
      .then((blob) => {
        if (revoked) return;
        const url = URL.createObjectURL(blob);
        setPdfBlobUrl(url);
      })
      .catch((err) => {
        if (revoked) return;
        setError(err?.response?.data?.detail ?? err?.message ?? 'Error al cargar el PDF');
      })
      .finally(() => {
        if (!revoked) setLoading(false);
      });
    return () => {
      revoked = true;
      setPdfBlobUrl((prev) => {
        if (prev) URL.revokeObjectURL(prev);
        return null;
      });
    };
  }, [open, source.signed_url]);

  const title = <span>📄 {source.document_name}</span>;

  return (
    <Modal
      title={title}
      open={open}
      onCancel={onClose}
      footer={null}
      width="90%"
      style={{ top: 24 }}
      destroyOnClose
    >
      <Row gutter={[16, 16]}>
        {(source.page_number != null || source.score != null) && (
          <Col span={24}>
            <Text type="secondary">
              {source.page_number != null && `📍 Página: ${source.page_number}`}
              {source.page_number != null && source.score != null && ' · '}
              {source.score != null && (
                <>🎯 Relevancia: {typeof source.score === 'number' ? `${Math.round(source.score * 100)}%` : source.score}</>
              )}
            </Text>
          </Col>
        )}
        {source.snippet && (
          <Col span={24}>
            <details>
              <summary style={{ cursor: 'pointer', color: '#1890ff' }}>Fragmento relevante</summary>
              <pre
                style={{
                  marginTop: 8,
                  padding: 12,
                  background: '#f5f5f5',
                  borderRadius: 8,
                  maxHeight: 120,
                  overflow: 'auto',
                  fontSize: 12,
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                }}
              >
                {source.snippet.slice(0, 800)}
                {source.snippet.length > 800 ? '...' : ''}
              </pre>
            </details>
          </Col>
        )}
        <Col span={24}>
          {!source.signed_url ? (
            <Text type="secondary">URL del documento no disponible.</Text>
          ) : loading ? (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 400 }}>
              <Spin size="large" tip="Cargando PDF..." />
            </div>
          ) : error ? (
            <Text type="danger">{error}</Text>
          ) : pdfBlobUrl ? (
            <iframe
              title={source.document_name}
              src={source.page_number ? `${pdfBlobUrl}#page=${source.page_number}` : pdfBlobUrl}
              width="100%"
              height={600}
              style={{ border: '1px solid #e8e8e8', borderRadius: 8 }}
            />
          ) : null}
        </Col>
        {source.signed_url && (
          <Col span={24}>
            <a href={source.signed_url} target="_blank" rel="noopener noreferrer">
              Abrir en nueva pestaña
            </a>
          </Col>
        )}
      </Row>
    </Modal>
  );
}
