import { useState, useEffect } from 'react';
import { tenant as svc } from '../services/tenant';
import Spinner from '../components/ui/Spinner';
import { useToast } from '../components/ui/Toast';
import { useAuth } from '../context/AuthContext';

export default function ConfiguracionPage() {
  const { user } = useAuth();
  const toast = useToast();
  const [tenantData, setTenantData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    business_name: '',
    business_ruc: '',
    business_address: '',
    business_email: '',
    business_phone: '',
  });

  useEffect(() => {
    svc.get().then((t) => {
      setTenantData(t);
      setForm({
        business_name:    t.business_name    || '',
        business_ruc:     t.business_ruc     || '',
        business_address: t.business_address || '',
        business_email:   t.business_email   || '',
        business_phone:   t.business_phone   || '',
      });
    }).catch(() => toast('Error al cargar configuración', 'error'))
      .finally(() => setLoading(false));
  }, []);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await svc.update(form);
      toast('Configuración guardada');
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="flex h-64 items-center justify-center"><Spinner size="lg" /></div>;

  const isAdmin = ['admin', 'superadmin'].includes(user?.rol);

  return (
    <div className="p-6 max-w-2xl">
      <div className="mb-6">
        <h1 className="text-lg font-semibold text-gray-900">Configuración</h1>
        <p className="text-sm text-gray-500">Datos de tu empresa</p>
      </div>

      <div className="rounded-xl border border-gray-200 bg-white shadow-sm p-6">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="label">Razón social *</label>
            <input required className="input" disabled={!isAdmin} value={form.business_name} onChange={set('business_name')} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">RUC</label>
              <input className="input" disabled={!isAdmin} value={form.business_ruc} onChange={set('business_ruc')} />
            </div>
            <div>
              <label className="label">Teléfono</label>
              <input className="input" disabled={!isAdmin} value={form.business_phone} onChange={set('business_phone')} />
            </div>
          </div>
          <div>
            <label className="label">Dirección</label>
            <input className="input" disabled={!isAdmin} value={form.business_address} onChange={set('business_address')} />
          </div>
          <div>
            <label className="label">Email de negocio</label>
            <input type="email" className="input" disabled={!isAdmin} value={form.business_email} onChange={set('business_email')} />
          </div>
          {isAdmin && (
            <div className="flex justify-end pt-2">
              <button type="submit" disabled={saving} className="btn-primary flex items-center gap-2">
                {saving && <Spinner size="sm" />} Guardar cambios
              </button>
            </div>
          )}
        </form>
      </div>

      {/* Info sesión */}
      <div className="mt-6 rounded-xl border border-gray-200 bg-white shadow-sm p-6">
        <h2 className="text-sm font-semibold text-gray-900 mb-3">Tu perfil</h2>
        <dl className="space-y-2 text-sm">
          <div className="flex gap-2"><dt className="text-gray-500 w-28">Nombre:</dt><dd className="text-gray-900">{user?.nombre_completo || '—'}</dd></div>
          <div className="flex gap-2"><dt className="text-gray-500 w-28">Email:</dt><dd className="text-gray-900">{user?.email}</dd></div>
          <div className="flex gap-2"><dt className="text-gray-500 w-28">Rol:</dt><dd className="text-gray-900 capitalize">{user?.rol}</dd></div>
        </dl>
      </div>
    </div>
  );
}
