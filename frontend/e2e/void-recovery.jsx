import React from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { ThemeProvider } from '../src/context/ThemeContext';
import { ToastProvider } from '../src/components/ui/Toast';
import { InkoraDialogProvider } from '../src/components/ui/InkoraDialogProvider';
import FiscalDocumentActions from '../src/components/documents/FiscalDocumentActions';
import BajasPage from '../src/pages/BajasPage';
import '../src/app.css';
import '../src/styles/tokens.css';
import '../src/styles/globals.css';

const params = new URL(location.href).searchParams;
localStorage.setItem('token', 'void-qa-offline-only');
localStorage.setItem('inkora-theme', params.get('theme') || 'light');
const doc = { id: 42, document_kind: 'fiscal_document', tipo_comprobante: '03', serie: 'B001', correlativo: 42,
  document_number: 'B001-000042', estado: 'facturada', fiscal_status: 'emitted', provider_verification_status: 'verified',
  has_sunat_xml: true, has_sunat_cdr: true, sunat_accepted: true, sunat_xml_content: '<synthetic/>', sunat_cdr_content: '<synthetic/>',
  total_venta: 118, moneda: 'PEN', fecha_emision: '2026-10-07T12:00:00-05:00', cliente: { razon_social: 'Cliente de prueba', numero_documento: '20123456789' } };
const state = window.voidQa = { calls: [], status: 'queued', revision: 1 };
const originalFetch = window.fetch.bind(window);
window.fetch = async (input, options = {}) => {
  const url = new URL(String(input), location.href);
  if (url.origin === location.origin) return originalFetch(input, options);
  const path = url.pathname.replace(/\/$/, '');
  const method = options.method || 'GET';
  state.calls.push({ path, method, payload: options.body ? JSON.parse(options.body) : null });
  const respond = (value, status = 200) => new Response(JSON.stringify(value), { status, headers: { 'Content-Type': 'application/json' } });
  if (path === '/facturas-emitidas/42/acciones') return respond({ void: true, retry_emission: false });
  if (path === '/bajas/anular' && method === 'POST') return respond({ queued: true, job_id: 7001, job_status: state.status }, 202);
  if (path === '/emission-jobs/7001') return respond({ id: 7001, resource_id: 42, action: 'void_fiscal_document', status: state.status,
    last_error: state.status === 'retry' ? 'Baja pendiente de CDR; se consulta sin reenviar.' : null, updated_at: `2026-10-07T15:00:${state.revision}` });
  if (path === '/facturas-emitidas/page') return respond({ items: [{ ...doc, estado: state.status === 'succeeded' ? 'anulada' : 'facturada' }], total: 1,
    counts: { all: 1, emitted: state.status === 'succeeded' ? 0 : 1, voided: state.status === 'succeeded' ? 1 : 0 } });
  // Unknown API traffic is contained in the fixture, never forwarded.
  return respond({ detail: 'Operación no prevista por la prueba aislada.' }, 404);
};
createRoot(document.getElementById('root')).render(<ThemeProvider><ToastProvider><InkoraDialogProvider><MemoryRouter>
  <main style={{ maxWidth: 1200, margin: 'auto', padding: 12 }}>
    {params.get('entry') === 'bajas' ? <BajasPage /> : <FiscalDocumentActions doc={doc} reload={async () => { state.revision += 1; }} />}
  </main>
</MemoryRouter></InkoraDialogProvider></ToastProvider></ThemeProvider>);
