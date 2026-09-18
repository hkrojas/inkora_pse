export function buildFiscalListQuery({ page = 1, search = '', filters = {} } = {}) {
  const params = new URLSearchParams({ skip: String((Math.max(1, page) - 1) * 15), limit: '15', tab: 'all' });
  const mapping = { tipo: 'tipo_comprobante', docReceptor: 'documento_cliente', razonSocial: 'razon_social',
    serie: 'serie', numero: 'numero', moneda: 'moneda', formaPago: 'forma_pago', desde: 'desde', hasta: 'hasta' };
  if (search.trim()) params.set('q', search.trim());
  for (const [key, name] of Object.entries(mapping)) {
    const value = String(filters[key] || '').trim();
    if (value && value !== 'all') params.set(name, value);
  }
  return `?${params.toString()}`;
}
