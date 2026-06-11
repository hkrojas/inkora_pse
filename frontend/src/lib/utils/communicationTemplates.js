export const COMMUNICATION_TEMPLATE_METHOD_TYPE = 'communication_templates';

export const DEFAULT_SHARE_TEMPLATES = {
  whatsapp_message: [
    'Hola {cliente}, le compartimos la cotizacion {numero} por {moneda} {total}.',
    '',
    'Puede descargar el documento aqui: {url}',
    '',
    'El enlace es privado y solo debe compartirse con personas autorizadas.',
  ].join('\n'),
  email_subject: 'Cotizacion {numero} - {empresa}',
  email_body: [
    'Estimado cliente,',
    '',
    'Le enviamos el enlace para descargar la cotizacion {numero}.',
    '',
    'Enlace de descarga:',
    '{url}',
    '',
    'El enlace es privado y solo debe compartirse con personas autorizadas.',
    '',
    'Quedamos atentos a sus comentarios.',
    '',
    'Saludos cordiales,',
    '{empresa}',
  ].join('\n'),
};

export const SHARE_TEMPLATE_PLACEHOLDERS = [
  '{cliente}',
  '{numero}',
  '{moneda}',
  '{total}',
  '{url}',
  '{empresa}',
];

const LIMITS = {
  whatsapp_message: 1200,
  email_subject: 180,
  email_body: 3000,
};

function toText(value) {
  return String(value || '').trim();
}

function clip(value, key) {
  return toText(value).slice(0, LIMITS[key]);
}

function findTemplateEntry(methods) {
  if (!Array.isArray(methods)) return null;
  return methods.find((method) => (
    method
    && typeof method === 'object'
    && toText(method.tipo).toLowerCase() === COMMUNICATION_TEMPLATE_METHOD_TYPE
  )) || null;
}

export function extractCommunicationTemplates(methods) {
  const entry = findTemplateEntry(methods);
  return {
    whatsapp_message: clip(entry?.whatsapp_message || DEFAULT_SHARE_TEMPLATES.whatsapp_message, 'whatsapp_message'),
    email_subject: clip(entry?.email_subject || DEFAULT_SHARE_TEMPLATES.email_subject, 'email_subject'),
    email_body: clip(entry?.email_body || DEFAULT_SHARE_TEMPLATES.email_body, 'email_body'),
  };
}

export function serializeCommunicationTemplates(templates) {
  return {
    tipo: COMMUNICATION_TEMPLATE_METHOD_TYPE,
    whatsapp_message: clip(templates?.whatsapp_message || DEFAULT_SHARE_TEMPLATES.whatsapp_message, 'whatsapp_message'),
    email_subject: clip(templates?.email_subject || DEFAULT_SHARE_TEMPLATES.email_subject, 'email_subject'),
    email_body: clip(templates?.email_body || DEFAULT_SHARE_TEMPLATES.email_body, 'email_body'),
  };
}

export function mergeCommunicationTemplates(methods, templates) {
  const cleanMethods = Array.isArray(methods)
    ? methods.filter((method) => toText(method?.tipo).toLowerCase() !== COMMUNICATION_TEMPLATE_METHOD_TYPE)
    : [];
  return [
    ...cleanMethods,
    serializeCommunicationTemplates(templates),
  ];
}
