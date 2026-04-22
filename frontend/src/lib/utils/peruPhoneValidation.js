export function digitsOnly(value) {
  return String(value || '').replace(/\D+/g, '');
}

export function normalizePeruMobileInput(value) {
  const digits = digitsOnly(value);

  if (!digits) return '';

  if (digits.startsWith('51')) {
    return digits.slice(2, 11);
  }

  return digits.slice(0, 9);
}

export function validatePeruMobilePhone(value, label = 'Celular') {
  const normalized = normalizePeruMobileInput(value);

  if (!normalized) return null;
  if (normalized.length !== 9) return `${label} debe tener 9 digitos.`;
  if (!normalized.startsWith('9')) return `${label} debe iniciar en 9.`;

  return null;
}

export function isValidPeruMobilePhone(value) {
  return !validatePeruMobilePhone(value);
}
