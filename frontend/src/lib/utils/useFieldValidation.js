import { useState, useCallback } from 'react';

// Lightweight field-level validation hook.
// rules: { fieldName: (value, allValues) => errorString | null }
// Returns: { errors, validate, setError, clearErrors, isValid }
export function useFieldValidation(rules) {
  const [errors, setErrors] = useState({});

  const validate = useCallback((values) => {
    const next = {};
    for (const [field, rule] of Object.entries(rules)) {
      const msg = rule(values[field], values);
      if (msg) next[field] = msg;
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  }, [rules]);

  const setError = useCallback((field, message) => {
    setErrors((prev) => ({ ...prev, [field]: message }));
  }, []);

  const clearErrors = useCallback(() => setErrors({}), []);

  const clearField = useCallback((field) => {
    setErrors((prev) => {
      const next = { ...prev };
      delete next[field];
      return next;
    });
  }, []);

  const isValid = Object.keys(errors).length === 0;

  return { errors, validate, setError, clearErrors, clearField, isValid };
}

// Common validation rules
export const rules = {
  required: (label) => (v) => (!v || !String(v).trim() ? `${label} es obligatorio` : null),
  requiredNum: (label) => (v) => (!v || Number(v) <= 0 ? `${label} debe ser mayor a 0` : null),
  ruc: () => (v) => {
    const s = String(v || '').trim();
    if (!s) return 'RUC es obligatorio';
    if (!/^\d{11}$/.test(s)) return 'RUC debe tener 11 dígitos';
    return null;
  },
  dni: () => (v) => {
    const s = String(v || '').trim();
    if (!s) return 'DNI es obligatorio';
    if (!/^\d{8}$/.test(s)) return 'DNI debe tener 8 dígitos';
    return null;
  },
  docByType: () => (v, all) => {
    const s = String(v || '').trim();
    if (!s) return 'Número de documento es obligatorio';
    if (all?.cliente_tipo_documento === '6' || all?.tipo_comprobante === '01') {
      if (!/^\d{11}$/.test(s)) return 'Factura requiere RUC (11 dígitos)';
    } else if (all?.cliente_tipo_documento === '1') {
      if (!/^\d{8}$/.test(s)) return 'DNI debe tener 8 dígitos';
    }
    return null;
  },
};
