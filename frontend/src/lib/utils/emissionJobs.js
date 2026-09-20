const ACTIVE_STATUSES = new Set(['queued', 'processing', 'retry']);

const STATUS_LABELS = {
  queued: 'En cola fiscal',
  processing: 'Procesando',
  retry: 'Reintentando',
  contingency_pending: 'Reservado en contingencia',
  pending_confirmation: 'Pendiente de confirmación',
  succeeded: 'Aceptado por SUNAT',
  failed: 'Rechazado',
};

export function getEmissionJobLabel(status) {
  return STATUS_LABELS[String(status || '').toLowerCase()] || status || '';
}

export function isEmissionJobActive(status) {
  return ACTIVE_STATUSES.has(String(status || '').toLowerCase());
}

const GUIDE_CONSULT_LABELS = {
  queued: 'Consulta fiscal en cola',
  processing: 'Consultando Smart PSE',
  retry: 'Reintentando consulta',
  pending_confirmation: 'Resultado pendiente de conciliación',
  succeeded: 'Resultado fiscal conciliado',
  failed: 'Consulta fiscal sin resultado',
};

export function getGuideEmissionJobLabel(job = {}) {
  const status = String(job?.status || '').toLowerCase();
  if (job?.action === 'consult_guide') {
    return GUIDE_CONSULT_LABELS[status] || getEmissionJobLabel(status);
  }
  return {
    queued: 'En cola para SUNAT',
    processing: 'Enviando a SUNAT',
    retry: 'Reintentando emisión',
    pending_confirmation: 'Resultado pendiente de conciliación',
    contingency_pending: 'Emisión retenida por contingencia',
    succeeded: 'Aceptada por SUNAT',
    failed: 'Emisión fallida',
  }[status];
}

export function getGuideEmissionJobCompletion(job = {}) {
  const status = String(job?.status || '').toLowerCase();
  const isConsult = job?.action === 'consult_guide';
  if (status === 'succeeded') {
    return {
      message: isConsult
        ? 'Resultado fiscal conciliado. Revisa el estado y el CDR de la guía.'
        : 'Guía aceptada por SUNAT. El CDR está disponible.',
      toastType: 'success',
    };
  }
  if (status === 'pending_confirmation') {
    return {
      message: 'Smart PSE no devolvió un resultado definitivo. La guía no fue reenviada y conserva su reserva.',
      toastType: 'warning',
    };
  }
  if (isConsult) {
    return {
      message: job?.last_error || 'No se pudo completar la consulta fiscal. La guía no fue reenviada.',
      toastType: 'error',
    };
  }
  return {
    message: job?.last_error || 'La emisión no pudo completarse.',
    toastType: 'error',
  };
}

export function getEmissionOutcome(response = {}, documentLabel = 'Comprobante') {
  const jobStatus = String(response?.job_status || response?.status || '').toLowerCase();

  if (response?.deferred || jobStatus === 'contingency_pending') {
    return {
      kind: 'deferred',
      jobStatus: 'contingency_pending',
      message: `${documentLabel} reservada en contingencia. Queda pendiente de envío y validación fiscal.`,
      toastType: 'warning',
      shouldPoll: false,
      canShare: false,
    };
  }

  if (response?.pending_confirmation || jobStatus === 'pending_confirmation') {
    return {
      kind: 'pending_confirmation',
      jobStatus: 'pending_confirmation',
      message: `${documentLabel} pendiente de confirmación fiscal. No se volverá a enviar automáticamente para evitar duplicados.`,
      toastType: 'warning',
      shouldPoll: false,
      canShare: false,
    };
  }

  if (jobStatus === 'succeeded') {
    return {
      kind: 'accepted',
      jobStatus,
      message: `${documentLabel} aceptada por SUNAT.`,
      toastType: 'success',
      shouldPoll: false,
      canShare: true,
    };
  }

  return {
    kind: 'processing',
    jobStatus: jobStatus || 'queued',
    message: `${documentLabel} enviada a procesamiento fiscal. La aceptación de SUNAT aún está pendiente.`,
    toastType: 'info',
    shouldPoll: true,
    canShare: false,
  };
}
