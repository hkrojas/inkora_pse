import { useCallback, useEffect, useMemo, useState } from 'react';
import { ArrowDown, ArrowUp, Boxes, ClipboardList, PackageCheck, Plus, RefreshCw, Search, Warehouse } from 'lucide-react';
import Button from '../components/ui/Button';
import Spinner from '../components/ui/Spinner';
import EmptyState from '../components/ui/EmptyState';
import { PageError } from '../components/ui/PageState';
import { useToast } from '../components/ui/Toast';
import { useAuth } from '../context/AuthContext';
import { inventory } from '../services/inventory';
import { productos } from '../services/productos';

const tabs = [
  { id: 'stock', label: 'Existencias', icon: Boxes },
  { id: 'kardex', label: 'Kardex', icon: ClipboardList },
  { id: 'warehouses', label: 'Almacenes', icon: Warehouse },
];
const qty = (value) => Number(value || 0).toLocaleString('es-PE', { maximumFractionDigits: 4 });
const labels = { ok: 'Disponible', low: 'Stock bajo', out: 'Agotado', negative: 'Negativo' };

function Metric({ label, value, danger }) {
  return <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4"><p className="text-[10px] font-black uppercase tracking-wider text-[var(--color-text-muted)]">{label}</p><p className={`mt-2 font-mono text-2xl font-black ${danger ? 'text-[var(--color-danger)]' : ''}`}>{value}</p></div>;
}

export default function InventarioPage() {
  const { user } = useAuth();
  const toast = useToast();
  const [tab, setTab] = useState('stock');
  const [stock, setStock] = useState([]);
  const [movements, setMovements] = useState([]);
  const [warehouses, setWarehouses] = useState([]);
  const [catalog, setCatalog] = useState([]);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [open, setOpen] = useState(false);
  const [configOpen, setConfigOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ warehouse_id: '', product_id: '', quantity: '', reason: '' });
  const [config, setConfig] = useState({ product_id: '', warehouse_id: '', opening_stock: '0', minimum_stock: '0', item_type: 'inventory' });
  const isAdmin = user?.is_superadmin || user?.rol === 'admin';
  const canOperate = isAdmin || user?.rol === 'operador';

  const load = useCallback(async () => {
    setLoading(true); setError('');
    try {
      const [s, m, w, p] = await Promise.all([inventory.stock(), inventory.movements(), inventory.warehouses(), productos.list('?skip=0&limit=100')]);
      setStock(s); setMovements(m); setWarehouses(w); setCatalog(p);
    } catch (err) { setError(err.message || 'No se pudo cargar el inventario.'); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const filtered = useMemo(() => {
    const term = query.trim().toLowerCase();
    return term ? stock.filter((row) => `${row.product_name} ${row.product_code || ''} ${row.warehouse_name}`.toLowerCase().includes(term)) : stock;
  }, [query, stock]);
  const uniqueProducts = useMemo(() => [...new Map(stock.map((row) => [row.product_id, row])).values()], [stock]);
  const alerts = stock.filter((row) => ['low', 'out', 'negative'].includes(row.status)).length;

  const activate = async () => {
    setSaving(true);
    try { await inventory.activate({ warehouse_name: 'Almacén principal', warehouse_code: 'PRINCIPAL' }); toast('Inventario activado.', 'success'); await load(); }
    catch (err) { toast(err.message, 'error'); } finally { setSaving(false); }
  };
  const submit = async (event) => {
    event.preventDefault(); setSaving(true);
    try {
      await inventory.adjust({ ...form, warehouse_id: Number(form.warehouse_id), product_id: Number(form.product_id), quantity: Number(form.quantity), movement_type: 'adjustment' });
      toast('Ajuste registrado en el kardex.', 'success'); setOpen(false); setForm({ warehouse_id: '', product_id: '', quantity: '', reason: '' }); await load();
    } catch (err) { toast(err.message, 'error'); } finally { setSaving(false); }
  };
  const configure = async (event) => {
    event.preventDefault(); setSaving(true);
    try {
      await inventory.configureProduct(Number(config.product_id), {
        item_type: config.item_type,
        inventory_enabled: config.item_type === 'inventory',
        warehouse_id: config.item_type === 'inventory' ? Number(config.warehouse_id) : null,
        opening_stock: Number(config.opening_stock), minimum_stock: Number(config.minimum_stock),
      });
      toast('Configuración de inventario guardada.', 'success'); setConfigOpen(false); await load();
    } catch (err) { toast(err.message, 'error'); } finally { setSaving(false); }
  };

  if (loading) return <div className="grid min-h-[360px] place-items-center"><Spinner /></div>;
  if (error) return <PageError title="No se pudo cargar Inventario" description={error} onRetry={load} />;

  return <main className="mx-auto w-full max-w-[1500px] space-y-5 pb-10">
    <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between"><div><p className="text-[10px] font-black uppercase tracking-[0.16em] text-[var(--color-primary)]">Control operativo</p><h1 className="mt-1 text-3xl font-black tracking-[-0.04em]">Inventario</h1><p className="mt-1 text-sm text-[var(--color-text-muted)]">Stock comercial, compromisos SUNAT y trazabilidad por comprobante.</p></div><div className="flex flex-wrap gap-2"><Button variant="secondary" onClick={load}><RefreshCw size={15} />Actualizar</Button>{isAdmin && warehouses.length > 0 && <Button variant="secondary" onClick={() => setConfigOpen(true)}><PackageCheck size={15} />Configurar producto</Button>}{canOperate && stock.length > 0 && <Button onClick={() => setOpen(true)}><Plus size={15} />Registrar ajuste</Button>}</div></header>
    <section className="grid gap-3 sm:grid-cols-3" aria-label="Resumen"><Metric label="Productos controlados" value={uniqueProducts.length} /><Metric label="Alertas de stock" value={alerts} danger={alerts > 0} /><Metric label="Unidades comprometidas" value={qty(stock.reduce((sum, row) => sum + Number(row.committed || 0), 0))} /></section>
    <div className="flex gap-1 overflow-x-auto rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-1" role="tablist">{tabs.map(({ id, label, icon: Icon }) => <button key={id} type="button" role="tab" aria-selected={tab === id} onClick={() => setTab(id)} className={`inline-flex min-h-10 items-center gap-2 rounded-xl px-4 text-sm font-bold ${tab === id ? 'bg-[var(--color-primary-soft)] text-[var(--color-primary)]' : 'text-[var(--color-text-muted)] hover:bg-[var(--color-surface-soft)]'}`}><Icon size={15} />{label}</button>)}</div>
    {tab === 'stock' && <section className="overflow-hidden rounded-3xl border border-[var(--color-border)] bg-[var(--color-surface)]"><div className="border-b border-[var(--color-border)] p-4"><label className="relative block max-w-md"><Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" size={16} /><span className="sr-only">Buscar existencias</span><input className="input pl-10" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Producto, SKU o almacén" /></label></div>{filtered.length === 0 ? <div className="p-8"><EmptyState icon={PackageCheck} title="Aún no hay productos con stock" description="Activa el inventario en un producto y registra su saldo de apertura." action={isAdmin ? { label: 'Activar inventario', onClick: activate, loading: saving } : undefined} /></div> : <div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm"><thead className="bg-[var(--color-surface-soft)] text-[10px] uppercase tracking-wider text-[var(--color-text-muted)]"><tr><th className="px-5 py-3">Producto</th><th className="px-5 py-3">Almacén</th><th className="px-5 py-3 text-right">Actual</th><th className="px-5 py-3 text-right">Comprometido</th><th className="px-5 py-3 text-right">Disponible</th><th className="px-5 py-3">Estado</th></tr></thead><tbody className="divide-y divide-[var(--color-border)]">{filtered.map((row) => <tr key={`${row.warehouse_id}-${row.product_id}`}><td className="px-5 py-4"><p className="font-bold">{row.product_name}</p><p className="text-xs text-[var(--color-text-muted)]">{row.product_code || 'Sin SKU'} · {row.unit}</p></td><td className="px-5 py-4 text-[var(--color-text-muted)]">{row.warehouse_name}</td><td className="px-5 py-4 text-right font-mono font-bold">{qty(row.on_hand)}</td><td className="px-5 py-4 text-right font-mono">{qty(row.committed)}</td><td className="px-5 py-4 text-right font-mono font-black">{qty(row.available)}</td><td className="px-5 py-4"><span className={`rounded-full px-2.5 py-1 text-xs font-bold ${row.status === 'ok' ? 'bg-[var(--color-success-soft)] text-[var(--color-success)]' : 'bg-[var(--color-danger-soft)] text-[var(--color-danger)]'}`}>{labels[row.status]}</span></td></tr>)}</tbody></table></div>}</section>}
    {tab === 'kardex' && <section className="overflow-hidden rounded-3xl border border-[var(--color-border)] bg-[var(--color-surface)]">{movements.length === 0 ? <div className="p-8"><EmptyState icon={ClipboardList} title="El kardex está vacío" description="Aperturas, ventas aceptadas, ajustes y transferencias aparecerán aquí." /></div> : <div className="overflow-x-auto"><table className="w-full min-w-[800px] text-left text-sm"><thead className="bg-[var(--color-surface-soft)] text-[10px] uppercase tracking-wider text-[var(--color-text-muted)]"><tr><th className="px-5 py-3">Fecha</th><th className="px-5 py-3">Producto</th><th className="px-5 py-3">Origen</th><th className="px-5 py-3 text-right">Movimiento</th><th className="px-5 py-3 text-right">Saldo</th></tr></thead><tbody className="divide-y divide-[var(--color-border)]">{movements.map((row) => <tr key={row.id}><td className="px-5 py-4 text-[var(--color-text-muted)]">{new Date(row.created_at).toLocaleString('es-PE')}</td><td className="px-5 py-4"><b>{row.product_name}</b><p className="text-xs text-[var(--color-text-muted)]">{row.warehouse_name}</p></td><td className="px-5 py-4">{row.reason || row.source_type}{row.source_id && <p className="text-xs text-[var(--color-text-muted)]">Documento #{row.source_id}</p>}</td><td className={`px-5 py-4 text-right font-mono font-black ${Number(row.quantity) >= 0 ? 'text-[var(--color-success)]' : 'text-[var(--color-danger)]'}`}>{Number(row.quantity) >= 0 ? <ArrowUp className="mr-1 inline" size={13} /> : <ArrowDown className="mr-1 inline" size={13} />}{qty(Math.abs(row.quantity))}</td><td className="px-5 py-4 text-right font-mono font-bold">{qty(row.balance_after)}</td></tr>)}</tbody></table></div>}</section>}
    {tab === 'warehouses' && <section className="grid gap-3 md:grid-cols-2">{warehouses.length === 0 ? <EmptyState icon={Warehouse} title="Configura el almacén principal" description="El inventario sigue desactivado hasta completar este paso." action={isAdmin ? { label: 'Activar inventario', onClick: activate, loading: saving } : undefined} /> : warehouses.map((row) => <article key={row.id} className="rounded-3xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5"><div className="flex justify-between"><Warehouse className="text-[var(--color-primary)]" />{row.is_default && <span className="rounded-full bg-[var(--color-primary-soft)] px-2 py-1 text-[10px] font-black uppercase text-[var(--color-primary)]">Principal</span>}</div><h2 className="mt-4 font-black">{row.name}</h2><p className="font-mono text-xs text-[var(--color-text-muted)]">{row.code}</p><p className="mt-3 text-sm text-[var(--color-text-muted)]">{row.location || 'Sin ubicación registrada'}</p></article>)}</section>}
    {open && <div className="fixed inset-0 z-50 grid place-items-center bg-black/45 p-4" onMouseDown={(e) => e.target === e.currentTarget && setOpen(false)}><form onSubmit={submit} role="dialog" aria-modal="true" aria-labelledby="adjust-title" className="w-full max-w-lg space-y-4 rounded-3xl bg-[var(--color-surface)] p-6 shadow-[var(--shadow-floating)]"><div><h2 id="adjust-title" className="text-xl font-black">Registrar ajuste</h2><p className="text-sm text-[var(--color-text-muted)]">Usa una cantidad negativa para una salida manual.</p></div><label className="block text-sm font-bold">Almacén<select required className="input mt-1" value={form.warehouse_id} onChange={(e) => setForm({ ...form, warehouse_id: e.target.value })}><option value="">Selecciona</option>{warehouses.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}</select></label><label className="block text-sm font-bold">Producto<select required className="input mt-1" value={form.product_id} onChange={(e) => setForm({ ...form, product_id: e.target.value })}><option value="">Selecciona</option>{uniqueProducts.map((p) => <option key={p.product_id} value={p.product_id}>{p.product_name}</option>)}</select></label><label className="block text-sm font-bold">Cantidad<input required type="number" step="0.0001" className="input mt-1" value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })} /></label><label className="block text-sm font-bold">Motivo<textarea required minLength={3} className="input mt-1 min-h-20" value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} /></label><div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={() => setOpen(false)}>Cancelar</Button><Button type="submit" loading={saving}>Guardar</Button></div></form></div>}
    {configOpen && <div className="fixed inset-0 z-50 grid place-items-center bg-black/45 p-4" onMouseDown={(e) => e.target === e.currentTarget && setConfigOpen(false)}><form onSubmit={configure} role="dialog" aria-modal="true" aria-labelledby="config-title" className="w-full max-w-lg space-y-4 rounded-3xl bg-[var(--color-surface)] p-6 shadow-[var(--shadow-floating)]"><div><h2 id="config-title" className="text-xl font-black">Configurar producto</h2><p className="text-sm text-[var(--color-text-muted)]">Los documentos anteriores no modificarán este saldo de apertura.</p></div><label className="block text-sm font-bold">Producto<select required className="input mt-1" value={config.product_id} onChange={(e) => setConfig({ ...config, product_id: e.target.value })}><option value="">Selecciona</option>{catalog.map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}</select></label><label className="block text-sm font-bold">Tipo<select className="input mt-1" value={config.item_type} onChange={(e) => setConfig({ ...config, item_type: e.target.value })}><option value="inventory">Producto inventariable</option><option value="service">Servicio (sin stock)</option></select></label>{config.item_type === 'inventory' && <><label className="block text-sm font-bold">Almacén<select required className="input mt-1" value={config.warehouse_id} onChange={(e) => setConfig({ ...config, warehouse_id: e.target.value })}><option value="">Selecciona</option>{warehouses.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}</select></label><div className="grid grid-cols-2 gap-3"><label className="block text-sm font-bold">Saldo de apertura<input type="number" step="0.0001" className="input mt-1" value={config.opening_stock} onChange={(e) => setConfig({ ...config, opening_stock: e.target.value })} /></label><label className="block text-sm font-bold">Stock mínimo<input type="number" min="0" step="0.0001" className="input mt-1" value={config.minimum_stock} onChange={(e) => setConfig({ ...config, minimum_stock: e.target.value })} /></label></div></>}<div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={() => setConfigOpen(false)}>Cancelar</Button><Button type="submit" loading={saving}>Guardar</Button></div></form></div>}
  </main>;
}
