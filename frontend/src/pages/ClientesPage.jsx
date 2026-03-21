// Ruta: frontend/src/pages/ClientesPage.jsx
import React, { useEffect, useState } from 'react';
import DashboardLayout from '../components/DashboardLayout.jsx';
import { Plus, Search, Pencil, Trash2, Building2 } from 'lucide-react';
import Button from '../components/Button.jsx';
import ClienteModal from '../components/ClienteModal.jsx';
import { getClientes, deleteCliente } from '../utils/apiUtils.js';
import { useToast } from '../context/ToastContext.jsx';
import LoadingSpinner from '../components/LoadingSpinner.jsx';

const ClientesPage = () => {
  const [clientes, setClientes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingCliente, setEditingCliente] = useState(null);
  const { showToast } = useToast();

  const fetchData = async () => {
    try { setClientes(await getClientes()); } 
    catch (e) { showToast('Error al cargar', 'error'); } 
    finally { setLoading(false); }
  };

  useEffect(() => { fetchData(); }, []);

  const handleDelete = async (id) => {
    if (window.confirm('¿Eliminar cliente?')) {
      try { await deleteCliente(id); showToast('Eliminado', 'success'); fetchData(); } 
      catch (e) { showToast('Error al eliminar', 'error'); }
    }
  };

  const filtered = clientes.filter(c => c.razon_social.toLowerCase().includes(filter.toLowerCase()) || c.numero_documento.includes(filter));

  return (
    <DashboardLayout title="Directorio de Clientes">
      <div className="card p-6 md:p-8">
        <div className="flex flex-col sm:flex-row justify-between items-center gap-4 mb-8">
          <div className="relative w-full sm:w-[400px]">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 h-5 w-5" />
            <input type="text" placeholder="Buscar empresa o RUC..." className="input-field pl-12" value={filter} onChange={(e) => setFilter(e.target.value)} />
          </div>
          <Button onClick={() => {setEditingCliente(null); setIsModalOpen(true);}} icon={Plus} className="w-full sm:w-auto">Nuevo Cliente</Button>
        </div>

        {loading ? <div className="flex justify-center py-20"><LoadingSpinner /></div> : (
          <div className="overflow-x-auto rounded-2xl border border-slate-100 dark:border-surface-800">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50 dark:bg-surface-900 border-b border-slate-100 dark:border-surface-800 text-slate-400 dark:text-surface-400 text-xs font-bold uppercase tracking-wider">
                  <th className="py-4 px-6">Razón Social</th>
                  <th className="py-4 px-6">Identificación</th>
                  <th className="py-4 px-6">Contacto</th>
                  <th className="py-4 px-6 text-right">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50 dark:divide-surface-800">
                {filtered.map((c) => (
                  <tr key={c.id} className="hover:bg-slate-50/50 dark:hover:bg-surface-900/50 transition-colors group">
                    <td className="py-4 px-6">
                      <div className="flex items-center gap-4">
                        <div className="w-10 h-10 rounded-xl bg-blue-50 dark:bg-blue-500/10 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
                          <Building2 size={20} strokeWidth={2.5} />
                        </div>
                        <span className="font-bold text-slate-900 dark:text-white">{c.razon_social}</span>
                      </div>
                    </td>
                    <td className="py-4 px-6">
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-1 bg-slate-100 dark:bg-surface-800 rounded-md text-[10px] font-bold text-slate-500 dark:text-surface-400 uppercase tracking-wider">{c.tipo_documento === '6' ? 'RUC' : 'DNI'}</span>
                        <span className="font-mono text-sm text-slate-600 dark:text-surface-300">{c.numero_documento}</span>
                      </div>
                    </td>
                    <td className="py-4 px-6 text-sm text-slate-600 dark:text-surface-300">
                      <div className="font-medium">{c.email || 'Sin correo'}</div>
                      <div className="text-xs text-slate-400">{c.telefono || 'Sin teléfono'}</div>
                    </td>
                    <td className="py-4 px-6 text-right">
                      <div className="flex justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button onClick={() => {setEditingCliente(c); setIsModalOpen(true);}} className="p-2 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 dark:hover:bg-indigo-500/20 rounded-xl transition-all"><Pencil size={18} /></button>
                        <button onClick={() => handleDelete(c.id)} className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-500/20 rounded-xl transition-all"><Trash2 size={18} /></button>
                      </div>
                    </td>
                  </tr>
                ))}
                {filtered.length === 0 && <tr><td colSpan="4" className="py-16 text-center text-slate-400 font-medium">Ningún cliente encontrado</td></tr>}
              </tbody>
            </table>
          </div>
        )}
      </div>
      <ClienteModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} clienteToEdit={editingCliente} onSuccess={fetchData} />
    </DashboardLayout>
  );
};

export default ClientesPage;