import { useEffect, useMemo, useState } from 'react';
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
import Spinner from '../components/ui/Spinner';
import CustomSelect from '../components/ui/CustomSelect';
import DatePicker from '../components/ui/DatePicker';
import FormField from '../components/ui/FormField';
import { useToast } from '../components/ui/Toast';

const today = () => new Date().toISOString().slice(0, 10);
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
    setLoading(true);
    svc.documentContext(documentId).then((data) => {
      setContext(data);
      const sourceEstablishment = data.source_location?.ready
        ? data.source_location.establishment
        : null;
      setForm((current) => ({
        ...current,
        partida_direccion: sourceEstablishment?.address || current.partida_direccion,
        partida_ubigeo: sourceEstablishment?.ubigeo || current.partida_ubigeo,
        llegada_direccion: current.llegada_direccion || data.customer?.address || '',
        llegada_ubigeo: current.llegada_ubigeo || data.customer?.ubigeo || '',
      }));
      setQuantities(Object.fromEntries((data.lines || []).map((line) => [line.id, ''])));
    }).catch((error) => toast(error.message, 'error')).finally(() => setLoading(false));
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

  const set = (key) => (eventOrValue) => setForm((current) => ({
    ...current,
    [key]: eventOrValue?.target ? (eventOrValue.target.type === 'checkbox' ? eventOrValue.target.checked : eventOrValue.target.value) : eventOrValue,
  }));

  const hasDriverData = (value) => Boolean(
    value.conductor_nro_doc || value.conductor_nombres || value.conductor_apellidos || value.conductor_licencia,
  );

  const setM1L = (event) => {
    const checked = event.target.checked;
    if (checked && hasDriverData(form) && !window.confirm('Al activar M1/L se quitarán los datos del conductor. ¿Deseas continuar?')) return;
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

  const setCarrierFleet = (event) => {
    const checked = event.target.checked;
    if (!checked && hasDriverData(form) && !window.confirm('Al desactivar esta opción se quitarán los datos del vehículo y conductor del transportista. ¿Deseas continuar?')) return;
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

  const setTransportMode = (value) => {
    const changingToPublic = value === '01' && form.modalidad_traslado !== '01';
    const changingToPrivate = value === '02' && form.modalidad_traslado !== '02';
    const incompatible = changingToPublic
      ? hasDriverData(form) || form.vehiculo_placa
      : form.transportista_ruc || form.transportista_razon_social || form.transportista_nro_mtc;
    if (incompatible && !window.confirm('Cambiar la modalidad quitará datos que ya no corresponden al escenario. ¿Deseas continuar?')) return;
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

  const submit = async (event) => {
    event.preventDefault();
    const lines = (context?.lines || []).filter((line) => Number(quantities[line.id]) > 0).map((line) => ({
      fiscal_document_item_id: line.id,
      quantity: Number(quantities[line.id]),
      confirmed_as_goods: !line.requires_goods_confirmation || Boolean(confirmedGoods[line.id]),
    }));
    if (!lines.length) { toast('Selecciona al menos una cantidad para despachar.', 'error'); return; }
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
      const result = editingGuideId
        ? await svc.updateDispatch(editingGuideId, { ...payload, version: dispatchVersion })
        : await svc.createFromDocument({ ...payload, fiscal_document_id: Number(documentId), idempotency_key: crypto.randomUUID() });
      const guide = result.guides?.find((item) => item.tipo_documento === '09');
      toast(context.eligibility?.can_reserve ? 'Borrador guardado y cantidades reservadas.' : 'Borrador provisional guardado; aún no reserva cantidades.', 'success');
      navigate(guide ? `/guias/${guide.id}` : '/guias');
    } catch (error) {
      if (error.status === 409 && error.detail?.context) {
        setContext(error.detail.context);
        setDispatchVersion(error.detail.current_version || dispatchVersion);
      }
      toast(error.message || 'No se pudo guardar el despacho.', 'error');
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
          <p className="page-subtitle">Prepara el despacho desde una factura o boleta de Inkora y reserva solo las cantidades que realmente saldrán.</p>
        </div>
        <div className="guide-workflow__assurance" aria-label="Controles del flujo">
          <ShieldCheck size={18} />
          <span>La guía no vuelve a descontar inventario</span>
        </div>
      </div>

      <form onSubmit={submit} className="guide-workflow__form">
        <section className="guide-flow-section guide-flow-section--origin">
          <GuideSectionHeader
            icon={FileText}
            title="Comprobante de origen"
            description="Busca el documento de venta y revisa su elegibilidad antes de asignar cantidades."
            aside={context?.source_document && <span className="guide-origin-badge">{context.source_document.label}</span>}
          />
          <div className="guide-flow-section__body">
            <div className="guide-origin-grid">
              {!editingGuideId && (
                <FormField label="Buscar comprobante" icon={Search} hint="Serie, número, cliente o documento de identidad.">
                  <input className="input" value={documentQuery} onChange={(event) => setDocumentQuery(event.target.value)} placeholder="Ej. F001-178 o nombre del cliente" />
                </FormField>
              )}
              <FormField label="Factura o boleta" required className={editingGuideId ? 'md:col-span-2' : ''}>
                <CustomSelect
                  searchable
                  ariaLabel="Factura o boleta de origen"
                  value={documentId}
                  onChange={setDocumentId}
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
                  <FormField label="Evidencia de revisión" required>
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

        {loading && <Spinner size="lg" label="Cargando comprobante" hint="Calculando saldos disponibles y reglas de despacho." />}
        {context && !loading && <>
          <section className="guide-flow-section guide-flow-section--goods">
            <GuideSectionHeader
              icon={Package}
              title="Bienes a despachar"
              description="Asigna el despacho por línea. Los productos repetidos conservan saldos independientes."
              aside={<span className="guide-origin-badge">{context.lines.length} {context.lines.length === 1 ? 'línea' : 'líneas'}</span>}
            />
            <div className="ink-table-scroll">
              <table className="ink-table guide-quantity-table">
                <thead><tr><th>Bien</th><th>Facturado</th><th>Reservado</th><th>Cubierto</th><th>Disponible</th><th>A despachar</th></tr></thead>
                <tbody>{context.lines.map((line) => <tr key={line.id}>
                  <td data-label="Bien"><strong>{line.description}</strong><div className="ink-table-cell__meta">{line.unit} · línea #{line.id}</div>{line.pending_adjustment && <div className="guide-line-warning">Ajuste fiscal pendiente</div>}</td>
                  <td data-label="Facturado" className="font-mono-label">{Number(line.invoiced)}</td>
                  <td data-label="Reservado" className="font-mono-label">{Number(line.reserved)}</td>
                  <td data-label="Cubierto" className="font-mono-label">{Number(line.covered)}</td>
                  <td data-label="Disponible"><span className="guide-available-quantity">{Number(line.available)} {line.unit}</span></td>
                  <td data-label="A despachar">
                    <input
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
                    {line.requires_goods_confirmation && Number(quantities[line.id]) > 0 && <label className="guide-inline-check"><input type="checkbox" checked={Boolean(confirmedGoods[line.id])} onChange={(event) => setConfirmedGoods((current) => ({ ...current, [line.id]: event.target.checked }))} />Confirmo que es un bien</label>}
                  </td>
                </tr>)}</tbody>
              </table>
            </div>
          </section>

          <section className="guide-flow-section guide-flow-section--transport">
            <GuideSectionHeader icon={Truck} title="Traslado y transporte" description="Confirma la ruta, el peso y el escenario que corresponde al vehículo real." />
            <div className="guide-flow-section__body guide-transport-stack">
              <div className="guide-form-grid">
                <FormField label="Fecha de traslado" required>
                  <DatePicker value={form.fecha_traslado} onChange={set('fecha_traslado')} min={today()} required ariaLabel="Fecha de traslado" />
                </FormField>
                <FormField label="Peso bruto" icon={Scale} required>
                  <div className="guide-weight-control">
                    <input aria-label="Peso bruto" required min="0.001" step="0.001" type="number" className="input" value={form.peso_bruto_total} onChange={set('peso_bruto_total')} placeholder="0.000" />
                    <CustomSelect compact ariaLabel="Unidad de peso" value={form.unidad_medida_peso} onChange={set('unidad_medida_peso')} options={[{ value: 'KGM', label: 'KGM' }, { value: 'TNE', label: 'TNE' }]} />
                  </div>
                </FormField>
                <FormField label="Bultos" hint="Opcional cuando no corresponde al traslado.">
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
                  <FormField label="Ubigeo de partida" required><input required readOnly={Boolean(context.source_location?.ready)} inputMode="numeric" pattern="[0-9]{6}" maxLength={6} className="input" value={form.partida_ubigeo} onChange={set('partida_ubigeo')} placeholder="150101" /></FormField>
                  <FormField label="Dirección de partida" required className="md:col-span-2"><input required readOnly={Boolean(context.source_location?.ready)} className="input" value={form.partida_direccion} onChange={set('partida_direccion')} placeholder="Dirección completa de origen" /></FormField>
                  <FormField label="Ubigeo de llegada" required><input required inputMode="numeric" pattern="[0-9]{6}" maxLength={6} className="input" value={form.llegada_ubigeo || ''} onChange={set('llegada_ubigeo')} placeholder="150103" /></FormField>
                  <FormField label="Dirección de llegada" required className="md:col-span-2"><input required className="input" value={form.llegada_direccion || ''} onChange={set('llegada_direccion')} placeholder="Dirección completa de destino" /></FormField>
                </div>
              </div>

              <div className="guide-scenario-block">
                <div className="guide-subsection-title"><Truck size={16} /><span>Modalidad de transporte</span></div>
                <div className="guide-mode-grid" role="group" aria-label="Modalidad de transporte">
                  <button type="button" className={`guide-mode-option ${form.modalidad_traslado === '02' ? 'is-active' : ''}`} aria-pressed={form.modalidad_traslado === '02'} onClick={() => setTransportMode('02')}>
                    <Truck size={18} /><span><strong>Privado</strong><small>Vehículo y conductor del remitente</small></span>
                  </button>
                  <button type="button" className={`guide-mode-option ${form.modalidad_traslado === '01' ? 'is-active' : ''}`} aria-pressed={form.modalidad_traslado === '01'} onClick={() => setTransportMode('01')}>
                    <ShieldCheck size={18} /><span><strong>Público</strong><small>Empresa transportista identificada</small></span>
                  </button>
                </div>

                <label className={`guide-choice-card ${form.indicador_m1_l ? 'is-selected' : ''}`}>
                  <input type="checkbox" checked={form.indicador_m1_l} onChange={setM1L} />
                  <span><strong>Vehículo M1/L</strong><small>Exige placa, pero no datos del conductor.</small></span>
                </label>

                <div key={`${form.modalidad_traslado}-${form.indicador_m1_l}-${form.registrar_vehiculo_transportista}`} className="guide-scenario-panel">
                  {form.modalidad_traslado === '01' && <div className="guide-form-grid">
                    {!form.indicador_m1_l && <>
                      <FormField label="RUC del transportista" required><input required inputMode="numeric" pattern="[0-9]{11}" maxLength={11} className="input" value={form.transportista_ruc} onChange={set('transportista_ruc')} placeholder="20XXXXXXXXX" /></FormField>
                      <FormField label="Razón social" required><input required className="input" value={form.transportista_razon_social} onChange={set('transportista_razon_social')} placeholder="Empresa transportista" /></FormField>
                      <FormField label="Registro MTC" required><input required className="input uppercase" value={form.transportista_nro_mtc} onChange={set('transportista_nro_mtc')} placeholder="Registro vigente" /></FormField>
                    </>}
                    <FormField label="Entrega al transportista" required>
                      <DatePicker value={form.fecha_entrega_transportista} onChange={set('fecha_entrega_transportista')} min={today()} required ariaLabel="Fecha de entrega al transportista" />
                    </FormField>
                    {!form.indicador_m1_l && <label className={`guide-choice-card md:col-span-2 ${form.registrar_vehiculo_transportista ? 'is-selected' : ''}`}><input type="checkbox" checked={form.registrar_vehiculo_transportista} onChange={setCarrierFleet} /><span><strong>Registrar vehículo y conductor del transportista</strong><small>Con el acuerdo correspondiente, este escenario no exige GRE 31.</small></span></label>}
                    {form.registrar_vehiculo_transportista && !form.indicador_m1_l && <label className={`guide-choice-card md:col-span-3 ${form.transportista_acuerdo_confirmado ? 'is-selected' : ''}`}><input required type="checkbox" checked={form.transportista_acuerdo_confirmado} onChange={set('transportista_acuerdo_confirmado')} /><span><strong>Acuerdo confirmado</strong><small>Confirmo que existe autorización para registrar el vehículo y conductor en esta GRE.</small></span></label>}
                  </div>}

                  {(form.indicador_m1_l || form.modalidad_traslado === '02' || form.registrar_vehiculo_transportista) && <div className="guide-form-grid guide-vehicle-grid">
                    <FormField label="Placa" required><input required className="input uppercase" value={form.vehiculo_placa} onChange={set('vehiculo_placa')} placeholder="ABC123" /></FormField>
                    {form.registrar_vehiculo_transportista && !form.indicador_m1_l && <FormField label="Número de circulación" required><input required className="input uppercase" value={form.vehiculo_nro_circulacion} onChange={set('vehiculo_nro_circulacion')} placeholder="Constancia o circulación" /></FormField>}
                    {!form.indicador_m1_l && (form.modalidad_traslado === '02' || form.registrar_vehiculo_transportista) && <>
                      <FormField label="Tipo de documento" required><CustomSelect ariaLabel="Tipo de documento del conductor" value={form.conductor_tipo_doc} onChange={set('conductor_tipo_doc')} options={[{ value: '1', label: 'DNI' }, { value: '4', label: 'Carné de extranjería' }, { value: '6', label: 'RUC' }, { value: '7', label: 'Pasaporte' }]} /></FormField>
                      <FormField label="Documento del conductor" required><input required className="input" value={form.conductor_nro_doc} onChange={set('conductor_nro_doc')} placeholder="Número de documento" /></FormField>
                      <FormField label="Licencia" required><input required className="input uppercase" value={form.conductor_licencia} onChange={set('conductor_licencia')} placeholder="Q12345678" /></FormField>
                      <FormField label="Nombres" required><input required className="input" value={form.conductor_nombres} onChange={set('conductor_nombres')} placeholder="Nombres del conductor" /></FormField>
                      <FormField label="Apellidos" required><input required className="input" value={form.conductor_apellidos} onChange={set('conductor_apellidos')} placeholder="Apellidos del conductor" /></FormField>
                    </>}
                  </div>}

                  {form.modalidad_traslado === '01' && !form.indicador_m1_l && !form.registrar_vehiculo_transportista && <div className="guide-public-notice"><AlertTriangle size={18} /><p><strong>Se requerirá GRE transportista 31.</strong><span>Para este escenario no ingreses conductor ni vehículo. La salida se habilita cuando la GRE 31 esté aceptada y verificada.</span></p></div>}
                </div>
              </div>

              <FormField label="Observaciones" hint={`${form.observaciones.length}/500 caracteres`}>
                <textarea maxLength={500} className="input guide-observations" value={form.observaciones} onChange={set('observaciones')} placeholder="Información adicional relevante para el traslado" />
              </FormField>
            </div>
          </section>

          <div className="guide-form-actions">
            <div><strong>{context.eligibility?.can_reserve ? 'Las cantidades quedarán reservadas' : 'Se guardará como preparación provisional'}</strong><span>Puedes validar y emitir desde el detalle de la guía.</span></div>
            <div className="guide-form-actions__buttons">
              <Link to="/guias" className="btn-secondary">Cancelar</Link>
              <button disabled={saving || !context.eligibility?.can_prepare} className="btn-primary" type="submit">{saving ? <Spinner size="sm" /> : <Save size={16} />}{saving ? 'Guardando…' : 'Guardar borrador'}</button>
            </div>
          </div>
        </>}
      </form>
    </div>
  );
}
