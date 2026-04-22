export const DEFAULT_NOTE_1_TEXT = 'TODO TRABAJO SE REALIZA CON EL 50% DE ADELANTO';
export const DEFAULT_NOTE_2_TEXT = 'LOS PRECIOS NO INCLUYEN ENVIOS';
export const DEFAULT_NOTE_1_COLOR = '#FF0000';
export const DEFAULT_NOTE_2_COLOR = '#111111';

function normalizeColor(value, fallback) {
  const candidate = String(value || '').trim();
  if (/^#([0-9A-Fa-f]{6})$/.test(candidate)) return candidate.toUpperCase();
  return fallback;
}

function parseObservationConfig(rawValue) {
  if (typeof rawValue !== 'string') return null;
  const trimmed = rawValue.trim();
  if (!trimmed || (!trimmed.startsWith('{') && !trimmed.startsWith('['))) return null;

  try {
    const parsed = JSON.parse(trimmed);
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

function getConfigLine(config, key) {
  return config?.[key] && typeof config[key] === 'object' ? config[key] : {};
}

export function parseTenantObservationDefaults(tenantData = null) {
  const rawNote2 = tenantData?.pdf_note_2;
  const config = parseObservationConfig(rawNote2);
  const line1Config = getConfigLine(config, 'line_1');
  const line2Config = getConfigLine(config, 'line_2');
  const legacyNote2Text = config ? '' : String(rawNote2 || '');

  return {
    line1: {
      text: String(line1Config.text || tenantData?.pdf_note_1 || DEFAULT_NOTE_1_TEXT),
      color: normalizeColor(line1Config.color || tenantData?.pdf_note_1_color || DEFAULT_NOTE_1_COLOR, DEFAULT_NOTE_1_COLOR),
      bold: typeof line1Config.bold === 'boolean' ? line1Config.bold : true,
    },
    line2: {
      text: String(line2Config.text || legacyNote2Text || DEFAULT_NOTE_2_TEXT),
      color: normalizeColor(line2Config.color || DEFAULT_NOTE_2_COLOR, DEFAULT_NOTE_2_COLOR),
      bold: typeof line2Config.bold === 'boolean' ? line2Config.bold : false,
    },
  };
}

export function serializeTenantObservationDefaults({ line1, line2 }) {
  return JSON.stringify({
    version: 1,
    line_1: {
      text: String(line1?.text || ''),
      color: normalizeColor(line1?.color || DEFAULT_NOTE_1_COLOR, DEFAULT_NOTE_1_COLOR),
      bold: Boolean(line1?.bold),
    },
    line_2: {
      text: String(line2?.text || ''),
      color: normalizeColor(line2?.color || DEFAULT_NOTE_2_COLOR, DEFAULT_NOTE_2_COLOR),
      bold: Boolean(line2?.bold),
    },
  });
}
