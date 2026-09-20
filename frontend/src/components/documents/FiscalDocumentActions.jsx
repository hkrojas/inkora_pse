import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Download, Eye, RefreshCw, Share2, Mail, MessageCircle, Send, FileArchive, FileDiff, Truck, XCircle, Clock3 } from 'lucide-react';
import { api } from '../../lib/utils/api';
import { getEmissionOutcome } from '../../lib/utils/emissionJobs';
import { getFiscalDocumentStatus, hasFiscalDownload } from '../../lib/utils/documentArtifacts';
import { fiscalTrackingState } from '../../lib/utils/fiscalTracking';
import useFiscalTracking from '../../hooks/useFiscalTracking';
import ActionMenu from '../ui/ActionMenu';
import { useToast } from '../ui/Toast';
import Modal from '../ui/Modal';
import './fiscalDocumentActions.css';

export default function FiscalDocumentActions({ doc, allowGuides = true, reload, hideDetail = false }) {
  const toast = useToast();
  const submitting = useRef(false);
  const [actions, setActions] = useState(null);
  const [actionError, setActionError] = useState('');
  const [busy, setBusy] = useState('');
  const [confirm, setConfirm] = useState(null);
  const [reason, setReason] = useState('');
  const [showTracking, setShowTracking] = useState(false);
  const number = `${doc.serie}-${String(doc.correlativo).padStart(6, '0')}`;
  const accepted = getFiscalDocumentStatus(doc)?.kind === 'ok';
  const { job, error: trackingError, track, refresh } = useFiscalTracking(doc.id, reload);
  const trackingState = fiscalTrackingState(job || {}, doc.fiscal_status);
  const loadActions = useCallback(async (signal) => {
    setActions(null);
    setActionError('');
    try {
      const result = await api.get(`/facturas-emitidas/${doc.id}/acciones`, { signal });
      if (signal?.aborted) return;
      setActions(result);
      // Completed jobs are inspected on demand; active work resumes after reload.
      if (['queued', 'processing', 'retry', 'contingency_pending'].includes(result.job_status)) track(result);
      return result;
    } catch (error) {
      if (!signal?.aborted) setActionError(error.message || 'No se pudieron comprobar las acciones fiscales.');
    }
  }, [doc.id, track]);
  useEffect(() => {
    if (accepted || doc.estado === 'anulada') return undefined;
    const controller = new AbortController();
    loadActions(controller.signal);
    return () => controller.abort();
  }, [accepted, doc.estado, loadActions]);

  const run = async (key, task) => {
    if (submitting.current) return;
    submitting.current = true;
    setBusy(key);
    try { await task(); }
    catch (error) { toast(error.message || 'No se pudo completar la operación.', 'error'); }
    finally { submitting.current = false; setBusy(''); }
  };

  const pdf = (preview) => run(preview ? 'view' : 'pdf', async () => {
    const result = await api.getBlob(`/cotizaciones/${doc.id}/pdf/download`, { timeoutMs: 60000 });
    if (!result.contentType.includes('application/pdf')) {
      toast('El PDF sigue en preparación. Vuelve a intentarlo en unos segundos.', 'info');
      return;
    }
    const url = URL.createObjectURL(result.blob);
    if (preview) {
      const opened = window.open(url, '_blank');
      if (!opened) { URL.revokeObjectURL(url); throw new Error('Permite ventanas emergentes para ver el PDF o usa Descargar PDF.'); }
      opened.opener = null;
    } else {
      const link = document.createElement('a');
      link.href = url;
      link.download = /filename="?([^";]+)"?/i.exec(result.disposition)?.[1] || `${number}.pdf`;
      link.click();
    }
    window.setTimeout(() => URL.revokeObjectURL(url), 60000);
  });

  const download = (type) => run(type, async () => {
    const { blob } = await api.blob(`/facturacion/${type}`, { comprobante_id: doc.id });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${number}.${type === 'cdr' ? 'zip' : type}`;
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  });

  const share = (channel) => run(channel, async () => {
    const data = await api.get(`/cotizaciones/${doc.id}/compartir`);
    if (channel === 'copy') {
      if (!data.url_compartir) throw new Error('No se pudo preparar el enlace.');
      await navigator.clipboard.writeText(data.url_compartir);
      toast('Enlace copiado.', 'success');
      return;
    }
    if ((channel === 'whatsapp' || channel === 'both') && !data.whatsapp_link) throw new Error('El cliente no tiene WhatsApp válido.');
    if ((channel === 'email' || channel === 'both') && !data.mailto_link) throw new Error('El cliente no tiene correo registrado.');
    if (channel !== 'email') window.open(data.whatsapp_link, '_blank', 'noopener,noreferrer');
    if (channel !== 'whatsapp') window.location.href = data.mailto_link;
  });

  const artifacts = () => run('artifacts', async () => {
    const response = await api.post(`/facturacion/${doc.id}/artifacts/retry`, {}, { timeoutMs: 60000 });
    toast(response.message || 'Archivos recuperados.', response.ok ? 'success' : 'info');
    await reload();
  });

  const submit = () => run(confirm, async () => {
    if (confirm === 'retry') {
      const response = await api.post(`/facturas-emitidas/${doc.id}/reintentar`, {}, { timeoutMs: 60000 });
      const outcome = getEmissionOutcome(response);
      toast(outcome.message, outcome.toastType);
      track({ job_id: response.job_id, job_status: response.job_status, job_action: 'emit_fiscal_document' });
      setShowTracking(true);
    } else {
      const response = await api.post('/bajas/anular', { comprobante_id: doc.id, motivo: reason.trim() }, { timeoutMs: 60000 });
      track({ job_id: response.job_id, job_status: response.job_status, job_action: 'void_fiscal_document' });
      setShowTracking(true);
      toast('Solicitud de baja registrada. Revisa su resultado en Bajas.', 'info');
    }
    setConfirm(null);
    await loadActions();
  });

  const hasPdf = hasFiscalDownload(doc, 'pdf');
  return (
    <div className="fiscal-actions" aria-label={`Acciones de ${number}`}>
      {hasPdf && <>
        <button className="history-action-button history-action-button--brand" disabled={Boolean(busy)} onClick={() => pdf(true)} aria-label={`Ver PDF de ${number}`}><Eye size={15} /><span>Ver</span></button>
        <button className="history-action-button history-action-button--info" disabled={Boolean(busy)} onClick={() => pdf(false)} aria-label={`Descargar PDF de ${number}`}><Download size={15} /><span>PDF</span></button>
      </>}
      <ActionMenu label={`Más acciones de ${number}`} disabled={Boolean(busy)} onOpen={() => loadActions()}>
          <div className="ink-action-menu-title">{number}</div>
          {!hideDetail && <Link to={`/cotizaciones/${doc.id}`}><Eye />Ver detalle</Link>}
          {hasFiscalDownload(doc, 'xml') && <button onClick={() => download('xml')}><Download />Descargar XML</button>}
          {hasFiscalDownload(doc, 'cdr') && <button onClick={() => download('cdr')}><FileArchive />Descargar CDR</button>}
          <button onClick={async () => { const result = await loadActions(); track(result); setShowTracking(true); }}><Clock3 />Ver seguimiento fiscal</button>
          {!actions && !actionError && <p role="status">Comprobando acciones fiscales…</p>}
          {actionError && <><p role="alert">{actionError}</p><button data-keep-open onClick={() => loadActions()}><RefreshCw />Consultar acciones de nuevo</button></>}
          {actions && doc.estado !== 'anulada' && !accepted && <>
            <button disabled={!actions.retry_emission || trackingState.poll} aria-describedby={`retry-reason-${doc.id}`} onClick={() => setConfirm('retry')}><RefreshCw />{actions.retry_label || 'Reintentar envío fiscal'}</button>
            {!actions.retry_emission && <p id={`retry-reason-${doc.id}`}>{actions.retry_block_reason}</p>}
          </>}
          {actions?.retry_artifacts && <button onClick={artifacts}><RefreshCw />Reintentar archivos PDF/CDR</button>}
          {allowGuides && actions?.create_guide && <Link to={`/guias/nueva?comprobante_id=${doc.id}`}><Truck />Crear guía</Link>}
          {actions?.credit_note && <Link to={`/notas/nueva?documento=${doc.id}&tipo=credito`}><FileDiff />Crear nota de crédito</Link>}
          {actions?.debit_note && <Link to={`/notas/nueva?documento=${doc.id}&tipo=debito`}><FileDiff />Crear nota de débito</Link>}
          <div className="ink-action-menu-divider" />
          {hasPdf && <>
            <button onClick={() => share('copy')}><Share2 />Copiar enlace</button>
            <button onClick={() => share('whatsapp')}><MessageCircle />WhatsApp</button>
            <button onClick={() => share('email')}><Mail />Correo</button>
            <button onClick={() => share('both')}><Send />WhatsApp + correo</button>
          </>}
          {actions?.void && <button className="is-danger" onClick={() => { setReason(''); setConfirm('void'); }}><XCircle />Dar de baja</button>}
          <button onClick={() => run('reload', reload)}><RefreshCw />Actualizar lista</button>
      </ActionMenu>
      {job && trackingState.poll && <button className="fiscal-tracking-badge" onClick={() => setShowTracking(true)}><Clock3 size={13} />{trackingState.label}</button>}
      <Modal open={showTracking} onClose={() => setShowTracking(false)} title={`Seguimiento · ${number}`}>
        <p role="status">{trackingState.label}</p>
        {job?.last_error && <p className="mt-3">{job.last_error}</p>}
        {actions?.retry_block_reason && <p className="mt-3">{actions.retry_block_reason}</p>}
        {trackingError && <p role="alert" className="mt-3">{trackingError}</p>}
        <p className="mt-3">Esta vista consulta el trabajo guardado en Inkora; no reenvía ni realiza una conciliación con Smart PSE. Si el resultado es incierto, solicita revisión a soporte indicando {number}.</p>
        <button className="btn-secondary mt-4" onClick={async () => { const result = await loadActions(); track(result); refresh(); }}>Actualizar seguimiento</button>
      </Modal>
      <Modal open={Boolean(confirm)} onClose={() => { if (!busy) setConfirm(null); }} title={confirm === 'retry' ? (actions?.retry_label || 'Reintentar envío fiscal') : 'Solicitar baja'} footer={<>
        <button className="btn-secondary" disabled={Boolean(busy)} onClick={() => setConfirm(null)}>Cancelar</button>
        <button className={confirm === 'void' ? 'btn-danger' : 'btn-primary'} disabled={Boolean(busy) || (confirm === 'void' && !reason.trim())} onClick={submit}>{busy ? 'Procesando…' : 'Confirmar'}</button>
      </>}>
        <p>{number}</p>
        {confirm === 'retry' ? <p>Inkora comprobará nuevamente si el reintento está permitido y conservará la serie y el correlativo. La aceptación se confirma después del procesamiento.</p> : <label className="block mt-4">Motivo de baja<textarea className="input mt-2" value={reason} onChange={(event) => setReason(event.target.value)} maxLength={500} /></label>}
      </Modal>
    </div>
  );
}
