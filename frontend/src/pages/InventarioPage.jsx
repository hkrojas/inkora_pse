import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ArrowDown, ArrowLeftRight, ArrowUp, Boxes, ClipboardList, PackageCheck,
  Plus, RefreshCw, RotateCcw, Search, Warehouse,
} from 'lucide-react';
import Button from '../components/ui/Button';
import EmptyState from '../components/ui/EmptyState';
import Modal from '../components/ui/Modal';
import Pagination from '../components/ui/Pagination';
import Spinner from '../components/ui/Spinner';
import { PageError } from '../components/ui/PageState';
import { useToast } from '../components/ui/Toast';
import { useAuth } from '../context/AuthContext';
import { inventory } from '../services/inventory';
import { productos } from '../services/productos';

const PAGE_SIZE = 15;
const tabs = [
  { id: 'stock', label: 'Existencias', icon: Boxes },
  { id: 'kardex', label: 'Kardex', icon: ClipboardList },
  { id: 'warehouses', label: 'Almacenes', icon: Warehouse },
  { id: 'transfers', label: 'Transferencias', icon: ArrowLeftRight },
  { id: 'returns', label: 'Devoluciones', icon: RotateCcw },
];
const labels = { ok: 'Disponible', low: 'Stock bajo', out: 'Agotado', negative: 'Negativo' };
const qty = (value) => Number(value || 0).toLocaleString('es-PE', { maximumFractionDigits: 4 });

function Metric({ label, value, danger }) {
  return (
    <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
      <p className="text-[10px] font-black uppercase tracking-wider text-[var(--color-text-muted)]">{label}</p>
      <p className={`mt-2 font-mono text-2xl font-black ${danger ? 'text-[var(--color-danger)]' : ''}`}>{value}</p>
    </div>
  );
}

function StockStatus({ status }) {
  const ok = status === 'ok';
  return (
    <span className={`rounded-full px-2.5 py-1 text-xs font-bold ${ok ? 'bg-[var(--color-success-soft)] text-[var(--color-success)]' : 'bg-[var(--color-danger-soft)] text-[var(--color-danger)]'}`}>
      {labels[status] || status}
    </span>
  );
}

export default function InventarioPage() {
  const { user } = useAuth();
  const toast = useToast();
  const isAdmin = user?.is_superadmin || user?.rol === 'admin';
  const canOperate = isAdmin || user?.rol === 'operador';
  const [tab, setTab] = useState('stock');
  const [stock, setStock] = useState([]);
  const [movements, setMovements] = useState([]);
  const [movementTotal, setMovementTotal] = useState(0);
  const [movementPage, setMovementPage] = useState(1);
  const [warehouses, setWarehouses] = useState([]);
  const [returns, setReturns] = useState([]);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [modal, setModal] = useState(null);
  const [selectedReturn, setSelectedReturn] = useState(null);
  const [productQuery, setProductQuery] = useState('');
  const [productOptions, setProductOptions] = useState([]);
  const [form, setForm] = useState({ warehouse_id: '', product_id: '', quantity: '', reason: '', movement_type: 'adjustment' });
  const [warehouseForm, setWarehouseForm] = useState({ code: '', name: '', location: '', is_default: false });
  const [config, setConfig] = useState({ product_id: '', warehouse_id: '', opening_stock: '0', minimum_stock: '0', item_type: 'inventory' });
  const [transfer, setTransfer] = useState({ source_warehouse_id: '', destination_warehouse_id: '', product_id: '', quantity: '', reason: '' });
  const [receipt, setReceipt] = useState({});

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const skip = (movementPage - 1) * PAGE_SIZE;
      const [stockRows, movementData, warehouseRows, returnRows] = await Promise.all([
        inventory.stock(),
        inventory.movementsPage(`?skip=${skip}&limit=${PAGE_SIZE}`),
        inventory.warehouses(),
        inventory.returns('?skip=0&limit=15'),
      ]);
      setStock(stockRows);
      setMovements(movementData.items || []);
      setMovementTotal(Number(movementData.total || 0));
      setWarehouses(warehouseRows);
      setReturns(returnRows);
    } catch (err) {
      setError(err.message || 'No se pudo cargar el inventario.');
    } finally {
      setLoading(false);
    }
  }, [movementPage]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    if (productQuery.trim().length < 2) {
      setProductOptions([]);
      return undefined;
    }
    const timer = window.setTimeout(() => {
      productos.search(productQuery.trim(), 20)
        .then(setProductOptions)
        .catch(() => setProductOptions([]));
    }, 250);
    return () => window.clearTimeout(timer);
  }, [productQuery]);

  const filtered = useMemo(() => {
    const term = query.trim().toLowerCase();
    return term
      ? stock.filter((row) => `${row.product_name} ${row.product_code || ''} ${row.warehouse_name}`.toLowerCase().includes(term))
      : stock;
  }, [query, stock]);
  const uniqueProducts = useMemo(() => [...new Map(stock.map((row) => [row.product_id, row])).values()], [stock]);
  const alerts = stock.filter((row) => ['low', 'out', 'negative'].includes(row.status)).length;
  const movementPages = Math.max(1, Math.ceil(movementTotal / PAGE_SIZE));

  const run = async (action, successMessage) => {
    setSaving(true);
    try {
      await action();
      toast(successMessage, 'success');
      setModal(null);
      setSelectedReturn(null);
      await load();
    } catch (err) {
      toast(err.message || 'No se pudo completar la operación.', 'error');
    } finally {
      setSaving(false);
    }
  };

  const activate = () => run(
    () => inventory.activate({ warehouse_name: 'Almacén principal', warehouse_code: 'PRINCIPAL' }),
    'Inventario activado.',
  );
  const submitAdjustment = (event) => {
    event.preventDefault();
    return run(() => inventory.adjust({
      ...form,
      warehouse_id: Number(form.warehouse_id),
      product_id: Number(form.product_id),
      quantity: Number(form.quantity),
      movement_type: form.movement_type || 'adjustment',
    }), 'Ajuste registrado en el kardex.');
  };
  const openAdjustment = () => {
    setForm({ warehouse_id: warehouses[0]?.id || '', product_id: '', quantity: '', reason: '', movement_type: 'adjustment' });
    setModal('adjust');
  };
  const openStock = (row) => {
    setForm({
      warehouse_id: row.warehouse_id,
      product_id: row.product_id,
      quantity: '',
      reason: 'Carga de stock disponible',
      movement_type: 'opening_adjustment',
    });
    setModal('stock');
  };
  const submitWarehouse = (event) => {
    event.preventDefault();
    return run(() => inventory.createWarehouse(warehouseForm), 'Almacén creado.');
  };
  const submitConfig = (event) => {
    event.preventDefault();
    return run(() => inventory.configureProduct(Number(config.product_id), {
      item_type: config.item_type,
      inventory_enabled: config.item_type === 'inventory',
      warehouse_id: config.item_type === 'inventory' ? Number(config.warehouse_id) : null,
      opening_stock: Number(config.opening_stock),
      minimum_stock: Number(config.minimum_stock),
    }), 'Configuración de inventario guardada.');
  };
  const submitTransfer = (event) => {
    event.preventDefault();
    return run(() => inventory.transfer({
      source_warehouse_id: Number(transfer.source_warehouse_id),
      destination_warehouse_id: Number(transfer.destination_warehouse_id),
      reason: transfer.reason,
      items: [{ product_id: Number(transfer.product_id), quantity: Number(transfer.quantity) }],
    }), 'Transferencia registrada.');
  };
  const openReceipt = (row) => {
    setSelectedReturn(row);
    setReceipt(Object.fromEntries(row.items.map((item) => [item.id, ''])));
    setModal('receipt');
  };
  const submitReceipt = (event) => {
    event.preventDefault();
    const items = selectedReturn.items
      .map((item) => ({ return_item_id: item.id, quantity: Number(receipt[item.id] || 0) }))
      .filter((item) => item.quantity > 0);
    return run(() => inventory.receiveReturn(selectedReturn.id, { items, reason: 'Recepción física confirmada' }), 'Recepción registrada en el kardex.');
  };

  if (loading && !stock.length) return <div className="grid min-h-[360px] place-items-center"><Spinner /></div>;
  if (error && !stock.length) return <PageError title="No se pudo cargar Inventario" description={error} onRetry={load} />;

  return (
    <main className="mx-auto w-full max-w-[1500px] space-y-5 pb-10">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-[10px] font-black uppercase tracking-[0.16em] text-[var(--color-primary)]">Control operativo</p>
          <h1 className="mt-1 text-3xl font-black tracking-[-0.04em]">Inventario</h1>
          <p className="mt-1 text-sm text-[var(--color-text-muted)]">Existencias, almacenes y movimientos vinculados a comprobantes.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" onClick={load}><RefreshCw size={15} />Actualizar</Button>
          {isAdmin && warehouses.length > 0 && <Button variant="secondary" onClick={() => setModal('config')}><PackageCheck size={15} />Configurar producto</Button>}
          {canOperate && stock.length > 0 && <Button onClick={openAdjustment}><Plus size={15} />Registrar movimiento</Button>}
        </div>
      </header>

      <section className="grid gap-3 sm:grid-cols-3" aria-label="Resumen de inventario">
        <Metric label="Productos controlados" value={uniqueProducts.length} />
        <Metric label="Alertas de stock" value={alerts} danger={alerts > 0} />
        <Metric label="Unidades comprometidas" value={qty(stock.reduce((sum, row) => sum + Number(row.committed || 0), 0))} />
      </section>

      <div className="flex gap-1 overflow-x-auto rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-1" role="tablist" aria-label="Secciones de inventario">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button key={id} type="button" role="tab" aria-selected={tab === id} onClick={() => setTab(id)} className={`inline-flex min-h-10 shrink-0 items-center gap-2 rounded-xl px-4 text-sm font-bold ${tab === id ? 'bg-[var(--color-primary-soft)] text-[var(--color-primary)]' : 'text-[var(--color-text-muted)] hover:bg-[var(--color-surface-soft)]'}`}>
            <Icon size={15} />{label}
          </button>
        ))}
      </div>

      {tab === 'stock' && (
        <section className="overflow-hidden rounded-3xl border border-[var(--color-border)] bg-[var(--color-surface)]">
          <div className="border-b border-[var(--color-border)] p-4">
            <label className="relative block max-w-md"><Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" size={16} /><span className="sr-only">Buscar existencias</span><input className="input pl-10" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Producto, SKU o almacén" /></label>
          </div>
          {filtered.length === 0 ? <div className="p-8"><EmptyState icon={<PackageCheck size={22} />} title={query ? 'No encontramos productos' : 'Aún no hay productos registrados'} description={query ? 'Prueba con otro nombre, SKU o almacén.' : 'Los productos nuevos aparecerán aquí automáticamente con stock cero.'} /></div> : (
            <>
              <div className="hidden overflow-x-auto md:block"><table className="w-full text-left text-sm"><thead className="bg-[var(--color-surface-soft)] text-[10px] uppercase tracking-wider text-[var(--color-text-muted)]"><tr><th className="px-5 py-3">Producto</th><th className="px-5 py-3">Almacén</th><th className="px-5 py-3 text-right">Actual</th><th className="px-5 py-3 text-right">Comprometido</th><th className="px-5 py-3 text-right">Disponible</th><th className="px-5 py-3">Estado</th>{isAdmin && <th className="px-5 py-3 text-right">Acción</th>}</tr></thead><tbody className="divide-y divide-[var(--color-border)]">{filtered.map((row) => <tr key={`${row.warehouse_id}-${row.product_id}`}><td className="px-5 py-4"><p className="font-bold">{row.product_name}</p><p className="text-xs text-[var(--color-text-muted)]">{row.product_code || 'Sin SKU'} · {row.unit}</p></td><td className="px-5 py-4 text-[var(--color-text-muted)]">{row.warehouse_name}</td><td className="px-5 py-4 text-right font-mono font-bold">{qty(row.on_hand)}</td><td className="px-5 py-4 text-right font-mono">{qty(row.committed)}</td><td className="px-5 py-4 text-right font-mono font-black">{qty(row.available)}</td><td className="px-5 py-4"><StockStatus status={row.status} /></td>{isAdmin && <td className="px-5 py-4 text-right"><button type="button" onClick={() => openStock(row)} className="rounded-xl border border-[var(--color-border)] px-3 py-2 text-xs font-bold text-[var(--color-primary)] hover:bg-[var(--color-primary-soft)]">Registrar stock</button></td>}</tr>)}</tbody></table></div>
              <div className="divide-y divide-[var(--color-border)] md:hidden">{filtered.map((row) => <article key={`${row.warehouse_id}-${row.product_id}`} className="space-y-3 p-4"><div className="flex items-start justify-between gap-3"><div><p className="font-bold">{row.product_name}</p><p className="text-xs text-[var(--color-text-muted)]">{row.warehouse_name} · {row.unit}</p></div><StockStatus status={row.status} /></div><dl className="grid grid-cols-3 gap-2 text-center"><div><dt className="text-[10px] uppercase text-[var(--color-text-muted)]">Actual</dt><dd className="font-mono font-bold">{qty(row.on_hand)}</dd></div><div><dt className="text-[10px] uppercase text-[var(--color-text-muted)]">Comprometido</dt><dd className="font-mono">{qty(row.committed)}</dd></div><div><dt className="text-[10px] uppercase text-[var(--color-text-muted)]">Disponible</dt><dd className="font-mono font-black">{qty(row.available)}</dd></div></dl>{isAdmin && <button type="button" onClick={() => openStock(row)} className="min-h-10 w-full rounded-xl border border-[var(--color-border)] text-sm font-bold text-[var(--color-primary)]">Registrar stock</button>}</article>)}</div>
            </>
          )}
        </section>
      )}

      {tab === 'kardex' && (
        <section className="overflow-hidden rounded-3xl border border-[var(--color-border)] bg-[var(--color-surface)]">
          {movements.length === 0 ? <div className="p-8"><EmptyState icon={<ClipboardList size={22} />} title="El kardex está vacío" description="Aperturas, ventas aceptadas, ajustes y transferencias aparecerán aquí." /></div> : <div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm"><thead className="bg-[var(--color-surface-soft)] text-[10px] uppercase tracking-wider text-[var(--color-text-muted)]"><tr><th className="px-5 py-3">Fecha</th><th className="px-5 py-3">Producto</th><th className="px-5 py-3">Origen</th><th className="px-5 py-3 text-right">Movimiento</th><th className="px-5 py-3 text-right">Saldo</th></tr></thead><tbody className="divide-y divide-[var(--color-border)]">{movements.map((row) => <tr key={row.id}><td className="px-5 py-4 text-[var(--color-text-muted)]">{new Date(row.created_at).toLocaleString('es-PE')}</td><td className="px-5 py-4"><b>{row.product_name}</b><p className="text-xs text-[var(--color-text-muted)]">{row.warehouse_name}</p></td><td className="px-5 py-4"><b>{row.source_document_number || row.reason || row.source_type}</b>{row.source_document_number && <p className="text-xs text-[var(--color-text-muted)]">{row.reason}</p>}</td><td className={`px-5 py-4 text-right font-mono font-black ${Number(row.quantity) >= 0 ? 'text-[var(--color-success)]' : 'text-[var(--color-danger)]'}`}>{Number(row.quantity) >= 0 ? <ArrowUp className="mr-1 inline" size={13} /> : <ArrowDown className="mr-1 inline" size={13} />}{qty(Math.abs(row.quantity))}</td><td className="px-5 py-4 text-right font-mono font-bold">{qty(row.balance_after)}</td></tr>)}</tbody></table></div>}
          {movementTotal > PAGE_SIZE && <div className="border-t border-[var(--color-border)] p-4"><Pagination page={movementPage} totalPages={movementPages} onPageChange={setMovementPage} ariaLabel="Paginación del kardex" /></div>}
        </section>
      )}

      {tab === 'warehouses' && <section className="grid gap-3 md:grid-cols-2">{warehouses.length === 0 ? <EmptyState icon={<Warehouse size={22} />} title="Configura el almacén principal" description="El inventario seguirá desactivado hasta completar este paso." actionLabel={isAdmin ? 'Activar inventario' : undefined} onAction={activate} /> : <>{warehouses.map((row) => <article key={row.id} className="rounded-3xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5"><div className="flex justify-between"><Warehouse className="text-[var(--color-primary)]" />{row.is_default && <span className="rounded-full bg-[var(--color-primary-soft)] px-2 py-1 text-[10px] font-black uppercase text-[var(--color-primary)]">Principal</span>}</div><h2 className="mt-4 font-black">{row.name}</h2><p className="font-mono text-xs text-[var(--color-text-muted)]">{row.code}</p><p className="mt-3 text-sm text-[var(--color-text-muted)]">{row.location || 'Sin ubicación registrada'}</p></article>)}{isAdmin && <button type="button" onClick={() => setModal('warehouse')} className="grid min-h-40 place-items-center rounded-3xl border border-dashed border-[var(--color-border-strong)] bg-[var(--color-surface-soft)] p-5 font-bold text-[var(--color-primary)]"><span className="inline-flex items-center gap-2"><Plus size={17} />Añadir almacén</span></button>}</>}</section>}

      {tab === 'transfers' && <section className="rounded-3xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6"><EmptyState icon={<ArrowLeftRight size={22} />} title="Mueve stock entre almacenes" description="Cada transferencia genera una salida y una entrada enlazadas en el kardex." actionLabel={canOperate && warehouses.length > 1 && stock.length ? 'Nueva transferencia' : undefined} onAction={() => setModal('transfer')} />{warehouses.length < 2 && <p className="mt-3 text-center text-sm text-[var(--color-text-muted)]">Necesitas al menos dos almacenes activos.</p>}</section>}

      {tab === 'returns' && <section className="space-y-3">{returns.length === 0 ? <div className="rounded-3xl border border-[var(--color-border)] bg-[var(--color-surface)] p-8"><EmptyState icon={<RotateCcw size={22} />} title="No hay devoluciones pendientes" description="Las notas de crédito con devolución física aparecerán aquí después de ser aceptadas." /></div> : returns.map((row) => <article key={row.id} className="rounded-3xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5"><div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between"><div><p className="text-xs font-black uppercase tracking-wider text-[var(--color-text-muted)]">Nota de crédito</p><h2 className="mt-1 text-lg font-black">{row.credit_note_number || `Documento #${row.credit_note_id}`}</h2><p className="text-sm text-[var(--color-text-muted)]">{row.items.length} producto(s) · Estado: {row.status}</p></div>{canOperate && row.status !== 'received' && <Button onClick={() => openReceipt(row)}>Confirmar recepción</Button>}</div><div className="mt-4 grid gap-2 sm:grid-cols-2">{row.items.map((item) => <div key={item.id} className="rounded-xl bg-[var(--color-surface-soft)] p-3 text-sm"><b>{item.product_name || `Producto #${item.product_id}`}</b><p className="mt-1 text-[var(--color-text-muted)]">Recibido {qty(item.received_quantity)} de {qty(item.authorized_quantity)}</p></div>)}</div></article>)}</section>}

      <Modal open={modal === 'adjust' || modal === 'stock'} onClose={() => setModal(null)} title={modal === 'stock' ? 'Registrar stock disponible' : 'Registrar movimiento'} subtitle={modal === 'stock' ? 'La cantidad ingresada se sumará al stock actual del producto.' : 'Las cantidades negativas representan salidas manuales.'} icon={Plus} footer={<><Button type="button" variant="secondary" onClick={() => setModal(null)}>Cancelar</Button><Button type="submit" form="adjust-form" loading={saving}>{modal === 'stock' ? 'Guardar stock' : 'Guardar movimiento'}</Button></>}><form id="adjust-form" onSubmit={submitAdjustment} className="space-y-4"><label className="block text-sm font-bold">Almacén<select required disabled={modal === 'stock'} className="input mt-1" value={form.warehouse_id} onChange={(event) => setForm({ ...form, warehouse_id: event.target.value })}><option value="">Selecciona</option>{warehouses.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}</select></label><label className="block text-sm font-bold">Producto<select required disabled={modal === 'stock'} className="input mt-1" value={form.product_id} onChange={(event) => setForm({ ...form, product_id: event.target.value })}><option value="">Selecciona</option>{uniqueProducts.map((row) => <option key={row.product_id} value={row.product_id}>{row.product_name}</option>)}</select></label><label className="block text-sm font-bold">Cantidad a ingresar<input required type="number" min={modal === 'stock' ? '0.0001' : undefined} step="0.0001" className="input mt-1" value={form.quantity} onChange={(event) => setForm({ ...form, quantity: event.target.value })} /></label><label className="block text-sm font-bold">Motivo<textarea required minLength={3} className="input mt-1 min-h-20" value={form.reason} onChange={(event) => setForm({ ...form, reason: event.target.value })} /></label></form></Modal>

      <Modal open={modal === 'warehouse'} onClose={() => setModal(null)} title="Nuevo almacén" subtitle="Crea una ubicación adicional para transferencias." icon={Warehouse} footer={<><Button type="button" variant="secondary" onClick={() => setModal(null)}>Cancelar</Button><Button type="submit" form="warehouse-form" loading={saving}>Crear almacén</Button></>}><form id="warehouse-form" onSubmit={submitWarehouse} className="space-y-4"><label className="block text-sm font-bold">Código<input required maxLength={30} className="input mt-1 uppercase" value={warehouseForm.code} onChange={(event) => setWarehouseForm({ ...warehouseForm, code: event.target.value.toUpperCase() })} placeholder="TIENDA-01" /></label><label className="block text-sm font-bold">Nombre<input required minLength={2} className="input mt-1" value={warehouseForm.name} onChange={(event) => setWarehouseForm({ ...warehouseForm, name: event.target.value })} /></label><label className="block text-sm font-bold">Ubicación<input className="input mt-1" value={warehouseForm.location} onChange={(event) => setWarehouseForm({ ...warehouseForm, location: event.target.value })} /></label><label className="flex items-center gap-2 text-sm font-bold"><input type="checkbox" checked={warehouseForm.is_default} onChange={(event) => setWarehouseForm({ ...warehouseForm, is_default: event.target.checked })} />Usar como almacén principal</label></form></Modal>

      <Modal open={modal === 'config'} onClose={() => setModal(null)} title="Configurar producto" subtitle="Busca cualquier producto del catálogo, incluso si aún no controla stock." icon={PackageCheck} footer={<><Button type="button" variant="secondary" onClick={() => setModal(null)}>Cancelar</Button><Button type="submit" form="config-form" loading={saving}>Guardar configuración</Button></>}><form id="config-form" onSubmit={submitConfig} className="space-y-4"><label className="block text-sm font-bold">Buscar producto<input className="input mt-1" value={productQuery} onChange={(event) => setProductQuery(event.target.value)} placeholder="Escribe nombre o SKU" /></label><label className="block text-sm font-bold">Producto<select required className="input mt-1" value={config.product_id} onChange={(event) => setConfig({ ...config, product_id: event.target.value })}><option value="">Selecciona un resultado</option>{productOptions.map((product) => <option key={product.id} value={product.id}>{product.nombre}{product.codigo_interno ? ` · ${product.codigo_interno}` : ''}</option>)}</select></label><label className="block text-sm font-bold">Tipo<select className="input mt-1" value={config.item_type} onChange={(event) => setConfig({ ...config, item_type: event.target.value })}><option value="inventory">Producto inventariable</option><option value="service">Servicio sin stock</option></select></label>{config.item_type === 'inventory' && <><label className="block text-sm font-bold">Almacén<select required className="input mt-1" value={config.warehouse_id} onChange={(event) => setConfig({ ...config, warehouse_id: event.target.value })}><option value="">Selecciona</option>{warehouses.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}</select></label><div className="grid grid-cols-2 gap-3"><label className="block text-sm font-bold">Saldo inicial<input type="number" step="0.0001" className="input mt-1" value={config.opening_stock} onChange={(event) => setConfig({ ...config, opening_stock: event.target.value })} /></label><label className="block text-sm font-bold">Stock mínimo<input type="number" min="0" step="0.0001" className="input mt-1" value={config.minimum_stock} onChange={(event) => setConfig({ ...config, minimum_stock: event.target.value })} /></label></div></>}</form></Modal>

      <Modal open={modal === 'transfer'} onClose={() => setModal(null)} title="Nueva transferencia" subtitle="El movimiento queda registrado en ambos almacenes." icon={ArrowLeftRight} footer={<><Button type="button" variant="secondary" onClick={() => setModal(null)}>Cancelar</Button><Button type="submit" form="transfer-form" loading={saving}>Registrar transferencia</Button></>}><form id="transfer-form" onSubmit={submitTransfer} className="space-y-4"><div className="grid gap-3 sm:grid-cols-2"><label className="block text-sm font-bold">Origen<select required className="input mt-1" value={transfer.source_warehouse_id} onChange={(event) => setTransfer({ ...transfer, source_warehouse_id: event.target.value })}><option value="">Selecciona</option>{warehouses.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}</select></label><label className="block text-sm font-bold">Destino<select required className="input mt-1" value={transfer.destination_warehouse_id} onChange={(event) => setTransfer({ ...transfer, destination_warehouse_id: event.target.value })}><option value="">Selecciona</option>{warehouses.filter((row) => String(row.id) !== String(transfer.source_warehouse_id)).map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}</select></label></div><label className="block text-sm font-bold">Producto<select required className="input mt-1" value={transfer.product_id} onChange={(event) => setTransfer({ ...transfer, product_id: event.target.value })}><option value="">Selecciona</option>{uniqueProducts.map((row) => <option key={row.product_id} value={row.product_id}>{row.product_name}</option>)}</select></label><label className="block text-sm font-bold">Cantidad<input required type="number" min="0.0001" step="0.0001" className="input mt-1" value={transfer.quantity} onChange={(event) => setTransfer({ ...transfer, quantity: event.target.value })} /></label><label className="block text-sm font-bold">Motivo<textarea required minLength={3} className="input mt-1 min-h-20" value={transfer.reason} onChange={(event) => setTransfer({ ...transfer, reason: event.target.value })} /></label></form></Modal>

      <Modal open={modal === 'receipt' && Boolean(selectedReturn)} onClose={() => { setModal(null); setSelectedReturn(null); }} title="Confirmar recepción física" subtitle={selectedReturn?.credit_note_number || 'Devolución autorizada'} icon={RotateCcw} footer={<><Button type="button" variant="secondary" onClick={() => setModal(null)}>Cancelar</Button><Button type="submit" form="receipt-form" loading={saving} disabled={!Object.values(receipt).some((value) => Number(value) > 0)}>Ingresar al stock</Button></>}><form id="receipt-form" onSubmit={submitReceipt} className="space-y-3">{selectedReturn?.items.map((item) => { const remaining = Number(item.authorized_quantity) - Number(item.received_quantity); return <label key={item.id} className="block rounded-xl border border-[var(--color-border)] p-3 text-sm font-bold">{item.product_name || `Producto #${item.product_id}`}<span className="mt-1 block text-xs font-normal text-[var(--color-text-muted)]">Pendiente: {qty(remaining)}</span><input type="number" min="0" max={remaining} step="0.0001" className="input mt-2" value={receipt[item.id] || ''} onChange={(event) => setReceipt({ ...receipt, [item.id]: event.target.value })} /></label>; })}</form></Modal>
    </main>
  );
}
