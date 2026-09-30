const DAY = 86400000;

export function limaToday(now = new Date()) {
  const parts = new Intl.DateTimeFormat('en', {
    timeZone: 'America/Lima', year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(now);
  const part = (name) => parts.find((item) => item.type === name).value;
  return `${part('year')}-${part('month')}-${part('day')}`;
}

function dateValue(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value || '')) return NaN;
  const time = Date.parse(`${value}T00:00:00Z`);
  return Number.isFinite(time) && new Date(time).toISOString().slice(0, 10) === value ? time : NaN;
}

export function rangeDays(start, end) {
  return Math.round((dateValue(end) - dateValue(start)) / DAY) + 1;
}

export function validateDashboardRange(start, end, today) {
  if (!Number.isFinite(dateValue(start)) || !Number.isFinite(dateValue(end))) return 'Elige una fecha de inicio y una de fin.';
  if (start > end) return 'La fecha de inicio debe ser anterior o igual a la de fin.';
  if (end > today) return 'La fecha de fin no puede estar en el futuro.';
  if (rangeDays(start, end) > 367) return 'Elige hasta 367 días o usa Todo el historial.';
  return '';
}

export function resolveDashboardRange(filters, today) {
  const { preset, month, start, end } = filters;
  if (preset === 'all') return null;
  if (preset === 'custom') return { start, end };
  if (preset === 'week' || preset === 'thirty') {
    const days = preset === 'week' ? 7 : 30;
    return { start: new Date(dateValue(today) - (days - 1) * DAY).toISOString().slice(0, 10), end: today };
  }
  const selectedMonth = preset === 'month' ? month : today.slice(0, 7);
  const first = `${selectedMonth}-01`;
  if (!Number.isFinite(dateValue(first)) || first > today) return { start: '', end: '' };
  const last = new Date(dateValue(first));
  last.setUTCMonth(last.getUTCMonth() + 1);
  last.setUTCDate(0);
  return { start: first, end: [last.toISOString().slice(0, 10), today].sort()[0] };
}

export function dashboardPeriodParams(filters, today) {
  const range = resolveDashboardRange(filters, today);
  if (!range) return { period_scope: 'all', history_scope: 'period', group_by: 'month' };
  return {
    desde: range.start, hasta: range.end, period_scope: 'selected', history_scope: 'period',
    group_by: rangeDays(range.start, range.end) > 93 ? 'month' : filters.group,
  };
}

export function chartPointBounds(point) {
  if (point.period_start && point.period_end) return { desde: point.period_start, hasta: point.period_end };
  if (point.date) return { desde: point.date, hasta: point.date };
  const month = String(point.month).padStart(2, '0');
  const last = new Date(Date.UTC(point.year, point.month, 0)).getUTCDate();
  return { desde: `${point.year}-${month}-01`, hasta: `${point.year}-${month}-${String(point.is_partial && point.cutoff_day ? point.cutoff_day : last).padStart(2, '0')}` };
}
