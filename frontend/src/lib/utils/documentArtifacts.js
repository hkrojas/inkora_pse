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

export function hasFiscalDownload(doc = {}, type) {
  const verificationRequired = Boolean(doc.provider_verification_status);
  const providerVerified = doc.provider_verification_status === 'verified';
  if (type === 'pdf') {
    return doc.estado !== 'anulada' && (doc.has_deliverable_fiscal_xml === undefined || doc.has_deliverable_fiscal_xml
      || (doc.sunat_accepted && Boolean(doc.sunat_pdf_url)));
  }
  if (type === 'xml' && doc.has_deliverable_fiscal_xml) return true;
  if (type === 'cdr' && doc.provider_verification_status === 'rejected') return Boolean(doc.has_sunat_cdr || doc.sunat_cdr_url);
  if (verificationRequired && !providerVerified) {
    return false;
  }
  if (type === 'xml') {
    return Boolean(doc.has_sunat_xml || doc.sunat_xml_url);
  }
  if (type === 'cdr') {
    return Boolean(doc.has_sunat_cdr || doc.sunat_cdr_url);
  }
  return false;
}

export function getFiscalDocumentStatus(item = {}) {
  const authoritative = {
    voided: { label: 'ANULADO', variant: 'danger', kind: 'voided' },
    draft: { label: 'BORRADOR', variant: 'default', kind: 'draft' },
    emitted: { label: 'ACEPTADO', variant: 'success', kind: 'ok' },
    rejected: { label: 'RECHAZADO', variant: 'danger', kind: 'error', tooltip: item.sunat_error },
    pending_confirmation: { label: 'PROCESANDO', variant: 'warning', kind: 'pending', tooltip: 'Inkora verifica automáticamente el resultado del comprobante.' },
    pending: { label: 'PROCESANDO', variant: 'warning', kind: 'pending', tooltip: 'Verificando el resultado del comprobante.' },
  };
  if (authoritative[item.fiscal_status]) return authoritative[item.fiscal_status];
  if (item.estado === 'anulada') {
    return { label: 'ANULADO', variant: 'danger', kind: 'voided' };
  }
  if (item.provider_verification_status === 'pending_confirmation' || /\b1033\b/.test(item.sunat_error || '')) {
    return authoritative.pending_confirmation;
  }
  if (item.sunat_error) {
    return item.provider_verification_status === 'rejected' ? authoritative.rejected : authoritative.pending_confirmation;
  }
  if (item.provider_verification_status && item.provider_verification_status !== 'verified') {
    return {
      label: 'NO VERIFICADO',
      variant: 'warning',
      kind: 'pending',
      tooltip: item.provider_verification_error || 'Smart PSE no confirmo este documento.',
    };
  }
  if (
    (item.sunat_accepted || item.has_sunat_cdr || item.sunat_cdr_url)
    && (!item.provider_verification_status || item.provider_verification_status === 'verified')
  ) {
    return { label: 'ACEPTADO', variant: 'success', kind: 'ok' };
  }
  if (item.document_kind !== 'quotation') {
    return { label: 'PENDIENTE', variant: 'warning', kind: 'pending' };
  }
  return null;
}
