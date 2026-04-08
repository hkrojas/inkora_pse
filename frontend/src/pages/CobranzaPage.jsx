import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { AlertCircle, Eye } from 'lucide-react';
import { dashboard } from '../services/dashboard';
import Spinner from '../components/ui/Spinner';
import EmptyState from '../components/ui/EmptyState';
import Badge, { statusBadge } from '../components/ui/Badge';
import { useToast } from '../components/ui/Toast';

export default function CobranzaPage() {
  const toast = useToast();
  const [vencidas, setVencidas] = useState([]);
  const [resumen, setResumen] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([dashboard.cobranzaVencidas(), dashboard.cobranzaResumen()])
      .then(([v, r]) => { setVencidas(Array.isArray(v) ? v : []); setResumen(r); })
      .catch(() => toast('Error al cargar cobranza', 'error'))
      .finally(() => setLoading(false));
  }, []);

  const fmt = (n) => Number(n || 0).toLocaleString('es-PE', { minimumFractionDigits: 2 });

  if (loading) return <div className="flex h-64 items-center justify-center"><Spinner size="lg" /></div>;

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-gray-900">Cobranza</h1>
        <p className="text-sm text-gray-500">Seguimiento de cobros y saldos pendientes</p>
      </div>

      {/* Resumen */}
      {resumen && (
        <div className="grid grid-cols-3 gap-4">
          {[
            { label: 'Total pendiente', value: `S/ ${fmt(resumen.total_por_cobrar)}`, color: 'text-orange-600' },
            { label: 'Docs vencidos', value: resumen.documentos_vencidos ?? '—', color: 'text-red-600' },
            { label: 'Cobrado este mes', value: `S/ ${fmt(resumen.total_pagado_mes)}`, color: 'text-green-600' },
          ].map(({ label, value, color }) => (
            <div key={label} className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</p>
              <p className={`mt-1 text-2xl font-bold ${color}`}>{value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Tabla vencidas */}
      <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
        <div className="flex items-center gap-2 border-b border-gray-100 px-5 py-3.5">
          <AlertCircle className="h-4 w-4 text-red-500" />
          <h2 className="text-sm font-semibold text-gray-900">Cotizaciones vencidas</h2>
          <span className="ml-auto text-xs text-gray-400">{vencidas.length} registros</span>
        </div>
        {vencidas.length === 0 ? (
          <EmptyState title="Sin vencimientos" description="No hay cotizaciones vencidas" />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                <th className="px-4 py-3">Orden</th>
                <th className="px-4 py-3">Cliente</th>
                <th className="px-4 py-3">Vencimiento</th>
                <th className="px-4 py-3 text-right">Total</th>
                <th className="px-4 py-3 text-right">Saldo</th>
                <th className="px-4 py-3">Estado</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {vencidas.map((item) => (
                <tr key={item.cotizacion_id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">{item.internal_order_number || item.document_number || `#${item.cotizacion_id}`}</td>
                  <td className="px-4 py-3 font-medium text-gray-900">{item.cliente_nombre || '—'}</td>
                  <td className="px-4 py-3 text-red-600 text-xs">
                    {item.fecha_vencimiento ? new Date(item.fecha_vencimiento).toLocaleDateString('es-PE') : '—'}
                  </td>
                  <td className="px-4 py-3 text-right">S/ {fmt(item.total_venta)}</td>
                  <td className="px-4 py-3 text-right font-semibold text-red-600">S/ {fmt(item.saldo_pendiente)}</td>
                  <td className="px-4 py-3">
                    <span className="text-xs text-red-500">{item.dias_vencido}d</span>
                  </td>
                  <td className="px-4 py-3">
                    <Link to={`/cotizaciones/${item.cotizacion_id}`} className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600 inline-flex">
                      <Eye className="h-4 w-4" />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
