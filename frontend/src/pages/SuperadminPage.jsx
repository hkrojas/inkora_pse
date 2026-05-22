import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  AlertCircle,
  Building2,
  Gauge,
  KeyRound,
  PencilLine,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  ShieldOff,
  SlidersHorizontal,
  Trash2,
  Truck,
  UserPlus,
  Users,
} from 'lucide-react';
import { Navigate } from 'react-router-dom';
import { superadmin as svc } from '../services/superadmin';
import Modal from '../components/ui/Modal';
import Drawer from '../components/ui/Drawer';
import Spinner from '../components/ui/Spinner';
import Badge from '../components/ui/Badge';
import EmptyState from '../components/ui/EmptyState';
import { useToast } from '../components/ui/Toast';
import CustomSelect from '../components/ui/CustomSelect';
import { useAuth } from '../context/AuthContext';
import { getSmartPseGreStatusMeta } from '../lib/utils/fiscalStatus';
import { getPageCount } from '../lib/utils/queryParams';

const SUPERADMIN_PAGE_SIZE = 25;
const DEFAULT_TENANT_METRICS = {
  total: 0,
  active: 0,
  smartpse_gre: 0,
  smartpse_gre_pending: 0,
};
const TENANT_GRE_FILTER_OPTIONS = [
  { value: 'all', label: 'Todos' },
  { value: 'configured', label: 'GRE configurado' },
  { value: 'missing', label: 'GRE pendiente' },
  { value: 'ok', label: 'GRE ok' },
  { value: 'invalid', label: 'GRE invalido' },
  { value: 'unchecked', label: 'GRE sin verificar' },
];
const TENANT_ACTIVE_FILTER_OPTIONS = [
  { value: 'all', label: 'Todos' },
  { value: 'active', label: 'Activos' },
  { value: 'inactive', label: 'Inactivos' },
];

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

function getSmartPseCpeStatusMeta(tenant) {
  const hasCredentials = Boolean(tenant?.has_smartpse_credentials);
  const status = String(tenant?.smartpse_status || 'unchecked').toLowerCase();

  if (!hasCredentials) {
    return {
      badgeVariant: 'default',
      label: 'pendiente',
      description: 'Pendiente de aprovisionamiento CPE en Smart PSE.',
      canCheck: false,
    };
  }
  if (status === 'ok') {
    return {
      badgeVariant: 'success',
      label: 'ok',
      description: 'Credenciales CPE activas para emitir por Smart PSE.',
      canCheck: true,
    };
  }
  if (status === 'invalid') {
    return {
      badgeVariant: 'danger',
      label: 'invalido',
      description: 'Credenciales CPE rechazadas por Smart PSE.',
      canCheck: true,
    };
  }
  return {
    badgeVariant: 'default',
    label: 'sin verificar',
    description: 'Credenciales CPE guardadas, pendientes de verificacion.',
    canCheck: true,
  };
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
  const [form, setForm] = useState({
    business_name: tenant.business_name || '',
    business_ruc: tenant.business_ruc || '',
    business_address: tenant.business_address || '',
    is_active: tenant.is_active ?? true,
  });
  const smartPseMeta = getSmartPseCpeStatusMeta(tenant);

  const setField = (key) => (event) => {
    const rawValue =
      event.target.type === 'checkbox' ? event.target.checked : event.target.value;
    const value = key === 'business_ruc' ? sanitizeRuc(rawValue) : rawValue;

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

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSaving(true);

    try {
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
    <Drawer
      open={Boolean(tenant)}
      onClose={onClose}
      title="Editar tenant"
      subtitle={tenant.business_name}
      icon={<PencilLine size={18} />}
    >
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
            kicker="Smart PSE CPE"
            title="Estado de aprovisionamiento"
            copy="Las credenciales CPE se gestionan desde Smart PSE. El tenant solo ve estados operativos, nunca secretos."
          />

          <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_220px]">
            <div className="ink-inline-alert ink-inline-alert-info">
              <p className="text-sm font-semibold text-[var(--text-primary)]">Estado actual</p>
              <p className="mt-1 text-sm text-[var(--text-secondary)]">{smartPseMeta.description}</p>
              <p className="mt-2 text-xs text-[var(--text-tertiary)]">
                Ambiente: {tenant.smartpse_environment || 'demo'} · Ultima verificacion: {formatDateTime(tenant.smartpse_checked_at)}
              </p>
            </div>

            <div className="flex flex-col items-start justify-center gap-2 border border-[var(--border-subtle)] bg-[var(--bg-surface-low)] p-4">
              <StatusDot ok={tenant.has_smartpse_credentials} />
              <Badge variant={smartPseMeta.badgeVariant}>{smartPseMeta.label}</Badge>
            </div>
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
    </Drawer>
  );
}

function CreateTenantModal({ onClose, onCreated }) {
  const toast = useToast();
  const [saving, setSaving] = useState(false);
  const [lookupLoading, setLookupLoading] = useState(false);
  const [form, setForm] = useState({
    business_name: '',
    business_ruc: '',
    business_address: '',
  });

  const setField = (key) => (event) => {
    const value = key === 'business_ruc' ? sanitizeRuc(event.target.value) : event.target.value;

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

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!form.business_name.trim() || !form.business_ruc.trim()) {
      toast('Razon social y RUC son obligatorios', 'error');
      return;
    }

    setSaving(true);
    try {
      const payload = {
        business_name: form.business_name.trim(),
        business_ruc: form.business_ruc.trim(),
      };

      if (form.business_address.trim()) {
        payload.business_address = form.business_address.trim();
      }

      const created = await svc.createTenant(payload);
      let tenantForList = created;
      try {
        tenantForList = await svc.provisionSmartPseTenant(created.id, { environment: 'demo' });
        toast('Tenant creado y Smart PSE CPE aprovisionado');
      } catch (provisionError) {
        toast(`Tenant creado. Smart PSE CPE queda pendiente: ${provisionError.message}`, 'error');
      }
      onCreated(tenantForList);
      onClose();
    } catch (error) {
      toast(error.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Drawer
      open={true}
      onClose={onClose}
      title="Nuevo tenant"
      subtitle="Alta operativa Smart PSE CPE"
      icon={<Building2 size={18} />}
      footer={(
        <>
          <button type="button" onClick={onClose} className="btn-secondary">
            Cancelar
          </button>
          <button
            type="submit"
            form="new-tenant-form"
            disabled={saving}
            className="btn-primary flex items-center gap-2"
          >
            {saving ? <Spinner size="sm" /> : null}
            Crear y aprovisionar
          </button>
        </>
      )}
    >
      <form id="new-tenant-form" onSubmit={handleSubmit} className="space-y-6">
        <section className="card-raw" data-label="alta">
          <SectionHeader
            kicker="Onboarding"
            title="Crear empresa operativa"
            copy="El alta fiscal parte por la identidad basica. Al crear el tenant se aprovisiona Smart PSE CPE en ambiente demo."
          />

          <div className="space-y-4">
            <div>
              <label className="label">Razon social *</label>
              <input
                className="input"
                value={form.business_name}
                onChange={setField('business_name')}
                aria-label="Razon social"
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
                  aria-label="RUC"
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
                aria-label="Direccion fiscal"
              />
            </div>
          </div>
        </section>

        <section className="ink-card p-6">
          <SectionHeader
            kicker="Smart PSE CPE"
            title="Aprovisionamiento demo"
            copy="El panel creara la empresa en Smart PSE y guardara solo el estado operativo visible para el superadmin."
          />

          <div className="ink-inline-alert ink-inline-alert-info">
            <p className="text-sm font-semibold text-[var(--text-primary)]">Ambiente demo</p>
            <p className="mt-1 text-sm text-[var(--text-secondary)]">
              El payload de creacion solo incluye identidad fiscal. Luego se solicita el aprovisionamiento CPE con Smart PSE.
            </p>
          </div>
        </section>
      </form>
    </Drawer>
  );
}

function TenantGreCredentialsModal({ tenant, onClose, onSaved }) {
  const toast = useToast();
  const [localTenant, setLocalTenant] = useState(tenant);
  const [saving, setSaving] = useState(false);
  const [checking, setChecking] = useState(false);
  const [validationResult, setValidationResult] = useState(null);
  const [form, setForm] = useState({
    sol_username: '',
    sol_password: '',
    client_id: '',
    client_secret: '',
  });

  const greMeta = getSmartPseGreStatusMeta(localTenant);
  const canSave = Object.values(form).every((value) => value.trim());

  const setField = (key) => (event) => {
    const value = key === 'sol_username' ? event.target.value.toUpperCase() : event.target.value;
    setValidationResult(null);
    setForm((current) => ({ ...current, [key]: value }));
  };

  const handleSave = async (event) => {
    event.preventDefault();

    if (!canSave) {
      toast('Completa usuario SOL, clave SOL, client ID y client secret.', 'error');
      return;
    }

    setSaving(true);
    try {
      const updated = await svc.updateSmartPseGreCredentials(tenant.id, {
        sol_username: form.sol_username.trim(),
        sol_password: form.sol_password.trim(),
        client_id: form.client_id.trim(),
        client_secret: form.client_secret.trim(),
      });
      setLocalTenant(updated);
      onSaved(updated);
      setForm({
        sol_username: '',
        sol_password: '',
        client_id: '',
        client_secret: '',
      });
      toast('Credenciales GRE guardadas');
    } catch (error) {
      toast(error.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleCheck = async () => {
    if (!greMeta.canCheck) {
      toast('Primero guarda las credenciales GRE.', 'error');
      return;
    }

    setChecking(true);
    try {
      const result = await svc.checkSmartPseGreCredentials(tenant.id);
      const updated = {
        ...localTenant,
        has_smartpse_gre_credentials: true,
        smartpse_gre_status: result.valid ? 'ok' : 'invalid',
        smartpse_gre_checked_at: new Date().toISOString(),
      };
      setLocalTenant(updated);
      onSaved(updated);
      setValidationResult(result);
      toast(result.valid ? 'Credenciales GRE validas' : result.message, result.valid ? 'success' : 'error');
    } catch (error) {
      toast(error.message, 'error');
    } finally {
      setChecking(false);
    }
  };

  return (
    <Drawer
      open={Boolean(tenant)}
      onClose={onClose}
      title="Smart PSE GRE"
      subtitle={tenant.business_name}
      icon={<Truck size={18} />}
    >
      <div className="space-y-6">
        <section className="card-raw" data-label="smart-pse-gre">
          <SectionHeader
            kicker="Smart PSE GRE"
            title="Credenciales SUNAT para guias"
            copy="El backend las guarda cifradas y solo expone estado operativo en esta pantalla."
          />

          <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_220px]">
            <div className="ink-inline-alert ink-inline-alert-warning">
              <p className="text-sm font-semibold text-[var(--text-primary)]">Estado actual</p>
              <p className="mt-1 text-sm text-[var(--text-secondary)]">{greMeta.description}</p>
              <p className="mt-2 text-xs text-[var(--text-tertiary)]">
                Ultima validacion: {formatDateTime(localTenant.smartpse_gre_checked_at)}
              </p>
            </div>

            <div className="flex flex-col items-start justify-center gap-2 border border-[var(--border-subtle)] bg-[var(--bg-surface-low)] p-4">
              <StatusDot ok={localTenant.has_smartpse_gre_credentials} />
              <Badge variant={greMeta.badgeVariant}>{greMeta.label}</Badge>
              <button
                type="button"
                className="btn-secondary mt-1 flex items-center gap-2 whitespace-nowrap"
                onClick={handleCheck}
                disabled={checking || !greMeta.canCheck}
              >
                {checking ? <Spinner size="sm" /> : <RefreshCw className="h-3.5 w-3.5" />}
                Validar
              </button>
            </div>
          </div>
        </section>

        <form onSubmit={handleSave} className="ink-card p-6">
          <SectionHeader
            kicker="Rotacion"
            title="Guardar nuevas credenciales"
            copy="Los campos no se precargan para no exponer secretos ya guardados."
          />

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="label">Usuario SOL corto</label>
              <input
                className="input font-mono text-xs"
                value={form.sol_username}
                onChange={setField('sol_username')}
                placeholder="USUARIO"
                aria-label="Usuario SOL corto"
                autoComplete="off"
              />
              <p className="mt-2 text-xs text-[var(--text-secondary)]">Sin RUC; el backend construye RUC + usuario.</p>
            </div>

            <div>
              <label className="label">Clave SOL</label>
              <input
                type="password"
                className="input font-mono text-xs"
                value={form.sol_password}
                onChange={setField('sol_password')}
                placeholder="••••••••"
                aria-label="Clave SOL"
                autoComplete="new-password"
              />
            </div>

            <div>
              <label className="label">Client ID SUNAT</label>
              <input
                className="input font-mono text-xs"
                value={form.client_id}
                onChange={setField('client_id')}
                placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                aria-label="Client ID SUNAT"
                autoComplete="off"
              />
            </div>

            <div>
              <label className="label">Client secret SUNAT</label>
              <input
                type="password"
                className="input font-mono text-xs"
                value={form.client_secret}
                onChange={setField('client_secret')}
                placeholder="••••••••"
                aria-label="Client secret SUNAT"
                autoComplete="new-password"
              />
            </div>
          </div>

          <div className="mt-4">
            <ValidationNotice result={validationResult} />
          </div>

          <div className="mt-6 flex flex-wrap justify-end gap-2 border-t border-[var(--border-subtle)] pt-4">
            <button type="button" onClick={onClose} className="btn-secondary" disabled={saving || checking}>
              Cerrar
            </button>
            <button type="submit" className="btn-primary flex items-center gap-2" disabled={saving || !canSave}>
              {saving ? <Spinner size="sm" /> : <KeyRound className="h-4 w-4" />}
              Guardar cifrado
            </button>
          </div>
        </form>
      </div>
    </Drawer>
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
    <Drawer
      open={true}
      onClose={onClose}
      title="Nuevo usuario"
      subtitle={tenant.business_name}
      icon={<UserPlus size={18} />}
    >
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
    </Drawer>
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
    <Drawer
      open={true}
      onClose={onClose}
      title="Usuarios"
      subtitle={tenant.business_name}
      icon={<Users size={18} />}
      size="wide"
    >
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
    </Drawer>
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
    <Drawer
      open={true}
      onClose={onClose}
      title="Límites de emisión"
      subtitle={tenant.business_name}
      icon={<Gauge size={18} />}
      size="wide"
    >

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
    </Drawer>
  );
}

function formatDateTime(value) {
  if (!value) return 'Sin validar';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Sin validar';
  return date.toLocaleString('es-PE', {
    dateStyle: 'short',
    timeStyle: 'short',
  });
}

function TenantFiscalFlagsModal({ tenant, onClose }) {
  const toast = useToast();
  const [flags, setFlags] = useState({});
  const [definitions, setDefinitions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const loadFlags = useCallback(async () => {
    setLoading(true);
    try {
      const data = await svc.fiscalFlags(tenant.id);
      setFlags(data.flags || {});
      setDefinitions(data.definitions || []);
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      setLoading(false);
    }
  }, [tenant.id, toast]);

  useEffect(() => { loadFlags(); }, [loadFlags]);

  const handleToggle = (key) => {
    setFlags((current) => ({ ...current, [key]: !current[key] }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const data = await svc.updateFiscalFlags(tenant.id, flags);
      setFlags(data.flags || {});
      setDefinitions(data.definitions || definitions);
      toast('Flags fiscales actualizados.');
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Drawer
      open={true}
      onClose={onClose}
      title="Flags fiscales beta"
      subtitle={tenant.business_name}
      icon={<SlidersHorizontal size={18} />}
      size="wide"
    >
      <div className="ink-inline-alert ink-inline-alert-warning mb-5">
        <p className="text-xs">
          Estos controles habilitan funciones fiscales sensibles por tenant. Facturas y boletas siguen controladas por suscripcion,
          credenciales Smart PSE CPE y limites de emision; estos flags son para notas, guias y operaciones con mayor riesgo fiscal.
        </p>
      </div>

      {loading ? (
        <div className="flex justify-center py-10">
          <Spinner size="lg" label="Cargando flags fiscales" />
        </div>
      ) : definitions.length === 0 ? (
        <EmptyState title="Sin flags fiscales" description="El backend no devolvio definiciones de flags para este tenant." />
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {definitions.map((definition) => {
            const enabled = Boolean(flags[definition.key]);
            return (
              <label
                key={definition.key}
                className="ink-card flex cursor-pointer items-start gap-3 p-4"
              >
                <input
                  type="checkbox"
                  checked={enabled}
                  onChange={() => handleToggle(definition.key)}
                  className="mt-1"
                />
                <span className="min-w-0 flex-1">
                  <span className="flex flex-wrap items-center gap-2">
                    <span className="font-semibold text-sm text-[var(--text-primary)]">
                      {definition.label}
                    </span>
                    <Badge variant={enabled ? 'success' : 'default'}>
                      {enabled ? 'activo' : 'bloqueado'}
                    </Badge>
                  </span>
                  <span className="mt-1 block text-xs text-[var(--text-secondary)]">
                    {definition.control}
                  </span>
                  <span className="mt-1 block font-mono text-[10px] text-[var(--text-tertiary)]">
                    {definition.key} · {definition.category}
                  </span>
                </span>
              </label>
            );
          })}
        </div>
      )}

      <div className="mt-5 flex justify-end gap-2 border-t border-[var(--border-subtle)] pt-4">
        <button type="button" onClick={onClose} className="btn-secondary">Cerrar</button>
        <button type="button" onClick={handleSave} disabled={saving || loading} className="btn-primary">
          <SlidersHorizontal className="h-4 w-4" />
          {saving ? 'Guardando...' : 'Guardar flags'}
        </button>
      </div>
    </Drawer>
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
    <Drawer
      open={true}
      onClose={onClose}
      title="Errores de emisión"
      subtitle={tenant.business_name}
      icon={<AlertCircle size={18} />}
      size="wide"
    >
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
    </Drawer>
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
  const [viewingFiscalFlagsOf, setViewingFiscalFlagsOf] = useState(null);
  const [checkingSmartPseId, setCheckingSmartPseId] = useState(null);
  const [editingGreOf, setEditingGreOf] = useState(null);
  const [checkingGreId, setCheckingGreId] = useState(null);
  const [tenantSearch, setTenantSearch] = useState('');
  const [debouncedTenantSearch, setDebouncedTenantSearch] = useState('');
  const [tenantGreFilter, setTenantGreFilter] = useState('all');
  const [tenantActiveFilter, setTenantActiveFilter] = useState('all');
  const [tenantPage, setTenantPage] = useState(1);
  const [tenantTotal, setTenantTotal] = useState(0);
  const [tenantMetrics, setTenantMetrics] = useState(DEFAULT_TENANT_METRICS);
  const [tenantReloadKey, setTenantReloadKey] = useState(0);

  useEffect(() => {
    if (!user?.is_superadmin) {
      setLoading(false);
      return;
    }
    svc.tenantsPage({
      skip: (tenantPage - 1) * SUPERADMIN_PAGE_SIZE,
      limit: SUPERADMIN_PAGE_SIZE,
      q: debouncedTenantSearch || undefined,
      gre_status: tenantGreFilter === 'all' ? undefined : tenantGreFilter,
      active_status: tenantActiveFilter === 'all' ? undefined : tenantActiveFilter,
    })
      .then((data) => {
        setTenants(Array.isArray(data.items) ? data.items : []);
        setTenantTotal(Number(data.total || 0));
        setTenantMetrics({ ...DEFAULT_TENANT_METRICS, ...(data.metrics || {}) });
      })
      .catch(() => toast('No se pudo cargar la lista de tenants. Revisa tu conexión e inténtalo nuevamente.', 'error'))
      .finally(() => setLoading(false));
  }, [
    debouncedTenantSearch,
    tenantActiveFilter,
    tenantGreFilter,
    tenantPage,
    tenantReloadKey,
    toast,
    user?.is_superadmin,
  ]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setTenantPage(1);
      setDebouncedTenantSearch(tenantSearch.trim());
    }, 300);
    return () => window.clearTimeout(timer);
  }, [tenantSearch]);

  useEffect(() => {
    setTenantPage(1);
  }, [tenantActiveFilter, tenantGreFilter]);

  const tenantPageCount = getPageCount(tenantTotal, SUPERADMIN_PAGE_SIZE);
  const boundedTenantPage = Math.min(tenantPage, tenantPageCount);
  const visibleTenants = tenants;

  useEffect(() => {
    if (tenantPage > tenantPageCount) setTenantPage(tenantPageCount);
  }, [tenantPage, tenantPageCount]);

  if (!user?.is_superadmin) {
    return <Navigate to="/dashboard" replace />;
  }

  const refreshTenantPage = () => setTenantReloadKey((key) => key + 1);

  const handleSaved = (updated) => {
    setTenants((current) => current.map((tenant) => (tenant.id === updated.id ? updated : tenant)));
    setEditing((current) => (current?.id === updated.id ? updated : current));
    setEditingGreOf((current) => (current?.id === updated.id ? updated : current));
    refreshTenantPage();
  };

  const handleCreated = (newTenant) => {
    setTenants((current) => [newTenant, ...current]);
    setTenantPage(1);
    refreshTenantPage();
  };

  const handleDeleted = (tenantId) => {
    setTenants((current) => current.filter((tenant) => tenant.id !== tenantId));
    refreshTenantPage();
  };

  const handleCheckSmartPseCpe = async (tenant) => {
    const cpeMeta = getSmartPseCpeStatusMeta(tenant);
    if (!cpeMeta.canCheck) {
      toast('Primero aprovisiona Smart PSE CPE para este tenant.', 'error');
      return;
    }

    setCheckingSmartPseId(tenant.id);
    try {
      const result = await svc.checkSmartPseTenant(tenant.id);
      setTenants((current) =>
        current.map((t) =>
          t.id === tenant.id
            ? {
                ...t,
                has_smartpse_credentials: true,
                smartpse_status: result.valid ? 'ok' : 'invalid',
                smartpse_checked_at: new Date().toISOString(),
              }
            : t,
        ),
      );
      toast(
        result.valid ? 'Smart PSE CPE validado' : result.message,
        result.valid ? 'success' : 'error',
      );
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      refreshTenantPage();
      setCheckingSmartPseId(null);
    }
  };

  const handleCheckGreCredentials = async (tenant) => {
    const greMeta = getSmartPseGreStatusMeta(tenant);
    if (!greMeta.canCheck) {
      toast('Primero guarda las credenciales GRE de Smart PSE.', 'error');
      return;
    }

    setCheckingGreId(tenant.id);
    try {
      const result = await svc.checkSmartPseGreCredentials(tenant.id);
      setTenants((current) =>
        current.map((t) =>
          t.id === tenant.id
            ? {
                ...t,
                has_smartpse_gre_credentials: true,
                smartpse_gre_status: result.valid ? 'ok' : 'invalid',
                smartpse_gre_checked_at: new Date().toISOString(),
              }
            : t,
        ),
      );
      toast(result.valid ? 'Credenciales GRE validas' : result.message, result.valid ? 'success' : 'error');
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      refreshTenantPage();
      setCheckingGreId(null);
    }
  };

  const metrics = [
    {
      label: 'Tenants totales',
      value: tenantMetrics.total,
      note: 'Base total registrada en la plataforma.',
      icon: Building2,
      tone: 'neutral',
    },
    {
      label: 'Tenants activos',
      value: tenantMetrics.active,
      note: 'Empresas habilitadas para operar.',
      icon: ShieldCheck,
      tone: 'success',
    },
    {
      label: 'Smart PSE GRE',
      value: tenantMetrics.smartpse_gre,
      note: 'Tenants listos para guias con credenciales cifradas.',
      icon: Truck,
      tone: 'brand',
    },
    {
      label: 'GRE pendientes',
      value: tenantMetrics.smartpse_gre_pending,
      note: 'Empresas que aun requieren configuracion Smart PSE GRE.',
      icon: KeyRound,
      tone: tenantMetrics.smartpse_gre_pending > 0 ? 'warning' : 'success',
    },
  ];
  const showMetricSkeleton = loading && tenantTotal === 0 && tenants.length === 0;

  return (
    <div className="dashboard-page superadmin-shell">
      <div className="page-head ink-enter-1">
        <div>
          <p className="eyebrow">Control interno</p>
          <h2 style={{ margin: 0, fontSize: '28px', lineHeight: 1, letterSpacing: '-.06em' }}>
            Superadmin operativo
          </h2>
          <p style={{ margin: '8px 0 0', color: 'var(--color-text-muted)', fontSize: '14px' }}>
            Altas, estados Smart PSE y gobierno de usuarios con la misma lectura operativa de Inkora.
          </p>
        </div>
        <div className="page-actions">
          <button type="button" onClick={() => setCreating(true)} className="btn flex items-center gap-2">
            <Plus className="h-4 w-4" />
            Nuevo tenant
          </button>
        </div>
      </div>

      <section className="attention superadmin-attention ink-enter-2">
        <div className="attention-title">
          <span className="attention-title-badge">
            <ShieldCheck size={16} />
          </span>
          <h3>Gobierno interno</h3>
          <p>Controla altas, credenciales cifradas y validaciones sin exponer secretos al tenant.</p>
        </div>
        <div className="attention-card superadmin-attention-card">
          <strong>Demo</strong>
          <span className="attention-card-text">Smart PSE CPE queda aprovisionado en ambiente controlado.</span>
          <div className="attention-card-link">Sin SUNAT real</div>
        </div>
        <div className="attention-card superadmin-attention-card">
          <strong>{tenantMetrics.smartpse_gre}</strong>
          <span className="attention-card-text">Tenants con GRE Smart PSE listo y credenciales cifradas.</span>
          <div className="attention-card-link">GRE seguro</div>
        </div>
        <div className="attention-card superadmin-attention-card">
          <strong>{tenantMetrics.active}</strong>
          <span className="attention-card-text">Empresas activas para operar dentro del alcance beta.</span>
          <div className="attention-card-link">Operativos</div>
        </div>
        <div className="attention-card superadmin-attention-card">
          <strong>0</strong>
          <span className="attention-card-text">Secretos visibles para tenants: usuario SOL, clave o token.</span>
          <div className="attention-card-link">Sin exposición</div>
        </div>
      </section>

      <section className="metrics-grid">
        {metrics.map((metric) => {
          const badgeClass = metric.tone === 'warning' ? 'warn' : metric.tone === 'neutral' ? 'neutral' : '';
          return (
            <article key={metric.label} className="metric-card">
              <div className="metric-top">
                <div className="metric-label">{metric.label}</div>
                <span className={`metric-badge ${badgeClass}`}>{metric.tone === 'warning' ? 'Revisar' : 'Ok'}</span>
              </div>
              <div className="metric-value">
                {showMetricSkeleton ? (
                  <span className="ink-metric-skeleton" aria-label="Cargando metrica" />
                ) : (
                  metric.value
                )}
              </div>
              <div className="metric-sub">{metric.note}</div>
            </article>
          );
        })}
      </section>

      {loading ? (
        <div className="flex justify-center py-20">
          <Spinner size="lg" />
        </div>
      ) : tenantTotal === 0 ? (
        <EmptyState
          title="Sin tenants registrados"
          description="Crea el primer tenant para iniciar la operacion multiempresa."
        />
      ) : (
        <div className="panel superadmin-table-card">
          <div className="panel-header superadmin-table-header">
            <div>
              <h3 className="ink-card-title">Tenants registrados</h3>
              <p className="ink-card-subtitle">{tenantTotal} empresa{tenantTotal !== 1 ? 's' : ''} - Alta, edicion fiscal y gestion de usuarios.</p>
            </div>
            <button onClick={() => setCreating(true)} className="btn-secondary superadmin-add-tenant-btn">
              <Plus className="h-3.5 w-3.5" />
              Nuevo tenant
            </button>
          </div>

          <div className="superadmin-filter-bar">
            <label className="search-box">
              <Search size={16} />
              <input
                placeholder="Buscar empresa, RUC, plan o estado GRE..."
                value={tenantSearch}
                onChange={(event) => setTenantSearch(event.target.value)}
              />
            </label>

            <div className="document-list-filter">
              <span>GRE</span>
              <CustomSelect
                compact
                value={tenantGreFilter}
                onChange={setTenantGreFilter}
                options={TENANT_GRE_FILTER_OPTIONS}
              />
            </div>

            <div className="document-list-filter">
              <span>Estado</span>
              <CustomSelect
                compact
                value={tenantActiveFilter}
                onChange={setTenantActiveFilter}
                options={TENANT_ACTIVE_FILTER_OPTIONS}
              />
            </div>

            <div className="sort-text">
              Mostrando <strong>{visibleTenants.length}</strong> de <strong>{tenantTotal}</strong>
            </div>
          </div>

          <div className="ink-table-scroll">
            <table className="ink-table superadmin-tenants-table">
            <thead>
              <tr>
                <th>Empresa</th>
                <th>RUC</th>
                <th>Plan</th>
                <th>Smart PSE CPE</th>
                <th>Smart PSE GRE</th>
                <th>Estado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {visibleTenants.map((tenant) => {
                const cpeMeta = getSmartPseCpeStatusMeta(tenant);
                const greMeta = getSmartPseGreStatusMeta(tenant);
                const initials = tenant.business_name
                  .split(' ')
                  .slice(0, 2)
                  .map((w) => w[0]?.toUpperCase() || '')
                  .join('');
                return (
                  <tr key={tenant.id} className="superadmin-tenant-row">
                    <td data-label="Empresa">
                      <div className="superadmin-tenant-identity">
                        {/* Avatar inicial */}
                        <div className="superadmin-avatar">
                          {initials}
                        </div>
                        <div className="superadmin-tenant-copy">
                          <p className="superadmin-tenant-name">{tenant.business_name}</p>
                          <p className="superadmin-tenant-address">
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

                    <td data-label="Smart PSE CPE">
                      <div className="superadmin-status-panel">
                        <div className="superadmin-status-caption">
                          <StatusDot ok={tenant.has_smartpse_credentials} />
                        </div>
                        <div className="superadmin-status-line">
                          <Badge variant={cpeMeta.badgeVariant}>{cpeMeta.label}</Badge>
                          {cpeMeta.canCheck && (
                            <button
                              type="button"
                              title="Verificar Smart PSE CPE"
                              aria-label={`Verificar Smart PSE CPE de ${tenant.business_name}`}
                              aria-busy={checkingSmartPseId === tenant.id}
                              disabled={checkingSmartPseId === tenant.id}
                              onClick={() => handleCheckSmartPseCpe(tenant)}
                              className="superadmin-token-check"
                            >
                              <RefreshCw className="h-3 w-3 superadmin-token-check-icon" />
                            </button>
                          )}
                        </div>
                        <span className="superadmin-status-meta">
                          {tenant.smartpse_environment || 'demo'} - {formatDateTime(tenant.smartpse_checked_at)}
                        </span>
                      </div>
                    </td>

                    <td data-label="Smart PSE GRE">
                      <div className="superadmin-status-panel">
                        <div className="superadmin-status-caption">
                          <StatusDot ok={tenant.has_smartpse_gre_credentials} />
                        </div>
                        <div className="superadmin-status-line">
                          <Badge variant={greMeta.badgeVariant}>{greMeta.label}</Badge>
                          {greMeta.canCheck && (
                            <button
                              type="button"
                              title="Validar GRE desde Smart PSE"
                              aria-label={`Validar credenciales GRE de ${tenant.business_name}`}
                              aria-busy={checkingGreId === tenant.id}
                              disabled={checkingGreId === tenant.id}
                              onClick={() => handleCheckGreCredentials(tenant)}
                              className="superadmin-token-check"
                            >
                              <RefreshCw className="h-3 w-3 superadmin-token-check-icon" />
                            </button>
                          )}
                        </div>
                        <span className="superadmin-status-meta">
                          {formatDateTime(tenant.smartpse_gre_checked_at)}
                        </span>
                      </div>
                    </td>

                    <td data-label="Estado">
                      <Badge variant={tenant.is_active ? 'success' : 'danger'}>
                        {tenant.is_active ? 'activo' : 'inactivo'}
                      </Badge>
                    </td>

                    <td data-label="Acciones">
                      <div className="superadmin-row-actions">
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
                          title="Usuarios"
                          aria-label={`Usuarios de ${tenant.business_name}`}
                          className="superadmin-toolbar-btn superadmin-toolbar-btn--icon"
                        >
                          <Users className="h-3 w-3" />
                          Usuarios
                        </button>

                        <button
                          type="button"
                          onClick={() => setViewingErrorsOf(tenant)}
                          title="Errores"
                          aria-label={`Errores fiscales de ${tenant.business_name}`}
                          className="superadmin-toolbar-btn superadmin-toolbar-btn--icon superadmin-toolbar-btn--warning"
                        >
                          <AlertCircle className="h-3 w-3" />
                          Errores
                        </button>

                        <button
                          type="button"
                          onClick={() => setEditingGreOf(tenant)}
                          title="Smart PSE GRE"
                          aria-label="GRE"
                          className="superadmin-toolbar-btn superadmin-toolbar-btn--icon superadmin-toolbar-btn--accent"
                        >
                          <Truck className="h-3 w-3" />
                          GRE
                        </button>

                        <button
                          type="button"
                          onClick={() => setViewingLimitsOf(tenant)}
                          title="Limites"
                          aria-label={`Limites de ${tenant.business_name}`}
                          className="superadmin-toolbar-btn superadmin-toolbar-btn--icon superadmin-toolbar-btn--accent"
                        >
                          <Gauge className="h-3 w-3" />
                          Límites
                        </button>
                        <button
                          type="button"
                          onClick={() => setViewingFiscalFlagsOf(tenant)}
                          title="Flags fiscales"
                          aria-label={`Flags fiscales de ${tenant.business_name}`}
                          className="superadmin-toolbar-btn superadmin-toolbar-btn--icon"
                        >
                          <SlidersHorizontal className="h-3 w-3" />
                          Flags
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
            </table>
          </div>

          {tenantPageCount > 1 && (
            <div className="ink-table-footer">
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setTenantPage((page) => Math.max(1, page - 1))}
                disabled={boundedTenantPage <= 1}
              >
                Anterior
              </button>
              <span className="ink-table-count">
                Pagina {boundedTenantPage} de {tenantPageCount}
              </span>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setTenantPage((page) => Math.min(tenantPageCount, page + 1))}
                disabled={boundedTenantPage >= tenantPageCount}
              >
                Siguiente
              </button>
            </div>
          )}
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

      {editingGreOf ? (
        <TenantGreCredentialsModal
          tenant={editingGreOf}
          onClose={() => setEditingGreOf(null)}
          onSaved={handleSaved}
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

      {viewingFiscalFlagsOf ? (
        <TenantFiscalFlagsModal
          tenant={viewingFiscalFlagsOf}
          onClose={() => setViewingFiscalFlagsOf(null)}
        />
      ) : null}
    </div>
  );
}
