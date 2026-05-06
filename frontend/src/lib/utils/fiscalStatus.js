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

export function getSmartPseGreStatusMeta(tenant = {}) {
  const hasCredentials = Boolean(tenant?.has_smartpse_gre_credentials);
  const status = String(tenant?.smartpse_gre_status || '').toLowerCase();

  if (!hasCredentials) {
    return {
      label: 'no configurado',
      badgeVariant: 'default',
      tone: 'neutral',
      canCheck: false,
      description: 'Faltan credenciales GRE cifradas.',
    };
  }

  if (status === 'ok') {
    return {
      label: 'ok',
      badgeVariant: 'success',
      tone: 'ok',
      canCheck: true,
      description: 'Credenciales listas para emitir GRE.',
    };
  }

  if (status === 'invalid') {
    return {
      label: 'inválido',
      badgeVariant: 'danger',
      tone: 'bad',
      canCheck: true,
      description: 'Revisar usuario SOL, clave, client ID o client secret.',
    };
  }

  return {
    label: 'sin verificar',
    badgeVariant: 'warning',
    tone: 'warn',
    canCheck: true,
    description: 'Credenciales guardadas; falta validarlas.',
  };
}
