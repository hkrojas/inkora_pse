import { addDays, inputDateToday } from './documents.js';

export function fiscalIssueDateWindow(type, now = new Date()) {
  const days = type === '03' ? 5 : 3;
  const max = inputDateToday(now);
  return { min: addDays(max, -days), max, days };
}

export function fiscalIssueDateError(value, type, now = new Date()) {
  if (!value) return 'Fecha de emisión es obligatoria';
  const parsed = new Date(`${value}T00:00:00Z`);
  if (Number.isNaN(parsed.getTime()) || parsed.toISOString().slice(0, 10) !== value) return 'Fecha de emisión no es válida';
  const { min, max, days } = fiscalIssueDateWindow(type, now);
  if (value > max) return 'La fecha de emisión no puede ser futura';
  if (value < min) return `El plazo de envío individual es de ${days} días calendario siguientes a la emisión. Elige una fecha vigente.`;
  return null;
}
