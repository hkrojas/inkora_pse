function fmtMoney(value) {
  return Number(value || 0).toLocaleString('es-PE', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function fmtQty(value) {
  const n = Number(value || 0);
  const hasDecimals = Math.abs(n - Math.trunc(n)) > 0.0001;
  return n.toLocaleString('es-PE', {
    minimumFractionDigits: hasDecimals ? 2 : 0,
    maximumFractionDigits: 3,
  });
}

function amountToWords(amount) {
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
  const hundreds = ['', 'CIENTO', 'DOSCIENTOS', 'TRESCIENTOS', 'CUATROCIENTOS', 'QUINIENTOS', 'SEISCIENTOS', 'SETECIENTOS', 'OCHOCIENTOS', 'NOVECIENTOS'];
  const sub100 = (v) => {
    if (v < 10) return units[v];
    if (specials[v]) return specials[v];
    const t = Math.floor(v / 10);
    const u = v % 10;
    return u === 0 ? tens[t] : `${tens[t]} Y ${units[u]}`;
  };
  const sub1000 = (v) => {
    if (v === 0) return 'CERO';
    if (v === 100) return 'CIEN';
    if (v < 100) return sub100(v);
    const h = Math.floor(v / 100);
    const r = v % 100;
    return r === 0 ? hundreds[h] : `${hundreds[h]} ${sub100(r)}`;
  };
  const convert = (v) => {
    if (v <= 0) return 'CERO';
    if (v < 1000) return sub1000(v);
    const mil = Math.floor(v / 1000);
    const rem = v % 1000;
    const parts = [];
    if (mil > 0) parts.push(mil === 1 ? 'MIL' : `${convert(mil)} MIL`);
    if (rem > 0) parts.push(convert(rem));
    return parts.join(' ').trim();
  };
  const safe = Math.round(Number(amount || 0) * 100) / 100;
  const int = Math.floor(safe);
  const dec = String(Math.round((safe - int) * 100)).padStart(2, '0');
  const words = convert(int)
    .replace(/\bVEINTIUNO\b/g, 'VEINTIUN')
    .replace(/\bUNO\b/g, 'UN')
    .replace(/\b(TREINTA|CUARENTA|CINCUENTA|SESENTA|SETENTA|OCHENTA|NOVENTA) Y UNO\b/g, '$1 Y UN');
  return `SON: ${words} CON ${dec}/100 SOLES`;
}

function getDocumentTitle(tipoLabel = 'FACTURA') {
  const upper = tipoLabel.toUpperCase();
  if (upper.includes('BOLETA')) return ['BOLETA DE VENTA', 'ELECTRONICA'];
  if (upper.includes('NOTA CREDITO') || upper.includes('NOTA DE CRÉDITO')) return ['NOTA DE CRÉDITO', 'ELECTRONICA'];
  if (upper.includes('NOTA DEBITO') || upper.includes('NOTA DE DÉBITO')) return ['NOTA DE DÉBITO', 'ELECTRONICA'];
  return ['FACTURA', 'ELECTRONICA'];
}

function formatDocumentNumber(serie, numero) {
  const raw = String(numero || '000001');
  const normalized = /^\d+$/.test(raw) ? raw.padStart(6, '0') : raw;
  return `${serie || 'F001'}-${normalized}`;
}

function FiscalQrMark() {
  return (
    <svg className="fiscal-preview-qr-mark" viewBox="0 0 7 7" aria-hidden="true">
      <rect x="0" y="0" width="3" height="3" />
      <rect x="1" y="1" width="1" height="1" fill="#fff" />
      <rect x="4" y="0" width="3" height="3" />
      <rect x="5" y="1" width="1" height="1" fill="#fff" />
      <rect x="0" y="4" width="3" height="3" />
      <rect x="1" y="5" width="1" height="1" fill="#fff" />
      <rect x="4" y="3" width="1" height="1" />
      <rect x="3" y="4" width="1" height="1" />
      <rect x="5" y="4" width="2" height="1" />
      <rect x="4" y="5" width="1" height="2" />
      <rect x="6" y="6" width="1" height="1" />
    </svg>
  );
}

export default function FiscalDocPreview({
  accentColor = '#2563eb',
  company = {},
  client = {},
  docInfo = {},
  items = [],
  totals = { subtotal: 0, igv: 0, total: 0 },
}) {
  const [docTitle1, docTitle2] = getDocumentTitle(docInfo.tipoLabel);
  const documentNumber = formatDocumentNumber(docInfo.serie, docInfo.numero);
  const companyName = company.name || 'EMPRESA';
  const companyEmail = company.email || '';
  const companyPhone = company.phone || '';
  const companyRuc = company.ruc || '—';
  const clientDocLabel = client.tipo_documento_label || 'RUC';
  const displayItems = items.length > 0 ? items : [{
    codigo: 'ITEM-001',
    descripcion: 'Sin items agregados',
    unidad: 'UND',
    cantidad: 0,
    valorUnitario: 0,
    precioUnitario: 0,
    valorVenta: 0,
  }];

  return (
    <div className="document-preview-canvas">
      <div className="cotizacion-preview-sheet fiscal-preview-sheet" style={{ '--quote-preview-accent': accentColor }}>
        <div className="cotizacion-preview-header">
          <div className="cotizacion-preview-logo-block">
            {company.logoUrl ? (
              <img className="cotizacion-preview-logo-img" src={company.logoUrl} alt={`Logo ${companyName}`} />
            ) : (
              <div className="cotizacion-preview-logo-fallback">{companyName}</div>
            )}
          </div>

          <div className="cotizacion-preview-company">
            <div className="cotizacion-preview-company-name">{companyName.toUpperCase()}</div>
            {companyRuc && <div className="cotizacion-preview-company-meta">RUC {companyRuc}</div>}
            {company.address && <div className="cotizacion-preview-company-meta">{company.address}</div>}
            {companyEmail && <div className="cotizacion-preview-company-meta">Email: {companyEmail}</div>}
            {companyPhone && <div className="cotizacion-preview-company-meta">Teléfono: {companyPhone}</div>}
          </div>

          <div className="cotizacion-preview-docbox">
            <div className="cotizacion-preview-docbox-title">
              <span>{docTitle1}</span>
              <span>{docTitle2}</span>
            </div>
            <div className="cotizacion-preview-docbox-number">{documentNumber}</div>
            <div className="cotizacion-preview-docbox-ruc">RUC: {companyRuc}</div>
          </div>
        </div>

        <div className="cotizacion-preview-section-line" />

        <div className="cotizacion-preview-client">
          <div className="cotizacion-preview-client-grid">
            <div className="cotizacion-preview-client-label">Señores:</div>
            <div className="cotizacion-preview-client-value">{client.razon_social || '—'}</div>
            <div className="cotizacion-preview-client-label">Emisión:</div>
            <div className="cotizacion-preview-client-value">{docInfo.fecha_emision || '—'}</div>

            <div className="cotizacion-preview-client-label">{clientDocLabel}:</div>
            <div className="cotizacion-preview-client-value">{client.numero_documento || '—'}</div>
            <div className="cotizacion-preview-client-label">Moneda:</div>
            <div className="cotizacion-preview-client-value">{docInfo.moneda_texto || 'SOLES'}</div>

            <div className="cotizacion-preview-client-label">Dirección:</div>
            <div className="cotizacion-preview-client-value">{client.direccion || '—'}</div>
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
              {displayItems.map((item, index) => {
                const quantity = Number(item.cantidad || 0);
                const total = Number(item.precioUnitario || 0) * quantity;
                return (
                  <tr key={`${item.descripcion || 'item'}-${index}`}>
                    <td>{index + 1}</td>
                    <td>{fmtQty(quantity)} {item.unidad || 'UND'}</td>
                    <td>{item.codigo || `ITEM-${String(index + 1).padStart(3, '0')}`}</td>
                    <td>{item.descripcion || '—'}</td>
                    <td>S/ {fmtMoney(item.valorUnitario)}</td>
                    <td>S/ {fmtMoney(item.precioUnitario)}</td>
                    <td>S/ {fmtMoney(item.valorVenta)}</td>
                    <td>S/ {fmtMoney(total)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div className="cotizacion-preview-totals">
          <div className="cotizacion-preview-total-row">
            <span>OP. GRAVADAS:</span>
            <span>S/ {fmtMoney(totals.subtotal)}</span>
          </div>
          <div className="cotizacion-preview-total-row">
            <span>IGV (18%):</span>
            <span>S/ {fmtMoney(totals.igv)}</span>
          </div>
          <div className="cotizacion-preview-total-row is-strong">
            <span>IMPORTE TOTAL:</span>
            <span>S/ {fmtMoney(totals.total)}</span>
          </div>
        </div>

        <div className="cotizacion-preview-amount">
          <div className="cotizacion-preview-amount-line">{amountToWords(totals.total)}</div>
        </div>

        <div className="cotizacion-preview-footer fiscal-preview-footer">
          <div className="cotizacion-preview-qr-frame fiscal-preview-qr-frame">
            <FiscalQrMark />
          </div>

          <div className="cotizacion-preview-footer-divider" />

          <div className="cotizacion-preview-footer-copy">
            <strong>Representación impresa de la {docTitle1} {docTitle2}.</strong>
            <p>El usuario puede consultar su validez en SUNAT Virtual:</p>
            <p className="fiscal-preview-sunat-url">www.sunat.gob.pe</p>
            {docInfo.observaciones && (
              <p className="cotizacion-preview-note">{docInfo.observaciones}</p>
            )}
          </div>
        </div>

        <div className="cotizacion-preview-bottom">
          <span>Puedes descargar el XML, CDR y representación impresa desde nuestro portal.</span>
          <span>{companyEmail || companyPhone || companyName}</span>
        </div>
      </div>
    </div>
  );
}
