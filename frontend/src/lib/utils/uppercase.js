const DEFAULT_UPPERCASE_FIELDS = new Set([
  'razon_social',
  'nombre_comercial',
  'nombre',
  'direccion',
  'direccion_entrega',
  'contacto',
  'descripcion',
  'codigo',
  'codigo_interno',
]);

export function forceUppercaseText(value) {
  return typeof value === 'string' ? value.toUpperCase() : value;
}

export function normalizeUppercaseFieldValue(key, value, fields = DEFAULT_UPPERCASE_FIELDS) {
  return fields.has(key) ? forceUppercaseText(value) : value;
}

export function normalizeUppercaseShape(values = {}, fields = DEFAULT_UPPERCASE_FIELDS) {
  const next = { ...values };
  fields.forEach((key) => {
    if (typeof next[key] === 'string') {
      next[key] = forceUppercaseText(next[key]);
    }
  });
  return next;
}
