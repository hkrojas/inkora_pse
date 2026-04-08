import { useState, useEffect } from 'react';
import { Plus, Search, Pencil, Trash2 } from 'lucide-react';
import { clientes as svc } from '../services/clientes';
import Spinner from '../components/ui/Spinner';
import EmptyState from '../components/ui/EmptyState';
import Modal from '../components/ui/Modal';
import { useToast } from '../components/ui/Toast';

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

function ClienteForm({ initial = EMPTY_FORM, onSave, onCancel, saving }) {
  const [form, setForm] = useState(initial);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave(form);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="label">Tipo doc.</label>
          <select className="input" value={form.tipo_documento} onChange={set('tipo_documento')}>
            <option value="6">RUC</option>
            <option value="1">DNI</option>
            <option value="0">Otro</option>
          </select>
        </div>
        <div>
          <label className="label">Nº documento *</label>
          <input required className="input" value={form.numero_documento} onChange={set('numero_documento')} />
        </div>
      </div>
      <div>
        <label className="label">Razón social / Nombre *</label>
        <input required className="input" value={form.razon_social} onChange={set('razon_social')} />
      </div>
      <div>
        <label className="label">Dirección</label>
        <input className="input" value={form.direccion} onChange={set('direccion')} />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="label">Email</label>
          <input type="email" className="input" value={form.email} onChange={set('email')} />
        </div>
        <div>
          <label className="label">Teléfono</label>
          <input className="input" value={form.telefono} onChange={set('telefono')} />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="label">WhatsApp</label>
          <input className="input" value={form.whatsapp} onChange={set('whatsapp')} />
        </div>
        <div>
          <label className="label">Condición de pago</label>
          <select className="input" value={form.condicion_pago} onChange={set('condicion_pago')}>
            <option value="contado">Contado</option>
            <option value="credito_7">Crédito 7 días</option>
            <option value="credito_15">Crédito 15 días</option>
            <option value="credito_30">Crédito 30 días</option>
          </select>
        </div>
      </div>
      <div className="flex justify-end gap-3 pt-2">
        <button type="button" onClick={onCancel} className="btn-secondary">Cancelar</button>
        <button type="submit" disabled={saving} className="btn-primary flex items-center gap-2">
          {saving && <Spinner size="sm" />} Guardar
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
  const [modal, setModal] = useState(null); // null | { mode: 'create' } | { mode: 'edit', item }
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(null);

  const load = () => {
    setLoading(true);
    svc.list().then(setList).catch(() => toast('Error al cargar clientes', 'error')).finally(() => setLoading(false));
  };

  useEffect(load, []);

  const filtered = list.filter((c) =>
    c.razon_social?.toLowerCase().includes(search.toLowerCase()) ||
    c.numero_documento?.includes(search)
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
    if (!confirm('¿Eliminar este cliente?')) return;
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
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-gray-900">Clientes</h1>
          <p className="text-sm text-gray-500">{list.length} clientes registrados</p>
        </div>
        <button className="btn-primary flex items-center gap-2" onClick={() => setModal({ mode: 'create' })}>
          <Plus className="h-4 w-4" /> Nuevo cliente
        </button>
      </div>

      {/* Search */}
      <div className="mb-4 relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
        <input
          className="input pl-9 max-w-sm"
          placeholder="Buscar por nombre o RUC/DNI..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {/* Table */}
      {loading ? (
        <div className="flex justify-center py-16"><Spinner size="lg" /></div>
      ) : filtered.length === 0 ? (
        <EmptyState
          title="Sin clientes"
          description="Agrega tu primer cliente para empezar"
          action={<button className="btn-primary" onClick={() => setModal({ mode: 'create' })}>Agregar cliente</button>}
        />
      ) : (
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                <th className="px-4 py-3">Razón social</th>
                <th className="px-4 py-3">RUC/DNI</th>
                <th className="px-4 py-3">Contacto</th>
                <th className="px-4 py-3">Condición</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {filtered.map((c) => (
                <tr key={c.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 font-medium text-gray-900">{c.razon_social}</td>
                  <td className="px-4 py-3 text-gray-500">{c.numero_documento}</td>
                  <td className="px-4 py-3 text-gray-500">{c.email || c.telefono || '—'}</td>
                  <td className="px-4 py-3 text-gray-500 capitalize">{c.condicion_pago?.replace('_', ' ') || 'contado'}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2 justify-end">
                      <button
                        onClick={() => setModal({ mode: 'edit', item: c })}
                        className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
                      >
                        <Pencil className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => handleDelete(c.id)}
                        disabled={deleting === c.id}
                        className="rounded-lg p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-500"
                      >
                        {deleting === c.id ? <Spinner size="sm" /> : <Trash2 className="h-4 w-4" />}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
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
