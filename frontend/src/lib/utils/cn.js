import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Combina clases de Tailwind de forma condicional y resuelve conflictos.
 * Útil para componentes reutilizables con variantes.
 *
 * @example
 * cn('btn-primary', isLoading && 'opacity-50', className)
 */
export function cn(...inputs) {
  return twMerge(clsx(inputs));
}
