import { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, CheckCircle2, Download, MapPin, Package, Pencil, RefreshCw, ShieldCheck, Truck, XCircle } from 'lucide-react';
import { guias as svc } from '../services/guias';
import { internalTransfers } from '../services/internalTransfers';
import Spinner from '../components/ui/Spinner';
import Badge from '../components/ui/Badge';
import { useToast } from '../components/ui/Toast';
import { getDispatchReservationLabel, getGuideStatusMeta } from '../lib/utils/fiscalStatus';
import { getGuideEmissionJobCompletion, getGuideEmissionJobLabel } from '../lib/utils/emissionJobs';

const MOTIVO_LABEL = {
  '01': 'Venta',
  '02': 'Compra',
  '04': 'Traslado entre establecimientos',
  '13': 'Otros',
};

const MODALIDAD_LABEL = {
  '01': 'Transporte público',
  '02': 'Transporte privado',
};

const transportScenarioLabel = (guide) => {
  if (guide.indicador_m1_l) return 'Vehículo M1/L · sin conductor';
  if (guide.modalidad_traslado === '01' && guide.registrar_vehiculo_transportista) return 'Público · vehículo y conductor registrados';
  if (guide.modalidad_traslado === '01') return 'Público · requiere GRE 31';
  return 'Privado · vehículo y conductor';
};

export default function GuiaDetalle() {
  const { id } = useParams();
  const toast = useToast();
  const [guia, setGuia] = useState(null);
  const [loading, setLoading] = useState(true);
  const [emissionJob, setEmissionJob] = useState(null);
  const [emitting, setEmitting] = useState(false);
  const [workingAction, setWorkingAction] = useState(null);
  const [validationResult, setValidationResult] = useState(null);
  const [showCarrierForm, setShowCarrierForm] = useState(false);
  const [showVerificationForm, setShowVerificationForm] = useState(false);
  const [carrierForm, setCarrierForm] = useState({ issuer_ruc: '', series: 'V001', number: '' });
  const [verificationForm, setVerificationForm] = useState({
    environment: 'demo', provider_document_name: '', signed_xml: '', cdr: '', note: '',
  });

  const loadGuide = useCallback(async ({ silent = false } = {}) => {
    if (!silent) setLoading(true);
    try {
      const next = await svc.get(id);
      setGuia(next);
      setEmissionJob(next.emission_job || null);
      return next;
    } catch (error) {
      toast(error.message || 'No se pudo cargar la guía. Revisa tu conexión e inténtalo nuevamente.', 'error');
      return null;
    } finally {
      if (!silent) setLoading(false);
    }
  }, [id, toast]);

  useEffect(() => { loadGuide(); }, [loadGuide]);

  const jobIsActive = ['queued', 'processing', 'retry'].includes(emissionJob?.status);

  useEffect(() => {
    if (!emissionJob?.id || !jobIsActive) return undefined;
    const timer = window.setInterval(async () => {
      try {
        const nextJob = await svc.getEmissionJob(emissionJob.id);
        setEmissionJob(nextJob);
        if (!['queued', 'processing', 'retry'].includes(nextJob.status)) {
          setEmitting(false);
          await loadGuide({ silent: true });
          const completion = getGuideEmissionJobCompletion(nextJob);
          toast(completion.message, completion.toastType);
        }
      } catch (error) {
        setEmitting(false);
        toast(error.message || 'No se pudo consultar el estado de emisión.', 'error');
      }
    }, 2000);
    return () => window.clearInterval(timer);
  }, [emissionJob?.id, jobIsActive, loadGuide, toast]);

  const runAction = async (name, action, successMessage) => {
    setWorkingAction(name);
    try {
      const result = await action();
      if (result?.job_id) setEmissionJob({ id: result.job_id, status: result.job_status });
      await loadGuide({ silent: true });
      if (successMessage) toast(successMessage, 'success');
      return result;
    } catch (error) {
      toast(error.message || 'No se pudo completar la operación.', 'error');
      return null;
    } finally {
      setWorkingAction(null);
    }
  };

  const handleValidate = async () => {
    setWorkingAction('validate');
    try {
      const result = await svc.validate(id);
      setValidationResult(result);
      toast(result.valid ? 'La guía está lista para emitir.' : 'La guía contiene datos por corregir.', result.valid ? 'success' : 'error');
    } catch (error) {
      toast(error.message || 'No se pudo validar la guía.', 'error');
    } finally { setWorkingAction(null); }
  };

  const handleCancel = async () => {
    if (!window.confirm('Se cancelará el borrador y se liberarán sus cantidades. ¿Deseas continuar?')) return;
    await runAction('cancel', () => svc.cancelDraft(id), 'Borrador cancelado y cantidades liberadas.');
  };

  const handleReconcile = async () => {
    await runAction('consult', () => svc.reconcile(id), 'Consulta fiscal encolada sin reenviar la guía.');
  };

  const handleDeparture = async () => {
    if (!window.confirm('¿Confirmas que los bienes salieron físicamente? Esta acción es operativa e idempotente.')) return;
    await runAction(
      'departure',
      () => guia.internal_transfer_dispatch_id
        ? internalTransfers.confirmDeparture(guia.internal_transfer_dispatch_id, `internal-departure-${guia.internal_transfer_dispatch_id}`)
        : svc.confirmDeparture(guia.dispatch_id, `departure-${guia.dispatch_id}`),
      'Salida física confirmada.',
    );
  };

  const handleExternalCarrier = async (event) => {
    event.preventDefault();
    const result = await runAction('carrier', () => svc.registerExternalCarrier(id, {
      document_type: '31',
      issuer_ruc: carrierForm.issuer_ruc,
      series: carrierForm.series.toUpperCase(),
      number: carrierForm.number,
    }), 'GRE transportista registrada; falta verificar su XML y CDR.');
    if (result) setShowCarrierForm(false);
  };

  const handleVerification = async (event) => {
    event.preventDefault();
    const result = await runAction(
      'verification',
      () => svc.verifyExternalReference(id, verificationForm),
      'Referencia GRE verificada con XML y CDR coincidentes.',
    );
    if (result) setShowVerificationForm(false);
  };

  const handleEmit = async () => {
    if (!window.confirm('La guía se enviará a SUNAT y no podrá editarse. ¿Deseas continuar?')) return;
    setEmitting(true);
    try {
      const queued = await svc.emitir(id);
      setEmissionJob({ id: queued.job_id, status: queued.job_status });
      toast('Guía encolada para emisión fiscal.', 'info');
    } catch (error) {
      setEmitting(false);
      toast(error.message || 'No se pudo encolar la guía para emisión.', 'error');
    }
  };

  const handleDownload = async (type) => {
    try {
      const { blob, disposition } = await svc.download(id, type);
      const fallback = `${type === 'cdr' ? 'R-' : ''}${guia.serie}-${String(guia.correlativo).padStart(6, '0')}.${type === 'pdf' ? 'pdf' : 'xml'}`;
      const filename = disposition.match(/filename=\"?([^\";]+)\"?/i)?.[1] || fallback;
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (error) {
      toast(error.message || 'No se pudo descargar el archivo fiscal.', 'error');
    }
  };

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!guia) {
    return (
      <div className="page-shell">
        <Link to="/guias" className="guide-back-link">
          <ArrowLeft className="h-4 w-4" />
          Volver a guías
        </Link>
        <p className="text-sm text-[var(--text-secondary)]">Guía no encontrada.</p>
      </div>
    );
  }

  const numero =
    guia.serie && guia.correlativo != null
      ? `${guia.serie}-${String(guia.correlativo).padStart(6, '0')}`
      : `#${guia.id}`;

  const fmt = (value) => (value ? new Date(value).toLocaleDateString('es-PE') : '--');
  const statusMeta = getGuideStatusMeta(guia);
  const jobLabel = getGuideEmissionJobLabel(emissionJob);
  const hasFiscalEvidence = Boolean(statusMeta.provider === 'smartpse' || guia.cdr_disponible || guia.sunat_hash || guia.sunat_ticket);

  return (
    <div className="page-shell max-w-5xl guide-detail-page">
      <div className="page-header">
        <div className="page-header-copy">
          <Link to="/guias" className="guide-back-link">
            <ArrowLeft className="h-4 w-4" />
            Volver a guías
          </Link>
          <p className="page-kicker">Seguimiento de despacho</p>
          <h2 className="page-title">Guía {numero}</h2>
          <p className="page-subtitle">
            Fecha documento: {fmt(guia.fecha_emision)} · Traslado: {fmt(guia.fecha_traslado)}
          </p>
        </div>

        <div className="page-actions guide-detail-actions">
          <Badge variant={statusMeta.badgeVariant}>{statusMeta.label}</Badge>
          <button type="button" className="btn-secondary" onClick={() => handleDownload('pdf')}><Download size={15} />Descargar PDF</button>
          {guia.actions?.validate?.enabled && (
            <button type="button" className="btn-secondary" onClick={handleValidate} disabled={workingAction === 'validate'}>
              <CheckCircle2 size={15} />Validar
            </button>
          )}
          {guia.actions?.edit?.enabled && (
            <Link to={`/guias/${guia.id}/editar`} className="btn-secondary"><Pencil size={15} />Editar borrador</Link>
          )}
          {guia.actions?.cancel?.enabled && (
            <button type="button" className="btn-secondary" onClick={handleCancel} disabled={workingAction === 'cancel'}>
              <XCircle size={15} />Cancelar borrador
            </button>
          )}
          {guia.actions?.consult?.enabled && (
            <button type="button" className="btn-primary" onClick={handleReconcile} disabled={workingAction === 'consult'}>
              <RefreshCw size={15} />Consultar resultado
            </button>
          )}
          {guia.actions?.confirm_departure?.enabled && (
            <button type="button" className="btn-primary" onClick={handleDeparture} disabled={workingAction === 'departure'}>
              <Truck size={15} />Confirmar salida
            </button>
          )}
          {guia.actions?.emit?.enabled && (
            <button type="button" className="btn-primary" onClick={handleEmit} disabled={emitting || jobIsActive}>
              {emitting || jobIsActive ? <Spinner size="sm" /> : <Truck className="h-4 w-4" />}
              {jobIsActive ? 'Emisión en curso' : 'Emitir a SUNAT'}
            </button>
          )}
        </div>
      </div>

      <div className="guide-status-rail" aria-label="Estado de la guía y del despacho">
        <div className="guide-status-rail__item">
          <p className="label">Resultado fiscal</p>
          <p className="mt-1 text-sm font-semibold text-[var(--text-primary)]">{statusMeta.label}</p>
        </div>
        <div className="guide-status-rail__item">
          <p className="label">Reserva de despacho</p>
          <p className="mt-1 text-sm font-semibold text-[var(--text-primary)]">{getDispatchReservationLabel(guia.reservation_status)}</p>
        </div>
        <div className="guide-status-rail__item">
          <p className="label">Salida física</p>
          <p className="mt-1 text-sm font-semibold text-[var(--text-primary)]">
            {guia.departure_confirmed_at ? `Confirmada el ${fmt(guia.departure_confirmed_at)}` : 'Pendiente'}
          </p>
        </div>
      </div>

      {validationResult && (
        <div className={`ink-card p-4 text-sm ${validationResult.valid ? 'text-[var(--color-success)]' : 'text-[var(--color-error)]'}`}>
          <strong>{validationResult.valid ? 'Validación correcta' : 'Datos por corregir'}</strong>
          {!validationResult.valid && (
            <ul className="mt-2 list-disc space-y-1 pl-5">
              {validationResult.errors.map((error) => <li key={`${error.field}-${error.code}`}>{error.message}</li>)}
            </ul>
          )}
        </div>
      )}

      {jobLabel && (
        <div className={`ink-card p-4 text-sm ${emissionJob?.status === 'failed' ? 'text-[var(--color-error)]' : 'text-[var(--text-secondary)]'}`}>
          <strong>{jobLabel}</strong>
          {emissionJob?.last_error && <p className="mt-1">{emissionJob.last_error}</p>}
        </div>
      )}

      {guia.external_gre_reference && (
        <div className="ink-card p-5 guide-detail-section">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="ink-card-title flex items-center gap-2"><ShieldCheck size={16} />Referencia GRE externa</h3>
              <p className="mt-2 text-sm text-[var(--text-secondary)]">
                {guia.external_gre_reference.document_type} · {guia.external_gre_reference.issuer_ruc} · {guia.external_gre_reference.series}-{guia.external_gre_reference.number}
              </p>
            </div>
            <Badge variant={guia.external_gre_reference.verification_status === 'verified' ? 'success' : 'warning'}>
              {guia.external_gre_reference.verification_status === 'verified' ? 'Verificada' : 'Sin verificar'}
            </Badge>
          </div>
          {guia.actions?.verify_external_reference?.enabled && (
            <button type="button" className="btn-secondary mt-4" onClick={() => setShowVerificationForm((value) => !value)}>
              Verificar XML y CDR
            </button>
          )}
          {showVerificationForm && (
            <form onSubmit={handleVerification} className="mt-4 grid gap-4">
              <div className="grid gap-4 md:grid-cols-2">
                <label><span className="label">Ambiente</span><select className="input" value={verificationForm.environment} onChange={(event) => setVerificationForm((current) => ({ ...current, environment: event.target.value }))}><option value="demo">Demo</option><option value="production">Producción</option></select></label>
                <label><span className="label">Nombre en proveedor</span><input className="input" value={verificationForm.provider_document_name} onChange={(event) => setVerificationForm((current) => ({ ...current, provider_document_name: event.target.value }))} /></label>
              </div>
              <label><span className="label">XML firmado</span><textarea className="input min-h-32 font-mono text-xs" required value={verificationForm.signed_xml} onChange={(event) => setVerificationForm((current) => ({ ...current, signed_xml: event.target.value }))} /></label>
              <label><span className="label">CDR XML o Base64</span><textarea className="input min-h-32 font-mono text-xs" required value={verificationForm.cdr} onChange={(event) => setVerificationForm((current) => ({ ...current, cdr: event.target.value }))} /></label>
              <label><span className="label">Nota de revisión</span><textarea className="input" required minLength={10} value={verificationForm.note} onChange={(event) => setVerificationForm((current) => ({ ...current, note: event.target.value }))} /></label>
              <button type="submit" className="btn-primary justify-self-start" disabled={workingAction === 'verification'}>{workingAction === 'verification' ? <Spinner size="sm" /> : <ShieldCheck size={15} />}Verificar evidencia</button>
            </form>
          )}
        </div>
      )}

      {guia.actions?.register_external_carrier?.enabled && (
        <div className="ink-card p-5 guide-detail-section">
          <h3 className="ink-card-title">GRE transportista recibida</h3>
          <p className="mt-2 text-sm text-[var(--text-secondary)]">Registra el documento 31 entregado por el transportista. Después un administrador deberá verificar su XML y CDR.</p>
          <button type="button" className="btn-secondary mt-4" onClick={() => setShowCarrierForm((value) => !value)}>Registrar GRE 31</button>
          {showCarrierForm && (
            <form onSubmit={handleExternalCarrier} className="mt-4 grid gap-4 md:grid-cols-3">
              <label><span className="label">RUC transportista</span><input className="input" required pattern="\d{11}" value={carrierForm.issuer_ruc} onChange={(event) => setCarrierForm((current) => ({ ...current, issuer_ruc: event.target.value }))} /></label>
              <label><span className="label">Serie</span><input className="input uppercase" required minLength={4} maxLength={4} value={carrierForm.series} onChange={(event) => setCarrierForm((current) => ({ ...current, series: event.target.value }))} /></label>
              <label><span className="label">Número</span><input className="input" required pattern="\d{1,8}" value={carrierForm.number} onChange={(event) => setCarrierForm((current) => ({ ...current, number: event.target.value }))} /></label>
              <button type="submit" className="btn-primary justify-self-start md:col-span-3" disabled={workingAction === 'carrier'}>Guardar referencia</button>
            </form>
          )}
        </div>
      )}

      {hasFiscalEvidence && (
        <div className="ink-card p-5 smartpse-evidence-card">
          <div className="smartpse-evidence-head">
            <div>
              <h3 className="ink-card-title flex items-center gap-2">
                <Truck className="h-4 w-4 text-[var(--text-brand)]" />
                Smart PSE
              </h3>
              <p className="mt-2 text-sm text-[var(--text-secondary)]">
                {guia.cdr_disponible
                  ? 'XML firmado y CDR definitivo disponibles.'
                  : 'XML firmado por Smart PSE; CDR pendiente.'}
              </p>
            </div>
            <Badge variant={guia.cdr_disponible ? 'success' : 'warning'}>
              {guia.cdr_disponible ? 'CDR disponible' : 'CDR pendiente'}
            </Badge>
          </div>

          <div className="smartpse-evidence-grid">
            <div className="smartpse-evidence-item">
              <p className="label">Hash</p>
              <p className="smartpse-evidence-value" title={guia.sunat_hash || ''}>
                {guia.sunat_hash || '--'}
              </p>
            </div>
            <div className="smartpse-evidence-item">
              <p className="label">Ticket</p>
              <p className="smartpse-evidence-value" title={guia.sunat_ticket || ''}>
                {guia.sunat_ticket || '--'}
              </p>
            </div>
            <div className="smartpse-evidence-item">
              <p className="label">CDR</p>
              {guia.cdr_disponible ? (
                <button type="button" onClick={() => handleDownload('cdr')} className="smartpse-evidence-link">
                  Descargar CDR
                </button>
              ) : (
                <p className="smartpse-evidence-state">CDR pendiente</p>
              )}
            </div>
            {guia.xml_disponible && (
              <div className="smartpse-evidence-item">
                <p className="label">XML firmado</p>
                <button type="button" onClick={() => handleDownload('xml')} className="smartpse-evidence-link">
                  Descargar XML
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="ink-card p-5 guide-detail-section">
          <h3 className="ink-card-title flex items-center gap-2">
            <Truck className="h-4 w-4 text-[var(--text-brand)]" />
            Traslado
          </h3>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <div>
              <p className="label">Motivo</p>
              <p className="text-sm text-[var(--text-primary)]">
                {MOTIVO_LABEL[guia.motivo_traslado] || guia.motivo_traslado}{' '}
                {guia.descripcion_motivo ? `· ${guia.descripcion_motivo}` : ''}
              </p>
            </div>
            <div>
              <p className="label">Modalidad</p>
              <p className="text-sm text-[var(--text-primary)]">
                {MODALIDAD_LABEL[guia.modalidad_traslado] || guia.modalidad_traslado}
              </p>
              <p className="mt-1 text-xs text-[var(--text-secondary)]">{transportScenarioLabel(guia)}</p>
            </div>
            <div>
              <p className="label">Peso bruto</p>
              <p className="text-sm text-[var(--text-primary)]">
                {guia.peso_bruto_total} {guia.unidad_medida_peso}
              </p>
            </div>
            {guia.internal_order_number && (
              <div>
                <p className="label">{guia.internal_transfer_id ? 'Traslado interno' : 'Orden'}</p>
                <Link to={guia.internal_transfer_id ? `/traslados-internos/${guia.internal_transfer_id}` : `/cotizaciones/${guia.cotizacion_id}`} className="text-sm text-[var(--text-brand)] underline">
                  {guia.internal_order_number}
                </Link>
              </div>
            )}
            {guia.observaciones && <div className="md:col-span-2"><p className="label">Observaciones</p><p className="text-sm text-[var(--text-primary)]">{guia.observaciones}</p></div>}
          </div>
        </div>

        <div className="ink-card p-5">
          <h3 className="ink-card-title flex items-center gap-2">
            <MapPin className="h-4 w-4 text-[var(--text-brand)]" />
            Ruta
          </h3>
          <div className="mt-4 grid gap-6 md:grid-cols-2">
            <div>
              <p className="label">Origen</p>
              <p className="text-sm text-[var(--text-primary)]">{guia.partida_direccion || '--'}</p>
              {guia.partida_ubigeo && (
                <p className="mt-1 text-xs text-[var(--text-secondary)]">Ubigeo: {guia.partida_ubigeo}</p>
              )}
            </div>
            <div>
              <p className="label">Destino</p>
              <p className="text-sm text-[var(--text-primary)]">{guia.llegada_direccion || '--'}</p>
              {guia.llegada_ubigeo && (
                <p className="mt-1 text-xs text-[var(--text-secondary)]">Ubigeo: {guia.llegada_ubigeo}</p>
              )}
            </div>
          </div>
        </div>
      </div>

      {(guia.transportista_ruc || guia.conductor_nro_doc || guia.vehiculo_placa) && (
        <div className="ink-card p-5">
          <h3 className="ink-card-title">Transportista</h3>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            {guia.transportista_ruc && (
              <div>
                <p className="label">RUC transportista</p>
                <p className="text-sm text-[var(--text-primary)]">
                  {guia.transportista_ruc}
                  {guia.transportista_razon_social ? ` · ${guia.transportista_razon_social}` : ''}
                </p>
              </div>
            )}
            {guia.conductor_nro_doc && (
              <div>
                <p className="label">Conductor</p>
                <p className="text-sm text-[var(--text-primary)]">
                  {[guia.conductor_nombres, guia.conductor_apellidos].filter(Boolean).join(' ') ||
                    guia.conductor_nro_doc}
                </p>
                <p className="mt-1 text-xs text-[var(--text-secondary)]">Doc. tipo {guia.conductor_tipo_doc || '1'}: {guia.conductor_nro_doc}</p>
                {guia.conductor_licencia && (
                  <p className="mt-1 text-xs text-[var(--text-secondary)]">
                    Licencia: {guia.conductor_licencia}
                  </p>
                )}
              </div>
            )}
            {guia.vehiculo_placa && (
              <div>
                <p className="label">Vehículo</p>
                <p className="font-mono-label text-sm text-[var(--text-primary)]">
                  {guia.vehiculo_placa}
                </p>
              </div>
            )}
            {guia.transportista_acuerdo_confirmado_at && <div><p className="label">Acuerdo con transportista</p><p className="text-sm text-[var(--color-success)]">Confirmado y auditado</p></div>}
          </div>
        </div>
      )}

      {guia.items && guia.items.length > 0 && (
        <div className="ink-table-card">
          <div className="ink-card-header">
            <div>
                <h3 className="ink-card-title flex items-center gap-2">
                <Package className="h-4 w-4 text-[var(--text-brand)]" />
                Bienes a trasladar
              </h3>
              <p className="ink-card-subtitle">{guia.items.length} {guia.items.length === 1 ? 'bien incluido' : 'bienes incluidos'} en la guía</p>
            </div>
          </div>

          <table className="ink-table">
            <thead>
              <tr>
                <th>Descripción</th>
                <th className="text-right">Cantidad</th>
                <th>Unidad</th>
              </tr>
            </thead>
            <tbody>
              {guia.items.map((item) => (
                <tr key={item.id}>
                  <td data-label="Descripción">{item.descripcion}</td>
                  <td data-label="Cantidad" className="text-right font-mono-label">{Number(item.cantidad)}</td>
                  <td data-label="Unidad" className="text-[var(--text-secondary)]">{item.unidad_medida}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {(guia.sunat_pdf_url || guia.sunat_error) && (
        <div className="ink-card p-5">
          <h3 className="ink-card-title">SUNAT</h3>
          {guia.sunat_pdf_url && (
            <a href={guia.sunat_pdf_url} target="_blank" rel="noreferrer" className="mt-4 inline-flex text-sm text-[var(--text-brand)] underline">
              Descargar PDF SUNAT
            </a>
          )}
          {guia.sunat_error && (
            <p className="mt-3 text-sm text-[var(--color-error)]">{guia.sunat_error}</p>
          )}
        </div>
      )}
    </div>
  );
}
