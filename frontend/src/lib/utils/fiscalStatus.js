export function getGuideStatusMeta(item = {}) {
  const status = String(item?.estado || '').toLowerCase();

  if (status === 'pendiente_smartpse') {
    return {
      tabKey: 'pending',
      label: 'Pendiente Smart PSE',
      tone: 'warn',
      badgeVariant: 'warning',
      provider: 'smartpse',
      helper: 'XML firmado; CDR pendiente.',
    };
  }

  if (status === 'cancelled' || status === 'cancelada' || status === 'cancelado') {
    return {
      tabKey: 'cancelled',
      label: 'Borrador cancelado',
      tone: 'neutral',
      badgeVariant: 'cancelled',
      provider: null,
      helper: 'Las cantidades reservadas fueron liberadas.',
    };
  }

  if (status.includes('anulad')) {
    return {
      tabKey: 'voided',
      label: 'Anulada',
      tone: 'bad',
      badgeVariant: 'error',
      provider: null,
      helper: '',
    };
  }

  if (status.includes('transit')) {
    return {
      tabKey: 'transit',
      label: 'En transito',
      tone: 'info',
      badgeVariant: 'info',
      provider: null,
      helper: '',
    };
  }

  if (status.includes('emitid')) {
    return {
      tabKey: 'emitted',
      label: 'Emitida',
      tone: 'ok',
      badgeVariant: 'success',
      provider: null,
      helper: '',
    };
  }

  return {
    tabKey: 'pending',
    label: 'Pendiente',
    tone: 'warn',
    badgeVariant: 'warning',
    provider: null,
    helper: '',
  };
}

const RESERVATION_STATUS_LABELS = {
  provisional: 'Provisional',
  active: 'Activa',
  covered: 'Cubierta por GRE',
  released: 'Liberada',
};

const DISPATCH_STATUS_LABELS = {
  provisional: 'Preparación provisional',
  draft: 'Borrador con reserva',
  guide_pending: 'GRE pendiente de resultado',
  guide_accepted: 'GRE aceptada',
  guide_rejected: 'GRE rechazada',
  departed: 'Salida confirmada',
  cancelled: 'Borrador cancelado',
  blocked: 'Bloqueado',
};

export function getDispatchReservationLabel(status) {
  const normalized = String(status || '').trim().toLowerCase();
  return RESERVATION_STATUS_LABELS[normalized] || 'No aplica';
}

export function getDispatchStatusLabel(status) {
  const normalized = String(status || '').trim().toLowerCase();
  return DISPATCH_STATUS_LABELS[normalized] || 'Sin estado operativo';
}

export function getSmartPseGreStatusMeta(tenant = {}) {
  const hasCredentials = Boolean(tenant?.has_smartpse_gre_credentials);
  const status = String(tenant?.smartpse_gre_status || '').toLowerCase();

  if (!hasCredentials) {
    return {
      label: 'Pendiente',
      badgeVariant: 'default',
      tone: 'neutral',
      canCheck: false,
      description: 'Falta completar la conexión para emitir guías.',
    };
  }

  if (status === 'ok') {
    return {
      label: 'Operativo',
      badgeVariant: 'success',
      tone: 'ok',
      canCheck: true,
      description: 'La conexión para emitir guías está verificada.',
    };
  }

  if (status === 'invalid') {
    return {
      label: 'Revisar',
      badgeVariant: 'danger',
      tone: 'bad',
      canCheck: true,
      description: 'Smart PSE rechazó una o más credenciales de guías.',
    };
  }

  return {
    label: 'Sin verificar',
    badgeVariant: 'warning',
    tone: 'warn',
    canCheck: true,
    description: 'Las credenciales están guardadas y todavía no se han comprobado.',
  };
}
