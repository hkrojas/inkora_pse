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
      method: 'getBlob',
      path: `/cotizaciones/${doc.id}/pdf/download`,
    };
  }
  return {
    method: 'blob',
    path: `/facturacion/${type}`,
    body: { comprobante_id: doc.id },
  };
}

export function hasFiscalDownload(doc = {}, type) {
  if (type === 'pdf') {
    if (doc.estado === 'anulada') return false;
    if (doc.pdf_artifact_status === 'failed') return false;
    if (doc.pdf_artifact_status === 'pending' && !doc.sunat_pdf_url) return false;
    return true;
  }
  if (type === 'xml') {
    return Boolean(doc.has_sunat_xml || doc.sunat_xml_url);
  }
  if (type === 'cdr') {
    if (doc.cdr_artifact_status === 'pending') return false;
    return Boolean(doc.has_sunat_cdr || doc.sunat_cdr_url);
  }
  return false;
}

export function getFiscalArtifactStatus(doc = {}, type) {
  const status = type === 'pdf' ? doc.pdf_artifact_status : doc.cdr_artifact_status;
  const hasArtifact = type === 'pdf'
    ? Boolean(doc.sunat_pdf_url)
    : Boolean(doc.has_sunat_cdr || doc.sunat_cdr_url);
  if (status === 'ready' || hasArtifact) return { label: `${type.toUpperCase()} listo`, variant: 'success', kind: 'ready' };
  if (status === 'failed') return { label: `${type.toUpperCase()} falló`, variant: 'error', kind: 'failed' };
  if (status === 'pending') return { label: `${type.toUpperCase()} pendiente`, variant: 'warning', kind: 'pending' };
  return null;
}

export function canRetryFiscalArtifacts(doc = {}) {
  return Boolean(
    doc?.id
    && doc.estado !== 'anulada'
    && (
      doc.provider_verification_status === 'verified'
      || doc.provider_verification_status == null
    )
    && (
      doc.cdr_artifact_status === 'failed'
      || doc.pdf_artifact_status === 'failed'
      || (doc.has_sunat_cdr && !doc.sunat_pdf_url)
    )
  );
}

export function getFiscalDocumentStatus(item = {}) {
  if (item.estado === 'anulada') {
    return { label: 'ANULADO', variant: 'danger', kind: 'voided' };
  }
  if (item.sunat_error) {
    return { label: 'RECHAZADO', variant: 'danger', kind: 'error', tooltip: item.sunat_error };
  }
  if (item.provider_verification_status === 'failed') {
    return {
      label: 'RECHAZADO',
      variant: 'danger',
      kind: 'error',
      tooltip: 'No se pudo validar este comprobante.',
    };
  }
  if (item.provider_verification_status === 'pending') {
    return { label: 'PENDIENTE', variant: 'warning', kind: 'pending', tooltip: 'Validacion pendiente.' };
  }
  const providerVerified = item.provider_verification_status === 'verified' || item.provider_verification_status == null;
  if (providerVerified && (item.sunat_accepted || item.has_sunat_cdr || item.sunat_cdr_url)) {
    return { label: 'ACEPTADO', variant: 'success', kind: 'ok' };
  }
  if (item.document_kind !== 'quotation') {
    return { label: 'PENDIENTE', variant: 'warning', kind: 'pending' };
  }
  return null;
}
