import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, Pencil, Plus, Trash2, Truck } from 'lucide-react';
import { guias as svc } from '../services/guias';
import GuideLookup from '../components/guides/GuideLookup';
import DatePicker from '../components/ui/DatePicker';
import Spinner from '../components/ui/Spinner';
import { useToast } from '../components/ui/Toast';
import { GuideField, GuideForm, GuideFormErrors, useGuideFormFeedback } from '../components/guides/GuideFormFeedback';
import '../styles/carrierGuideWizard.css';

const today = () => new Date().toLocaleDateString('en-CA', { timeZone: 'America/Lima' });
const steps = ['Documentos', 'Ruta y transporte', 'Carga y revisión'];
const documentFields = ['gre_ruc', 'gre_serie', 'gre_numero', 'factura_ruc', 'factura_serie', 'factura_numero', 'remitente_nro_doc', 'remitente_razon_social', 'destinatario_nro_doc', 'destinatario_razon_social'];
const extraFields = ['transportista_nro_mtc', 'vehiculo_nro_circulacion'];
const fieldStep = (name) => documentFields.includes(name) ? 1 : name.startsWith('lines.') || ['peso_bruto_total', 'numero_bultos'].includes(name) ? 3 : 2;
const errorAliases = {
  'gre_remitente.issuer_ruc': 'gre_ruc', 'gre_remitente.series': 'gre_serie', 'gre_remitente.number': 'gre_numero',
  'goods_invoice.issuer_ruc': 'factura_ruc', 'goods_invoice.series': 'factura_serie', 'goods_invoice.number': 'factura_numero',
};
const hints = {
  partida_ubigeo: 'Código de 6 dígitos del distrito de salida.',
  llegada_ubigeo: 'Código de 6 dígitos del distrito de entrega.',
  conductor_nro_doc: 'Ingresa los 8 dígitos del DNI del conductor.',
  conductor_licencia: 'Puedes consultarla con el DNI o copiarla de la licencia del conductor.',
  transportista_nro_mtc: 'Registro de la empresa de transporte ante el MTC.',
  vehiculo_nro_circulacion: 'Número de la constancia o tarjeta de circulación.',
};
const field = (label, key, form, setForm, props = {}, lookup) => (
  <GuideField name={key} label={label} required={props.required} hint={hints[key]} lookup={lookup}>
    <input className="input" inputMode={/ruc|ubigeo|nro_doc|numero/.test(key) ? 'numeric' : undefined}
      value={form[key]} onChange={(event) => setForm((current) => ({ ...current, [key]: key === 'vehiculo_placa' ? event.target.value.toUpperCase().replace(/[-\s]/g, '') : event.target.value }))} {...props} />
  </GuideField>
);

function GuideLineError({ feedback, name }) {
  return feedback.errors[name] ? <p className="guide-field-error" id={`${feedback.control(name).id}-error`}>{feedback.errors[name]}</p> : null;
}

export default function GuiaTransportistaNuevaPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const [step, setStep] = useState(1);
  const [extraTransportOpen, setExtraTransportOpen] = useState(false);
  const stepHeading = useRef(null);
  const saveAttempt = useRef({});
  const inFlight = useRef(false);
  const feedback = useGuideFormFeedback({ onFieldFocus: (name) => {
    setStep(fieldStep(name));
    if (extraFields.includes(name)) setExtraTransportOpen(true);
  } });
  const [saving, setSaving] = useState(false);
  const [items, setItems] = useState([{ descripcion: '', cantidad: '1', unidad_medida: 'NIU', codigo_producto: '' }]);
  const [form, setForm] = useState({
    gre_ruc: '', gre_serie: 'T001', gre_numero: '', factura_ruc: '', factura_serie: 'F001', factura_numero: '',
    remitente_nro_doc: '', remitente_razon_social: '', destinatario_tipo_doc: '6', destinatario_nro_doc: '', destinatario_razon_social: '',
    fecha_traslado: today(), peso_bruto_total: '', numero_bultos: '', partida_ubigeo: '', partida_direccion: '', llegada_ubigeo: '', llegada_direccion: '',
    transportista_nro_mtc: '', vehiculo_placa: '', vehiculo_nro_circulacion: '', conductor_nro_doc: '', conductor_nombres: '', conductor_apellidos: '', conductor_licencia: '',
  });
  useEffect(() => { stepHeading.current?.focus(); }, [step]);
  const changeStep = (next) => { feedback.reset(); setStep(next); };
  const changeItem = (index, key, value) => setItems((current) => current.map((row, i) => i === index ? { ...row, [key]: value } : row));
  const lookup = (kind, source, targets) => <GuideLookup kind={kind} form={form} setForm={setForm} source={source} targets={targets} onApplied={(keys) => keys.forEach(feedback.clearField)} />;

  const submit = async (event) => {
    event.preventDefault();
    if (inFlight.current) return;
    if (step < 3) { setStep(step + 1); return; }
    const emptyLine = items.findIndex((item) => !item.descripcion.trim());
    if (emptyLine >= 0) { feedback.show({ [`lines.${emptyLine}.descripcion`]: 'Escribe qué producto vas a transportar.' }); return; }
    inFlight.current = true;
    setSaving(true);
    try {
      const payload = {
        modalidad_traslado: '01',
        gre_remitente: { document_type: '09', issuer_ruc: form.gre_ruc, series: form.gre_serie.toUpperCase(), number: form.gre_numero },
        goods_invoice: { document_type: '01', issuer_ruc: form.factura_ruc, series: form.factura_serie.toUpperCase(), number: form.factura_numero },
        remitente_tipo_doc: '6', remitente_nro_doc: form.remitente_nro_doc, remitente_razon_social: form.remitente_razon_social,
        destinatario_tipo_doc: form.destinatario_tipo_doc, destinatario_nro_doc: form.destinatario_nro_doc, destinatario_razon_social: form.destinatario_razon_social,
        fecha_traslado: new Date(`${form.fecha_traslado}T12:00:00-05:00`).toISOString(), peso_bruto_total: Number(form.peso_bruto_total), unidad_medida_peso: 'KGM',
        numero_bultos: form.numero_bultos ? Number(form.numero_bultos) : null,
        partida_ubigeo: form.partida_ubigeo, partida_direccion: form.partida_direccion, llegada_ubigeo: form.llegada_ubigeo, llegada_direccion: form.llegada_direccion,
        transportista_nro_mtc: form.transportista_nro_mtc || null, vehiculo_placa: form.vehiculo_placa, vehiculo_nro_circulacion: form.vehiculo_nro_circulacion || null,
        conductor_tipo_doc: '1', conductor_nro_doc: form.conductor_nro_doc, conductor_nombres: form.conductor_nombres, conductor_apellidos: form.conductor_apellidos, conductor_licencia: form.conductor_licencia,
        lines: items.map((item) => ({ ...item, cantidad: Number(item.cantidad), codigo_producto: item.codigo_producto || null })),
      };
      const signature = JSON.stringify(payload);
      if (saveAttempt.current.signature !== signature) saveAttempt.current = { signature, key: crypto.randomUUID() };
      const guide = await svc.createTransport({ ...payload, idempotency_key: saveAttempt.current.key });
      toast('Borrador guardado. Puedes revisar la guía antes de emitirla.', 'success');
      navigate(`/guias/${guide.id}`);
    } catch (error) { feedback.reportError(error, errorAliases); }
    finally { inFlight.current = false; setSaving(false); }
  };

  return <div className="page-shell max-w-6xl carrier-guide-wizard">
    <div className="page-header"><div className="page-header-copy">
      <Link to="/guias" className="mb-4 inline-flex items-center gap-2 text-sm text-[var(--color-text-muted)]"><ArrowLeft size={16} />Volver a guías</Link>
      <p className="page-kicker">Empresa transportista · GRE 31</p>
      <h2 className="page-title">Nueva guía transportista</h2>
      <p className="page-subtitle">Prepara el traslado en tres pasos. La guía se guardará como borrador antes de emitirla.</p>
    </div></div>
    <GuideForm feedback={feedback} onSubmit={submit} validateHidden={step === 3} className="space-y-6 guide-accessible-form">
      <ol className="guide-wizard-steps" aria-label="Pasos para crear la guía transportista">
        {steps.map((title, index) => <li key={title} aria-current={step === index + 1 ? 'step' : undefined}>
          <button type="button" disabled={index + 1 > step || saving} onClick={() => changeStep(index + 1)}><span>{index + 1}</span>{title}</button>
        </li>)}
      </ol>
      <h3 ref={stepHeading} tabIndex={-1} className="guide-step-heading">Paso {step} de 3 · {step === 1 ? 'Documentos y participantes' : steps[step - 1]}</h3>
      <GuideFormErrors />

      <div hidden={step !== 1} className="carrier-guide__step" data-carrier-step="1">
        <section className="ink-card carrier-guide__section" aria-labelledby="carrier-documents-heading">
          <h3 id="carrier-documents-heading" className="ink-card-title">Documentos del traslado</h3>
          <p className="guide-field-hint">Ten a mano la guía del remitente y la factura de los productos. Copia sus datos tal como aparecen.</p>
          <h4 className="carrier-guide__subheading">Guía del remitente</h4>
          <div className="carrier-guide__grid carrier-guide__grid--documents">
            {field('RUC de quien emitió la guía', 'gre_ruc', form, setForm, { required: true, pattern: '[0-9]{11}', maxLength: 11 })}
            {field('Serie de la guía', 'gre_serie', form, setForm, { required: true, minLength: 4, maxLength: 4 })}
            {field('Número de la guía', 'gre_numero', form, setForm, { required: true, pattern: '[0-9]{1,8}', maxLength: 8 })}
          </div>
          <h4 className="carrier-guide__subheading">Factura de los productos</h4>
          <p className="guide-field-hint">Usa la factura de los productos que llevarás, no la del servicio de transporte.</p>
          <div className="carrier-guide__grid carrier-guide__grid--documents">
            {field('RUC de quien emitió la factura', 'factura_ruc', form, setForm, { required: true, pattern: '[0-9]{11}', maxLength: 11 })}
            {field('Serie de la factura', 'factura_serie', form, setForm, { required: true, minLength: 4, maxLength: 4 })}
            {field('Número de la factura', 'factura_numero', form, setForm, { required: true, pattern: '[0-9]{1,8}', maxLength: 8 })}
          </div>
        </section>
        <section className="ink-card carrier-guide__section" aria-labelledby="carrier-people-heading">
          <h3 id="carrier-people-heading" className="ink-card-title">Quién envía y quién recibe</h3>
          <h4 className="carrier-guide__subheading">Quién envía</h4>
          <div className="carrier-guide__grid">
            {field('RUC de quien envía', 'remitente_nro_doc', form, setForm, { required: true, pattern: '[0-9]{11}', maxLength: 11 }, lookup('RUC', 'remitente_nro_doc', { remitente_razon_social: 'razon_social' }))}
            {field('Nombre o razón social de quien envía', 'remitente_razon_social', form, setForm, { required: true })}
          </div>
          <h4 className="carrier-guide__subheading">Quién recibe</h4>
          <div className="carrier-guide__grid">
            {field('RUC de quien recibe', 'destinatario_nro_doc', form, setForm, { required: true, pattern: '[0-9]{11}', maxLength: 11 }, lookup('RUC', 'destinatario_nro_doc', { destinatario_razon_social: 'razon_social' }))}
            {field('Nombre o razón social de quien recibe', 'destinatario_razon_social', form, setForm, { required: true })}
          </div>
        </section>
      </div>

      <div hidden={step !== 2} className="carrier-guide__step" data-carrier-step="2">
        <section className="ink-card carrier-guide__section" aria-labelledby="carrier-route-heading">
          <h3 id="carrier-route-heading" className="ink-card-title">Ruta del traslado</h3>
          <div className="carrier-guide__grid carrier-guide__date">
            <GuideField name="fecha_traslado" label="Fecha de salida" required><DatePicker value={form.fecha_traslado} min={today()} onChange={(value) => setForm((current) => ({ ...current, fecha_traslado: value }))} required ariaLabel="Fecha de salida" /></GuideField>
          </div>
          <h4 className="carrier-guide__subheading">Punto de salida</h4>
          <div className="carrier-guide__grid">
            {field('Ubigeo de salida', 'partida_ubigeo', form, setForm, { required: true, pattern: '[0-9]{6}', maxLength: 6 })}
            {field('Dirección de salida', 'partida_direccion', form, setForm, { required: true })}
          </div>
          <h4 className="carrier-guide__subheading">Punto de llegada</h4>
          <div className="carrier-guide__grid">
            {field('Ubigeo de llegada', 'llegada_ubigeo', form, setForm, { required: true, pattern: '[0-9]{6}', maxLength: 6 })}
            {field('Dirección de llegada', 'llegada_direccion', form, setForm, { required: true })}
          </div>
        </section>
        <section className="ink-card carrier-guide__section" aria-labelledby="carrier-transport-heading">
          <h3 id="carrier-transport-heading" className="ink-card-title flex items-center gap-2"><Truck size={16} aria-hidden="true" />Vehículo y conductor</h3>
          <div className="carrier-guide__grid carrier-guide__spaced">
            {field('Placa', 'vehiculo_placa', form, setForm, { required: true }, lookup('placa', 'vehiculo_placa'))}
            {field('DNI del conductor', 'conductor_nro_doc', form, setForm, { required: true, pattern: '[0-9]{8}', maxLength: 8 }, lookup('DNI', 'conductor_nro_doc', { conductor_nombres: 'nombres', conductor_apellidos: 'apellidos' }))}
            {field('Nombres', 'conductor_nombres', form, setForm, { required: true })}
            {field('Apellidos', 'conductor_apellidos', form, setForm, { required: true })}
            {field('Licencia de conducir', 'conductor_licencia', form, setForm, { required: true }, lookup('licencia', 'conductor_nro_doc', { conductor_licencia: 'numero' }))}
          </div>
          <details className="guide-advanced-options carrier-guide__extras" open={extraTransportOpen} onToggle={(event) => setExtraTransportOpen(event.currentTarget.open)}>
            <summary>Otros datos del transporte (opcional)</summary>
            <div className="carrier-guide__grid">
              {field('Registro MTC', 'transportista_nro_mtc', form, setForm)}
              {field('Número de circulación', 'vehiculo_nro_circulacion', form, setForm)}
            </div>
          </details>
        </section>
      </div>

      <div hidden={step !== 3} className="carrier-guide__step" data-carrier-step="3">
        <section className="ink-table-card carrier-guide__goods" aria-labelledby="carrier-goods-heading">
          <div className="ink-card-header"><h3 id="carrier-goods-heading" className="ink-card-title">Productos a transportar</h3>
            <button type="button" className="btn-secondary" disabled={saving} onClick={() => { feedback.reset(); setItems((current) => [...current, { descripcion: '', cantidad: '1', unidad_medida: 'NIU', codigo_producto: '' }]); }}><Plus size={14} aria-hidden="true" />Agregar producto</button>
          </div>
          <table className="ink-table" role="table"><thead role="rowgroup"><tr role="row"><th scope="col">Descripción</th><th scope="col">Código (opcional)</th><th scope="col">Cantidad</th><th scope="col">Unidad</th><th scope="col"><span className="sr-only">Acciones</span></th></tr></thead>
            <tbody role="rowgroup">{items.map((item, index) => <tr key={index} role="row">
              <td role="cell" data-label="Descripción" className="carrier-guide__description"><input {...feedback.control(`lines.${index}.descripcion`)} aria-label={`Descripción del bien ${index + 1}`} data-field-label={`Producto ${index + 1}`} required className="input" value={item.descripcion} onChange={(event) => changeItem(index, 'descripcion', event.target.value)} /><GuideLineError feedback={feedback} name={`lines.${index}.descripcion`} /></td>
              <td role="cell" data-label="Código (opcional)"><input {...feedback.control(`lines.${index}.codigo_producto`)} aria-label={`Código del bien ${index + 1}`} data-field-label={`Código del producto ${index + 1}`} className="input" value={item.codigo_producto} onChange={(event) => changeItem(index, 'codigo_producto', event.target.value)} /><GuideLineError feedback={feedback} name={`lines.${index}.codigo_producto`} /></td>
              <td role="cell" data-label="Cantidad"><input {...feedback.control(`lines.${index}.cantidad`)} aria-label={`Cantidad del bien ${index + 1}`} data-field-label={`Cantidad del producto ${index + 1}`} required className="input" type="number" min="0.0001" step="0.0001" value={item.cantidad} onChange={(event) => changeItem(index, 'cantidad', event.target.value)} /><GuideLineError feedback={feedback} name={`lines.${index}.cantidad`} /></td>
              <td role="cell" data-label="Unidad">Unidades</td>
              <td role="cell" className="carrier-guide__remove"><button type="button" className="ink-row-btn" aria-label={`Quitar producto ${index + 1}`} disabled={saving || items.length === 1} onClick={() => { feedback.reset(); setItems((current) => current.filter((_, i) => i !== index)); }}><Trash2 size={16} aria-hidden="true" /></button></td>
            </tr>)}</tbody>
          </table>
        </section>
        <section className="ink-card carrier-guide__section" aria-labelledby="carrier-weight-heading">
          <h3 id="carrier-weight-heading" className="ink-card-title">Peso y paquetes</h3>
          <div className="carrier-guide__grid carrier-guide__spaced">
            {field('Peso total (kg)', 'peso_bruto_total', form, setForm, { required: true, type: 'number', min: '0.001', step: '0.001' })}
            {field('Número de bultos (opcional)', 'numero_bultos', form, setForm, { type: 'number', min: '1' })}
          </div>
        </section>
        <section className="ink-card carrier-guide__section" aria-label="Resumen de la guía transportista">
          <h3 className="ink-card-title">Revisa antes de guardar</h3>
          <div className="carrier-guide__review-heading"><h4>Documentos y participantes</h4><button type="button" className="btn-secondary" disabled={saving} onClick={() => changeStep(1)}><Pencil size={14} aria-hidden="true" />Editar documentos y participantes</button></div>
          <dl className="guide-review-grid">
            <div><dt>Guía del remitente</dt><dd>{form.gre_serie.toUpperCase()}-{form.gre_numero} · RUC {form.gre_ruc}</dd></div>
            <div><dt>Factura de los productos</dt><dd>{form.factura_serie.toUpperCase()}-{form.factura_numero} · RUC {form.factura_ruc}</dd></div>
            <div><dt>Quién envía</dt><dd>{form.remitente_razon_social} · {form.remitente_nro_doc}</dd></div>
            <div><dt>Quién recibe</dt><dd>{form.destinatario_razon_social} · {form.destinatario_nro_doc}</dd></div>
          </dl>
          <div className="carrier-guide__review-heading"><h4>Ruta y transporte</h4><button type="button" className="btn-secondary" disabled={saving} onClick={() => changeStep(2)}><Pencil size={14} aria-hidden="true" />Editar ruta y transporte</button></div>
          <dl className="guide-review-grid">
            <div><dt>Fecha de salida</dt><dd>{form.fecha_traslado.split('-').reverse().join('/')}</dd></div>
            <div><dt>Vehículo</dt><dd>{form.vehiculo_placa}{form.vehiculo_nro_circulacion && ` · Circulación ${form.vehiculo_nro_circulacion}`}</dd></div>
            <div><dt>Salida</dt><dd>{form.partida_direccion} · {form.partida_ubigeo}</dd></div>
            <div><dt>Llegada</dt><dd>{form.llegada_direccion} · {form.llegada_ubigeo}</dd></div>
            <div><dt>Conductor</dt><dd>{form.conductor_nombres} {form.conductor_apellidos} · DNI {form.conductor_nro_doc}</dd></div>
            <div><dt>Licencia de conducir</dt><dd>{form.conductor_licencia}</dd></div>
            {form.transportista_nro_mtc && <div><dt>Registro MTC</dt><dd>{form.transportista_nro_mtc}</dd></div>}
          </dl>
          <p className="guide-field-hint">Los productos, el peso y los bultos se muestran arriba. Puedes corregirlos aquí antes de guardar.</p>
        </section>
      </div>
      <div className="carrier-guide__footer">
        <p className="guide-field-hint">{step === 3 ? 'Guardar crea un borrador. Todavía no se envía a SUNAT.' : 'Puedes volver sin perder tus datos. Continuar no guarda ni emite la guía.'}</p>
        <div className="carrier-guide__actions">
          {step > 1 ? <button type="button" disabled={saving} className="btn-secondary" onClick={() => changeStep(step - 1)}>Atrás</button> : <Link to="/guias" className="btn-secondary">Cancelar</Link>}
          <button type="submit" className="btn-primary" disabled={saving} aria-busy={saving || undefined}>{saving && <Spinner size="sm" />}{step < 3 ? 'Continuar' : saving ? 'Guardando…' : 'Guardar borrador'}</button>
        </div>
      </div>
    </GuideForm>
  </div>;
}
