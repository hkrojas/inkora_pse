import { normalizePeruMobileInput, validatePeruMobilePhone } from './peruPhoneValidation';

function normalizeText(value) {
  return String(value || '').trim();
}

function normalizeKey(value) {
  return normalizeText(value)
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase();
}

export function digitsOnly(value) {
  return String(value || '').replace(/\D+/g, '');
}

function matchesBank(bankKey, aliases) {
  return aliases.some((alias) => bankKey === alias || bankKey.includes(alias));
}

function buildRule({ allowedLengths = [], minLength = null, maxLength = null, description }) {
  return { allowedLengths, minLength, maxLength, description };
}

export function getBankAccountRule(bankName, accountType = '') {
  const bankKey = normalizeKey(bankName);
  const typeKey = normalizeKey(accountType);

  if (matchesBank(bankKey, ['bcp', 'credito del peru', 'banco de credito del peru'])) {
    if (typeKey.includes('corriente')) {
      return buildRule({
        allowedLengths: [13],
        description: '13 digitos para cuenta corriente BCP.',
      });
    }

    return buildRule({
      allowedLengths: [13, 14],
      description: '13 o 14 digitos segun el tipo de cuenta BCP.',
    });
  }

  if (matchesBank(bankKey, ['bbva', 'continental'])) {
    return buildRule({
      allowedLengths: [18, 20],
      description: '18 o 20 digitos para cuentas BBVA.',
    });
  }

  if (matchesBank(bankKey, ['interbank'])) {
    return buildRule({
      allowedLengths: [13],
      description: '13 digitos para cuentas Interbank.',
    });
  }

  if (matchesBank(bankKey, ['scotiabank', 'scotia'])) {
    return buildRule({
      allowedLengths: [10, 14],
      description: '10 o 14 digitos para cuentas Scotiabank.',
    });
  }

  if (matchesBank(bankKey, ['banco de la nacion', 'banco de la nacion', 'nacion'])) {
    return buildRule({
      minLength: 10,
      maxLength: 13,
      description: '10 a 13 digitos para cuentas del Banco de la Nacion.',
    });
  }

  if (matchesBank(bankKey, ['banbif'])) {
    return buildRule({
      allowedLengths: [10, 12],
      description: '10 o 12 digitos para cuentas BanBif.',
    });
  }

  if (matchesBank(bankKey, ['pichincha'])) {
    return buildRule({
      allowedLengths: [12],
      description: '12 digitos para cuentas Banco Pichincha.',
    });
  }

  if (matchesBank(bankKey, ['caja huancayo'])) {
    return buildRule({
      allowedLengths: [18],
      description: '18 digitos para cuentas Caja Huancayo.',
    });
  }

  return buildRule({
    minLength: 6,
    maxLength: 20,
    description: 'Longitud variable segun la entidad. Usa entre 6 y 20 digitos numericos.',
  });
}

export function getBankAccountHint(bankName, accountType = '') {
  return getBankAccountRule(bankName, accountType).description;
}

export function validateBankPaymentMethod(method) {
  if (!method || method.tipo === 'wallet') return {};

  const errors = {};
  const accountDigits = digitsOnly(method.cuenta);
  const cciDigits = digitsOnly(method.cci);
  const hasAccountInput = normalizeText(method.cuenta).length > 0;
  const hasCciInput = normalizeText(method.cci).length > 0;
  const rule = getBankAccountRule(method.banco, method.tipo_cuenta);

  if (hasAccountInput) {
    if (rule.allowedLengths?.length > 0) {
      if (!rule.allowedLengths.includes(accountDigits.length)) {
        errors.cuenta = `Numero de cuenta invalido para ${method.banco || 'este banco'}: debe tener ${rule.description.toLowerCase()}`;
      }
    } else if (
      typeof rule.minLength === 'number'
      && typeof rule.maxLength === 'number'
      && (accountDigits.length < rule.minLength || accountDigits.length > rule.maxLength)
    ) {
      errors.cuenta = `Numero de cuenta invalido: debe tener entre ${rule.minLength} y ${rule.maxLength} digitos.`;
    }
  }

  if (hasCciInput && cciDigits.length !== 20) {
    errors.cci = 'CCI invalido: debe tener 20 digitos.';
  }

  return errors;
}

export function validateWalletPaymentMethod(method) {
  if (!method || method.tipo !== 'wallet') return {};

  const errors = {};
  const hasNumberInput = normalizeText(method.numero).length > 0;
  if (hasNumberInput) {
    const phoneError = validatePeruMobilePhone(method.numero, 'Numero asociado');
    if (phoneError) errors.numero = phoneError;
  }

  return errors;
}

export function buildPaymentMethodErrorMap(methods) {
  const next = {};

  methods.forEach((method, index) => {
    const errors = method?.tipo === 'wallet'
      ? validateWalletPaymentMethod(method)
      : validateBankPaymentMethod(method);
    if (Object.keys(errors).length > 0) {
      next[index] = errors;
    }
  });

  return next;
}

export function normalizeWalletPhone(value) {
  return normalizePeruMobileInput(value);
}
