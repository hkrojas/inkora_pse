import { useEffect, useRef, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  Eye, Plus, Search, Trash2, PlusCircle, Send, FileText,
  Download, CheckCircle2, Clock, AlertCircle, XCircle,
  ChevronDown, ChevronUp, Receipt, SlidersHorizontal,
  History, Copy, Share2, MessageCircle, Mail, MoreHorizontal,
} from 'lucide-react';
import { cotizaciones as svc } from '../services/cotizaciones';
import { clientes as cliSvc } from '../services/clientes';
import { productos as prodSvc } from '../services/productos';
import { tenant as tenantSvc } from '../services/tenant';
import Spinner from '../components/ui/Spinner';
import ColorPickerField from '../components/ui/ColorPickerField';
import EmptyState from '../components/ui/EmptyState';
import Badge, { statusBadge } from '../components/ui/Badge';
import Modal from '../components/ui/Modal';
import CustomSelect from '../components/ui/CustomSelect';
import DatePicker from '../components/ui/DatePicker';
import ClientCombobox from '../components/ui/ClientCombobox';
import ProductLineCell from '../components/ui/ProductLineCell';
import { FieldError } from '../components/ui/FieldError';
import { useToast } from '../components/ui/Toast';
import { getPaymentMethodPreview, normalizePaymentMethods } from '../lib/utils/paymentMethods';
import { normalizePeruMobileInput, validatePeruMobilePhone } from '../lib/utils/peruPhoneValidation';
import {
  DEFAULT_NOTE_1_COLOR,
  DEFAULT_NOTE_1_TEXT,
  DEFAULT_NOTE_2_COLOR,
  DEFAULT_NOTE_2_TEXT,
  parseTenantObservationDefaults,
} from '../lib/utils/pdfObservationDefaults';
import { upsertCliente, upsertProductos } from '../lib/utils/upsert';
import { useAuth } from '../context/AuthContext';

// ─── Constantes de dominio ────────────────────────────────────────────────────

const UNIDADES_MEDIDA = [
  { value: 'NIU', label: 'NIU – Unidad' },
  { value: 'ZZ',  label: 'ZZ – Servicio' },
  { value: 'KGM', label: 'KGM – Kilogramo' },
  { value: 'H87', label: 'H87 – Pieza' },
  { value: 'BG',  label: 'BG – Bolsa' },
  { value: 'BX',  label: 'BX – Caja' },
  { value: 'RM',  label: 'RM – Resma' },
];

const AFECTACION_IGV = [
  { value: '10', label: '10 – Gravado' },
  { value: '20', label: '20 – Exonerado' },
  { value: '30', label: '30 – Inafecto' },
  { value: '40', label: '40 – Exportación' },
];

const CONDICIONES_PAGO = [
  { value: 'contado',    label: 'Contado' },
  { value: 'credito_7',  label: 'Crédito 7 días' },
  { value: 'credito_15', label: 'Crédito 15 días' },
  { value: 'credito_30', label: 'Crédito 30 días' },
  { value: 'credito_60', label: 'Crédito 60 días' },
];

const MOTIVOS_NC = [
  { value: '01', label: '01 – Anulación de la operación' },
  { value: '02', label: '02 – Anulación por error en el RUC' },
  { value: '03', label: '03 – Corrección en la descripción' },
  { value: '04', label: '04 – Descuento global' },
  { value: '05', label: '05 – Descuento por ítem' },
  { value: '06', label: '06 – Devolución total' },
  { value: '07', label: '07 – Devolución por ítem' },
  { value: '08', label: '08 – Bonificación' },
  { value: '09', label: '09 – Disminución en el valor' },
  { value: '10', label: '10 – Otros conceptos' },
];

const MOTIVOS_ND = [
  { value: '01', label: '01 – Intereses por mora' },
  { value: '02', label: '02 – Aumento en el valor' },
  { value: '03', label: '03 – Penalidades / otros conceptos' },
];

// ─── Helpers ──────────────────────────────────────────────────────────────────

const ADVANCED_PREF_KEY = 'cotizaciones.avanzado';

function getSunatStatus(item) {
  if (item.estado === 'anulada')    return { label: 'ANULADO',  variant: 'danger',  icon: XCircle };
  if (item.sunat_error)            return { label: 'RECHAZADO', variant: 'danger',  icon: AlertCircle, tooltip: item.sunat_error };
  if (item.sunat_xml_url)          return { label: 'ACEPTADO',  variant: 'success', icon: CheckCircle2 };
  if (item.document_kind !== 'quotation') return { label: 'PENDIENTE', variant: 'warning', icon: Clock };
  return null;
}

function calcFechaVencimiento(condicion) {
  if (!condicion || condicion === 'contado') return '';
  const days = { credito_7: 7, credito_15: 15, credito_30: 30, credito_60: 60 }[condicion];
  if (!days) return '';
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

function getWhatsAppLink(cliente, doc) {
  const phone = cliente?.whatsapp || cliente?.telefono;
  if (!phone) return null;
  const normalizedPhone = normalizePeruMobileInput(phone);
  if (validatePeruMobilePhone(normalizedPhone, 'WhatsApp')) return null;
  const number = `51${normalizedPhone}`;
  const docNum = doc.serie
    ? `${doc.serie}-${String(doc.correlativo || 0).padStart(6, '0')}`
    : `#${doc.id}`;
  const sym = doc.moneda === 'USD' ? '$' : 'S/';
  const msg = `Hola, le compartimos el comprobante ${docNum} por ${sym} ${Number(doc.total_venta || 0).toFixed(2)}.`;
  return `https://wa.me/${number}?text=${encodeURIComponent(msg)}`;
}

function getPublicShareUrl(doc) {
  if (!doc?.uuid_publico) return null;
  const baseUrl = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');
  return `${baseUrl}/public/cotizaciones/${doc.uuid_publico}/pdf`;
}

function getEmailLink(cliente, doc) {
  if (!cliente?.email) return null;
  const docNum = doc.serie
    ? `${doc.serie}-${String(doc.correlativo || 0).padStart(6, '0')}`
    : `#${doc.id}`;
  const shareUrl = getPublicShareUrl(doc);
  const subject = encodeURIComponent(`Cotización ${docNum}`);
  const body = encodeURIComponent(
    [
      'Hola,',
      '',
      `Le compartimos la cotización ${docNum}.`,
      shareUrl ? `Descargar documento: ${shareUrl}` : '',
      '',
      'Quedamos atentos.',
    ].filter(Boolean).join('\n'),
  );
  return `mailto:${cliente.email}?subject=${subject}&body=${body}`;
}

function getLinkedSunatStatus(item) {
  if (!item?.linked_fiscal_document_number) return null;
  if (item.linked_fiscal_document_status === 'anulada') {
    return { label: 'ANULADO', variant: 'danger', icon: XCircle };
  }
  if (item.linked_fiscal_document_status === 'facturada') {
    return { label: 'ACEPTADO', variant: 'success', icon: CheckCircle2 };
  }
  return { label: 'PENDIENTE', variant: 'warning', icon: Clock };
}

function docLabel(tipo) {
  const m = { '01': 'FACTURA', '03': 'BOLETA', '07': 'NC', '08': 'ND', '00': 'COT.' };
  return m[tipo] || tipo;
}

function docVariant(tipo) {
  const m = { '01': 'brand', '03': 'info', '07': 'warning', '08': 'warning', '00': 'default' };
  return m[tipo] || 'default';
}

const fmt = (v) => Number(v || 0).toLocaleString('es-PE', { minimumFractionDigits: 2 });

function normalizeObservationLine(line, fallback = {}) {
  const text = String(line?.text || '').trim();
  return {
    text,
    color: line?.color || fallback.color || '#111111',
    bold: typeof line?.bold === 'boolean' ? line.bold : Boolean(fallback.bold),
  };
}

function buildDefaultObservationLines(tenantData = null) {
  const defaults = parseTenantObservationDefaults(tenantData);
  return [
    normalizeObservationLine(
      {
        text: defaults.line1.text || DEFAULT_NOTE_1_TEXT,
        color: defaults.line1.color || DEFAULT_NOTE_1_COLOR,
        bold: defaults.line1.bold,
      },
      { color: DEFAULT_NOTE_1_COLOR, bold: true },
    ),
    normalizeObservationLine(
      {
        text: defaults.line2.text || DEFAULT_NOTE_2_TEXT,
        color: defaults.line2.color || DEFAULT_NOTE_2_COLOR,
        bold: defaults.line2.bold,
      },
      { color: DEFAULT_NOTE_2_COLOR, bold: false },
    ),
  ];
}

function parseObservationValue(value, tenantData = null) {
  if (!value) return buildDefaultObservationLines(tenantData);

  if (Array.isArray(value)) {
    return value.map((line, index) => normalizeObservationLine(line, buildDefaultObservationLines(tenantData)[index] || {}));
  }

  if (typeof value === 'string') {
    const raw = value.trim();
    if (!raw) return buildDefaultObservationLines(tenantData);

    if (raw.startsWith('{') || raw.startsWith('[')) {
      try {
        const parsed = JSON.parse(raw);
        const lines = Array.isArray(parsed) ? parsed : parsed?.lines;
        if (Array.isArray(lines)) return parseObservationValue(lines, tenantData);
      } catch {
        return raw.split('\n').map((line, index) => normalizeObservationLine(
          { text: line },
          buildDefaultObservationLines(tenantData)[index] || { color: '#111111', bold: false },
        ));
      }
    }

    return raw.split('\n').map((line, index) => normalizeObservationLine(
      { text: line },
      buildDefaultObservationLines(tenantData)[index] || { color: '#111111', bold: false },
    ));
  }

  return buildDefaultObservationLines(tenantData);
}

function serializeObservationLines(lines) {
  return JSON.stringify({
    version: 1,
    lines: lines
      .map((line, index) => normalizeObservationLine(line, buildDefaultObservationLines()[index] || {}))
      .filter((line) => line.text),
  });
}

function formatPreviewDate(value, fallback = '') {
  if (!value) return fallback;

  if (value instanceof Date && !Number.isNaN(value.getTime())) {
    const day = String(value.getDate()).padStart(2, '0');
    const month = String(value.getMonth() + 1).padStart(2, '0');
    return `${day}/${month}/${value.getFullYear()}`;
  }

  const raw = String(value).trim();
  const match = raw.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (match) return `${match[3]}/${match[2]}/${match[1]}`;

  const parsed = new Date(raw);
  if (Number.isNaN(parsed.getTime())) return fallback || raw;
  return formatPreviewDate(parsed, fallback);
}

function formatPreviewQuantity(value) {
  const amount = Number(value || 0);
  if (!Number.isFinite(amount)) return '0';
  return amount.toLocaleString('es-PE', {
    minimumFractionDigits: Number.isInteger(amount) ? 0 : 2,
    maximumFractionDigits: 2,
  });
}

function getCondicionPagoLabel(value) {
  return CONDICIONES_PAGO.find((option) => option.value === value)?.label || 'Contado';
}

function getTipoDocumentoClienteLabel(value) {
  const map = {
    '6': 'RUC',
    '1': 'DNI',
    '4': 'CE',
    '7': 'PASAPORTE',
    '0': 'DOC',
  };
  return map[String(value || '')] || 'DOC';
}

function getMonedaTexto(moneda) {
  return moneda === 'USD' ? 'DOLARES' : 'SOLES';
}

function normalizeWordsForCurrency(text) {
  return text
    .replace(/\bVEINTIUNO\b/g, 'VEINTIUN')
    .replace(/\bTREINTA Y UNO\b/g, 'TREINTA Y UN')
    .replace(/\bCUARENTA Y UNO\b/g, 'CUARENTA Y UN')
    .replace(/\bCINCUENTA Y UNO\b/g, 'CINCUENTA Y UN')
    .replace(/\bSESENTA Y UNO\b/g, 'SESENTA Y UN')
    .replace(/\bSETENTA Y UNO\b/g, 'SETENTA Y UN')
    .replace(/\bOCHENTA Y UNO\b/g, 'OCHENTA Y UN')
    .replace(/\bNOVENTA Y UNO\b/g, 'NOVENTA Y UN')
    .replace(/\bUNO\b/g, 'UN');
}

function convertNumberBelowHundred(value) {
  const units = ['CERO', 'UNO', 'DOS', 'TRES', 'CUATRO', 'CINCO', 'SEIS', 'SIETE', 'OCHO', 'NUEVE'];
  const specials = {
    10: 'DIEZ',
    11: 'ONCE',
    12: 'DOCE',
    13: 'TRECE',
    14: 'CATORCE',
    15: 'QUINCE',
    16: 'DIECISEIS',
    17: 'DIECISIETE',
    18: 'DIECIOCHO',
    19: 'DIECINUEVE',
    20: 'VEINTE',
    21: 'VEINTIUNO',
    22: 'VEINTIDOS',
    23: 'VEINTITRES',
    24: 'VEINTICUATRO',
    25: 'VEINTICINCO',
    26: 'VEINTISEIS',
    27: 'VEINTISIETE',
    28: 'VEINTIOCHO',
    29: 'VEINTINUEVE',
  };
  const tens = ['', '', '', 'TREINTA', 'CUARENTA', 'CINCUENTA', 'SESENTA', 'SETENTA', 'OCHENTA', 'NOVENTA'];

  if (value < 10) return units[value];
  if (specials[value]) return specials[value];

  const ten = Math.floor(value / 10);
  const unit = value % 10;
  return unit === 0 ? tens[ten] : `${tens[ten]} Y ${units[unit]}`;
}

function convertNumberBelowThousand(value) {
  const hundreds = ['', 'CIENTO', 'DOSCIENTOS', 'TRESCIENTOS', 'CUATROCIENTOS', 'QUINIENTOS', 'SEISCIENTOS', 'SETECIENTOS', 'OCHOCIENTOS', 'NOVECIENTOS'];

  if (value === 0) return 'CERO';
  if (value === 100) return 'CIEN';
  if (value < 100) return convertNumberBelowHundred(value);

  const hundred = Math.floor(value / 100);
  const remainder = value % 100;
  return remainder === 0
    ? hundreds[hundred]
    : `${hundreds[hundred]} ${convertNumberBelowHundred(remainder)}`;
}

function numberToSpanishWords(value) {
  const amount = Math.floor(Number(value || 0));
  if (!Number.isFinite(amount) || amount <= 0) return 'CERO';
  if (amount < 1000) return convertNumberBelowThousand(amount);

  const millions = Math.floor(amount / 1000000);
  const thousands = Math.floor((amount % 1000000) / 1000);
  const remainder = amount % 1000;
  const parts = [];

  if (millions > 0) {
    parts.push(millions === 1 ? 'UN MILLON' : `${numberToSpanishWords(millions)} MILLONES`);
  }

  if (thousands > 0) {
    parts.push(thousands === 1 ? 'MIL' : `${numberToSpanishWords(thousands)} MIL`);
  }

  if (remainder > 0) {
    parts.push(numberToSpanishWords(remainder));
  }

  return parts.join(' ').trim();
}

function amountToWords(amount, moneda) {
  const safeAmount = Math.round(Number(amount || 0) * 100) / 100;
  const integerPart = Math.floor(safeAmount);
  const decimalPart = String(Math.round((safeAmount - integerPart) * 100)).padStart(2, '0');
  const currencyName = moneda === 'USD' ? 'DOLARES' : 'SOLES';
  const textInteger = normalizeWordsForCurrency(numberToSpanishWords(integerPart));
  return `SON: ${textInteger} CON ${decimalPart}/100 ${currencyName}`;
}

function getPreviewClientData(clienteId, clienteForm, clientes) {
  const selectedClient = clientes.find((item) => String(item.id) === String(clienteId)) || null;
  return {
    razon_social: (clienteForm?.razon_social || selectedClient?.razon_social || 'Cliente general').trim(),
    tipo_documento: clienteForm?.tipo_documento || selectedClient?.tipo_documento || '0',
    numero_documento: (clienteForm?.numero_documento || selectedClient?.numero_documento || '').trim(),
    direccion: (clienteForm?.direccion || selectedClient?.direccion || '-').trim() || '-',
  };
}

function CotizacionPreviewSheet({
  tenantData,
  user,
  cliente,
  moneda,
  condicion,
  fechaVenc,
  items,
  observationLines,
  subtotalGravado,
  igv,
  totalGeneral,
}) {
  const accentColor = tenantData?.primary_color || 'var(--brand-600)';
  const companyName = tenantData?.business_name || user?.tenant?.business_name || 'Nombre del negocio';
  const companyRuc = tenantData?.business_ruc || user?.tenant?.business_ruc || '';
  const companyAddress = tenantData?.business_address || 'Direccion no especificada';
  const companyPhone = tenantData?.business_phone || '';
  const companyEmail = user?.business_email || user?.email || '';
  const paymentMethods = normalizePaymentMethods(tenantData?.bank_accounts);
  const validItems = items
    .filter((item) => item.descripcion?.trim() && Number(item.cantidad) > 0 && Number(item.precio_unitario) > 0)
    .map((item) => {
      const quantity = Number(item.cantidad) || 0;
      const unitPrice = Number(item.precio_unitario) || 0;
      const lineTotal = quantity * unitPrice;
      const itemIgv = item.tipo_afectacion_igv === '10' ? (lineTotal * 0.18) / 1.18 : 0;
      return {
        descripcion: item.descripcion.trim(),
        cantidad: quantity,
        precio_unitario: unitPrice,
        igv: itemIgv,
        total: lineTotal,
      };
    });
  const displayItems = validItems.length > 0 ? validItems : [{
    descripcion: 'Sin items agregados',
    cantidad: 0,
    precio_unitario: 0,
    igv: 0,
    total: 0,
  }];
  const todayLabel = formatPreviewDate(new Date(), '');
  const dueDateLabel = formatPreviewDate(fechaVenc, todayLabel);
  const amountInWords = amountToWords(totalGeneral, moneda);
  const displayObservationLines = (observationLines || []).filter((line) => line?.text?.trim());
  const currencySymbol = moneda === 'USD' ? '$' : 'S/';

  return (
    <div style={{ background: 'var(--border-subtle)', padding: '16px', display: 'flex', justifyContent: 'center' }}>
      <div className="cotizacion-preview-sheet" style={{ '--quote-preview-accent': accentColor, width: '794px', minHeight: '1123px', background: '#fff', boxShadow: '0 2px 16px rgba(0,0,0,0.18)', padding: '32px 36px', display: 'flex', flexDirection: 'column' }}>
        <div className="cotizacion-preview-header">
          <div className="cotizacion-preview-logo">
            {tenantData?.logo_filename ? (
              <img src={tenantData.logo_filename} alt={`Logo ${companyName}`} />
            ) : (
              <div className="cotizacion-preview-logo-fallback">{companyName}</div>
            )}
          </div>

          <div className="cotizacion-preview-company">
            <div className="cotizacion-preview-company-name">{companyName.toUpperCase()}</div>
            <div className="cotizacion-preview-company-meta">{companyAddress}</div>
            {companyEmail && <div className="cotizacion-preview-company-meta">{companyEmail}</div>}
            {companyPhone && <div className="cotizacion-preview-company-meta">{companyPhone}</div>}
          </div>

          <div className="cotizacion-preview-docbox">
            {companyRuc && <div className="cotizacion-preview-docbox-ruc">RUC {companyRuc}</div>}
            <div className="cotizacion-preview-docbox-title">COTIZACION</div>
            <div className="cotizacion-preview-docbox-number">N° 0000</div>
          </div>
        </div>

        <div className="cotizacion-preview-client">
          <div className="cotizacion-preview-client-grid">
            <div className="cotizacion-preview-client-label">Senores:</div>
            <div className="cotizacion-preview-client-value">{cliente.razon_social}</div>
            <div className="cotizacion-preview-client-label">Emision:</div>
            <div className="cotizacion-preview-client-value">{todayLabel}</div>

            <div className="cotizacion-preview-client-label">{getTipoDocumentoClienteLabel(cliente.tipo_documento)}:</div>
            <div className="cotizacion-preview-client-value">{cliente.numero_documento || '-'}</div>
            <div className="cotizacion-preview-client-label">Vencimiento:</div>
            <div className="cotizacion-preview-client-value">{condicion === 'contado' ? todayLabel : dueDateLabel}</div>

            <div className="cotizacion-preview-client-label">Direccion:</div>
            <div className="cotizacion-preview-client-value">{cliente.direccion || '-'}</div>
            <div className="cotizacion-preview-client-label">Moneda:</div>
            <div className="cotizacion-preview-client-value">{getMonedaTexto(moneda)}</div>
          </div>
        </div>

        <div className="cotizacion-preview-table-wrap">
          <table className="cotizacion-preview-table">
            <thead>
              <tr>
                <th>Descripcion</th>
                <th>Cantidad</th>
                <th>P.Unit</th>
                <th>IGV</th>
                <th>Precio</th>
              </tr>
            </thead>
            <tbody>
              {displayItems.map((item, index) => (
                <tr key={`${item.descripcion}-${index}`}>
                  <td>{item.descripcion}</td>
                  <td>{formatPreviewQuantity(item.cantidad)}</td>
                  <td>{`${currencySymbol} ${fmt(item.precio_unitario)}`}</td>
                  <td>{`${currencySymbol} ${fmt(item.igv)}`}</td>
                  <td>{`${currencySymbol} ${fmt(item.total)}`}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="cotizacion-preview-totals">
          <div className="cotizacion-preview-total-row">
            <span>Total Gravado</span>
            <span>{`${currencySymbol} ${fmt(subtotalGravado)}`}</span>
          </div>
          <div className="cotizacion-preview-total-row">
            <span>Total IGV</span>
            <span>{`${currencySymbol} ${fmt(igv)}`}</span>
          </div>
          <div className="cotizacion-preview-total-row is-strong">
            <span>Importe Total</span>
            <span>{`${currencySymbol} ${fmt(totalGeneral)}`}</span>
          </div>
        </div>

        <div className="cotizacion-preview-amount">
          <div className="cotizacion-preview-amount-line">
            IMPORTE TOTAL A PAGAR {currencySymbol} {fmt(totalGeneral)}
          </div>
          <div className="cotizacion-preview-amount-line">{amountInWords}</div>
        </div>

        <div className="cotizacion-preview-footer">
          <div className="cotizacion-preview-footer-meta">
            <span>Condicion de pago:</span> {getCondicionPagoLabel(condicion)}
          </div>

          {displayObservationLines.map((line, index) => (
            <div
              key={`preview-note-${index}`}
              className={`cotizacion-preview-note ${line.bold ? 'cotizacion-preview-note--primary' : ''}`}
              style={{ color: line.color }}
            >
              {line.text}
            </div>
          ))}

          {paymentMethods.length > 0 && (
            <div className="cotizacion-preview-bank">
              <div className="cotizacion-preview-bank-title">Datos para la Transferencia</div>
              <div className="cotizacion-preview-bank-line">
                Beneficiario: {companyName.toUpperCase()}
              </div>
              {paymentMethods.map((method, index) => {
                const preview = getPaymentMethodPreview(method);
                if (!preview) return null;
                return (
                  <div key={`${preview.title}-${index}`} className="cotizacion-preview-bank-item">
                    <div className="cotizacion-preview-bank-name">{preview.title}</div>
                    {preview.lines.map((line, lineIndex) => (
                      <div key={`${preview.title}-${lineIndex}`} className="cotizacion-preview-bank-line">
                        {line}
                      </div>
                    ))}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Modal: Nuevo cliente ─────────────────────────────────────────────────────

function NuevoClienteModal({ onClose, onCreated, initialName = '' }) {
  const toast = useToast();
  const [saving, setSaving] = useState(false);
  const [lookup, setLookup] = useState(false);
  const [phoneError, setPhoneError] = useState(null);
  const [form, setForm] = useState({
    tipo_documento: '1',
    numero_documento: '',
    razon_social: '',
    direccion: '',
    telefono: '',
    email: '',
  });
  const set = (k) => (v) => {
    const rawValue = typeof v === 'string' ? v : v.target.value;
    const nextValue = k === 'telefono' ? normalizePeruMobileInput(rawValue) : rawValue;
    setForm((f) => ({ ...f, [k]: nextValue }));
    if (k === 'telefono') {
      setPhoneError(validatePeruMobilePhone(nextValue, 'Telefono / WhatsApp'));
    }
  };

  useEffect(() => {
    setForm({
      tipo_documento: '1',
      numero_documento: '',
      razon_social: initialName || '',
      direccion: '',
      telefono: '',
      email: '',
    });
    setPhoneError(null);
  }, [initialName]);

  const handleLookup = async () => {
    if (!form.numero_documento) return;
    setLookup(true);
    try {
      const data = await cliSvc.lookupDocument(form.numero_documento);
      setForm((f) => ({
        ...f,
        razon_social: data.razon_social || data.nombre || f.razon_social,
        direccion:    data.direccion || f.direccion,
      }));
    } catch {
      toast('No se encontró el documento en SUNAT/RENIEC', 'error');
    } finally {
      setLookup(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const nextPhoneError = validatePeruMobilePhone(form.telefono, 'Telefono / WhatsApp');
    setPhoneError(nextPhoneError);
    if (nextPhoneError) return;
    setSaving(true);
    try {
      const created = await cliSvc.create(form);
      toast('Cliente creado');
      onCreated(created);
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <label className="label">Tipo documento</label>
          <CustomSelect
            value={form.tipo_documento}
            onChange={set('tipo_documento')}
            options={[
              { value: '1', label: 'DNI' },
              { value: '6', label: 'RUC' },
              { value: '4', label: 'Carnet extranjería' },
              { value: '7', label: 'Pasaporte' },
            ]}
          />
        </div>
        <div>
          <label className="label">N° documento</label>
          <div style={{ display: 'flex', gap: '6px' }}>
            <input
              required
              className="input"
              style={{ flex: 1 }}
              value={form.numero_documento}
              onChange={set('numero_documento')}
              placeholder={form.tipo_documento === '6' ? '20XXXXXXXXX' : '7XXXXXXX'}
            />
            <button
              type="button"
              onClick={handleLookup}
              disabled={lookup}
              className="btn-secondary"
              style={{ whiteSpace: 'nowrap', padding: '0 12px' }}
            >
              {lookup ? <Spinner size="sm" /> : 'Consultar'}
            </button>
          </div>
        </div>
      </div>
      <div>
        <label className="label">Razón social / Nombre</label>
        <input required className="input" value={form.razon_social} onChange={set('razon_social')} />
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <label className="label">Teléfono / WhatsApp</label>
          <input className="input" value={form.telefono} onChange={set('telefono')} inputMode="numeric" placeholder="999999999" />
          <FieldError message={phoneError} />
        </div>
        <div>
          <label className="label">Email</label>
          <input className="input" type="email" value={form.email} onChange={set('email')} />
        </div>
      </div>
      <div>
        <label className="label">Dirección</label>
        <input className="input" value={form.direccion} onChange={set('direccion')} />
      </div>
      <div className="flex justify-end gap-3 pt-2">
        <button type="button" onClick={onClose} className="btn-secondary">Cancelar</button>
        <button type="submit" disabled={saving} className="btn-primary flex items-center gap-2">
          {saving && <Spinner size="sm" />} Guardar cliente
        </button>
      </div>
    </form>
  );
}

// ─── Modal: Emitir comprobante desde cotización ───────────────────────────────

function EmitirModal({ cotizacion, onClose, onSuccess }) {
  const toast = useToast();
  const [saving, setSaving] = useState(false);
  const [tipo, setTipo] = useState('01');
  const [serieOverride, setSerieOverride] = useState('');

  const cliente = cotizacion?.cliente;
  const tipoDocCliente = cliente?.tipo_documento;
  const esRUC = tipoDocCliente === '6' || (cliente?.numero_documento?.length === 11);
  const esDNI = tipoDocCliente === '1' || (cliente?.numero_documento?.length === 8);

  const facturaInvalida = tipo === '01' && !esRUC;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (facturaInvalida) return;
    setSaving(true);
    try {
      await svc.facturar(cotizacion.id, {
        tipo_comprobante: tipo,
        serie_override: serieOverride || undefined,
      });
      toast(`Comprobante ${tipo === '01' ? 'Factura' : 'Boleta'} emitido correctamente`);
      onSuccess();
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div style={{ padding: '12px 16px', background: 'var(--bg-surface-2)', border: '1px solid var(--border-subtle)' }}>
        <p style={{ fontSize: '12px', color: 'var(--text-tertiary)', marginBottom: '2px' }}>Cotización origen</p>
        <p style={{ fontWeight: 700, fontSize: '14px' }}>
          {cotizacion?.internal_order_number || `#${cotizacion?.id}`}
          {' — '}
          {cliente?.razon_social}
        </p>
        <p style={{ fontSize: '12px', color: 'var(--text-tertiary)' }}>
          Doc. cliente: {cliente?.numero_documento} ({tipoDocCliente === '6' ? 'RUC' : tipoDocCliente === '1' ? 'DNI' : tipoDocCliente})
        </p>
      </div>

      <div>
        <label className="label">Tipo de comprobante</label>
        <CustomSelect
          value={tipo}
          onChange={setTipo}
          options={[
            { value: '01', label: 'Factura (tipo 01)' },
            { value: '03', label: 'Boleta (tipo 03)' },
          ]}
        />
      </div>

      {facturaInvalida && (
        <div style={{ padding: '10px 14px', background: 'var(--color-error-bg)', border: '1px solid rgba(220,38,38,0.2)', color: 'var(--color-error)', fontSize: '13px' }}>
          Para emitir factura, el cliente debe tener RUC (11 dígitos). El cliente actual tiene{' '}
          {esDNI ? 'DNI' : `documento tipo ${tipoDocCliente}`}.
          Cambia a Boleta o actualiza el documento del cliente.
        </div>
      )}

      <div>
        <label className="label">Serie (opcional — deja vacío para usar la serie por defecto)</label>
        <input
          className="input"
          value={serieOverride}
          onChange={(e) => setSerieOverride(e.target.value)}
          placeholder={tipo === '01' ? 'F001' : 'B001'}
        />
      </div>

      <div className="flex justify-end gap-3">
        <button type="button" onClick={onClose} className="btn-secondary">Cancelar</button>
        <button
          type="submit"
          disabled={saving || facturaInvalida}
          className="btn-primary flex items-center gap-2"
        >
          {saving && <Spinner size="sm" />}
          Emitir {tipo === '01' ? 'Factura' : 'Boleta'}
        </button>
      </div>
    </form>
  );
}

// ─── Modal: Anular documento ──────────────────────────────────────────────────

function AnularModal({ documento, onClose, onSuccess }) {
  const toast = useToast();
  const [saving, setSaving] = useState(false);
  const [motivo, setMotivo] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await svc.anular({ comprobante_id: documento.id, motivo });
      toast('Documento anulado');
      onSuccess();
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  const docNum = documento.serie
    ? `${documento.serie}-${String(documento.correlativo || 0).padStart(6, '0')}`
    : `#${documento.id}`;

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div style={{ padding: '12px 16px', background: 'var(--color-error-bg)', border: '1px solid rgba(220,38,38,0.2)' }}>
        <p style={{ fontSize: '13px', fontWeight: 700, color: 'var(--color-error)' }}>
          Anulación: {docNum}
        </p>
        <p style={{ fontSize: '12px', color: 'var(--text-tertiary)', marginTop: '2px' }}>
          {documento.cliente?.razon_social} — Total: {documento.moneda === 'USD' ? '$' : 'S/'} {fmt(documento.total_venta)}
        </p>
      </div>
      <div>
        <label className="label">Motivo de anulación</label>
        <textarea
          required
          className="input"
          rows={3}
          value={motivo}
          onChange={(e) => setMotivo(e.target.value)}
          placeholder="Describe el motivo de la anulación..."
          style={{ resize: 'vertical', minHeight: '80px' }}
        />
      </div>
      <div className="flex justify-end gap-3">
        <button type="button" onClick={onClose} className="btn-secondary">Cancelar</button>
        <button type="submit" disabled={saving || !motivo.trim()} className="btn-primary flex items-center gap-2" style={{ background: 'var(--color-error)' }}>
          {saving && <Spinner size="sm" />} Anular documento
        </button>
      </div>
    </form>
  );
}

// ─── Modal: Nota de crédito / débito ─────────────────────────────────────────

function NotaModal({ documento, onClose, onSuccess }) {
  const toast = useToast();
  const [saving, setSaving] = useState(false);
  const [tipoNota, setTipoNota] = useState('credito');
  const [codMotivo, setCodMotivo] = useState('01');
  const [descMotivo, setDescMotivo] = useState('');

  const motivos = tipoNota === 'credito' ? MOTIVOS_NC : MOTIVOS_ND;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await svc.notas({
        comprobante_afectado_id: documento.id,
        tipo_nota: tipoNota,
        cod_motivo: codMotivo,
        descripcion_motivo: descMotivo,
      });
      toast(`Nota de ${tipoNota} emitida`);
      onSuccess();
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  const docNum = documento.serie
    ? `${documento.serie}-${String(documento.correlativo || 0).padStart(6, '0')}`
    : `#${documento.id}`;

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div style={{ padding: '12px 16px', background: 'var(--bg-surface-2)', border: '1px solid var(--border-subtle)' }}>
        <p style={{ fontSize: '12px', color: 'var(--text-tertiary)' }}>Documento afectado</p>
        <p style={{ fontWeight: 700, fontSize: '14px' }}>{docNum} — {documento.cliente?.razon_social}</p>
      </div>

      <div>
        <label className="label">Tipo de nota</label>
        <CustomSelect
          value={tipoNota}
          onChange={(v) => { setTipoNota(v); setCodMotivo('01'); }}
          options={[
            { value: 'credito', label: 'Nota de Crédito' },
            { value: 'debito',  label: 'Nota de Débito' },
          ]}
        />
      </div>

      <div>
        <label className="label">Motivo</label>
        <CustomSelect
          value={codMotivo}
          onChange={setCodMotivo}
          options={motivos}
        />
      </div>

      <div>
        <label className="label">Descripción adicional (opcional)</label>
        <textarea
          className="input"
          rows={2}
          value={descMotivo}
          onChange={(e) => setDescMotivo(e.target.value)}
          placeholder="Detalle adicional del motivo..."
          style={{ resize: 'vertical' }}
        />
      </div>

      <div className="flex justify-end gap-3">
        <button type="button" onClick={onClose} className="btn-secondary">Cancelar</button>
        <button type="submit" disabled={saving} className="btn-primary flex items-center gap-2">
          {saving && <Spinner size="sm" />} Emitir nota
        </button>
      </div>
    </form>
  );
}

// ─── Formulario: Nueva cotización ─────────────────────────────────────────────

function NuevaCotizacionForm({
  onSave,
  onClear,
  saving,
  clientes,
  productosDisp,
  onNuevoCliente,
  quoteCountByClient = {},
  recentClientIds = [],
  createdClient,
}) {
  const { user } = useAuth();
  const toast = useToast();
  const emptyItem = () => ({
    producto_id: '',
    codigo: '',
    descripcion: '',
    cantidad: 1,
    precio_unitario: '',
    unidad_medida: 'NIU',
    tipo_afectacion_igv: '10',
    _isNew: false,
  });

  const [clienteId, setClienteId]       = useState('');
  const [clienteForm, setClienteForm]   = useState(null);  // current form values from ClientCombobox
  const [clienteDirty, setClienteDirty] = useState(false); // existing client edited
  const [clienteIsNew, setClienteIsNew] = useState(false);
  const [moneda, setMoneda]             = useState('PEN');
  const [condicion, setCondicion]       = useState('contado');
  const [fechaVenc, setFechaVenc]       = useState('');
  const [observationLines, setObservationLines] = useState(buildDefaultObservationLines());
  const [observacionesOpen, setObservacionesOpen] = useState(true);
  const [avanzado, setAvanzado]         = useState(false);
  const [items, setItems]               = useState([emptyItem()]);
  const [previewOpen, setPreviewOpen]   = useState(false);
  const [tenantData, setTenantData]     = useState(null);
  const [observationsInitialized, setObservationsInitialized] = useState(false);

  // Pre-fill condición de pago desde el cliente seleccionado
  useEffect(() => {
    const saved = localStorage.getItem(ADVANCED_PREF_KEY);
    if (saved !== null) {
      setAvanzado(saved === '1');
    }
  }, []);

  useEffect(() => {
    localStorage.setItem(ADVANCED_PREF_KEY, avanzado ? '1' : '0');
  }, [avanzado]);

  useEffect(() => {
    let active = true;

    tenantSvc.get()
      .then((response) => {
        if (!active) return;
        setTenantData(response);
        setObservationLines((current) => {
          if (observationsInitialized) return current;
          return buildDefaultObservationLines(response);
        });
        setObservationsInitialized(true);
      })
      .catch(() => {});

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (createdClient?.id) {
      setClienteId(String(createdClient.id));
    }
  }, [createdClient]);

  useEffect(() => {
    const cli = clientes.find((c) => String(c.id) === String(clienteId));
    if (cli?.condicion_pago) {
      setCondicion(cli.condicion_pago);
    }
  }, [clienteId, clientes]);

  // Auto-calc fecha vencimiento según condición
  useEffect(() => {
    if (condicion === 'contado') {
      setFechaVenc('');
      return;
    }
    setFechaVenc(calcFechaVencimiento(condicion));
  }, [condicion]);

  const addItem    = () => setItems((cur) => [...cur, emptyItem()]);
  const removeItem = (idx) => setItems((cur) => cur.filter((_, i) => i !== idx));
  const setItemAll = (idx, next) =>
    setItems((cur) => cur.map((it, i) => (i === idx ? { ...it, ...next } : it)));
  const setItem    = (idx, key, val) =>
    setItems((cur) => cur.map((it, i) => (i === idx ? { ...it, [key]: val } : it)));

  const handleClientFormChange = (formData, { isDirty, isNew }) => {
    setClienteForm(formData);
    setClienteDirty(isDirty);
    setClienteIsNew(isNew);
  };

  const handleGenerateCode = async () => {
    try {
      const data = await prodSvc.generateCode();
      return data.codigo;
    } catch {
      return '';
    }
  };

  const updateObservationLine = (index, patch) => {
    setObservationLines((current) => current.map((line, lineIndex) => (
      lineIndex === index ? { ...line, ...patch } : line
    )));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (clienteIsNew && !clienteForm?.razon_social?.trim()) {
      toast('Falta nombre del cliente', 'error');
      return;
    }
    if (!clienteId && !clienteIsNew && !clienteForm?.razon_social) return;

    try {
      // 1. Upsert client if needed
      const resolvedClienteId = await upsertCliente({
        id:      clienteId,
        isNew:   clienteIsNew,
        isDirty: clienteDirty,
        form:    clienteForm || {},
      });

      // 2. Upsert new products
      const resolvedItems = await upsertProductos(items);

      // 3. Create quote
      onSave({
        cliente_id:        Number(resolvedClienteId),
        moneda,
        tipo_comprobante:  '00',
        condicion_pago:    condicion,
        fecha_vencimiento: condicion === 'contado' ? undefined : (fechaVenc || undefined),
        observaciones:     observationLines.some((line) => line.text?.trim())
          ? serializeObservationLines(observationLines)
          : undefined,
        items: resolvedItems
          .filter((it) => it.descripcion?.trim() && Number(it.cantidad) > 0 && Number(it.precio_unitario) > 0)
          .map((it) => ({
            producto_id:         it.producto_id ? Number(it.producto_id) : undefined,
            descripcion:         it.descripcion,
            cantidad:            Number(it.cantidad),
            precio_unitario:     Number(it.precio_unitario),
            unidad_medida:       it.unidad_medida,
            tipo_afectacion_igv: it.tipo_afectacion_igv,
          })),
      });
    } catch (err) {
      // onSave's parent handles errors; surface this one for product/client failures
      throw err;
    }
  };

  const handleClear = () => {
    setClienteId('');
    setClienteForm(null);
    setClienteDirty(false);
    setClienteIsNew(false);
    setMoneda('PEN');
    setCondicion('contado');
    setFechaVenc('');
    setObservationLines(buildDefaultObservationLines(tenantData));
    setObservacionesOpen(true);
    setItems([emptyItem()]);
    onClear?.();
  };

  const sym = moneda === 'USD' ? '$' : 'S/';

  // Totales desglosados por afectación
  const totales = items.reduce((acc, it) => {
    const lineTotal = (Number(it.cantidad) * Number(it.precio_unitario) || 0);
    const af = it.tipo_afectacion_igv;
    if (af === '20') acc.exonerado += lineTotal;
    else if (af === '30') acc.inafecto += lineTotal;
    else if (af === '40') acc.exportacion += lineTotal;
    else acc.gravado += lineTotal;
    return acc;
  }, { gravado: 0, exonerado: 0, inafecto: 0, exportacion: 0 });

  const igv = totales.gravado * 0.18 / 1.18;
  const subtotalGravado = totales.gravado - igv;
  const totalGeneral = totales.gravado + totales.exonerado + totales.inafecto + totales.exportacion;
  const previewClient = getPreviewClientData(clienteId, clienteForm, clientes);
  const hasObservationLines = observationLines.some((line) => line.text?.trim());

  return (
    <>
      <form onSubmit={handleSubmit} className="view-embedded-form cotizaciones-form-surface">

      {/* Sección: Cliente, moneda, condición */}
      <div className="cotizacion-form-section cotizacion-form-section--entry">
        <div className="cotizacion-entry-layout">
          <div className="cotizacion-entry-main">
            <label className="label" style={{ marginBottom: '6px' }}>Cliente</label>
            <ClientCombobox
              value={clienteId}
              onChange={setClienteId}
              clients={clientes}
              onFormChange={handleClientFormChange}
              quoteCountByClient={quoteCountByClient}
              recentClientIds={recentClientIds}
            />
          </div>
          <div className="cotizacion-entry-sidebar">
            <div className="cotizacion-field-stack">
              <label className="label">Moneda</label>
            <CustomSelect
              value={moneda}
              onChange={setMoneda}
              options={[
                { value: 'PEN', label: 'PEN (S/) Soles' },
                { value: 'USD', label: 'USD ($) Dólares' },
              ]}
              />
            </div>
            <div className="cotizacion-entry-sidebar-grid">
              <div className="cotizacion-field-stack">
            <label className="label">Condición de pago</label>
            <CustomSelect
              value={condicion}
              onChange={setCondicion}
              options={CONDICIONES_PAGO}
            />
          </div>
              <div className="cotizacion-field-stack">
            <label className="label">Fecha vencimiento</label>
            <DatePicker
              value={fechaVenc}
              onChange={setFechaVenc}
              disabled={condicion === 'contado'}
            />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Sección: Líneas de detalle */}
      <div className="cotizacion-form-section cotizacion-form-section--detail">
        <div className="cotizacion-detail-header">
          <p className="cotizacion-section-kicker">
            Líneas de detalle
          </p>
          <button
            type="button"
            onClick={() => setAvanzado((current) => !current)}
            className={`cotizacion-advanced-toggle ${avanzado ? 'is-active' : ''}`}
            aria-checked={avanzado}
            role="switch"
          >
            <span className="cotizacion-advanced-toggle-track">
              <span className="cotizacion-advanced-toggle-thumb" />
            </span>
            <span>Mostrar unidad y afectacion IGV</span>
          </button>
        </div>

        <div style={{ background: '#fff', border: '1px solid var(--border-subtle)', overflow: 'hidden' }}>
          <div className="ink-table-scroll">
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead style={{ background: 'var(--bg-surface-2)', borderBottom: '1px solid var(--border-subtle)' }}>
                <tr>
                  <th style={thStyle(avanzado ? '44%' : '60%')}>Código / Producto</th>
                  {avanzado && <th style={thStyle('10%')}>Unidad</th>}
                  {avanzado && <th style={thStyle('10%')}>Afectación</th>}
                  <th style={thStyle('8%', 'right')}>Cant.</th>
                  <th style={thStyle('12%', 'right')}>P. Unit.</th>
                  <th style={thStyle('10%', 'right')}>Total</th>
                  <th style={{ width: '4%', background: 'var(--bg-surface-2)' }} />
                </tr>
              </thead>
              <tbody style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                {items.map((item, idx) => {
                  const lineTotal = Number(item.cantidad) * Number(item.precio_unitario) || 0;
                  return (
                    <tr key={idx} style={{ borderBottom: '1px solid var(--bg-surface-2)' }}>
                      <td className="spreadsheet-cell" style={{ borderRight: '1px solid var(--border-subtle)', padding: '4px 6px' }}>
                        <ProductLineCell
                          value={item}
                          onChange={(next) => setItemAll(idx, next)}
                          products={productosDisp}
                          incluyeIgv
                          sym={sym}
                          onGenerateCode={handleGenerateCode}
                        />
                      </td>
                      {avanzado && (
                        <td className="spreadsheet-cell" style={{ borderRight: '1px solid var(--border-subtle)', padding: 0 }}>
                          <CustomSelect
                            compact
                            value={item.unidad_medida}
                            onChange={(v) => setItem(idx, 'unidad_medida', v)}
                            options={UNIDADES_MEDIDA}
                          />
                        </td>
                      )}
                      {avanzado && (
                        <td className="spreadsheet-cell" style={{ borderRight: '1px solid var(--border-subtle)', padding: 0 }}>
                          <CustomSelect
                            compact
                            value={item.tipo_afectacion_igv}
                            onChange={(v) => setItem(idx, 'tipo_afectacion_igv', v)}
                            options={AFECTACION_IGV}
                          />
                        </td>
                      )}
                      <td className="spreadsheet-cell" style={{ borderRight: '1px solid var(--border-subtle)', padding: 0 }}>
                        <input
                          required type="number" min="0.01" step="any"
                          className="spreadsheet-input spreadsheet-input-mono input-no-spinner"
                          value={item.cantidad}
                          onChange={(e) => setItem(idx, 'cantidad', e.target.value)}
                        />
                      </td>
                      <td className="spreadsheet-cell" style={{ borderRight: '1px solid var(--border-subtle)', padding: 0, position: 'relative' }}>
                        <span style={prefixStyle}>{sym}</span>
                        <input
                          required type="number" min="0.01" step="0.01"
                          className="spreadsheet-input spreadsheet-input-mono input-no-spinner"
                          style={{ paddingLeft: '24px' }}
                          value={item.precio_unitario}
                          onChange={(e) => setItem(idx, 'precio_unitario', e.target.value)}
                        />
                      </td>
                      <td style={{ borderRight: '1px solid var(--border-subtle)', background: 'var(--bg-surface-2)', position: 'relative' }}>
                        <span style={prefixStyle}>{sym}</span>
                        <input
                          readOnly
                          className="spreadsheet-input spreadsheet-input-mono"
                          style={{ paddingLeft: '24px', color: 'var(--text-tertiary)' }}
                          value={fmt(lineTotal)}
                        />
                      </td>
                      <td style={{ padding: 0, textAlign: 'center' }}>
                        {items.length > 1 && (
                          <button
                            type="button"
                            onClick={() => removeItem(idx)}
                            style={{ width: '100%', minHeight: '40px', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'none', border: 'none', color: 'var(--border-subtle)', cursor: 'pointer' }}
                            onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--color-error)'; }}
                            onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--border-subtle)'; }}
                          >
                            <Trash2 style={{ width: '14px', height: '14px' }} />
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div style={{ padding: '8px', background: '#fff', borderTop: '1px solid var(--border-subtle)' }}>
            <button
              type="button"
              onClick={addItem}
              style={{ display: 'flex', alignItems: 'center', gap: '6px', fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--brand-600)', background: 'none', border: 'none', cursor: 'pointer', padding: '6px 16px' }}
              onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--brand-100)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = 'none'; }}
            >
              <PlusCircle style={{ width: '14px', height: '14px' }} /> Agregar línea
            </button>
          </div>
        </div>

        {/* Panel de totales */}
        <div className="cotizacion-modal-summary-wrap">
          <div className="cotizacion-modal-summary">
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontFamily: 'var(--font-mono)', fontSize: '13px' }}>
              {totales.gravado > 0 && (
                <>
                  <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-tertiary)' }}>
                    <span>Subtotal gravado</span>
                    <span>{sym} {fmt(subtotalGravado)}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-tertiary)' }}>
                    <span>IGV (18%)</span>
                    <span>{sym} {fmt(igv)}</span>
                  </div>
                </>
              )}
              {totales.exonerado > 0 && (
                <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-tertiary)' }}>
                  <span>Exonerado</span>
                  <span>{sym} {fmt(totales.exonerado)}</span>
                </div>
              )}
              {totales.inafecto > 0 && (
                <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-tertiary)' }}>
                  <span>Inafecto</span>
                  <span>{sym} {fmt(totales.inafecto)}</span>
                </div>
              )}
              {totales.exportacion > 0 && (
                <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-tertiary)' }}>
                  <span>Exportación</span>
                  <span>{sym} {fmt(totales.exportacion)}</span>
                </div>
              )}
              <div style={{ paddingTop: '12px', borderTop: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
                <span style={{ fontWeight: 700, color: 'var(--text-primary)', fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Total cotización</span>
                <span style={{ fontSize: '22px', fontWeight: 900, color: 'var(--brand-600)' }}>{sym} {fmt(totalGeneral)}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Sección: Observaciones */}
      <div className="cotizacion-form-section cotizacion-form-section--notes">
        {!observacionesOpen && !hasObservationLines ? (
          <button
            type="button"
            className="cotizacion-observaciones-toggle"
            onClick={() => setObservacionesOpen(true)}
          >
            <ChevronDown style={{ width: '14px', height: '14px' }} />
            + Anadir observaciones
          </button>
        ) : (
          <div>
            <button
              type="button"
              className="cotizacion-observaciones-toggle"
              onClick={() => setObservacionesOpen((current) => !current)}
              style={{ marginBottom: '12px' }}
            >
              {observacionesOpen ? <ChevronUp style={{ width: '14px', height: '14px' }} /> : <ChevronDown style={{ width: '14px', height: '14px' }} />}
              {observacionesOpen ? 'Ocultar observaciones' : 'Mostrar observaciones'}
            </button>
            {observacionesOpen && (
              <div style={{ display: 'grid', gap: '12px' }}>
                <label className="label">Observaciones (aparecen en el PDF)</label>
                {observationLines.map((line, index) => (
                  <div key={`observation-line-${index}`} style={{ border: '1px solid var(--border-subtle)', background: 'var(--bg-surface-2)', padding: '12px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px', marginBottom: '10px', flexWrap: 'wrap' }}>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-secondary)' }}>
                        Linea {index + 1}
                      </span>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                        <label style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: 'var(--text-secondary)' }}>
                          <input
                            type="checkbox"
                            checked={line.bold}
                            onChange={(event) => updateObservationLine(index, { bold: event.target.checked })}
                          />
                          Negrita
                        </label>
                        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: 'var(--text-secondary)' }}>
                          Color
                          <ColorPickerField
                            value={line.color}
                            onChange={(val) => updateObservationLine(index, { color: val })}
                            fallback={index === 0 ? 'var(--color-error)' : '#111111'}
                            presets={['var(--color-error)', 'var(--color-error)', 'var(--color-warning)', 'var(--color-warning)', 'var(--text-primary)', 'var(--brand-600)']}
                            openUpward
                          />
                        </div>
                      </div>
                    </div>
                    <textarea
                      className="input"
                      rows={2}
                      value={line.text}
                      onChange={(event) => updateObservationLine(index, { text: event.target.value })}
                      placeholder={index === 0 ? DEFAULT_NOTE_1_TEXT : DEFAULT_NOTE_2_TEXT}
                      style={{
                        resize: 'vertical',
                        color: line.color,
                        fontWeight: line.bold ? 700 : 400,
                      }}
                    />
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="modal-footer cotizacion-form-footer">
        <button type="button" onClick={handleClear} className="cotizacion-clear-link">
          Limpiar formulario
        </button>
        <div className="cotizacion-form-actions">
          <button
            type="button"
            onClick={() => setPreviewOpen(true)}
            className="btn-secondary cotizacion-preview-button"
          >
            <Eye className="h-4 w-4" />
            Vista previa
          </button>
          <button
            type="submit"
            disabled={saving || (!clienteId && !clienteForm?.razon_social)}
            className="btn-primary"
            style={{ minWidth: '220px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}
          >
            {saving ? <Spinner size="sm" /> : <Receipt className="h-4 w-4" />}
            Guardar cotizacion
          </button>
        </div>
      </div>
      </form>

      <Modal
        open={previewOpen}
        onClose={() => setPreviewOpen(false)}
        title="Vista previa de cotizacion"
        size="xl"
      >
        <div style={{ margin: '-24px', overflow: 'auto', maxHeight: '82vh' }}>
          <CotizacionPreviewSheet
            tenantData={tenantData}
            user={user}
            cliente={previewClient}
            moneda={moneda}
            condicion={condicion}
            fechaVenc={fechaVenc}
            items={items}
            observationLines={observationLines}
            subtotalGravado={subtotalGravado}
            igv={igv}
            totalGeneral={totalGeneral}
          />
        </div>
      </Modal>
    </>
  );
}

// Estilos inline reutilizables
const thStyle = (width, textAlign = 'left') => ({
  padding: '8px 16px',
  textAlign,
  fontFamily: 'var(--font-mono)',
  fontSize: '10px',
  fontWeight: 700,
  color: 'var(--text-secondary)',
  textTransform: 'uppercase',
  letterSpacing: '0.08em',
  borderRight: '1px solid var(--border-subtle)',
  width,
});

const prefixStyle = {
  position: 'absolute',
  left: '8px',
  top: '50%',
  transform: 'translateY(-50%)',
  fontSize: '10px',
  color: 'var(--text-tertiary)',
  fontFamily: 'var(--font-mono)',
  fontWeight: 700,
  pointerEvents: 'none',
};

// ─── Página principal ─────────────────────────────────────────────────────────

export default function CotizacionesPage() {
  const toast = useToast();

  // Vista activa: 'create' | 'history' | 'fiscal'
  const [view, setView] = useState('create');

  // Datos compartidos
  const [clientes, setClientes]         = useState([]);
  const [productosDisp, setProductosDisp] = useState([]);
  const [loadingMaster, setLoadingMaster] = useState(true);

  // Documentos
  const [list, setList]         = useState([]);
  const [loading, setLoading]   = useState(false);
  const [saving, setSaving]     = useState(false);

  // Búsqueda y filtros
  const [search, setSearch]         = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState({
    // compartidos
    desde: '', hasta: '',
    // historial
    // fiscal
    tipo: 'all', docReceptor: '', razonSocial: '', serie: '', numero: '', moneda: 'all', formaPago: 'all',
  });

  // Fila seleccionada en tab fiscal (para activar toolbar)
  const [selectedFiscal, setSelectedFiscal] = useState(null);

  // Modales
  const [nuevoClienteOpen, setNuevoClienteOpen] = useState(false);
  const [nuevoClientePrefill, setNuevoClientePrefill] = useState('');
  const [createdClient, setCreatedClient] = useState(null);
  const [recentClientIds, setRecentClientIds] = useState([]);
  const [emitirDoc, setEmitirDoc]   = useState(null);
  const [anularDoc, setAnularDoc]   = useState(null);
  const [notaDoc, setNotaDoc]       = useState(null);

  // Carga de datos maestros (clientes y productos) — una sola vez
  useEffect(() => {
    Promise.all([cliSvc.list(), prodSvc.list()])
      .then(([c, p]) => { setClientes(c); setProductosDisp(p); })
      .finally(() => setLoadingMaster(false));
  }, []);

  const load = useCallback(() => {
    setLoading(true);
    svc.list()
      .then(setList)
      .catch(() => toast('No se pudo cargar la información. Revisa tu conexión e inténtalo nuevamente.', 'error'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  // Separación por tipo
  const quotations = list.filter((d) => d.document_kind === 'quotation');
  const fiscalDocs = list.filter((d) => d.document_kind !== 'quotation');
  const quoteCountByClient = quotations.reduce((acc, item) => {
    const clientId = item.cliente?.id;
    if (!clientId) return acc;
    acc[clientId] = (acc[clientId] || 0) + 1;
    return acc;
  }, {});

  // Filtrado historial
  const filteredHistory = quotations.filter((item) => {
    const q = search.toLowerCase();
    const matchSearch = !q
      || item.cliente?.razon_social?.toLowerCase().includes(q)
      || String(item.id).includes(q)
      || item.internal_order_number?.toLowerCase().includes(q);
    const matchDesde = !filters.desde || new Date(item.fecha_emision) >= new Date(filters.desde);
    const matchHasta = !filters.hasta || new Date(item.fecha_emision) <= new Date(filters.hasta);
    return matchSearch && matchDesde && matchHasta;
  });

  // Filtrado emitidas
  const filteredFiscal = fiscalDocs.filter((item) => {
    const matchDoc    = !filters.docReceptor  || item.cliente?.numero_documento?.includes(filters.docReceptor);
    const matchRazon  = !filters.razonSocial  || item.cliente?.razon_social?.toLowerCase().includes(filters.razonSocial.toLowerCase());
    const matchSerie  = !filters.serie        || item.serie?.toLowerCase().startsWith(filters.serie.toLowerCase());
    const matchNumero = !filters.numero       || String(item.correlativo || '').includes(filters.numero);
    const matchTipo   = filters.tipo   === 'all' || item.tipo_comprobante === filters.tipo;
    const matchMoneda = filters.moneda === 'all' || item.moneda === filters.moneda;
    const matchPago   = filters.formaPago === 'all'
      || (filters.formaPago === 'contado' && (!item.condicion_pago || item.condicion_pago === 'contado'))
      || (filters.formaPago === 'credito' && item.condicion_pago && item.condicion_pago !== 'contado');
    const matchDesde  = !filters.desde || new Date(item.fecha_emision) >= new Date(filters.desde);
    const matchHasta  = !filters.hasta || new Date(item.fecha_emision) <= new Date(filters.hasta);
    const q = search.toLowerCase();
    const matchSearch = !q
      || item.cliente?.razon_social?.toLowerCase().includes(q)
      || item.cliente?.numero_documento?.includes(q)
      || String(item.id).includes(q)
      || item.serie?.toLowerCase().includes(q);
    return matchDoc && matchRazon && matchSerie && matchNumero && matchTipo && matchMoneda && matchPago && matchDesde && matchHasta && matchSearch;
  });

  const handleOpenNuevoCliente = (prefill = '') => {
    setNuevoClientePrefill(prefill);
    setNuevoClienteOpen(true);
  };

  const handleSave = async (data) => {
    setSaving(true);
    try {
      await svc.create(data);
      toast('Cotización guardada');
      setView('history');
      load();
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleNuevoCliente = (created) => {
    setClientes((prev) => {
      const next = prev.filter((item) => item.id !== created.id);
      return [created, ...next];
    });
    setCreatedClient(created);
    setRecentClientIds((prev) => (prev.includes(created.id) ? prev : [...prev, created.id]));
    setNuevoClienteOpen(false);
    setNuevoClientePrefill('');
    toast('Cliente anadido al catalogo');
  };

  const handleEmitirSuccess = () => {
    setEmitirDoc(null);
    setView('fiscal');
    load();
  };

  const handleAnularSuccess = () => {
    setAnularDoc(null);
    load();
  };

  const handleNotaSuccess = () => {
    setNotaDoc(null);
    load();
  };

  const handleFilterChange = (k, v) => setFilters((f) => ({ ...f, [k]: v }));

  const handleOpenPdf = async (item) => {
    try {
      const data = await svc.pdf(item.id);
      const url = data?.url || data?.url_compartir || data?.public_url || data?.sunat_pdf_url;
      if (url) {
        window.open(url, '_blank', 'noopener,noreferrer');
        return;
      }
      toast(data?.detail || 'No se pudo abrir el PDF', 'error');
    } catch (err) {
      toast(err.message, 'error');
    }
  };

  const handleCopyShareLink = async (item) => {
    try {
      const data = await svc.share(item.id);
      const url = data?.url_compartir || data?.url || getPublicShareUrl(item);
      if (!url) {
        toast('No se pudo generar el enlace publico', 'error');
        return;
      }
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(url);
      } else {
        window.prompt('Copia el enlace:', url);
      }
      toast('Enlace publico copiado');
    } catch (err) {
      toast(err.message, 'error');
    }
  };

  const handleDuplicateQuote = async (item) => {
    try {
      const duplicated = await svc.duplicar(item.id);
      toast(`Cotizacion duplicada: ${duplicated.internal_order_number || `#${duplicated.id}`}`);
      load();
    } catch (err) {
      toast(err.message, 'error');
    }
  };

  const handleDeleteQuote = async (item) => {
    const confirmed = window.confirm(
      `Eliminar la cotizacion ${item.internal_order_number || `#${item.id}`}?`,
    );
    if (!confirmed) return;
    try {
      await svc.remove(item.id);
      toast('Cotizacion eliminada');
      load();
    } catch (err) {
      toast(err.message, 'error');
    }
  };

  const tabBtn = (id, label, Icon, count) => (
    <button
      type="button"
      onClick={() => setView(id)}
      className={`cotizaciones-tab ${view === id ? 'is-active' : ''}`}
    >
      <Icon className="h-4 w-4" />
      <span>{label}</span>
      {typeof count === 'number' && (
        <span className="cotizaciones-tab-badge">{count}</span>
      )}
    </button>
  );

  return (
    <div className="page-shell cotizaciones-page-shell">

      {/* Tab bar */}
      <div className="cotizaciones-tabs">
        {tabBtn('create', '+ Nueva cotizacion', Plus)}
        <span className="cotizaciones-tab-separator" />
        {tabBtn('history', 'Historial', History, quotations.length)}
        <span className="cotizaciones-tab-separator" />
        {tabBtn('fiscal', 'Emitidas SUNAT', Receipt, fiscalDocs.length)}
      </div>

      {/* ── Vista: Crear ── */}
      {view === 'create' && (
        <>
          {loadingMaster ? (
            <div className="flex justify-center py-16"><Spinner size="lg" /></div>
          ) : (
            <div className="ink-card" style={{ padding: '0', overflow: 'hidden' }}>
              <NuevaCotizacionForm
                onSave={handleSave}
                onClear={() => {}}
                saving={saving}
                clientes={clientes}
                productosDisp={productosDisp}
                onNuevoCliente={handleOpenNuevoCliente}
                quoteCountByClient={quoteCountByClient}
                recentClientIds={recentClientIds}
                createdClient={createdClient}
              />
            </div>
          )}
        </>
      )}

      {/* ── Vista: Historial ── */}
      {view === 'history' && (
        <>
          <SearchBar
            search={search}
            onSearch={setSearch}
            showFilters={showFilters}
            onToggleFilters={() => setShowFilters(!showFilters)}
            onNewAction={() => setView('create')}
            newLabel="+ Nueva cotización"
          />

          {showFilters && (
            <div className="ink-card" style={{ margin: '0 0 20px', padding: '20px' }}>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="flex flex-col gap-1">
                  <label className="label-xs">Desde</label>
                  <DatePicker compact value={filters.desde} onChange={(v) => handleFilterChange('desde', v)} />
                </div>
                <div className="flex flex-col gap-1">
                  <label className="label-xs">Hasta</label>
                  <DatePicker compact value={filters.hasta} onChange={(v) => handleFilterChange('hasta', v)} />
                </div>
              </div>
            </div>
          )}

          {loading ? (
            <div className="flex justify-center py-16"><Spinner size="lg" /></div>
          ) : filteredHistory.length === 0 ? (
            <EmptyState
              title="Sin cotizaciones"
              description="Crea tu primera cotización para activar el flujo comercial."
              action={
                <button className="view-switcher-active h-10 px-6 flex items-center gap-2" onClick={() => setView('create')}>
                  Crear primera cotizacion
                </button>
              }
            />
          ) : (
            <div className="ink-table-card">
              <table className="ink-table">
                <thead>
                  <tr>
                    <th className="ink-th">F. Emisión</th>
                    <th className="ink-th">N° Orden</th>
                    <th className="ink-th">Cliente</th>
                    <th className="ink-th text-center">M.</th>
                    <th className="ink-th text-right">Total</th>
                    <th className="ink-th text-right">Saldo</th>
                    <th className="ink-th">Pago</th>
                    <th className="ink-th">Comprobante</th>
                    <th className="ink-th text-right">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredHistory.map((item) => {
                    const hasLinked = !!item.linked_fiscal_document_number && item.linked_fiscal_document_status !== 'anulada';
                    const sym = item.moneda === 'USD' ? '$' : 'S/';
                    const linkedSunat = getLinkedSunatStatus(item);
                    const waLink = getWhatsAppLink(item.cliente, item);
                    const emailLink = getEmailLink(item.cliente, item);
                    const canDelete = !hasLinked && item.estado !== 'anulada';
                    return (
                      <tr key={item.id} className="ink-tr">
                        <td className="ink-td">
                          <span className="font-mono-label text-[10px] uppercase">
                            {item.fecha_emision ? new Date(item.fecha_emision).toLocaleDateString('es-PE') : '--'}
                          </span>
                        </td>
                        <td className="ink-td font-mono-label text-xs">
                          {item.internal_order_number || `#${item.id}`}
                        </td>
                        <td className="ink-td">
                          <div className="flex flex-col">
                            <span className="font-bold text-xs uppercase">{item.cliente?.razon_social || '--'}</span>
                            <span className="text-[10px] text-[var(--text-tertiary)]">{item.cliente?.numero_documento || ''}</span>
                          </div>
                        </td>
                        <td className="ink-td text-center font-mono-label text-[10px]">{sym}</td>
                        <td className="ink-td text-right font-bold font-mono-label text-xs">{sym} {fmt(item.total_venta)}</td>
                        <td className="ink-td text-right font-mono-label text-xs text-[var(--text-tertiary)]">
                          {sym} {fmt(item.saldo_pendiente)}
                        </td>
                        <td className="ink-td">
                          <Badge variant={statusBadge(item.payment_status)}>
                            {item.payment_status || 'pendiente'}
                          </Badge>
                        </td>
                        <td className="ink-td">
                          {hasLinked ? (
                            <div className="flex items-center gap-2 flex-wrap">
                              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: 700, color: 'var(--brand-600)' }}>
                                {item.linked_fiscal_document_number}
                              </span>
                              {linkedSunat && (
                                <span className={`history-sunat-pill history-sunat-pill--${linkedSunat.variant}`}>
                                  <linkedSunat.icon className="h-3 w-3" />
                                  {linkedSunat.label}
                                </span>
                              )}
                            </div>
                          ) : (
                            <span style={{ fontSize: '10px', color: 'var(--text-tertiary)' }}>Sin emitir</span>
                          )}
                        </td>
                        <td className="ink-td">
                          <div className="history-actions-desktop">
                            <div className="history-actions-cluster">
                              <Link
                                to={`/cotizaciones/${item.id}`}
                                className="row-action-icon row-action-icon--brand"
                                title="Ver detalle"
                              >
                                <Eye className="h-3 w-3" />
                              </Link>
                              <button
                                type="button"
                                title="Duplicar cotizacion"
                                className="row-action-icon row-action-icon--neutral"
                                onClick={() => handleDuplicateQuote(item)}
                              >
                                <Copy className="h-3 w-3" />
                              </button>
                              <button
                                type="button"
                                title="Descargar PDF"
                                className="row-action-icon row-action-icon--info"
                                onClick={() => handleOpenPdf(item)}
                              >
                                <Download className="h-3 w-3" />
                              </button>
                              <button
                                type="button"
                                title="Copiar enlace publico"
                                className="row-action-icon row-action-icon--info"
                                onClick={() => handleCopyShareLink(item)}
                              >
                                <Share2 className="h-3 w-3" />
                              </button>
                              {waLink && (
                                <a
                                  href={waLink}
                                  target="_blank"
                                  rel="noreferrer"
                                  title="Enviar por WhatsApp"
                                  className="row-action-icon row-action-icon--success"
                                >
                                  <MessageCircle className="h-3 w-3" />
                                </a>
                              )}
                              {emailLink && (
                                <a
                                  href={emailLink}
                                  title="Enviar por correo"
                                  className="row-action-icon row-action-icon--info"
                                >
                                  <Mail className="h-3 w-3" />
                                </a>
                              )}
                              {waLink && emailLink && (
                                <button
                                  type="button"
                                  title="WhatsApp + correo"
                                  className="row-action-icon row-action-icon--accent"
                                  onClick={() => {
                                    window.open(waLink, '_blank', 'noopener,noreferrer');
                                    window.setTimeout(() => window.open(emailLink, '_blank', 'noopener,noreferrer'), 80);
                                  }}
                                >
                                  <Send className="h-3 w-3" />
                                </button>
                              )}
                            </div>
                            <div className="history-actions-divider" />
                            <div className="history-actions-cluster">
                              {!hasLinked && (
                                <button
                                  type="button"
                                  title="Emitir factura o boleta"
                                  className="row-action-icon row-action-icon--accent"
                                  onClick={() => setEmitirDoc(item)}
                                >
                                  <Receipt className="h-3 w-3" />
                                </button>
                              )}
                              {canDelete && (
                                <button
                                  type="button"
                                  title="Eliminar cotizacion"
                                  className="row-action-icon row-action-icon--danger"
                                  onClick={() => handleDeleteQuote(item)}
                                >
                                  <Trash2 className="h-3 w-3" />
                                </button>
                              )}
                            </div>
                          </div>

                          <details className="history-actions-mobile">
                            <summary className="row-action-icon row-action-icon--neutral" title="Mas acciones">
                              <MoreHorizontal className="h-3 w-3" />
                            </summary>
                            <div className="history-actions-mobile-menu">
                              <Link to={`/cotizaciones/${item.id}`} className="history-actions-mobile-item">
                                <Eye className="h-3.5 w-3.5" />
                                Ver detalle
                              </Link>
                              <button type="button" className="history-actions-mobile-item" onClick={() => handleDuplicateQuote(item)}>
                                <Copy className="h-3.5 w-3.5" />
                                Duplicar
                              </button>
                              <button type="button" className="history-actions-mobile-item" onClick={() => handleOpenPdf(item)}>
                                <Download className="h-3.5 w-3.5" />
                                Descargar PDF
                              </button>
                              <button type="button" className="history-actions-mobile-item" onClick={() => handleCopyShareLink(item)}>
                                <Share2 className="h-3.5 w-3.5" />
                                Copiar enlace
                              </button>
                              {waLink && (
                                <a href={waLink} target="_blank" rel="noreferrer" className="history-actions-mobile-item">
                                  <MessageCircle className="h-3.5 w-3.5" />
                                  WhatsApp
                                </a>
                              )}
                              {emailLink && (
                                <a href={emailLink} className="history-actions-mobile-item">
                                  <Mail className="h-3.5 w-3.5" />
                                  Correo
                                </a>
                              )}
                              {waLink && emailLink && (
                                <button
                                  type="button"
                                  className="history-actions-mobile-item"
                                  onClick={() => {
                                    window.open(waLink, '_blank', 'noopener,noreferrer');
                                    window.setTimeout(() => window.open(emailLink, '_blank', 'noopener,noreferrer'), 80);
                                  }}
                                >
                                  <Send className="h-3.5 w-3.5" />
                                  WhatsApp + correo
                                </button>
                              )}
                              {!hasLinked && (
                                <button type="button" className="history-actions-mobile-item" onClick={() => setEmitirDoc(item)}>
                                  <Receipt className="h-3.5 w-3.5" />
                                  Emitir
                                </button>
                              )}
                              {canDelete && (
                                <button type="button" className="history-actions-mobile-item is-danger" onClick={() => handleDeleteQuote(item)}>
                                  <Trash2 className="h-3.5 w-3.5" />
                                  Eliminar
                                </button>
                              )}
                            </div>
                          </details>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {/* ── Vista: Emitidas SUNAT ── */}
      {view === 'fiscal' && (
        <>{/* Panel de filtros — siempre visible, 2 filas */}
          <div className="ink-card" style={{ padding: '16px 20px', marginBottom: '0', borderBottom: 'none' }}>
            {/* Fila 1 */}
            <div className="grid grid-cols-2 md:grid-cols-7 gap-3 mb-3">
              <div className="flex flex-col gap-1">
                <label className="label-xs">Doc. Receptor</label>
                <input className="input-compact" placeholder="DNI / RUC" value={filters.docReceptor}
                  onChange={(e) => handleFilterChange('docReceptor', e.target.value)} />
              </div>
              <div className="flex flex-col gap-1 md:col-span-2">
                <label className="label-xs">Razón Social / Nombre Receptor</label>
                <input className="input-compact" placeholder="Nombre del cliente" value={filters.razonSocial}
                  onChange={(e) => handleFilterChange('razonSocial', e.target.value)} />
              </div>
              <div className="flex flex-col gap-1">
                <label className="label-xs">Tipo</label>
                <CustomSelect compact value={filters.tipo} onChange={(v) => handleFilterChange('tipo', v)}
                  options={[
                    { value: 'all', label: 'Todos' },
                    { value: '01',  label: 'Factura' },
                    { value: '03',  label: 'Boleta' },
                    { value: '07',  label: 'Nota Crédito' },
                    { value: '08',  label: 'Nota Débito' },
                  ]}
                />
              </div>
              <div className="flex flex-col gap-1">
                <label className="label-xs">Serie</label>
                <input className="input-compact" placeholder="F001" value={filters.serie}
                  onChange={(e) => handleFilterChange('serie', e.target.value)} />
              </div>
              <div className="flex flex-col gap-1">
                <label className="label-xs">Emisión desde</label>
                <DatePicker compact value={filters.desde}
                  onChange={(v) => handleFilterChange('desde', v)} />
              </div>
              <div className="flex flex-col gap-1">
                <label className="label-xs">Hasta</label>
                <DatePicker compact value={filters.hasta}
                  onChange={(v) => handleFilterChange('hasta', v)} />
              </div>
            </div>
            {/* Fila 2 */}
            <div className="grid grid-cols-2 md:grid-cols-7 gap-3 items-end">
              <div className="flex flex-col gap-1">
                <label className="label-xs">N° Correlativo</label>
                <input className="input-compact" placeholder="000001" value={filters.numero}
                  onChange={(e) => handleFilterChange('numero', e.target.value)} />
              </div>
              <div className="flex flex-col gap-1">
                <label className="label-xs">Moneda</label>
                <CustomSelect compact value={filters.moneda} onChange={(v) => handleFilterChange('moneda', v)}
                  options={[
                    { value: 'all', label: 'Todas' },
                    { value: 'PEN', label: 'PEN (S/)' },
                    { value: 'USD', label: 'USD ($)' },
                  ]}
                />
              </div>
              <div className="flex flex-col gap-1">
                <label className="label-xs">Forma de Pago</label>
                <CustomSelect compact value={filters.formaPago} onChange={(v) => handleFilterChange('formaPago', v)}
                  options={[
                    { value: 'all',     label: 'TODOS' },
                    { value: 'contado', label: 'Contado' },
                    { value: 'credito', label: 'Crédito' },
                  ]}
                />
              </div>
              <div className="md:col-span-2" />
              <div className="md:col-span-2 flex justify-end items-end">
                <button
                  type="button"
                  onClick={() => setFilters({ tipo: 'all', docReceptor: '', razonSocial: '', serie: '', numero: '', moneda: 'all', formaPago: 'all', desde: '', hasta: '' })}
                  className="btn-ghost text-xs"
                  style={{ height: '36px' }}
                >
                  Limpiar filtros
                </button>
              </div>
            </div>
          </div>

          {/* Barra de resultados y acciones */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 20px', background: 'var(--bg-surface-2)', border: '1px solid var(--border-subtle)', borderTop: 'none', marginBottom: '0' }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: 700, color: 'var(--text-tertiary)' }}>
              Total registros: {filteredFiscal.length}
            </span>
            <div className="cotizacion-fiscal-toolbar">
              {!selectedFiscal ? (
                <span className="cotizacion-fiscal-placeholder">
                  Selecciona un comprobante para emitir nota o anular
                </span>
              ) : (
                <>
              <button
                className="btn-ghost text-[10px] font-bold uppercase tracking-wider px-3 py-1.5 flex items-center gap-2"
                disabled={!selectedFiscal || !['01','03'].includes(selectedFiscal?.tipo_comprobante) || selectedFiscal?.estado === 'anulada'}
                onClick={() => selectedFiscal && setNotaDoc(selectedFiscal)}
                style={{ color: selectedFiscal ? 'var(--color-warning)' : 'var(--border-subtle)', cursor: selectedFiscal ? 'pointer' : 'default' }}
              >
                Nota de Crédito
              </button>
              <button
                className="btn-ghost text-[10px] font-bold uppercase tracking-wider px-3 py-1.5 flex items-center gap-2"
                disabled={!selectedFiscal || !['01','03'].includes(selectedFiscal?.tipo_comprobante) || selectedFiscal?.estado === 'anulada'}
                onClick={() => selectedFiscal && setNotaDoc(selectedFiscal)}
                style={{ color: selectedFiscal ? 'var(--color-warning)' : 'var(--border-subtle)', cursor: selectedFiscal ? 'pointer' : 'default' }}
              >
                Nota de Débito
              </button>
              <div style={{ width: '1px', height: '16px', background: 'var(--border-subtle)' }} />
              <button
                className="btn-ghost text-[10px] font-bold uppercase tracking-wider px-3 py-1.5 flex items-center gap-2"
                disabled={!selectedFiscal || selectedFiscal?.estado === 'anulada'}
                onClick={() => selectedFiscal && setAnularDoc(selectedFiscal)}
                style={{ color: selectedFiscal ? 'var(--color-error)' : 'var(--border-subtle)', cursor: selectedFiscal ? 'pointer' : 'default' }}
              >
                Anular
              </button>
              <div style={{ width: '1px', height: '16px', background: 'var(--border-subtle)' }} />
              {/* Iconos de descarga rápida para el registro seleccionado */}
              <a
                href={selectedFiscal?.sunat_pdf_url || '#'}
                target={selectedFiscal?.sunat_pdf_url ? '_blank' : undefined}
                rel="noreferrer"
                title="PDF"
                style={{ opacity: selectedFiscal?.sunat_pdf_url ? 1 : 0.3, color: 'var(--color-error)', pointerEvents: selectedFiscal?.sunat_pdf_url ? 'auto' : 'none' }}
                className="row-action-icon row-action-icon--danger"
              >
                <FileText className="h-3 w-3" />
              </a>
              <a
                href={selectedFiscal?.sunat_xml_url || '#'}
                target={selectedFiscal?.sunat_xml_url ? '_blank' : undefined}
                rel="noreferrer"
                title="XML"
                style={{ opacity: selectedFiscal?.sunat_xml_url ? 1 : 0.3, color: 'var(--color-info)', pointerEvents: selectedFiscal?.sunat_xml_url ? 'auto' : 'none' }}
                className="row-action-icon row-action-icon--info"
              >
                <Download className="h-3 w-3" />
              </a>
                </>
              )}
            </div>
          </div>

          {loading ? (
            <div className="flex justify-center py-16"><Spinner size="lg" /></div>
          ) : filteredFiscal.length === 0 ? (
            <EmptyState
              title="Sin comprobantes emitidos"
              description="Emite tu primera factura o boleta desde la pestaña Historial."
            />
          ) : (
            <div className="ink-table-card">
              <table className="ink-table">
                <thead>
                  <tr>
                    <th className="ink-th">F. Emisión</th>
                    <th className="ink-th">Tipo</th>
                    <th className="ink-th">Serie-Núm</th>
                    <th className="ink-th">Cliente</th>
                    <th className="ink-th text-center">M.</th>
                    <th className="ink-th text-right">Base Grav.</th>
                    <th className="ink-th text-right">IGV</th>
                    <th className="ink-th text-right">Total</th>
                    <th className="ink-th">Estado SUNAT</th>
                    <th className="ink-th text-right">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredFiscal.map((item) => {
                    const sunatSt = getSunatStatus(item);
                    const sym = item.moneda === 'USD' ? '$' : 'S/';
                    const docNum = item.serie
                      ? `${item.serie}-${String(item.correlativo || 0).padStart(6, '0')}`
                      : `#${item.id}`;
                    const waLink = getWhatsAppLink(item.cliente, item);
                    const canAnular = item.estado !== 'anulada';
                    const canNota = ['01', '03'].includes(item.tipo_comprobante) && item.estado !== 'anulada';
                    const isSelected = selectedFiscal?.id === item.id;
                    return (
                      <tr
                        key={item.id}
                        className="ink-tr"
                        onClick={() => setSelectedFiscal(isSelected ? null : item)}
                        style={{ cursor: 'pointer', background: isSelected ? 'var(--ink-primary-fixed)' : undefined, boxShadow: isSelected ? 'inset 2px 0 0 var(--ink-primary)' : undefined }}
                      >
                        <td className="ink-td">
                          <span className="font-mono-label text-[10px] uppercase">
                            {item.fecha_emision ? new Date(item.fecha_emision).toLocaleDateString('es-PE') : '--'}
                          </span>
                        </td>
                        <td className="ink-td">
                          <Badge variant={docVariant(item.tipo_comprobante)}>
                            {docLabel(item.tipo_comprobante)}
                          </Badge>
                        </td>
                        <td className="ink-td font-mono-label text-xs">{docNum}</td>
                        <td className="ink-td">
                          <div className="flex flex-col">
                            <span className="font-bold text-xs uppercase">{item.cliente?.razon_social || '--'}</span>
                            <span className="text-[10px] text-[var(--text-tertiary)]">{item.cliente?.numero_documento || ''}</span>
                          </div>
                        </td>
                        <td className="ink-td text-center font-mono-label text-[10px]">{sym}</td>
                        <td className="ink-td text-right font-mono-label text-xs">
                          {sym} {fmt(item.total_gravada)}
                        </td>
                        <td className="ink-td text-right font-mono-label text-xs">
                          {sym} {fmt(item.total_igv)}
                        </td>
                        <td className="ink-td text-right font-bold font-mono-label text-xs">
                          {sym} {fmt(item.total_venta)}
                        </td>
                        <td className="ink-td">
                          {sunatSt ? (
                            <div
                              title={sunatSt.tooltip || ''}
                              style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '4px',
                                padding: '2px 8px',
                                fontSize: '9px',
                                fontWeight: 700,
                                fontFamily: 'var(--font-mono)',
                                textTransform: 'uppercase',
                                letterSpacing: '0.08em',
                                borderRadius: '2px',
                                ...(sunatSt.variant === 'success' ? { background: 'var(--color-success-bg)', color: 'var(--color-success)', border: '1px solid rgba(5,150,105,0.2)' }
                                  : sunatSt.variant === 'danger'  ? { background: 'var(--color-error-bg)', color: 'var(--color-error)', border: '1px solid rgba(220,38,38,0.2)' }
                                  : { background: 'var(--color-warning-bg)', color: 'var(--color-warning)', border: '1px solid rgba(217,119,6,0.2)' }),
                              }}
                            >
                              <sunatSt.icon style={{ width: '10px', height: '10px' }} />
                              {sunatSt.label}
                            </div>
                          ) : (
                            <span style={{ color: 'var(--text-tertiary)', fontSize: '11px' }}>—</span>
                          )}
                        </td>
                        <td className="ink-td">
                          <div className="flex justify-end items-center gap-1">
                            {item.sunat_pdf_url && (
                              <a href={item.sunat_pdf_url} target="_blank" rel="noreferrer"
                                title="Descargar PDF"
                                className="row-action-icon row-action-icon--danger">
                                <FileText className="h-3 w-3" />
                              </a>
                            )}
                            {item.sunat_xml_url && (
                              <a href={item.sunat_xml_url} target="_blank" rel="noreferrer"
                                title="Descargar XML"
                                className="row-action-icon row-action-icon--info">
                                <Download className="h-3 w-3" />
                              </a>
                            )}
                            {waLink && (
                              <a href={waLink} target="_blank" rel="noreferrer"
                                title="Enviar por WhatsApp"
                                className="row-action-icon row-action-icon--success">
                                <Send className="h-3 w-3" />
                              </a>
                            )}
                            {canNota && (
                              <button
                                title="Emitir nota de crédito/débito"
                                className="row-action-icon row-action-icon--warning"
                                onClick={() => setNotaDoc(item)}
                              >
                                <FileText className="h-3 w-3" />
                              </button>
                            )}
                            {canAnular && (
                              <button
                                title="Anular documento"
                                className="row-action-icon row-action-icon--danger"
                                onClick={() => setAnularDoc(item)}
                              >
                                <XCircle className="h-3 w-3" />
                              </button>
                            )}
                            <div className="history-actions-divider mx-1 h-4" />
                            <Link
                              to={`/cotizaciones/${item.id}`}
                              className="row-action-icon row-action-icon--brand"
                              title="Ver detalle"
                            >
                              <Eye className="h-3 w-3" />
                            </Link>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {/* ── Modales ── */}

      <Modal open={nuevoClienteOpen} onClose={() => { setNuevoClienteOpen(false); setNuevoClientePrefill(''); }} title="Nuevo cliente" size="md">
        <NuevoClienteModal
          onClose={() => { setNuevoClienteOpen(false); setNuevoClientePrefill(''); }}
          onCreated={handleNuevoCliente}
          initialName={nuevoClientePrefill}
        />
      </Modal>

      <Modal open={!!emitirDoc} onClose={() => setEmitirDoc(null)} title="Emitir comprobante fiscal" size="md">
        {emitirDoc && (
          <EmitirModal
            cotizacion={emitirDoc}
            onClose={() => setEmitirDoc(null)}
            onSuccess={handleEmitirSuccess}
          />
        )}
      </Modal>

      <Modal open={!!anularDoc} onClose={() => setAnularDoc(null)} title="Anular documento" size="md">
        {anularDoc && (
          <AnularModal
            documento={anularDoc}
            onClose={() => setAnularDoc(null)}
            onSuccess={handleAnularSuccess}
          />
        )}
      </Modal>

      <Modal open={!!notaDoc} onClose={() => setNotaDoc(null)} title="Emitir nota de crédito / débito" size="md">
        {notaDoc && (
          <NotaModal
            documento={notaDoc}
            onClose={() => setNotaDoc(null)}
            onSuccess={handleNotaSuccess}
          />
        )}
      </Modal>
    </div>
  );
}

// ─── Componente auxiliar: barra de búsqueda ───────────────────────────────────

function SearchBar({ search, onSearch, showFilters, onToggleFilters, onNewAction, newLabel }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: '8px', background: 'var(--bg-surface-2)', border: '1px solid var(--border-subtle)', padding: '0 14px', height: '40px' }}>
        <Search className="h-4 w-4 text-[var(--text-tertiary)]" style={{ flexShrink: 0 }} />
        <input
          className="input-flat"
          style={{ flex: 1, background: 'transparent' }}
          placeholder="Buscar por cliente, número u orden..."
          value={search}
          onChange={(e) => onSearch(e.target.value)}
        />
      </div>
      <button
        onClick={onToggleFilters}
        className="btn-secondary"
        style={{ display: 'flex', alignItems: 'center', gap: '6px', height: '40px', whiteSpace: 'nowrap' }}
      >
        <SlidersHorizontal className="h-3.5 w-3.5" />
        {showFilters ? 'Ocultar filtros' : 'Filtros'}
      </button>
      {onNewAction && (
        <button
          onClick={onNewAction}
          className="btn-primary"
          style={{ height: '40px', whiteSpace: 'nowrap' }}
        >
          {newLabel}
        </button>
      )}
    </div>
  );
}
