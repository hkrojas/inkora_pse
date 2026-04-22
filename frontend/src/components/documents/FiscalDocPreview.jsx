import { getPaymentMethodPreview, normalizePaymentMethods } from '../../lib/utils/paymentMethods';

// ─── Helpers ─────────────────────────────────────────────────────────────────

function fmtMoney(value) {
  return Number(value || 0).toLocaleString('es-PE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function fmtQty(value) {
  const n = Number(value || 0);
  return n.toLocaleString('es-PE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function amountToWords(amount) {
  const units    = ['CERO','UNO','DOS','TRES','CUATRO','CINCO','SEIS','SIETE','OCHO','NUEVE'];
  const specials = {10:'DIEZ',11:'ONCE',12:'DOCE',13:'TRECE',14:'CATORCE',15:'QUINCE',16:'DIECISEIS',17:'DIECISIETE',18:'DIECIOCHO',19:'DIECINUEVE',20:'VEINTE',21:'VEINTIUNO',22:'VEINTIDOS',23:'VEINTITRES',24:'VEINTICUATRO',25:'VEINTICINCO',26:'VEINTISEIS',27:'VEINTISIETE',28:'VEINTIOCHO',29:'VEINTINUEVE'};
  const tens     = ['','','','TREINTA','CUARENTA','CINCUENTA','SESENTA','SETENTA','OCHENTA','NOVENTA'];
  const hundreds = ['','CIENTO','DOSCIENTOS','TRESCIENTOS','CUATROCIENTOS','QUINIENTOS','SEISCIENTOS','SETECIENTOS','OCHOCIENTOS','NOVECIENTOS'];
  const sub100   = (v) => { if (v < 10) return units[v]; if (specials[v]) return specials[v]; const t=Math.floor(v/10),u=v%10; return u===0?tens[t]:`${tens[t]} Y ${units[u]}`; };
  const sub1000  = (v) => { if (v===0) return 'CERO'; if (v===100) return 'CIEN'; if (v<100) return sub100(v); const h=Math.floor(v/100),r=v%100; return r===0?hundreds[h]:`${hundreds[h]} ${sub100(r)}`; };
  const convert  = (v) => { if (v<=0) return 'CERO'; if (v<1000) return sub1000(v); const mil=Math.floor(v/1000),rem=v%1000; const parts=[]; if (mil>0) parts.push(mil===1?'MIL':`${convert(mil)} MIL`); if (rem>0) parts.push(convert(rem)); return parts.join(' ').trim(); };
  const safe = Math.round(Number(amount||0)*100)/100;
  const int  = Math.floor(safe);
  const dec  = String(Math.round((safe-int)*100)).padStart(2,'0');
  const words = convert(int).replace(/\bVEINTIUNO\b/g,'VEINTIUN').replace(/\bUNO\b/g,'UN').replace(/\b(TREINTA|CUARENTA|CINCUENTA|SESENTA|SETENTA|OCHENTA|NOVENTA) Y UNO\b/g,'$1 Y UN');
  return `SON: ${words} CON ${dec}/100 SOLES`;
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Props:
 *   accentColor    string   hex color (e.g. '#004AAD')
 *   company        { name, ruc, address, phone, email }
 *   client         { razon_social, tipo_documento_label, numero_documento, direccion }
 *   docInfo        { tipoLabel, serie, numero, fecha_emision, fecha_vencimiento,
 *                    moneda_texto, condicion_pago_label, medio_pago, observaciones }
 *   items          [{ codigo, descripcion, unidad, cantidad,
 *                     valorUnitario, precioUnitario, descuento, valorVenta }]
 *   totals         { subtotal, igv, total }
 *   bankAccounts   raw bank_accounts string from tenantData
 */
export default function FiscalDocPreview({
  accentColor = '#004AAD',
  company = {},
  client = {},
  docInfo = {},
  items = [],
  totals = { subtotal: 0, igv: 0, total: 0 },
  bankAccounts,
}) {
  const paymentMethods  = normalizePaymentMethods(bankAccounts);
  const condPagoLabel   = docInfo.condicion_pago_label || 'CONTADO';
  const tipoLabelUpper  = (docInfo.tipoLabel || 'FACTURA').toUpperCase();
  const [tipoLine1, tipoLine2] = tipoLabelUpper.includes('BOLETA')
    ? ['BOLETA DE', 'VENTA']
    : tipoLabelUpper.includes('NOTA CREDITO') || tipoLabelUpper.includes('NOTA DE CRÉDITO')
    ? ['NOTA DE', 'CRÉDITO']
    : tipoLabelUpper.includes('NOTA DEBITO') || tipoLabelUpper.includes('NOTA DE DÉBITO')
    ? ['NOTA DE', 'DÉBITO']
    : ['FACTURA', null];

  return (
    <div style={{ background: '#e5e7eb', padding: '16px', display: 'flex', justifyContent: 'center' }}>
    <div style={{ width: '794px', minHeight: '1123px', background: '#fff', boxShadow: '0 2px 16px rgba(0,0,0,0.18)', fontFamily: 'Arial, Helvetica, sans-serif', fontSize: '10px', color: '#111', padding: '32px 36px', lineHeight: 1.5, display: 'flex', flexDirection: 'column' }}>

      {/* ══ HEADER ══════════════════════════════════════════════════════════ */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.2fr 1fr', gap: '16px', alignItems: 'center', marginBottom: '14px' }}>

        {/* Logo */}
        <div style={{ background: '#f1f5f9', border: '1px solid #e2e8f0', minHeight: '90px', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '12px', textAlign: 'center' }}>
          <span style={{ fontWeight: 700, fontSize: '11px', color: '#475569' }}>{company.name || 'EMPRESA'}</span>
        </div>

        {/* Company info */}
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontWeight: 700, fontSize: '13px', marginBottom: '5px', lineHeight: 1.3 }}>{company.name || '—'}</div>
          {company.address && <div style={{ fontSize: '10px', color: '#444', marginBottom: '2px' }}>{company.address}</div>}
          {company.phone   && <div style={{ fontSize: '10px', color: '#444', marginBottom: '2px' }}>Teléfono: {company.phone}</div>}
          {company.email   && <div style={{ fontSize: '10px', color: '#444' }}>{company.email}</div>}
        </div>

        {/* Document box — big & prominent */}
        <div style={{ border: `2px solid ${accentColor}`, borderRadius: '3px', padding: '12px 14px', textAlign: 'center' }}>
          <div style={{ fontSize: '22px', fontWeight: 900, letterSpacing: '1px', color: '#111', lineHeight: 1.1 }}>
            {tipoLine1}
          </div>
          {tipoLine2 && (
            <div style={{ fontSize: '22px', fontWeight: 900, letterSpacing: '1px', color: '#111', lineHeight: 1.1 }}>
              {tipoLine2}
            </div>
          )}
          <div style={{ fontSize: '11px', letterSpacing: '1.5px', color: '#555', margin: '4px 0 2px' }}>
            ELECTRÓNICA
          </div>
          <div style={{ height: '1px', background: accentColor, margin: '6px 0' }} />
          <div style={{ fontSize: '10px', color: '#444', marginBottom: '2px' }}>R.U.C.: {company.ruc || '—'}</div>
          <div style={{ fontSize: '16px', fontWeight: 700, color: '#111', marginTop: '4px' }}>
            {docInfo.serie || 'F001'}-{String(docInfo.numero || '000001').padStart(6, '0')}
          </div>
        </div>
      </div>

      {/* Divider */}
      <div style={{ height: '1.5px', background: accentColor, marginBottom: '10px' }} />

      {/* ══ CLIENT SECTION ══════════════════════════════════════════════════ */}
      <div style={{ border: '1px solid #d1d5db', borderRadius: '2px', padding: '8px 12px', marginBottom: '12px', fontSize: '10px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '3px 24px' }}>
          <div><strong>Razón Social:</strong> {client.razon_social || '—'}</div>
          <div><strong>{client.tipo_documento_label || 'RUC'}:</strong> {client.numero_documento || '—'}</div>
          <div><strong>Fecha Emisión:</strong> {docInfo.fecha_emision || '—'}</div>
          <div><strong>Dirección:</strong> {client.direccion || '—'}</div>
          <div><strong>Tipo Moneda:</strong> {docInfo.moneda_texto || 'SOLES'}</div>
          {docInfo.fecha_vencimiento && (
            <div><strong>Fecha Vencimiento:</strong> {docInfo.fecha_vencimiento}</div>
          )}
        </div>
      </div>

      {/* ══ ITEMS TABLE ═════════════════════════════════════════════════════ */}
      <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: '10px', fontSize: '9px' }}>
        <thead>
          <tr style={{ background: accentColor, color: '#fff' }}>
            <th style={{ padding: '5px 4px', textAlign: 'center', fontWeight: 700, width: '4%' }}>ITEM</th>
            <th style={{ padding: '5px 4px', textAlign: 'center', fontWeight: 700, width: '10%' }}>CANTIDAD</th>
            <th style={{ padding: '5px 4px', textAlign: 'center', fontWeight: 700, width: '10%' }}>CÓDIGO</th>
            <th style={{ padding: '5px 4px', textAlign: 'left',   fontWeight: 700 }}>DESCRIPCIÓN</th>
            <th style={{ padding: '5px 4px', textAlign: 'right',  fontWeight: 700, width: '10%' }}>V/U</th>
            <th style={{ padding: '5px 4px', textAlign: 'right',  fontWeight: 700, width: '10%' }}>P/U</th>
            <th style={{ padding: '5px 4px', textAlign: 'right',  fontWeight: 700, width: '10%' }}>SUBTOTAL</th>
            <th style={{ padding: '5px 4px', textAlign: 'right',  fontWeight: 700, width: '10%' }}>TOTAL</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, i) => (
            <tr key={i} style={{ borderBottom: '1px solid #e5e7eb' }}>
              <td style={{ padding: '4px', textAlign: 'center' }}>{i + 1}</td>
              <td style={{ padding: '4px', textAlign: 'center' }}>{fmtQty(item.cantidad)} {item.unidad || 'NIU'}</td>
              <td style={{ padding: '4px', textAlign: 'center' }}>{item.codigo || `ITEM-${String(i+1).padStart(3,'0')}`}</td>
              <td style={{ padding: '4px', textAlign: 'left' }}>{item.descripcion}</td>
              <td style={{ padding: '4px', textAlign: 'right' }}>S/ {fmtMoney(item.valorUnitario)}</td>
              <td style={{ padding: '4px', textAlign: 'right' }}>S/ {fmtMoney(item.precioUnitario)}</td>
              <td style={{ padding: '4px', textAlign: 'right' }}>S/ {fmtMoney(item.valorVenta)}</td>
              <td style={{ padding: '4px', textAlign: 'right' }}>S/ {fmtMoney(item.precioUnitario * item.cantidad)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Divider */}
      <div style={{ height: '1px', background: '#d1d5db', marginBottom: '10px' }} />

      {/* ══ AMOUNT + TOTALS ROW ══════════════════════════════════════════════ */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: '16px', alignItems: 'start', marginBottom: '10px' }}>

        {/* Left — amount in words */}
        <div>
          <div style={{ fontWeight: 700, fontSize: '10px', marginBottom: '8px' }}>{amountToWords(totals.total)}</div>

          {/* Observaciones / Información adicional */}
          <div style={{ marginTop: '6px' }}>
            <div style={{ fontWeight: 700, fontSize: '10px', borderBottom: '1px solid #d1d5db', paddingBottom: '2px', marginBottom: '4px' }}>
              Información Adicional
            </div>
            {docInfo.observaciones
              ? <div style={{ fontSize: '9px', color: '#555' }}>{docInfo.observaciones}</div>
              : <div style={{ fontSize: '9px', color: '#aaa' }}>—</div>}
          </div>

          {/* Forma de pago */}
          <div style={{ marginTop: '10px', fontSize: '10px' }}>
            <strong>Forma de Pago:</strong> {docInfo.condicion_pago_label ? condPagoLabel.charAt(0).toUpperCase() + condPagoLabel.slice(1).toLowerCase() : 'Contado'}
          </div>
        </div>

        {/* Right — totals */}
        <div style={{ minWidth: '200px', fontSize: '10px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '32px', padding: '3px 0', borderBottom: '1px solid #e5e7eb' }}>
            <span style={{ color: '#555' }}>Op. Gravadas:</span>
            <strong>S/ {fmtMoney(totals.subtotal)}</strong>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '32px', padding: '3px 0', borderBottom: '1px solid #e5e7eb' }}>
            <span style={{ color: '#555' }}>I.G.V.:</span>
            <strong>S/ {fmtMoney(totals.igv)}</strong>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '32px', padding: '3px 0', borderTop: '1.5px solid #111', marginTop: '2px' }}>
            <span style={{ fontWeight: 700 }}>Precio Venta:</span>
            <strong>S/ {fmtMoney(totals.total)}</strong>
          </div>
        </div>
      </div>

      {/* ══ SPACER — empuja el footer al fondo ══════════════════════════════ */}
      <div style={{ flex: 1 }} />

      {/* ══ BANK DATA ═══════════════════════════════════════════════════════ */}
      {paymentMethods.length > 0 && (
        <div style={{ marginTop: '16px', fontSize: '9px' }}>
          <div style={{ fontWeight: 700, marginBottom: '3px' }}>
            Datos para la Transferencia Beneficiario: {company.name}
          </div>
          {paymentMethods.map((method, i) => {
            const preview = getPaymentMethodPreview(method);
            if (!preview) return null;
            return (
              <div key={i} style={{ marginTop: '4px' }}>
                <div style={{ fontWeight: 700 }}>{preview.title}</div>
                {preview.lines.map((line, j) => <div key={j}>{line}</div>)}
              </div>
            );
          })}
        </div>
      )}

      {/* ══ LEGAL FOOTER ════════════════════════════════════════════════════ */}
      <div style={{ marginTop: '20px' }}>
        {/* Top dividers */}
        <div style={{ height: '1.5px', background: accentColor, marginBottom: '2px' }} />
        <div style={{ height: '1.5px', background: accentColor, marginBottom: '6px' }} />

        {/* Line 1 */}
        <div style={{ fontSize: '9px', marginBottom: '2px' }}>
          Representación Impresa de la {tipoLine1}{tipoLine2 ? ` ${tipoLine2}` : ''} Electrónica
        </div>

        {/* Line 2 — resolución + página */}
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '9px', marginBottom: '8px' }}>
          <span>Autorizado mediante Resolución Nro 0340050005929 / SUNAT</span>
          <span>Pag. 1 / 1</span>
        </div>

        {/* Bottom row — QR + consulta + proveedor */}
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '16px' }}>
          {/* QR */}
          <div style={{ width: '80px', height: '80px', border: '1px solid #bbb', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, fontSize: '9px', color: '#999', flexDirection: 'column', gap: '4px' }}>
            <svg width="48" height="48" viewBox="0 0 7 7" style={{ imageRendering: 'pixelated' }}>
              <rect x="0" y="0" width="3" height="3" fill="#111" />
              <rect x="1" y="1" width="1" height="1" fill="#fff" />
              <rect x="4" y="0" width="3" height="3" fill="#111" />
              <rect x="5" y="1" width="1" height="1" fill="#fff" />
              <rect x="0" y="4" width="3" height="3" fill="#111" />
              <rect x="1" y="5" width="1" height="1" fill="#fff" />
              <rect x="4" y="3" width="1" height="1" fill="#111" />
              <rect x="3" y="4" width="1" height="1" fill="#111" />
              <rect x="5" y="4" width="2" height="1" fill="#111" />
              <rect x="4" y="5" width="1" height="2" fill="#111" />
              <rect x="6" y="6" width="1" height="1" fill="#111" />
            </svg>
            <span>QR</span>
          </div>

          {/* Consulta */}
          <div style={{ flex: 1, fontSize: '9px' }}>
            <div style={{ marginBottom: '3px' }}>Para consultar el comprobante ingrese a:</div>
            <div style={{ color: accentColor }}>https://api.apis.net.pe/verComprobante</div>
            <div style={{ color: accentColor }}>https://api.apis.net.pe/portal</div>
          </div>

          {/* Proveedor */}
          <div style={{ textAlign: 'right', fontSize: '8.5px', flexShrink: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', justifyContent: 'flex-end', marginBottom: '4px' }}>
              <div style={{ border: '1.5px solid #999', borderRadius: '50%', width: '28px', height: '28px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '7px', fontWeight: 700, color: '#555' }}>API</div>
              <div style={{ textAlign: 'left', fontSize: '8px' }}>
                <div style={{ fontWeight: 700 }}>Proveedor</div>
                <div>autorizado por</div>
              </div>
              <div style={{ fontWeight: 900, fontSize: '13px', color: '#1a56db', letterSpacing: '-0.5px' }}>SUNAT</div>
            </div>
            <div style={{ color: accentColor }}>www.apis.net.pe</div>
          </div>
        </div>
      </div>

    </div>
    </div>
  );
}
