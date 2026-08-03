import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Barcode,
  Boxes,
  DollarSign,
  Download,
  Package,
  Pencil,
  Plus,
  Percent,
  RefreshCw,
  Ruler,
  Save,
  Search,
  Tag,
  Trash2,
} from 'lucide-react';
import { productos as svc } from '../services/productos';
import Spinner from '../components/ui/Spinner';
import EmptyState from '../components/ui/EmptyState';
import Drawer from '../components/ui/Drawer';
import FormField from '../components/ui/FormField';
import CustomSelect from '../components/ui/CustomSelect';
import Pagination from '../components/ui/Pagination';
import { PageError } from '../components/ui/PageState';
import { useToast } from '../components/ui/Toast';
import useDebouncedValue from '../hooks/useDebouncedValue';
import OperationalPageHeader from '../components/ui/OperationalPageHeader';
import {
  PRODUCT_DESCRIPTION_MAX_LENGTH,
  PRODUCT_INTERNAL_CODE_MAX_LENGTH,
  PRODUCT_NAME_MAX_LENGTH,
  SUNAT_TAX_AFFECTATION_OPTIONS,
  SUNAT_UNIT_OPTIONS,
  isTaxedAffectation,
  isValidInternalProductCode,
  isValidSunatUnitCode,
  isValidTaxAffectationCode,
  normalizeInternalProductCode,
  normalizeSunatUnitCode,
} from '../lib/utils/sunatCatalogs';
import { forceUppercaseText, normalizeUppercaseFieldValue, normalizeUppercaseShape } from '../lib/utils/uppercase';

const IGV_FACTOR = 1.18;
const AVATAR_COLORS = ['a-green', 'a-blue', 'a-purple', 'a-yellow', 'a-red'];

const EMPTY_FORM = {
  nombre: '',
  descripcion: '',
  moneda: 'PEN',
  precio_unitario: '',
  precio_incluye_igv: true,
  unidad_medida: 'NIU',
  tipo_afectacion_igv: '10',
  codigo_interno: '',
};

const MONEDA_OPTIONS = [
  { value: 'PEN', label: 'Soles (PEN)' },
  { value: 'USD', label: 'Dolares (USD)' },
];

function normalizeProductPayload(form) {
  return {
    ...form,
    nombre: form.nombre.trim(),
    descripcion: form.descripcion?.trim() || null,
    codigo_interno: normalizeInternalProductCode(form.codigo_interno) || null,
    moneda: form.moneda || 'PEN',
    unidad_medida: normalizeSunatUnitCode(form.unidad_medida),
    tipo_afectacion_igv: form.tipo_afectacion_igv || '10',
    precio_unitario: Number(form.precio_unitario),
  };
}

function escapeCsv(value) {
  const normalized = value == null ? '' : String(value);
  return `"${normalized.replace(/"/g, '""')}"`;
}

function formatCurrency(value) {
  return Number(value || 0).toLocaleString('es-PE', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function getCurrencySymbol(moneda = 'PEN') {
  return moneda === 'USD' ? '$' : 'S/';
}

function getProductKind(item = {}) {
  return item.unidad_medida === 'ZZ' ? 'Servicio' : 'Producto';
}

function isProductActive(item = {}) {
  return item.activo !== false && item.estado !== 'inactivo';
}

function getInitials(name) {
  if (!name) return '??';
  const parts = String(name).split(/\s+/).filter(Boolean);
  if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  return parts[0].slice(0, 2).toUpperCase();
}

function getAvatarColor(item) {
  if (!item?.id) return 'a-green';
  const code = String(item.id).charCodeAt(0) || 0;
  return AVATAR_COLORS[code % AVATAR_COLORS.length];
}

function ProductoForm({ initial = EMPTY_FORM, onSave, onCancel, saving, onGenerateCode }) {
  const [form, setForm] = useState({
    ...EMPTY_FORM,
    ...initial,
    moneda: initial?.moneda || 'PEN',
    unidad_medida: normalizeSunatUnitCode(initial?.unidad_medida || 'NIU'),
    tipo_afectacion_igv: initial?.tipo_afectacion_igv || '10',
    precio_incluye_igv: initial?.precio_incluye_igv ?? true,
  });
  const [errors, setErrors] = useState({});
  const [generatingCode, setGeneratingCode] = useState(false);

  useEffect(() => {
    setForm(normalizeUppercaseShape({
      ...EMPTY_FORM,
      ...initial,
      moneda: initial?.moneda || 'PEN',
      unidad_medida: normalizeSunatUnitCode(initial?.unidad_medida || 'NIU'),
      tipo_afectacion_igv: initial?.tipo_afectacion_igv || '10',
      precio_incluye_igv: initial?.precio_incluye_igv ?? true,
    }));
    setErrors({});
  }, [initial]);

  const set = (key) => (event) =>
    setForm((current) => {
      const value = key === 'codigo_interno'
        ? forceUppercaseText(event.target.value)
        : normalizeUppercaseFieldValue(key, event.target.value);
      return { ...current, [key]: value };
    });

  const validate = (nextForm = form) => {
    const nextErrors = {};
    if (!nextForm.nombre.trim()) nextErrors.nombre = 'Ingresa el nombre del producto o servicio.';
    if (nextForm.nombre.trim().length > PRODUCT_NAME_MAX_LENGTH) {
      nextErrors.nombre = `El nombre debe tener ${PRODUCT_NAME_MAX_LENGTH} caracteres como máximo.`;
    }
    if ((nextForm.descripcion || '').trim().length > PRODUCT_DESCRIPTION_MAX_LENGTH) {
      nextErrors.descripcion = `La descripción debe tener ${PRODUCT_DESCRIPTION_MAX_LENGTH} caracteres como máximo.`;
    }
    const precio = Number(nextForm.precio_unitario);
    if (!Number.isFinite(precio) || precio <= 0) {
      nextErrors.precio_unitario = 'Ingresa un precio mayor a cero.';
    }
    if (!isValidSunatUnitCode(nextForm.unidad_medida)) {
      nextErrors.unidad_medida = 'Selecciona una unidad SUNAT válida.';
    }
    if (!isValidTaxAffectationCode(nextForm.tipo_afectacion_igv)) {
      nextErrors.tipo_afectacion_igv = 'Selecciona una afectación IGV válida.';
    }
    const codigo = normalizeInternalProductCode(nextForm.codigo_interno);
    if (codigo && codigo.length > PRODUCT_INTERNAL_CODE_MAX_LENGTH) {
      nextErrors.codigo_interno = `El SKU debe tener ${PRODUCT_INTERNAL_CODE_MAX_LENGTH} caracteres como máximo.`;
    } else if (!isValidInternalProductCode(codigo)) {
      nextErrors.codigo_interno = 'Usa solo letras, números, punto, guion, slash o guion bajo.';
    }
    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    if (!validate()) return;
    onSave(normalizeProductPayload(form));
  };

  const handleGenerateCode = async () => {
    if (!onGenerateCode || generatingCode) return;
    setGeneratingCode(true);
    try {
      const codigo = await onGenerateCode();
      if (codigo) {
        setForm((current) => ({ ...current, codigo_interno: codigo.toUpperCase() }));
        setErrors((current) => ({ ...current, codigo_interno: undefined }));
      }
    } finally {
      setGeneratingCode(false);
    }
  };

  const precioIngresado = Number(form.precio_unitario || 0);
  const isGravado = isTaxedAffectation(form.tipo_afectacion_igv);
  const precioBase = isGravado && form.precio_incluye_igv
    ? precioIngresado / IGV_FACTOR
    : precioIngresado;
  const precioFinal = isGravado && !form.precio_incluye_igv
    ? precioIngresado * IGV_FACTOR
    : precioIngresado;
  const showPreview = Number.isFinite(precioIngresado) && precioIngresado > 0;
  const currencySymbol = getCurrencySymbol(form.moneda);

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-5">
      <div className="ink-form-section">
        <h4 className="mb-3 flex items-center gap-2 text-[11px] font-extrabold uppercase tracking-wider text-[var(--color-text-muted)]">
          <Package className="h-3.5 w-3.5" />
          Información del producto
        </h4>
        <div className="flex flex-col gap-4">
          <FormField label="Nombre" icon={Tag} required error={errors.nombre}>
            <input
              required
              maxLength={PRODUCT_NAME_MAX_LENGTH}
              className="input"
              value={form.nombre}
              onChange={set('nombre')}
              onBlur={() => validate()}
              placeholder="Ej. Impresión A4 full color"
            />
          </FormField>
          <FormField label="Descripción" icon={Boxes} error={errors.descripcion}>
            <textarea
              maxLength={PRODUCT_DESCRIPTION_MAX_LENGTH}
              className="input min-h-[80px] resize-none"
              rows={2}
              value={form.descripcion}
              onChange={set('descripcion')}
              placeholder="Descripción del producto o servicio"
            />
          </FormField>
        </div>
      </div>

      <div className="ink-form-section">
        <h4 className="mb-3 flex items-center gap-2 text-[11px] font-extrabold uppercase tracking-wider text-[var(--color-text-muted)]">
          <DollarSign className="h-3.5 w-3.5" />
          Precio y unidad
        </h4>
        <div className="grid gap-4 md:grid-cols-2">
          <FormField
            label={isGravado && form.precio_incluye_igv ? 'Precio (con IGV)' : 'Precio (sin IGV)'}
            icon={DollarSign}
            error={errors.precio_unitario}
          >
            <div className="relative">
              <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 font-mono text-sm font-bold text-[var(--color-text-soft)]">
                {currencySymbol}
              </span>
              <input
                required
                type="number"
                step="0.0001"
                min="0"
                className="input pl-8 text-right font-mono font-bold"
                value={form.precio_unitario}
                onChange={set('precio_unitario')}
                onBlur={() => validate()}
              />
            </div>
            {showPreview && (
              <div className="mt-2 rounded-lg bg-[var(--color-surface-soft)] p-2.5 text-xs leading-relaxed text-[var(--color-text-muted)]">
                <div className="flex justify-between">
                  <span>{isGravado ? 'Base sin IGV:' : 'Base no gravada:'}</span>
                  <span className="font-mono font-bold text-[var(--color-text)]">{currencySymbol} {formatCurrency(precioBase)}</span>
                </div>
                <div className="flex justify-between">
                  <span>IGV:</span>
                  <span className="font-mono font-bold text-[var(--color-text)]">
                    {currencySymbol} {formatCurrency(precioFinal - precioBase)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Precio final:</span>
                  <span className="font-mono font-bold text-[var(--color-primary)]">{currencySymbol} {formatCurrency(precioFinal)}</span>
                </div>
              </div>
            )}
          </FormField>

          <FormField label="Moneda" icon={DollarSign}>
            <CustomSelect
              value={form.moneda}
              onChange={(value) => setForm((current) => ({ ...current, moneda: value }))}
              options={MONEDA_OPTIONS}
            />
          </FormField>

          <FormField label="Modo de registro">
            <CustomSelect
              value={form.precio_incluye_igv ? 'con_igv' : 'sin_igv'}
              onChange={(value) =>
                setForm((current) => ({ ...current, precio_incluye_igv: value === 'con_igv' }))
              }
              disabled={!isGravado}
              options={[
                { value: 'con_igv', label: 'Con IGV incluido' },
                { value: 'sin_igv', label: 'Sin IGV (precio base)' },
              ]}
            />
            {!isGravado && (
              <p className="mt-2 text-xs text-[var(--color-text-muted)]">
                Para exonerado o inafecto se registra el precio final sin IGV.
              </p>
            )}
          </FormField>

          <FormField label="Unidad de medida" icon={Ruler} error={errors.unidad_medida}>
            <CustomSelect
              value={form.unidad_medida}
              onChange={(value) => setForm((current) => ({
                ...current,
                unidad_medida: normalizeSunatUnitCode(value),
              }))}
              options={SUNAT_UNIT_OPTIONS}
            />
          </FormField>

          <FormField label="Afectacion IGV SUNAT" icon={Percent} error={errors.tipo_afectacion_igv}>
            <CustomSelect
              value={form.tipo_afectacion_igv}
              onChange={(value) => setForm((current) => ({
                ...current,
                tipo_afectacion_igv: value,
                precio_incluye_igv: value === '10' ? current.precio_incluye_igv : false,
              }))}
              options={SUNAT_TAX_AFFECTATION_OPTIONS}
            />
          </FormField>

          <FormField label="Código SKU" icon={Barcode} error={errors.codigo_interno}>
            <div className="relative">
              <input
                maxLength={PRODUCT_INTERNAL_CODE_MAX_LENGTH}
                className="input pr-20 font-mono font-semibold uppercase"
                value={form.codigo_interno}
                onChange={set('codigo_interno')}
                onBlur={() => validate()}
                placeholder="Ej. IMP-A4-FC"
              />
              <button
                type="button"
                className="label-action-btn absolute right-2 top-1/2 -translate-y-1/2"
                onClick={handleGenerateCode}
                disabled={generatingCode}
              >
                {generatingCode ? <Spinner size="sm" /> : <RefreshCw className="h-3 w-3" />}
                Generar
              </button>
            </div>
          </FormField>
        </div>
      </div>

      <div className="flex items-center justify-end gap-3 pt-2">
        <button type="button" onClick={onCancel} className="btn-secondary">
          Cancelar
        </button>
        <button type="submit" disabled={saving} className="btn-primary flex items-center gap-2">
          {saving ? <Spinner size="sm" /> : <Save className="h-4 w-4" />}
          Guardar producto
        </button>
      </div>
    </form>
  );
}

export default function ProductosPage() {
  const toast = useToast();
  const [searchParams] = useSearchParams();
  const [list, setList] = useState([]);
  const [total, setTotal] = useState(0);
  const [counts, setCounts] = useState({ all: 0, productos: 0, servicios: 0, con_sku: 0, con_precio: 0 });
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
    svc
      .page(`?${params.toString()}`)
      .then((data) => {
        if (requestSeq.current !== seq) return;
        setList(data.items || []);
        setTotal(data.total || 0);
        setCounts(data.counts || { all: 0, productos: 0, servicios: 0, con_sku: 0, con_precio: 0 });
      })
      .catch((err) => {
        if (requestSeq.current !== seq) return;
        setError(err);
        setList([]);
        setTotal(0);
        setCounts({ all: 0, productos: 0, servicios: 0, con_sku: 0, con_precio: 0 });
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
    const productos = counts.productos || 0;
    const servicios = counts.servicios || 0;
    const conSku = counts.con_sku || 0;
    const conPrecio = counts.con_precio || 0;
    return { productos, servicios, conSku, conPrecio };
  }, [counts]);

  const filtered = list;
  const pristineEmpty = !loading && !error && counts.all === 0 && !search.trim() && segment === 'all';
  const totalPages = Math.max(1, Math.ceil(total / 15));

  const handleExport = () => {
    if (filtered.length === 0) {
      toast('No hay productos para exportar.', 'error');
      return;
    }

    const headers = [
      'nombre',
      'descripcion',
      'codigo_interno',
      'tipo',
      'unidad_medida',
      'tipo_afectacion_igv',
      'moneda',
      'precio_unitario',
      'valor_unitario',
      'estado',
    ];
    const rows = filtered.map((item) => [
      item.nombre,
      item.descripcion,
      item.codigo_interno,
      getProductKind(item),
      item.unidad_medida,
      item.tipo_afectacion_igv || '10',
      item.moneda || 'PEN',
      item.precio_unitario,
      item.valor_unitario,
      isProductActive(item) ? 'activo' : 'inactivo',
    ]);
    const csv = [headers, ...rows]
      .map((row) => row.map(escapeCsv).join(','))
      .join('\n');
    const blob = new Blob([`\uFEFF${csv}`], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `productos-${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const handleGenerateCode = async () => {
    try {
      const data = await svc.generateCode();
      return data.codigo;
    } catch (err) {
      toast(err.message, 'error');
      return null;
    }
  };

  const handleSave = async (form) => {
    setSaving(true);
    try {
      const payload = {
        ...form,
        moneda: form.moneda || 'PEN',
        precio_unitario: Number(form.precio_unitario),
      };
      if (modal.mode === 'create') {
        await svc.create(payload);
        toast('Producto creado');
      } else {
        await svc.update(modal.item.id, payload);
        toast('Producto actualizado');
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
    if (!confirm('Eliminar este producto?')) return;
    setDeleting(id);
    try {
      await svc.remove(id);
      toast('Producto eliminado');
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
    { key: 'productos', label: `Productos ${counts.productos}` },
    { key: 'servicios', label: `Servicios ${counts.servicios}` },
    { key: 'con_sku', label: `Con SKU ${counts.con_sku}` },
    { key: 'con_precio', label: `Con precio ${counts.con_precio}` },
  ];

  return (
    <div className="productos-page">
      <OperationalPageHeader
        eyebrow="Catálogo reutilizable"
        title="Productos y servicios"
        description={`${counts.all} productos y servicios disponibles para cotizaciones, facturas y guías.`}
        meta={<span className="operational-page-header__scope">Catálogo para venta y despacho</span>}
        actions={<>
          <button
            type="button"
            className="btn"
            onClick={handleExport}
            style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}
          >
            <Download size={15} />
            Exportar
          </button>
          <button
            type="button"
            className="btn-primary"
            onClick={() => setModal({ mode: 'create' })}
            style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}
          >
            <Plus size={15} />
            Nuevo producto
          </button>
        </>}
      />

      {!pristineEmpty && <section className="stats-row ink-enter-2">
        <article className="stat">
          <div className="stat-label">Productos</div>
          <div className="stat-value">{stats.productos}</div>
          <div className="stat-foot good">Ítems físicos en catálogo</div>
        </article>
        <article className="stat">
          <div className="stat-label">Servicios</div>
          <div className="stat-value">{stats.servicios}</div>
          <div className="stat-foot">Unidad ZZ disponibles</div>
        </article>
        <article className="stat">
          <div className="stat-label">Con código SKU</div>
          <div className="stat-value">{stats.conSku}</div>
          <div className={`stat-foot ${counts.all - stats.conSku > 0 ? 'warn' : 'good'}`}>
            {counts.all - stats.conSku > 0
              ? `${counts.all - stats.conSku} sin código`
              : 'Todos con código'}
          </div>
        </article>
        <article className="stat">
          <div className="stat-label">Con precio definido</div>
          <div className="stat-value">{stats.conPrecio}</div>
          <div className="stat-foot good">Listos para cotizar</div>
        </article>
      </section>}

      <article className="panel ink-enter-3">
        {!pristineEmpty && <>
        <div className="toolbar">
          <label className="search-box">
            <Search size={16} />
            <input
              placeholder="Buscar por nombre, código o SKU..."
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </label>
          <div className="toolbar-actions">
            <button
              type="button"
              className="btn-primary"
              onClick={() => setModal({ mode: 'create' })}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}
            >
              <Plus size={15} />
              Nuevo producto
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
          <div className="sort-text">
            Ordenar por: <strong>Nombre</strong>
          </div>
        </div>
        </>}

        {error ? (
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
              variant={pristineEmpty ? 'onboarding' : 'default'}
              title={pristineEmpty ? 'Crea tu primer producto o servicio' : 'Sin productos para esta vista'}
              description="Agrega productos o servicios para acelerar tu operación comercial."
              action={
                <button className="btn-primary" onClick={() => setModal({ mode: 'create' })}>
                  Agregar producto
                </button>
              }
            />
          </div>
        ) : (
          <>
            <div className="product-list">
              <div className="product-list-head">
                <div>Producto / Servicio</div>
                <div>SKU</div>
                <div>Tipo / U.M.</div>
                <div>Precio</div>
                <div>Estado</div>
                <div style={{ textAlign: 'right' }}>Acción</div>
              </div>

              {filtered.map((item) => {
                const kind = getProductKind(item);
                const active = isProductActive(item);
                const currencySymbol = getCurrencySymbol(item.moneda);
                return (
                  <div key={item.id} className="product-row">
                    <div className="client-main">
                      <div className={`client-avatar ${getAvatarColor(item)}`}>
                        {getInitials(item.nombre)}
                      </div>
                      <div style={{ minWidth: 0 }}>
                        <div className="client-name">{item.nombre}</div>
                        <div className="meta">
                          {item.descripcion || 'Sin descripción comercial.'}
                        </div>
                      </div>
                    </div>

                    <div className="contact-block">
                      <strong style={{ fontFamily: 'var(--font-mono)', fontSize: '13px' }}>
                        {item.codigo_interno || '—'}
                      </strong>
                    </div>

                    <div className="commercial">
                      <span className={`pill ${kind === 'Servicio' ? 'person' : 'company'}`}>
                        {kind}
                      </span>
                      <span className="pill ok">{item.unidad_medida}</span>
                      <span className="pill new">IGV {item.tipo_afectacion_igv || '10'}</span>
                    </div>

                    <div className="activity-block">
                      <strong>{currencySymbol} {formatCurrency(item.precio_unitario)}</strong>
                      <span>
                        Base {currencySymbol}{' '}
                        {formatCurrency(
                          item.valor_unitario ??
                            Number(item.precio_unitario || 0) / IGV_FACTOR,
                        )}
                      </span>
                    </div>

                    <div>
                      <span className={`pill ${active ? 'ok' : 'inactive'}`}>
                        {active ? 'Activo' : 'Inactivo'}
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
                        aria-label={`Eliminar ${item.nombre}`}
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
              <div>
                Mostrando <strong>{filtered.length}</strong> de <strong>{total}</strong> ítems
              </div>
              <Pagination
                page={page}
                totalPages={totalPages}
                onPageChange={setPage}
                ariaLabel="Paginación de productos"
              />
            </div>
          </>
        )}
      </article>

      <Drawer
        open={!!modal}
        onClose={() => setModal(null)}
        variant="editor"
        eyebrow="Catálogo comercial"
        status={isEditing ? 'Edición' : 'Nuevo ítem'}
        initialFocus="input, select, textarea"
        title={isEditing ? 'Editar producto' : 'Nuevo producto'}
        subtitle={
          isEditing
            ? 'Actualiza precio, unidad y datos comerciales sin salir del catálogo.'
            : 'Registra un producto o servicio para reutilizarlo en cotizaciones y comprobantes.'
        }
        icon={<Package size={22} />}
      >
        {modal && (
          <ProductoForm
            initial={isEditing ? modal.item : EMPTY_FORM}
            onSave={handleSave}
            onCancel={() => setModal(null)}
            saving={saving}
            onGenerateCode={handleGenerateCode}
          />
        )}
      </Drawer>
    </div>
  );
}
