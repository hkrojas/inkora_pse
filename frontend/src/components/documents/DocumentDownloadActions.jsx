import { useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Download, Eye, FileArchive } from 'lucide-react';
import { api } from '../../lib/utils/api';
import { hasFiscalDownload } from '../../lib/utils/documentArtifacts';
import ActionMenu from '../ui/ActionMenu';
import { useToast } from '../ui/Toast';
import './fiscalDocumentActions.css';

export default function DocumentDownloadActions({ document: record, guide = false }) {
  const toast = useToast();
  const submitting = useRef(false);
  const [busy, setBusy] = useState('');
  const number = record.document_number || `${record.serie}-${String(record.correlativo).padStart(6, '0')}`;
  const available = guide
    ? { pdf: true, xml: Boolean(record.xml_disponible), cdr: Boolean(record.cdr_disponible) }
    : Object.fromEntries(['pdf', 'xml', 'cdr'].map((type) => [type, hasFiscalDownload(record, type)]));

  const download = async (type, preview = false) => {
    if (submitting.current) return;
    submitting.current = true;
    setBusy(preview ? 'view' : type);
    try {
      const result = guide
        ? await api.download(`/guias-remision/${record.id}/${type}`, { timeoutMs: 60000 })
        : type === 'pdf'
          ? await api.getBlob(`/cotizaciones/${record.id}/pdf/download`, { timeoutMs: 60000 })
          : await api.blob(`/facturacion/${type}`, { comprobante_id: record.id }, { timeoutMs: 60000 });
      if (type === 'pdf' && !result.contentType.includes('application/pdf')) {
        toast('El PDF sigue en preparación. Vuelve a intentarlo en unos segundos.', 'info');
        return;
      }
      const extension = type === 'cdr' ? (guide ? 'xml' : 'zip') : type;
      const fallback = `${guide && type === 'cdr' ? 'R-' : ''}${number}.${extension}`;
      const url = URL.createObjectURL(result.blob);
      if (preview) {
        const opened = window.open(url, '_blank');
        if (!opened) {
          URL.revokeObjectURL(url);
          throw new Error('Permite ventanas emergentes para ver el PDF o usa Descargar PDF.');
        }
        opened.opener = null;
      } else {
        const link = document.createElement('a');
        link.href = url;
        link.download = /filename="?([^";]+)"?/i.exec(result.disposition)?.[1] || fallback;
        document.body.appendChild(link);
        link.click();
        link.remove();
      }
      window.setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch (error) {
      toast(error.message || 'No se pudo descargar el archivo. Inténtalo de nuevo.', 'error');
    } finally {
      submitting.current = false;
      setBusy('');
    }
  };

  return <div className="fiscal-actions document-download-actions" aria-label={`Archivos de ${number}`}>
    {guide
      ? <Link to={`/guias/${record.id}`} className="history-action-button history-action-button--brand" aria-label={`Ver guía ${number}`}><Eye size={15} aria-hidden="true" /><span>Ver</span></Link>
      : available.pdf && <button type="button" className="history-action-button history-action-button--brand" disabled={Boolean(busy)} aria-label={`Ver PDF de ${number}`} onClick={() => download('pdf', true)}><Eye size={15} aria-hidden="true" /><span>Ver</span></button>}
    {available.pdf
      ? <button type="button" className="history-action-button history-action-button--info" disabled={Boolean(busy)} aria-label={`Descargar PDF de ${number}`} onClick={() => download('pdf')}><Download size={15} aria-hidden="true" /><span>{busy === 'pdf' ? 'Descargando…' : 'PDF'}</span></button>
      : <span className="text-sm text-[var(--color-text-muted)]">{record.estado === 'anulada' ? 'PDF no disponible' : 'PDF en preparación'}</span>}
    {(available.xml || available.cdr) && <ActionMenu label={`Otros archivos de ${number}`} disabled={Boolean(busy)}>
      {available.xml && <button type="button" onClick={() => download('xml')}><Download aria-hidden="true" />Descargar XML</button>}
      {available.cdr && <button type="button" onClick={() => download('cdr')}><FileArchive aria-hidden="true" />Descargar CDR</button>}
    </ActionMenu>}
  </div>;
}
