import { useCallback, useEffect, useRef, useState, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  AlertCircle,
  ArrowLeft,
  CalendarClock,
  Eye,
  FileUp,
  Mail,
  Receipt,
  ShieldCheck,
  Trash2,
} from 'lucide-react';
import { clientes as clientesSvc } from '../services/clientes';
import { productos as productosSvc } from '../services/productos';
import { cotizaciones as cotizacionesSvc } from '../services/cotizaciones';
import { tenant as tenantSvc } from '../services/tenant';
import { inventory } from '../services/inventory';
import FiscalDocPreview from '../components/documents/FiscalDocPreview';
import ClientCombobox from '../components/ui/ClientCombobox';
import ProductLineCell from '../components/ui/ProductLineCell';
import { hasCatalogProductOverrides } from '../lib/utils/productCatalogSync';
import { clienteSnapshotFromForm, syncCatalogProductos, upsertCliente, upsertProductos } from '../lib/utils/upsert';
import SectionNavigation from '../components/ui/SectionNavigation';
import Spinner from '../components/ui/Spinner';
import { PageError } from '../components/ui/PageState';
import Modal from '../components/ui/Modal';
import CustomSelect from '../components/ui/CustomSelect';
import DatePicker from '../components/ui/DatePicker';
import { FieldError } from '../components/ui/FieldError';
import { DocumentTypeSwitcher } from '../components/documents/DocumentType';
import ConfirmEmitDialog from '../components/documents/ConfirmEmitDialog';
import { useToast } from '../components/ui/Toast';
import {
  PAYMENT_OPTIONS,
  MEDIO_PAGO_OPTIONS,
  OPERATION_OPTIONS,
  UNIT_OPTIONS,
  inputDateToday,
  addDays,
  paymentDays,
  toApiDate,
  formatCurrency,
  deriveSeries,
  computeLine,
  computeDocumentTotals,
} from '../lib/utils/documents';
import {
  isPositiveDecimal,
  isSameMoney,
  money,
  moneyDifference,
  normalizeQuantity,
  normalizeUnitPrice,
  priceWithIgv,
  priceWithoutIgv,
  sumMoney,
} from '../lib/utils/ublCalculations';
import {
  PRODUCT_INTERNAL_CODE_MAX_LENGTH,
  isValidInternalProductCode,
  isValidSunatUnitCode,
  isValidTaxAffectationCode,
  normalizeInternalProductCode,
} from '../lib/utils/sunatCatalogs';
import { normalizeFiscalClientForm } from '../lib/utils/fiscalClientValidation';
import { useFieldValidation, rules } from '../lib/utils/useFieldValidation';

const EMPTY_ITEM = () => ({
  key: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
  producto_id: '',
  codigo: '',
  descripcion: '',
  unidad_medida: 'NIU',
  cantidad: '1',
  precio_unitario: '',
  tipo_afectacion_igv: '10',
  _isNew: false,
  _catalogSnapshot: null,
  _syncCatalogChanges: false,
});

const RUC_ONLY_DOCUMENT_TYPES = ['6'];
const DNI_ONLY_DOCUMENT_TYPES = ['1'];

function getRequiredClientDocType(tipoComprobante) {
  return tipoComprobante === '03' ? '1' : '6';
}

function createEmptyClient(tipoComprobante) {
  return {
    tipo_documento: getRequiredClientDocType(tipoComprobante),
    numero_documento: '',
    razon_social: '',
    direccion: '',
    email: '',
    telefono: '',
  };
}

function createInitialForm(initialType) {
  const tipo = initialType === '03' ? '03' : '01';
  return {
    tipo_comprobante: tipo,
    modo_emision: 'cpe',
    moneda: 'PEN',
    tipo_operacion: '0101',
    condicion_pago: 'contado',
    medio_pago: 'Efectivo',
    warehouse_id: '',
    fecha_emision: inputDateToday(),
    fecha_vencimiento: '',
    cuotas_pago: [],
    observaciones: '',
    incluye_igv: true,
    enviar_correo: false,
    cliente_id: '',
    cliente: createEmptyClient(tipo),
    items: [EMPTY_ITEM()],
  };
}

function parseInputDate(dateString) {
  if (!dateString) return null;
  const date = new Date(`${dateString}T00:00:00`);
  return Number.isNaN(date.getTime()) ? null : date;
}

function isFutureInputDate(dateString) {
  const date = parseInputDate(dateString);
  if (!date) return false;
  const today = parseInputDate(inputDateToday());
  return today ? date > today : false;
}

function isCreditCondition(value) {
  return Boolean(value && value !== 'contado');
}

function moneyInput(value) {
  return money(value);
}

function createCuotaPago(fechaPago, monto) {
  return {
    key: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    fecha_pago: fechaPago || '',
    monto: moneyInput(monto),
  };
}

function buildDefaultCuotas(fechaEmision, condicionPago, total) {
  const days = paymentDays(condicionPago) || 30;
  const fechaPago = addDays(fechaEmision, days);
  return fechaPago ? [createCuotaPago(fechaPago, total)] : [];
}

function cuotasTotal(cuotas) {
  return sumMoney((cuotas || []).map((cuota) => cuota.monto));
}

function lastCuotaDate(cuotas) {
  return (cuotas || [])
    .map((cuota) => cuota.fecha_pago)
    .filter(Boolean)
    .sort()
    .at(-1) || '';
}

function buildValidationRules(form) {
  return {
    razon_social: rules.required('Nombre / Razón social'),
    numero_documento: (v) => {
      const s = String(v || '').trim();
      if (!s) return 'Número de documento es obligatorio';
      if (form.tipo_comprobante === '01') {
        if (form.cliente.tipo_documento !== '6' || !/^\d{11}$/.test(s)) {
          return 'Factura requiere cliente con RUC (11 dígitos)';
        }
      } else if (form.tipo_comprobante === '03') {
        if (form.cliente.tipo_documento !== '1' || !/^\d{8}$/.test(s)) {
          return 'Boleta requiere cliente con DNI (8 dígitos) en beta';
        }
      }
      return null;
    },
    fecha_emision: (v) => {
      if (!v) return 'Fecha de emision es obligatoria';
      if (!parseInputDate(v)) return 'Fecha de emision no es valida';
      if (isFutureInputDate(v)) return 'La fecha de emision no puede ser futura';
      return null;
    },
    cuotas_pago: () => {
      if (!isCreditCondition(form.condicion_pago)) return null;

      const cuotas = form.cuotas_pago || [];
      if (!cuotas.length) return 'Agrega al menos una cuota para una venta al credito';

      const fechaEmision = parseInputDate(form.fecha_emision);
      for (const [index, cuota] of cuotas.entries()) {
        if (!parseInputDate(cuota.fecha_pago)) {
          return `La cuota ${index + 1} necesita fecha de vencimiento`;
        }
        if (fechaEmision && parseInputDate(cuota.fecha_pago) <= fechaEmision) {
          return `La cuota ${index + 1} debe vencer despues de la fecha de emision`;
        }
        if (!isPositiveDecimal(cuota.monto)) {
          return `La cuota ${index + 1} debe tener monto mayor a cero`;
        }
      }

      const total = computeDocumentTotals(form.items, form.incluye_igv).total;
      const sumaCuotas = cuotasTotal(cuotas);
      if (!isSameMoney(sumaCuotas, total)) {
        return `La suma de cuotas (${formatCurrency(sumaCuotas, form.moneda)}) debe coincidir con el total (${formatCurrency(total, form.moneda)})`;
      }
      return null;
    },
    items: () => {
      const candidateItems = (form.items || []).filter(
        (it) => it.descripcion.trim() && isPositiveDecimal(it.cantidad) && isPositiveDecimal(it.precio_unitario),
      );
      if (candidateItems.length === 0) {
        return 'Agrega al menos una linea con descripcion, cantidad y precio';
      }

      for (const item of candidateItems) {
        if (item.descripcion.trim().length > 500) {
          return 'La descripcion de una linea excede 500 caracteres';
        }
        const normalizedCode = normalizeInternalProductCode(item.codigo);
        if (normalizedCode.length > PRODUCT_INTERNAL_CODE_MAX_LENGTH) {
          return `El codigo SKU no debe exceder ${PRODUCT_INTERNAL_CODE_MAX_LENGTH} caracteres`;
        }
        if (normalizedCode && !isValidInternalProductCode(normalizedCode)) {
          return 'El codigo SKU solo acepta letras, numeros, punto, guion, slash o guion bajo';
        }
        if (!isValidSunatUnitCode(item.unidad_medida)) {
          return 'Selecciona una unidad de medida SUNAT valida';
        }
        if (!isValidTaxAffectationCode(item.tipo_afectacion_igv)) {
          return 'Selecciona una afectacion IGV SUNAT valida';
        }
      }

      return null;
    },
  };
}

function getIdentityLabel(tipoDocumento) {
  if (tipoDocumento === '6') return 'RUC';
  if (tipoDocumento === '1') return 'DNI';
  return 'DOC';
}

function ModeSwitch({ mode, onChange }) {
  return (
    <div className="document-mode-switch" role="group" aria-label="Modo de emisión">
      <button
        type="button"
        aria-pressed={mode === 'cpe'}
        className={`document-mode-button${mode === 'cpe' ? ' is-active' : ''}`}
        onClick={() => onChange('cpe')}
      >
        Emisión estándar
      </button>
      <button
        type="button"
        aria-pressed={mode === 'contingencia'}
        className={`document-mode-button${mode === 'contingencia' ? ' is-active' : ''}`}
        onClick={() => onChange('contingencia')}
      >
        Contingencia
      </button>
    </div>
  );
}

function BuilderSwitch({ label, checked, onChange }) {
  return (
    <button
      type="button"
      className="toggle-chip"
      aria-pressed={checked}
      onClick={() => onChange(!checked)}
    >
      <span className={`switch ${checked ? 'on' : ''}`} />
      <span>{label}</span>
    </button>
  );
}

function PreviewModal({ open, onClose, form, totals, tenantData }) {
  const series = deriveSeries(form.tipo_comprobante, form.modo_emision, tenantData);
  const tipoLabel = form.tipo_comprobante === '01' ? 'FACTURA' : 'BOLETA DE VENTA';
  const tipoDocLabel = getIdentityLabel(form.cliente.tipo_documento);
  const condPagoLabel = PAYMENT_OPTIONS.find((o) => o.value === form.condicion_pago)?.label?.toUpperCase() || 'CONTADO';
  const monedaTexto = form.moneda === 'USD' ? 'DÓLARES' : 'SOLES';

  const fmtDate = (iso) => {
    if (!iso) return '';
    const [y, m, d] = iso.split('-');
    return `${d}/${m}/${y}`;
  };

  const fiscalItems = form.items
    .filter((it) => it.descripcion.trim() && isPositiveDecimal(it.cantidad) && isPositiveDecimal(it.precio_unitario))
    .map((it) => {
      const line = computeLine(it, form.incluye_igv);
      return {
        codigo: it.codigo || '',
        descripcion: it.descripcion,
        unidad: it.unidad_medida || 'NIU',
        cantidad: line.cantidad,
        valorUnitario: line.unitBase,
        precioUnitario: line.unitFinal,
        descuento: 0,
        valorVenta: line.subtotal,
        total: line.total,
      };
    });

  const company = {
    name: tenantData?.business_name || '—',
    ruc: tenantData?.business_ruc || '—',
    address: tenantData?.business_address || '—',
    phone: tenantData?.business_phone || '',
    email: tenantData?.business_email || '',
    logoUrl: tenantData?.logo_filename || '',
  };

  return (
    <Modal open={open} onClose={onClose} title={`Vista previa · ${tipoLabel} ${series}-XXXXXX`} size="xl">
      <div style={{ overflow: 'auto', maxHeight: '75vh' }}>
        <FiscalDocPreview
          accentColor={tenantData?.primary_color || '#004AAD'}
          company={company}
          client={{
            razon_social: form.cliente.razon_social || '—',
            tipo_documento_label: tipoDocLabel,
            numero_documento: form.cliente.numero_documento || '—',
            direccion: form.cliente.direccion || '—',
          }}
          docInfo={{
            tipoLabel,
            serie: series,
            numero: 'XXXXXX',
            fecha_emision: fmtDate(form.fecha_emision),
            fecha_vencimiento: fmtDate(form.fecha_vencimiento),
            moneda_texto: monedaTexto,
            condicion_pago_label: condPagoLabel,
            medio_pago: (form.medio_pago || 'EFECTIVO').toUpperCase(),
            observaciones: form.observaciones || '',
          }}
          items={fiscalItems}
          totals={totals}
          bankAccounts={tenantData?.bank_accounts}
        />
      </div>
    </Modal>
  );
}

function LineRow({
  item,
  index,
  moneda,
  incluyeIgv,
  products,
  isLast,
  animateIn,
  onItemChange,
  onFieldChange,
  onRemove,
  onAddNext,
}) {
  const priceRef = useRef(null);
  const line = computeLine(item, incluyeIgv);
  const sym = moneda === 'USD' ? '$' : 'S/';

  const handlePriceKeyDown = (e) => {
    if (e.key === 'Tab' && !e.shiftKey && isLast) {
      e.preventDefault();
      onAddNext();
    }
  };

  const handleGenerateCode = async () => {
    try {
      const data = await productosSvc.generateCode();
      return data.codigo;
    } catch {
      return '';
    }
  };

  return (
    <div
      className={`line-row line-row--comprobante${animateIn ? ' line-row--entering' : ''}`}
    >
      <div className="product-input line-row-cell line-row-cell--product" data-mobile-label="Producto">
        <ProductLineCell
          value={item}
          onChange={(next) => onItemChange(index, next)}
          products={products}
          incluyeIgv={incluyeIgv}
          sym={sym}
          onGenerateCode={handleGenerateCode}
        />
      </div>

      <div className="line-row-cell line-row-cell--unit" data-mobile-label="Unidad">
        <CustomSelect
          value={item.unidad_medida}
          onChange={(v) => onFieldChange(index, 'unidad_medida', v)}
          options={UNIT_OPTIONS}
          compact
        />
      </div>

      <div className="line-row-cell line-row-cell--qty" data-mobile-label="Cantidad">
        <input
          className="line-edit-input"
          type="text"
          inputMode="decimal"
          value={item.cantidad}
          onChange={(e) => onFieldChange(index, 'cantidad', e.target.value)}
          style={{ MozAppearance: 'textfield', WebkitAppearance: 'none', appearance: 'none' }}
          required
        />
      </div>

      <div className="line-row-cell line-row-cell--price" data-mobile-label="Precio unitario">
        <input
          className="line-edit-input"
          ref={priceRef}
          type="text"
          inputMode="decimal"
          value={item.precio_unitario}
          onChange={(e) => onFieldChange(index, 'precio_unitario', e.target.value)}
          onKeyDown={handlePriceKeyDown}
          placeholder="0.00"
          style={{ MozAppearance: 'textfield', WebkitAppearance: 'none', appearance: 'none' }}
          required
        />
      </div>

      <div className="line-row-cell line-row-cell--total" data-mobile-label="Total">
        <input
          className="line-static-input"
          readOnly
          value={`${sym} ${Number(line.total).toLocaleString('es-PE', { minimumFractionDigits: 2 })}`}
        />
      </div>

      <div className="line-row-cell line-row-cell--actions">
        <button type="button" className="trash-btn" onClick={() => onRemove(index)}>
          <Trash2 size={14} />
        </button>
      </div>
    </div>
  );
}

function ValidationSummary({ errors }) {
  const msgs = Object.values(errors).filter(Boolean);
  if (!msgs.length) return null;

  return (
    <div className="ink-inline-alert ink-inline-alert-danger document-validation-alert">
      <div>
        <p className="document-validation-alert__title">Faltan datos para emitir</p>
        <ul className="document-validation-alert__list">
          {msgs.map((message, index) => (
            <li key={index}>{message}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export default function ComprobanteNuevoPage() {
  const toast = useToast();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const initialType = searchParams.get('tipo') || '01';

  const [form, setForm] = useState(() => createInitialForm(initialType));
  const [clientes, setClientes] = useState([]);
  const [productos, setProductos] = useState([]);
  const [tenantData, setTenantData] = useState(null);
  const [warehouses, setWarehouses] = useState([]);
  const [loadingData, setLoadingData] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [saving, setSaving] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [igvConfirmOpen, setIgvConfirmOpen] = useState(false);
  const [pendingIgv, setPendingIgv] = useState(null);
  const [clienteState, setClienteState] = useState({ isDirty: false, isNew: false });
  const [updateExistingClient, setUpdateExistingClient] = useState(true);
  const [recentItemKey, setRecentItemKey] = useState(null);
  const fileRef = useRef(null);

  const { errors, validate, clearField } = useFieldValidation(buildValidationRules(form));

  useEffect(() => {
    setForm(createInitialForm(initialType));
    setClienteState({ isDirty: false, isNew: false });
    setUpdateExistingClient(true);
    setRecentItemKey(null);
  }, [initialType]);

  useEffect(() => {
    if (!recentItemKey) return undefined;
    const timeoutId = window.setTimeout(() => setRecentItemKey(null), 520);
    return () => window.clearTimeout(timeoutId);
  }, [recentItemKey]);

  const loadBaseData = useCallback(() => {
    setLoadingData(true);
    setLoadError(null);
    Promise.all([clientesSvc.page('?limit=15'), productosSvc.page('?limit=15'), tenantSvc.get(), inventory.warehouses()])
      .then(([c, p, t, w]) => {
        setClientes(Array.isArray(c) ? c : c?.items || []);
        setProductos(Array.isArray(p) ? p : p?.items || []);
        setTenantData(t || null);
        setWarehouses(w || []);
        const preferred = w?.find((warehouse) => warehouse.is_default);
        if (preferred) setForm((current) => ({ ...current, warehouse_id: current.warehouse_id || String(preferred.id) }));
      })
      .catch((err) => {
        setLoadError(err);
        toast(err.message || 'No se pudo cargar el catálogo base del comprobante.', 'error');
      })
      .finally(() => setLoadingData(false));
  }, [toast]);

  useEffect(() => {
    loadBaseData();
  }, [loadBaseData]);

  const seriesPreview = deriveSeries(form.tipo_comprobante, form.modo_emision, tenantData);
  const totals = computeDocumentTotals(form.items, form.incluye_igv);
  const isCreditPayment = isCreditCondition(form.condicion_pago);
  const cuotasMontoTotal = cuotasTotal(form.cuotas_pago);
  const cuotasDiferencia = moneyDifference(totals.total, cuotasMontoTotal);
  const tipoLabel = form.tipo_comprobante === '01' ? 'Factura' : 'Boleta de venta';
  const requiredClientDocType = getRequiredClientDocType(form.tipo_comprobante);
  const allowedClientDocumentTypes = form.tipo_comprobante === '03'
    ? DNI_ONLY_DOCUMENT_TYPES
    : RUC_ONLY_DOCUMENT_TYPES;
  const clientDocRuleCopy = form.tipo_comprobante === '01'
    ? 'Factura: solo cliente con RUC de 11 dígitos.'
    : 'Boleta: solo cliente con DNI de 8 dígitos en esta beta.';
  const emissionValidationValues = {
    razon_social: form.cliente.razon_social,
    numero_documento: form.cliente.numero_documento,
    cliente_tipo_documento: form.cliente.tipo_documento,
    tipo_comprobante: form.tipo_comprobante,
    fecha_emision: form.fecha_emision,
    cuotas_pago: form.cuotas_pago,
    items: form.items,
  };
  const emissionBlockers = Object.entries(buildValidationRules(form))
    .map(([field, rule]) => rule(emissionValidationValues[field], emissionValidationValues))
    .filter(Boolean);
  const canEmit = emissionBlockers.length === 0;

  const setRootField = useCallback((key, value) => {
    if (key === 'cliente_id' || key === 'tipo_comprobante') {
      setUpdateExistingClient(true);
    }
    setForm((current) => {
      if (key === 'condicion_pago') {
        const days = paymentDays(value);
        const total = computeDocumentTotals(current.items, current.incluye_igv).total;
        const fechaVencimiento = days > 0 ? addDays(current.fecha_emision, days) : '';
        return {
          ...current,
          condicion_pago: value,
          fecha_vencimiento: fechaVencimiento,
          cuotas_pago: isCreditCondition(value)
            ? buildDefaultCuotas(current.fecha_emision, value, total)
            : [],
        };
      }

      if (key === 'fecha_emision') {
        const days = paymentDays(current.condicion_pago);
        const fechaVencimiento = days > 0 ? addDays(value, days) : current.fecha_vencimiento;
        const shouldSyncSingleCuota = isCreditCondition(current.condicion_pago)
          && (current.cuotas_pago || []).length <= 1;
        return {
          ...current,
          fecha_emision: value,
          fecha_vencimiento: fechaVencimiento,
          cuotas_pago: shouldSyncSingleCuota
            ? buildDefaultCuotas(
                value,
                current.condicion_pago,
                computeDocumentTotals(current.items, current.incluye_igv).total,
              )
            : current.cuotas_pago,
        };
      }

      if (key === 'fecha_vencimiento') {
        const shouldSyncSingleCuota = isCreditCondition(current.condicion_pago)
          && (current.cuotas_pago || []).length <= 1;
        return {
          ...current,
          fecha_vencimiento: value,
          cuotas_pago: shouldSyncSingleCuota
            ? [createCuotaPago(value, computeDocumentTotals(current.items, current.incluye_igv).total)]
            : current.cuotas_pago,
        };
      }

      if (key === 'tipo_comprobante') {
        const nextClientDocType = getRequiredClientDocType(value);
        const keepClient = current.cliente.tipo_documento === nextClientDocType;
        return {
          ...current,
          tipo_comprobante: value,
          tipo_operacion: '0101',
          cliente_id: keepClient ? current.cliente_id : '',
          cliente: keepClient ? current.cliente : createEmptyClient(value),
        };
      }

      return { ...current, [key]: value };
    });
  }, []);

  const handleClientFormChange = useCallback((formData, { isDirty, isNew }) => {
    setForm((current) => ({ ...current, cliente: { ...current.cliente, ...formData } }));
    setClienteState({ isDirty, isNew });
    clearField('razon_social');
    clearField('numero_documento');
  }, [clearField]);

  const mergeClienteIntoCatalog = useCallback((client) => {
    if (!client?.id) return;
    setClientes((current) => {
      const next = current.filter((item) => String(item.id) !== String(client.id));
      return [client, ...next];
    });
  }, []);

  const setItemField = useCallback((index, key, value) => {
    setForm((current) => ({
      ...current,
      items: current.items.map((item, itemIndex) => (
        itemIndex === index ? { ...item, [key]: value } : item
      )),
    }));
  }, []);

  const handleItemChange = useCallback((index, next) => {
    setForm((current) => ({
      ...current,
      items: current.items.map((item, itemIndex) => (
        itemIndex === index ? { ...item, ...next } : item
      )),
    }));
  }, []);

  const catalogSyncEligibleCount = useMemo(
    () => form.items.filter((item) => hasCatalogProductOverrides(item)).length,
    [form.items],
  );
  const catalogSyncSelectedCount = useMemo(
    () => form.items.filter((item) => hasCatalogProductOverrides(item) && item._syncCatalogChanges).length,
    [form.items],
  );
  const syncCatalogOnSave = catalogSyncEligibleCount > 0 && catalogSyncSelectedCount === catalogSyncEligibleCount;
  const toggleCatalogSyncForEligible = useCallback(() => {
    setForm((current) => {
      const eligible = current.items.filter((item) => hasCatalogProductOverrides(item));
      const nextValue = !(eligible.length > 0 && eligible.every((item) => item._syncCatalogChanges));
      return {
        ...current,
        items: current.items.map((item) => (
          hasCatalogProductOverrides(item)
            ? { ...item, _syncCatalogChanges: nextValue }
            : item
        )),
      };
    });
  }, []);

  const addItem = useCallback(() => {
    const nextItem = EMPTY_ITEM();
    setForm((current) => ({ ...current, items: [...current.items, nextItem] }));
    setRecentItemKey(nextItem.key);
  }, []);

  const removeItem = useCallback((index) => {
    setForm((current) => ({
      ...current,
      items: current.items.length === 1 ? current.items : current.items.filter((_, itemIndex) => itemIndex !== index),
    }));
  }, []);

  const setCuotaField = useCallback((index, key, value) => {
    setForm((current) => {
      const cuotas = (current.cuotas_pago || []).map((cuota, cuotaIndex) => (
        cuotaIndex === index ? { ...cuota, [key]: value } : cuota
      ));
      return {
        ...current,
        cuotas_pago: cuotas,
        fecha_vencimiento: lastCuotaDate(cuotas) || current.fecha_vencimiento,
      };
    });
  }, []);

  const addCuotaPago = useCallback(() => {
    setForm((current) => {
      const total = computeDocumentTotals(current.items, current.incluye_igv).total;
      const sumaActual = cuotasTotal(current.cuotas_pago);
      const diferencia = moneyDifference(total, sumaActual);
      const restante = isPositiveDecimal(diferencia) ? diferencia : '0.00';
      const ultimaFecha = lastCuotaDate(current.cuotas_pago) || current.fecha_emision;
      const fechaPago = addDays(ultimaFecha, 15);
      const cuotas = [
        ...(current.cuotas_pago || []),
        createCuotaPago(fechaPago, restante || total),
      ];
      return {
        ...current,
        cuotas_pago: cuotas,
        fecha_vencimiento: lastCuotaDate(cuotas) || current.fecha_vencimiento,
      };
    });
  }, []);

  const removeCuotaPago = useCallback((index) => {
    setForm((current) => {
      const cuotas = (current.cuotas_pago || []).filter((_, cuotaIndex) => cuotaIndex !== index);
      return {
        ...current,
        cuotas_pago: cuotas,
        fecha_vencimiento: lastCuotaDate(cuotas) || '',
      };
    });
  }, []);

  const resetCuotasToTotal = useCallback(() => {
    setForm((current) => {
      const total = computeDocumentTotals(current.items, current.incluye_igv).total;
      const cuotas = buildDefaultCuotas(current.fecha_emision, current.condicion_pago, total);
      return {
        ...current,
        cuotas_pago: cuotas,
        fecha_vencimiento: lastCuotaDate(cuotas),
      };
    });
  }, []);

  const applyIgvToggle = (newVal) => {
    setForm((current) => ({
      ...current,
      incluye_igv: newVal,
      items: current.items.map((item) => {
        if (!isPositiveDecimal(item.precio_unitario)) return item;
        const nextPrice = newVal
          ? priceWithIgv(item, false)
          : priceWithoutIgv(item, true);
        const shouldRefreshSnapshot = item.producto_id && item._catalogSnapshot && !hasCatalogProductOverrides(item);
        return {
          ...item,
          precio_unitario: nextPrice,
          _catalogSnapshot: shouldRefreshSnapshot
            ? { ...item._catalogSnapshot, precio_unitario: nextPrice }
            : item._catalogSnapshot,
        };
      }),
    }));
  };

  const handleIgvToggle = (newVal) => {
    const hasPrices = form.items.some((item) => isPositiveDecimal(item.precio_unitario));
    if (hasPrices) {
      setPendingIgv(newVal);
      setIgvConfirmOpen(true);
      return;
    }
    applyIgvToggle(newVal);
  };

  const handleImportCsv = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const hasData = form.items.some((item) => item.descripcion.trim());
    if (hasData) {
      const ok = window.confirm(`Vas a reemplazar ${form.items.length} línea(s) con el contenido del CSV. ¿Sí, reemplazar?`);
      if (!ok) {
        event.target.value = '';
        return;
      }
    }

    try {
      const text = await file.text();
      const [headerLine, ...lines] = text.split(/\r?\n/).filter(Boolean);
      const headers = headerLine.split(',').map((value) => value.trim().toLowerCase());
      const imported = lines
        .map((line) => {
          const values = line.split(',');
          const row = Object.fromEntries(headers.map((header, index) => [header, (values[index] || '').trim()]));
          return {
            ...EMPTY_ITEM(),
            codigo: row.codigo || '',
            descripcion: row.descripcion || row.detalle || '',
            unidad_medida: row.unidad_medida || row.unidad || 'NIU',
            cantidad: row.cantidad || '1',
            precio_unitario: row.precio_unitario || row.precio || '',
          };
        })
        .filter((item) => item.descripcion);

      if (!imported.length) {
        toast('El archivo no contiene líneas válidas', 'error');
        return;
      }

      setForm((current) => ({ ...current, items: imported }));
      toast(`Se importaron ${imported.length} líneas desde CSV`);
    } catch {
      toast('No se pudo leer el archivo CSV', 'error');
    } finally {
      event.target.value = '';
    }
  };

  const handleEmitClick = () => {
    const values = {
      razon_social: form.cliente.razon_social,
      numero_documento: form.cliente.numero_documento,
      cliente_tipo_documento: form.cliente.tipo_documento,
      tipo_comprobante: form.tipo_comprobante,
      fecha_emision: form.fecha_emision,
      cuotas_pago: form.cuotas_pago,
      items: form.items,
    };
    const ok = validate(values);
    if (!ok) return;
    setConfirmOpen(true);
  };

  const buildQuotePayload = (clienteId, resolvedItems = null) => {
    const srcItems = resolvedItems || form.items;
    return {
      cliente_id: Number(clienteId),
      warehouse_id: form.warehouse_id ? Number(form.warehouse_id) : null,
      cliente_snapshot: clienteSnapshotFromForm(form.cliente),
      fecha_emision: toApiDate(form.fecha_emision),
      fecha_vencimiento: form.condicion_pago === 'contado'
        ? null
        : toApiDate(lastCuotaDate(form.cuotas_pago) || form.fecha_vencimiento),
      moneda: form.moneda,
      tipo_comprobante: form.tipo_comprobante,
      observaciones: form.observaciones || null,
      condicion_pago: form.condicion_pago,
      cuotas_pago: form.condicion_pago === 'contado'
        ? []
        : (form.cuotas_pago || []).map((cuota) => ({
            fecha_pago: toApiDate(cuota.fecha_pago),
            monto: money(cuota.monto),
          })),
      items: srcItems
        .filter((item) => item.descripcion.trim() && isPositiveDecimal(item.cantidad) && isPositiveDecimal(item.precio_unitario))
        .map((item) => ({
          producto_id: item.producto_id ? Number(item.producto_id) : null,
          codigo_producto: normalizeInternalProductCode(item.codigo) || null,
          descripcion: item.descripcion.trim(),
          cantidad: normalizeQuantity(item.cantidad),
          precio_unitario: priceWithIgv(item, form.incluye_igv),
          unidad_medida: item.unidad_medida || 'NIU',
          tipo_afectacion_igv: item.tipo_afectacion_igv || '10',
        })),
    };
  };

  const handleEmitConfirmed = async () => {
    setSaving(true);
    try {

      const {
        id: clienteId,
        client: persistedClient,
      } = await upsertCliente({
        id: form.cliente_id,
        isNew: clienteState.isNew,
        isDirty: clienteState.isDirty,
        form: form.cliente,
        updateExisting: updateExistingClient,
      });

      if (persistedClient) {
        const normalizedClient = normalizeFiscalClientForm(persistedClient);
        mergeClienteIntoCatalog({ ...persistedClient, ...normalizedClient, id: persistedClient.id });
        setClienteState({ isDirty: false, isNew: false });
        setForm((current) => ({
          ...current,
          cliente_id: String(persistedClient.id),
          cliente: normalizedClient,
        }));
      }

      const createdItems = await upsertProductos(form.items, { priceIncludesIgv: form.incluye_igv });
      const resolvedItems = await syncCatalogProductos(createdItems, { priceIncludesIgv: form.incluye_igv });
      setForm((current) => ({
        ...current,
        cliente_id: String(clienteId),
        items: resolvedItems,
      }));

      const quote = await cotizacionesSvc.create(buildQuotePayload(clienteId, resolvedItems));
      const availability = await inventory.documentAvailability(quote.id);
      if (availability?.inventory_enabled && !availability.sufficient) {
        const missing = availability.items
          .filter((item) => !item.sufficient)
          .map((item) => `${item.product_name}: ${item.available} de ${item.requested} ${item.unit}`)
          .join('; ');
        throw new Error(`Stock insuficiente en ${availability.warehouse_name}. ${missing}`);
      }
      await cotizacionesSvc.facturar(quote.id, {
        tipo_comprobante: form.tipo_comprobante,
        tipo_operacion: form.tipo_operacion,
      });

      if (form.enviar_correo) {
        const share = await cotizacionesSvc.share(quote.id);
        if (share.mailto_link) {
          window.open(share.mailto_link, '_blank', 'noopener,noreferrer');
        }
      }

      toast(`${tipoLabel} emitida correctamente`);
      navigate(`/cotizaciones/${quote.id}`);
    } catch (err) {
      toast(err.message || 'No se pudo emitir el comprobante', 'error');
    } finally {
      setSaving(false);
      setConfirmOpen(false);
    }
  };

  const hasValidationErrors = Object.keys(errors).length > 0;
  const paymentLabel = PAYMENT_OPTIONS.find((option) => option.value === form.condicion_pago)?.label || 'Contado';
  const modeLabel = form.modo_emision === 'contingencia' ? 'Contingencia activada' : 'Emisión estándar';
  const readyLines = form.items.filter(
    (item) => item.descripcion.trim() && isPositiveDecimal(item.cantidad) && isPositiveDecimal(item.precio_unitario),
  ).length;
  const clientName = form.cliente.razon_social?.trim() || 'Sin cliente seleccionado';
  const clientDoc = form.cliente.numero_documento?.trim()
    ? `${getIdentityLabel(form.cliente.tipo_documento)} ${form.cliente.numero_documento.trim()}`
    : 'Documento pendiente';
  const clientInitials = clientName === 'Sin cliente seleccionado'
    ? 'SN'
    : clientName
        .split(/\s+/)
        .filter(Boolean)
        .map((part) => part[0])
        .join('')
        .slice(0, 2)
        .toUpperCase();
  const issueDateLabel = form.fecha_emision
    ? new Date(`${form.fecha_emision}T00:00:00`).toLocaleDateString('es-PE')
    : 'Hoy';
  const finalDueDate = lastCuotaDate(form.cuotas_pago) || form.fecha_vencimiento;
  const dueDateLabel = form.condicion_pago === 'contado'
    ? 'Pago al emitir'
    : finalDueDate
      ? new Date(`${finalDueDate}T00:00:00`).toLocaleDateString('es-PE')
      : 'Definir vencimiento';
  const readinessLabel = hasValidationErrors
    ? 'Revisar datos antes de emitir'
    : canEmit
      ? 'Listo para revisión fiscal'
      : 'Completa cliente y líneas';
  const documentSections = [
    { id: 'document-emission', label: 'Documento', status: 'Configurado' },
    { id: 'document-client', label: 'Cliente', status: form.cliente.razon_social ? 'Listo' : 'Pendiente' },
    { id: 'document-lines', label: 'Líneas', status: readyLines ? `${readyLines} lista${readyLines !== 1 ? 's' : ''}` : 'Pendiente' },
    { id: 'document-review', label: 'Revisión', status: canEmit ? 'Listo' : 'Revisar' },
  ];

  if (loadingData) {
    return <div className="flex h-64 items-center justify-center"><Spinner size="lg" /></div>;
  }

  if (loadError) {
    return (
      <div className="comprobante-nuevo-page">
        <PageError
          error={loadError}
          title="No se pudo preparar el comprobante"
          onRetry={loadBaseData}
        />
      </div>
    );
  }

  return (
    <>
      <div className="comprobante-nuevo-page">
        <section className="attention document-hero ink-enter-1">
          <div className="attention-title document-hero-title">
            <span className="attention-title-badge">
              <ArrowLeft size={16} />
            </span>
            <p className="eyebrow document-hero-eyebrow">Emisión fiscal segura · {seriesPreview}-XXXXXX</p>
            <h2>Nueva {tipoLabel}</h2>
            <p>Usa la misma estructura clara de cotizaciones, pero con validación fiscal antes de emitir a SUNAT.</p>
            <div className="document-hero-actions">
              <span className="document-hero-status">{modeLabel}</span>
              <span className="document-hero-status">{paymentLabel}</span>
            </div>
          </div>

          <div className="attention-card document-hero-card">
            <strong>{tipoLabel}</strong>
            <span>{seriesPreview} · {modeLabel}</span>
            <div className="attention-card-link">Documento listo</div>
          </div>

          <div className="attention-card document-hero-card">
            <strong>{paymentLabel}</strong>
            <span>Vence: {dueDateLabel}</span>
            <div className="attention-card-link">Cobranza ordenada</div>
          </div>

          <div className="attention-card document-hero-card">
            <strong>{readyLines}</strong>
            <span>Línea{readyLines !== 1 ? 's' : ''} válida{readyLines !== 1 ? 's' : ''} para emitir</span>
            <div className="attention-card-link">{readinessLabel}</div>
          </div>

          <div className="attention-card document-hero-card document-hero-card--action">
            <button
              className="document-hero-preview-btn"
              type="button"
              onClick={() => setPreviewOpen(true)}
            >
              <Eye size={14} /> Vista previa
            </button>
            <span>{form.enviar_correo ? 'Correo habilitado' : clientDoc}</span>
            <strong>{clientName}</strong>
          </div>
        </section>

        <SectionNavigation label="Progreso de emisión" items={documentSections} />

        <section className="builder ink-enter-2">
          <div>
            <article id="document-emission" tabIndex={-1} className="panel form-section-anchor">
              <div className="panel-header">
                <div>
                  <h3>Documento y emisión</h3>
                  <p>Define el comprobante, la condición comercial y lo que debe quedar fijo antes del envío fiscal.</p>
                </div>
              </div>
              <div className="panel-body">
                <div className="document-toolbar">
                  <DocumentTypeSwitcher
                    value={form.tipo_comprobante}
                    onChange={(v) => setRootField('tipo_comprobante', v)}
                    options={['01', '03']}
                  />
                  <ModeSwitch mode={form.modo_emision} onChange={(v) => setRootField('modo_emision', v)} />
                </div>

                <div className="ink-inline-alert ink-inline-alert-warning document-builder-alert">
                  <AlertCircle size={16} className="flex-shrink-0" />
                  <span>Antes de emitir, revisa cliente, montos y condición de pago. Después de enviarlo a SUNAT, el comprobante no podrá editarse directamente.</span>
                </div>

                <div className="form-grid">
                  <div className="field span-4">
                    <label>Moneda</label>
                    <CustomSelect
                      value={form.moneda}
                      onChange={(v) => setRootField('moneda', v)}
                      options={[
                        { value: 'PEN', label: 'S/ Soles' },
                        { value: 'USD', label: '$ Dólares' },
                      ]}
                    />
                  </div>

                  {form.tipo_comprobante === '01' && (
                    <div className="field span-4">
                      <label>Tipo de operación</label>
                      <CustomSelect
                        value={form.tipo_operacion}
                        onChange={(v) => setRootField('tipo_operacion', v)}
                        options={OPERATION_OPTIONS}
                      />
                    </div>
                  )}

                  <div className="field span-4">
                    <label>Forma de pago</label>
                    <CustomSelect
                      value={form.condicion_pago}
                      onChange={(v) => setRootField('condicion_pago', v)}
                      options={PAYMENT_OPTIONS}
                    />
                  </div>

                  <div className="field span-4">
                    <label>Medio de pago</label>
                    <CustomSelect
                      value={form.medio_pago}
                      onChange={(v) => setRootField('medio_pago', v)}
                      options={MEDIO_PAGO_OPTIONS}
                    />
                  </div>

                  {warehouses.length > 0 && <div className="field span-4"><label>Almacén de salida</label><CustomSelect value={form.warehouse_id} onChange={(value) => setRootField('warehouse_id', String(value || ''))} options={warehouses.map((warehouse) => ({ value: String(warehouse.id), label: `${warehouse.name}${warehouse.is_default ? ' · Principal' : ''}` }))} /></div>}

                  <div className="field span-4">
                    <label>Fecha de emisión</label>
                    <DatePicker value={form.fecha_emision} onChange={(v) => setRootField('fecha_emision', v)} />
                  </div>

                  <div className="field span-4">
                    <label>{isCreditPayment ? 'Vencimiento final' : 'Fecha de vencimiento'}</label>
                    <DatePicker
                      value={form.fecha_vencimiento}
                      disabled={form.condicion_pago === 'contado'}
                      onChange={(v) => setRootField('fecha_vencimiento', v)}
                    />
                  </div>

                  {isCreditPayment && (
                    <div className="field span-12">
                      <div className="rounded-[24px] border border-[var(--border-subtle)] bg-[var(--bg-surface-2)] p-4">
                        <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                          <div>
                            <label className="mb-1 block">Cronograma de cuotas SUNAT</label>
                            <p className="tx-meta">
                              SUNAT exige monto pendiente, fecha de vencimiento y monto por cada cuota.
                            </p>
                          </div>
                          <div className="flex flex-wrap gap-2">
                            <button type="button" className="mini-action" onClick={resetCuotasToTotal}>
                              Ajustar al total
                            </button>
                            <button type="button" className="mini-action" onClick={addCuotaPago}>
                              + Agregar cuota
                            </button>
                          </div>
                        </div>

                        <div className="mt-4 space-y-3">
                          {(form.cuotas_pago || []).map((cuota, index) => (
                            <div
                              key={cuota.key || `${cuota.fecha_pago}-${index}`}
                              className="grid gap-3 rounded-[18px] bg-white p-3 md:grid-cols-[120px_minmax(180px,1fr)_160px_40px]"
                            >
                              <div className="flex items-center font-mono text-sm font-black text-[var(--text-secondary)]">
                                Cuota {String(index + 1).padStart(3, '0')}
                              </div>
                              <DatePicker
                                value={cuota.fecha_pago}
                                onChange={(value) => setCuotaField(index, 'fecha_pago', value)}
                                compact
                              />
                              <input
                                className="input font-mono"
                                type="number"
                                min="0"
                                step="0.01"
                                value={cuota.monto}
                                onChange={(event) => setCuotaField(index, 'monto', event.target.value)}
                                onBlur={(event) => setCuotaField(index, 'monto', moneyInput(event.target.value))}
                                placeholder="0.00"
                              />
                              <button
                                type="button"
                                className="mini-action justify-center"
                                onClick={() => removeCuotaPago(index)}
                                disabled={(form.cuotas_pago || []).length === 1}
                                aria-label={`Eliminar cuota ${index + 1}`}
                              >
                                <Trash2 size={14} />
                              </button>
                            </div>
                          ))}
                        </div>

                        <div className="mt-4 flex flex-wrap items-center justify-between gap-2 text-sm">
                          <span className="tx-meta">
                            Suma de cuotas: <strong>{formatCurrency(cuotasMontoTotal, form.moneda)}</strong>
                          </span>
                          <span className={cuotasDiferencia === '0.00' ? 'text-[var(--color-success)]' : 'text-[var(--color-error)]'}>
                            Diferencia: {formatCurrency(cuotasDiferencia, form.moneda)}
                          </span>
                        </div>
                        <FieldError message={errors.cuotas_pago} />
                      </div>
                    </div>
                  )}

                  <div className="field span-6">
                    <label>Modo de precios</label>
                    <BuilderSwitch
                      label={form.incluye_igv ? 'Los precios ya incluyen IGV' : 'Los precios se ingresan sin IGV'}
                      checked={form.incluye_igv}
                      onChange={handleIgvToggle}
                    />
                    <span className="tx-meta">
                      {form.incluye_igv
                        ? 'El IGV se desglosa desde el precio digitado.'
                        : 'El IGV se agregará sobre el precio digitado.'}
                    </span>
                  </div>

                  <div className="field span-12">
                    <label>Observaciones para el comprobante</label>
                    <textarea
                      className="input min-h-[92px] resize-none"
                      rows={3}
                      value={form.observaciones}
                      onChange={(e) => setRootField('observaciones', e.target.value)}
                      placeholder="Condiciones especiales, instrucciones de entrega o notas visibles para el cliente."
                    />
                  </div>
                </div>
              </div>
            </article>

            <article id="document-client" tabIndex={-1} className="panel form-section-anchor">
              <div className="panel-header">
                <div>
                  <h3>Cliente y entrega</h3>
                  <p>Selecciona o crea el cliente primero para emitir sin doble digitación y con datos completos.</p>
                </div>
              </div>
              <div className="panel-body">
                <div className="field full">
                  <label>Cliente</label>
                  <ClientCombobox
                    key={form.tipo_comprobante}
                    clients={clientes}
                    value={form.cliente_id}
                    onChange={(id) => setRootField('cliente_id', id)}
                    onFormChange={handleClientFormChange}
                    defaultDocumentType={requiredClientDocType}
                    allowedDocumentTypes={allowedClientDocumentTypes}
                  />
                  <p className="tx-meta mt-2">{clientDocRuleCopy}</p>
                  <FieldError message={errors.numero_documento} />
                  <FieldError message={errors.razon_social} />
                </div>

                {form.cliente.razon_social && (
                  <div className="client-result">
                    <div className="avatar">{clientInitials}</div>
                    <div>
                      <strong>{form.cliente.razon_social}</strong>
                      <span>
                        {clientDoc}
                        {form.cliente.telefono ? ` · ${form.cliente.telefono}` : ''}
                      </span>
                    </div>
                    <span className={`status-pill ${form.enviar_correo ? 'ok' : 'warn'}`}>
                      {form.enviar_correo ? 'Correo listo' : 'Revisar entrega'}
                    </span>
                  </div>
                )}
                {form.cliente_id && clienteState.isDirty && !clienteState.isNew && (
                  <button
                    type="button"
                    className="toggle-chip"
                    aria-pressed={updateExistingClient}
                    onClick={() => setUpdateExistingClient((current) => !current)}
                    style={{ marginTop: '12px' }}
                  >
                    <span className={`switch ${updateExistingClient ? 'on' : ''}`} />
                    Actualizar ficha del cliente
                  </button>
                )}

                <div className="document-client-status-grid">
                  <div className="status-tile">
                    <span className="tile-label">Documento</span>
                    <span className="tile-value">{clientDoc}</span>
                  </div>
                  <div className="status-tile">
                    <span className="tile-label">Contacto</span>
                    <span className="tile-value">{form.cliente.email || 'Sin correo de facturación'}</span>
                  </div>
                  <div className="status-tile">
                    <span className="tile-label">Despacho</span>
                    <span className="tile-value">{form.enviar_correo ? 'Enviar al emitir' : 'Entrega manual'}</span>
                  </div>
                </div>

                <div className="document-client-actions">
                  <BuilderSwitch
                    label={form.enviar_correo ? 'Correo habilitado al emitir' : 'Enviar correo al emitir'}
                    checked={form.enviar_correo}
                    onChange={(v) => setRootField('enviar_correo', v)}
                  />
                </div>
              </div>
            </article>

            <article id="document-lines" tabIndex={-1} className="panel form-section-anchor">
              <div className="panel-header document-lines-header">
                <div>
                  <h3>Líneas del comprobante</h3>
                  <p>Agrega productos o servicios reutilizando el mismo lenguaje visual de cotizaciones para evitar errores de carga.</p>
                </div>
                <div className="document-lines-actions">
                  <input ref={fileRef} type="file" accept=".csv" className="hidden" onChange={handleImportCsv} />
                  {catalogSyncEligibleCount > 0 && (
                    <button
                      type="button"
                      className={`toggle-chip line-sync-chip${syncCatalogOnSave ? ' is-active' : ''}`}
                      aria-pressed={syncCatalogOnSave}
                      onClick={toggleCatalogSyncForEligible}
                    >
                      <span className={`switch ${syncCatalogOnSave ? 'on' : ''}`} />
                      {syncCatalogOnSave ? 'Actualizar catalogo al guardar' : 'Aplicar cambios al catalogo'}
                    </button>
                  )}
                  <button type="button" className="mini-action document-lines-upload" onClick={() => fileRef.current?.click()}>
                    <FileUp size={14} /> Subir CSV
                  </button>
                </div>
              </div>
              <div className="panel-body">
                {catalogSyncEligibleCount > 0 && (
                  <div className={`line-sync-banner${syncCatalogOnSave ? ' is-active' : ''}`}>
                    <strong>
                      {catalogSyncEligibleCount} producto{catalogSyncEligibleCount !== 1 ? 's' : ''} con cambios de catalogo
                    </strong>
                    <span>
                      {syncCatalogOnSave
                        ? 'Se actualizaran en la base al guardar este comprobante.'
                        : 'Los cambios quedaran solo en este comprobante hasta que actives el guardado global.'}
                    </span>
                  </div>
                )}
                <div className="line-table line-table--comprobante">
                  <div className="line-head">
                    <div>Código / Producto</div>
                    <div>Unidad</div>
                    <div>Cant.</div>
                    <div>P. unit.</div>
                    <div>Total</div>
                    <div />
                  </div>

                  {form.items.map((item, index) => (
                    <LineRow
                      key={item.key}
                      item={item}
                      index={index}
                    moneda={form.moneda}
                    incluyeIgv={form.incluye_igv}
                    products={productos}
                    isLast={index === form.items.length - 1}
                    animateIn={recentItemKey === item.key}
                    onItemChange={handleItemChange}
                    onFieldChange={setItemField}
                    onRemove={removeItem}
                    onAddNext={addItem}
                    />
                  ))}
                </div>

                {errors.items && (
                  <div style={{ marginTop: '10px' }}>
                    <FieldError message={errors.items} />
                  </div>
                )}

                <div className="line-footer">
                  <button type="button" className="link-btn" onClick={addItem}>⊕ Agregar otra línea</button>
                  <span className="tx-meta">
                    {readyLines} línea{readyLines !== 1 ? 's' : ''} lista{readyLines !== 1 ? 's' : ''} · {form.items.length} total
                  </span>
                </div>
              </div>
            </article>
          </div>

          <aside>
            <article id="document-review" tabIndex={-1} className="summary-card form-section-anchor">
              <div className="summary-header">
                <h3>Resumen del comprobante</h3>
                <p>Cálculo siempre visible para no emitir sin revisar cliente, fechas y monto final.</p>
              </div>
              <div className="summary-body">
                <div className="total-line"><span>Documento</span><strong>{tipoLabel}</strong></div>
                <div className="total-line"><span>Cliente</span><strong>{clientName}</strong></div>
                <div className="total-line"><span>Fecha de emisión</span><strong>{issueDateLabel}</strong></div>
                <div className="total-line"><span>Subtotal</span><strong>{formatCurrency(totals.subtotal, form.moneda)}</strong></div>
                <div className="total-line"><span>IGV (18%)</span><strong>{formatCurrency(totals.igv, form.moneda)}</strong></div>
                <div className="total-line"><span>Líneas válidas</span><strong>{readyLines}</strong></div>
                <div className="grand-total"><span>Total</span><strong>{formatCurrency(totals.total, form.moneda)}</strong></div>

                <ValidationSummary errors={errors} />

                {form.enviar_correo && (
                  <div className="document-summary-note">
                    <Mail size={13} />
                    <span>El cliente recibirá el comprobante por correo después de emitirse.</span>
                  </div>
                )}
                {!canEmit && (
                  <p id="emission-blocker" className="mt-3 text-center text-xs font-semibold text-[var(--color-text-muted)]" aria-live="polite">
                    Para habilitar la emisión: {emissionBlockers[0]}
                  </p>
                )}
              </div>
              <div className="summary-actions">
                <button type="button" className="side-btn" onClick={() => setPreviewOpen(true)}>
                  <Eye size={16} /> Vista previa
                </button>
                <button
                  type="button"
                  className="side-btn primary disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0"
                  onClick={handleEmitClick}
                  disabled={saving || !canEmit}
                  aria-describedby={!canEmit ? 'emission-blocker' : undefined}
                >
                  {saving ? <Spinner size="sm" /> : <Receipt size={16} />}
                  Emitir {form.tipo_comprobante === '01' ? 'factura' : 'boleta'}
                </button>
              </div>
            </article>

            <article className="hint-card">
              <h3>Checklist antes de enviar</h3>
              <p>Confirma que el documento del cliente, la forma de pago y el total coincidan con la operación real.</p>
              <ul className="document-hint-list">
                <li><ShieldCheck size={14} /> {clientDoc}</li>
                <li><CalendarClock size={14} /> Emisión {issueDateLabel} · vencimiento {dueDateLabel}</li>
                <li><Mail size={14} /> {form.enviar_correo ? 'Se enviará por correo al cliente' : 'Entrega manual posterior'}</li>
              </ul>
            </article>
          </aside>
        </section>
        <div className="mobile-summary-bar" aria-live="polite">
          <div>
            <span>Total del comprobante</span>
            <strong>{formatCurrency(totals.total, form.moneda)}</strong>
          </div>
          <button type="button" className="btn-primary" onClick={handleEmitClick} disabled={saving || !canEmit}>
            {saving ? 'Emitiendo…' : 'Emitir'}
          </button>
        </div>
      </div>

      <PreviewModal
        open={previewOpen}
        onClose={() => setPreviewOpen(false)}
        form={form}
        totals={totals}
        tenantData={tenantData}
      />

      <ConfirmEmitDialog
        open={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        onConfirm={handleEmitConfirmed}
        loading={saving}
        mode="emit"
        tipo={form.tipo_comprobante}
        serie={`${seriesPreview}-XXXXXX`}
        cliente={form.cliente.razon_social}
        total={totals.total}
        moneda={form.moneda}
        extraLines={[
          `${getIdentityLabel(form.cliente.tipo_documento)} ${form.cliente.numero_documento}`,
          `${form.items.length} línea${form.items.length !== 1 ? 's' : ''} · ${paymentLabel}`,
        ]}
      />

      <Modal open={igvConfirmOpen} onClose={() => setIgvConfirmOpen(false)} title="Cambiar modo de precios" size="sm">
        <div className="space-y-4">
          <p style={{ fontSize: '13px', color: 'var(--color-text-muted)', lineHeight: 1.6 }}>
            Cambiar el modo de IGV va a <strong>recalcular los precios</strong> de todas las líneas ya ingresadas (
            {form.items.filter((item) => isPositiveDecimal(item.precio_unitario)).length} línea
            {form.items.filter((item) => isPositiveDecimal(item.precio_unitario)).length !== 1 ? 's' : ''}). ¿Sí, cambiar?
          </p>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
            <button className="btn-secondary" onClick={() => setIgvConfirmOpen(false)}>Cancelar</button>
            <button
              className="btn-primary"
              onClick={() => {
                applyIgvToggle(pendingIgv);
                setIgvConfirmOpen(false);
              }}
            >
              Sí, recalcular precios
            </button>
          </div>
        </div>
      </Modal>
    </>
  );
}

