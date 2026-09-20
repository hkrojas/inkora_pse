import React from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter, Routes, Route, Link } from 'react-router-dom';
import { ThemeProvider } from '../src/context/ThemeContext';
import { AuthProvider } from '../src/context/AuthContext';
import { ToastProvider } from '../src/components/ui/Toast';
import FacturasPage from '../src/pages/FacturasPage';
import CotizacionesPage from '../src/pages/CotizacionesPage';
import '../src/app.css';
import '../src/styles/tokens.css';
import '../src/styles/globals.css';

const started = Number(sessionStorage.getItem('fixture-job-start') || 0);
let jobStart = started;
const jobStatus = () => !jobStart ? null : Date.now() - jobStart < 8000 ? 'queued' : Date.now() - jobStart < 16000 ? 'processing' : 'pending_confirmation';
const rows = Array.from({ length: 185 }, (_, i) => ({ id: 99001+i, serie: 'FA01', correlativo: i+1,
  estado: i === 3 ? 'anulada' : i === 0 || i > 3 ? 'facturada' : 'pendiente',
  fiscal_status: i === 3 ? 'voided' : i === 1 ? 'pending_confirmation' : i === 2 ? 'rejected' : 'emitted',
  provider_verification_status: i === 1 ? 'pending_confirmation' : 'verified',
  has_sunat_xml: true, has_sunat_cdr: i === 0 || i > 3, sunat_error: i === 1 ? '[1033] Resultado incierto' : i === 2 ? '[3127] Error XML' : null,
  document_kind: 'fiscal_document', tipo_comprobante: '01', total_venta: 118, total_gravada: 100, total_igv: 18,
  moneda: 'PEN', fecha_emision: '2026-09-18', cliente: { id: 1, razon_social: i === 184 ? 'CLIENTE REMOTO 185' : 'CLIENTE SINTÉTICO', numero_documento: '20123456789' },
}));
const quote = { ...rows[0], id: 98001, serie: 'COT', correlativo: 277, estado: 'pendiente', document_kind: 'quotation', fiscal_status: null, items: [], detalles: [], tipo_comprobante: null };
const realFetch = window.fetch.bind(window);
window.fetch = async (input, options = {}) => {
  const url = new URL(String(input), location.href);
  if (url.origin === location.origin) return realFetch(input, options);
  const path = url.pathname.replace(/\/$/, '');
  const respond = (data, status = 200) => new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } });
  if (path === '/users/me') return respond({ id: 1, tenant_id: 1, rol: 'admin', is_active: true, nombre_completo: 'Operador aislado' });
  if (path === '/tenant') return respond({ id: 1, business_name: 'PRUEBA AISLADA', is_active: true });
  if (path === '/sunat/exchange-rate') return respond({ buy: '3.4', sell: '3.41' });
  if (path === '/facturas-emitidas/page') {
    let filtered = rows.filter(row => !url.searchParams.get('q') || `${row.serie}-${String(row.correlativo).padStart(6, '0')} ${row.cliente.razon_social}`.toLowerCase().includes(url.searchParams.get('q').toLowerCase()));
    if (url.searchParams.get('numero')) filtered = filtered.filter(row => String(row.correlativo).includes(url.searchParams.get('numero').replace(/^0+/, '')));
    if (url.searchParams.get('razon_social')) filtered = filtered.filter(row => row.cliente.razon_social.toLowerCase().includes(url.searchParams.get('razon_social').toLowerCase()));
    const tab = url.searchParams.get('tab');
    if (tab && tab !== 'all') filtered = filtered.filter(row => row.fiscal_status === tab || tab === 'pending' && row.fiscal_status === 'pending_confirmation');
    const skip = Number(url.searchParams.get('skip') || 0);
    return respond({ items: filtered.slice(skip, skip + 15), total: filtered.length, counts: { all: 185, emitted: 182, pending: 1, rejected: 1, draft: 0, voided: 1 } });
  }
  if (path === '/cotizaciones/page') return respond({ items: [quote], total: 1 });
  if (path === '/clientes' || path === '/productos') return respond([]);
  if (path === '/clientes/page' || path === '/productos/page') return respond({ items: [], total: 0 });
  if (path.endsWith('/acciones')) {
    const id = Number(path.split('/')[2]);
    const accepted = id === 99001 || id > 99004;
    return respond({ retry_label: 'Reenviar a Smart PSE', retry_emission: id === 99003 && !jobStart,
      retry_block_reason: id === 99002 || id === 99003 && jobStart ? 'Resultado pendiente de conciliación. No se permite reenviar.' : null,
      retry_artifacts: accepted, void: accepted, credit_note: accepted, debit_note: accepted, create_guide: accepted,
      ...(id === 99003 && jobStart ? { job_id: 7001, job_status: jobStatus(), job_action: 'emit_fiscal_document' } : {}) });
  }
  if (path.endsWith('/reintentar')) { jobStart = Date.now(); sessionStorage.setItem('fixture-job-start', String(jobStart)); return respond({ job_id: 7001, job_status: 'queued' }, 202); }
  if (path === '/emission-jobs/7001') return respond({ id: 7001, resource_id: 99003, status: jobStatus(), action: 'emit_fiscal_document' });
  return respond({ detail: 'Operación bloqueada por el simulador aislado.' }, 404);
};
localStorage.setItem('token', 'isolated-fixture-only');
localStorage.setItem('inkora-theme', new URL(location.href).searchParams.get('theme') || 'light');
createRoot(document.getElementById('root')).render(<ThemeProvider><AuthProvider><ToastProvider><MemoryRouter initialEntries={['/facturas']}>
  <nav style={{ padding: 12 }}><strong>SIMULADOR AISLADO · SIN ENVÍOS REALES</strong> · <Link to="/facturas">Facturas</Link> · <Link to="/cotizaciones?view=history">Cotizaciones</Link> · <Link to="/cotizaciones?view=fiscal">Emitidas SUNAT</Link></nav>
  <Routes><Route path="/facturas" element={<FacturasPage />} /><Route path="/cotizaciones" element={<CotizacionesPage />} /></Routes>
</MemoryRouter></ToastProvider></AuthProvider></ThemeProvider>);
