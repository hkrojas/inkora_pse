import { useEffect, useMemo, useState } from 'react';
import Spinner from '../components/ui/Spinner';
import ColorPickerField from '../components/ui/ColorPickerField';
import { useToast } from '../components/ui/Toast';
import { tenant as tenantSvc } from '../services/tenant';
import { useAuth } from '../context/AuthContext';
import { getPaymentMethodPreview, getPaymentQrImageUrl, normalizePaymentMethods } from '../lib/utils/paymentMethods';
import FiscalDocPreview from '../components/documents/FiscalDocPreview';
import {
  DEFAULT_NOTE_1_COLOR,
  DEFAULT_NOTE_1_TEXT,
  DEFAULT_NOTE_2_COLOR,
  DEFAULT_NOTE_2_TEXT,
  parseTenantObservationDefaults,
  serializeTenantObservationDefaults,
} from '../lib/utils/pdfObservationDefaults';

const DEFAULT_PRIMARY_COLOR = '#004AAD';
const PDF_COLOR_PRESETS = ['#004AAD', '#2563EB', '#0F172A', '#14B8A6', '#F97316', '#EF4444', '#7C3AED'];
const NOTE_COLOR_PRESETS = ['#FF0000', '#DC2626', '#F97316', '#CA8A04', '#0F172A', '#2563EB'];

const SAMPLE_COMPANY = {
  name: 'IMPRESIONES INKORA S.A.C.',
  ruc: '20512345678',
  address: 'AV. INDUSTRIAL 342, ATE, LIMA',
  phone: '01 234-5678',
  email: 'ventas@inkora.pe',
};

const SAMPLE_CLIENT = {
  razon_social: 'ALIMENTOS PRIME S.A.C.',
  tipo_documento: '6',
  numero_documento: '20602259251',
  direccion: 'MZA. 03 LOTE 9 URB. CIUDAD DEL PESCADOR',
};

const SAMPLE_ITEMS_RAW = [
  { codigo: 'BOLKRAFT-12', descripcion: 'BOLSAS DE PAPEL KRAFT #12 CON IMPRESION A DOBLE CARA',    unidad: 'UND', cantidad: 1850, precio_unitario: 0.66 },
  { codigo: 'BOLKRAFT-25', descripcion: 'BOLSAS DE PAPEL KRAFT N 25 IMP. A UN COLOR',               unidad: 'UND', cantidad: 500,  precio_unitario: 1.00 },
  { codigo: 'STICK-05CM',  descripcion: 'STICKERS TROQUEL CIRCULAR 5CM FULL COLOR PLASTIFICADO',    unidad: 'UND', cantidad: 2000, precio_unitario: 0.18 },
];

const SAMPLE_FISCAL_ITEMS = SAMPLE_ITEMS_RAW.map((it) => {
  const valorUnitario = it.precio_unitario / 1.18;
  const valorVenta    = valorUnitario * it.cantidad;
  return {
    codigo:        it.codigo,
    descripcion:   it.descripcion,
    unidad:        it.unidad,
    cantidad:      it.cantidad,
    valorUnitario,
    precioUnitario: it.precio_unitario,
    descuento:     0,
    valorVenta,
  };
});

const SAMPLE_TOTALS = SAMPLE_FISCAL_ITEMS.reduce(
  (acc, it) => ({ subtotal: acc.subtotal + it.valorVenta, igv: acc.igv + (it.valorVenta * 0.18), total: acc.total + it.valorVenta * 1.18 }),
  { subtotal: 0, igv: 0, total: 0 },
);

const SAMPLE_ITEMS = SAMPLE_ITEMS_RAW.map((it) => ({ ...it, tipo_afectacion_igv: '10' }));

function buildDraftState(tenantData) {
  const defaults = parseTenantObservationDefaults(tenantData);
  return {
    primary_color: tenantData?.primary_color || DEFAULT_PRIMARY_COLOR,
    pdf_note_1: defaults.line1.text,
    pdf_note_1_color: defaults.line1.color,
    pdf_note_1_bold: defaults.line1.bold,
    pdf_note_2: defaults.line2.text,
    pdf_note_2_color: defaults.line2.color,
    pdf_note_2_bold: defaults.line2.bold,
  };
}

function getSafeColor(value, fallback) {
  return /^#([0-9A-Fa-f]{6})$/.test(String(value || '').trim()) ? value : fallback;
}

function formatMoney(value) {
  return Number(value || 0).toLocaleString('es-PE', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatQuantity(value) {
  const amount = Number(value || 0);
  return amount.toLocaleString('es-PE', {
    minimumFractionDigits: Number.isInteger(amount) ? 0 : 2,
    maximumFractionDigits: 2,
  });
}

function amountToWords(amount) {
  const units = ['CERO', 'UNO', 'DOS', 'TRES', 'CUATRO', 'CINCO', 'SEIS', 'SIETE', 'OCHO', 'NUEVE'];
  const specials = {
    10: 'DIEZ', 11: 'ONCE', 12: 'DOCE', 13: 'TRECE', 14: 'CATORCE', 15: 'QUINCE',
    16: 'DIECISEIS', 17: 'DIECISIETE', 18: 'DIECIOCHO', 19: 'DIECINUEVE', 20: 'VEINTE',
    21: 'VEINTIUNO', 22: 'VEINTIDOS', 23: 'VEINTITRES', 24: 'VEINTICUATRO', 25: 'VEINTICINCO',
    26: 'VEINTISEIS', 27: 'VEINTISIETE', 28: 'VEINTIOCHO', 29: 'VEINTINUEVE',
  };
  const tens = ['', '', '', 'TREINTA', 'CUARENTA', 'CINCUENTA', 'SESENTA', 'SETENTA', 'OCHENTA', 'NOVENTA'];
  const hundreds = ['', 'CIENTO', 'DOSCIENTOS', 'TRESCIENTOS', 'CUATROCIENTOS', 'QUINIENTOS', 'SEISCIENTOS', 'SETECIENTOS', 'OCHOCIENTOS', 'NOVECIENTOS'];

  const convertBelowHundred = (value) => {
    if (value < 10) return units[value];
    if (specials[value]) return specials[value];
    const ten = Math.floor(value / 10);
    const unit = value % 10;
    return unit === 0 ? tens[ten] : `${tens[ten]} Y ${units[unit]}`;
  };

  const convertBelowThousand = (value) => {
    if (value === 0) return 'CERO';
    if (value === 100) return 'CIEN';
    if (value < 100) return convertBelowHundred(value);
    const hundred = Math.floor(value / 100);
    const remainder = value % 100;
    return remainder === 0 ? hundreds[hundred] : `${hundreds[hundred]} ${convertBelowHundred(remainder)}`;
  };

  const convert = (value) => {
    if (value <= 0) return 'CERO';
    if (value < 1000) return convertBelowThousand(value);
    const millions = Math.floor(value / 1000000);
    const thousands = Math.floor((value % 1000000) / 1000);
    const remainder = value % 1000;
    const parts = [];

    if (millions > 0) parts.push(millions === 1 ? 'UN MILLON' : `${convert(millions)} MILLONES`);
    if (thousands > 0) parts.push(thousands === 1 ? 'MIL' : `${convert(thousands)} MIL`);
    if (remainder > 0) parts.push(convert(remainder));

    return parts.join(' ').trim();
  };

  const safeAmount = Math.round(Number(amount || 0) * 100) / 100;
  const integerPart = Math.floor(safeAmount);
  const decimalPart = String(Math.round((safeAmount - integerPart) * 100)).padStart(2, '0');
  const normalized = convert(integerPart)
    .replace(/\bVEINTIUNO\b/g, 'VEINTIUN')
    .replace(/\bTREINTA Y UNO\b/g, 'TREINTA Y UN')
    .replace(/\bCUARENTA Y UNO\b/g, 'CUARENTA Y UN')
    .replace(/\bCINCUENTA Y UNO\b/g, 'CINCUENTA Y UN')
    .replace(/\bSESENTA Y UNO\b/g, 'SESENTA Y UN')
    .replace(/\bSETENTA Y UNO\b/g, 'SETENTA Y UN')
    .replace(/\bOCHENTA Y UNO\b/g, 'OCHENTA Y UN')
    .replace(/\bNOVENTA Y UNO\b/g, 'NOVENTA Y UN')
    .replace(/\bUNO\b/g, 'UN');

  return `SON: ${normalized} CON ${decimalPart}/100 SOLES`;
}

function ObservationNoteCard({
  lineNumber,
  title,
  description,
  text,
  color,
  bold,
  onTextChange,
  onColorChange,
  onBoldChange,
}) {
  return (
    <div className="pdf-designer-note-card pdf-designer-note-card--enhanced">
      <div className="pdf-designer-note-header">
        <div className="pdf-designer-note-header-copy">
          <p className="page-kicker" style={{ margin: 0 }}>{`Linea ${lineNumber}`}</p>
          <h4 className="pdf-designer-note-title">{title}</h4>
          <p className="pdf-designer-note-description">{description}</p>
        </div>
      </div>

      <div className="pdf-designer-note-layout">
        <div className="pdf-designer-note-editor">
          <div className="pdf-designer-note-editor-head">
            <label className="label">Texto de la linea</label>
            <span className="pdf-designer-note-editor-hint">Vista en vivo</span>
          </div>

          <div className="pdf-designer-note-editor-frame" style={{ '--note-preview-color': color }}>
            <textarea
              className={`input pdf-designer-note-textarea pdf-designer-note-textarea--styled ${bold ? 'is-bold' : ''}`}
              rows={3}
              value={text}
              onChange={onTextChange}
              style={{ color }}
            />
          </div>
        </div>

        <div className="pdf-designer-note-settings">
          <div className="pdf-designer-note-settings-head">
            <span className="label">Formato</span>
            <button
              type="button"
              className={`pdf-designer-note-toggle-btn ${bold ? 'is-active' : ''}`}
              aria-pressed={bold}
              onClick={onBoldChange}
            >
              <span className="pdf-designer-note-toggle-btn-label">Negrita</span>
              <span className="pdf-designer-note-toggle-btn-state">{bold ? 'Activa' : 'Normal'}</span>
            </button>
          </div>

          <div className="pdf-designer-color-field">
            <ColorPickerField
              label={`Color linea ${lineNumber}`}
              value={color}
              onChange={onColorChange}
              fallback={lineNumber === 1 ? DEFAULT_NOTE_1_COLOR : DEFAULT_NOTE_2_COLOR}
              presets={NOTE_COLOR_PRESETS}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

function PdfPreviewSheet({ tenantData }) {
  const accentColor = getSafeColor(tenantData?.primary_color, DEFAULT_PRIMARY_COLOR);
  const companyName = SAMPLE_COMPANY.name;
  const companyRuc = SAMPLE_COMPANY.ruc;
  const companyAddress = SAMPLE_COMPANY.address;
  const companyPhone = SAMPLE_COMPANY.phone;
  const companyEmail = SAMPLE_COMPANY.email;
  const observationDefaults = parseTenantObservationDefaults(tenantData);
  const observationLines = [
    {
      text: observationDefaults.line1.text || DEFAULT_NOTE_1_TEXT,
      color: getSafeColor(observationDefaults.line1.color, DEFAULT_NOTE_1_COLOR),
      bold: observationDefaults.line1.bold,
    },
    {
      text: observationDefaults.line2.text || DEFAULT_NOTE_2_TEXT,
      color: getSafeColor(observationDefaults.line2.color, DEFAULT_NOTE_2_COLOR),
      bold: observationDefaults.line2.bold,
    },
  ].filter((line) => line.text?.trim());
  const paymentMethods = normalizePaymentMethods(tenantData?.bank_accounts);
  const paymentQrUrl = getPaymentQrImageUrl(tenantData);
  const items = SAMPLE_ITEMS.map((item) => {
    const quantity = Number(item.cantidad) || 0;
    const unitPrice = Number(item.precio_unitario) || 0;
    const total = quantity * unitPrice;
    const igv = (total * 0.18) / 1.18;
    const subtotal = total - igv;
    return {
      ...item,
      quantity,
      unitPrice,
      valorUnitario: quantity > 0 ? subtotal / quantity : 0,
      subtotal,
      total,
      igv,
    };
  });
  const totalGeneral = items.reduce((acc, item) => acc + item.total, 0);
  const totalIgv = items.reduce((acc, item) => acc + item.igv, 0);
  const subtotalGravado = totalGeneral - totalIgv;

  return (
    <div style={{ background: '#e5e7eb', padding: '16px', display: 'flex', justifyContent: 'center' }}>
      <div className="cotizacion-preview-sheet" style={{ '--quote-preview-accent': accentColor, width: '794px', minHeight: '1123px', background: '#fff', boxShadow: '0 2px 16px rgba(0,0,0,0.18)', padding: '32px 36px', display: 'flex', flexDirection: 'column' }}>
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
            <div className="cotizacion-preview-company-meta">{companyAddress}</div>
            {companyEmail && <div className="cotizacion-preview-company-meta">{companyEmail}</div>}
            {companyPhone && <div className="cotizacion-preview-company-meta">{companyPhone}</div>}
          </div>

          <div className="cotizacion-preview-docbox">
            {companyRuc && <div className="cotizacion-preview-docbox-ruc">RUC {companyRuc}</div>}
            <div className="cotizacion-preview-docbox-title">COTIZACION</div>
            <div className="cotizacion-preview-docbox-number">COT-000037</div>
          </div>
        </div>

        <div className="cotizacion-preview-section-line" />

        <div className="cotizacion-preview-client">
          <div className="cotizacion-preview-client-grid">
            <div className="cotizacion-preview-client-label">Señores:</div>
            <div className="cotizacion-preview-client-value">{SAMPLE_CLIENT.razon_social}</div>
            <div className="cotizacion-preview-client-label">Emisión:</div>
            <div className="cotizacion-preview-client-value">26/10/2025</div>

            <div className="cotizacion-preview-client-label">RUC:</div>
            <div className="cotizacion-preview-client-value">{SAMPLE_CLIENT.numero_documento}</div>
            <div className="cotizacion-preview-client-label">Moneda:</div>
            <div className="cotizacion-preview-client-value">SOLES</div>

            <div className="cotizacion-preview-client-label">Dirección:</div>
            <div className="cotizacion-preview-client-value">{SAMPLE_CLIENT.direccion}</div>
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
              {items.map((item, index) => (
                <tr key={`${item.descripcion}-${index}`}>
                  <td>{index + 1}</td>
                  <td>{`${formatQuantity(item.quantity)} ${item.unidad}`}</td>
                  <td>{item.codigo}</td>
                  <td>{item.descripcion}</td>
                  <td>S/ {formatMoney(item.valorUnitario)}</td>
                  <td>S/ {formatMoney(item.unitPrice)}</td>
                  <td>S/ {formatMoney(item.subtotal)}</td>
                  <td>S/ {formatMoney(item.total)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="cotizacion-preview-totals">
          <div className="cotizacion-preview-total-row">
            <span>OP. GRAVADAS:</span>
            <span>S/ {formatMoney(subtotalGravado)}</span>
          </div>
          <div className="cotizacion-preview-total-row">
            <span>IGV (18%):</span>
            <span>S/ {formatMoney(totalIgv)}</span>
          </div>
          <div className="cotizacion-preview-total-row is-strong">
            <span>IMPORTE TOTAL:</span>
            <span>S/ {formatMoney(totalGeneral)}</span>
          </div>
        </div>

        <div className="cotizacion-preview-amount">
          <div className="cotizacion-preview-amount-line">{amountToWords(totalGeneral)}</div>
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
            <strong>Escanea para pagar esta cotizacion.</strong>
            <p>QR compatible con la billetera digital configurada por la empresa.</p>
            <p><span>Condicion de pago:</span> Credito a 30 dias</p>

            {observationLines.map((line, index) => (
              <p
                key={`pdf-design-note-${index}`}
                className={`cotizacion-preview-note ${line.bold ? 'cotizacion-preview-note--primary' : ''}`}
                style={{ color: line.color }}
              >
                {line.text}
              </p>
            ))}

            {paymentMethods.length > 0 && (
              <div className="cotizacion-preview-bank">
                <div className="cotizacion-preview-bank-title">Datos para la transferencia</div>
                <div className="cotizacion-preview-bank-line">Beneficiario: {companyName.toUpperCase()}</div>
                {paymentMethods.slice(0, 2).map((method, index) => {
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

        <div className="cotizacion-preview-bottom">
          <span>Documento comercial sin valor fiscal.</span>
          <span>{companyEmail || companyPhone || companyName}</span>
        </div>
      </div>
    </div>
  );
}

function FiscalDesignerPreview({ tenantData }) {
  const accentColor = getSafeColor(tenantData?.primary_color, DEFAULT_PRIMARY_COLOR);
  return (
    <FiscalDocPreview
      accentColor={accentColor}
      company={SAMPLE_COMPANY}
      client={{ razon_social: SAMPLE_CLIENT.razon_social, tipo_documento_label: 'RUC', numero_documento: SAMPLE_CLIENT.numero_documento, direccion: SAMPLE_CLIENT.direccion }}
      docInfo={{ tipoLabel: 'FACTURA', serie: 'FFA1', numero: '000001', fecha_emision: '20/04/2026', fecha_vencimiento: '', moneda_texto: 'SOLES', condicion_pago_label: 'CONTADO', medio_pago: 'EFECTIVO', observaciones: '' }}
      items={SAMPLE_FISCAL_ITEMS}
      totals={SAMPLE_TOTALS}
      bankAccounts={tenantData?.bank_accounts}
    />
  );
}

export default function PdfDesignerPage() {
  const { user } = useAuth();
  const toast = useToast();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [tenantData, setTenantData] = useState(null);
  const [draft, setDraft] = useState(() => buildDraftState(null));
  const [previewTab, setPreviewTab] = useState('cotizacion');

  useEffect(() => {
    tenantSvc.get()
      .then((response) => {
        setTenantData(response);
        setDraft(buildDraftState(response));
      })
      .catch(() => toast('No se pudo cargar el diseño del PDF. Revisa tu conexión e inténtalo nuevamente.', 'error'))
      .finally(() => setLoading(false));
  }, []);

  const previewTenant = useMemo(() => ({
    ...tenantData,
    ...draft,
    pdf_note_2: serializeTenantObservationDefaults({
      line1: {
        text: draft.pdf_note_1,
        color: draft.pdf_note_1_color,
        bold: draft.pdf_note_1_bold,
      },
      line2: {
        text: draft.pdf_note_2,
        color: draft.pdf_note_2_color,
        bold: draft.pdf_note_2_bold,
      },
    }),
  }), [tenantData, draft]);

  const setField = (key) => (valueOrEvent) => {
    const value = typeof valueOrEvent === 'string' ? valueOrEvent : valueOrEvent.target.value;
    setDraft((current) => ({ ...current, [key]: value }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload = {
        primary_color: draft.primary_color,
        pdf_note_1: draft.pdf_note_1,
        pdf_note_1_color: draft.pdf_note_1_color,
        pdf_note_2: serializeTenantObservationDefaults({
          line1: {
            text: draft.pdf_note_1,
            color: draft.pdf_note_1_color,
            bold: draft.pdf_note_1_bold,
          },
          line2: {
            text: draft.pdf_note_2,
            color: draft.pdf_note_2_color,
            bold: draft.pdf_note_2_bold,
          },
        }),
      };

      const updated = await tenantSvc.update(payload);
      setTenantData(updated);
      setDraft(buildDraftState(updated));
      toast('Diseño PDF actualizado');
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="page-shell pdf-designer-shell">
      <div className="pdf-designer-grid">
        <section className="ink-table-card pdf-designer-panel">
          <div className="pdf-designer-panel-header">
            <div>
              <p className="page-kicker" style={{ margin: 0 }}>Plantilla comercial</p>
              <h2 className="pdf-designer-panel-title">Editor de PDF</h2>
              <p className="pdf-designer-panel-copy">
                Define el color principal de tabla, cuadros y lineas, ademas de las observaciones por defecto.
              </p>
            </div>
            <button type="button" onClick={handleSave} disabled={saving} className="btn-primary pdf-designer-save">
              {saving && <Spinner size="sm" />} Guardar diseño
            </button>
          </div>

          <div className="pdf-designer-section">
            <div className="pdf-designer-section-head">
              <h3>Apariencia</h3>
              <p>Este color controla la tabla, los cuadros del encabezado y las lineas del documento.</p>
            </div>
            <div className="pdf-designer-color-row">
              <div className="pdf-designer-color-field">
                <ColorPickerField
                  label="Color principal del PDF"
                  value={draft.primary_color}
                  onChange={setField('primary_color')}
                  fallback={DEFAULT_PRIMARY_COLOR}
                  presets={PDF_COLOR_PRESETS}
                />
              </div>
            </div>
          </div>

          <div className="pdf-designer-section">
            <div className="pdf-designer-section-head">
              <h3>Observaciones por defecto</h3>
              <p>Se aplican por defecto al crear nuevas cotizaciones y alimentan la vista previa del documento.</p>
            </div>

            <div className="pdf-designer-note-stack">
              <ObservationNoteCard
                lineNumber={1}
                title="Destacada"
                description="Mensaje principal del pie del PDF. Ideal para condiciones comerciales o avisos de cobro."
                text={draft.pdf_note_1}
                color={draft.pdf_note_1_color}
                bold={draft.pdf_note_1_bold}
                onTextChange={setField('pdf_note_1')}
                onColorChange={setField('pdf_note_1_color')}
                onBoldChange={() => setDraft((current) => ({ ...current, pdf_note_1_bold: !current.pdf_note_1_bold }))}
              />

              <ObservationNoteCard
                lineNumber={2}
                title="Secundaria"
                description="Complementa la nota principal. Sirve para aclaraciones, exclusiones o recordatorios adicionales."
                text={draft.pdf_note_2}
                color={draft.pdf_note_2_color}
                bold={draft.pdf_note_2_bold}
                onTextChange={setField('pdf_note_2')}
                onColorChange={setField('pdf_note_2_color')}
                onBoldChange={() => setDraft((current) => ({ ...current, pdf_note_2_bold: !current.pdf_note_2_bold }))}
              />
            </div>
          </div>

          <div className="pdf-designer-section pdf-designer-section--hint">
            <div className="pdf-designer-section-head">
              <h3>Medios de cobro</h3>
              <p>Las cuentas bancarias y billeteras digitales se administran solo desde Configuracion. Esta vista previa usa lo que ya este guardado alli.</p>
            </div>
          </div>
        </section>

        <aside className="pdf-designer-preview-panel">
          <div className="ink-table-card pdf-designer-preview-card">
            <div className="pdf-designer-preview-head">
              <div>
                <p className="page-kicker" style={{ margin: 0 }}>Vista previa</p>
                <h2 className="pdf-designer-panel-title">Cambios en tiempo real</h2>
              </div>
              <div style={{ display: 'flex', gap: '4px', background: 'var(--bg-surface-2)', borderRadius: 0, padding: '3px' }}>
                <button
                  type="button"
                  onClick={() => setPreviewTab('cotizacion')}
                  style={{
                    padding: '4px 12px',
                    fontSize: '11px',
                    fontWeight: previewTab === 'cotizacion' ? 700 : 400,
                    borderRadius: '4px',
                    border: 'none',
                    cursor: 'pointer',
                    background: previewTab === 'cotizacion' ? 'var(--bg-surface)' : 'transparent',
                    color: previewTab === 'cotizacion' ? 'var(--text-primary)' : 'var(--text-tertiary)',
                    boxShadow: previewTab === 'cotizacion' ? 'var(--shadow-brut-sm)' : 'none',
                    transition: 'all 0.15s',
                  }}
                >
                  Cotización
                </button>
                <button
                  type="button"
                  onClick={() => setPreviewTab('fiscal')}
                  style={{
                    padding: '4px 12px',
                    fontSize: '11px',
                    fontWeight: previewTab === 'fiscal' ? 700 : 400,
                    borderRadius: '4px',
                    border: 'none',
                    cursor: 'pointer',
                    background: previewTab === 'fiscal' ? 'var(--bg-surface)' : 'transparent',
                    color: previewTab === 'fiscal' ? 'var(--text-primary)' : 'var(--text-tertiary)',
                    boxShadow: previewTab === 'fiscal' ? 'var(--shadow-brut-sm)' : 'none',
                    transition: 'all 0.15s',
                  }}
                >
                  Factura / Boleta
                </button>
              </div>
            </div>
            <div className="pdf-designer-preview-frame">
              <div className="pdf-designer-preview-stage">
                {previewTab === 'cotizacion'
                  ? <PdfPreviewSheet tenantData={previewTenant} />
                  : <FiscalDesignerPreview tenantData={previewTenant} />}
              </div>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
