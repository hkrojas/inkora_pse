export function buildQueryString(params) {
  if (!params) return '';
  if (typeof params === 'string') return params;

  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      query.set(key, String(value));
    }
  });

  const text = query.toString();
  return text ? `?${text}` : '';
}

export function getPageCount(total, limit) {
  const safeTotal = Number.isFinite(Number(total)) ? Number(total) : 0;
  const safeLimit = Number.isFinite(Number(limit)) && Number(limit) > 0 ? Number(limit) : 1;
  return Math.max(1, Math.ceil(safeTotal / safeLimit));
}
