import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Building2,
  CreditCard,
  Download,
  FileText,
  Filter,
  Mail,
  MapPin,
  MessageCircle,
  Pencil,
  Phone,
  Plus,
  Save,
  Search,
  Trash2,
  Upload,
  User,
  ClipboardList,
  Truck,
} from 'lucide-react';
import { clientes as svc } from '../services/clientes';
import Spinner from '../components/ui/Spinner';
import EmptyState from '../components/ui/EmptyState';
import Drawer from '../components/ui/Drawer';
import CustomSelect from '../components/ui/CustomSelect';
import FormField from '../components/ui/FormField';
import Pagination from '../components/ui/Pagination';
import { PageError } from '../components/ui/PageState';
import { useToast } from '../components/ui/Toast';
import useDebouncedValue from '../hooks/useDebouncedValue';
import { normalizePeruMobileInput, validatePeruMobilePhone } from '../lib/utils/peruPhoneValidation';
import {
  getLookupAddress,
  getLookupCommercialName,
  getLookupDocumentType,
  getLookupName,
  getLookupUbigeo,
} from '../lib/utils/documentLookup';
import { normalizeUppercaseFieldValue, normalizeUppercaseShape } from '../lib/utils/uppercase';
import OperationalPageHeader from '../components/ui/OperationalPageHeader';

const DOC_TYPE_OPTIONS = [
  { value: '6', label: 'RUC' },
  { value: '1', label: 'DNI' },
  { value: '4', label: 'Carnet de extranjeria' },
  { value: '7', label: 'Pasaporte' },
  { value: '0', label: 'Doc. trib. no dom. s/ RUC' },
  { value: 'A', label: 'Cedula diplomatica' },
];

const DOC_TYPE_META = {
  '6': { label: 'RUC', placeholder: 'Ej. 20100200300', maxLength: 11, inputMode: 'numeric', lookupEnabled: true },
  '1': { label: 'DNI', placeholder: 'Ej. 12345678', maxLength: 8, inputMode: 'numeric', lookupEnabled: true },
  '4': { label: 'Carnet de extranjeria', placeholder: 'Ej. CE1234567', maxLength: 15, inputMode: 'text', lookupEnabled: false },
  '7': { label: 'Pasaporte', placeholder: 'Ej. P1234567', maxLength: 15, inputMode: 'text', lookupEnabled: false },
  '0': { label: 'Doc. trib. no dom. s/ RUC', placeholder: 'Ej. EXT123456', maxLength: 15, inputMode: 'text', lookupEnabled: false },
  A: { label: 'Cedula diplomatica', placeholder: 'Ej. CD123456', maxLength: 15, inputMode: 'text', lookupEnabled: false },
};

const EMPTY_FORM = {
  tipo_documento: '6',
  numero_documento: '',
  razon_social: '',
  nombre_comercial: '',
  direccion: '',
  ubigeo: '',
  email: '',
  telefono: '',
  whatsapp: '',
  contacto: '',
  condicion_pago: 'contado',
  direccion_entrega: '',
  observaciones: '',
};

function getDocMeta(tipoDocumento) {
  return DOC_TYPE_META[tipoDocumento] || {
    label: 'Documento',
    placeholder: 'Numero de documento',
    maxLength: 15,
    inputMode: 'text',
    lookupEnabled: false,
  };
}

function getDocumentLabel(tipoDocumento) {
  return getDocMeta(tipoDocumento).label;
}

function normalizeDocumentNumber(tipoDocumento, rawValue) {
  const value = String(rawValue || '').trim().toUpperCase().replace(/\s+/g, '');
  if (tipoDocumento === '6' || tipoDocumento === '1') {
    return value.replace(/\D/g, '').slice(0, getDocMeta(tipoDocumento).maxLength);
  }
  return value.slice(0, getDocMeta(tipoDocumento).maxLength);
}

function normalizeUbigeo(rawValue) {
  return String(rawValue || '').replace(/\D/g, '').slice(0, 6);
}

function validateDocumentNumber(tipoDocumento, numeroDocumento) {
  const value = String(numeroDocumento || '').trim();
  if (!value) return 'Numero de documento es obligatorio.';
  if (tipoDocumento === '6' && !/^\d{11}$/.test(value)) return 'RUC debe tener exactamente 11 digitos.';
  if (tipoDocumento === '1' && !/^\d{8}$/.test(value)) return 'DNI debe tener exactamente 8 digitos.';
  if (value.length < 3) return 'Numero de documento demasiado corto.';
  return undefined;
}

function validateUbigeo(value) {
  const ubigeo = String(value || '').trim();
  if (!ubigeo) return undefined;
  if (!/^\d{6}$/.test(ubigeo)) return 'Ubigeo debe tener exactamente 6 digitos.';
  return undefined;
}

function normalizeClientForm(initial) {
  return normalizeUppercaseShape({
    ...EMPTY_FORM,
    ...initial,
    numero_documento: normalizeDocumentNumber(initial?.tipo_documento || '6', initial?.numero_documento || ''),
    ubigeo: normalizeUbigeo(initial?.ubigeo || ''),
    telefono: normalizePeruMobileInput(initial?.telefono || ''),
    whatsapp: normalizePeruMobileInput(initial?.whatsapp || ''),
  });
}

function getClientDisplayName(item = {}) {
  return (
    item.razon_social ||
    item.nombre_comercial ||
    item.nombre ||
    item.cliente_nombre ||
    item.email ||
    'Cliente sin nombre'
  );
}

function isCompany(item = {}) {
  return item.tipo_documento === '6' || String(item.numero_documento || '').length === 11;
}

function getCommercialGaps(item = {}) {
  const gaps = [];
  if (!item.email) gaps.push('correo');
  if (!(item.telefono || item.whatsapp)) gaps.push('teléfono o WhatsApp');
  if (!item.direccion) gaps.push('dirección');
  if (!item.condicion_pago) gaps.push('condición comercial');
  return gaps;
}

function isIncomplete(item = {}) {
  return getCommercialGaps(item).length > 0;
}

function getInitials(name) {
  if (!name) return '??';
  const parts = name.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  return parts[0].slice(0, 2).toUpperCase();
}

const AVATAR_COLORS = ['a-green', 'a-purple', 'a-yellow', 'a-red', 'a-blue'];

function getAvatarColor(item) {
  if (!item?.id) return 'a-green';
  const code = String(item.id).charCodeAt(0) || 0;
  return AVATAR_COLORS[code % AVATAR_COLORS.length];
}

function getPaymentLabel(item = {}) {
  const value = item.condicion_pago;
  if (!value) return 'Sin condición';
  return value
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function getPaymentTone(item = {}) {
  const value = item.condicion_pago;
  if (!value) return 'risk';
  if (value === 'contado') return 'cash';
  if (value.startsWith('credito')) return 'credit';
  return 'ok';
}

function validateClientForm(form) {
  const nextErrors = {
    numero_documento: validateDocumentNumber(form.tipo_documento, form.numero_documento),
    razon_social: !String(form.razon_social || '').trim() ? 'Razon social / Nombre es obligatorio.' : undefined,
    direccion: undefined,
    ubigeo: validateUbigeo(form.ubigeo),
    email: undefined,
    telefono: validatePeruMobilePhone(form.telefono, 'Telefono') || undefined,
    whatsapp: validatePeruMobilePhone(form.whatsapp, 'WhatsApp') || undefined,
  };

  if (form.email?.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
    nextErrors.email = 'Email no tiene un formato valido.';
  }

  if (form.tipo_documento === '6') {
    if (!String(form.direccion || '').trim()) {
      nextErrors.direccion = 'Direccion fiscal es obligatoria para clientes con RUC.';
    }
    if (!String(form.ubigeo || '').trim()) {
      nextErrors.ubigeo = 'Ubigeo es obligatorio para clientes con RUC.';
    }
  }

  return nextErrors;
}

function ClienteForm({ initial = EMPTY_FORM, onSave, onCancel, saving }) {
  const toast = useToast();
  const [form, setForm] = useState(() => normalizeClientForm(initial));
  const [errors, setErrors] = useState({});
  const [lookupLoading, setLookupLoading] = useState(false);
  const [lookupHint, setLookupHint] = useState('');
  const docMeta = getDocMeta(form.tipo_documento);

  useEffect(() => {
    setForm(normalizeClientForm(initial));
    setErrors({});
    setLookupHint('');
    setLookupLoading(false);
  }, [initial]);

  const set = (key) => (event) => {
    const nextValue = normalizeUppercaseFieldValue(key, event.target.value);
    setForm((current) => ({ ...current, [key]: nextValue }));
    setErrors((current) => ({ ...current, [key]: undefined }));
  };

  const setTipoDocumento = (value) => {
    setForm((current) => ({
      ...current,
      tipo_documento: value,
      numero_documento: normalizeDocumentNumber(value, current.numero_documento),
    }));
    setLookupHint('');
    setErrors((current) => ({
      ...current,
      numero_documento: undefined,
      direccion: undefined,
      ubigeo: undefined,
    }));
  };

  const setDocumentNumber = (event) => {
    const nextValue = normalizeDocumentNumber(form.tipo_documento, event.target.value);
    setForm((current) => ({ ...current, numero_documento: nextValue }));
    setLookupHint('');
    setErrors((current) => ({ ...current, numero_documento: undefined }));
  };

  const setUbigeo = (event) => {
    const nextValue = normalizeUbigeo(event.target.value);
    setForm((current) => ({ ...current, ubigeo: nextValue }));
    setErrors((current) => ({ ...current, ubigeo: undefined }));
  };

  const setMobile = (key) => (event) => {
    const nextValue = normalizePeruMobileInput(event.target.value);
    setForm((current) => ({ ...current, [key]: nextValue }));
    setErrors((current) => ({
      ...current,
      [key]: validatePeruMobilePhone(nextValue, key === 'whatsapp' ? 'WhatsApp' : 'Telefono') || undefined,
    }));
  };

  const handleLookup = async () => {
    const numero = form.numero_documento.trim();
    if (!numero) {
      setErrors((current) => ({
        ...current,
        numero_documento: 'Ingresa un RUC o DNI para consultar.',
      }));
      return;
    }

    setLookupLoading(true);
    setLookupHint('');
    setErrors((current) => ({ ...current, numero_documento: undefined }));

    try {
      const data = await svc.lookupDocument(numero);
      const resolvedName = getLookupName(data);
      const resolvedAddress = getLookupAddress(data);
      const resolvedDocumentType = getLookupDocumentType(data, form.tipo_documento);

      setForm((current) => ({
        ...current,
        tipo_documento: resolvedDocumentType,
        razon_social: resolvedName || current.razon_social,
        nombre_comercial: getLookupCommercialName(data) || current.nombre_comercial,
        direccion: resolvedAddress || current.direccion,
        ubigeo: normalizeUbigeo(getLookupUbigeo(data) || current.ubigeo || ''),
      }));

      setLookupHint(resolvedName ? 'Datos fiscales encontrados y completados.' : 'Consulta realizada. Completa el nombre manualmente.');
      toast('Documento consultado');
    } catch (err) {
      const message = err?.message || 'No se pudo consultar el documento.';
      setErrors((current) => ({ ...current, numero_documento: message }));
      toast(message, 'error');
    } finally {
      setLookupLoading(false);
    }
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    const nextErrors = validateClientForm(form);
    setErrors(nextErrors);
    if (Object.values(nextErrors).some(Boolean)) return;

    const payload = { ...form };
    if (!payload.nombre_comercial) delete payload.nombre_comercial;
    if (!payload.ubigeo) delete payload.ubigeo;
    if (!payload.email) delete payload.email;
    if (!payload.telefono) payload.telefono = null;
    if (!payload.whatsapp) payload.whatsapp = null;
    if (!payload.contacto) delete payload.contacto;
    if (!payload.direccion_entrega) delete payload.direccion_entrega;
    if (!payload.observaciones) delete payload.observaciones;

    onSave(payload);
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-5">
      <div className="ink-form-section">
        <h4 className="mb-3 flex items-center gap-2 text-[11px] font-extrabold uppercase tracking-wider text-[var(--color-text-muted)]">
          <FileText className="h-3.5 w-3.5" />
          Identidad fiscal
        </h4>
        <p className="mb-4 text-[12px] text-[var(--color-text-muted)]">
          Campos usados en emision fiscal: tipo, numero, razon social, direccion fiscal y ubigeo.
        </p>
        <div className="grid gap-4 md:grid-cols-3">
          <FormField label="Tipo documento" icon={FileText}>
            <CustomSelect
              value={form.tipo_documento}
              onChange={setTipoDocumento}
              options={DOC_TYPE_OPTIONS}
            />
          </FormField>
          <FormField
            label="Numero documento"
            icon={FileText}
            className="md:col-span-2"
            required
            error={errors.numero_documento}
            hint={!errors.numero_documento && lookupHint ? lookupHint : undefined}
          >
            <div className="relative">
              <input
                required
                className="input pr-24"
                value={form.numero_documento}
                onChange={setDocumentNumber}
                placeholder={docMeta.placeholder}
                maxLength={docMeta.maxLength}
                inputMode={docMeta.inputMode}
              />
              {docMeta.lookupEnabled && (
                <button
                  type="button"
                  onClick={handleLookup}
                  disabled={lookupLoading || !form.numero_documento.trim()}
                  className="label-action-btn absolute right-2 top-1/2 -translate-y-1/2"
                >
                  {lookupLoading ? <Spinner size="sm" /> : <Search className="h-3 w-3" />}
                  Consultar
                </button>
              )}
            </div>
          </FormField>
        </div>

        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <FormField label="Razon social / Nombre" icon={Building2} required error={errors.razon_social}>
            <input
              required
              className="input"
              value={form.razon_social}
              onChange={set('razon_social')}
              placeholder="Nombre completo o razon social"
            />
          </FormField>
          <FormField label="Nombre comercial" icon={Building2}>
            <input
              className="input"
              value={form.nombre_comercial || ''}
              onChange={set('nombre_comercial')}
              placeholder="Nombre comercial (opcional)"
            />
          </FormField>
        </div>
      </div>

      <div className="ink-form-section">
        <h4 className="mb-3 flex items-center gap-2 text-[11px] font-extrabold uppercase tracking-wider text-[var(--color-text-muted)]">
          <MapPin className="h-3.5 w-3.5" />
          Ubicacion
        </h4>
        <p className="mb-4 text-[12px] text-[var(--color-text-muted)]">
          Para clientes con RUC, direccion fiscal y ubigeo deben quedar completos.
        </p>
        <div className="grid gap-4 md:grid-cols-2">
          <FormField label="Direccion fiscal" icon={MapPin} error={errors.direccion}>
            <input
              className="input"
              value={form.direccion || ''}
              onChange={set('direccion')}
              placeholder="Direccion fiscal"
            />
          </FormField>
          <FormField label="Ubigeo" icon={MapPin} error={errors.ubigeo}>
            <input
              className="input"
              value={form.ubigeo || ''}
              onChange={setUbigeo}
              placeholder="Codigo ubigeo (ej. 150101)"
              maxLength={6}
              inputMode="numeric"
            />
          </FormField>
        </div>
        <div className="mt-4">
          <FormField label="Direccion de entrega" icon={Truck}>
            <input
              className="input"
              value={form.direccion_entrega || ''}
              onChange={set('direccion_entrega')}
              placeholder="Direccion de entrega (si difiere de la fiscal)"
            />
          </FormField>
        </div>
      </div>

      <div className="ink-form-section">
        <h4 className="mb-3 flex items-center gap-2 text-[11px] font-extrabold uppercase tracking-wider text-[var(--color-text-muted)]">
          <Mail className="h-3.5 w-3.5" />
          Contacto
        </h4>
        <p className="mb-4 text-[12px] text-[var(--color-text-muted)]">
          Datos comerciales opcionales para identificar al receptor fiscal y facilitar el seguimiento.
        </p>
        <div className="grid gap-4 md:grid-cols-2">
          <FormField label="Persona de contacto" icon={User}>
            <input
              className="input"
              value={form.contacto || ''}
              onChange={set('contacto')}
              placeholder="Nombre del contacto (opcional)"
            />
          </FormField>
          <FormField label="Email" icon={Mail} error={errors.email}>
            <input
              type="email"
              className="input"
              value={form.email || ''}
              onChange={set('email')}
              placeholder="correo@ejemplo.com"
            />
          </FormField>
          <FormField label="Telefono" icon={Phone} error={errors.telefono}>
            <input
              className="input"
              value={form.telefono || ''}
              onChange={setMobile('telefono')}
              inputMode="numeric"
              placeholder="999999999"
            />
          </FormField>
          <FormField label="WhatsApp" icon={MessageCircle} error={errors.whatsapp}>
            <input
              className="input"
              value={form.whatsapp || ''}
              onChange={setMobile('whatsapp')}
              inputMode="numeric"
              placeholder="999999999"
            />
          </FormField>
        </div>
      </div>

      <div className="ink-form-section">
        <h4 className="mb-3 flex items-center gap-2 text-[11px] font-extrabold uppercase tracking-wider text-[var(--color-text-muted)]">
          <CreditCard className="h-3.5 w-3.5" />
          Condicion comercial
        </h4>
        <div className="grid gap-4 md:grid-cols-2">
          <FormField label="Condicion de pago" icon={CreditCard}>
            <CustomSelect
              value={form.condicion_pago}
              onChange={(value) => setForm((current) => ({ ...current, condicion_pago: value }))}
              options={[
                { value: 'contado', label: 'Contado' },
                { value: 'credito_7', label: 'Credito 7 dias' },
                { value: 'credito_15', label: 'Credito 15 dias' },
                { value: 'credito_30', label: 'Credito 30 dias' },
                { value: 'credito_60', label: 'Credito 60 dias' },
              ]}
            />
          </FormField>
          <FormField label="Observaciones" icon={ClipboardList}>
            <input
              className="input"
              value={form.observaciones || ''}
              onChange={set('observaciones')}
              placeholder="Notas internas (opcional)"
            />
          </FormField>
        </div>
      </div>

      <div className="flex items-center justify-end gap-3 pt-2">
        <button type="button" onClick={onCancel} className="btn-secondary">
          Cancelar
        </button>
        <button type="submit" disabled={saving} className="btn-primary flex items-center gap-2">
          {saving ? <Spinner size="sm" /> : <Save className="h-4 w-4" />}
          Guardar cliente
        </button>
      </div>
    </form>
  );
}

export default function ClientesPage() {
  const toast = useToast();
  const [searchParams] = useSearchParams();
  const [list, setList] = useState([]);
  const [total, setTotal] = useState(0);
  const [counts, setCounts] = useState({ all: 0, empresa: 0, persona: 0, credito: 0, incompletos: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState(() => searchParams.get('q') || '');
  const debouncedSearch = useDebouncedValue(search, 300);
  const [segment, setSegment] = useState('all');
  const [page, setPage] = useState(1);
  const [modal, setModal] = useState(null);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(null);
  const requestSeq = useRef(0);

  const load = useCallback(() => {
    const seq = requestSeq.current + 1;
    requestSeq.current = seq;
    setLoading(true);
    setError(null);
    const params = new URLSearchParams({
      skip: String((page - 1) * 15),
      limit: '15',
      segment,
    });
    if (debouncedSearch.trim()) params.set('q', debouncedSearch.trim());
    svc.page(`?${params.toString()}`)
      .then((data) => {
        if (requestSeq.current !== seq) return;
        setList(data.items || []);
        setTotal(data.total || 0);
        setCounts(data.counts || { all: 0, empresa: 0, persona: 0, credito: 0, incompletos: 0 });
      })
      .catch((err) => {
        if (requestSeq.current !== seq) return;
        setError(err);
        setList([]);
        setTotal(0);
        setCounts({ all: 0, empresa: 0, persona: 0, credito: 0, incompletos: 0 });
        toast(err.message || 'No se pudo cargar la información. Revisa tu conexión e inténtalo nuevamente.', 'error');
      })
      .finally(() => {
        if (requestSeq.current === seq) setLoading(false);
      });
  }, [debouncedSearch, page, segment, toast]);

  useEffect(load, [load]);

  useEffect(() => {
    const query = searchParams.get('q') || '';
    setSearch((current) => (current === query ? current : query));
  }, [searchParams]);

  useEffect(() => {
    setPage(1);
  }, [debouncedSearch, segment]);

  const stats = useMemo(() => {
    const activos = counts.all || 0;
    const conCredito = counts.credito || 0;
    const incompletos = counts.incompletos || 0;
    const conDeuda = counts.credito || 0;
    return { activos, conCredito, conDeuda, incompletos };
  }, [counts]);

  const filtered = list;
  const totalPages = Math.max(1, Math.ceil(total / 15));

  const handleSave = async (form) => {
    setSaving(true);
    try {
      if (modal.mode === 'create') {
        await svc.create(form);
        toast('Cliente creado');
      } else {
        await svc.update(modal.item.id, form);
        toast('Cliente actualizado');
      }
      setModal(null);
      load();
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Eliminar este cliente?')) return;
    setDeleting(id);
    try {
      await svc.remove(id);
      toast('Cliente eliminado');
      load();
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      setDeleting(null);
    }
  };

  const isEditing = modal?.mode === 'edit';

  const segments = [
    { key: 'all', label: `Todos ${counts.all}` },
    { key: 'empresa', label: `Empresas ${counts.empresa}` },
    { key: 'persona', label: `Personas ${counts.persona}` },
    { key: 'credito', label: `Con deuda ${counts.credito}` },
    { key: 'incompletos', label: `Datos incompletos ${counts.incompletos}` },
  ];

  return (
    <div className="clients-page">
      <OperationalPageHeader
        eyebrow="Directorio comercial"
        title="Clientes"
        description={`${counts.all} registros disponibles para cotización, emisión y cobranza.`}
        meta={<span className="operational-page-header__scope">Base comercial compartida</span>}
        actions={<>
          <button type="button" className="btn" style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
            <Upload size={15} />
            Importar
          </button>
          <button type="button" className="btn" style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
            <Download size={15} />
            Exportar
          </button>
          <button type="button" className="btn-primary" onClick={() => setModal({ mode: 'create' })} style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
            <Plus size={15} />
            Nuevo cliente
          </button>
        </>}
      />

      <section className="stats-row ink-enter-2">
        <article className="stat">
          <div className="stat-label">Clientes activos</div>
          <div className="stat-value">{stats.activos}</div>
          <div className="stat-foot good">Registrados en este tenant</div>
        </article>
        <article className="stat">
          <div className="stat-label">Con crédito</div>
          <div className="stat-value">{stats.conCredito}</div>
          <div className="stat-foot warn">Condición comercial a crédito</div>
        </article>
        <article className="stat">
          <div className="stat-label">Con deuda</div>
          <div className="stat-value">{stats.conDeuda}</div>
          <div className="stat-foot bad">Requieren seguimiento comercial</div>
        </article>
        <article className="stat">
          <div className="stat-label">Datos incompletos</div>
          <div className="stat-value">{stats.incompletos}</div>
          <div className="stat-foot">Falta correo, teléfono o condición</div>
        </article>
      </section>

      <article className="panel ink-enter-3">
        <div className="toolbar">
          <label className="search-box">
            <Search size={16} />
            <input
              placeholder="Buscar por nombre, RUC/DNI, correo o teléfono..."
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </label>
          <div className="toolbar-actions">
            <button type="button" className="btn" style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
              <Filter size={15} />
              Filtrar
            </button>
            <button type="button" className="btn-primary" onClick={() => setModal({ mode: 'create' })} style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
              <Plus size={15} />
              Nuevo cliente
            </button>
          </div>
        </div>

        <div className="segments-row">
          <div className="segments">
            {segments.map(({ key, label }) => (
              <button
                key={key}
                type="button"
                className={`segment ${segment === key ? 'active' : ''}`}
                onClick={() => setSegment(key)}
              >
                {label}
              </button>
            ))}
          </div>
          <div className="sort-text">Ordenar por: <strong>Ultima actividad</strong></div>
        </div>

        {error && !loading ? (
          <div style={{ padding: '40px 18px' }}>
            <PageError error={error} onRetry={load} />
          </div>
        ) : loading ? (
          <div style={{ padding: '40px 18px' }}>
            <Spinner />
          </div>
        ) : filtered.length === 0 ? (
          <div style={{ padding: '40px 18px' }}>
            <EmptyState
              title="Sin clientes"
              description="No hay resultados con los filtros actuales."
              action={
                <button className="btn-primary" onClick={() => setModal({ mode: 'create' })}>
                  Agregar cliente
                </button>
              }
            />
          </div>
        ) : (
          <>
            <div className="client-list">
              <div className="list-head">
                <div>Cliente</div>
                <div>Contacto</div>
                <div>Condición</div>
                <div>Actividad / saldo</div>
                <div style={{ textAlign: 'right' }}>Acción</div>
              </div>

              {filtered.map((item) => {
                const company = isCompany(item);
                const commercialGaps = getCommercialGaps(item);
                const incomplete = commercialGaps.length > 0;
                const debtTone = (item.condicion_pago || 'contado') === 'contado' ? 'zero' : 'owed';
                return (
                  <div key={item.id} className="client-row">
                    <div className="client-main">
                      <div className={`client-avatar ${getAvatarColor(item)}`}>
                        {getInitials(getClientDisplayName(item))}
                      </div>
                      <div style={{ minWidth: 0 }}>
                        <div className="client-name-line">
                          <div className="client-name">{getClientDisplayName(item)}</div>
                          <span className={`pill ${company ? 'company' : 'person'}`}>
                            {company ? 'Empresa' : 'Persona'}
                          </span>
                        </div>
                        <div className="meta">
                          {getDocumentLabel(item.tipo_documento)} {item.numero_documento || 'Sin documento'}
                          {item.direccion ? ` · ${item.direccion}` : ''}
                        </div>
                      </div>
                    </div>

                    <div className="contact-block">
                      <strong>{item.email || 'Sin correo principal'}</strong>
                      <span>{item.telefono || item.whatsapp || 'Falta teléfono o WhatsApp'}</span>
                    </div>

                    <div className="commercial">
                      <span className={`pill ${getPaymentTone(item)}`}>{getPaymentLabel(item)}</span>
                      <span className={`pill ${incomplete ? 'risk' : 'ok'}`}>{incomplete ? 'Revisión' : 'Activo'}</span>
                    </div>

                    <div className="activity-block">
                      <strong>{incomplete ? 'Ficha comercial pendiente' : 'Ficha comercial completa'}</strong>
                      <span className={`debt ${debtTone}`}>
                        {incomplete
                          ? `Pendiente: ${commercialGaps.join(', ')}.`
                          : 'Listo para cotizar, emitir y cobrar.'}
                      </span>
                    </div>

                    <div className="actions-col">
                      <button
                        type="button"
                        className="edit-btn"
                        onClick={() => setModal({ mode: 'edit', item })}
                      >
                        <Pencil size={13} />
                        Editar
                      </button>
                      <button
                        type="button"
                        className="more-btn"
                        onClick={() => handleDelete(item.id)}
                        disabled={deleting === item.id}
                        title="Eliminar"
                      >
                        {deleting === item.id ? <Spinner size="sm" /> : <Trash2 size={14} />}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="table-footer">
              <div>Mostrando <strong>{filtered.length}</strong> de <strong>{total}</strong> clientes</div>
              <Pagination
                page={page}
                totalPages={totalPages}
                onPageChange={setPage}
                ariaLabel="Paginacion de clientes"
              />
            </div>
          </>
        )}
      </article>

      <Drawer
        open={!!modal}
        onClose={() => setModal(null)}
        variant="editor"
        eyebrow="Relación comercial"
        status={isEditing ? 'Edición' : 'Nuevo registro'}
        initialFocus="input, select, textarea"
        title={isEditing ? 'Editar cliente' : 'Nuevo cliente'}
        subtitle={isEditing ? 'Actualiza los datos comerciales sin salir del listado.' : 'Registra un cliente para cotizar, emitir y cobrar con datos ordenados.'}
        icon={<Building2 size={22} />}
      >
        {modal && (
          <ClienteForm
            initial={isEditing ? modal.item : EMPTY_FORM}
            onSave={handleSave}
            onCancel={() => setModal(null)}
            saving={saving}
          />
        )}
      </Drawer>
    </div>
  );
}
