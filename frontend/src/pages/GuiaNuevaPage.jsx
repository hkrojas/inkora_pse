import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  FileText,
  MapPin,
  Package,
  Save,
  Scale,
  Search,
  ShieldCheck,
  Truck,
} from 'lucide-react';
import { guias as svc } from '../services/guias';
import GuideLookup from '../components/guides/GuideLookup';
import Spinner from '../components/ui/Spinner';
import CustomSelect from '../components/ui/CustomSelect';
import DatePicker from '../components/ui/DatePicker';
import { GuideField as FormField, GuideForm, GuideFormErrors, useGuideFormFeedback } from '../components/guides/GuideFormFeedback';
import { useToast } from '../components/ui/Toast';
import { useInkoraDialog } from '../components/ui/InkoraDialogProvider';

const today = () => new Date().toLocaleDateString('en-CA', { timeZone: 'America/Lima' });
const isoDate = (value) => new Date(`${value}T12:00:00-05:00`).toISOString();

function GuideSectionHeader({ icon: Icon, title, description, aside }) {
  return (
    <div className="guide-flow-section__header">
      <div className="guide-flow-section__heading">
        <span className="guide-flow-section__icon"><Icon size={17} /></span>
        <div>
          <h3>{title}</h3>
          <p>{description}</p>
        </div>
      </div>
      {aside}
    </div>
  );
}

export default function GuiaNuevaPage() {
  const [params] = useSearchParams();
  const { id: editingGuideId } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const [step, setStep] = useState(1);
  const stepHeading = useRef(null);
  const saveAttempt = useRef({});
  const revealField = (name) => setStep(name.startsWith('lines.') || ['fiscal_document_id', 'document_query', 'reconciliation_note'].includes(name) ? 1 : 2);
  const feedback = useGuideFormFeedback({ onFieldFocus: revealField });
  const changeStep = (next) => { feedback.reset(); setStep(next); };
  useEffect(() => { stepHeading.current?.focus(); }, [step]);
  const { confirmAction } = useInkoraDialog();
  const [documents, setDocuments] = useState([]);
  const [documentTotal, setDocumentTotal] = useState(0);
  const [documentQuery, setDocumentQuery] = useState('');
  const [documentId, setDocumentId] = useState(params.get('comprobante_id') || params.get('factura_id') || '');
  const [context, setContext] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [reconciling, setReconciling] = useState(false);
  const [reconciliationConfirmed, setReconciliationConfirmed] = useState(false);
  const [reconciliationNote, setReconciliationNote] = useState('');
  const [dispatchVersion, setDispatchVersion] = useState(null);
  const [quantities, setQuantities] = useState({});
  const [confirmedGoods, setConfirmedGoods] = useState({});
  const [form, setForm] = useState({
    fecha_traslado: today(), peso_bruto_total: '', unidad_medida_peso: 'KGM', numero_bultos: '', modalidad_traslado: '02',
    partida_ubigeo: '', partida_direccion: '', llegada_ubigeo: '', llegada_direccion: '',
    transportista_ruc: '', transportista_razon_social: '', transportista_nro_mtc: '',
    fecha_entrega_transportista: today(), indicador_m1_l: false, registrar_vehiculo_transportista: false,
    transportista_acuerdo_confirmado: false, observaciones: '',
    vehiculo_placa: '', vehiculo_nro_circulacion: '', conductor_nro_doc: '',
    conductor_tipo_doc: '1', conductor_nombres: '', conductor_apellidos: '', conductor_licencia: '',
  });

  useEffect(() => {
    const timer = window.setTimeout(() => {
      Promise.all([
        svc.salesDocuments({ tipo_comprobante: '01', q: documentQuery || undefined, skip: 0, limit: 15 }),
        svc.salesDocuments({ tipo_comprobante: '03', q: documentQuery || undefined, skip: 0, limit: 15 }),
      ])
        .then(([invoicesPage, receiptsPage]) => {
          setDocuments([...(invoicesPage.items || []), ...(receiptsPage.items || [])].sort((a, b) => b.id - a.id));
          setDocumentTotal((invoicesPage.total || 0) + (receiptsPage.total || 0));
        })
        .catch((error) => toast(error.message, 'error'))
        .finally(() => setLoading(false));
    }, 250);
    return () => window.clearTimeout(timer);
  }, [documentQuery, toast]);

  useEffect(() => {
    if (!documentId || editingGuideId) { if (!editingGuideId) setContext(null); return; }
    let active = true;
    setContext(null);
    setLoading(true);
    svc.documentContext(documentId).then((data) => {
      if (!active) return;
      setContext(data);
      const sourceEstablishment = data.source_location?.ready
        ? data.source_location.establishment
        : null;
      setForm((current) => ({
        ...current,
        partida_direccion: sourceEstablishment?.address || current.partida_direccion,
        partida_ubigeo: sourceEstablishment?.ubigeo || current.partida_ubigeo,
        llegada_direccion: data.customer?.address || '',
        llegada_ubigeo: data.customer?.ubigeo || '',
      }));
      setQuantities(Object.fromEntries((data.lines || []).map((line) => [line.id, ''])));
    }).catch((error) => { if (active) toast(error.message, 'error'); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [editingGuideId, documentId, toast]);

  useEffect(() => {
    if (!editingGuideId) return;
    setLoading(true);
    svc.get(editingGuideId).then(async (guide) => {
      if (!guide.dispatch_id || !guide.fiscal_document_id) throw new Error('La guía no pertenece a un despacho editable.');
      const [dispatch, invoiceContext] = await Promise.all([
        svc.dispatch(guide.dispatch_id), svc.documentContext(guide.fiscal_document_id, guide.dispatch_id),
      ]);
      setDocumentId(String(guide.fiscal_document_id));
      setContext(invoiceContext);
      setDispatchVersion(dispatch.version);
      setQuantities(Object.fromEntries(dispatch.lines.map((line) => [line.fiscal_document_item_id, String(line.quantity)])));
      setConfirmedGoods(Object.fromEntries(dispatch.lines.map((line) => [line.fiscal_document_item_id, line.confirmed_as_goods])));
      setForm((current) => ({ ...current,
        fecha_traslado: String(guide.fecha_traslado).slice(0, 10),
        peso_bruto_total: String(guide.peso_bruto_total), numero_bultos: guide.numero_bultos || '',
        modalidad_traslado: guide.modalidad_traslado, partida_ubigeo: guide.partida_ubigeo || '',
        partida_direccion: guide.partida_direccion || '', llegada_ubigeo: guide.llegada_ubigeo || '',
        llegada_direccion: guide.llegada_direccion || '', transportista_ruc: guide.transportista_ruc || '',
        transportista_razon_social: guide.transportista_razon_social || '', transportista_nro_mtc: guide.transportista_nro_mtc || '',
        fecha_entrega_transportista: guide.fecha_entrega_transportista ? String(guide.fecha_entrega_transportista).slice(0, 10) : today(),
        indicador_m1_l: Boolean(guide.indicador_m1_l), registrar_vehiculo_transportista: Boolean(guide.registrar_vehiculo_transportista),
        transportista_acuerdo_confirmado: Boolean(guide.transportista_acuerdo_confirmado_at),
        observaciones: guide.observaciones || '',
        vehiculo_placa: guide.vehiculo_placa || '', vehiculo_nro_circulacion: guide.vehiculo_nro_circulacion || '',
        conductor_tipo_doc: guide.conductor_tipo_doc || '1', conductor_nro_doc: guide.conductor_nro_doc || '', conductor_nombres: guide.conductor_nombres || '',
        conductor_apellidos: guide.conductor_apellidos || '', conductor_licencia: guide.conductor_licencia || '',
      }));
    }).catch((error) => toast(error.message, 'error')).finally(() => setLoading(false));
  }, [editingGuideId, toast]);

  const options = useMemo(() => {
    const values = documents.map((document) => ({
      value: String(document.id),
      label: `${document.tipo_comprobante === '03' ? 'Boleta' : 'Factura'} · ${document.serie || '-'}-${String(document.correlativo || '').padStart(8, '0')} · ${document.cliente?.razon_social || document.cliente_nombre || 'Cliente'}`,
    }));
    if (context?.source_document && !values.some((option) => option.value === String(context.source_document.id))) {
      values.unshift({
        value: String(context.source_document.id),
        label: `${context.source_document.label} · ${context.source_document.number}`,
      });
    }
    return values;
  }, [context, documents]);

  const set = (key) => (eventOrValue) => {
    feedback.clearField(key);
    setForm((current) => ({
      ...current,
      [key]: key === 'vehiculo_placa' ? String(eventOrValue?.target?.value ?? eventOrValue).toUpperCase().replace(/[-\s]/g, '') : eventOrValue?.target ? (eventOrValue.target.type === 'checkbox' ? eventOrValue.target.checked : eventOrValue.target.value) : eventOrValue,
    }));
  };

  const hasDriverData = (value) => Boolean(
    value.conductor_nro_doc || value.conductor_nombres || value.conductor_apellidos || value.conductor_licencia,
  );

  const setM1L = async (event) => {
    const checked = event.target.checked;
    if (checked && hasDriverData(form)) {
      const confirmed = await confirmAction({
        title: 'Activar vehículo M1/L',
        eyebrow: 'Datos de transporte',
        description: 'Este escenario no utiliza los datos del conductor registrados actualmente.',
        detail: 'Al continuar se borrarán el documento, nombres, apellidos y licencia del conductor.',
        confirmLabel: 'Activar M1/L',
        tone: 'warning',
      });
      if (!confirmed) return;
    }
    feedback.reset();
    setForm((current) => ({
      ...current,
      indicador_m1_l: checked,
      registrar_vehiculo_transportista: checked ? false : current.registrar_vehiculo_transportista,
      transportista_acuerdo_confirmado: checked ? false : current.transportista_acuerdo_confirmado,
      ...(checked ? {
        conductor_nro_doc: '', conductor_nombres: '', conductor_apellidos: '', conductor_licencia: '',
        vehiculo_nro_circulacion: '',
        transportista_ruc: '', transportista_razon_social: '', transportista_nro_mtc: '',
      } : {}),
    }));
  };

  const setCarrierFleet = async (event) => {
    const checked = event.target.checked;
    if (!checked && hasDriverData(form)) {
      const confirmed = await confirmAction({
        title: 'Quitar vehículo y conductor',
        eyebrow: 'Transporte público',
        description: 'La guía dejará de registrar la flota del transportista.',
        detail: 'Al continuar se borrarán la placa y los datos del conductor ingresados.',
        confirmLabel: 'Quitar datos',
        tone: 'warning',
      });
      if (!confirmed) return;
    }
    feedback.reset();
    setForm((current) => ({
      ...current,
      registrar_vehiculo_transportista: checked,
      indicador_m1_l: checked ? false : current.indicador_m1_l,
      transportista_acuerdo_confirmado: checked ? current.transportista_acuerdo_confirmado : false,
      ...(!checked ? {
        vehiculo_placa: '', vehiculo_nro_circulacion: '', conductor_nro_doc: '',
        conductor_nombres: '', conductor_apellidos: '', conductor_licencia: '',
      } : {}),
    }));
  };

  const setTransportMode = async (value) => {
    const changingToPublic = value === '01' && form.modalidad_traslado !== '01';
    const changingToPrivate = value === '02' && form.modalidad_traslado !== '02';
    const incompatible = changingToPublic
      ? hasDriverData(form) || form.vehiculo_placa
      : form.transportista_ruc || form.transportista_razon_social || form.transportista_nro_mtc;
    if (incompatible) {
      const confirmed = await confirmAction({
        title: 'Cambiar modalidad de transporte',
        eyebrow: 'Datos de transporte',
        description: `Cambiarás a transporte ${value === '01' ? 'público' : 'privado'}.`,
        detail: 'Los datos incompatibles con la nueva modalidad se borrarán para evitar una guía inconsistente.',
        confirmLabel: 'Cambiar modalidad',
        tone: 'warning',
      });
      if (!confirmed) return;
    }
    feedback.reset();
    setForm((current) => ({
      ...current,
      modalidad_traslado: value,
      indicador_m1_l: false,
      registrar_vehiculo_transportista: false,
      transportista_acuerdo_confirmado: false,
      ...(changingToPublic ? {
        vehiculo_placa: '', vehiculo_nro_circulacion: '', conductor_nro_doc: '',
        conductor_nombres: '', conductor_apellidos: '', conductor_licencia: '',
      } : {}),
      ...(changingToPrivate ? {
        transportista_ruc: '', transportista_razon_social: '', transportista_nro_mtc: '',
      } : {}),
    }));
  };

  const loadMoreDocuments = async () => {
    try {
      const invoiceCount = documents.filter((item) => item.tipo_comprobante === '01').length;
      const receiptCount = documents.filter((item) => item.tipo_comprobante === '03').length;
      const [invoicesPage, receiptsPage] = await Promise.all([
        svc.salesDocuments({ tipo_comprobante: '01', q: documentQuery || undefined, skip: invoiceCount, limit: 15 }),
        svc.salesDocuments({ tipo_comprobante: '03', q: documentQuery || undefined, skip: receiptCount, limit: 15 }),
      ]);
      setDocuments((current) => [...current, ...(invoicesPage.items || []), ...(receiptsPage.items || [])].sort((a, b) => b.id - a.id));
      setDocumentTotal((invoicesPage.total || 0) + (receiptsPage.total || 0));
    } catch (error) {
      toast(error.message || 'No se pudieron cargar más comprobantes.', 'error');
    }
  };

  const reconcileHistoricalInvoice = async () => {
    if (!documentId || !reconciliationConfirmed || reconciliationNote.trim().length < 10) return;
    setReconciling(true);
    try {
      await svc.reconcileHistoricalDocument(documentId, {
        confirmed_no_prior_dispatch: true,
        note: reconciliationNote.trim(),
      });
      const refreshed = await svc.documentContext(documentId);
      setContext(refreshed);
      setReconciliationConfirmed(false);
      setReconciliationNote('');
      toast('Comprobante histórico conciliado. Ya puede reservar cantidades para la guía.', 'success');
    } catch (error) {
      toast(error.message || 'No se pudo conciliar el comprobante histórico.', 'error');
    } finally {
      setReconciling(false);
    }
  };

  const selectedLines = (context?.lines || []).filter((line) => Number(quantities[line.id]) > 0);
  const checkGoods = () => {
    if (!context || loading) { feedback.show({}, 'Selecciona una factura o boleta y espera a que carguen sus productos.'); return false; }
    if (!selectedLines.length) { feedback.show({}, 'Indica cuánto llevarás de al menos un producto.'); return false; }
    const missing = selectedLines.find((line) => line.requires_goods_confirmation && !confirmedGoods[line.id]);
    if (missing) { feedback.show({ [`lines.${missing.id}.quantity`]: 'Confirma que esta línea corresponde a un bien.' }); return false; }
    return true;
  };
  const submit = async (event) => {
    event.preventDefault();
    if (step < 3) {
      if (step === 1 && !checkGoods()) return;
      setStep(step + 1);
      return;
    }
    if (!checkGoods()) { setStep(1); return; }
    if (saving) return;
    const emitRequested = event.nativeEvent.submitter?.value === 'emit';
    if (emitRequested) {
      const confirmed = await confirmAction({
        title: 'Emitir guía de remisión', eyebrow: 'Emisión fiscal',
        description: 'Enviaremos la guía a SUNAT. Después no podrás editar sus datos.',
        detail: 'La salida física de los productos se confirma por separado, cuando realmente salgan.',
        confirmLabel: 'Emitir guía', tone: 'warning',
      });
      if (!confirmed) return;
    }
    const lines = (context?.lines || []).filter((line) => Number(quantities[line.id]) > 0).map((line) => ({
      fiscal_document_item_id: line.id,
      quantity: Number(quantities[line.id]),
      confirmed_as_goods: !line.requires_goods_confirmation || Boolean(confirmedGoods[line.id]),
    }));
    if (!lines.length) { feedback.show(context?.lines?.length ? { [`lines.${context.lines[0].id}.quantity`]: 'Indica cuánto llevarás de al menos un producto.' } : {}, 'Indica las cantidades que vas a llevar.'); return; }
    setSaving(true);
    try {
      const payload = {
        ...Object.fromEntries(Object.entries(form).map(([key, value]) => [key, value === '' ? null : value])),
        fecha_traslado: isoDate(form.fecha_traslado),
        fecha_entrega_transportista: form.modalidad_traslado === '01' ? isoDate(form.fecha_entrega_transportista) : null,
        peso_bruto_total: Number(form.peso_bruto_total),
        numero_bultos: form.numero_bultos ? Number(form.numero_bultos) : null,
        lines,
      };
      const signature = JSON.stringify({ ...payload, fiscal_document_id: documentId });
      if (saveAttempt.current.signature !== signature) saveAttempt.current = { signature, key: crypto.randomUUID() };
      const result = editingGuideId
        ? await svc.updateDispatch(editingGuideId, { ...payload, version: dispatchVersion })
        : await svc.createFromDocument({ ...payload, fiscal_document_id: Number(documentId), idempotency_key: saveAttempt.current.key });
      const guide = result.guides?.find((item) => item.tipo_documento === '09');
      toast(context.eligibility?.can_reserve ? 'Borrador guardado y cantidades reservadas.' : 'Borrador provisional guardado; aún no reserva cantidades.', 'success');
      if (emitRequested && guide) {
        // Once saved, all retries belong to this guide; never create another dispatch.
        try {
          await svc.emitir(guide.id);
          toast('Guía enviada para emisión. Puedes seguir su respuesta aquí.', 'info');
        } catch (error) {
          toast(`La guía quedó guardada. ${error.isTimeout || error.status == null ? 'No recibimos confirmación de la emisión. Revisa su estado antes de reintentar.' : error.message || 'Revisa los datos antes de emitir desde su detalle.'}`, 'error');
        }
      }
      navigate(guide ? `/guias/${guide.id}` : '/guias');
    } catch (error) {
      if (error.status === 409 && error.detail?.context) {
        setContext(error.detail.context);
        setDispatchVersion(error.detail.current_version || dispatchVersion);
      }
      const aliases = Object.fromEntries(lines.map((line, index) => [`lines.${index}.quantity`, `lines.${line.fiscal_document_item_id}.quantity`]));
      feedback.reportError(error, aliases);
    } finally { setSaving(false); }
  };

  return (
    <div className="page-shell max-w-6xl guide-workflow">
      <div className="page-header guide-workflow__hero">
        <div className="page-header-copy">
          <Link to="/guias" className="guide-back-link"><ArrowLeft size={15} />Volver a guías</Link>
          <div className="guide-workflow__identity">
            <span>GRE remitente 09</span>
            <span>Venta</span>
          </div>
          <h2 className="page-title">{editingGuideId ? 'Editar guía remitente' : 'Nueva guía remitente'}</h2>
          <p className="page-subtitle">Elige la venta, indica cómo viajarán los productos y revisa tu guía antes de emitirla.</p>
        </div>
        <div className="guide-workflow__assurance" aria-label="Controles del flujo">
          <ShieldCheck size={18} />
          <span>La guía no vuelve a descontar inventario</span>
        </div>
      </div>

      <GuideForm feedback={feedback} onSubmit={submit} validateHidden={step === 3} className="guide-workflow__form guide-accessible-form">
        <ol className="guide-wizard-steps" aria-label="Pasos para crear la guía">
          {['Venta y cantidades', 'Transporte', 'Revisar guía'].map((title, index) => <li key={title} aria-current={step === index + 1 ? 'step' : undefined}>
            <button type="button" disabled={index + 1 > step || saving} onClick={() => changeStep(index + 1)}><span>{index + 1}</span>{title}</button>
          </li>)}
        </ol>
        <h3 ref={stepHeading} tabIndex={-1} className="guide-step-heading">Paso {step} de 3 · {['¿Qué vas a llevar?', '¿Cómo se transportará?', 'Revisa tu guía'][step - 1]}</h3>
        <GuideFormErrors />
        <div hidden={step !== 1} data-guide-step="1">
        <section className="guide-flow-section guide-flow-section--origin">
          <GuideSectionHeader
            icon={FileText}
            title="Comprobante de origen"
            description="El cliente se toma de esta venta. Indica solo las cantidades que llevarás ahora."
            aside={context?.source_document && <span className="guide-origin-badge">{context.source_document.label}</span>}
          />
          <div className="guide-flow-section__body">
            <div className="guide-origin-grid">
              {!editingGuideId && (
                <FormField name="document_query" label="Buscar comprobante" icon={Search} hint="Serie, número, cliente o documento de identidad.">
                  <input className="input" value={documentQuery} onChange={(event) => setDocumentQuery(event.target.value)} placeholder="Ej. F001-178 o nombre del cliente" />
                </FormField>
              )}
              <FormField name="fiscal_document_id" label="Factura o boleta" required className={editingGuideId ? 'md:col-span-2' : ''}>
                <CustomSelect
                  searchable
                  ariaLabel="Factura o boleta de origen"
                  value={documentId}
                  onChange={(id) => { feedback.reset(); setDocumentId(id); }}
                  options={options}
                  placeholder="Seleccionar comprobante"
                  searchPlaceholder="Filtrar comprobantes..."
                  disabled={Boolean(editingGuideId)}
                />
              </FormField>
            </div>
            {!editingGuideId && documents.length < documentTotal && (
              <button type="button" className="btn-ghost guide-load-more" onClick={loadMoreDocuments}>
                Cargar 15 más <span>{documents.length} de {documentTotal}</span>
              </button>
            )}
            {context?.source_document && (
              <div className={`guide-eligibility ${context.eligibility?.can_reserve ? 'is-ready' : 'is-warning'}`} aria-live="polite">
                {context.eligibility?.can_reserve ? <CheckCircle2 size={18} /> : <AlertTriangle size={18} />}
                <div>
                  <strong>{context.source_document.label} {context.source_document.number}</strong>
                  <p>{context.eligibility?.can_reserve ? 'Aceptado fiscalmente. Al guardar se reservarán las cantidades seleccionadas.' : context.eligibility?.reason}</p>
                </div>
              </div>
            )}
            {context?.eligibility?.code === 'HISTORICAL_RECONCILIATION_REQUIRED' && !editingGuideId && (
              <div className="guide-reconciliation">
                <AlertTriangle size={19} />
                <div className="guide-reconciliation__content">
                  <div>
                    <strong>Conciliación histórica requerida</strong>
                    <p>Verifica que este comprobante no tuvo despachos o guías fuera de Inkora antes de habilitar su saldo.</p>
                  </div>
                  <label className="guide-choice-card is-compact">
                    <input type="checkbox" checked={reconciliationConfirmed} onChange={(event) => setReconciliationConfirmed(event.target.checked)} />
                    <span>Confirmo que no existieron despachos previos fuera de este flujo.</span>
                  </label>
                  <FormField name="reconciliation_note" label="Evidencia de revisión" required>
                    <textarea className="input min-h-24" minLength={10} maxLength={500} value={reconciliationNote} onChange={(event) => setReconciliationNote(event.target.value)} placeholder="Describe qué revisaste y por qué puede habilitarse el saldo." />
                  </FormField>
                  <button type="button" className="btn-secondary justify-self-start" disabled={reconciling || !reconciliationConfirmed || reconciliationNote.trim().length < 10} onClick={reconcileHistoricalInvoice}>
                    {reconciling ? <Spinner size="sm" /> : <ShieldCheck size={15} />}Confirmar conciliación
                  </button>
                </div>
              </div>
            )}
          </div>
        </section>

        </div>
        {loading && <Spinner size="lg" label="Cargando comprobante" hint="Calculando saldos disponibles y reglas de despacho." />}
        {context && !loading && <>
          <div hidden={step !== 1} data-guide-step="1">
          <section className="guide-flow-section guide-flow-section--goods">
            <GuideSectionHeader
              icon={Package}
              title="Productos que llevarás"
              description="Disponible es lo que aún puedes enviar. Deja vacío lo que no llevarás."
              aside={<span className="guide-origin-badge">{context.lines.length} {context.lines.length === 1 ? 'línea' : 'líneas'}</span>}
            />
            <div className="ink-table-scroll">
              <table className="ink-table guide-quantity-table">
                <thead><tr><th>Bien</th><th>Vendido</th><th><abbr title="Cantidades apartadas en otras guías que todavía no salieron">Reservado</abbr></th><th><abbr title="Cantidades que ya salieron o ya tienen su despacho cubierto">Enviado</abbr></th><th>Disponible</th><th>A despachar</th></tr></thead>
                <tbody>{context.lines.map((line) => <tr key={line.id}>
                  <td data-label="Bien"><strong>{line.description}</strong><div className="ink-table-cell__meta">{line.unit} · línea #{line.id}</div>{line.pending_adjustment && <div className="guide-line-warning">Ajuste fiscal pendiente</div>}</td>
                  <td data-label="Facturado" className="font-mono-label">{Number(line.invoiced)}</td>
                  <td data-label="Reservado" className="font-mono-label">{Number(line.reserved)}</td>
                  <td data-label="Cubierto" className="font-mono-label">{Number(line.covered)}</td>
                  <td data-label="Disponible"><span className="guide-available-quantity">{Number(line.available)} {line.unit}</span></td>
                  <td data-label="A despachar">
                    <input
                      {...feedback.control(`lines.${line.id}.quantity`)}
                      data-field-label={`Cantidad de ${line.description}`}
                      aria-label={`Cantidad a despachar de ${line.description}`}
                      className="input guide-quantity-input"
                      type="number"
                      min="0"
                      max={Number(line.available)}
                      step="0.0001"
                      disabled={!line.dispatchable || line.pending_adjustment || line.inventory_evidence_missing}
                      value={quantities[line.id] || ''}
                      onChange={(event) => setQuantities((current) => ({ ...current, [line.id]: event.target.value }))}
                    />
                    {feedback.errors[`lines.${line.id}.quantity`] && <p className="guide-field-error" id={`${feedback.control(`lines.${line.id}.quantity`).id}-error`}>{feedback.errors[`lines.${line.id}.quantity`]}</p>}
                    {line.requires_goods_confirmation && Number(quantities[line.id]) > 0 && <label className="guide-inline-check"><input type="checkbox" checked={Boolean(confirmedGoods[line.id])} onChange={(event) => setConfirmedGoods((current) => ({ ...current, [line.id]: event.target.checked }))} />Confirmo que es un bien</label>}
                  </td>
                </tr>)}</tbody>
              </table>
            </div>
          </section>

          </div>
          <div hidden={step !== 2} data-guide-step="2">
          <section className="guide-flow-section guide-flow-section--transport">
            <GuideSectionHeader icon={Truck} title="Ruta y transporte" description="Revisa las direcciones y completa los datos de quien llevará los productos." />
            <div className="guide-flow-section__body guide-transport-stack">
              <div className="guide-form-grid">
                <FormField name="fecha_traslado" label="Fecha de traslado" required>
                  <DatePicker value={form.fecha_traslado} onChange={set('fecha_traslado')} min={today()} required ariaLabel="Fecha de traslado" />
                </FormField>
                <FormField name="peso_bruto_total" label="Peso bruto" icon={Scale} required hint="Peso de todo lo que llevarás, incluido el empaque.">
                  <div className="guide-weight-control">
                    <input {...feedback.control("peso_bruto_total")} data-field-label="Peso bruto" aria-label="Peso bruto" required min="0.001" step="0.001" type="number" className="input" value={form.peso_bruto_total} onChange={set('peso_bruto_total')} placeholder="0.000" />
                    <CustomSelect compact ariaLabel="Unidad de peso" value={form.unidad_medida_peso} onChange={set('unidad_medida_peso')} options={[{ value: 'KGM', label: 'Kilogramos (kg)' }, { value: 'TNE', label: 'Toneladas (t)' }]} />
                  </div>
                </FormField>
                <FormField name="numero_bultos" label="Bultos" hint="Opcional cuando no corresponde al traslado.">
                  <input aria-label="Número de bultos" min="1" type="number" className="input" value={form.numero_bultos} onChange={set('numero_bultos')} placeholder="Ej. 4" />
                </FormField>
              </div>

              <div className="guide-route-block">
                <div className="guide-subsection-title"><MapPin size={16} /><span>Ruta del traslado</span></div>
                {context.source_location?.ready ? (
                  <div className="guide-eligibility is-ready">
                    <ShieldCheck size={18} />
                    <div>
                      <strong>{context.source_location.establishment.sunat_code} · {context.source_location.warehouse.name}</strong>
                      <p>El origen se toma del establecimiento SUNAT vinculado al almacén del comprobante.</p>
                    </div>
                  </div>
                ) : (
                  <div className="guide-eligibility is-warning">
                    <AlertTriangle size={18} />
                    <div>
                      <strong>Origen fiscal pendiente</strong>
                      <p>{context.source_location?.reason || 'Configura el almacén de origen antes de emitir la guía.'}</p>
                    </div>
                  </div>
                )}
                <div className="guide-form-grid">
                  <FormField name="partida_ubigeo" label="Ubigeo de partida" required hint="Código de 6 dígitos del distrito de salida."><input required readOnly={Boolean(context.source_location?.ready)} inputMode="numeric" pattern="[0-9]{6}" maxLength={6} className="input" value={form.partida_ubigeo} onChange={set('partida_ubigeo')} placeholder="150101" /></FormField>
                  <FormField name="partida_direccion" label="Dirección de partida" required className="md:col-span-2"><input required readOnly={Boolean(context.source_location?.ready)} className="input" value={form.partida_direccion} onChange={set('partida_direccion')} placeholder="Dirección completa de origen" /></FormField>
                  <FormField name="llegada_ubigeo" label="Ubigeo de llegada" required hint="Código de 6 dígitos del distrito de entrega. Revisa que coincida con la dirección."><input required inputMode="numeric" pattern="[0-9]{6}" maxLength={6} className="input" value={form.llegada_ubigeo || ''} onChange={set('llegada_ubigeo')} placeholder="150103" /></FormField>
                  <FormField name="llegada_direccion" label="Dirección de llegada" required className="md:col-span-2"><input required className="input" value={form.llegada_direccion || ''} onChange={set('llegada_direccion')} placeholder="Dirección completa de destino" /></FormField>
                </div>
              </div>

              <div className="guide-scenario-block">
                <div className="guide-subsection-title"><Truck size={16} /><span>Modalidad de transporte</span></div>
                <div className="guide-mode-grid" role="group" aria-label="Modalidad de transporte">
                  <button type="button" className={`guide-mode-option ${form.modalidad_traslado === '02' ? 'is-active' : ''}`} aria-pressed={form.modalidad_traslado === '02'} onClick={() => setTransportMode('02')}>
                    <Truck size={18} /><span><strong>Nosotros</strong><small>Nos encargamos del vehículo y el conductor</small></span>
                  </button>
                  <button type="button" className={`guide-mode-option ${form.modalidad_traslado === '01' ? 'is-active' : ''}`} aria-pressed={form.modalidad_traslado === '01'} onClick={() => setTransportMode('01')}>
                    <ShieldCheck size={18} /><span><strong>Empresa de transporte</strong><small>Contratamos a un transportista</small></span>
                  </button>
                </div>

                <details className="guide-advanced-options"><summary>Opciones del vehículo</summary><label className={`guide-choice-card ${form.indicador_m1_l ? 'is-selected' : ''}`}>
                  <input type="checkbox" checked={form.indicador_m1_l} onChange={setM1L} />
                  <span><strong>Vehículo M1/L</strong><small>Revisa la categoría en la tarjeta del vehículo. Esta opción pide placa y no datos del conductor.</small></span>
                </label></details>

                <div key={`${form.modalidad_traslado}-${form.indicador_m1_l}-${form.registrar_vehiculo_transportista}`} className="guide-scenario-panel">
                  {form.modalidad_traslado === '01' && <div className="guide-form-grid">
                    {!form.indicador_m1_l && <>
                      <div className="guide-field-with-query"><FormField name="transportista_ruc" label="RUC del transportista" required><input required inputMode="numeric" pattern="[0-9]{11}" maxLength={11} className="input" value={form.transportista_ruc} onChange={set('transportista_ruc')} placeholder="20XXXXXXXXX" /></FormField>
<GuideLookup kind="RUC" form={form} setForm={setForm} source="transportista_ruc" targets={{ transportista_razon_social: 'razon_social' }} onApplied={(keys) => keys.forEach(feedback.clearField)} /></div>
                      <FormField name="transportista_razon_social" label="Razón social" required><input required className="input" value={form.transportista_razon_social} onChange={set('transportista_razon_social')} placeholder="Empresa transportista" /></FormField>
                      <FormField name="transportista_nro_mtc" label="Registro MTC" required hint="Solicita este registro a la empresa de transporte."><input required className="input uppercase" value={form.transportista_nro_mtc} onChange={set('transportista_nro_mtc')} placeholder="Registro vigente" /></FormField>
                    </>}
                    <FormField name="fecha_entrega_transportista" label="Entrega al transportista" required>
                      <DatePicker value={form.fecha_entrega_transportista} onChange={set('fecha_entrega_transportista')} min={today()} required ariaLabel="Fecha de entrega al transportista" />
                    </FormField>
                    {!form.indicador_m1_l && <label className={`guide-choice-card md:col-span-2 ${form.registrar_vehiculo_transportista ? 'is-selected' : ''}`}><input type="checkbox" checked={form.registrar_vehiculo_transportista} onChange={setCarrierFleet} /><span><strong>Registrar vehículo y conductor del transportista</strong><small>Con el acuerdo correspondiente, este escenario no exige GRE 31.</small></span></label>}
                    {form.registrar_vehiculo_transportista && !form.indicador_m1_l && <label className={`guide-choice-card md:col-span-3 ${form.transportista_acuerdo_confirmado ? 'is-selected' : ''}`}><input {...feedback.control("transportista_acuerdo_confirmado")} data-field-label="Acuerdo confirmado" required type="checkbox" checked={form.transportista_acuerdo_confirmado} onChange={set('transportista_acuerdo_confirmado')} /><span><strong>Acuerdo confirmado</strong><small>Confirmo que existe autorización para registrar el vehículo y conductor en esta GRE.</small>{feedback.errors.transportista_acuerdo_confirmado && <span className="guide-field-error" id={`${feedback.control("transportista_acuerdo_confirmado").id}-error`}>{feedback.errors.transportista_acuerdo_confirmado}</span>}</span></label>}
                  </div>}

                  {(form.indicador_m1_l || form.modalidad_traslado === '02' || form.registrar_vehiculo_transportista) && <div className="guide-form-grid guide-vehicle-grid">
                    <div className="guide-field-with-query"><FormField name="vehiculo_placa" label="Placa" required><input required className="input uppercase" value={form.vehiculo_placa} onChange={set('vehiculo_placa')} placeholder="ABC123" /></FormField>
<GuideLookup kind="placa" form={form} setForm={setForm} source="vehiculo_placa" /></div>
                    {form.registrar_vehiculo_transportista && !form.indicador_m1_l && <FormField name="vehiculo_nro_circulacion" label="Número de circulación" required><input required className="input uppercase" value={form.vehiculo_nro_circulacion} onChange={set('vehiculo_nro_circulacion')} placeholder="Constancia o circulación" /></FormField>}
                    {!form.indicador_m1_l && (form.modalidad_traslado === '02' || form.registrar_vehiculo_transportista) && <>
                      <FormField name="conductor_tipo_doc" label="Tipo de documento" required><CustomSelect ariaLabel="Tipo de documento del conductor" value={form.conductor_tipo_doc} onChange={set('conductor_tipo_doc')} options={[{ value: '1', label: 'DNI' }, { value: '4', label: 'Carné de extranjería' }, { value: '6', label: 'RUC' }, { value: '7', label: 'Pasaporte' }]} /></FormField>
                      <div className="guide-field-with-query"><FormField name="conductor_nro_doc" label="Documento del conductor" required hint={form.conductor_tipo_doc === '1' ? 'Ingresa los 8 dígitos del DNI.' : 'Ingresa el documento elegido.'}><input inputMode={form.conductor_tipo_doc === '1' ? 'numeric' : 'text'} pattern={form.conductor_tipo_doc === '1' ? '[0-9]{8}' : undefined} maxLength={form.conductor_tipo_doc === '1' ? 8 : 15} required className="input" value={form.conductor_nro_doc} onChange={set('conductor_nro_doc')} placeholder="Número de documento" /></FormField>
{form.conductor_tipo_doc === '1' && <GuideLookup kind="DNI" form={form} setForm={setForm} source="conductor_nro_doc" identityType={form.conductor_tipo_doc} targets={{ conductor_nombres: 'nombres', conductor_apellidos: 'apellidos' }} onApplied={(keys) => keys.forEach(feedback.clearField)} />}</div>
                      <div className="guide-field-with-query"><FormField name="conductor_licencia" label="Licencia" required hint="Copia el número que aparece en la licencia del conductor."><input required className="input uppercase" value={form.conductor_licencia} onChange={set('conductor_licencia')} placeholder="Q12345678" /></FormField>
{form.conductor_tipo_doc === '1' && <GuideLookup kind="licencia" form={form} setForm={setForm} source="conductor_nro_doc" identityType={form.conductor_tipo_doc} targets={{ conductor_licencia: 'numero' }} onApplied={(keys) => keys.forEach(feedback.clearField)} />}</div>
                      <FormField name="conductor_nombres" label="Nombres" required><input required className="input" value={form.conductor_nombres} onChange={set('conductor_nombres')} placeholder="Nombres del conductor" /></FormField>
                      <FormField name="conductor_apellidos" label="Apellidos" required><input required className="input" value={form.conductor_apellidos} onChange={set('conductor_apellidos')} placeholder="Apellidos del conductor" /></FormField>
                    </>}
                  </div>}

                  {form.modalidad_traslado === '01' && !form.indicador_m1_l && !form.registrar_vehiculo_transportista && <div className="guide-public-notice"><AlertTriangle size={18} /><p><strong>Necesitarás la guía de la empresa transportista (GRE 31).</strong><span>La empresa transportista te entregará su propia guía. Regístrala y verifica su aceptación antes de confirmar la salida de los bienes.</span></p></div>}
                </div>
              </div>

              <FormField name="observaciones" label="Observaciones" hint={`${form.observaciones.length}/500 caracteres`}>
                <textarea maxLength={500} className="input guide-observations" value={form.observaciones} onChange={set('observaciones')} placeholder="Información adicional relevante para el traslado" />
              </FormField>
            </div>
          </section>

          </div>
          <section hidden={step !== 3} className="guide-flow-section guide-review" aria-label="Resumen de la guía">
            <GuideSectionHeader icon={CheckCircle2} title="Todo listo para revisar" description="Guardar conserva una preparación. Emitir envía la guía a SUNAT y bloquea su edición." />
            <div className="guide-flow-section__body">
              <dl className="guide-review-grid">
                <div><dt>Venta y cliente</dt><dd>{context.source_document?.number} · {context.customer?.name || 'Cliente de la venta'}</dd></div>
                <div><dt>Fecha y peso</dt><dd>{new Date(`${form.fecha_traslado}T12:00:00-05:00`).toLocaleDateString('es-PE', { timeZone: 'America/Lima' })} · {form.peso_bruto_total} {form.unidad_medida_peso === 'KGM' ? 'kg' : 't'}</dd></div>
                <div><dt>Desde</dt><dd>{form.partida_direccion} · {form.partida_ubigeo}</dd></div>
                <div><dt>Hasta</dt><dd>{form.llegada_direccion} · {form.llegada_ubigeo}</dd></div>
                <div><dt>Transporte</dt><dd>{form.modalidad_traslado === '02' ? 'Nosotros' : form.transportista_razon_social || 'Empresa de transporte'}{form.vehiculo_placa && ` · ${form.vehiculo_placa}`}</dd></div>
                {!form.indicador_m1_l && form.conductor_nro_doc && <div><dt>Conductor</dt><dd>{form.conductor_nombres} {form.conductor_apellidos} · {form.conductor_nro_doc} · {form.conductor_licencia}</dd></div>}
              </dl>
              <ul className="guide-review-goods">{selectedLines.map((line) => <li key={line.id}><span>{line.description}</span><strong>{quantities[line.id]} {line.unit}</strong></li>)}</ul>
              <p className="guide-field-hint">La emisión no confirma que los productos ya salieron. Esa confirmación se registra cuando salgan del almacén.</p>
              {!context.eligibility?.can_emit && <p className="guide-field-error">{context.eligibility?.reason || 'Esta venta aún no permite emitir. Puedes guardar una preparación.'}</p>}
            </div>
          </section>
          <div className="guide-form-actions">
            <div><strong>{step === 3 ? 'Revisa los datos antes de emitir' : 'Puedes volver sin perder tus datos'}</strong><span>{step === 3 ? 'Solo al emitir se enviará la guía a SUNAT.' : 'Continuar no guarda ni emite una guía.'}</span></div>
            <div className="guide-form-actions__buttons">
              {step > 1 ? <button type="button" disabled={saving} className="btn-secondary" onClick={() => changeStep(step - 1)}>Atrás</button> : <Link to="/guias" className="btn-secondary">Cancelar</Link>}
              {step < 3 ? <button type="submit" className="btn-primary" disabled={!context.eligibility?.can_prepare}>Continuar</button> : <>
                <button disabled={saving || !context.eligibility?.can_prepare} className="btn-secondary" type="submit" name="action" value="draft">{saving ? <Spinner size="sm" /> : <Save size={16} />}Guardar borrador</button>
                <button disabled={saving || !context.eligibility?.can_emit} className="btn-primary" type="submit" name="action" value="emit">{saving ? <Spinner size="sm" /> : <ShieldCheck size={16} />}Emitir guía</button>
              </>}
            </div>
          </div>
        </>}
        {!context && !loading && <div className="guide-form-actions"><span>Selecciona la venta para ver sus productos.</span><button type="submit" className="btn-primary">Continuar</button></div>}
      </GuideForm>
    </div>
  );
}
