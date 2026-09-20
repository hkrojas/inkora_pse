import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, Plus, Trash2, Truck } from 'lucide-react';
import { guias as svc } from '../services/guias';
import Spinner from '../components/ui/Spinner';
import { useToast } from '../components/ui/Toast';

const today = () => new Date().toISOString().slice(0, 10);
const field = (label, key, form, setForm, props = {}) => <div><label className="label">{label}</label><input className="input" value={form[key]} onChange={(event) => setForm((current) => ({ ...current, [key]: event.target.value }))} {...props} /></div>;

export default function GuiaTransportistaNuevaPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const [saving, setSaving] = useState(false);
  const [items, setItems] = useState([{ descripcion: '', cantidad: '1', unidad_medida: 'NIU', codigo_producto: '' }]);
  const [form, setForm] = useState({
    gre_ruc: '', gre_serie: 'T001', gre_numero: '', factura_ruc: '', factura_serie: 'F001', factura_numero: '',
    remitente_nro_doc: '', remitente_razon_social: '', destinatario_tipo_doc: '6', destinatario_nro_doc: '', destinatario_razon_social: '',
    fecha_traslado: today(), peso_bruto_total: '', numero_bultos: '', partida_ubigeo: '', partida_direccion: '', llegada_ubigeo: '', llegada_direccion: '',
    transportista_nro_mtc: '', vehiculo_placa: '', vehiculo_nro_circulacion: '', conductor_nro_doc: '', conductor_nombres: '', conductor_apellidos: '', conductor_licencia: '',
  });

  const submit = async (event) => {
    event.preventDefault(); setSaving(true);
    try {
      const guide = await svc.createTransport({
        idempotency_key: crypto.randomUUID(), modalidad_traslado: '01',
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
      });
      toast('Borrador GRE transportista creado con el RUC de esta empresa.', 'success');
      navigate(`/guias/${guide.id}`);
    } catch (error) { toast(error.message, 'error'); } finally { setSaving(false); }
  };

  return <div className="page-shell max-w-6xl">
    <div className="page-header"><div className="page-header-copy"><Link to="/guias" className="mb-4 inline-flex items-center gap-2 text-sm text-[var(--text-secondary)]"><ArrowLeft size={16} />Volver a guías</Link><p className="page-kicker">Empresa transportista</p><h2 className="page-title">Nueva GRE transportista 31</h2><p className="page-subtitle">El emisor y transportista se derivan de la empresa autenticada. La factura indicada es la de los bienes, no la del flete.</p></div></div>
    <form onSubmit={submit} className="space-y-6">
      <section className="ink-card p-5"><h3 className="ink-card-title">Referencias externas</h3><div className="mt-4 grid gap-4 md:grid-cols-3">{field('RUC emisor GRE 09', 'gre_ruc', form, setForm, { required: true, pattern: '[0-9]{11}' })}{field('Serie GRE 09', 'gre_serie', form, setForm, { required: true, maxLength: 4 })}{field('Número GRE 09', 'gre_numero', form, setForm, { required: true })}{field('RUC emisor factura de bienes', 'factura_ruc', form, setForm, { required: true, pattern: '[0-9]{11}' })}{field('Serie factura', 'factura_serie', form, setForm, { required: true, maxLength: 4 })}{field('Número factura', 'factura_numero', form, setForm, { required: true })}</div></section>
      <section className="ink-card p-5"><h3 className="ink-card-title">Sujetos y traslado</h3><div className="mt-4 grid gap-4 md:grid-cols-3">{field('RUC remitente', 'remitente_nro_doc', form, setForm, { required: true, pattern: '[0-9]{11}' })}{field('Razón social remitente', 'remitente_razon_social', form, setForm, { required: true })}{field('Documento destinatario', 'destinatario_nro_doc', form, setForm, { required: true })}{field('Razón social destinatario', 'destinatario_razon_social', form, setForm, { required: true })}{field('Fecha traslado', 'fecha_traslado', form, setForm, { required: true, type: 'date' })}{field('Peso bruto KGM', 'peso_bruto_total', form, setForm, { required: true, type: 'number', min: '0.001', step: '0.001' })}{field('Bultos', 'numero_bultos', form, setForm, { type: 'number', min: '1' })}{field('Ubigeo partida', 'partida_ubigeo', form, setForm, { required: true, pattern: '[0-9]{6}' })}{field('Dirección partida', 'partida_direccion', form, setForm, { required: true })}{field('Ubigeo llegada', 'llegada_ubigeo', form, setForm, { required: true, pattern: '[0-9]{6}' })}{field('Dirección llegada', 'llegada_direccion', form, setForm, { required: true })}</div></section>
      <section className="ink-card p-5"><h3 className="ink-card-title flex items-center gap-2"><Truck size={16} />Flota y conductor</h3><div className="mt-4 grid gap-4 md:grid-cols-3">{field('Registro MTC', 'transportista_nro_mtc', form, setForm)}{field('Placa', 'vehiculo_placa', form, setForm, { required: true })}{field('Nro. circulación', 'vehiculo_nro_circulacion', form, setForm)}{field('Documento conductor', 'conductor_nro_doc', form, setForm, { required: true })}{field('Nombres', 'conductor_nombres', form, setForm, { required: true })}{field('Apellidos', 'conductor_apellidos', form, setForm, { required: true })}{field('Licencia', 'conductor_licencia', form, setForm, { required: true })}</div></section>
      <section className="ink-table-card"><div className="ink-card-header"><h3 className="ink-card-title">Bienes transportados</h3><button type="button" className="btn-secondary" onClick={() => setItems((current) => [...current, { descripcion: '', cantidad: '1', unidad_medida: 'NIU', codigo_producto: '' }])}><Plus size={14} />Agregar</button></div><div className="ink-table-scroll"><table className="ink-table"><thead><tr><th>Descripción</th><th>Código</th><th>Cantidad</th><th>Unidad</th><th /></tr></thead><tbody>{items.map((item, index) => <tr key={index}><td><input required className="input" value={item.descripcion} onChange={(e) => setItems((current) => current.map((row, i) => i === index ? { ...row, descripcion: e.target.value } : row))} /></td><td><input className="input" value={item.codigo_producto} onChange={(e) => setItems((current) => current.map((row, i) => i === index ? { ...row, codigo_producto: e.target.value } : row))} /></td><td><input required className="input" type="number" min="0.0001" step="0.0001" value={item.cantidad} onChange={(e) => setItems((current) => current.map((row, i) => i === index ? { ...row, cantidad: e.target.value } : row))} /></td><td>NIU</td><td><button type="button" className="ink-row-btn" disabled={items.length === 1} onClick={() => setItems((current) => current.filter((_, i) => i !== index))}><Trash2 size={14} /></button></td></tr>)}</tbody></table></div></section>
      <div className="flex justify-end gap-3"><Link to="/guias" className="btn-secondary">Cancelar</Link><button className="btn-primary" disabled={saving}>{saving && <Spinner size="sm" />}Guardar borrador 31</button></div>
    </form>
  </div>;
}
