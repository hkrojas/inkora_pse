/**
 * Configuración centralizada del frontend.
 *
 * Todos los módulos que necesiten la URL del backend o constantes
 * globales deben importar desde aquí para evitar duplicación.
 */

export const BASE_URL =
  import.meta.env.VITE_API_URL || 'http://localhost:8000';
