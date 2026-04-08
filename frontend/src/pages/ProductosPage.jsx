import { useState, useEffect } from 'react';
import { Plus, Search, Pencil, Trash2 } from 'lucide-react';
import { productos as svc } from '../services/productos';
import Spinner from '../components/ui/Spinner';
import EmptyState from '../components/ui/EmptyState';
import Modal from '../components/ui/Modal';
import { useToast } from '../components/ui/Toast';

const EMPTY_FORM = {
  nombre: '',
  descripcion: '',
  precio_unitario: '',
  unidad_medida: 'NIU',
  codigo: '',
};

function ProductoForm({ initial = EMPTY_FORM, onSave, onCancel, saving }) {
  const [form, setForm] = useState(initial);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  return (
    <form onSubmit={(e) => { e.preventDefault(); onSave(form); }} className="space-y-4">
      <div>
        <label className="label">Nombre *</label>
        <input required className="input" value={form.nombre} onChange={set('nombre')} />
      </div>
      <div>
        <label className="label">Descripción</label>
        <textarea className="input resize-none" rows={2} value={form.descripcion} onChange={set('descripcion')} />
      </div>
      <div className="grid grid-cols-3 gap-4">
        <div>
          <label className="label">Precio unit. (S/) *</label>
          <input required type="number" step="0.01" min="0" className="input" value={form.precio_unitario} onChange={set('precio_unitario')} />
        </div>
        <div>
          <label className="label">Unidad</label>
          <select className="input" value={form.unidad_medida} onChange={set('unidad_medida')}>
            <option value="NIU">Unidad</option>
            <option value="ZZ">Servicio</option>
            <option value="KGM">Kg</option>
            <option value="MTR">Metro</option>
          </select>
        </div>
        <div>
          <label className="label">Código interno</label>
          <input className="input" value={form.codigo} onChange={set('codigo')} />
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

export default function ProductosPage() {
  const toast = useToast();
  const [list, setList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [modal, setModal] = useState(null);
  const [saving, setSaving] = useState(false);

  const load = () => {
    setLoading(true);
    svc.list().then(setList).catch(() => toast('Error al cargar productos', 'error')).finally(() => setLoading(false));
  };
  useEffect(load, []);

  const filtered = list.filter((p) =>
    p.nombre?.toLowerCase().includes(search.toLowerCase()) ||
    p.codigo?.toLowerCase().includes(search.toLowerCase())
  );

  const handleSave = async (form) => {
    setSaving(true);
    try {
      const payload = { ...form, precio_unitario: Number(form.precio_unitario) };
      if (modal.mode === 'create') {
        await svc.create(payload);
        toast('Producto creado');
      } else {
        await svc.update(modal.item.id, payload);
        toast('Producto actualizado');
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
    if (!confirm('¿Eliminar este producto?')) return;
    try {
      await svc.remove(id);
      toast('Producto eliminado');
      load();
    } catch (err) {
      toast(err.message, 'error');
    }
  };

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-gray-900">Productos</h1>
          <p className="text-sm text-gray-500">{list.length} productos en catálogo</p>
        </div>
        <button className="btn-primary flex items-center gap-2" onClick={() => setModal({ mode: 'create' })}>
          <Plus className="h-4 w-4" /> Nuevo producto
        </button>
      </div>

      <div className="mb-4 relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
        <input className="input pl-9 max-w-sm" placeholder="Buscar por nombre o código..." value={search} onChange={(e) => setSearch(e.target.value)} />
      </div>

      {loading ? (
        <div className="flex justify-center py-16"><Spinner size="lg" /></div>
      ) : filtered.length === 0 ? (
        <EmptyState title="Sin productos" description="Agrega productos a tu catálogo" action={<button className="btn-primary" onClick={() => setModal({ mode: 'create' })}>Agregar producto</button>} />
      ) : (
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                <th className="px-4 py-3">Nombre</th>
                <th className="px-4 py-3">Código</th>
                <th className="px-4 py-3">Unidad</th>
                <th className="px-4 py-3 text-right">Precio unit.</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {filtered.map((p) => (
                <tr key={p.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{p.nombre}</td>
                  <td className="px-4 py-3 text-gray-500">{p.codigo || '—'}</td>
                  <td className="px-4 py-3 text-gray-500">{p.unidad_medida}</td>
                  <td className="px-4 py-3 text-right font-medium">
                    S/ {Number(p.precio_unitario).toLocaleString('es-PE', { minimumFractionDigits: 2 })}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2 justify-end">
                      <button onClick={() => setModal({ mode: 'edit', item: p })} className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600">
                        <Pencil className="h-4 w-4" />
                      </button>
                      <button onClick={() => handleDelete(p.id)} className="rounded-lg p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-500">
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Modal open={!!modal} onClose={() => setModal(null)} title={modal?.mode === 'create' ? 'Nuevo producto' : 'Editar producto'}>
        {modal && (
          <ProductoForm initial={modal.mode === 'edit' ? modal.item : EMPTY_FORM} onSave={handleSave} onCancel={() => setModal(null)} saving={saving} />
        )}
      </Modal>
    </div>
  );
}
