/**
 * Configuración centralizada del frontend.
 *
 * Todos los módulos que necesiten la URL del backend o constantes
 * globales deben importar desde aquí para evitar duplicación.
 */

const DEFAULT_API_URL = import.meta.env.DEV
  ? 'http://localhost:8000'
  : 'https://inkorapse-production.up.railway.app';

export const BASE_URL = (import.meta.env.VITE_API_URL || DEFAULT_API_URL).replace(/\/$/, '');
