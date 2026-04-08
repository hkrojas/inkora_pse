import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { FileText, Users, CreditCard, AlertCircle, TrendingUp } from 'lucide-react';
import { dashboard } from '../services/dashboard';
import Spinner from '../components/ui/Spinner';
import Badge, { statusBadge } from '../components/ui/Badge';
import { useAuth } from '../context/AuthContext';

function StatCard({ label, value, icon: Icon, color = 'blue' }) {
  const colors = {
    blue:   'bg-blue-50 text-blue-600',
    green:  'bg-green-50 text-green-600',
    orange: 'bg-orange-50 text-orange-600',
    red:    'bg-red-50 text-red-600',
  };
  return (
    <div className="rounded-xl bg-white p-5 shadow-sm border border-gray-200">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</p>
          <p className="mt-1 text-2xl font-bold text-gray-900">{value ?? '—'}</p>
        </div>
        <div className={`rounded-lg p-2.5 ${colors[color]}`}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [vencidas, setVencidas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([
      dashboard.stats().catch(() => null),
      dashboard.cobranzaVencidas().catch(() => []),
    ]).then(([s, v]) => {
      setStats(s);
      setVencidas(Array.isArray(v) ? v.slice(0, 5) : []);
    }).catch(() => setError('No se pudo cargar el dashboard'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return (
    <div className="flex h-64 items-center justify-center">
      <Spinner size="lg" />
    </div>
  );

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-gray-900">
          Hola, {user?.nombre_completo?.split(' ')[0] || 'bienvenido'}
        </h1>
        <p className="text-sm text-gray-500">Resumen del negocio</p>
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
          <AlertCircle className="h-4 w-4" /> {error}
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Emitidos este mes" value={stats?.documentos_emitidos_mes ?? '—'} icon={FileText} color="blue" />
        <StatCard label="Ingresos cobrados" value={stats?.ingresos_totales != null ? `S/ ${Number(stats.ingresos_totales).toLocaleString('es-PE', {minimumFractionDigits:2})}` : '—'} icon={Users} color="green" />
        <StatCard label="Por cobrar" value={stats?.saldos_por_cobrar != null ? `S/ ${Number(stats.saldos_por_cobrar).toLocaleString('es-PE', {minimumFractionDigits:2})}` : '—'} icon={CreditCard} color="orange" />
        <StatCard label="Docs vencidos" value={stats?.documentos_vencidos ?? '—'} icon={AlertCircle} color="red" />
      </div>

      {/* Cotizaciones vencidas */}
      {vencidas.length > 0 && (
        <div className="rounded-xl bg-white border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between border-b border-gray-100 px-5 py-3.5">
            <h2 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-orange-500" />
              Cobranza vencida
            </h2>
            <Link to="/cobranza" className="text-xs text-blue-600 hover:underline">Ver todo</Link>
          </div>
          <div className="divide-y divide-gray-50">
            {vencidas.map((item) => (
              <div key={item.cotizacion_id} className="flex items-center justify-between px-5 py-3">
                <div>
                  <p className="text-sm font-medium text-gray-900">{item.cliente_nombre || '—'}</p>
                  <p className="text-xs text-gray-500">
                    Vence: {item.fecha_vencimiento ? new Date(item.fecha_vencimiento).toLocaleDateString('es-PE') : '—'}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-semibold text-red-600">
                    S/ {Number(item.saldo_pendiente || 0).toLocaleString('es-PE', { minimumFractionDigits: 2 })}
                  </p>
                  <Badge variant={statusBadge(item.payment_status)}>{item.payment_status}</Badge>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
