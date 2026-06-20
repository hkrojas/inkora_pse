export function formatFiscalDate(value) {
  if (!value) return '';
  const text = String(value).trim();
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(text);
  if (match) {
    return `${match[3]}/${match[2]}/${match[1]}`;
  }
  const parsed = new Date(text);
  if (Number.isNaN(parsed.getTime())) return '';
  return parsed.toLocaleDateString('es-PE');
}

export function buildFiscalDownloadRequest(doc, type) {
  if (type === 'pdf') {
    return {
      method: 'get',
      path: `/cotizaciones/${doc.id}/pdf`,
    };
  }
  return {
    method: 'blob',
    path: `/facturacion/${type}`,
    body: { comprobante_id: doc.id },
  };
}

export function getFiscalDocumentStatus(item = {}) {
  if (item.estado === 'anulada') {
    return { label: 'ANULADO', variant: 'danger', kind: 'voided' };
  }
  if (item.sunat_error) {
    return { label: 'RECHAZADO', variant: 'danger', kind: 'error', tooltip: item.sunat_error };
  }
  if (item.sunat_accepted || item.sunat_cdr_url) {
    return { label: 'ACEPTADO', variant: 'success', kind: 'ok' };
  }
  if (item.document_kind !== 'quotation') {
    return { label: 'PENDIENTE', variant: 'warning', kind: 'pending' };
  }
  return null;
}
