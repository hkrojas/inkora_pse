import { useState, useEffect } from 'react';
import { superadmin as svc } from '../services/superadmin';
import Spinner from '../components/ui/Spinner';
import Badge from '../components/ui/Badge';
import EmptyState from '../components/ui/EmptyState';
import { useToast } from '../components/ui/Toast';
import { useAuth } from '../context/AuthContext';
import { Navigate } from 'react-router-dom';

export default function SuperadminPage() {
  const { user } = useAuth();
  const toast = useToast();
  const [tenants, setTenants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState('tenants');

  if (user?.rol !== 'superadmin') return <Navigate to="/dashboard" replace />;

  useEffect(() => {
    svc.tenants().then(setTenants).catch(() => toast('Error al cargar tenants', 'error')).finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-gray-900">Superadmin</h1>
        <p className="text-sm text-gray-500">Panel de administración de tenants</p>
      </div>

      <div className="flex gap-2 border-b border-gray-200">
        {['tenants'].map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors capitalize ${tab === t ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
          >
            {t}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex justify-center py-16"><Spinner size="lg" /></div>
      ) : tenants.length === 0 ? (
        <EmptyState title="Sin tenants" />
      ) : (
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                <th className="px-4 py-3">Empresa</th>
                <th className="px-4 py-3">RUC</th>
                <th className="px-4 py-3">Plan</th>
                <th className="px-4 py-3">Estado</th>
                <th className="px-4 py-3">Creado</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {tenants.map((t) => (
                <tr key={t.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{t.business_name}</td>
                  <td className="px-4 py-3 text-gray-500">{t.business_ruc || '—'}</td>
                  <td className="px-4 py-3 text-gray-500 capitalize">{t.plan || '—'}</td>
                  <td className="px-4 py-3">
                    <Badge variant={t.is_active ? 'success' : 'danger'}>{t.is_active ? 'activo' : 'inactivo'}</Badge>
                  </td>
                  <td className="px-4 py-3 text-gray-400 text-xs">
                    {t.created_at ? new Date(t.created_at).toLocaleDateString('es-PE') : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
