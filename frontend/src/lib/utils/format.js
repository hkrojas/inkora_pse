/**
 * Utilidades de formato compartidos por toda la aplicación.
 *
 * Evita duplicar `fmt()` y `new Date().toLocaleDateString()` en cada página.
 */

/**
 * Formatea un número como moneda (Soles por defecto).
 * @param {number|string} n
 * @param {string} currency - 'PEN' | 'USD'
 * @returns {string}
 */
export function formatCurrency(n, currency = 'PEN') {
  const locales = {
    PEN: 'es-PE',
    USD: 'en-US',
  };
  const symbols = {
    PEN: 'S/',
    USD: '$',
  };
  const locale = locales[currency] || locales.PEN;
  const symbol = symbols[currency] || symbols.PEN;
  const formatted = Number(n || 0).toLocaleString(locale, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return `${symbol} ${formatted}`;
}

/**
 * Formatea una fecha para visualización en Perú.
 * @param {string|number|Date} date
 * @returns {string}
 */
export function formatDate(date) {
  if (!date) return '—';
  return new Date(date).toLocaleDateString('es-PE');
}

/**
 * Formatea fecha + hora para visualización en Perú.
 * @param {string|number|Date} date
 * @returns {string}
 */
export function formatDateTime(date) {
  if (!date) return '—';
  return new Date(date).toLocaleString('es-PE');
}
