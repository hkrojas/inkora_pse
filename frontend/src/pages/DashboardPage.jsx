// Ruta: frontend/src/pages/DashboardPage.jsx
import React, { useEffect, useState } from 'react';
import DashboardLayout from '../components/DashboardLayout.jsx';
import Card from '../components/Card.jsx';
import { DollarSign, FileText, Users, Package, TrendingUp, AlertCircle } from 'lucide-react';
import { getCotizaciones, getClientes, getProductos } from '../utils/apiUtils.js';
import { useAuth } from '../context/AuthContext.jsx';
import { useToast } from '../context/ToastContext.jsx';
import LoadingSpinner from '../components/LoadingSpinner.jsx';

const StatCard = ({ title, value, icon: Icon, colorClass }) => (
  <div className="card p-6 flex items-center gap-5 hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1">
    <div className={`w-14 h-14 rounded-2xl flex items-center justify-center shrink-0 ${colorClass}`}>
      <Icon size={24} strokeWidth={2.5} />
    </div>
    <div>
      <h4 className="text-xs font-bold uppercase tracking-widest text-slate-400 dark:text-surface-400 mb-1">{title}</h4>
      <p className="text-2xl font-black text-slate-900 dark:text-white">{value}</p>
    </div>
  </div>
);

const DashboardPage = () => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({ ventasMes: 0, docsCount: 0, cliCount: 0, prodCount: 0, recentDocs: [] });

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [docs, cli, prod] = await Promise.all([getCotizaciones(), getClientes(), getProductos()]);
        const m = new Date().getMonth();
        const v = docs.filter(c => new Date(c.fecha_emision).getMonth() === m).reduce((s, c) => s + c.total_venta, 0);
        setStats({ ventasMes: v, docsCount: docs.length, cliCount: cli.length, prodCount: prod.length, recentDocs: docs.slice(0, 5) });
      } catch (e) {} finally { setLoading(false); }
    };
    fetchData();
  }, []);

  if (loading) return <DashboardLayout title="Panel Principal"><div className="flex justify-center py-32"><LoadingSpinner /></div></DashboardLayout>;

  return (
    <DashboardLayout title={`Hola, ${user?.nombre_completo || 'Usuario'}`}>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard title="Ventas del Mes" value={`S/ ${stats.ventasMes.toFixed(2)}`} icon={DollarSign} colorClass="bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400" />
        <StatCard title="Documentos" value={stats.docsCount} icon={FileText} colorClass="bg-blue-50 dark:bg-blue-500/10 text-blue-600 dark:text-blue-400" />
        <StatCard title="Clientes" value={stats.cliCount} icon={Users} colorClass="bg-purple-50 dark:bg-purple-500/10 text-purple-600 dark:text-purple-400" />
        <StatCard title="Productos" value={stats.prodCount} icon={Package} colorClass="bg-amber-50 dark:bg-amber-500/10 text-amber-600 dark:text-amber-400" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 card p-6 md:p-8">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-lg font-black text-slate-900 dark:text-white">Movimientos Recientes</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-slate-100 dark:border-surface-800 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                  <th className="pb-4">Cliente</th>
                  <th className="pb-4">Fecha</th>
                  <th className="pb-4 text-right">Monto</th>
                  <th className="pb-4 text-center">Estado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50 dark:divide-surface-800/50">
                {stats.recentDocs.map((doc) => (
                  <tr key={doc.id} className="hover:bg-slate-50/50 dark:hover:bg-surface-900/50 transition-colors">
                    <td className="py-4">
                      <p className="font-bold text-slate-900 dark:text-white">{doc.cliente.razon_social}</p>
                      <p className="text-xs text-slate-500 font-mono mt-0.5">{doc.serie}-{String(doc.correlativo).padStart(6,'0')}</p>
                    </td>
                    <td className="py-4 text-sm text-slate-600 dark:text-surface-300">{new Date(doc.fecha_emision).toLocaleDateString()}</td>
                    <td className="py-4 text-right font-black text-slate-900 dark:text-white">{doc.moneda==='PEN'?'S/':'$'} {doc.total_venta.toFixed(2)}</td>
                    <td className="py-4 text-center">
                      <span className={`px-2.5 py-1 rounded-md text-[10px] font-bold uppercase tracking-wider ${doc.estado === 'facturada' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300' : 'bg-slate-100 text-slate-600 dark:bg-surface-800 dark:text-surface-300'}`}>
                        {doc.estado === 'facturada' ? 'Emitido' : 'Borrador'}
                      </span>
                    </td>
                  </tr>
                ))}
                {stats.recentDocs.length === 0 && <tr><td colSpan="4" className="py-12 text-center text-slate-400">Sin movimientos</td></tr>}
              </tbody>
            </table>
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-gradient-to-br from-indigo-600 to-blue-700 rounded-3xl p-8 text-white shadow-2xl shadow-indigo-600/20 relative overflow-hidden">
            <div className="absolute top-0 right-0 w-48 h-48 bg-white/10 rounded-full blur-2xl -mr-10 -mt-10"></div>
            <div className="flex items-start justify-between mb-6 relative">
              <div>
                <p className="text-indigo-100 text-xs font-bold uppercase tracking-widest mb-2">Conexión SUNAT</p>
                <h3 className="text-3xl font-black">En Línea</h3>
              </div>
              <div className="p-3 bg-white/20 backdrop-blur-md rounded-2xl"><TrendingUp className="w-6 h-6" /></div>
            </div>
            <p className="text-sm text-indigo-100/90 font-medium leading-relaxed relative">Servicios de emisión y validación operando a máxima capacidad.</p>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
};

export default DashboardPage;