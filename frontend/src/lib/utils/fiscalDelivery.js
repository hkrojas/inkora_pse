export function fiscalDocumentId(response = {}) {
  const candidate = response.resource_id ?? response.document_id;
  if (!['number', 'string'].includes(typeof candidate)) return null;
  const id = Number(candidate);
  return Number.isSafeInteger(id) && id > 0 ? id : null;
}

export function isLinkedFiscalDocument(quote, document) {
  return Number(document?.id) === Number(quote?.linked_fiscal_document_id)
    && Number(document?.source_quote_id) === Number(quote?.id)
    && document?.document_kind === 'fiscal_document'
    && ['01', '03'].includes(document?.tipo_comprobante);
}
