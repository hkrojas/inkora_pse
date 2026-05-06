import { normalizePeruMobileInput, validatePeruMobilePhone } from './peruPhoneValidation';

export const FISCAL_DOC_TYPE_OPTIONS = [
  { value: '6', label: 'RUC' },
  { value: '1', label: 'DNI' },
  { value: '4', label: 'Carnet de extranjeria' },
  { value: '7', label: 'Pasaporte' },
  { value: '0', label: 'Doc. trib. no dom. s/ RUC' },
  { value: 'A', label: 'Cedula diplomatica' },
];

const DOC_TYPE_META = {
  '6': { label: 'RUC', placeholder: 'Ej. 20100200300', maxLength: 11, inputMode: 'numeric', lookupEnabled: true },
  '1': { label: 'DNI', placeholder: 'Ej. 12345678', maxLength: 8, inputMode: 'numeric', lookupEnabled: true },
  '4': { label: 'Carnet de extranjeria', placeholder: 'Ej. CE1234567', maxLength: 15, inputMode: 'text', lookupEnabled: false },
  '7': { label: 'Pasaporte', placeholder: 'Ej. P1234567', maxLength: 15, inputMode: 'text', lookupEnabled: false },
  '0': { label: 'Doc. trib. no dom. s/ RUC', placeholder: 'Ej. EXT123456', maxLength: 15, inputMode: 'text', lookupEnabled: false },
  A: { label: 'Cedula diplomatica', placeholder: 'Ej. CD123456', maxLength: 15, inputMode: 'text', lookupEnabled: false },
};

export function getFiscalDocMeta(tipoDocumento) {
  return DOC_TYPE_META[tipoDocumento] || {
    label: 'Documento',
    placeholder: 'Numero de documento',
    maxLength: 15,
    inputMode: 'text',
    lookupEnabled: false,
  };
}

export function getFiscalDocLabel(tipoDocumento) {
  return getFiscalDocMeta(tipoDocumento).label;
}

export function normalizeFiscalDocumentNumber(tipoDocumento, rawValue) {
  const value = String(rawValue || '').trim().toUpperCase().replace(/\s+/g, '');
  if (tipoDocumento === '6' || tipoDocumento === '1') {
    return value.replace(/\D/g, '').slice(0, getFiscalDocMeta(tipoDocumento).maxLength);
  }
  return value.slice(0, getFiscalDocMeta(tipoDocumento).maxLength);
}

export function normalizeFiscalUbigeo(rawValue) {
  return String(rawValue || '').replace(/\D/g, '').slice(0, 6);
}

export function validateFiscalDocumentNumber(tipoDocumento, numeroDocumento) {
  const value = String(numeroDocumento || '').trim();
  if (!value) return 'Numero de documento es obligatorio.';
  if (tipoDocumento === '6' && !/^\d{11}$/.test(value)) return 'RUC debe tener exactamente 11 digitos.';
  if (tipoDocumento === '1' && !/^\d{8}$/.test(value)) return 'DNI debe tener exactamente 8 digitos.';
  if (value.length < 3) return 'Numero de documento demasiado corto.';
  return undefined;
}

export function validateFiscalUbigeo(value) {
  const ubigeo = String(value || '').trim();
  if (!ubigeo) return undefined;
  if (!/^\d{6}$/.test(ubigeo)) return 'Ubigeo debe tener exactamente 6 digitos.';
  return undefined;
}

export function buildFiscalClientErrors(form = {}) {
  const errors = {
    numero_documento: validateFiscalDocumentNumber(form.tipo_documento, form.numero_documento),
    razon_social: !String(form.razon_social || '').trim() ? 'Razon social / Nombre es obligatorio.' : undefined,
    direccion: undefined,
    ubigeo: validateFiscalUbigeo(form.ubigeo),
    email: undefined,
    telefono: validatePeruMobilePhone(form.telefono, 'Telefono / WhatsApp') || undefined,
  };

  if (form.email?.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
    errors.email = 'Email no tiene un formato valido.';
  }

  if (form.tipo_documento === '6') {
    if (!String(form.direccion || '').trim()) {
      errors.direccion = 'Direccion fiscal es obligatoria para clientes con RUC.';
    }
    if (!String(form.ubigeo || '').trim()) {
      errors.ubigeo = 'Ubigeo es obligatorio para clientes con RUC.';
    }
  }

  return errors;
}

export function getFiscalClientErrorMessage(form = {}) {
  const errors = buildFiscalClientErrors(form);
  return Object.values(errors).find(Boolean) || null;
}

export function normalizeFiscalClientForm(initial = {}) {
  return {
    tipo_documento: initial.tipo_documento || '6',
    numero_documento: normalizeFiscalDocumentNumber(initial.tipo_documento || '6', initial.numero_documento || ''),
    razon_social: String(initial.razon_social || '').trim(),
    nombre_comercial: String(initial.nombre_comercial || '').trim(),
    direccion: String(initial.direccion || '').trim(),
    ubigeo: normalizeFiscalUbigeo(initial.ubigeo || ''),
    email: String(initial.email || '').trim(),
    telefono: normalizePeruMobileInput(initial.telefono || initial.whatsapp || ''),
  };
}
