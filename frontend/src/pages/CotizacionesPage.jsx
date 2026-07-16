import { useEffect, useState, useCallback, useMemo } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import {
  Eye, Search, Trash2, Send, FileText,
  Download, CheckCircle2, Clock, AlertCircle, XCircle,
  Receipt, SlidersHorizontal, Save,
  History, Copy, Share2, MessageCircle, Mail, MoreHorizontal, PencilLine,
} from 'lucide-react';
import { cotizaciones as svc } from '../services/cotizaciones';
import { clientes as cliSvc } from '../services/clientes';
import { productos as prodSvc } from '../services/productos';
import { tenant as tenantSvc } from '../services/tenant';
import Spinner from '../components/ui/Spinner';
import { SkeletonForm } from '../components/ui/Skeleton';
import ColorPickerField from '../components/ui/ColorPickerField';
import EmptyState from '../components/ui/EmptyState';
import Badge, { statusBadge } from '../components/ui/Badge';
import Modal from '../components/ui/Modal';
import Pagination from '../components/ui/Pagination';
import CustomSelect from '../components/ui/CustomSelect';
import DatePicker from '../components/ui/DatePicker';
import ClientCombobox from '../components/ui/ClientCombobox';
import ProductLineCell from '../components/ui/ProductLineCell';
import SectionNavigation from '../components/ui/SectionNavigation';
import { FieldError } from '../components/ui/FieldError';
import { useToast } from '../components/ui/Toast';
import '../styles/cotizacionesHistory.css';
import OperationalPageHeader from '../components/ui/OperationalPageHeader';
import {
  getDefaultQuoteBankMethods,
  getPaymentMethodPreview,
  getPaymentQrImageUrl,
  getQuoteBankMethodSignature,
  getQuoteBankMethods,
  serializeQuoteBankMethods,
  getTransferPaymentMethodPreviews,
  getWalletOptions,
  normalizePaymentMethods,
  resolveSelectedWallet,
} from '../lib/utils/paymentMethods';
import { BASE_URL } from '../lib/utils/config';
import { api } from '../lib/utils/api';
import { normalizePeruMobileInput, validatePeruMobilePhone } from '../lib/utils/peruPhoneValidation';
import { normalizeUppercaseFieldValue } from '../lib/utils/uppercase';
import {
  getLookupAddress,
  getLookupCommercialName,
  getLookupDocumentType,
  getLookupName,
  getLookupUbigeo,
} from '../lib/utils/documentLookup';
import {
  FISCAL_DOC_TYPE_OPTIONS,
  buildFiscalClientErrors,
  getFiscalDocLabel,
  getFiscalDocMeta,
  normalizeFiscalClientForm,
  normalizeFiscalDocumentNumber,
  normalizeFiscalUbigeo,
} from '../lib/utils/fiscalClientValidation';
import {
  DEFAULT_NOTE_1_COLOR,
  DEFAULT_NOTE_1_TEXT,
  DEFAULT_NOTE_2_COLOR,
  DEFAULT_NOTE_2_TEXT,
  parseTenantObservationDefaults,
} from '../lib/utils/pdfObservationDefaults';
import {
  SUNAT_TAX_AFFECTATION_OPTIONS,
  SUNAT_UNIT_OPTIONS,
  normalizeInternalProductCode,
} from '../lib/utils/sunatCatalogs';
import { hasCatalogProductOverrides } from '../lib/utils/productCatalogSync';
import { clienteSnapshotFromForm, syncCatalogProductos, upsertCliente, upsertProductos } from '../lib/utils/upsert';
import { useAuth } from '../context/AuthContext';

// ─── Constantes de dominio ────────────────────────────────────────────────────

const UNIDADES_MEDIDA = SUNAT_UNIT_OPTIONS;
const HISTORY_PAGE_SIZE = 15;

const AFECTACION_IGV = SUNAT_TAX_AFFECTATION_OPTIONS;

const CONDICIONES_PAGO = [
  { value: 'contado',    label: 'Contado' },
  { value: 'credito_7',  label: 'Crédito 7 días' },
  { value: 'credito_15', label: 'Crédito 15 días' },
  { value: 'credito_30', label: 'Crédito 30 días' },
  { value: 'credito_60', label: 'Crédito 60 días' },
];

const DEFAULT_QUOTE_PAYMENT_CONDITION = 'credito_15';

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

function getQuoteBankKeys(methods = []) {
  return getQuoteBankMethods(methods)
    .map((method) => getQuoteBankMethodSignature(method))
    .filter(Boolean);
}

function mergeQuoteBankMethods(...groups) {
  const unique = new Map();
  groups.flat().forEach((method) => {
    const key = getQuoteBankMethodSignature(method);
    if (!key || unique.has(key)) return;
    unique.set(key, method);
  });
  return Array.from(unique.values());
}

function getSunatStatus(item) {
  if (item.estado === 'anulada')    return { label: 'ANULADO',  variant: 'danger',  icon: XCircle };
  if (item.sunat_error)            return { label: 'RECHAZADO', variant: 'danger',  icon: AlertCircle, tooltip: item.sunat_error };
  if (item.sunat_xml_url)          return { label: 'ACEPTADO',  variant: 'success', icon: CheckCircle2 };
  if (item.document_kind !== 'quotation') return { label: 'PENDIENTE', variant: 'warning', icon: Clock };
  return null;
}

function getDocumentDisplayNumber(doc) {
  if (!doc) return '--';
  if (doc.document_number) return doc.document_number;
  if (doc.serie) {
    return `${doc.serie}-${String(doc.correlativo || 0).padStart(6, '0')}`;
  }
  if (doc.correlativo !== undefined && doc.correlativo !== null) {
    return `COT-${String(doc.correlativo).padStart(6, '0')}`;
  }
  return doc.internal_order_number || `#${doc.id}`;
}

function getPaymentStatusLabel(status) {
  const value = String(status || 'pendiente').trim();
  const normalized = value.toLowerCase();
  const labels = {
    pendiente: 'Pendiente',
    pagado: 'Pagado',
    parcial: 'Parcial',
    vencido: 'Vencido',
    anulada: 'Anulado',
  };
  if (labels[normalized]) return labels[normalized];
  return value
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
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
  const docNum = getDocumentDisplayNumber(doc);
  const sym = doc.moneda === 'USD' ? '$' : 'S/';
  const shareUrl = getPublicShareUrl(doc);
  const msg = [
    `Hola, le compartimos la cotizacion ${docNum} por ${sym} ${Number(doc.total_venta || 0).toFixed(2)}.`,
    shareUrl ? `Puede descargar el documento aqui: ${shareUrl}` : '',
  ].filter(Boolean).join('\n\n');
  return `https://wa.me/${number}?text=${encodeURIComponent(msg)}`;
}

function getPublicShareUrl(doc) {
  if (!doc?.uuid_publico) return null;
  return `${BASE_URL}/public/cotizaciones/${doc.uuid_publico}/pdf`;
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
    return { label: 'Anulado', variant: 'danger', icon: XCircle };
  }
  if (item.linked_fiscal_document_status === 'facturada') {
    return { label: 'Aceptado', variant: 'success', icon: CheckCircle2 };
  }
  return { label: 'Pendiente', variant: 'warning', icon: Clock };
}

function docLabel(tipo) {
  const m = { '01': 'FACTURA', '03': 'BOLETA', '07': 'NC', '08': 'ND', '00': 'COT.' };
  return m[tipo] || tipo;
}

function docVariant(tipo) {
  const m = { '01': 'brand', '03': 'info', '07': 'warning', '08': 'warning', '00': 'default' };
  return m[tipo] || 'default';
}

function fiscalTone(item) {
  const status = getSunatStatus(item);
  if (!status) return 'neutral';
  if (status.variant === 'success') return 'ok';
  if (status.variant === 'danger') return 'bad';
  if (status.variant === 'warning') return 'warn';
  return 'neutral';
}

const fmt = (v) => Number(v || 0).toLocaleString('es-PE', { minimumFractionDigits: 2 });

function toDateInputValue(value) {
  if (!value) return '';
  const raw = String(value);
  const match = raw.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (match) return `${match[1]}-${match[2]}-${match[3]}`;
  const parsed = new Date(raw);
  if (Number.isNaN(parsed.getTime())) return '';
  const month = String(parsed.getMonth() + 1).padStart(2, '0');
  const day = String(parsed.getDate()).padStart(2, '0');
  return `${parsed.getFullYear()}-${month}-${day}`;
}

function canEditCommercialQuote(item) {
  if (!item || item.document_kind !== 'quotation') return false;
  if (item.estado !== 'pendiente') return false;
  if (item.linked_fiscal_document_id || item.linked_fiscal_document_number) return false;
  return Number(item.monto_pagado || 0) <= 0;
}

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

function getTipoDocumentoClienteLabel(value, numeroDocumento = '') {
  const digits = String(numeroDocumento || '').replace(/\D/g, '');
  if (value === '6' || digits.length === 11) return 'RUC';
  return 'DNI';
}

function getFiscalCustomerDocKind(cliente) {
  const docType = String(cliente?.tipo_documento || '').trim();
  const docNumber = String(cliente?.numero_documento || '').replace(/\D/g, '');
  const isRuc = docType === '6' && docNumber.length === 11;
  const isDni = docType === '1' && docNumber.length === 8;

  if (isRuc) return 'ruc';
  if (isDni) return 'dni';
  return 'other';
}

function getRecommendedFiscalReceiptType(cliente) {
  return getFiscalCustomerDocKind(cliente) === 'dni' ? '03' : '01';
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
    ubigeo: (clienteForm?.ubigeo || selectedClient?.ubigeo || '').trim(),
  };
}

function CotizacionPreviewSheet({
  tenantData,
  user,
  cliente,
  moneda,
  condicion,
  items,
  observationLines,
  quotePaymentMethods,
  subtotalGravado,
  igv,
  totalGeneral,
  selectedWalletId,
}) {
  const accentColor = tenantData?.primary_color || 'var(--brand-600)';
  const companyName = tenantData?.business_name || user?.tenant?.business_name || 'Nombre del negocio';
  const companyRuc = tenantData?.business_ruc || user?.tenant?.business_ruc || '';
  const companyAddress = tenantData?.business_address || 'Direccion no especificada';
  const companyPhone = tenantData?.business_phone || '';
  const companyEmail = user?.business_email || user?.email || '';
  const paymentQrUrl = getPaymentQrImageUrl(tenantData);
  const paymentMethods = normalizePaymentMethods(tenantData?.bank_accounts);
  const transferSourceMethods = Array.isArray(quotePaymentMethods)
    ? quotePaymentMethods
    : getDefaultQuoteBankMethods(tenantData?.bank_accounts);
  const transferPaymentMethods = getTransferPaymentMethodPreviews(transferSourceMethods, { excludeWallets: true });
  const selectedWallet = resolveSelectedWallet(
    paymentMethods,
    selectedWalletId,
    tenantData?.quote_default_wallet_id,
  );
  const validItems = items
    .filter((item) => item.descripcion?.trim() && Number(item.cantidad) > 0 && Number(item.precio_unitario) > 0)
    .map((item) => {
      const quantity = Number(item.cantidad) || 0;
      const unitPrice = Number(item.precio_unitario) || 0;
      const lineTotal = quantity * unitPrice;
      const itemIgv = item.tipo_afectacion_igv === '10' ? (lineTotal * 0.18) / 1.18 : 0;
      const subtotal = lineTotal - itemIgv;
      return {
        codigo: item.codigo || item.codigo_producto || '',
        descripcion: item.descripcion.trim(),
        cantidad: quantity,
        unidad: item.unidad_medida === 'NIU' ? 'UND' : (item.unidad_medida || 'UND'),
        valor_unitario: quantity > 0 ? subtotal / quantity : 0,
        precio_unitario: unitPrice,
        igv: itemIgv,
        subtotal,
        total: lineTotal,
      };
    });
  const displayItems = validItems.length > 0 ? validItems : [{
    codigo: '',
    descripcion: 'Sin items agregados',
    cantidad: 0,
    unidad: 'UND',
    valor_unitario: 0,
    precio_unitario: 0,
    igv: 0,
    subtotal: 0,
    total: 0,
  }];
  const todayLabel = formatPreviewDate(new Date(), '');
  const amountInWords = amountToWords(totalGeneral, moneda);
  const displayObservationLines = (observationLines || []).filter((line) => line?.text?.trim());
  const currencySymbol = moneda === 'USD' ? '$' : 'S/';
  const formatPreviewMoney = (value) => Number(value || 0).toLocaleString('es-PE', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  return (
    <div className="document-preview-canvas">
      <div className="cotizacion-preview-sheet" style={{ '--quote-preview-accent': accentColor }}>
        <div className="cotizacion-preview-header">
          <div className="cotizacion-preview-logo-block">
            {tenantData?.logo_filename ? (
              <img className="cotizacion-preview-logo-img" src={tenantData.logo_filename} alt={`Logo ${companyName}`} />
            ) : (
              <div className="cotizacion-preview-logo-fallback">{companyName}</div>
            )}
          </div>

          <div className="cotizacion-preview-company">
            <div className="cotizacion-preview-company-name">{companyName.toUpperCase()}</div>
            {companyRuc && <div className="cotizacion-preview-company-meta">RUC {companyRuc}</div>}
            <div className="cotizacion-preview-company-meta">{companyAddress}</div>
            {companyEmail && <div className="cotizacion-preview-company-meta">{companyEmail}</div>}
            {companyPhone && <div className="cotizacion-preview-company-meta">{companyPhone}</div>}
          </div>

          <div className="cotizacion-preview-docbox">
            <div className="cotizacion-preview-docbox-title">COTIZACIÓN</div>
            <div className="cotizacion-preview-docbox-number">COT-000001</div>
            {companyRuc && <div className="cotizacion-preview-docbox-ruc">RUC: {companyRuc}</div>}
          </div>
        </div>

        <div className="cotizacion-preview-section-line" />

        <div className="cotizacion-preview-client">
          <div className="cotizacion-preview-client-grid">
            <div className="cotizacion-preview-client-label">Señores:</div>
            <div className="cotizacion-preview-client-value">{cliente.razon_social}</div>
            <div className="cotizacion-preview-client-label">Emisión:</div>
            <div className="cotizacion-preview-client-value">{todayLabel}</div>

            <div className="cotizacion-preview-client-label">{getTipoDocumentoClienteLabel(cliente.tipo_documento, cliente.numero_documento)}:</div>
            <div className="cotizacion-preview-client-value">{cliente.numero_documento || '-'}</div>
            <div className="cotizacion-preview-client-label">Moneda:</div>
            <div className="cotizacion-preview-client-value">{getMonedaTexto(moneda)}</div>

            <div className="cotizacion-preview-client-label">Dirección:</div>
            <div className="cotizacion-preview-client-value">{cliente.direccion || '-'}</div>
          </div>
        </div>

        <div className="cotizacion-preview-section-line" />

        <div className="cotizacion-preview-table-wrap">
          <table className="cotizacion-preview-table">
            <thead>
              <tr>
                <th>N°</th>
                <th>Cantidad</th>
                <th>Código</th>
                <th>Descripción</th>
                <th>V/U</th>
                <th>P/U</th>
                <th>Subtotal</th>
                <th>Total</th>
              </tr>
            </thead>
            <tbody>
              {displayItems.map((item, index) => (
                <tr key={`${item.descripcion}-${index}`}>
                  <td>{index + 1}</td>
                  <td>{`${formatPreviewQuantity(item.cantidad)} ${item.unidad}`}</td>
                  <td>{item.codigo || `ITEM-${String(index + 1).padStart(3, '0')}`}</td>
                  <td>{item.descripcion}</td>
                  <td>{`${currencySymbol} ${formatPreviewMoney(item.valor_unitario)}`}</td>
                  <td>{`${currencySymbol} ${formatPreviewMoney(item.precio_unitario)}`}</td>
                  <td>{`${currencySymbol} ${formatPreviewMoney(item.subtotal)}`}</td>
                  <td>{`${currencySymbol} ${formatPreviewMoney(item.total)}`}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="cotizacion-preview-totals">
          <div className="cotizacion-preview-total-row">
            <span>OP. GRAVADAS:</span>
            <span>{`${currencySymbol} ${formatPreviewMoney(subtotalGravado)}`}</span>
          </div>
          <div className="cotizacion-preview-total-row">
            <span>IGV (18%):</span>
            <span>{`${currencySymbol} ${formatPreviewMoney(igv)}`}</span>
          </div>
          <div className="cotizacion-preview-total-row is-strong">
            <span>IMPORTE TOTAL:</span>
            <span>{`${currencySymbol} ${formatPreviewMoney(totalGeneral)}`}</span>
          </div>
        </div>

        <div className="cotizacion-preview-amount">
          <div className="cotizacion-preview-amount-line">{amountInWords}</div>
        </div>

        <div className="cotizacion-preview-footer">
          <div className="cotizacion-preview-qr-frame">
            {paymentQrUrl ? (
              <img src={paymentQrUrl} alt={`QR de cobro ${companyName}`} />
            ) : (
              <span>QR DE COBRO</span>
            )}
          </div>

          <div className="cotizacion-preview-footer-divider" />

          <div className="cotizacion-preview-footer-copy">
            <strong>Escanea para pagar esta cotización.</strong>
            <p>QR compatible con la billetera digital configurada por la empresa.</p>
            <p><span>Condición de pago:</span> {getCondicionPagoLabel(condicion)}</p>

            {selectedWallet && (
              <div className="cotizacion-preview-bank">
                <div className="cotizacion-preview-bank-title">
                  QR de cobro: {selectedWallet.proveedor || 'Billetera digital'}
                </div>
                {selectedWallet.titular && (
                  <div className="cotizacion-preview-bank-line">Titular: {selectedWallet.titular}</div>
                )}
                {selectedWallet.numero && (
                  <div className="cotizacion-preview-bank-line">Numero: {selectedWallet.numero}</div>
                )}
                {selectedWallet.nota && (
                  <div className="cotizacion-preview-bank-line">{selectedWallet.nota}</div>
                )}
              </div>
            )}

            {displayObservationLines.map((line, index) => (
              <p
                key={`preview-note-${index}`}
                className={`cotizacion-preview-note ${line.bold ? 'cotizacion-preview-note--primary' : ''}`}
                style={{ color: line.color }}
              >
                {line.text}
              </p>
            ))}

            {transferPaymentMethods.length > 0 && (
              <div className="cotizacion-preview-bank">
                <div className="cotizacion-preview-bank-title">Datos para la transferencia</div>
                <div className="cotizacion-preview-bank-line">
                  Beneficiario: {companyName.toUpperCase()}
                </div>
                {transferPaymentMethods.map((preview, index) => {
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

        <div className="cotizacion-preview-bottom">
          <span>Documento comercial sin valor fiscal.</span>
          <span>{companyEmail || companyPhone || companyName}</span>
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
  const [errors, setErrors] = useState({});
  const [form, setForm] = useState(() => normalizeFiscalClientForm({
    tipo_documento: '6',
    razon_social: initialName,
  }));
  const set = (key) => (valueOrEvent) => {
    const rawValue = typeof valueOrEvent === 'string' ? valueOrEvent : valueOrEvent.target.value;
    const nextValue = key === 'telefono'
      ? normalizePeruMobileInput(rawValue)
      : key === 'numero_documento'
        ? normalizeFiscalDocumentNumber(form.tipo_documento, rawValue)
        : key === 'ubigeo'
          ? normalizeFiscalUbigeo(rawValue)
          : normalizeUppercaseFieldValue(key, rawValue);
    const nextForm = { ...form, [key]: nextValue };
    if (key === 'tipo_documento') {
      nextForm.numero_documento = normalizeFiscalDocumentNumber(nextValue, form.numero_documento);
    }
    setForm(nextForm);
    setErrors((current) => ({
      ...current,
      [key]: undefined,
      ...(key === 'tipo_documento'
        ? { numero_documento: undefined, direccion: undefined, ubigeo: undefined }
        : {}),
    }));
  };

  useEffect(() => {
    setForm(normalizeFiscalClientForm({
      tipo_documento: '6',
      razon_social: initialName,
    }));
    setErrors({});
  }, [initialName]);

  const validateForm = (nextForm = form) => {
    const nextErrors = buildFiscalClientErrors(nextForm);
    setErrors(nextErrors);
    return Object.values(nextErrors).every((value) => !value);
  };

  const handleLookup = async () => {
    if (!form.numero_documento) {
      validateForm({ ...form, numero_documento: '' });
      return;
    }
    setLookup(true);
    try {
      const data = await cliSvc.lookupDocument(form.numero_documento);
      const resolvedName = getLookupName(data);
      const nextForm = {
        ...form,
        tipo_documento: getLookupDocumentType(data, form.tipo_documento),
        razon_social: resolvedName || form.razon_social,
        nombre_comercial: getLookupCommercialName(data) || form.nombre_comercial,
        direccion: getLookupAddress(data) || form.direccion,
        ubigeo: normalizeFiscalUbigeo(getLookupUbigeo(data) || form.ubigeo),
      };
      setForm(nextForm);
      validateForm(nextForm);
    } catch {
      toast('No se encontró el documento en SUNAT/RENIEC', 'error');
    } finally {
      setLookup(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validateForm()) return;
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
            options={FISCAL_DOC_TYPE_OPTIONS}
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
              onBlur={() => validateForm()}
              placeholder={getFiscalDocMeta(form.tipo_documento).placeholder}
              inputMode={getFiscalDocMeta(form.tipo_documento).inputMode}
              maxLength={getFiscalDocMeta(form.tipo_documento).maxLength}
            />
            <button
              type="button"
              onClick={handleLookup}
              disabled={lookup || !getFiscalDocMeta(form.tipo_documento).lookupEnabled}
              className="btn-secondary"
              style={{ whiteSpace: 'nowrap', padding: '0 12px' }}
            >
              {lookup ? <Spinner size="sm" /> : 'Consultar'}
            </button>
          </div>
          <FieldError message={errors.numero_documento} />
        </div>
      </div>
      <div>
        <label className="label">Razón social / Nombre</label>
        <input required className="input" value={form.razon_social} onChange={set('razon_social')} onBlur={() => validateForm()} />
        <FieldError message={errors.razon_social} />
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <label className="label">Teléfono / WhatsApp</label>
          <input className="input" value={form.telefono} onChange={set('telefono')} onBlur={() => validateForm()} inputMode="numeric" placeholder="999999999" />
          <FieldError message={errors.telefono} />
        </div>
        <div>
          <label className="label">Email</label>
          <input className="input" type="email" value={form.email} onChange={set('email')} onBlur={() => validateForm()} />
          <FieldError message={errors.email} />
        </div>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <label className="label">Dirección fiscal</label>
          <input className="input" value={form.direccion} onChange={set('direccion')} onBlur={() => validateForm()} />
          <FieldError message={errors.direccion} />
        </div>
        <div>
          <label className="label">Ubigeo</label>
          <input className="input" value={form.ubigeo} onChange={set('ubigeo')} onBlur={() => validateForm()} inputMode="numeric" maxLength={6} placeholder="150101" />
          <FieldError message={errors.ubigeo} />
        </div>
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
  const [tipo, setTipo] = useState(() => getRecommendedFiscalReceiptType(cotizacion?.cliente));

  const cliente = cotizacion?.cliente;
  const tipoDocCliente = cliente?.tipo_documento;
  const fiscalDocKind = getFiscalCustomerDocKind(cliente);
  const esRUC = fiscalDocKind === 'ruc';
  const esDNI = fiscalDocKind === 'dni';

  const facturaInvalida = tipo === '01' && !esRUC;
  const boletaInvalida = tipo === '03' && !esDNI;
  const comprobanteInvalido = facturaInvalida || boletaInvalida;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (comprobanteInvalido) return;
    setSaving(true);
    try {
      await svc.facturar(cotizacion.id, {
        tipo_comprobante: tipo,
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
          Doc. cliente: {cliente?.numero_documento} ({tipoDocCliente === '6' ? 'RUC' : tipoDocCliente === '1' ? 'DNI' : tipoDocCliente || 'sin tipo'})
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
      {boletaInvalida && (
        <div style={{ padding: '10px 14px', background: 'var(--color-error-bg)', border: '1px solid rgba(220,38,38,0.2)', color: 'var(--color-error)', fontSize: '13px' }}>
          Para emitir boleta en beta, el cliente debe tener DNI (8 digitos). Si el cliente tiene RUC 10/20,
          corresponde emitir Factura.
        </div>
      )}

      <div className="flex justify-end gap-3">
        <button type="button" onClick={onClose} className="btn-secondary">Cancelar</button>
        <button
          type="submit"
          disabled={saving || comprobanteInvalido}
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
  onCancelEdit,
  onClientePersisted,
  saving,
  clientes,
  productosDisp,
  onNuevoCliente,
  quoteCountByClient = {},
  recentClientIds = [],
  createdClient,
  initialQuote = null,
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
    _syncCatalogChanges: false,
    _catalogSnapshot: null,
  });

  const [clienteId, setClienteId]       = useState('');
  const [clienteForm, setClienteForm]   = useState(null);  // current form values from ClientCombobox
  const [clienteDirty, setClienteDirty] = useState(false); // existing client edited
  const [clienteIsNew, setClienteIsNew] = useState(false);
  const [updateExistingClient, setUpdateExistingClient] = useState(true);
  const [moneda, setMoneda]             = useState('PEN');
  const [condicion, setCondicion]       = useState(DEFAULT_QUOTE_PAYMENT_CONDITION);
  const [fechaVenc, setFechaVenc]       = useState(() => calcFechaVencimiento(DEFAULT_QUOTE_PAYMENT_CONDITION));
  const [observationLines, setObservationLines] = useState(buildDefaultObservationLines());
  const [observacionesOpen, setObservacionesOpen] = useState(false);
  const [avanzado, setAvanzado]         = useState(false);
  const [items, setItems]               = useState([emptyItem()]);
  const [previewOpen, setPreviewOpen]   = useState(false);
  const [tenantData, setTenantData]     = useState(null);
  const [observationsInitialized, setObservationsInitialized] = useState(false);
  const [quoteBankSelectionMode, setQuoteBankSelectionMode] = useState('global');
  const [selectedQuoteBankKeys, setSelectedQuoteBankKeys] = useState([]);
  const isEditing = Boolean(initialQuote?.id);
  const editDisplayNumber = initialQuote ? getDocumentDisplayNumber(initialQuote) : '';
  const availableQuoteBankMethods = useMemo(() => mergeQuoteBankMethods(
    getQuoteBankMethods(tenantData?.bank_accounts),
    getQuoteBankMethods(initialQuote?.quote_payment_methods),
  ), [initialQuote?.quote_payment_methods, tenantData?.bank_accounts]);
  const defaultQuoteBankMethods = useMemo(
    () => getDefaultQuoteBankMethods(tenantData?.bank_accounts),
    [tenantData?.bank_accounts],
  );
  const defaultQuoteBankKeys = useMemo(
    () => getQuoteBankKeys(defaultQuoteBankMethods),
    [defaultQuoteBankMethods],
  );
  const selectedQuoteBankKeySet = useMemo(
    () => new Set(selectedQuoteBankKeys),
    [selectedQuoteBankKeys],
  );
  const effectiveQuoteBankMethods = useMemo(() => {
    if (quoteBankSelectionMode === 'global') return defaultQuoteBankMethods;
    return availableQuoteBankMethods.filter((method) => (
      selectedQuoteBankKeySet.has(getQuoteBankMethodSignature(method))
    ));
  }, [
    availableQuoteBankMethods,
    defaultQuoteBankMethods,
    quoteBankSelectionMode,
    selectedQuoteBankKeySet,
  ]);
  const formClientes = useMemo(() => (
    initialQuote?.cliente
      ? [
        initialQuote.cliente,
        ...clientes.filter((client) => String(client.id) !== String(initialQuote.cliente.id)),
      ]
      : clientes
  ), [clientes, initialQuote?.cliente]);
  const [quoteWalletId, setQuoteWalletId] = useState('');

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
        setQuoteWalletId('');
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
    if (!isEditing && createdClient?.id) {
      setClienteId(String(createdClient.id));
    }
  }, [createdClient, isEditing]);

  useEffect(() => {
    const cli = formClientes.find((c) => String(c.id) === String(clienteId));
    if (cli?.condicion_pago) {
      setCondicion(cli.condicion_pago);
    }
  }, [clienteId, formClientes]);

  useEffect(() => {
    setUpdateExistingClient(true);
  }, [clienteId]);

  useEffect(() => {
    if (!isEditing) return;

    const nextClient = initialQuote?.cliente_snapshot
      ? {
          ...(initialQuote?.cliente || {}),
          ...initialQuote.cliente_snapshot,
          id: initialQuote?.cliente?.id || initialQuote.cliente_snapshot.id,
        }
      : initialQuote?.cliente || null;
    const nextItems = (initialQuote?.items?.length ? initialQuote.items : []).map((item) => ({
      producto_id: item.producto_id ? String(item.producto_id) : '',
      codigo: item.codigo_producto || '',
      descripcion: item.descripcion || '',
      cantidad: item.cantidad || 1,
      precio_unitario: item.precio_unitario || '',
      unidad_medida: item.unidad_medida || 'NIU',
      tipo_afectacion_igv: item.tipo_afectacion_igv || '10',
      _isNew: false,
      _syncCatalogChanges: false,
    }));

    setClienteId(nextClient?.id ? String(nextClient.id) : String(initialQuote?.cliente_id || ''));
    setClienteForm(nextClient ? normalizeFiscalClientForm(nextClient) : null);
    setClienteDirty(false);
    setClienteIsNew(false);
    setUpdateExistingClient(true);
    setMoneda(initialQuote?.moneda || 'PEN');
    setCondicion(initialQuote?.condicion_pago || 'contado');
    setFechaVenc(toDateInputValue(initialQuote?.fecha_vencimiento));
    setQuoteWalletId(String(initialQuote?.quote_selected_wallet_id || ''));
    setObservationLines(parseObservationValue(initialQuote?.observaciones, tenantData));
    setObservacionesOpen(Boolean(initialQuote?.observaciones));
    if (Array.isArray(initialQuote?.quote_payment_methods)) {
      setQuoteBankSelectionMode('custom');
      setSelectedQuoteBankKeys(getQuoteBankKeys(initialQuote.quote_payment_methods));
    } else {
      setQuoteBankSelectionMode('global');
      setSelectedQuoteBankKeys(defaultQuoteBankKeys);
    }
    setItems(nextItems.length ? nextItems : [emptyItem()]);
  }, [defaultQuoteBankKeys, initialQuote, isEditing, tenantData]);

  useEffect(() => {
    if (isEditing || !tenantData) return;
    setQuoteBankSelectionMode('global');
    setSelectedQuoteBankKeys(defaultQuoteBankKeys);
  }, [defaultQuoteBankKeys, isEditing, tenantData]);

  // Auto-calc fecha vencimiento según condición
  useEffect(() => {
    if (isEditing && initialQuote?.fecha_vencimiento) return;
    if (condicion === 'contado') {
      setFechaVenc('');
      return;
    }
    setFechaVenc(calcFechaVencimiento(condicion));
  }, [condicion, initialQuote?.fecha_vencimiento, isEditing]);

  useEffect(() => {
    const walletOptions = getWalletOptions(tenantData?.bank_accounts);
    if (!quoteWalletId) return;
    if (!walletOptions.some((option) => option.value === quoteWalletId)) {
      setQuoteWalletId('');
    }
  }, [quoteWalletId, tenantData]);

  const addItem    = () => setItems((cur) => [...cur, emptyItem()]);
  const removeItem = (idx) => setItems((cur) => cur.filter((_, i) => i !== idx));
  const setItemAll = (idx, next) =>
    setItems((cur) => cur.map((it, i) => (i === idx ? { ...it, ...next } : it)));
  const setItem    = (idx, key, val) =>
    setItems((cur) => cur.map((it, i) => (i === idx ? { ...it, [key]: val } : it)));
  const catalogSyncEligibleCount = useMemo(
    () => items.filter((item) => hasCatalogProductOverrides(item)).length,
    [items],
  );
  const catalogSyncSelectedCount = useMemo(
    () => items.filter((item) => hasCatalogProductOverrides(item) && item._syncCatalogChanges).length,
    [items],
  );
  const syncCatalogOnSave = catalogSyncEligibleCount > 0 && catalogSyncSelectedCount === catalogSyncEligibleCount;
  const toggleCatalogSyncForEligible = () =>
    setItems((current) => {
      const eligible = current.filter((item) => hasCatalogProductOverrides(item));
      const nextValue = !(eligible.length > 0 && eligible.every((item) => item._syncCatalogChanges));
      return current.map((item) => (
        hasCatalogProductOverrides(item)
          ? { ...item, _syncCatalogChanges: nextValue }
          : item
      ));
    });

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

  const handleQuoteBankModeChange = (mode) => {
    if (mode === 'custom' && selectedQuoteBankKeys.length === 0) {
      setSelectedQuoteBankKeys(defaultQuoteBankKeys);
    }
    setQuoteBankSelectionMode(mode);
  };

  const toggleQuoteBankMethod = (method) => {
    const key = getQuoteBankMethodSignature(method);
    if (!key) return;
    setSelectedQuoteBankKeys((current) => (
      current.includes(key)
        ? current.filter((item) => item !== key)
        : [...current, key]
    ));
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

    const validItems = items
      .filter((it) => it.descripcion?.trim() && Number(it.cantidad) > 0 && Number(it.precio_unitario) > 0)
      .map((it) => ({
        producto_id: it.producto_id ? Number(it.producto_id) : undefined,
        codigo_producto: normalizeInternalProductCode(it.codigo) || undefined,
        descripcion: it.descripcion,
        cantidad: Number(it.cantidad),
        precio_unitario: Number(it.precio_unitario),
        unidad_medida: it.unidad_medida || 'NIU',
        tipo_afectacion_igv: it.tipo_afectacion_igv || '10',
      }));
    if (validItems.length === 0) {
      toast('Agrega al menos una linea valida antes de guardar la cotizacion.', 'error');
      return;
    }

    try {

      // 1. Upsert client if needed
      const {
        id: resolvedClienteId,
        client: persistedClient,
      } = await upsertCliente({
        id:      clienteId,
        isNew:   clienteIsNew,
        isDirty: clienteDirty,
        form:    clienteForm || {},
        updateExisting: updateExistingClient,
      });

      if (persistedClient) {
        const normalizedClient = normalizeFiscalClientForm(persistedClient);
        onClientePersisted?.({ ...persistedClient, ...normalizedClient, id: persistedClient.id });
        setClienteId(String(persistedClient.id));
        setClienteForm(normalizedClient);
        setClienteDirty(false);
        setClienteIsNew(false);
      }

      // 2. Upsert new products
      const createdItems = await upsertProductos(items, { priceIncludesIgv: true });
      const resolvedItems = await syncCatalogProductos(createdItems, { priceIncludesIgv: true });

      // 3. Create quote
      onSave({
        cliente_id:        Number(resolvedClienteId),
        cliente_snapshot:  clienteForm ? clienteSnapshotFromForm(clienteForm) : undefined,
        moneda,
        tipo_comprobante:  '00',
        condicion_pago:    condicion,
        fecha_vencimiento: condicion === 'contado' ? undefined : (fechaVenc || undefined),
        quote_selected_wallet_id: quoteWalletId || undefined,
        quote_payment_methods: serializeQuoteBankMethods(effectiveQuoteBankMethods),
        observaciones:     observationLines.some((line) => line.text?.trim())
          ? serializeObservationLines(observationLines)
          : undefined,
        items: resolvedItems
          .filter((it) => it.descripcion?.trim() && Number(it.cantidad) > 0 && Number(it.precio_unitario) > 0)
          .map((it) => ({
            producto_id: it.producto_id ? Number(it.producto_id) : undefined,
            codigo_producto: normalizeInternalProductCode(it.codigo) || undefined,
            descripcion: it.descripcion,
            cantidad: Number(it.cantidad),
            precio_unitario: Number(it.precio_unitario),
            unidad_medida: it.unidad_medida || 'NIU',
            tipo_afectacion_igv: it.tipo_afectacion_igv || '10',
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
    setUpdateExistingClient(true);
    setMoneda('PEN');
    setCondicion(DEFAULT_QUOTE_PAYMENT_CONDITION);
    setFechaVenc(calcFechaVencimiento(DEFAULT_QUOTE_PAYMENT_CONDITION));
    setQuoteWalletId('');
    setObservationLines(buildDefaultObservationLines(tenantData));
    setObservacionesOpen(false);
    setQuoteBankSelectionMode('global');
    setSelectedQuoteBankKeys(defaultQuoteBankKeys);
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
  const previewClient = getPreviewClientData(clienteId, clienteForm, formClientes);
  const hasObservationLines = observationLines.some((line) => line.text?.trim());
  const walletOptions = getWalletOptions(tenantData?.bank_accounts);
  const readyLines = items.filter((item) => item.descripcion?.trim() && Number(item.cantidad) > 0 && Number(item.precio_unitario) > 0).length;
  const quoteReady = Boolean(clienteId || clienteForm?.razon_social) && readyLines > 0;
  const missingQuoteRequirements = [
    !(clienteId || clienteForm?.razon_social) && 'seleccionar un cliente',
    !readyLines && 'agregar una línea con cantidad y precio',
  ].filter(Boolean);
  const quoteSections = [
    { id: 'quote-client', label: 'Cliente', status: clienteId || clienteForm?.razon_social ? 'Listo' : 'Pendiente' },
    { id: 'quote-lines', label: 'Detalle', status: readyLines ? `${readyLines} línea${readyLines !== 1 ? 's' : ''}` : 'Pendiente' },
    { id: 'quote-observations', label: 'PDF', status: hasObservationLines ? 'Incluido' : 'Opcional' },
    { id: 'quote-review', label: 'Revisión', status: quoteReady ? 'Listo' : 'Pendiente' },
  ];

return (
    <>
      <form onSubmit={handleSubmit} className="quote-builder-form">
        <SectionNavigation label="Progreso de cotización" items={quoteSections} />
        <section className="builder">
          {isEditing && (
            <article
              className="panel"
              style={{
                gridColumn: '1 / -1',
                borderColor: 'rgba(132, 204, 22, 0.42)',
                background: 'linear-gradient(135deg, rgba(132, 204, 22, 0.12), var(--color-surface) 45%)',
              }}
            >
              <div className="panel-header">
                <div>
                  <h3>Editando {editDisplayNumber}</h3>
                  <p>Solo se permite cambiar una cotizacion pendiente, sin pagos y sin comprobante asociado.</p>
                </div>
                <button type="button" className="mini-action" onClick={onCancelEdit}>Cancelar edicion</button>
              </div>
            </article>
          )}
          <div>
            <article id="quote-client" tabIndex={-1} className="panel form-section-anchor">
              <div className="panel-header"><div><h3>Cliente y condiciones</h3><p>Primero identifica al cliente. Si ya existe, se autocompletan sus datos.</p></div></div>
              <div className="panel-body">
                <ClientCombobox
                  value={clienteId}
                  onChange={setClienteId}
                  clients={formClientes}
                  onFormChange={handleClientFormChange}
                  quoteCountByClient={quoteCountByClient}
                  recentClientIds={recentClientIds}
                />
                {clienteId && clienteForm?.razon_social && (
                  <div className="client-result">
                    <div className="avatar">
                      {clienteForm.razon_social.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()}
                    </div>
                    <div>
                      <strong>{clienteForm.razon_social}</strong>
                      <span>
                        {getFiscalDocLabel(clienteForm.tipo_documento)} {clienteForm.numero_documento}
                        {clienteForm.telefono ? ` · ${clienteForm.telefono}` : ''}
                      </span>
                    </div>
                  </div>
                )}
                {clienteId && clienteDirty && !clienteIsNew && (
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
                <div className="form-grid" style={{ marginTop: '16px' }}>
                  <div className="field span-2">
                    <label>Moneda</label>
                    <div className="control">
                      <CustomSelect
                        value={moneda}
                        onChange={setMoneda}
                        options={[
                          { value: 'PEN', label: 'PEN (S/) Soles' },
                          { value: 'USD', label: 'USD ($) Dólares' },
                        ]}
                      />
                    </div>
                  </div>
                  <div className="field span-5">
                    <label>Condición de pago</label>
                    <div className="control">
                      <CustomSelect
                        value={condicion}
                        onChange={setCondicion}
                        options={CONDICIONES_PAGO}
                      />
                    </div>
                  </div>
                  <div className="field span-5">
                    <label>Fecha vencimiento</label>
                    <div className="control">
                      <DatePicker value={fechaVenc} onChange={setFechaVenc} disabled={condicion === 'contado'} />
                    </div>
                  </div>
                  <div className="field span-12">
                    <label>Billetera visible junto al QR</label>
                    <div className="control">
                      <CustomSelect
                        value={quoteWalletId}
                        onChange={(value) => setQuoteWalletId(String(value || ''))}
                        options={[
                          { value: '', label: 'Usar billetera predeterminada del negocio' },
                          ...walletOptions,
                        ]}
                        placeholder="Seleccionar billetera"
                        searchable
                        searchPlaceholder="Buscar billetera..."
                      />
                    </div>
                  </div>
                </div>
              </div>
            </article>

            <article id="quote-payment" tabIndex={-1} className="panel form-section-anchor quote-payment-panel">
              <div className="panel-header">
                <div>
                  <h3>Medios de cobro para el PDF</h3>
                  <p>Usa la selección predeterminada o personaliza lo que verá tu cliente.</p>
                </div>
              </div>
              <details className="quote-payment-details">
                <summary>
                  <span>
                    <strong>{effectiveQuoteBankMethods.length} cuenta{effectiveQuoteBankMethods.length !== 1 ? 's' : ''} visible{effectiveQuoteBankMethods.length !== 1 ? 's' : ''}</strong>
                    <small>{quoteBankSelectionMode === 'global' ? 'Usando la configuración predeterminada' : 'Selección personalizada para esta cotización'}</small>
                  </span>
                  <span className="quote-payment-details__action">Configurar</span>
                </summary>
                <div className="panel-body">
                <div className="quote-bank-selector-summary">
                  <div>
                    <strong>
                      {quoteBankSelectionMode === 'global'
                        ? `Usando selección global (${effectiveQuoteBankMethods.length})`
                        : `Selección personalizada (${effectiveQuoteBankMethods.length})`}
                    </strong>
                    <span>
                      {quoteBankSelectionMode === 'global'
                        ? 'Las nuevas cotizaciones usan las cuentas marcadas en Configuración.'
                        : 'Esta cotización puede mostrar un subconjunto distinto sin alterar la configuración general.'}
                    </span>
                  </div>
                  <div className="quote-bank-selector-actions">
                    <button
                      type="button"
                      className={`mini-action${quoteBankSelectionMode === 'global' ? ' is-active' : ''}`}
                      onClick={() => handleQuoteBankModeChange('global')}
                    >
                      Usar global
                    </button>
                    <button
                      type="button"
                      className={`mini-action${quoteBankSelectionMode === 'custom' ? ' is-active' : ''}`}
                      onClick={() => handleQuoteBankModeChange('custom')}
                    >
                      Personalizar
                    </button>
                  </div>
                </div>

                {availableQuoteBankMethods.length === 0 ? (
                  <div className="quote-bank-selector-empty">
                    No hay cuentas bancarias completas para mostrar en cotizaciones. Configúralas en Configuración.
                  </div>
                ) : (
                  <>
                    {quoteBankSelectionMode === 'custom' && (
                      <div className="quote-bank-selector-toolbar">
                        <button
                          type="button"
                          className="link-btn"
                          onClick={() => setSelectedQuoteBankKeys(getQuoteBankKeys(availableQuoteBankMethods))}
                        >
                          Seleccionar todas
                        </button>
                        <button
                          type="button"
                          className="link-btn"
                          onClick={() => setSelectedQuoteBankKeys([])}
                        >
                          Limpiar
                        </button>
                      </div>
                    )}

                    <div className="quote-bank-selector-grid">
                      {availableQuoteBankMethods.map((method, index) => {
                        const key = getQuoteBankMethodSignature(method);
                        const preview = getPaymentMethodPreview(method);
                        const isSelected = selectedQuoteBankKeySet.has(key);
                        const isDefault = defaultQuoteBankKeys.includes(key);

                        return (
                          <button
                            key={`${key || 'bank'}-${index}`}
                            type="button"
                            className={`quote-bank-option${isSelected ? ' is-selected' : ''}${quoteBankSelectionMode === 'global' ? ' is-disabled' : ''}`}
                            onClick={() => quoteBankSelectionMode === 'custom' && toggleQuoteBankMethod(method)}
                            aria-pressed={quoteBankSelectionMode === 'custom' ? isSelected : undefined}
                          >
                            <div className="quote-bank-option-copy">
                              <div className="quote-bank-option-head">
                                <span className="quote-bank-option-name">{preview?.title || 'Cuenta bancaria'}</span>
                                <span className={`quote-bank-option-badge${isSelected ? ' is-selected' : ''}`}>
                                  {quoteBankSelectionMode === 'global'
                                    ? (isSelected ? 'Global' : 'Oculta')
                                    : (isSelected ? 'Visible' : 'Oculta')}
                                </span>
                              </div>
                              {preview?.lines?.map((line, lineIndex) => (
                                <span key={`${key}-${lineIndex}`} className="quote-bank-option-meta">{line}</span>
                              ))}
                              <span className="quote-bank-option-meta quote-bank-option-meta--secondary">
                                {isDefault
                                  ? 'Disponible por defecto para nuevas cotizaciones.'
                                  : 'No está marcada como predeterminada en la configuración global.'}
                              </span>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </>
                )}
              </div>
              </details>
            </article>

            <article id="quote-lines" tabIndex={-1} className="panel form-section-anchor quote-lines-panel">
              <div className="panel-header line-items-panel-header">
                <div><h3>Líneas de detalle</h3><p>Agrega productos, servicios o descripciones libres.</p></div>
                <div className="line-items-panel-controls">
                  {catalogSyncEligibleCount > 0 && (
                    <button
                      type="button"
                      className={`toggle-chip line-sync-chip${syncCatalogOnSave ? ' is-active' : ''}`}
                      aria-pressed={syncCatalogOnSave}
                      onClick={toggleCatalogSyncForEligible}
                    >
                      <span className={`switch ${syncCatalogOnSave ? 'on' : ''}`} />
                      {syncCatalogOnSave ? 'Actualizar catálogo al guardar' : 'Aplicar cambios al catálogo'}
                    </button>
                  )}
                  <label className="toggle-chip">
                    <span className={`switch ${avanzado ? 'on' : ''}`} />
                    Mostrar unidad e IGV
                    <input type="checkbox" checked={avanzado} onChange={() => setAvanzado((c) => !c)} style={{ position: 'absolute', opacity: 0, width: 0, height: 0 }} />
                  </label>
                </div>
              </div>
              <div className="panel-body">
                {catalogSyncEligibleCount > 0 && (
                  <div className={`line-sync-banner${syncCatalogOnSave ? ' is-active' : ''}`}>
                    <strong>
                      {catalogSyncEligibleCount} producto{catalogSyncEligibleCount !== 1 ? 's' : ''} con cambios de catálogo
                    </strong>
                    <span>
                      {syncCatalogOnSave
                        ? 'Se actualizaran en la base al guardar este documento.'
                        : 'Los cambios quedaran solo en este documento hasta que actives el guardado global.'}
                    </span>
                  </div>
                )}
                <div className={`line-table${avanzado ? ' line-table--avanzado' : ''}`}>
                  <div className="line-head">
                    <div>Código / Producto</div>
                    {avanzado && <div>Unidad</div>}
                    {avanzado && <div>Afectación</div>}
                    <div>Cant.</div>
                    <div>P. unit.</div>
                    <div>Total</div>
                    <div></div>
                  </div>
                  {items.map((item, idx) => {
                    const lineTotal = Number(item.cantidad) * Number(item.precio_unitario) || 0;
                    return (
                      <div className="line-row" key={idx}>
                        <div className="product-input line-row-cell line-row-cell--product" data-mobile-label="Producto">
                          <ProductLineCell
                            value={item}
                            onChange={(next) => setItemAll(idx, next)}
                            products={productosDisp}
                            incluyeIgv
                            sym={sym}
                            onGenerateCode={handleGenerateCode}
                          />
                        </div>
                        {avanzado && (
                          <div className="line-row-cell line-row-cell--unit" data-mobile-label="Unidad">
                            <CustomSelect compact value={item.unidad_medida} onChange={(v) => setItem(idx, 'unidad_medida', v)} options={UNIDADES_MEDIDA} />
                          </div>
                        )}
                        {avanzado && (
                          <div className="line-row-cell line-row-cell--tax" data-mobile-label="Afectación IGV">
                            <CustomSelect compact value={item.tipo_afectacion_igv} onChange={(v) => setItem(idx, 'tipo_afectacion_igv', v)} options={AFECTACION_IGV} />
                          </div>
                        )}
                        <div className="line-row-cell line-row-cell--qty" data-mobile-label="Cantidad"><input className="line-edit-input" aria-label={`Cantidad de ${item.descripcion || `línea ${idx + 1}`}`} required type="number" min="0.01" step="any" value={item.cantidad} onChange={(e) => setItem(idx, 'cantidad', e.target.value)} /></div>
                        <div className="line-row-cell line-row-cell--price" data-mobile-label="Precio unitario">
                          <div className="line-price-control">
                            <span aria-hidden="true">{sym}</span>
                            <input className="line-edit-input" aria-label={`Precio unitario de ${item.descripcion || `línea ${idx + 1}`}`} required type="text" inputMode="decimal" value={item.precio_unitario} onChange={(e) => setItem(idx, 'precio_unitario', e.target.value)} />
                          </div>
                        </div>
                        <div className="line-row-cell line-row-cell--total" data-mobile-label="Total"><input className="line-static-input" readOnly value={`${sym} ${fmt(lineTotal)}`} /></div>
                        <div className="line-row-cell line-row-cell--actions">{items.length > 1 && <button type="button" className="trash-btn" onClick={() => removeItem(idx)}>×</button>}</div>
                      </div>
                    );
                  })}
                </div>
                <div className="line-footer">
                  <button type="button" className="link-btn" onClick={addItem}>⊕ Agregar línea</button>
                </div>
              </div>
            </article>

            <article id="quote-observations" tabIndex={-1} className="panel form-section-anchor">
              <div className="panel-header">
                <div><h3>Observaciones del PDF</h3><p>Textos comerciales visibles para el cliente.</p></div>
                {!observacionesOpen && !hasObservationLines ? (
                  <button type="button" className="mini-action" onClick={() => setObservacionesOpen(true)}>Mostrar</button>
                ) : (
                  <button type="button" className="mini-action" onClick={() => setObservacionesOpen((c) => !c)}>{observacionesOpen ? 'Ocultar' : 'Mostrar'}</button>
                )}
              </div>
              {observacionesOpen && (
                <div className="panel-body">
                  <div className="note-blocks">
                    {observationLines.map((line, index) => (
                      <div key={`observation-line-${index}`} className="note-row">
                        <div className="note-top">
                          <div className="note-label">Línea {index + 1}</div>
                          <div className="note-tools">
                            <label className="check-label">
                              <input type="checkbox" checked={line.bold} onChange={(event) => updateObservationLine(index, { bold: event.target.checked })} />
                              Negrita
                            </label>
                            <span className="color-pill" style={{ '--pill-color': line.color, borderColor: line.color === '#111111' || line.color === 'var(--text-primary)' ? 'var(--color-border)' : line.color }}>
                              <span className="color-dot" style={{ background: line.color }} />
                              <span>{line.color}</span>
                              <ColorPickerField
                                value={line.color}
                                onChange={(val) => updateObservationLine(index, { color: val })}
                                fallback={index === 0 ? '#DC2626' : '#111111'}
                                presets={['#DC2626', '#D97706', '#111111', '#8DC63F']}
                                openUpward
                              />
                            </span>
                          </div>
                        </div>
                        <div className="control textarea">
                          <textarea
                            value={line.text}
                            onChange={(event) => updateObservationLine(index, { text: event.target.value })}
                            placeholder={index === 0 ? DEFAULT_NOTE_1_TEXT : DEFAULT_NOTE_2_TEXT}
                            style={{ color: line.color, fontWeight: line.bold ? 800 : 400 }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </article>
          </div>

          <aside>
            <article id="quote-review" tabIndex={-1} className="summary-card form-section-anchor">
              <div className="summary-header">
                <h3>{isEditing ? 'Resumen de edicion' : 'Resumen de cotización'}</h3>
                <p>{isEditing ? 'Revisa los nuevos totales antes de actualizar.' : 'Cálculo siempre visible para evitar guardar sin revisar.'}</p>
              </div>
              <div className="summary-body">
                <div className="total-line"><span>Subtotal</span><strong>{sym} {fmt(subtotalGravado + totales.exonerado + totales.inafecto + totales.exportacion)}</strong></div>
                <div className="total-line"><span>IGV (18%)</span><strong>{sym} {fmt(igv)}</strong></div>
                <div className="total-line"><span>Líneas</span><strong>{items.length}</strong></div>
                <div className="grand-total"><span>Total</span><strong>{sym} {fmt(totalGeneral)}</strong></div>
              </div>
              <div className="summary-actions">
                <button type="button" className="side-btn open-preview" onClick={() => setPreviewOpen(true)}><Eye size={16} /> Vista previa</button>
                <button type="button" className="side-btn"><Save size={16} /> Guardar borrador</button>
                {!quoteReady && (
                  <p id="quote-save-requirements" className="quote-save-requirements" role="status">
                    Falta {missingQuoteRequirements.join(' y ')}.
                  </p>
                )}
                <button type="submit" className="side-btn primary" disabled={saving || !quoteReady} aria-describedby={!quoteReady ? 'quote-save-requirements' : undefined}>
                  {saving ? 'Guardando…' : isEditing ? 'Actualizar cotizacion' : 'Guardar cotización'}
                </button>
              </div>
            </article>
          </aside>
        </section>
        <div className="mobile-summary-bar" aria-live="polite">
          <div>
            <span>Total de cotización</span>
            <strong>{sym} {fmt(totalGeneral)}</strong>
          </div>
          <button type="submit" className="btn-primary" disabled={saving || !quoteReady} aria-describedby={!quoteReady ? 'quote-save-requirements' : undefined}>
            {saving ? 'Guardando…' : 'Guardar'}
          </button>
        </div>
      </form>

      <Modal
        open={previewOpen}
        onClose={() => setPreviewOpen(false)}
        title="Vista previa de cotización"
        size="xl"
      >
        <div style={{ margin: '-24px', overflow: 'auto', maxHeight: '82vh' }}>
          <CotizacionPreviewSheet
            tenantData={tenantData}
            user={user}
            cliente={previewClient}
            moneda={moneda}
            condicion={condicion}
            items={items}
            observationLines={observationLines}
            quotePaymentMethods={effectiveQuoteBankMethods}
            subtotalGravado={subtotalGravado}
            igv={igv}
            totalGeneral={totalGeneral}
            selectedWalletId={quoteWalletId}
          />
        </div>
      </Modal>
    </>
  );
}

// ─── Página principal ─────────────────────────────────────────────────────────

export default function CotizacionesPage() {
  const toast = useToast();
  const [searchParams] = useSearchParams();
  const initialSearch = searchParams.get('q') || '';
  const initialViewParam = searchParams.get('view');
  const initialView = initialViewParam === 'fiscal' ? 'fiscal' : (initialSearch || initialViewParam === 'history' ? 'history' : 'create');

  // Vista activa: 'create' | 'history' | 'fiscal'
  const [view, setView] = useState(initialView);

  // Datos compartidos
  const [clientes, setClientes]         = useState([]);
  const [productosDisp, setProductosDisp] = useState([]);
  const [loadingMaster, setLoadingMaster] = useState(true);

  // Documentos
  const [list, setList]         = useState([]);
  const [fiscalDocs, setFiscalDocs] = useState([]);
  const [fiscalDocumentTotal, setFiscalDocumentTotal] = useState(0);
  const [fiscalCounts, setFiscalCounts] = useState({
    all: 0, draft: 0, emitted: 0, pending: 0, rejected: 0, voided: 0,
  });
  const [loading, setLoading]   = useState(false);
  const [saving, setSaving]     = useState(false);
  const [editingQuote, setEditingQuote] = useState(null);

  // Búsqueda y filtros
  const [search, setSearch]         = useState(initialSearch);
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
  const [historyPage, setHistoryPage] = useState(1);

  // Carga de datos maestros (clientes y productos) con una página inicial acotada.
  useEffect(() => {
    Promise.all([cliSvc.page('?limit=15'), prodSvc.page('?limit=15')])
      .then(([c, p]) => {
        setClientes(Array.isArray(c) ? c : c?.items || []);
        setProductosDisp(Array.isArray(p) ? p : p?.items || []);
      })
      .catch(() => toast('No se pudo cargar clientes y productos para cotizar.', 'error'))
      .finally(() => setLoadingMaster(false));
  }, [toast]);

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([svc.list(), svc.fiscalPage()])
      .then(([quotesResponse, fiscalResponse]) => {
        const quoteItems = Array.isArray(quotesResponse) ? quotesResponse : quotesResponse?.items || [];
        const fiscalItems = Array.isArray(fiscalResponse) ? fiscalResponse : fiscalResponse?.items || [];
        const fallbackCounts = {
          all: fiscalItems.length,
          draft: 0,
          emitted: fiscalItems.filter((item) => getSunatStatus(item)?.variant === 'success').length,
          pending: fiscalItems.filter((item) => getSunatStatus(item)?.variant === 'warning').length,
          rejected: fiscalItems.filter((item) => getSunatStatus(item)?.variant === 'danger').length,
          voided: 0,
        };

        setList(quoteItems);
        setFiscalDocs(fiscalItems);
        setFiscalDocumentTotal(Number(fiscalResponse?.total ?? fiscalItems.length));
        setFiscalCounts(fiscalResponse?.counts || fallbackCounts);
      })
      .catch(() => toast('No se pudo cargar la información. Revisa tu conexión e inténtalo nuevamente.', 'error'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const query = searchParams.get('q') || '';
    const viewParam = searchParams.get('view');
    const nextView = viewParam === 'fiscal' ? 'fiscal' : (query || viewParam === 'history' ? 'history' : 'create');
    setSearch((current) => (current === query ? current : query));
    setView((current) => (current === nextView ? current : nextView));
  }, [searchParams]);

  // Separación por tipo
  const quotations = list.filter((d) => d.document_kind === 'quotation');
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
      || item.internal_order_number?.toLowerCase().includes(q)
      || getDocumentDisplayNumber(item).toLowerCase().includes(q);
    const matchDesde = !filters.desde || new Date(item.fecha_emision) >= new Date(filters.desde);
    const matchHasta = !filters.hasta || new Date(item.fecha_emision) <= new Date(filters.hasta);
    return matchSearch && matchDesde && matchHasta;
  });

  useEffect(() => {
    setHistoryPage(1);
  }, [search, filters.desde, filters.hasta, quotations.length]);

  const historyPageCount = Math.max(1, Math.ceil(filteredHistory.length / HISTORY_PAGE_SIZE));
  const safeHistoryPage = Math.min(historyPage, historyPageCount);
  const historyPageStart = filteredHistory.length ? (safeHistoryPage - 1) * HISTORY_PAGE_SIZE : 0;
  const historyPageEnd = Math.min(historyPageStart + HISTORY_PAGE_SIZE, filteredHistory.length);
  const historyPageItems = filteredHistory.slice(historyPageStart, historyPageEnd);

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

  const hasHistoryFilters = Boolean(search || filters.desde || filters.hasta);
  const hasFiscalFilters = Boolean(
    search
    || filters.docReceptor
    || filters.razonSocial
    || filters.serie
    || filters.numero
    || filters.tipo !== 'all'
    || filters.moneda !== 'all'
    || filters.formaPago !== 'all'
    || filters.desde
    || filters.hasta,
  );

  const historyTotal = filteredHistory.reduce((sum, item) => sum + Number(item.total_venta || 0), 0);
  const historyPendingBalance = filteredHistory.reduce((sum, item) => sum + Number(item.saldo_pendiente || 0), 0);
  const historyLinkedCount = filteredHistory.filter(
    (item) => item.linked_fiscal_document_number && item.linked_fiscal_document_status !== 'anulada',
  ).length;

  const fiscalTotal = filteredFiscal.reduce((sum, item) => sum + Number(item.total_venta || 0), 0);
  const fiscalAcceptedCount = filteredFiscal.filter((item) => getSunatStatus(item)?.variant === 'success').length;
  const fiscalPendingCount = filteredFiscal.filter((item) => getSunatStatus(item)?.variant === 'warning').length;
  const fiscalRejectedCount = filteredFiscal.filter((item) => getSunatStatus(item)?.variant === 'danger').length;
  const fiscalVisibleCount = hasFiscalFilters ? filteredFiscal.length : fiscalDocumentTotal;
  const fiscalVisibleAcceptedCount = hasFiscalFilters ? fiscalAcceptedCount : Number(fiscalCounts.emitted || 0);
  const fiscalVisiblePendingCount = hasFiscalFilters ? fiscalPendingCount : Number(fiscalCounts.pending || 0);
  const fiscalVisibleRejectedCount = hasFiscalFilters ? fiscalRejectedCount : Number(fiscalCounts.rejected || 0);
  const fiscalLoadedIsPartial = fiscalDocumentTotal > fiscalDocs.length;

  const handleOpenNuevoCliente = (prefill = '') => {
    setNuevoClientePrefill(prefill);
    setNuevoClienteOpen(true);
  };

  const handleSave = async (data) => {
    setSaving(true);
    try {
      if (editingQuote?.id) {
        await svc.update(editingQuote.id, data);
        setEditingQuote(null);
      } else {
        await svc.create(data);
      }
      toast(editingQuote?.id ? 'Cotizacion actualizada' : 'Cotizacion guardada');
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

  const handlePersistedCliente = useCallback((client) => {
    if (!client?.id) return;
    setClientes((prev) => {
      const next = prev.filter((item) => String(item.id) !== String(client.id));
      return [client, ...next];
    });
    setRecentClientIds((prev) => (prev.includes(client.id) ? prev : [...prev, client.id]));
  }, []);

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
      const { blob, disposition } = await api.getBlob(`/cotizaciones/${item.id}/pdf/download`, { timeoutMs: 45000 });
      const filename = /filename="?([^"]+)"?/i.exec(disposition || '')?.[1]
        || `${item.serie || 'COT'}-${String(item.correlativo || 0).padStart(6, '0')}.pdf`;
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      toast(err.message || 'No se pudo descargar el PDF', 'error');
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

  const resolveShareLinks = async (item) => {
    try {
      const data = await svc.share(item.id);
      return {
        url: data?.url_compartir || data?.url || getPublicShareUrl(item),
        whatsapp: data?.whatsapp_link || '',
        email: data?.mailto_link || '',
      };
    } catch (err) {
      toast(err.message, 'error');
      return null;
    }
  };

  const openShareLink = (link, channel) => {
    if (!link) {
      toast(
        channel === 'email'
          ? 'El cliente no tiene correo registrado.'
          : 'El cliente no tiene WhatsApp valido.',
        'error',
      );
      return false;
    }

    if (channel === 'email') {
      window.location.href = link;
    } else {
      window.open(link, '_blank', 'noopener,noreferrer');
    }
    return true;
  };

  const handleOpenShareChannel = async (item, channel) => {
    const links = await resolveShareLinks(item);
    if (!links) return;
    openShareLink(channel === 'email' ? links.email : links.whatsapp, channel);
  };

  const handleOpenCombinedShare = async (item) => {
    const links = await resolveShareLinks(item);
    if (!links) return;
    const openedWhatsApp = openShareLink(links.whatsapp, 'whatsapp');
    if (links.email) {
      window.setTimeout(() => openShareLink(links.email, 'email'), openedWhatsApp ? 120 : 0);
    } else {
      toast('El cliente no tiene correo registrado.', 'error');
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

  const handleEditQuote = async (item) => {
    if (!canEditCommercialQuote(item)) {
      toast('Solo se puede editar una cotizacion pendiente sin pagos ni comprobante asociado.', 'error');
      return;
    }

    try {
      const detail = await svc.get(item.id);
      setEditingQuote(detail);
      setView('create');
      window.scrollTo({ top: 0, behavior: 'smooth' });
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

  return (
    <div className="cotizaciones-page">
      <OperationalPageHeader
        variant="workflow"
        eyebrow="Motor comercial"
        title={view === 'create' && editingQuote ? `Editar ${getDocumentDisplayNumber(editingQuote)}` : view === 'create' ? 'Nueva cotización' : view === 'history' ? 'Historial' : 'Emitidas SUNAT'}
        description={view === 'create' && editingQuote
          ? 'Actualiza una cotización pendiente antes de pasarla a comprobante.'
          : view === 'create'
          ? 'Construye una propuesta clara, calcula totales y déjala lista para vista previa.'
          : `${quotations.length} cotizaciones · ${fiscalDocumentTotal} comprobantes emitidos.`}
      />

      <nav className="quote-tabs ink-enter-2">
        <button className={`tab ${view === 'create' ? 'active' : ''}`} onClick={() => { setEditingQuote(null); setView('create'); }}>＋ Nueva cotización</button>
        <button className={`tab ${view === 'history' ? 'active' : ''}`} onClick={() => { setEditingQuote(null); setView('history'); }}>↺ Historial <span className="count-badge">{quotations.length}</span></button>
        <button className={`tab ${view === 'fiscal' ? 'active' : ''}`} onClick={() => setView('fiscal')}>▣ Emitidas SUNAT <span className="count-badge">{fiscalDocumentTotal}</span></button>
      </nav>

      {/* ── Vista: Crear ── */}
      {view === 'create' && (
        loadingMaster ? (
              <article className="panel">
                <div className="panel-body">
                  <SkeletonForm fields={5} />
                </div>
              </article>
            ) : (
              <NuevaCotizacionForm
                onSave={handleSave}
                onClear={() => {}}
                onClientePersisted={handlePersistedCliente}
                saving={saving}
                clientes={clientes}
                productosDisp={productosDisp}
                onNuevoCliente={handleOpenNuevoCliente}
                quoteCountByClient={quoteCountByClient}
                recentClientIds={recentClientIds}
                createdClient={createdClient}
                initialQuote={editingQuote}
                onCancelEdit={() => {
                  setEditingQuote(null);
                  setView('history');
                }}
              />
            )
      )}

      {/* ── Vista: Historial ── */}
      {view === 'history' && (
        <>
          <SearchBar
            search={search}
            onSearch={setSearch}
            showFilters={showFilters}
            onToggleFilters={() => setShowFilters(!showFilters)}
            onNewAction={() => {
              setEditingQuote(null);
              setView('create');
            }}
            newLabel="+ Nueva cotización"
          />

          {showFilters && (
            <div className="proto-filter-card proto-filter-card--history">
              <div className="proto-filter-field">
                <label>Desde</label>
                <div className="proto-filter-control">
                  <DatePicker compact value={filters.desde} onChange={(v) => handleFilterChange('desde', v)} />
                </div>
              </div>
              <div className="proto-filter-field">
                <label>Hasta</label>
                <div className="proto-filter-control">
                  <DatePicker compact value={filters.hasta} onChange={(v) => handleFilterChange('hasta', v)} />
                </div>
              </div>
              <div className="proto-filter-actions">
                <button type="button" className="btn-secondary" onClick={() => setFilters((current) => ({ ...current, desde: '', hasta: '' }))}>
                  Limpiar rango
                </button>
              </div>
            </div>
          )}

          {!loading && filteredHistory.length > 0 && (
            <div className="summary-strip summary-strip--history">
              <div className="summary-items">
                <div className="summary-item">
                  <div className="summary-icon"><History size={16} /></div>
                  <div>
                    <span>Cotizaciones visibles</span>
                    <strong>{filteredHistory.length}</strong>
                    <span>En esta vista</span>
                  </div>
                </div>
                <div className="summary-item">
                  <div className="summary-icon"><Receipt size={16} /></div>
                  <div>
                    <span>Total visible</span>
                    <strong>S/ {fmt(historyTotal)}</strong>
                    <span>Monto filtrado</span>
                  </div>
                </div>
                <div className="summary-item">
                  <div className="summary-icon"><Clock size={16} /></div>
                  <div>
                    <span>Saldo pendiente</span>
                    <strong>S/ {fmt(historyPendingBalance)}</strong>
                    <span>{historyLinkedCount} convertidas a comprobante</span>
                  </div>
                </div>
              </div>
              <div className="proto-pagination">
                <span>{hasHistoryFilters ? 'Filtros activos' : 'Vista completa'}</span>
              </div>
            </div>
          )}

          {loading ? (
            <div className="records-card">
              <div className="p-4">
                <div className="skeleton skeleton--title" style={{ width: '30%' }} />
                <div className="mt-4 space-y-2">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <div key={i} className="skeleton-row">
                      <div className="skeleton skeleton--circle" style={{ width: 32, height: 32 }} />
                      <div className="skeleton skeleton-row__cell" />
                      <div className="skeleton skeleton-row__cell skeleton-row__cell--sm" />
                    </div>
                  ))}
                </div>
              </div>
            </div>
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
            <div className="records-card cotizaciones-history-card">
              <div className="panel-header">
                <div>
                  <h3>Historial comercial</h3>
                  <p>Seguimiento de cotizaciones, conversiones y cobranza asociada.</p>
                </div>
                <div className="proto-pagination">
                  <span>
                    {filteredHistory.length
                      ? `${historyPageStart + 1}-${historyPageEnd} de ${filteredHistory.length}`
                      : 'Sin registros'}
                  </span>
                </div>
              </div>
              <div className="ink-table-scroll cotizaciones-history-scroll">
              <table className="ink-table cotizaciones-history-table">
                <thead>
                  <tr>
                    <th className="ink-th">F. Emisión</th>
                    <th className="ink-th">N° Cotización</th>
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
                  {historyPageItems.map((item) => {
                    const hasLinked = !!item.linked_fiscal_document_number && item.linked_fiscal_document_status !== 'anulada';
                    const sym = item.moneda === 'USD' ? '$' : 'S/';
                    const linkedSunat = getLinkedSunatStatus(item);
                    const waLink = getWhatsAppLink(item.cliente, item);
                    const emailLink = getEmailLink(item.cliente, item);
                    const canDelete = !hasLinked && item.estado !== 'anulada';
                    return (
                      <tr key={item.id} className="ink-tr">
                        <td className="ink-td history-date-cell" data-label="F. emision">
                          <span className="history-date-value">
                            {item.fecha_emision ? new Date(item.fecha_emision).toLocaleDateString('es-PE') : '--'}
                          </span>
                        </td>
                        <td className="ink-td font-mono-label text-xs" data-label="N° cotización">
                          <span className="history-quote-number">{getDocumentDisplayNumber(item)}</span>
                        </td>
                        <td className="ink-td" data-label="Cliente">
                          <div className="history-client-cell">
                            <span>{item.cliente?.razon_social || '--'}</span>
                            {item.cliente?.numero_documento && <small>{item.cliente.numero_documento}</small>}
                          </div>
                        </td>
                        <td className="ink-td text-center" data-label="M."><span className="history-currency">{sym}</span></td>
                        <td className="ink-td text-right" data-label="Total"><span className="history-money history-money--strong">{sym} {fmt(item.total_venta)}</span></td>
                        <td className="ink-td text-right" data-label="Saldo">
                          <span className="history-money">{sym} {fmt(item.saldo_pendiente)}</span>
                        </td>
                        <td className="ink-td" data-label="Pago">
                          <Badge variant={statusBadge(item.payment_status)} className="history-payment-badge">
                            {item.payment_status === 'pendiente' ? 'Por cobrar' : getPaymentStatusLabel(item.payment_status)}
                          </Badge>
                        </td>
                        <td className="ink-td" data-label="Comprobante">
                          {hasLinked ? (
                            <div className="history-linked-doc">
                              <span className="history-linked-number">
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
                            <span className="history-unissued-pill">Sin comprobante</span>
                          )}
                        </td>
                        <td className="ink-td" data-label="Acciones">
                          <div className="history-actions-desktop">
                            <Link
                              to={`/cotizaciones/${item.id}`}
                              className="history-action-button history-action-button--brand"
                              aria-label="Ver detalle de cotizacion"
                            >
                              <Eye className="h-4 w-4" />
                              <span>Ver</span>
                            </Link>
                            <button
                              type="button"
                              className="history-action-button history-action-button--info"
                              onClick={() => handleOpenPdf(item)}
                              aria-label="Descargar PDF de cotizacion"
                            >
                              <Download className="h-4 w-4" />
                              <span>PDF</span>
                            </button>
                            {!hasLinked && (
                              <button
                                type="button"
                                className="history-action-button history-action-button--accent"
                                onClick={() => setEmitirDoc(item)}
                                aria-label="Emitir factura o boleta desde esta cotizacion"
                              >
                                <Receipt className="h-4 w-4" />
                                <span>Emitir</span>
                              </button>
                            )}
                            <details className="history-actions-more">
                              <summary className="history-action-button history-action-button--neutral" aria-label="Mas acciones">
                                <MoreHorizontal className="h-4 w-4" />
                                <span>Mas</span>
                              </summary>
                              <div className="history-actions-more-menu">
                                {canEditCommercialQuote(item) && (
                                  <button type="button" className="history-actions-mobile-item" onClick={() => handleEditQuote(item)}>
                                    <PencilLine className="h-3.5 w-3.5" />
                                    Editar cotizacion
                                  </button>
                                )}
                                <button type="button" className="history-actions-mobile-item" onClick={() => handleDuplicateQuote(item)}>
                                  <Copy className="h-3.5 w-3.5" />
                                  Duplicar
                                </button>
                                <button type="button" className="history-actions-mobile-item" onClick={() => handleCopyShareLink(item)}>
                                  <Share2 className="h-3.5 w-3.5" />
                                  Copiar enlace
                                </button>
                                {waLink && (
                                  <button type="button" className="history-actions-mobile-item" onClick={() => handleOpenShareChannel(item, 'whatsapp')}>
                                    <MessageCircle className="h-3.5 w-3.5" />
                                    WhatsApp
                                  </button>
                                )}
                                {emailLink && (
                                  <button type="button" className="history-actions-mobile-item" onClick={() => handleOpenShareChannel(item, 'email')}>
                                    <Mail className="h-3.5 w-3.5" />
                                    Correo
                                  </button>
                                )}
                                {waLink && emailLink && (
                                  <button
                                    type="button"
                                    className="history-actions-mobile-item"
                                    onClick={() => handleOpenCombinedShare(item)}
                                  >
                                    <Send className="h-3.5 w-3.5" />
                                    WhatsApp + correo
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
                          </div>

                          <details className="history-actions-mobile">
                            <summary className="history-action-button history-action-button--neutral" title="Mas acciones">
                              <MoreHorizontal className="h-4 w-4" />
                              <span>Acciones</span>
                            </summary>
                            <div className="history-actions-mobile-menu">
                              <Link to={`/cotizaciones/${item.id}`} className="history-actions-mobile-item">
                                <Eye className="h-3.5 w-3.5" />
                                Ver detalle
                              </Link>
                              {canEditCommercialQuote(item) && (
                                <button type="button" className="history-actions-mobile-item" onClick={() => handleEditQuote(item)}>
                                  <PencilLine className="h-3.5 w-3.5" />
                                  Editar cotizacion
                                </button>
                              )}
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
                                <button type="button" className="history-actions-mobile-item" onClick={() => handleOpenShareChannel(item, 'whatsapp')}>
                                  <MessageCircle className="h-3.5 w-3.5" />
                                  WhatsApp
                                </button>
                              )}
                              {emailLink && (
                                <button type="button" className="history-actions-mobile-item" onClick={() => handleOpenShareChannel(item, 'email')}>
                                  <Mail className="h-3.5 w-3.5" />
                                  Correo
                                </button>
                              )}
                              {waLink && emailLink && (
                                <button
                                  type="button"
                                  className="history-actions-mobile-item"
                                  onClick={() => handleOpenCombinedShare(item)}
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
              <div className="history-table-footer">
                <span>
                  Pag. {safeHistoryPage} de {historyPageCount} · {HISTORY_PAGE_SIZE} por página
                </span>
                <Pagination
                  page={safeHistoryPage}
                  totalPages={historyPageCount}
                  onPageChange={setHistoryPage}
                  ariaLabel="Paginacion de cotizaciones"
                />
              </div>
            </div>
          )}
        </>
      )}

      {/* ── Vista: Emitidas SUNAT ── */}
      {view === 'fiscal' && (
        <>{/* Panel de filtros — siempre visible, 2 filas */}
          <div className="proto-filter-card proto-filter-card--fiscal-grid">
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
          <div className="summary-strip">
            <div className="summary-items">
              <div className="summary-item">
                <div className="summary-icon"><Receipt size={16} /></div>
                <div>
                  <span>Total registros</span>
                  <strong>{fiscalVisibleCount}</strong>
                  <span>{hasFiscalFilters ? 'Vista filtrada' : fiscalLoadedIsPartial ? `Mostrando los ${fiscalDocs.length} más recientes` : 'Vista completa'}</span>
                </div>
              </div>
              <div className="summary-item">
                <div className="summary-icon"><CheckCircle2 size={16} /></div>
                <div>
                  <span>Aceptados por SUNAT</span>
                  <strong>{fiscalVisibleAcceptedCount}</strong>
                  <span>{fiscalVisiblePendingCount} pendientes y {fiscalVisibleRejectedCount} observados</span>
                </div>
              </div>
              <div className="summary-item">
                <div className="summary-icon"><FileText size={16} /></div>
                <div>
                  <span>Total visible</span>
                  <strong>S/ {fmt(fiscalTotal)}</strong>
                  <span>Importe de los comprobantes visibles</span>
                </div>
              </div>
            </div>
            <div className="proto-summary-actions">
              {!selectedFiscal ? (
                <span className="proto-selection-note">
                  Selecciona un comprobante para emitir nota o anular
                </span>
              ) : (
                <>
              <button
                className="btn-secondary text-[10px] font-bold uppercase tracking-wider px-3 py-1.5 flex items-center gap-2"
                disabled={!selectedFiscal || !['01','03'].includes(selectedFiscal?.tipo_comprobante) || selectedFiscal?.estado === 'anulada'}
                onClick={() => selectedFiscal && setNotaDoc(selectedFiscal)}
                style={{ color: selectedFiscal ? 'var(--color-warning)' : 'var(--border-subtle)', cursor: selectedFiscal ? 'pointer' : 'default' }}
              >
                Nota de Crédito
              </button>
              <button
                className="btn-secondary text-[10px] font-bold uppercase tracking-wider px-3 py-1.5 flex items-center gap-2"
                disabled={!selectedFiscal || !['01','03'].includes(selectedFiscal?.tipo_comprobante) || selectedFiscal?.estado === 'anulada'}
                onClick={() => selectedFiscal && setNotaDoc(selectedFiscal)}
                style={{ color: selectedFiscal ? 'var(--color-warning)' : 'var(--border-subtle)', cursor: selectedFiscal ? 'pointer' : 'default' }}
              >
                Nota de Débito
              </button>
              <div className="proto-action-divider" />
              <button
                className="btn-secondary text-[10px] font-bold uppercase tracking-wider px-3 py-1.5 flex items-center gap-2"
                disabled={!selectedFiscal || selectedFiscal?.estado === 'anulada'}
                onClick={() => selectedFiscal && setAnularDoc(selectedFiscal)}
                style={{ color: selectedFiscal ? 'var(--color-error)' : 'var(--border-subtle)', cursor: selectedFiscal ? 'pointer' : 'default' }}
              >
                Anular
              </button>
              <div className="proto-action-divider" />
              {/* Iconos de descarga rápida para el registro seleccionado */}
              <button
                type="button"
                title="PDF"
                disabled={!selectedFiscal}
                onClick={() => selectedFiscal && handleOpenPdf(selectedFiscal)}
                style={{ opacity: selectedFiscal ? 1 : 0.3, color: 'var(--color-error)', pointerEvents: selectedFiscal ? 'auto' : 'none' }}
                className="row-action-icon row-action-icon--danger"
              >
                <FileText className="h-3 w-3" />
              </button>
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
            <div className="records-card">
              <div className="p-4">
                <div className="skeleton skeleton--title" style={{ width: '30%' }} />
                <div className="mt-4 space-y-2">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <div key={i} className="skeleton-row">
                      <div className="skeleton skeleton--circle" style={{ width: 32, height: 32 }} />
                      <div className="skeleton skeleton-row__cell" />
                      <div className="skeleton skeleton-row__cell skeleton-row__cell--sm" />
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : filteredFiscal.length === 0 ? (
            <EmptyState
              title="Sin comprobantes emitidos"
              description="Emite tu primera factura o boleta desde la pestaña Historial."
            />
          ) : (
            <div className="records-card">
              <div className="panel-header">
                <div>
                  <h3>Comprobantes emitidos</h3>
                  <p>Emision fiscal, estado SUNAT y acciones posteriores desde una sola bandeja.</p>
                </div>
                <div className="proto-pagination">
                  <span>{selectedFiscal ? `Seleccionado: ${selectedFiscal.serie || ''}-${String(selectedFiscal.correlativo || '').padStart(6, '0')}` : 'Selecciona un registro'}</span>
                </div>
              </div>
              <div className="ink-table-scroll">
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
                        className={`ink-tr ${isSelected ? 'ink-table-row--active' : ''}`.trim()}
                        onClick={() => setSelectedFiscal(isSelected ? null : item)}
                        style={{ cursor: 'pointer' }}
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
                              <button type="button" onClick={() => handleOpenPdf(item)}
                                title="Descargar PDF"
                                className="row-action-icon row-action-icon--danger">
                                <FileText className="h-3 w-3" />
                              </button>
                            )}
                            {item.sunat_xml_url && (
                              <a href={item.sunat_xml_url} target="_blank" rel="noreferrer"
                                title="Descargar XML"
                                className="row-action-icon row-action-icon--info">
                                <Download className="h-3 w-3" />
                              </a>
                            )}
                            {waLink && (
                              <button type="button" onClick={() => handleOpenShareChannel(item, 'whatsapp')}
                                title="Enviar por WhatsApp"
                                className="row-action-icon row-action-icon--success">
                                <Send className="h-3 w-3" />
                              </button>
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
    <div className="proto-toolbar proto-toolbar-compact">
      <div className="proto-search-box">
        <Search className="h-4 w-4 text-[var(--text-tertiary)]" style={{ flexShrink: 0 }} />
        <input
          className="input-flat"
          style={{ flex: 1, background: 'transparent' }}
          placeholder="Buscar por cliente, número u orden..."
          value={search}
          onChange={(e) => onSearch(e.target.value)}
        />
      </div>
      <div className="proto-toolbar-actions">
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
    </div>
  );
}
