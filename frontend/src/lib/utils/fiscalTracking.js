export function fiscalTrackingState(job = {}, documentStatus) {
  const status = job.status;
  const isVoid = job.action === 'void_fiscal_document';
  const messages = {
    queued: 'En cola fiscal', processing: 'Procesando con el proveedor', retry: 'Reintento automático en curso',
    contingency_pending: 'Retenido por contingencia; aún no se envía',
    pending_confirmation: 'Resultado por conciliar. No se reenviará.',
    failed: 'El trabajo no pudo completarse. Revisa el motivo; no implica rechazo fiscal definitivo.',
  };
  if (status === 'succeeded') return {
    label: isVoid ? 'Baja procesada. Actualizando resultado fiscal.'
      : documentStatus === 'emitted' ? 'Aceptado por SUNAT' : 'Trabajo completado. Verificando resultado fiscal.',
    poll: false, terminal: true,
  };
  return { label: messages[status] || 'Sin trabajo fiscal registrado',
    poll: ['queued', 'processing', 'retry', 'contingency_pending'].includes(status),
    terminal: ['failed', 'pending_confirmation'].includes(status) };
}
