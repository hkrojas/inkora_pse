export function fiscalTrackingState(job = {}, documentStatus) {
  const status = job.status;
  const isVoid = job.action === 'void_fiscal_document';
  const messages = {
    queued: 'Procesando', processing: 'Procesando', retry: 'Procesando',
    contingency_pending: 'Procesando',
    pending_confirmation: 'Procesando',
    failed: 'Requiere atención. Revisa el resultado del comprobante.',
  };
  if (status === 'succeeded') return {
    label: isVoid ? 'Baja aceptada por SUNAT'
      : documentStatus === 'emitted' ? 'Aceptado por SUNAT' : 'Trabajo completado. Verificando resultado fiscal.',
    poll: false, terminal: true,
  };
  return { label: messages[status] || 'Sin trabajo fiscal registrado',
    poll: ['queued', 'processing', 'retry', 'contingency_pending', 'pending_confirmation'].includes(status),
    terminal: status === 'failed' };
}
