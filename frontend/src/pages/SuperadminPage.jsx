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

function sanitizeRuc(value) {
  return value.replace(/\D/g, '').slice(0, 11);
}

function getTenantLookupFields(data) {
  return {
    business_name: data?.razon_social || '',
    business_address: data?.direccion && data.direccion !== '-' ? data.direccion : '',
  };
}

function ValidationNotice({ result }) {
  if (!result) return null;

  const toneClasses = result.valid
    ? 'border-green-200 bg-green-50 text-green-700'
    : 'border-red-200 bg-red-50 text-red-700';

  return (
    <div className={`rounded-lg border px-3 py-2 text-xs ${toneClasses}`}>
      <p className="font-medium">{result.message}</p>
      {result.token_company_ruc && (
        <p className="mt-1 opacity-80">RUC del token: {result.token_company_ruc}</p>
      )}
      {result.provider_detail && (
        <p className="mt-1 opacity-80">Detalle proveedor: {result.provider_detail}</p>
      )}
    </div>
  );
}

/* ────────────────────────────────────────────────────────────── */
/* Modal: Editar tenant existente                                 */
/* ────────────────────────────────────────────────────────────── */
function TenantModal({ tenant, onClose, onSaved, onDeleted }) {
  const toast = useToast();
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [lookupLoading, setLookupLoading] = useState(false);
  const [tokenValidationLoading, setTokenValidationLoading] = useState(false);
  const [tokenValidationResult, setTokenValidationResult] = useState(null);
  const [form, setForm] = useState({
    business_name:    tenant.business_name    || '',
    business_ruc:     tenant.business_ruc     || '',
    business_address: tenant.business_address || '',
    is_active:        tenant.is_active ?? true,
    apisperu_token:   '',
    apisperu_url:     '',
  });

  const set = (k) => (e) => {
    const rawValue = e.target.type === 'checkbox' ? e.target.checked : e.target.value;
    const val = k === 'business_ruc' ? sanitizeRuc(rawValue) : rawValue;
    if (k === 'apisperu_token' || k === 'apisperu_url' || k === 'business_ruc') {
      setTokenValidationResult(null);
    }
    setForm((f) => ({ ...f, [k]: val }));
  };

  const handleLookupRuc = async () => {
    if (form.business_ruc.length !== 11) {
      toast('Ingresa un RUC válido de 11 dígitos', 'error');
      return;
    }

    setLookupLoading(true);
    try {
      const data = await svc.consultarDocumento(form.business_ruc);
      const nextFields = getTenantLookupFields(data);
      setForm((current) => ({
        ...current,
        ...nextFields,
      }));
      toast('Datos de empresa completados desde SUNAT');
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      setLookupLoading(false);
    }
  };

  const handleValidateToken = async () => {
    const token = form.apisperu_token.trim();
    if (!token) {
      toast('Ingresa un token de ApisPeru para validarlo', 'error');
      return null;
    }

    setTokenValidationLoading(true);
    try {
      const result = await svc.validateApisPeruToken({
        token,
        api_url: form.apisperu_url.trim() || undefined,
        business_ruc: form.business_ruc.trim() || undefined,
      });
      setTokenValidationResult(result);
      toast(
        result.valid ? 'Token validado correctamente' : result.message,
        result.valid ? 'success' : 'error',
      );
      return result;
    } catch (err) {
      const fallback = {
        valid: false,
        message: err.message || 'No se pudo validar el token de ApisPeru.',
        provider_detail: null,
      };
      setTokenValidationResult(fallback);
      toast(fallback.message, 'error');
      return fallback;
    } finally {
      setTokenValidationLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      if (form.apisperu_token.trim()) {
        const validation = tokenValidationResult?.valid
          ? tokenValidationResult
          : await handleValidateToken();
        if (!validation?.valid) {
          return;
        }
      }

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

  const handleDelete = async () => {
    const confirmed = window.confirm(
      `Se eliminará el tenant "${tenant.business_name}". Esta acción no se puede deshacer.`,
    );
    if (!confirmed) return;

    setDeleting(true);
    try {
      await svc.deleteTenant(tenant.id);
      toast('Tenant eliminado');
      onDeleted(tenant.id);
      onClose();
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      setDeleting(false);
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
                  <div className="flex items-center gap-2">
                    <input className="input font-mono" value={form.business_ruc} onChange={set('business_ruc')} maxLength={11} />
                    <button
                      type="button"
                      onClick={handleLookupRuc}
                      disabled={lookupLoading || form.business_ruc.length !== 11}
                      className="btn-secondary whitespace-nowrap"
                    >
                      {lookupLoading ? 'Consultando...' : 'Consultar RUC'}
                    </button>
                  </div>
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

          <div className="border-t border-gray-100 pt-4">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Token ApisPeru (empresa)</p>
            <p className="text-xs text-gray-400 mb-3">
              Token de empresa generado por ApisPeru — sin fecha de expiración.
              Estado actual: <StatusDot ok={tenant.has_apisperu_token} />
            </p>
            <div className="space-y-3">
              <div>
                <label className="text-xs font-medium text-gray-600 block mb-1">Nuevo token</label>
                <div className="flex items-center gap-2">
                  <input
                    className="input font-mono text-xs"
                    value={form.apisperu_token}
                    onChange={set('apisperu_token')}
                    placeholder="apis-token-xxxxx.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                  />
                  <button
                    type="button"
                    onClick={handleValidateToken}
                    disabled={tokenValidationLoading || !form.apisperu_token.trim()}
                    className="btn-secondary whitespace-nowrap"
                  >
                    {tokenValidationLoading ? 'Validando...' : 'Probar token'}
                  </button>
                </div>
                <p className="text-xs text-gray-400 mt-1">Dejar vacío para no cambiar el token actual.</p>
                <p className="text-xs text-gray-400 mt-1">Si ingresas un token nuevo, el sistema lo validará antes de guardar y rechazará el cambio si no pertenece al RUC del tenant.</p>
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
              <ValidationNotice result={tokenValidationResult} />
            </div>
          </div>

          <div className="flex items-center justify-between gap-2 pt-2 border-t border-gray-100">
            <button
              type="button"
              onClick={handleDelete}
              disabled={saving || deleting}
              className="text-sm font-medium text-red-600 hover:text-red-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {deleting ? 'Eliminando...' : 'Eliminar tenant'}
            </button>
            <div className="flex justify-end gap-2">
              <button type="button" onClick={onClose} className="btn-secondary">Cancelar</button>
              <button type="submit" disabled={saving || deleting} className="btn-primary flex items-center gap-2">
                {saving && <Spinner size="sm" />} Guardar
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ────────────────────────────────────────────────────────────── */
/* Modal: Crear tenant nuevo                                      */
/* ────────────────────────────────────────────────────────────── */
function CreateTenantModal({ onClose, onCreated }) {
  const toast = useToast();
  const [saving, setSaving] = useState(false);
  const [lookupLoading, setLookupLoading] = useState(false);
  const [tokenValidationLoading, setTokenValidationLoading] = useState(false);
  const [tokenValidationResult, setTokenValidationResult] = useState(null);
  const [form, setForm] = useState({
    business_name: '',
    business_ruc: '',
    business_address: '',
    apisperu_token: '',
    apisperu_url: '',
  });

  const set = (k) => (e) => {
    const value = k === 'business_ruc' ? sanitizeRuc(e.target.value) : e.target.value;
    if (k === 'apisperu_token' || k === 'apisperu_url' || k === 'business_ruc') {
      setTokenValidationResult(null);
    }
    setForm((f) => ({ ...f, [k]: value }));
  };

  const handleLookupRuc = async () => {
    if (form.business_ruc.length !== 11) {
      toast('Ingresa un RUC válido de 11 dígitos', 'error');
      return;
    }

    setLookupLoading(true);
    try {
      const data = await svc.consultarDocumento(form.business_ruc);
      const nextFields = getTenantLookupFields(data);
      setForm((current) => ({
        ...current,
        ...nextFields,
      }));
      toast('Datos de empresa completados desde SUNAT');
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      setLookupLoading(false);
    }
  };

  const handleValidateToken = async () => {
    const token = form.apisperu_token.trim();
    if (!token) {
      toast('Ingresa un token de ApisPeru para validarlo', 'error');
      return null;
    }

    setTokenValidationLoading(true);
    try {
      const result = await svc.validateApisPeruToken({
        token,
        api_url: form.apisperu_url.trim() || undefined,
        business_ruc: form.business_ruc.trim() || undefined,
      });
      setTokenValidationResult(result);
      toast(
        result.valid ? 'Token validado correctamente' : result.message,
        result.valid ? 'success' : 'error',
      );
      return result;
    } catch (err) {
      const fallback = {
        valid: false,
        message: err.message || 'No se pudo validar el token de ApisPeru.',
        provider_detail: null,
      };
      setTokenValidationResult(fallback);
      toast(fallback.message, 'error');
      return fallback;
    } finally {
      setTokenValidationLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.business_name.trim() || !form.business_ruc.trim()) {
      toast('Razón social y RUC son obligatorios', 'error');
      return;
    }
    setSaving(true);
    try {
      if (form.apisperu_token.trim()) {
        const validation = tokenValidationResult?.valid
          ? tokenValidationResult
          : await handleValidateToken();
        if (!validation?.valid) {
          return;
        }
      }

      const payload = {
        business_name: form.business_name.trim(),
        business_ruc: form.business_ruc.trim(),
      };
      if (form.business_address.trim()) payload.business_address = form.business_address.trim();
      if (form.apisperu_token.trim())   payload.apisperu_token   = form.apisperu_token.trim();
      if (form.apisperu_url.trim())     payload.apisperu_url     = form.apisperu_url.trim();

      const created = await svc.createTenant(payload);
      toast('Tenant creado correctamente');
      onCreated(created);
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
          <h2 className="text-sm font-semibold text-gray-900">Nuevo tenant</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-lg leading-none">×</button>
        </div>

        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Datos de empresa</p>
            <div className="space-y-3">
              <div>
                <label className="text-xs font-medium text-gray-600 block mb-1">Razón social *</label>
                <input className="input" value={form.business_name} onChange={set('business_name')} required />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600 block mb-1">RUC *</label>
                <div className="flex items-center gap-2">
                  <input className="input font-mono" value={form.business_ruc} onChange={set('business_ruc')} maxLength={11} required />
                  <button
                    type="button"
                    onClick={handleLookupRuc}
                    disabled={lookupLoading || form.business_ruc.length !== 11}
                    className="btn-secondary whitespace-nowrap"
                  >
                    {lookupLoading ? 'Consultando...' : 'Consultar RUC'}
                  </button>
                </div>
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600 block mb-1">Dirección fiscal</label>
                <input className="input" value={form.business_address} onChange={set('business_address')} />
              </div>
            </div>
          </div>

          <div className="border-t border-gray-100 pt-4">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Token ApisPeru (opcional)</p>
            <p className="text-xs text-gray-400 mb-3">
              Puedes configurarlo ahora o más tarde editando el tenant.
            </p>
            <div className="space-y-3">
              <div>
                <label className="text-xs font-medium text-gray-600 block mb-1">Token de empresa</label>
                <div className="flex items-center gap-2">
                  <input
                    className="input font-mono text-xs"
                    value={form.apisperu_token}
                    onChange={set('apisperu_token')}
                    placeholder="apis-token-xxxxx.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                  />
                  <button
                    type="button"
                    onClick={handleValidateToken}
                    disabled={tokenValidationLoading || !form.apisperu_token.trim()}
                    className="btn-secondary whitespace-nowrap"
                  >
                    {tokenValidationLoading ? 'Validando...' : 'Probar token'}
                  </button>
                </div>
                <p className="text-xs text-gray-400 mt-1">Si ingresas un token, el sistema lo validará antes de crear el tenant y verificará si corresponde al RUC indicado.</p>
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
              <ValidationNotice result={tokenValidationResult} />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-gray-100">
            <button type="button" onClick={onClose} className="btn-secondary">Cancelar</button>
            <button type="submit" disabled={saving} className="btn-primary flex items-center gap-2">
              {saving && <Spinner size="sm" />} Crear tenant
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ────────────────────────────────────────────────────────────── */
/* Modal: Crear usuario para un tenant                            */
/* ────────────────────────────────────────────────────────────── */
function CreateUserModal({ tenant, onClose, onCreated }) {
  const toast = useToast();
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    email: '',
    nombre_completo: '',
    password: '',
    rol: 'admin',
  });

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.email.trim() || !form.password.trim()) {
      toast('Email y contraseña son obligatorios', 'error');
      return;
    }
    setSaving(true);
    try {
      await svc.createUser(tenant.id, {
        email: form.email.trim(),
        nombre_completo: form.nombre_completo.trim() || undefined,
        password: form.password,
        rol: form.rol,
      });
      toast('Usuario creado correctamente');
      onCreated();
      onClose();
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div className="w-full max-w-md rounded-2xl bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-gray-100 px-6 py-4">
          <h2 className="text-sm font-semibold text-gray-900">Nuevo usuario — {tenant.business_name}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-lg leading-none">×</button>
        </div>

        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">
          <div className="space-y-3">
            <div>
              <label className="text-xs font-medium text-gray-600 block mb-1">Email *</label>
              <input type="email" className="input" value={form.email} onChange={set('email')} required />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600 block mb-1">Nombre completo</label>
              <input className="input" value={form.nombre_completo} onChange={set('nombre_completo')} />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600 block mb-1">Contraseña *</label>
              <input type="password" className="input" value={form.password} onChange={set('password')} required />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600 block mb-1">Rol</label>
              <select className="input" value={form.rol} onChange={set('rol')}>
                <option value="admin">Admin</option>
                <option value="vendedor">Vendedor</option>
                <option value="operador">Operador</option>
              </select>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-gray-100">
            <button type="button" onClick={onClose} className="btn-secondary">Cancelar</button>
            <button type="submit" disabled={saving} className="btn-primary flex items-center gap-2">
              {saving && <Spinner size="sm" />} Crear usuario
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ────────────────────────────────────────────────────────────── */
/* Página principal                                               */
/* ────────────────────────────────────────────────────────────── */
export default function SuperadminPage() {
  const { user } = useAuth();
  const toast = useToast();
  const [tenants, setTenants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null);
  const [creating, setCreating] = useState(false);
  const [addingUserTo, setAddingUserTo] = useState(null);

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

  const handleCreated = (newTenant) => {
    setTenants((prev) => [newTenant, ...prev]);
  };

  const handleDeleted = (tenantId) => {
    setTenants((prev) => prev.filter((tenant) => tenant.id !== tenantId));
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-gray-900">Superadmin</h1>
          <p className="text-sm text-gray-500">Gestión de tenants y configuración fiscal</p>
        </div>
        <button onClick={() => setCreating(true)} className="btn-primary text-sm">
          + Nuevo tenant
        </button>
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
                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => setEditing(t)}
                        className="text-xs text-blue-600 hover:text-blue-800 font-medium"
                      >
                        Editar
                      </button>
                      <button
                        onClick={() => setAddingUserTo(t)}
                        className="text-xs text-gray-500 hover:text-gray-700 font-medium"
                      >
                        + Usuario
                      </button>
                    </div>
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
          onDeleted={handleDeleted}
        />
      )}

      {creating && (
        <CreateTenantModal
          onClose={() => setCreating(false)}
          onCreated={handleCreated}
        />
      )}

      {addingUserTo && (
        <CreateUserModal
          tenant={addingUserTo}
          onClose={() => setAddingUserTo(null)}
          onCreated={() => {}}
        />
      )}
    </div>
  );
}
