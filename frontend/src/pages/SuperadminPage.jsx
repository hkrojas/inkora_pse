import { useCallback, useEffect, useState } from 'react';
import {
  AlertCircle,
  Building2,
  Gauge,
  KeyRound,
  PencilLine,
  Plus,
  RefreshCw,
  ShieldCheck,
  ShieldOff,
  Trash2,
  UserPlus,
  Users,
} from 'lucide-react';
import { Navigate } from 'react-router-dom';
import { superadmin as svc } from '../services/superadmin';
import Modal from '../components/ui/Modal';
import Spinner from '../components/ui/Spinner';
import Badge from '../components/ui/Badge';
import EmptyState from '../components/ui/EmptyState';
import { useToast } from '../components/ui/Toast';
import CustomSelect from '../components/ui/CustomSelect';
import { useAuth } from '../context/AuthContext';

function sanitizeRuc(value) {
  return value.replace(/\D/g, '').slice(0, 11);
}

function getTenantLookupFields(data) {
  return {
    business_name: data?.razon_social || '',
    business_address: data?.direccion && data.direccion !== '-' ? data.direccion : '',
  };
}

function StatusDot({ ok }) {
  return (
    <span className={`badge status-dot ${ok ? 'badge--success' : 'badge--neutral'}`}>
      <span className={ok ? 'status-dot-indicator' : 'status-dot-indicator text-[var(--text-tertiary)]'} />
      {ok ? 'configurado' : 'no configurado'}
    </span>
  );
}

function ValidationNotice({ result }) {
  if (!result) return null;

  const toneClass = result.valid ? 'ink-inline-alert-success' : 'ink-inline-alert-error';

  return (
    <div className={`ink-inline-alert ${toneClass}`}>
      <div className="space-y-1">
        <p className="font-medium">{result.message}</p>
        {result.token_company_ruc && (
          <p className="text-xs opacity-80">RUC del token: {result.token_company_ruc}</p>
        )}
        {result.provider_detail && (
          <p className="text-xs opacity-80">Detalle proveedor: {result.provider_detail}</p>
        )}
      </div>
    </div>
  );
}

function SectionHeader({ kicker, title, copy }) {
  return (
    <div className="mb-4">
      <p className="page-kicker">{kicker}</p>
      <h3 className="mt-1 font-heading text-base font-semibold tracking-[-0.02em] text-[var(--text-primary)]">{title}</h3>
      {copy ? <p className="mt-1.5 max-w-2xl text-sm leading-5 text-[var(--text-secondary)]">{copy}</p> : null}
    </div>
  );
}

function TenantModal({ tenant, onClose, onSaved, onDeleted }) {
  const toast = useToast();
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [lookupLoading, setLookupLoading] = useState(false);
  const [tokenValidationLoading, setTokenValidationLoading] = useState(false);
  const [tokenValidationResult, setTokenValidationResult] = useState(null);
  const [form, setForm] = useState({
    business_name: tenant.business_name || '',
    business_ruc: tenant.business_ruc || '',
    business_address: tenant.business_address || '',
    is_active: tenant.is_active ?? true,
    apisperu_token: '',
    apisperu_url: '',
  });

  const setField = (key) => (event) => {
    const rawValue =
      event.target.type === 'checkbox' ? event.target.checked : event.target.value;
    const value = key === 'business_ruc' ? sanitizeRuc(rawValue) : rawValue;

    if (key === 'business_ruc' || key === 'apisperu_token' || key === 'apisperu_url') {
      setTokenValidationResult(null);
    }

    setForm((current) => ({ ...current, [key]: value }));
  };

  const handleLookupRuc = async () => {
    if (form.business_ruc.length !== 11) {
      toast('Ingresa un RUC valido de 11 digitos', 'error');
      return;
    }

    setLookupLoading(true);
    try {
      const data = await svc.consultarDocumento(form.business_ruc);
      setForm((current) => ({
        ...current,
        ...getTenantLookupFields(data),
      }));
      toast('Datos de empresa completados desde SUNAT');
    } catch (error) {
      toast(error.message, 'error');
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
    } catch (error) {
      const fallback = {
        valid: false,
        message: error.message || 'No se pudo validar el token de ApisPeru.',
        provider_detail: null,
      };
      setTokenValidationResult(fallback);
      toast(fallback.message, 'error');
      return fallback;
    } finally {
      setTokenValidationLoading(false);
    }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSaving(true);

    try {
      if (form.apisperu_token.trim()) {
        const validation = tokenValidationResult?.valid
          ? tokenValidationResult
          : await handleValidateToken();

        if (!validation?.valid) return;
      }

      const payload = {};

      if (form.business_name !== (tenant.business_name || '')) {
        payload.business_name = form.business_name;
      }
      if (form.business_ruc !== (tenant.business_ruc || '')) {
        payload.business_ruc = form.business_ruc;
      }
      if (form.business_address !== (tenant.business_address || '')) {
        payload.business_address = form.business_address;
      }
      if (form.is_active !== (tenant.is_active ?? true)) {
        payload.is_active = form.is_active;
      }
      if (form.apisperu_token.trim()) {
        payload.apisperu_token = form.apisperu_token.trim();
      }
      if (form.apisperu_url.trim()) {
        payload.apisperu_url = form.apisperu_url.trim();
      }

      if (Object.keys(payload).length === 0) {
        onClose();
        return;
      }

      const updated = await svc.updateTenant(tenant.id, payload);
      toast('Tenant actualizado');
      onSaved(updated);
      onClose();
    } catch (error) {
      toast(error.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    const confirmed = window.confirm(
      `Se eliminara el tenant "${tenant.business_name}". Esta accion no se puede deshacer.`,
    );

    if (!confirmed) return;

    setDeleting(true);
    try {
      await svc.deleteTenant(tenant.id);
      toast('Tenant eliminado');
      onDeleted(tenant.id);
      onClose();
    } catch (error) {
      toast(error.message, 'error');
    } finally {
      setDeleting(false);
    }
  };

  return (
    <Modal open={Boolean(tenant)} onClose={onClose} title={`Editar tenant / ${tenant.business_name}`} size="lg">
      <form onSubmit={handleSubmit} className="space-y-6">
        <section className="card-raw" data-label="empresa">
          <SectionHeader
            kicker="Identidad"
            title="Base fiscal del tenant"
            copy="Manten la razon social, RUC y direccion alineados con la identidad tributaria activa."
          />

          <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_220px]">
            <div>
              <label className="label">Razon social</label>
              <input className="input" value={form.business_name} onChange={setField('business_name')} />
            </div>

            <label className="flex items-end gap-3 border border-[var(--border-subtle)] bg-[var(--bg-surface-low)] px-4 py-3">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={setField('is_active')}
                className="mt-0.5 h-4 w-4 rounded"
              />
              <span className="block">
                <span className="label mb-1">Estado</span>
                <span className="text-sm text-[var(--text-primary)]">Tenant activo</span>
              </span>
            </label>
          </div>

          <div className="mt-4 grid gap-4 md:grid-cols-[minmax(0,1fr)_auto]">
            <div>
              <label className="label">RUC</label>
              <input
                className="input font-mono"
                value={form.business_ruc}
                onChange={setField('business_ruc')}
                maxLength={11}
              />
            </div>

            <div className="flex items-end">
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

          <div className="mt-4">
            <label className="label">Direccion fiscal</label>
            <input className="input" value={form.business_address} onChange={setField('business_address')} />
          </div>
        </section>

        <section className="ink-card p-6">
          <SectionHeader
            kicker="ApisPeru"
            title="Token de empresa"
            copy="Si cargas un token nuevo, el backend lo valida antes de persistirlo y rechaza el cambio si no coincide con el RUC."
          />

          <div className="flex flex-wrap items-center gap-3">
            <span className="label mb-0">Estado actual</span>
            <StatusDot ok={tenant.has_apisperu_token} />
          </div>

          <div className="mt-4 grid gap-4 md:grid-cols-[minmax(0,1fr)_auto]">
            <div>
              <label className="label">Nuevo token</label>
              <input
                className="input font-mono text-xs"
                value={form.apisperu_token}
                onChange={setField('apisperu_token')}
                placeholder="apis-token-xxxxx.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
              />
              <p className="mt-2 text-xs text-[var(--text-secondary)]">
                Deja el campo vacio para mantener el token actual.
              </p>
            </div>

            <div className="flex items-end">
              <button
                type="button"
                onClick={handleValidateToken}
                disabled={tokenValidationLoading || !form.apisperu_token.trim()}
                className="btn-secondary whitespace-nowrap"
              >
                {tokenValidationLoading ? 'Validando...' : 'Probar token'}
              </button>
            </div>
          </div>

          <div className="mt-4">
            <label className="label">URL ApisPeru</label>
            <input
              className="input text-xs"
              value={form.apisperu_url}
              onChange={setField('apisperu_url')}
              placeholder="https://facturacion.apisperu.com/api/v1"
            />
          </div>

          <div className="mt-4">
            <ValidationNotice result={tokenValidationResult} />
          </div>
        </section>

        <div className="flex flex-col gap-3 border-t border-[var(--border-subtle)] pt-4 sm:flex-row sm:items-center sm:justify-between">
          <button
            type="button"
            onClick={handleDelete}
            disabled={saving || deleting}
            className="inline-flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.18em] text-[var(--color-error)] transition-opacity hover:opacity-75 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Trash2 className="h-4 w-4" />
            {deleting ? 'Eliminando...' : 'Eliminar tenant'}
          </button>

          <div className="flex flex-wrap justify-end gap-2">
            <button type="button" onClick={onClose} className="btn-secondary">
              Cancelar
            </button>
            <button type="submit" disabled={saving || deleting} className="btn-primary flex items-center gap-2">
              {saving ? <Spinner size="sm" /> : null}
              Guardar
            </button>
          </div>
        </div>
      </form>
    </Modal>
  );
}

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

  const setField = (key) => (event) => {
    const value = key === 'business_ruc' ? sanitizeRuc(event.target.value) : event.target.value;

    if (key === 'business_ruc' || key === 'apisperu_token' || key === 'apisperu_url') {
      setTokenValidationResult(null);
    }

    setForm((current) => ({ ...current, [key]: value }));
  };

  const handleLookupRuc = async () => {
    if (form.business_ruc.length !== 11) {
      toast('Ingresa un RUC valido de 11 digitos', 'error');
      return;
    }

    setLookupLoading(true);
    try {
      const data = await svc.consultarDocumento(form.business_ruc);
      setForm((current) => ({
        ...current,
        ...getTenantLookupFields(data),
      }));
      toast('Datos de empresa completados desde SUNAT');
    } catch (error) {
      toast(error.message, 'error');
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
    } catch (error) {
      const fallback = {
        valid: false,
        message: error.message || 'No se pudo validar el token de ApisPeru.',
        provider_detail: null,
      };
      setTokenValidationResult(fallback);
      toast(fallback.message, 'error');
      return fallback;
    } finally {
      setTokenValidationLoading(false);
    }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!form.business_name.trim() || !form.business_ruc.trim()) {
      toast('Razon social y RUC son obligatorios', 'error');
      return;
    }

    setSaving(true);
    try {
      if (form.apisperu_token.trim()) {
        const validation = tokenValidationResult?.valid
          ? tokenValidationResult
          : await handleValidateToken();

        if (!validation?.valid) return;
      }

      const payload = {
        business_name: form.business_name.trim(),
        business_ruc: form.business_ruc.trim(),
      };

      if (form.business_address.trim()) {
        payload.business_address = form.business_address.trim();
      }
      if (form.apisperu_token.trim()) {
        payload.apisperu_token = form.apisperu_token.trim();
      }
      if (form.apisperu_url.trim()) {
        payload.apisperu_url = form.apisperu_url.trim();
      }

      const created = await svc.createTenant(payload);
      toast('Tenant creado correctamente');
      onCreated(created);
      onClose();
    } catch (error) {
      toast(error.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal open={true} onClose={onClose} title="Nuevo tenant" size="lg">
      <form onSubmit={handleSubmit} className="space-y-6">
        <section className="card-raw" data-label="alta">
          <SectionHeader
            kicker="Onboarding"
            title="Crear empresa operativa"
            copy="El alta fiscal parte por la identidad basica. El token de ApisPeru sigue siendo opcional."
          />

          <div className="space-y-4">
            <div>
              <label className="label">Razon social *</label>
              <input
                className="input"
                value={form.business_name}
                onChange={setField('business_name')}
                required
              />
            </div>

            <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_auto]">
              <div>
                <label className="label">RUC *</label>
                <input
                  className="input font-mono"
                  value={form.business_ruc}
                  onChange={setField('business_ruc')}
                  maxLength={11}
                  required
                />
              </div>

              <div className="flex items-end">
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
              <label className="label">Direccion fiscal</label>
              <input
                className="input"
                value={form.business_address}
                onChange={setField('business_address')}
              />
            </div>
          </div>
        </section>

        <section className="ink-card p-6">
          <SectionHeader
            kicker="ApisPeru"
            title="Token inicial"
            copy="Puedes guardarlo ahora o dejarlo para despues. Si lo envias, se valida antes de crear el tenant."
          />

          <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_auto]">
            <div>
              <label className="label">Token de empresa</label>
              <input
                className="input font-mono text-xs"
                value={form.apisperu_token}
                onChange={setField('apisperu_token')}
                placeholder="apis-token-xxxxx.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
              />
            </div>

            <div className="flex items-end">
              <button
                type="button"
                onClick={handleValidateToken}
                disabled={tokenValidationLoading || !form.apisperu_token.trim()}
                className="btn-secondary whitespace-nowrap"
              >
                {tokenValidationLoading ? 'Validando...' : 'Probar token'}
              </button>
            </div>
          </div>

          <div className="mt-4">
            <label className="label">URL ApisPeru</label>
            <input
              className="input text-xs"
              value={form.apisperu_url}
              onChange={setField('apisperu_url')}
              placeholder="https://facturacion.apisperu.com/api/v1"
            />
          </div>

          <div className="mt-4">
            <ValidationNotice result={tokenValidationResult} />
          </div>
        </section>

        <div className="flex flex-wrap justify-end gap-2 border-t border-[var(--border-subtle)] pt-4">
          <button type="button" onClick={onClose} className="btn-secondary">
            Cancelar
          </button>
          <button type="submit" disabled={saving} className="btn-primary flex items-center gap-2">
            {saving ? <Spinner size="sm" /> : null}
            Crear tenant
          </button>
        </div>
      </form>
    </Modal>
  );
}

function CreateUserModal({ tenant, onClose, onCreated }) {
  const toast = useToast();
  const [saving, setSaving] = useState(false);
  const [result, setResult] = useState(null); // { temp_password, email }
  const [copied, setCopied] = useState(false);
  const [form, setForm] = useState({
    email: '',
    nombre_completo: '',
    rol: 'admin',
  });

  const setField = (key) => (event) => {
    setForm((current) => ({ ...current, [key]: event.target.value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!form.email.trim()) {
      toast('El email es obligatorio', 'error');
      return;
    }
    setSaving(true);
    try {
      const data = await svc.createUser(tenant.id, {
        email: form.email.trim(),
        nombre_completo: form.nombre_completo.trim() || undefined,
        rol: form.rol,
      });
      setResult({ temp_password: data.temp_password, email: data.user.email });
    } catch (error) {
      toast(error.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(result.temp_password).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const handleConfirm = () => {
    onCreated();
    onClose();
  };

  if (result) {
    return (
      <Modal open={true} onClose={handleConfirm} title="Usuario creado" size="md">
        <div className="space-y-4">
          <div className="ink-inline-alert ink-inline-alert-warning">
            <p className="font-bold text-sm mb-2">Contraseña temporal — copiar ahora, no se puede recuperar</p>
            <div className="flex items-center gap-3">
              <p className="font-mono text-xl font-bold tracking-widest flex-1">{result.temp_password}</p>
              <button type="button" className="btn-secondary text-xs" onClick={handleCopy}>
                {copied ? '¡Copiado!' : 'Copiar'}
              </button>
            </div>
            <p className="text-xs mt-2 opacity-75">Para: {result.email}</p>
          </div>
          <p className="text-sm text-[var(--text-secondary)]">
            Envía esta contraseña al usuario por WhatsApp. Deberá cambiarla en su primer inicio de sesión.
            Una vez que cierres este diálogo, la contraseña no se podrá ver de nuevo.
          </p>
          <div className="flex justify-end border-t border-[var(--border-subtle)] pt-4">
            <button type="button" className="btn-primary" onClick={handleConfirm}>
              Entendido, ya copié la contraseña
            </button>
          </div>
        </div>
      </Modal>
    );
  }

  return (
    <Modal open={true} onClose={onClose} title={`Nuevo usuario / ${tenant.business_name}`} size="md">
      <form onSubmit={handleSubmit} className="space-y-6">
        <section className="card-raw" data-label="usuario">
          <SectionHeader
            kicker="Acceso"
            title="Alta de usuario"
            copy="La contraseña se genera automáticamente. Podrás copiarla en el siguiente paso."
          />

          <div className="space-y-4">
            <div>
              <label className="label">Email *</label>
              <input
                type="email"
                className="input"
                value={form.email}
                onChange={setField('email')}
                required
              />
            </div>

            <div>
              <label className="label">Nombre completo</label>
              <input
                className="input"
                value={form.nombre_completo}
                onChange={setField('nombre_completo')}
              />
            </div>

            <div>
              <label className="label">Rol</label>
              <CustomSelect
                value={form.rol}
                onChange={(v) => setForm((c) => ({ ...c, rol: v }))}
                options={[
                  { value: 'admin',    label: 'Admin' },
                  { value: 'vendedor', label: 'Vendedor' },
                  { value: 'operador', label: 'Operador' },
                ]}
              />
            </div>
          </div>
        </section>

        <div className="flex flex-wrap justify-end gap-2 border-t border-[var(--border-subtle)] pt-4">
          <button type="button" onClick={onClose} className="btn-secondary">
            Cancelar
          </button>
          <button type="submit" disabled={saving} className="btn-primary flex items-center gap-2">
            {saving ? <Spinner size="sm" /> : null}
            Crear usuario
          </button>
        </div>
      </form>
    </Modal>
  );
}

const ACTION_LABELS = {
  emit_fiscal_document: 'Factura/Boleta',
  emit_note: 'Nota crédito/débito',
  void_fiscal_document: 'Anulación',
  emit_guide: 'Guía remisión',
};

function TenantUsersModal({ tenant, onClose }) {
  const toast = useToast();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [resettingId, setResettingId] = useState(null);
  const [togglingId, setTogglingId] = useState(null);
  const [tempPassword, setTempPassword] = useState(null);
  const [addingUser, setAddingUser] = useState(false);

  const loadUsers = useCallback(async () => {
    setLoading(true);
    try {
      const data = await svc.tenantUsersDetail(tenant.id);
      setUsers(data);
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      setLoading(false);
    }
  }, [tenant.id, toast]);

  useEffect(() => { loadUsers(); }, [loadUsers]);

  const handleToggleActive = async (u) => {
    setTogglingId(u.id);
    try {
      await svc.toggleUserActive(u.id, !u.is_active);
      toast(u.is_active ? 'Usuario bloqueado' : 'Usuario activado');
      loadUsers();
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      setTogglingId(null);
    }
  };

  const handleResetPassword = async (u) => {
    const confirmed = window.confirm(`¿Resetear la contraseña de ${u.email}? Se generará una contraseña temporal.`);
    if (!confirmed) return;
    setResettingId(u.id);
    try {
      const result = await svc.resetUserPassword(u.id);
      setTempPassword(result);
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      setResettingId(null);
    }
  };

  const fmtDate = (iso) => {
    if (!iso) return '—';
    return new Date(iso).toLocaleString('es-PE', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
  };

  return (
    <Modal open={true} onClose={onClose} title={`Usuarios · ${tenant.business_name}`} size="xl">
      {tempPassword && (
        <div className="ink-inline-alert ink-inline-alert-warning mb-4">
          <div>
            <p className="font-bold text-sm mb-1">Contraseña temporal — copiar ahora, no se puede recuperar</p>
            <p className="font-mono text-lg font-bold tracking-widest">{tempPassword.temp_password}</p>
            <p className="text-xs mt-1 opacity-75">Para: {tempPassword.email}</p>
          </div>
          <button className="btn-secondary mt-3" onClick={() => setTempPassword(null)}>Entendido</button>
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-10">
          <Spinner size="lg" label="Cargando usuarios" hint="Calculando métricas de documentos..." />
        </div>
      ) : users.length === 0 ? (
        <EmptyState title="Sin usuarios" description="Este tenant no tiene usuarios registrados." />
      ) : (
        <div className="ink-table-card">
          <table className="ink-table">
            <thead>
              <tr>
                <th>Usuario</th>
                <th>Rol</th>
                <th>Último login</th>
                <th className="text-center">Cot.</th>
                <th className="text-center">Fact.</th>
                <th className="text-center">Bol.</th>
                <th className="text-center">NC</th>
                <th className="text-center">Guías</th>
                <th>Estado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} style={{ opacity: u.is_active ? 1 : 0.45 }}>
                  <td>
                    <p className="font-semibold text-sm">{u.email}</p>
                    {u.nombre_completo && <p className="text-xs text-[var(--text-secondary)] mt-0.5">{u.nombre_completo}</p>}
                  </td>
                  <td><Badge variant="info">{u.rol}</Badge></td>
                  <td className="text-xs text-[var(--text-secondary)]">{fmtDate(u.last_login_at)}</td>
                  <td className="text-center text-xs">
                    <span title={`Total: ${u.metrics.cotizaciones_total}`}>
                      {u.metrics.cotizaciones_mes_actual}
                      <span className="text-[var(--text-tertiary)] text-[10px]">/{u.metrics.cotizaciones_total}</span>
                    </span>
                  </td>
                  <td className="text-center text-xs">
                    <span title={`Total: ${u.metrics.facturas_total}`}>
                      {u.metrics.facturas_mes_actual}
                      <span className="text-[var(--text-tertiary)] text-[10px]">/{u.metrics.facturas_total}</span>
                    </span>
                  </td>
                  <td className="text-center text-xs">
                    <span title={`Total: ${u.metrics.boletas_total}`}>
                      {u.metrics.boletas_mes_actual}
                      <span className="text-[var(--text-tertiary)] text-[10px]">/{u.metrics.boletas_total}</span>
                    </span>
                  </td>
                  <td className="text-center text-xs">{u.metrics.notas_credito_total}</td>
                  <td className="text-center text-xs">
                    <span title={`Total: ${u.metrics.guias_total}`}>
                      {u.metrics.guias_mes_actual}
                      <span className="text-[var(--text-tertiary)] text-[10px]">/{u.metrics.guias_total}</span>
                    </span>
                  </td>
                  <td>
                    <Badge variant={u.is_active ? 'success' : 'danger'}>
                      {u.is_active ? 'activo' : 'bloqueado'}
                    </Badge>
                  </td>
                  <td>
                    <div className="flex flex-col gap-1.5">
                      <button
                        type="button"
                        disabled={togglingId === u.id}
                        onClick={() => handleToggleActive(u)}
                        className="inline-flex items-center gap-1 font-mono text-[10px] uppercase tracking-[0.14em] text-[var(--text-secondary)] transition-opacity hover:opacity-70 disabled:cursor-not-allowed"
                      >
                        {u.is_active ? <ShieldOff className="h-3 w-3" /> : <ShieldCheck className="h-3 w-3" />}
                        {u.is_active ? 'Bloquear' : 'Activar'}
                      </button>
                      <button
                        type="button"
                        disabled={resettingId === u.id}
                        onClick={() => handleResetPassword(u)}
                        className="inline-flex items-center gap-1 font-mono text-[10px] uppercase tracking-[0.14em] text-[var(--text-brand)] transition-opacity hover:opacity-70 disabled:cursor-not-allowed"
                      >
                        <KeyRound className="h-3 w-3" />
                        Reset pass
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="mt-4 flex items-center justify-between border-t border-[var(--border-subtle)] pt-4">
        <p className="text-[11px] text-[var(--text-tertiary)]">Mes actual / Total · NC = Notas de crédito</p>
        <div className="flex gap-2">
          <button type="button" onClick={() => setAddingUser(true)} className="btn-secondary">
            <UserPlus className="h-3.5 w-3.5" />
            Nuevo usuario
          </button>
          <button type="button" onClick={onClose} className="btn-secondary">Cerrar</button>
        </div>
      </div>

      {addingUser && (
        <CreateUserModal
          tenant={tenant}
          onClose={() => setAddingUser(false)}
          onCreated={() => { setAddingUser(false); loadUsers(); }}
        />
      )}
    </Modal>
  );
}

const LIMIT_KIND_LABELS = {
  fiscal_invoice: 'Factura',
  fiscal_boleta: 'Boleta',
  guia: 'Guía',
  nota_credito: 'Nota de Crédito',
  nota_debito: 'Nota de Débito',
};

const LIMIT_KINDS = ['fiscal_invoice', 'fiscal_boleta', 'guia', 'nota_credito', 'nota_debito'];

const LIMIT_PERIOD_LABELS = {
  month: 'Mensual',
  day: 'Diario',
  total: 'Total',
};

const LIMIT_PERIODS = ['month', 'day', 'total'];

function TenantLimitsModal({ tenant, onClose }) {
  const toast = useToast();
  const [limits, setLimits] = useState([]);
  const [usage, setUsage] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [newLimit, setNewLimit] = useState({
    scope: 'tenant',
    user_id: '',
    document_kind: 'fiscal_invoice',
    period: 'month',
    max_count: '',
    notify_at_pct: 80,
    enabled: true,
  });

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const [limitsData, usersData] = await Promise.all([
        svc.tenantLimits(tenant.id),
        svc.tenantUsersDetail(tenant.id).catch(() => []),
      ]);
      setLimits(limitsData.limits || []);
      setUsage(limitsData.usage || []);
      setUsers(usersData || []);
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      setLoading(false);
    }
  }, [tenant.id, toast]);

  useEffect(() => { loadAll(); }, [loadAll]);

  const usageById = usage.reduce((acc, u) => { acc[u.limit_id] = u; return acc; }, {});
  const userById = users.reduce((acc, u) => { acc[u.id] = u; return acc; }, {});

  const handleAdd = async () => {
    const maxCount = parseInt(newLimit.max_count, 10);
    if (!Number.isFinite(maxCount) || maxCount <= 0) {
      toast('Ingresa un máximo entero mayor a 0.', 'error');
      return;
    }
    if (newLimit.scope === 'user' && !newLimit.user_id) {
      toast('Selecciona un usuario para el límite individual.', 'error');
      return;
    }
    const payload = [{
      user_id: newLimit.scope === 'user' ? parseInt(newLimit.user_id, 10) : null,
      document_kind: newLimit.document_kind,
      period: newLimit.period,
      max_count: maxCount,
      notify_at_pct: parseInt(newLimit.notify_at_pct, 10) || 80,
      enabled: true,
    }];
    setSaving(true);
    try {
      await svc.upsertTenantLimits(tenant.id, payload);
      toast('Límite guardado.');
      setNewLimit((s) => ({ ...s, max_count: '' }));
      await loadAll();
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (limitId) => {
    const confirmed = window.confirm('¿Eliminar este límite?');
    if (!confirmed) return;
    setSaving(true);
    try {
      await svc.deleteLimit(limitId);
      toast('Límite eliminado.');
      await loadAll();
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleToggle = async (lim) => {
    setSaving(true);
    try {
      await svc.upsertTenantLimits(tenant.id, [{
        user_id: lim.user_id,
        document_kind: lim.document_kind,
        period: lim.period,
        max_count: lim.max_count,
        notify_at_pct: lim.notify_at_pct ?? 80,
        enabled: !lim.enabled,
      }]);
      await loadAll();
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  const scopeLabel = (lim) => {
    if (!lim.user_id) return 'Tenant (todos los usuarios)';
    const u = userById[lim.user_id];
    return u ? u.email : `Usuario #${lim.user_id}`;
  };

  const progressColor = (pct, wouldBlock) => {
    if (wouldBlock) return 'var(--color-error)';
    if (pct >= 95) return 'var(--color-error)';
    if (pct >= 80) return 'var(--color-warning)';
    if (pct >= 50) return 'var(--brand-600)';
    return 'var(--color-success)'
  };

  const scopeOptions = [
    { value: 'tenant', label: 'Tenant completo' },
    { value: 'user', label: 'Usuario especifico' },
  ];
  const userOptions = [
    { value: '', label: 'Elegir usuario' },
    ...users.map((userOption) => ({ value: String(userOption.id), label: userOption.email })),
  ];
  const documentKindOptions = LIMIT_KINDS.map((kind) => ({
    value: kind,
    label: LIMIT_KIND_LABELS[kind],
  }));
  const periodOptions = LIMIT_PERIODS.map((period) => ({
    value: period,
    label: LIMIT_PERIOD_LABELS[period],
  }));

  return (
    <Modal open={true} onClose={onClose} title={`Límites de emisión · ${tenant.business_name}`} size="xl">

      {/* Regla de negocio */}
      <div className="ink-inline-alert ink-inline-alert-info mb-5">
        <p className="text-xs">
          <strong>Regla:</strong> las cotizaciones nunca se limitan. Los límites aplican a facturas, boletas, guías y notas. Puedes configurar un límite global del tenant (aplica a la suma de todos) o específico de un usuario.
        </p>
      </div>

      {/* Formulario nuevo límite */}
      <section className="ink-card p-5 mb-5">
        <p className="label mb-4">Agregar / reemplazar límite</p>

        <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3">
          <div>
            <label className="label">Alcance</label>
            <CustomSelect
              value={newLimit.scope}
              onChange={(value) => setNewLimit((current) => ({ ...current, scope: value, user_id: '' }))}
              options={scopeOptions}
            />
          </div>

          {newLimit.scope === 'user' && (
            <div>
              <label className="label">Usuario</label>
              <CustomSelect
                value={newLimit.user_id}
                onChange={(value) => setNewLimit((current) => ({ ...current, user_id: value }))}
                options={userOptions}
                searchable
                searchPlaceholder="Buscar usuario..."
              />
            </div>
          )}

          <div>
            <label className="label">Tipo de documento</label>
            <CustomSelect
              value={newLimit.document_kind}
              onChange={(value) => setNewLimit((current) => ({ ...current, document_kind: value }))}
              options={documentKindOptions}
            />
          </div>

          <div>
            <label className="label">Periodo</label>
            <CustomSelect
              value={newLimit.period}
              onChange={(value) => setNewLimit((current) => ({ ...current, period: value }))}
              options={periodOptions}
            />
          </div>

          <div>
            <label className="label">Máximo permitido</label>
            <input
              type="number"
              min="1"
              value={newLimit.max_count}
              onChange={(e) => setNewLimit((s) => ({ ...s, max_count: e.target.value }))}
              className="input"
              placeholder="100"
            />
          </div>

          <div>
            <label className="label">Alerta al % del límite</label>
            <input
              type="number"
              min="0"
              max="100"
              value={newLimit.notify_at_pct}
              onChange={(e) => setNewLimit((s) => ({ ...s, notify_at_pct: e.target.value }))}
              className="input"
              placeholder="80"
            />
          </div>
        </div>

        <div className="mt-4 flex justify-end">
          <button type="button" onClick={handleAdd} disabled={saving} className="btn-primary">
            <Plus className="h-4 w-4" />
            {saving ? 'Guardando...' : 'Agregar límite'}
          </button>
        </div>
      </section>

      {/* Lista de límites */}
      {loading ? (
        <div className="flex justify-center py-10">
          <Spinner size="lg" label="Cargando límites" />
        </div>
      ) : limits.length === 0 ? (
        <EmptyState
          title="Sin límites configurados"
          description="Este tenant puede emitir sin restricciones. Agrega un límite arriba para empezar a controlar el volumen."
        />
      ) : (
        <div className="ink-table-card">
          <table className="ink-table">
            <thead>
              <tr>
                <th>Alcance</th>
                <th>Documento</th>
                <th>Período</th>
                <th className="text-center">Uso</th>
                <th>Progreso</th>
                <th>Estado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {limits.map((lim) => {
                const u = usageById[lim.id] || { used: 0, pct: 0, would_block: false };
                return (
                  <tr key={lim.id} style={{ opacity: lim.enabled ? 1 : 0.45 }}>
                    <td className="text-xs">{scopeLabel(lim)}</td>
                    <td>
                      <Badge variant="info">{LIMIT_KIND_LABELS[lim.document_kind] || lim.document_kind}</Badge>
                    </td>
                    <td className="text-xs text-[var(--text-secondary)]">
                      {LIMIT_PERIOD_LABELS[lim.period] || lim.period}
                    </td>
                    <td className="text-center whitespace-nowrap font-semibold text-sm">
                      <span style={{ color: u.would_block ? 'var(--color-error)' : 'var(--text-primary)' }}>
                        {u.used}
                      </span>
                      <span className="text-[var(--text-tertiary)]"> / {lim.max_count}</span>
                    </td>
                    <td style={{ width: 160 }}>
                      <div className="superadmin-progress-track">
                        <div
                          className="superadmin-progress-bar"
                          style={{
                            width: `${Math.min(100, u.pct)}%`,
                            background: progressColor(u.pct, u.would_block),
                          }}
                        />
                      </div>
                      <p className="superadmin-mini-note mt-1">{u.pct}%</p>
                    </td>
                    <td>
                      {u.would_block ? (
                        <Badge variant="danger">bloquea</Badge>
                      ) : lim.enabled ? (
                        <Badge variant="success">activo</Badge>
                      ) : (
                        <Badge variant="default">pausado</Badge>
                      )}
                    </td>
                    <td>
                      <div className="flex items-center gap-3">
                        <button
                          type="button"
                          onClick={() => handleToggle(lim)}
                          disabled={saving}
                          className="superadmin-toolbar-btn"
                        >
                          {lim.enabled ? 'Pausar' : 'Activar'}
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDelete(lim.id)}
                          disabled={saving}
                          className="superadmin-toolbar-btn superadmin-toolbar-btn--danger"
                        >
                          <Trash2 className="h-3 w-3" />
                          Eliminar
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <div className="mt-5 flex justify-end border-t border-[var(--border-subtle)] pt-4">
        <button type="button" onClick={onClose} className="btn-secondary">Cerrar</button>
      </div>
    </Modal>
  );
}

function TenantErrorsModal({ tenant, onClose }) {
  const toast = useToast();
  const [errors, setErrors] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    svc.emissionErrors(tenant.id)
      .then(setErrors)
      .catch((err) => toast(err.message, 'error'))
      .finally(() => setLoading(false));
  }, [tenant.id, toast]);

  const fmtDate = (iso) => {
    if (!iso) return '—';
    return new Date(iso).toLocaleString('es-PE', { dateStyle: 'short', timeStyle: 'short' });
  };

  return (
    <Modal open={true} onClose={onClose} title={`Errores de emisión · ${tenant.business_name}`} size="xl">
      {loading ? (
        <div className="flex justify-center py-10">
          <Spinner size="lg" label="Cargando errores" />
        </div>
      ) : errors.length === 0 ? (
        <EmptyState title="Sin errores recientes" description="No hay jobs de emisión fallidos para este tenant." />
      ) : (
        <div className="ink-table-card">
          <table className="ink-table">
            <thead>
              <tr>
                <th>Tipo</th>
                <th>Recurso</th>
                <th className="text-center">Intentos</th>
                <th>Error</th>
                <th>Fecha</th>
              </tr>
            </thead>
            <tbody>
              {errors.map((e) => (
                <tr key={e.job_id}>
                  <td className="text-xs">{ACTION_LABELS[e.action] || e.action}</td>
                  <td className="font-mono text-xs">{e.resource_type} #{e.resource_id}</td>
                  <td className="text-center"><Badge variant="danger">{e.attempts}</Badge></td>
                  <td className="text-xs text-[var(--text-secondary)] max-w-xs break-words">{e.last_error || '—'}</td>
                  <td className="text-xs text-[var(--text-tertiary)] whitespace-nowrap">{fmtDate(e.finished_at || e.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <div className="mt-4 flex justify-end border-t border-[var(--border-subtle)] pt-4">
        <button type="button" onClick={onClose} className="btn-secondary">Cerrar</button>
      </div>
    </Modal>
  );
}

export default function SuperadminPage() {
  const { user } = useAuth();
  const toast = useToast();
  const [tenants, setTenants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null);
  const [creating, setCreating] = useState(false);
  const [addingUserTo, setAddingUserTo] = useState(null);
  const [viewingUsersOf, setViewingUsersOf] = useState(null);
  const [viewingErrorsOf, setViewingErrorsOf] = useState(null);
  const [viewingLimitsOf, setViewingLimitsOf] = useState(null);
  const [checkingTokenId, setCheckingTokenId] = useState(null);

  useEffect(() => {
    svc.tenants()
      .then(setTenants)
      .catch(() => toast('No se pudo cargar la lista de tenants. Revisa tu conexión e inténtalo nuevamente.', 'error'))
      .finally(() => setLoading(false));
  }, [toast]);

  if (user?.rol !== 'superadmin' && !user?.is_superadmin) {
    return <Navigate to="/dashboard" replace />;
  }

  const handleSaved = (updated) => {
    setTenants((current) => current.map((tenant) => (tenant.id === updated.id ? updated : tenant)));
  };

  const handleCreated = (newTenant) => {
    setTenants((current) => [newTenant, ...current]);
  };

  const handleDeleted = (tenantId) => {
    setTenants((current) => current.filter((tenant) => tenant.id !== tenantId));
  };

  const handleCheckTokenHealth = async (tenant) => {
    setCheckingTokenId(tenant.id);
    try {
      const result = await svc.checkTokenHealth(tenant.id);
      setTenants((current) =>
        current.map((t) =>
          t.id === tenant.id
            ? { ...t, apisperu_token_status: result.status, apisperu_token_checked_at: result.checked_at }
            : t,
        ),
      );
      toast(
        result.status === 'ok' ? 'Token válido ✓' : `Token inválido: ${result.message}`,
        result.status === 'ok' ? 'success' : 'error',
      );
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      setCheckingTokenId(null);
    }
  };

  const metrics = [
    {
      label: 'Tenants totales',
      value: tenants.length,
      note: 'Base total registrada en la plataforma.',
      icon: Building2,
    },
    {
      label: 'Tenants activos',
      value: tenants.filter((tenant) => tenant.is_active).length,
      note: 'Empresas habilitadas para operar.',
      icon: ShieldCheck,
    },
    {
      label: 'Token ApisPeru',
      value: tenants.filter((tenant) => tenant.has_apisperu_token).length,
      note: 'Tenants con integracion fiscal ya configurada.',
      icon: KeyRound,
    },
    {
      label: 'Pendientes de token',
      value: tenants.filter((tenant) => !tenant.has_apisperu_token).length,
      note: 'Tenants que aun requieren integracion fiscal.',
      icon: Users,
    },
  ];

  return (
    <div className="page-shell page-shell--dense superadmin-shell">
      <div className="page-header">
        <div className="page-header-copy">
          <p className="page-kicker">Control interno</p>
          <h2 className="page-title">Superadmin</h2>
          <p className="page-subtitle">
            Gestion de tenants, validacion de tokens y alta de usuarios operativos sin salir del panel interno.
          </p>
        </div>

        <div className="page-actions">
          <button onClick={() => setCreating(true)} className="btn-primary flex items-center gap-2">
            <Plus className="h-4 w-4" />
            Nuevo tenant
          </button>
        </div>
      </div>

      <section className="card-raw" data-label="control">
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1.3fr)_320px]">
          <div>
            <p className="page-kicker">Base operativa</p>
            <h3 className="superadmin-section-title mt-2">
              El frente interno ahora usa la misma gramatica visual de Inkora.
            </h3>
            <p className="superadmin-hero-note">
              Aqui concentras altas, cambios fiscales y administracion inicial por tenant. La prioridad sigue siendo
              claridad operativa, no volumen visual.
            </p>
            <div className="raw-lines mt-6" aria-hidden="true">
              <div />
              <div />
              <div />
            </div>
          </div>

          <div className="ink-card p-4">
            <p className="label">Observacion</p>
            <p className="mt-2 text-sm leading-6 text-[var(--text-secondary)]">
              La validacion de token ya esta conectada al backend. Si el token no corresponde al RUC del tenant, el
              guardado se bloquea antes de persistir el cambio.
            </p>
          </div>
        </div>
      </section>

      <div className="ink-metric-grid md:grid-cols-2 xl:grid-cols-4">
        {metrics.map((metric) => {
          const Icon = metric.icon;
          return (
            <div key={metric.label} className="ink-metric-card">
              <div className="flex items-center justify-between gap-3">
                <span className="ink-metric-label">{metric.label}</span>
                <Icon className="h-4 w-4 text-[var(--text-brand)]" />
              </div>
              <div className="ink-metric-value">{metric.value}</div>
              <p className="ink-metric-note">{metric.note}</p>
            </div>
          );
        })}
      </div>

      {loading ? (
        <div className="flex justify-center py-20">
          <Spinner size="lg" />
        </div>
      ) : tenants.length === 0 ? (
        <EmptyState
          title="Sin tenants registrados"
          description="Crea el primer tenant para iniciar la operacion multiempresa."
        />
      ) : (
        <div className="ink-table-card">
          <div className="ink-card-header">
            <div>
              <h3 className="ink-card-title">Tenants registrados</h3>
              <p className="ink-card-subtitle">{tenants.length} empresa{tenants.length !== 1 ? 's' : ''} · Alta, edición fiscal y gestión de usuarios.</p>
            </div>
            <button onClick={() => setCreating(true)} className="btn-secondary flex items-center gap-1.5">
              <Plus className="h-3.5 w-3.5" />
              Nuevo tenant
            </button>
          </div>

          <table className="ink-table">
            <thead>
              <tr>
                <th>Empresa</th>
                <th>RUC</th>
                <th>Plan</th>
                <th>ApisPeru</th>
                <th>Estado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {tenants.map((tenant) => {
                const tokenStatus = tenant.apisperu_token_status;
                const tokenStatusVariant = tokenStatus === 'ok' ? 'success' : tokenStatus === 'invalid' ? 'danger' : 'default';
                const tokenStatusLabel = tokenStatus === 'ok' ? 'ok' : tokenStatus === 'invalid' ? 'inválido' : 'sin verificar';
                const initials = tenant.business_name
                  .split(' ')
                  .slice(0, 2)
                  .map((w) => w[0]?.toUpperCase() || '')
                  .join('');
                return (
                  <tr key={tenant.id}>
                    <td data-label="Empresa">
                      <div className="flex items-center gap-3">
                        {/* Avatar inicial */}
                        <div className="superadmin-avatar">
                          {initials}
                        </div>
                        <div>
                          <p className="font-semibold text-sm text-[var(--text-primary)] leading-tight">{tenant.business_name}</p>
                          <p className="text-[11px] text-[var(--text-tertiary)] mt-0.5">
                            {tenant.business_address || 'Sin dirección fiscal'}
                          </p>
                        </div>
                      </div>
                    </td>

                    <td data-label="RUC" className="font-mono text-xs text-[var(--text-secondary)] tracking-wide">
                      {tenant.business_ruc || '—'}
                    </td>

                    <td data-label="Plan">
                      <Badge variant="brand" className="capitalize">
                        {tenant.plan_type || 'founder'}
                      </Badge>
                    </td>

                    <td data-label="ApisPeru">
                      <div className="flex flex-col gap-1.5">
                        <StatusDot ok={tenant.has_apisperu_token} />
                        {tenant.has_apisperu_token && (
                          <div className="flex items-center gap-1.5">
                            <Badge variant={tokenStatusVariant}>{tokenStatusLabel}</Badge>
                            <button
                              type="button"
                              title="Verificar token ahora"
                              disabled={checkingTokenId === tenant.id}
                              onClick={() => handleCheckTokenHealth(tenant)}
                              className="superadmin-token-check"
                            >
                              <RefreshCw className="h-3 w-3" />
                            </button>
                          </div>
                        )}
                      </div>
                    </td>

                    <td data-label="Estado">
                      <Badge variant={tenant.is_active ? 'success' : 'danger'}>
                        {tenant.is_active ? 'activo' : 'inactivo'}
                      </Badge>
                    </td>

                    <td data-label="Acciones">
                      <div className="flex flex-wrap gap-1">
                        <button
                          type="button"
                          onClick={() => setEditing(tenant)}
                          className="superadmin-toolbar-btn superadmin-toolbar-btn--brand"
                        >
                          <PencilLine className="h-3 w-3" />
                          Editar
                        </button>

                        <button
                          type="button"
                          onClick={() => setViewingUsersOf(tenant)}
                          className="superadmin-toolbar-btn"
                        >
                          <Users className="h-3 w-3" />
                          Usuarios
                        </button>

                        <button
                          type="button"
                          onClick={() => setViewingErrorsOf(tenant)}
                          className="superadmin-toolbar-btn superadmin-toolbar-btn--warning"
                        >
                          <AlertCircle className="h-3 w-3" />
                          Errores
                        </button>

                        <button
                          type="button"
                          onClick={() => setViewingLimitsOf(tenant)}
                          className="superadmin-toolbar-btn superadmin-toolbar-btn--accent"
                        >
                          <Gauge className="h-3 w-3" />
                          Límites
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {editing ? (
        <TenantModal
          tenant={editing}
          onClose={() => setEditing(null)}
          onSaved={handleSaved}
          onDeleted={handleDeleted}
        />
      ) : null}

      {creating ? (
        <CreateTenantModal
          onClose={() => setCreating(false)}
          onCreated={handleCreated}
        />
      ) : null}

      {addingUserTo ? (
        <CreateUserModal
          tenant={addingUserTo}
          onClose={() => setAddingUserTo(null)}
          onCreated={() => {}}
        />
      ) : null}

      {viewingUsersOf ? (
        <TenantUsersModal
          tenant={viewingUsersOf}
          onClose={() => setViewingUsersOf(null)}
        />
      ) : null}

      {viewingErrorsOf ? (
        <TenantErrorsModal
          tenant={viewingErrorsOf}
          onClose={() => setViewingErrorsOf(null)}
        />
      ) : null}

      {viewingLimitsOf ? (
        <TenantLimitsModal
          tenant={viewingLimitsOf}
          onClose={() => setViewingLimitsOf(null)}
        />
      ) : null}
    </div>
  );
}
