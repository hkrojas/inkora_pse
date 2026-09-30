import test from 'node:test';
import assert from 'node:assert/strict';
import { limaToday, resolveDashboardRange, dashboardPeriodParams, validateDashboardRange, chartPointBounds } from './dashboardPeriods.js';

test('uses the business date in Lima across the UTC midnight boundary', () => {
  assert.equal(limaToday(new Date('2026-09-30T02:00:00Z')), '2026-09-29');
});
test('seven days includes today and crosses the year correctly', () => {
  assert.deepEqual(resolveDashboardRange({ preset: 'week' }, '2026-01-03'), { start: '2025-12-28', end: '2026-01-03' });
});
test('specific month includes leap day and current month stops today', () => {
  assert.deepEqual(resolveDashboardRange({ preset: 'month', month: '2024-02' }, '2026-09-29'), { start: '2024-02-01', end: '2024-02-29' });
  assert.deepEqual(resolveDashboardRange({ preset: 'current' }, '2026-09-29'), { start: '2026-09-01', end: '2026-09-29' });
});
test('validates actual dates, future dates, reversed dates and maximum range', () => {
  for (const [start, end] of [['2026-02-30', '2026-03-01'], ['2026-09-01', '2026-09-30'], ['2026-09-29', '2026-09-01'], ['2024-01-01', '2026-09-29']]) {
    assert.ok(validateDashboardRange(start, end, '2026-09-29'));
  }
  assert.equal(validateDashboardRange('2026-09-29', '2026-09-29', '2026-09-29'), '');
});
test('long ranges and all history use months, short ranges keep chosen grouping', () => {
  assert.equal(dashboardPeriodParams({ preset: 'custom', start: '2026-01-01', end: '2026-09-29', group: 'day' }, '2026-09-29').group_by, 'month');
  assert.deepEqual(dashboardPeriodParams({ preset: 'all', group: 'day' }, '2026-09-29'), { period_scope: 'all', history_scope: 'period', group_by: 'month' });
  assert.equal(dashboardPeriodParams({ preset: 'week', group: 'day' }, '2026-09-29').group_by, 'day');
});
test('drilldown preserves exact partial boundaries and a daily point', () => {
  assert.deepEqual(chartPointBounds({ year: 2026, month: 9, period_start: '2026-09-23', period_end: '2026-09-29' }), { desde: '2026-09-23', hasta: '2026-09-29' });
  assert.deepEqual(chartPointBounds({ date: '2026-09-29' }), { desde: '2026-09-29', hasta: '2026-09-29' });
});
