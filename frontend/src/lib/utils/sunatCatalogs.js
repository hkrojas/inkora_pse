export const PRODUCT_NAME_MAX_LENGTH = 160;
export const PRODUCT_DESCRIPTION_MAX_LENGTH = 1000;
export const PRODUCT_INTERNAL_CODE_MAX_LENGTH = 30;

export const SUNAT_UNIT_OPTIONS = [
  { value: 'NIU', label: 'NIU - Unidad (bienes)' },
  { value: 'ZZ', label: 'ZZ - Servicio' },
  { value: 'KGM', label: 'KGM - Kilogramo' },
  { value: 'MTR', label: 'MTR - Metro' },
  { value: 'MTK', label: 'MTK - Metro cuadrado' },
  { value: 'MLL', label: 'MLL - Millares' },
  { value: 'RM', label: 'RM - Resma' },
  { value: 'BG', label: 'BG - Bolsa' },
  { value: 'BX', label: 'BX - Caja' },
  { value: 'SET', label: 'SET - Juego' },
  { value: 'PK', label: 'PK - Paquete' },
  { value: 'C62', label: 'C62 - Pieza' },
];

export const SUNAT_TAX_AFFECTATION_OPTIONS = [
  { value: '10', label: '10 - Gravado' },
  { value: '20', label: '20 - Exonerado' },
  { value: '30', label: '30 - Inafecto' },
];

export const SUNAT_UNIT_CODES = new Set(SUNAT_UNIT_OPTIONS.map((item) => item.value));
export const SUNAT_TAX_AFFECTATION_CODES = new Set(
  SUNAT_TAX_AFFECTATION_OPTIONS.map((item) => item.value),
);

export function normalizeInternalProductCode(value) {
  return String(value || '').trim().toUpperCase();
}

export function isValidInternalProductCode(value) {
  if (!value) return true;
  return /^[A-Z0-9._/-]+$/.test(normalizeInternalProductCode(value));
}

export function normalizeSunatUnitCode(value) {
  const normalized = String(value || 'NIU').trim().toUpperCase();
  return normalized === 'MIL' ? 'MLL' : normalized;
}

export function isValidSunatUnitCode(value) {
  return SUNAT_UNIT_CODES.has(normalizeSunatUnitCode(value));
}

export function isValidTaxAffectationCode(value) {
  return SUNAT_TAX_AFFECTATION_CODES.has(String(value || '10').trim());
}

export function isTaxedAffectation(value) {
  return String(value || '10') === '10';
}

