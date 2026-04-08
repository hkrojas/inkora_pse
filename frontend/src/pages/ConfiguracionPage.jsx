import { useState, useEffect } from 'react';
import { tenant as svc } from '../services/tenant';
import Spinner from '../components/ui/Spinner';
import { useToast } from '../components/ui/Toast';
import { useAuth } from '../context/AuthContext';

function StatusBadge({ ok, labelOk, labelNo }) {
  return ok
    ? <span className="inline-flex items-center gap-1 text-sm font-medium text-green-700"><span className="h-2 w-2 rounded-full bg-green-500" />{labelOk}</span>
    : <span className="inline-flex items-center gap-1 text-sm font-medium text-gray-400"><span className="h-2 w-2 rounded-full bg-gray-300" />{labelNo}</span>;
}

function ReadOnlyField({ label, value }) {
  return (
    <div>
      <dt className="text-xs font-medium text-gray-500 mb-1">{label}</dt>
      <dd className="text-sm text-gray-900 bg-gray-50 rounded-lg px-3 py-2 border border-gray-200">{value || <span className="text-gray-400 italic">No configurado</span>}</dd>
    </div>
  );
}

export default function ConfiguracionPage() {
  const { user } = useAuth();
  const toast = useToast();
  const [tenantData, setTenantData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [phone, setPhone] = useState('');

  useEffect(() => {
    svc.get().then((t) => {
      setTenantData(t);
      setPhone(t.business_phone || '');
    }).catch(() => toast('Error al cargar configuración', 'error'))
      .finally(() => setLoading(false));
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const updated = await svc.update({ business_phone: phone });
      setTenantData(updated);
      toast('Teléfono actualizado');
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="flex h-64 items-center justify-center"><Spinner size="lg" /></div>;

  const isAdmin = ['admin', 'superadmin'].includes(user?.rol);

  return (
    <div className="p-6 max-w-2xl space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-gray-900">Configuración</h1>
        <p className="text-sm text-gray-500">Datos de tu empresa</p>
      </div>

      {/* Perfil de empresa */}
      <div className="rounded-xl border border-gray-200 bg-white shadow-sm p-6">
        <h2 className="text-sm font-semibold text-gray-900 mb-4">Perfil de empresa</h2>
        <dl className="space-y-4">
          {tenantData?.logo_filename && (
            <div>
              <dt className="text-xs font-medium text-gray-500 mb-2">Logo</dt>
              <dd><img src={tenantData.logo_filename} alt="Logo" className="h-14 object-contain rounded" /></dd>
            </div>
          )}
          <ReadOnlyField label="Razón social" value={tenantData?.business_name} />
          <ReadOnlyField label="RUC" value={tenantData?.business_ruc} />
          <ReadOnlyField label="Dirección fiscal" value={tenantData?.business_address} />
        </dl>

        {isAdmin && (
          <form onSubmit={handleSubmit} className="mt-5 pt-4 border-t border-gray-100">
            <div className="flex items-end gap-3">
              <div className="flex-1">
                <label className="text-xs font-medium text-gray-500 block mb-1">Teléfono de contacto</label>
                <input
                  className="input"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="+51 999 999 999"
                />
              </div>
              <button type="submit" disabled={saving} className="btn-primary flex items-center gap-2">
                {saving && <Spinner size="sm" />} Guardar
              </button>
            </div>
          </form>
        )}
      </div>

      {/* Configuración fiscal */}
      <div className="rounded-xl border border-gray-200 bg-white shadow-sm p-6">
        <h2 className="text-sm font-semibold text-gray-900 mb-1">Configuración fiscal</h2>
        <p className="text-xs text-gray-500 mb-4">Estado de integración con SUNAT y ApisPeru. Los valores son confidenciales y solo visibles para el superadministrador.</p>
        <dl className="space-y-3">
          <div className="flex items-center justify-between py-2 border-b border-gray-100">
            <dt className="text-sm text-gray-700">Token ApisPeru (facturación electrónica)</dt>
            <dd><StatusBadge ok={tenantData?.has_apisperu_token} labelOk="Configurado" labelNo="No configurado" /></dd>
          </div>
          <div className="flex items-center justify-between py-2 border-b border-gray-100">
            <dt className="text-sm text-gray-700">Credenciales SOL (usuario y certificado)</dt>
            <dd><StatusBadge ok={tenantData?.has_sunat_credentials} labelOk="Configuradas" labelNo="Pendiente" /></dd>
          </div>
          <div className="flex items-center justify-between py-2">
            <dt className="text-sm text-gray-700">Certificado digital (.pfx)</dt>
            <dd><StatusBadge ok={tenantData?.has_sunat_cert} labelOk="Cargado" labelNo="No cargado" /></dd>
          </div>
        </dl>

        <div className="mt-4 rounded-lg bg-blue-50 border border-blue-100 px-4 py-3 text-xs text-blue-700">
          Para actualizar credenciales fiscales (token, usuario SOL, certificado), contacta al administrador de la plataforma.
        </div>
      </div>

      {/* Tu perfil */}
      <div className="rounded-xl border border-gray-200 bg-white shadow-sm p-6">
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
