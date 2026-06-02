function firstNonEmpty(data = {}, keys = []) {
  for (const key of keys) {
    const value = data?.[key];
    if (value === undefined || value === null) continue;
    if (typeof value === 'string') {
      const trimmed = value.trim();
      if (trimmed) return trimmed;
      continue;
    }
    return value;
  }
  return '';
}

export function getLookupName(data = {}) {
  const directName = firstNonEmpty(data, [
    'razon_social',
    'razonSocial',
    'nombre_o_razon_social',
    'nombreORazonSocial',
    'nombre_completo',
    'nombreCompleto',
    'nombre',
    'denominacion',
  ]);
  if (directName) return directName;

  return [
    firstNonEmpty(data, ['nombres']),
    firstNonEmpty(data, ['apellido_paterno', 'apellidoPaterno', 'ap_paterno']),
    firstNonEmpty(data, ['apellido_materno', 'apellidoMaterno', 'ap_materno']),
  ].filter(Boolean).join(' ').trim();
}

export function getLookupCommercialName(data = {}) {
  return firstNonEmpty(data, ['nombre_comercial', 'nombreComercial']);
}

export function getLookupAddress(data = {}) {
  const address = firstNonEmpty(data, [
    'direccion',
    'direccion_fiscal',
    'direccionFiscal',
    'domicilio_fiscal',
    'domicilioFiscal',
  ]);
  return address && address !== '-' ? address : '';
}

export function getLookupUbigeo(data = {}) {
  return firstNonEmpty(data, ['ubigeo', 'ubigeo_sunat', 'ubigeoSunat']);
}

export function getLookupDocumentType(data = {}, fallback = '6') {
  const rawType = String(firstNonEmpty(data, ['tipo', 'tipo_documento', 'tipoDocumento'])).toUpperCase();
  if (rawType === 'RUC' || rawType === '6') return '6';
  if (rawType === 'DNI' || rawType === '1') return '1';

  const digits = String(firstNonEmpty(data, ['documento', 'numero_documento', 'numeroDocumento', 'ruc', 'dni']))
    .replace(/\D/g, '');
  if (digits.length === 11) return '6';
  if (digits.length === 8) return '1';
  return fallback;
}
