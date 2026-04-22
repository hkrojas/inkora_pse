import { useEffect, useState } from 'react';
import { Pencil, Plus, Search, Trash2, Filter, Save, RotateCcw } from 'lucide-react';
import { clientes as svc } from '../services/clientes';
import Spinner from '../components/ui/Spinner';
import EmptyState from '../components/ui/EmptyState';
import Modal from '../components/ui/Modal';
import CustomSelect from '../components/ui/CustomSelect';
import { FieldError } from '../components/ui/FieldError';
import { useToast } from '../components/ui/Toast';
import { normalizePeruMobileInput, validatePeruMobilePhone } from '../lib/utils/peruPhoneValidation';

const EMPTY_FORM = {
  tipo_documento: '6',
  numero_documento: '',
  razon_social: '',
  direccion: '',
  email: '',
  telefono: '',
  whatsapp: '',
  condicion_pago: 'contado',
};

function normalizeClientForm(initial) {
  return {
    ...initial,
    telefono: normalizePeruMobileInput(initial?.telefono || ''),
    whatsapp: normalizePeruMobileInput(initial?.whatsapp || ''),
  };
}

function ClienteForm({ initial = EMPTY_FORM, onSave, onCancel, saving }) {
  const [form, setForm] = useState(() => normalizeClientForm(initial));
  const [errors, setErrors] = useState({});
  useEffect(() => {
    setForm(normalizeClientForm(initial));
    setErrors({});
  }, [initial]);
  const set = (key) => (event) =>
    setForm((current) => ({ ...current, [key]: event.target.value }));
  const setMobile = (key) => (event) => {
    const nextValue = normalizePeruMobileInput(event.target.value);
    setForm((current) => ({ ...current, [key]: nextValue }));
    setErrors((current) => ({
      ...current,
      [key]: validatePeruMobilePhone(nextValue, key === 'whatsapp' ? 'WhatsApp' : 'Telefono') || undefined,
    }));
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    const nextErrors = {
      telefono: validatePeruMobilePhone(form.telefono, 'Telefono') || undefined,
      whatsapp: validatePeruMobilePhone(form.whatsapp, 'WhatsApp') || undefined,
    };
    setErrors(nextErrors);
    if (nextErrors.telefono || nextErrors.whatsapp) return;
    onSave(form);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid gap-4 md:grid-cols-3">
        <div>
          <label className="label">Tipo doc.</label>
          <CustomSelect
            value={form.tipo_documento}
            onChange={(v) => setForm((c) => ({ ...c, tipo_documento: v }))}
            options={[
              { value: '6', label: 'RUC' },
              { value: '1', label: 'DNI' },
              { value: '0', label: 'Otro' },
            ]}
          />
        </div>
        <div className="md:col-span-2">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '6px' }}>
            <label className="label" style={{ margin: 0 }}>Numero documento</label>
            <button type="button" className="label-action-btn">
              <Search style={{ width: '10px', height: '10px' }} /> Consultar
            </button>
          </div>
          <input
            required
            className="input"
            value={form.numero_documento}
            onChange={set('numero_documento')}
            placeholder="Ej. 20100200300"
          />
        </div>
      </div>

      <div>
        <label className="label">Razon social / nombre</label>
        <input required className="input" value={form.razon_social} onChange={set('razon_social')} />
      </div>

      <div>
        <label className="label">Direccion</label>
        <input className="input" value={form.direccion} onChange={set('direccion')} />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <label className="label">Email</label>
          <input type="email" className="input" value={form.email} onChange={set('email')} />
        </div>
        <div>
          <label className="label">Telefono</label>
          <input className="input" value={form.telefono} onChange={setMobile('telefono')} inputMode="numeric" placeholder="999999999" />
          <FieldError message={errors.telefono} />
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <label className="label">WhatsApp</label>
          <input className="input" value={form.whatsapp} onChange={setMobile('whatsapp')} inputMode="numeric" placeholder="999999999" />
          <FieldError message={errors.whatsapp} />
        </div>
        <div>
          <label className="label">Condicion de pago</label>
          <CustomSelect
            value={form.condicion_pago}
            onChange={(v) => setForm((c) => ({ ...c, condicion_pago: v }))}
            options={[
              { value: 'contado',    label: 'Contado' },
              { value: 'credito_7',  label: 'Credito 7 dias' },
              { value: 'credito_15', label: 'Credito 15 dias' },
              { value: 'credito_30', label: 'Credito 30 dias' },
            ]}
          />
        </div>
      </div>

      <div className="modal-footer modal-footer--bleed">
        <button type="button" onClick={onCancel} className="btn-modal-cancel">
          Cancelar
        </button>
        <button type="submit" disabled={saving} className="btn-primary flex items-center gap-2">
          {saving ? <Spinner size="sm" /> : <Save className="h-4 w-4" />} Guardar
        </button>
      </div>
    </form>
  );
}

export default function ClientesPage() {
  const toast = useToast();
  const [list, setList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [modal, setModal] = useState(null);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(null);

  const load = () => {
    setLoading(true);
    svc.list()
      .then(setList)
      .catch(() => toast('Error al cargar clientes', 'error'))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const filtered = list.filter(
    (item) =>
      item.razon_social?.toLowerCase().includes(search.toLowerCase()) ||
      item.numero_documento?.includes(search),
  );

  const handleSave = async (form) => {
    setSaving(true);
    try {
      if (modal.mode === 'create') {
        await svc.create(form);
        toast('Cliente creado');
      } else {
        await svc.update(modal.item.id, form);
        toast('Cliente actualizado');
      }
      setModal(null);
      load();
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Eliminar este cliente?')) return;
    setDeleting(id);
    try {
      await svc.remove(id);
      toast('Cliente eliminado');
      load();
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      setDeleting(null);
    }
  };

  return (
    <div className="page-shell">
      <div className="page-header">
        <div className="page-header-copy">
          <p className="page-kicker">Directorio comercial</p>
          <h2 className="page-title">Clientes</h2>
          <p className="page-subtitle">{list.length} registros disponibles para cotizacion y emision.</p>
        </div>
      </div>

      {/* Toolbar */}
      <div className="ink-table-card" style={{ padding: '14px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
        <div className="ink-search" style={{ maxWidth: '400px', flex: '1' }}>
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--text-tertiary)]" />
          <input
            className="input pl-9"
            placeholder="Buscar por nombre o RUC/DNI..."
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>
        <div className="flex items-center gap-2">
          <button className="btn-secondary flex items-center gap-2">
            <Filter className="h-3.5 w-3.5" />
            Filtrar
          </button>
          <button className="btn-primary flex items-center gap-2" onClick={() => setModal({ mode: 'create' })}>
            <Plus className="h-4 w-4" />
            Nuevo cliente
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-16">
          <Spinner size="lg" />
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState
          title="Sin clientes"
          description="Agrega tu primer cliente para empezar el flujo comercial."
          action={
            <button className="btn-primary" onClick={() => setModal({ mode: 'create' })}>
              Agregar cliente
            </button>
          }
        />
      ) : (
        <div className="ink-table-card">
          <table className="ink-table">
            <thead>
              <tr>
                <th>Razon social</th>
                <th>RUC / DNI</th>
                <th>Contacto</th>
                <th>Condicion</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {filtered.map((item) => {
                const cond = item.condicion_pago || 'contado';
                const condLabel = cond.replace(/_/g, ' ');
                const condVariant = cond === 'contado'
                  ? 'ink-aging-badge--ok'
                  : cond.startsWith('credito')
                    ? 'ink-aging-badge--warning'
                    : 'ink-aging-badge--neutral';

                return (
                  <tr key={item.id}>
                    <td data-label="Razon social" style={{ fontWeight: 600 }}>{item.razon_social}</td>
                    <td data-label="RUC / DNI">
                      <span className="font-mono-label text-xs" style={{ color: '#475569', fontWeight: 600 }}>
                        {item.numero_documento}
                      </span>
                    </td>
                    <td data-label="Contacto" style={{ color: '#64748B', fontSize: '13px' }}>
                      {item.email || item.telefono || <span className="ink-empty-cell">--</span>}
                    </td>
                    <td data-label="Condicion">
                      <span className={`ink-aging-badge ${condVariant}`}>
                        {condLabel}
                      </span>
                    </td>
                    <td data-label="Acciones">
                      <div className="ink-row-actions">
                        <button
                          className="ink-row-btn"
                          onClick={() => setModal({ mode: 'edit', item })}
                          title="Editar"
                        >
                          <Pencil className="h-4 w-4" />
                        </button>
                        <button
                          className="ink-row-btn ink-row-btn--danger"
                          onClick={() => handleDelete(item.id)}
                          disabled={deleting === item.id}
                          title="Eliminar"
                        >
                          {deleting === item.id ? <Spinner size="sm" /> : <Trash2 className="h-4 w-4" />}
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <div className="ink-table-footer">
            <span className="ink-table-count">
              Mostrando <strong>{filtered.length}</strong> de <strong>{list.length}</strong> clientes
            </span>
          </div>
        </div>
      )}

      <Modal
        open={!!modal}
        onClose={() => setModal(null)}
        title={modal?.mode === 'create' ? 'Nuevo cliente' : 'Editar cliente'}
        size="lg"
      >
        {modal && (
          <ClienteForm
            initial={modal.mode === 'edit' ? modal.item : EMPTY_FORM}
            onSave={handleSave}
            onCancel={() => setModal(null)}
            saving={saving}
          />
        )}
      </Modal>
    </div>
  );
}
