import { useState, useEffect } from 'react';
import { superadmin as svc } from '../services/superadmin';
import Spinner from '../components/ui/Spinner';
import Badge from '../components/ui/Badge';
import EmptyState from '../components/ui/EmptyState';
import { useToast } from '../components/ui/Toast';
import { useAuth } from '../context/AuthContext';
import { Navigate } from 'react-router-dom';

function StatusDot({ ok }) {
  return ok
    ? <span className="inline-flex items-center gap-1 text-xs text-green-700 font-medium"><span className="h-1.5 w-1.5 rounded-full bg-green-500" />Configurado</span>
    : <span className="inline-flex items-center gap-1 text-xs text-gray-400"><span className="h-1.5 w-1.5 rounded-full bg-gray-300" />No configurado</span>;
}

function TenantModal({ tenant, onClose, onSaved }) {
  const toast = useToast();
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    business_name:    tenant.business_name    || '',
    business_ruc:     tenant.business_ruc     || '',
    business_address: tenant.business_address || '',
    is_active:        tenant.is_active ?? true,
    apisperu_token:   '',
    apisperu_url:     '',
  });

  const set = (k) => (e) => {
    const val = e.target.type === 'checkbox' ? e.target.checked : e.target.value;
    setForm((f) => ({ ...f, [k]: val }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = {};
      if (form.business_name    !== (tenant.business_name    || '')) payload.business_name    = form.business_name;
      if (form.business_ruc     !== (tenant.business_ruc     || '')) payload.business_ruc     = form.business_ruc;
      if (form.business_address !== (tenant.business_address || '')) payload.business_address = form.business_address;
      if (form.is_active        !== (tenant.is_active ?? true))       payload.is_active        = form.is_active;
      if (form.apisperu_token.trim()) payload.apisperu_token = form.apisperu_token.trim();
      if (form.apisperu_url.trim())   payload.apisperu_url   = form.apisperu_url.trim();

      if (Object.keys(payload).length === 0) { onClose(); return; }

      const updated = await svc.updateTenant(tenant.id, payload);
      toast('Tenant actualizado');
      onSaved(updated);
      onClose();
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div className="w-full max-w-lg rounded-2xl bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-gray-100 px-6 py-4">
          <h2 className="text-sm font-semibold text-gray-900">Editar tenant — {tenant.business_name}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-lg leading-none">×</button>
        </div>

        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">

          {/* Datos de empresa */}
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Datos de empresa</p>
            <div className="space-y-3">
              <div>
                <label className="text-xs font-medium text-gray-600 block mb-1">Razón social</label>
                <input className="input" value={form.business_name} onChange={set('business_name')} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-medium text-gray-600 block mb-1">RUC</label>
                  <input className="input" value={form.business_ruc} onChange={set('business_ruc')} maxLength={11} />
                </div>
                <div className="flex items-end gap-2 pb-0.5">
                  <label className="flex items-center gap-2 cursor-pointer select-none">
                    <input type="checkbox" checked={form.is_active} onChange={set('is_active')} className="h-4 w-4 rounded" />
                    <span className="text-sm text-gray-700">Tenant activo</span>
                  </label>
                </div>
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600 block mb-1">Dirección fiscal</label>
                <input className="input" value={form.business_address} onChange={set('business_address')} />
              </div>
            </div>
          </div>

          {/* Token ApisPeru */}
          <div className="border-t border-gray-100 pt-4">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Token ApisPeru (empresa)</p>
            <p className="text-xs text-gray-400 mb-3">
              Token de empresa generado por ApisPeru — sin fecha de expiración.
              Estado actual: <StatusDot ok={tenant.has_apisperu_token} />
            </p>
            <div className="space-y-3">
              <div>
                <label className="text-xs font-medium text-gray-600 block mb-1">Nuevo token</label>
                <input
                  className="input font-mono text-xs"
                  value={form.apisperu_token}
                  onChange={set('apisperu_token')}
                  placeholder="apis-token-xxxxx.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                />
                <p className="text-xs text-gray-400 mt-1">Dejar vacío para no cambiar el token actual.</p>
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600 block mb-1">URL ApisPeru (opcional)</label>
                <input
                  className="input text-xs"
                  value={form.apisperu_url}
                  onChange={set('apisperu_url')}
                  placeholder="https://facturacion.apisperu.com/api/v1"
                />
              </div>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-gray-100">
            <button type="button" onClick={onClose} className="btn-secondary">Cancelar</button>
            <button type="submit" disabled={saving} className="btn-primary flex items-center gap-2">
              {saving && <Spinner size="sm" />} Guardar
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function SuperadminPage() {
  const { user } = useAuth();
  const toast = useToast();
  const [tenants, setTenants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null);

  if (user?.rol !== 'superadmin' && !user?.is_superadmin) return <Navigate to="/dashboard" replace />;

  useEffect(() => {
    svc.tenants()
      .then(setTenants)
      .catch(() => toast('Error al cargar tenants', 'error'))
      .finally(() => setLoading(false));
  }, []);

  const handleSaved = (updated) => {
    setTenants((prev) => prev.map((t) => t.id === updated.id ? updated : t));
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-gray-900">Superadmin</h1>
        <p className="text-sm text-gray-500">Gestión de tenants y configuración fiscal</p>
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
                <th className="px-4 py-3">ApisPeru</th>
                <th className="px-4 py-3">Estado</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {tenants.map((t) => (
                <tr key={t.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{t.business_name}</td>
                  <td className="px-4 py-3 text-gray-500 font-mono text-xs">{t.business_ruc || '—'}</td>
                  <td className="px-4 py-3 text-gray-500 capitalize">{t.plan_type || 'Free'}</td>
                  <td className="px-4 py-3"><StatusDot ok={t.has_apisperu_token} /></td>
                  <td className="px-4 py-3">
                    <Badge variant={t.is_active ? 'success' : 'danger'}>{t.is_active ? 'activo' : 'inactivo'}</Badge>
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => setEditing(t)}
                      className="text-xs text-blue-600 hover:text-blue-800 font-medium"
                    >
                      Editar
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {editing && (
        <TenantModal
          tenant={editing}
          onClose={() => setEditing(null)}
          onSaved={handleSaved}
        />
      )}
    </div>
  );
}
