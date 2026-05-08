/**
 * Configuración centralizada del frontend.
 *
 * Todos los módulos que necesiten la URL del backend o constantes
 * globales deben importar desde aquí para evitar duplicación.
 */

const DEFAULT_API_URL = 'https://inkorapse-production.up.railway.app';
const viteEnv = import.meta.env || {};

export const BASE_URL = (viteEnv.VITE_API_URL || DEFAULT_API_URL).replace(/\/$/, '');
