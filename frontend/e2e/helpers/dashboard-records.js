export function recordsPayload(params, { total = 18, totalAmount = '7777.00' } = {}) {
  const skip = Number(params.get('skip') || 0);
  const measure = params.get('measure') || 'document';
  const limit = Number(params.get('limit') || 15);
  const end = params.get('hasta') || '2026-09-28';
  const baseAmount = total > 0 ? Math.floor(Number(totalAmount) * 100 / total) / 100 : 0;
  return {
    meta: {
      period: { start: params.get('desde') || '2026-09-01', end, label: '' },
      currency: 'PEN', measure,
      client_id: params.get('client_id') ? Number(params.get('client_id')) : null,
      product_id: params.get('product_id') ? Number(params.get('product_id')) : null,
    },
    total, total_amount: totalAmount, skip, limit,
    items: Array.from({ length: Math.max(0, Math.min(limit, total - skip)) }, (_, offset) => ({
      document_id: 9000 + skip + offset,
      reference: `F001-${String(skip + offset + 1).padStart(6, '0')}`,
      tipo_comprobante: '01', document_kind: 'fiscal_document',
      issued_at: `${end}T12:00:00`,
      client_name: params.get('client_id') ? `Cliente #${params.get('client_id')}` : 'Comprador real de prueba',
      amount: String(skip + offset === total - 1 ? Number(totalAmount) - baseAmount * (total - 1) : baseAmount), quantity: measure === 'product' ? '2' : null,
      unit: measure === 'product' ? params.get('product_unit') || 'NIU' : null,
      state: offset === 0 ? 'pendiente' : 'facturada',
    })),
  };
}
