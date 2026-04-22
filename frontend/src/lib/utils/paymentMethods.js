import { normalizePeruMobileInput } from './peruPhoneValidation';

const DEFAULT_BANK_ACCOUNT_TYPE = 'Cta Ahorro';
const DEFAULT_BANK_CURRENCY = 'Soles';

function toText(value) {
  return String(value || '').trim();
}

export function buildEmptyBankPaymentMethod() {
  return {
    tipo: 'bank',
    banco: '',
    tipo_cuenta: DEFAULT_BANK_ACCOUNT_TYPE,
    moneda: DEFAULT_BANK_CURRENCY,
    cuenta: '',
    cci: '',
  };
}

export function buildEmptyWalletPaymentMethod() {
  return {
    tipo: 'wallet',
    proveedor: '',
    titular: '',
    numero: '',
    nota: '',
  };
}

export function normalizePaymentMethod(method) {
  if (!method || typeof method !== 'object') return null;

  const rawType = toText(method.tipo).toLowerCase();
  const isWallet = rawType === 'wallet' || Boolean(method.proveedor);

  if (isWallet) {
    return {
      tipo: 'wallet',
      proveedor: toText(method.proveedor),
      titular: toText(method.titular),
      numero: normalizePeruMobileInput(method.numero || method.cuenta),
      nota: toText(method.nota),
    };
  }

  return {
    tipo: 'bank',
    banco: toText(method.banco),
    tipo_cuenta: toText(method.tipo_cuenta) || DEFAULT_BANK_ACCOUNT_TYPE,
    moneda: toText(method.moneda) || DEFAULT_BANK_CURRENCY,
    cuenta: toText(method.cuenta),
    cci: toText(method.cci),
  };
}

export function normalizePaymentMethods(methods) {
  if (!Array.isArray(methods)) return [];
  return methods
    .map(normalizePaymentMethod)
    .filter(Boolean);
}

export function hasPaymentMethodContent(method) {
  const normalized = normalizePaymentMethod(method);
  if (!normalized) return false;

  if (normalized.tipo === 'wallet') {
    return Boolean(
      normalized.proveedor
      || normalized.titular
      || normalized.numero
      || normalized.nota
    );
  }

  return Boolean(
    normalized.banco
    || normalized.cuenta
    || normalized.cci
  );
}

export function serializePaymentMethods(methods) {
  return normalizePaymentMethods(methods)
    .filter(hasPaymentMethodContent)
    .map((method) => {
      if (method.tipo === 'wallet') {
        return {
          tipo: 'wallet',
          proveedor: method.proveedor,
          titular: method.titular,
          numero: method.numero,
          nota: method.nota,
        };
      }

      return {
        tipo: 'bank',
        banco: method.banco,
        tipo_cuenta: method.tipo_cuenta,
        moneda: method.moneda,
        cuenta: method.cuenta,
        cci: method.cci,
      };
    });
}

export function getPaymentMethodPreview(method) {
  const normalized = normalizePaymentMethod(method);
  if (!normalized || !hasPaymentMethodContent(normalized)) return null;

  if (normalized.tipo === 'wallet') {
    const lines = [];
    if (normalized.titular) lines.push(`Titular: ${normalized.titular}`);
    if (normalized.numero) lines.push(`Numero: ${normalized.numero}`);
    if (normalized.nota) lines.push(normalized.nota);

    return {
      title: normalized.proveedor || 'Billetera digital',
      lines: lines.length > 0 ? lines : ['Sin datos'],
    };
  }

  const bankName = normalized.banco || 'Cuenta bancaria';
  const accountLabel = bankName.toLowerCase().includes('nacion')
    ? `Cuenta Detraccion en ${normalized.moneda || DEFAULT_BANK_CURRENCY}`
    : `${normalized.tipo_cuenta || DEFAULT_BANK_ACCOUNT_TYPE} en ${normalized.moneda || DEFAULT_BANK_CURRENCY}`;

  const accountLine = normalized.cuenta
    ? `${accountLabel}: ${normalized.cuenta}${normalized.cci ? `  CCI: ${normalized.cci}` : ''}`
    : normalized.cci
      ? `CCI: ${normalized.cci}`
      : accountLabel;

  return {
    title: bankName,
    lines: [accountLine],
  };
}
