export const SUMMARY_DETAIL_STATES = [
  { value: '1', label: '1 - Adicionar' },
  { value: '2', label: '2 - Modificar' },
  { value: '3', label: '3 - Anular' },
];

// Historical rows may say sent without a CDR. Only a response from the
// confirmation endpoint (or the new send endpoint) establishes acceptance.
export function summaryStatus(summary, confirmed = false) {
  if (summary.status === 'rejected') return 'rejected';
  if (summary.status === 'sent' && summary.success === true) return confirmed ? 'sent' : 'unverified';
  return 'pending';
}

export function summaryNumber(summary) {
  const sequence = String(summary.correlativo || summary._corr || '');
  if (/^RC-\d{8}-\d+(?:-\d+)?$/.test(sequence)) return sequence;
  if (/^\d{8}-\d+(?:-\d+)?$/.test(sequence)) return `RC-${sequence}`;
  const date = String(summary.fec_resumen || summary._fecha || summary.fec_generacion || '').slice(0, 10).replace(/-/g, '');
  const suffix = /^\d+$/.test(sequence) ? sequence.padStart(5, '0') : sequence;
  return date && sequence ? `RC-${date}-${suffix}` : sequence || '-';
}

export function summaryResultMessage(summary) {
  const status = summaryStatus(summary, true);
  if (status === 'sent') return { message: 'Resumen aceptado por SUNAT.', type: 'success' };
  if (status === 'rejected') return { message: summary.sunat_error || 'Resumen rechazado por SUNAT. Revisa el motivo antes de corregirlo.', type: 'error' };
  const ticket = summary.ticket ? ` Ticket: ${summary.ticket}.` : '';
  return { message: `Resumen pendiente de confirmación.${ticket} Consulta su estado; todavía no está aceptado.`, type: 'info' };
}

export function uncertainSummarySend(error) {
  return !error?.status || error.status >= 500;
}
