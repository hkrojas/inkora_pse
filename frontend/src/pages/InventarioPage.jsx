import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle, ArrowDown, ArrowLeftRight, ArrowUp, Boxes, ClipboardList,
  MapPin, PackageCheck, PackageMinus, Plus, RefreshCw, RotateCcw, Search, Warehouse,
} from 'lucide-react';
import Button from '../components/ui/Button';
import CustomSelect from '../components/ui/CustomSelect';
import Drawer from '../components/ui/Drawer';
import EmptyState from '../components/ui/EmptyState';
import OperationalPageHeader from '../components/ui/OperationalPageHeader';
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
const labels = { ok: 'Disponible', low: 'Stock bajo', out: 'Sin existencias', negative: 'Stock negativo' };
const qty = (value) => Number(value || 0).toLocaleString('es-PE', { maximumFractionDigits: 4 });

function Metric({ label, value, description, icon: Icon, tone = 'neutral' }) {
  return (
    <article className={`inventory-metric inventory-metric--${tone}`}>
      <div className="inventory-metric__head">
        <p>{label}</p>
        <span className="inventory-metric__icon" aria-hidden="true"><Icon size={16} /></span>
      </div>
      <p className="inventory-metric__value">{value}</p>
      <p className="inventory-metric__description">{description}</p>
    </article>
  );
}

function StockStatus({ status }) {
  const tones = {
    ok: 'inventory-status--ok',
    low: 'inventory-status--warning',
    out: 'inventory-status--empty',
    negative: 'inventory-status--danger',
  };
  return (
    <span className={`inventory-status ${tones[status] || 'inventory-status--empty'}`}>
      <span className="inventory-status__dot" aria-hidden="true" />
      {labels[status] || status}
    </span>
  );
}

function PanelHeading({ eyebrow, title, description, meta }) {
  return (
    <div className="inventory-panel__header">
      <div>
        <p className="inventory-panel__eyebrow">{eyebrow}</p>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
      {meta && <span className="inventory-panel__result-count">{meta}</span>}
    </div>
  );
}

function MovementDirection({ quantity }) {
  const amount = Number(quantity || 0);
  const isEntry = amount >= 0;
  return (
    <span className={`inventory-movement-badge inventory-movement-badge--${isEntry ? 'entry' : 'exit'}`}>
      {isEntry ? <ArrowUp size={13} /> : <ArrowDown size={13} />}
      <span>{isEntry ? 'Entrada' : 'Salida'}</span>
      <strong>{isEntry ? '+' : '−'}{qty(Math.abs(amount))}</strong>
    </span>
  );
}

function MovementDate({ value }) {
  const date = new Date(value);
  return (
    <div className="inventory-movement-date">
      <strong>{date.toLocaleDateString('es-PE', { day: '2-digit', month: 'short', year: 'numeric' })}</strong>
      <span>{date.toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit' })}</span>
    </div>
  );
}

export default function InventarioPage() {
  const { user } = useAuth();
  const toast = useToast();
  const isAdmin = user?.is_superadmin || user?.rol === 'admin';
  const canOperate = isAdmin || user?.rol === 'operador';
  const [tab, setTab] = useState('stock');
  const [stockPage, setStockPage] = useState(1);
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
  const [productSearchLoading, setProductSearchLoading] = useState(false);
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
    const searchTerm = productQuery.trim();
    if (searchTerm.length < 2) {
      setProductOptions([]);
      setProductSearchLoading(false);
      return undefined;
    }

    let active = true;
    const controller = new AbortController();
    setProductSearchLoading(true);
    const timer = window.setTimeout(() => {
      productos.search(searchTerm, 20, { signal: controller.signal })
        .then((rows) => { if (active) setProductOptions(rows); })
        .catch((requestError) => {
          if (active && !requestError?.isCanceled) setProductOptions([]);
        })
        .finally(() => { if (active) setProductSearchLoading(false); });
    }, 250);
    return () => {
      active = false;
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [productQuery]);

  const filtered = useMemo(() => {
    const term = query.trim().toLowerCase();
    return term
      ? stock.filter((row) => `${row.product_name} ${row.product_code || ''} ${row.warehouse_name}`.toLowerCase().includes(term))
      : stock;
  }, [query, stock]);
  const stockPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const paginatedStock = useMemo(() => {
    const start = (stockPage - 1) * PAGE_SIZE;
    return filtered.slice(start, start + PAGE_SIZE);
  }, [filtered, stockPage]);
  const uniqueProducts = useMemo(() => [...new Map(stock.map((row) => [row.product_id, row])).values()], [stock]);
  const outOfStock = stock.filter((row) => row.status === 'out').length;
  const criticalAlerts = stock.filter((row) => ['low', 'negative'].includes(row.status)).length;
  const committedTotal = stock.reduce((sum, row) => sum + Number(row.committed || 0), 0);
  const availableTotal = stock.reduce((sum, row) => sum + Number(row.available || 0), 0);
  const selectedStockRow = stock.find((row) => String(row.warehouse_id) === String(form.warehouse_id)
    && String(row.product_id) === String(form.product_id));
  const projectedStock = Number(selectedStockRow?.on_hand || 0) + Number(form.quantity || 0);
  const movementPages = Math.max(1, Math.ceil(movementTotal / PAGE_SIZE));
  const tabCounts = {
    stock: stock.length,
    kardex: movementTotal,
    warehouses: warehouses.length,
    transfers: null,
    returns: returns.length,
  };

  useEffect(() => { setStockPage(1); }, [query]);
  useEffect(() => {
    if (stockPage > stockPages) setStockPage(stockPages);
  }, [stockPage, stockPages]);

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
    if (!form.warehouse_id || !form.product_id) {
      toast('Selecciona un almacén y un producto.', 'error');
      return;
    }
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
    if (!config.product_id || (config.item_type === 'inventory' && !config.warehouse_id)) {
      toast('Selecciona el producto y su almacén.', 'error');
      return;
    }
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
    if (!transfer.source_warehouse_id || !transfer.destination_warehouse_id || !transfer.product_id) {
      toast('Completa el origen, destino y producto de la transferencia.', 'error');
      return;
    }
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
    <main className="inventory-page mx-auto w-full max-w-[1500px] space-y-5 pb-10">
      <OperationalPageHeader
        eyebrow="Control operativo"
        title="Inventario"
        description="Supervisa existencias por almacén y conserva la trazabilidad de cada entrada, salida y devolución."
        variant="monitoring"
        meta={<span className="operational-page-header__scope">Stock disponible · Kardex · Almacenes</span>}
        actions={<>
          <Button variant="secondary" onClick={load}><RefreshCw size={15} />Actualizar</Button>
          {isAdmin && warehouses.length > 0 && <Button variant="secondary" onClick={() => setModal('config')}><PackageCheck size={15} />Configurar producto</Button>}
          {canOperate && stock.length > 0 && <Button onClick={openAdjustment}><Plus size={15} />Registrar movimiento</Button>}
        </>}
      />

      <section className="inventory-metrics" aria-label="Resumen de inventario">
        <Metric label="Productos controlados" value={uniqueProducts.length} description="Ítems con seguimiento activo" icon={Boxes} tone="primary" />
        <Metric label="Sin existencias" value={outOfStock} description="Pendientes de entrada de stock" icon={PackageMinus} tone={outOfStock ? 'warning' : 'neutral'} />
        <Metric label="Alertas críticas" value={criticalAlerts} description="Stock bajo o negativo" icon={AlertTriangle} tone={criticalAlerts ? 'danger' : 'success'} />
        <Metric label="Stock disponible" value={qty(availableTotal)} description={`${qty(committedTotal)} unidades comprometidas`} icon={PackageCheck} tone="success" />
      </section>

      {outOfStock > 0 && tab === 'stock' && !query && (
        <section className="inventory-attention" aria-label="Productos sin existencias">
          <span className="inventory-attention__icon" aria-hidden="true"><PackageMinus size={19} /></span>
          <div className="inventory-attention__copy">
            <strong>{outOfStock} productos aún no tienen existencias registradas</strong>
            <p>Puedes cargar cada producto desde la lista o registrar una entrada general para comenzar el control.</p>
          </div>
          {canOperate && <Button size="sm" variant="soft" onClick={openAdjustment}><Plus size={14} />Registrar entrada</Button>}
        </section>
      )}

      <div className="inventory-tabs" role="tablist" aria-label="Secciones de inventario">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button key={id} type="button" role="tab" aria-selected={tab === id} onClick={() => setTab(id)} className="inventory-tab">
            <Icon size={15} /><span>{label}</span>{tabCounts[id] !== null && <span className="inventory-tab__count">{tabCounts[id]}</span>}
          </button>
        ))}
      </div>

      {tab === 'stock' && (
        <section className="inventory-panel">
          <div className="inventory-panel__header">
            <div>
              <p className="inventory-panel__eyebrow">Existencias por almacén</p>
              <h2>Stock disponible y comprometido</h2>
              <p>Consulta el saldo operativo de cada producto y registra entradas sin salir de la lista.</p>
            </div>
            <span className="inventory-panel__result-count">{filtered.length} {filtered.length === 1 ? 'registro' : 'registros'}</span>
          </div>
          <div className="inventory-toolbar">
            <label className="inventory-search"><Search size={16} /><span className="sr-only">Buscar existencias</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar producto, SKU o almacén" /></label>
            <p><span aria-hidden="true" /> El stock disponible descuenta las unidades comprometidas.</p>
          </div>
          {filtered.length === 0 ? <div className="p-8"><EmptyState icon={<PackageCheck size={22} />} title={query ? 'No encontramos productos' : 'Aún no hay productos registrados'} description={query ? 'Prueba con otro nombre, SKU o almacén.' : 'Los productos nuevos aparecerán aquí automáticamente con stock cero.'} /></div> : (
            <>
              <div className="inventory-table-wrap">
                <table className="inventory-table">
                  <thead><tr><th>Producto</th><th>Almacén</th><th className="is-number">Actual</th><th className="is-number">Comprometido</th><th className="is-number">Disponible</th><th>Estado</th>{isAdmin && <th className="is-action">Acción</th>}</tr></thead>
                  <tbody>{paginatedStock.map((row) => (
                    <tr key={`${row.warehouse_id}-${row.product_id}`} className={`inventory-stock-row inventory-stock-row--${row.status}`}>
                      <td><div className="inventory-product-cell"><span className="inventory-product-cell__icon" aria-hidden="true"><Boxes size={15} /></span><div><p>{row.product_name}</p><span>{row.product_code || 'Sin SKU'} · {row.unit}</span></div></div></td>
                      <td><span className="inventory-warehouse-name"><Warehouse size={14} />{row.warehouse_name}</span></td>
                      <td className="is-number"><strong>{qty(row.on_hand)}</strong></td>
                      <td className="is-number">{qty(row.committed)}</td>
                      <td className="is-number is-available"><span className="inventory-balance-chip"><strong>{qty(row.available)}</strong><small>{row.unit}</small></span></td>
                      <td><div className="inventory-status-cell"><StockStatus status={row.status} /><small>Mín. {qty(row.minimum_stock)}</small></div></td>
                      {isAdmin && <td className="is-action"><button type="button" onClick={() => openStock(row)} className="inventory-stock-action"><Plus size={13} />Registrar stock</button></td>}
                    </tr>
                  ))}</tbody>
                </table>
              </div>
              <div className="inventory-mobile-list">{paginatedStock.map((row) => (
                <article key={`${row.warehouse_id}-${row.product_id}`} className="inventory-stock-card">
                  <div className="inventory-stock-card__head"><div><p>{row.product_name}</p><span>{row.product_code || 'Sin SKU'} · {row.unit}</span></div><StockStatus status={row.status} /></div>
                  <p className="inventory-stock-card__warehouse"><Warehouse size={14} />{row.warehouse_name}</p>
                  <dl><div><dt>Actual</dt><dd>{qty(row.on_hand)}</dd></div><div><dt>Comprometido</dt><dd>{qty(row.committed)}</dd></div><div><dt>Disponible</dt><dd>{qty(row.available)}</dd></div></dl>
                  <div className="inventory-stock-card__foot"><span>Stock mínimo: {qty(row.minimum_stock)}</span>{isAdmin && <button type="button" onClick={() => openStock(row)}><Plus size={13} />Registrar stock</button>}</div>
                </article>
              ))}</div>
              <div className="inventory-list-footer">
                <span>Mostrando <strong>{paginatedStock.length}</strong> de <strong>{filtered.length}</strong> registros</span>
                <Pagination page={stockPage} totalPages={stockPages} onPageChange={setStockPage} ariaLabel="Paginación de existencias" />
              </div>
            </>
          )}
        </section>
      )}

      {tab === 'kardex' && (
        <section className="inventory-panel">
          <PanelHeading eyebrow="Trazabilidad" title="Kardex de movimientos" description="Cada entrada y salida conserva su documento o motivo de origen y el saldo resultante." meta={`${movementTotal} movimientos`} />
          {movements.length === 0 ? <div className="p-8"><EmptyState icon={<ClipboardList size={22} />} title="El kardex está vacío" description="Aperturas, ventas aceptadas, ajustes y transferencias aparecerán aquí." /></div> : <>
            <div className="inventory-kardex-table-wrap">
              <table className="inventory-table inventory-kardex-table">
                <thead><tr><th>Fecha</th><th>Producto y almacén</th><th>Documento o motivo</th><th>Movimiento</th><th className="is-number">Saldo resultante</th></tr></thead>
                <tbody>{movements.map((row) => (
                  <tr key={row.id} className={Number(row.quantity) >= 0 ? 'is-entry' : 'is-exit'}>
                    <td><MovementDate value={row.created_at} /></td>
                    <td><div className="inventory-product-cell"><span className="inventory-product-cell__icon" aria-hidden="true"><Boxes size={15} /></span><div><p>{row.product_name}</p><span><Warehouse size={11} />{row.warehouse_name}</span></div></div></td>
                    <td><div className="inventory-origin-cell"><span>{row.source_type || 'Movimiento manual'}</span><strong>{row.source_document_number || row.reason || 'Sin referencia'}</strong>{row.source_document_number && row.reason && <small>{row.reason}</small>}</div></td>
                    <td><MovementDirection quantity={row.quantity} /></td>
                    <td className="is-number"><span className="inventory-ledger-balance"><small>Nuevo saldo</small><strong>{qty(row.balance_after)}</strong></span></td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
            <div className="inventory-kardex-mobile">{movements.map((row) => (
              <article key={row.id} className={`inventory-movement-card ${Number(row.quantity) >= 0 ? 'is-entry' : 'is-exit'}`}>
                <div className="inventory-movement-card__top"><MovementDate value={row.created_at} /><MovementDirection quantity={row.quantity} /></div>
                <div className="inventory-movement-card__product"><span aria-hidden="true"><Boxes size={15} /></span><div><strong>{row.product_name}</strong><small><Warehouse size={11} />{row.warehouse_name}</small></div></div>
                <div className="inventory-movement-card__origin"><span>{row.source_type || 'Movimiento manual'}</span><strong>{row.source_document_number || row.reason || 'Sin referencia'}</strong>{row.source_document_number && row.reason && <small>{row.reason}</small>}</div>
                <div className="inventory-movement-card__balance"><span>Saldo después del movimiento</span><strong>{qty(row.balance_after)}</strong></div>
              </article>
            ))}</div>
          </>}
          {movementTotal > PAGE_SIZE && <div className="inventory-list-footer inventory-list-footer--kardex"><span>Página <strong>{movementPage}</strong> de <strong>{movementPages}</strong></span><Pagination page={movementPage} totalPages={movementPages} onPageChange={setMovementPage} ariaLabel="Paginación del kardex" /></div>}
        </section>
      )}

      {tab === 'warehouses' && <section className="inventory-panel"><PanelHeading eyebrow="Ubicaciones" title="Almacenes activos" description="Organiza el stock por sede y prepara transferencias entre ubicaciones." meta={`${warehouses.length} almacenes`} /><div className="inventory-warehouse-grid">{warehouses.length === 0 ? <EmptyState icon={<Warehouse size={22} />} title="Configura el almacén principal" description="El inventario seguirá desactivado hasta completar este paso." actionLabel={isAdmin ? 'Activar inventario' : undefined} onAction={activate} /> : <>{warehouses.map((row) => <article key={row.id} className={`inventory-warehouse-card ${row.is_default ? 'is-primary' : ''}`}><div className="inventory-warehouse-card__top"><span className="inventory-warehouse-card__icon"><Warehouse size={18} /></span>{row.is_default ? <span className="inventory-warehouse-card__badge">Almacén principal</span> : <span className="inventory-warehouse-card__badge inventory-warehouse-card__badge--secondary">Sede adicional</span>}</div><div className="inventory-warehouse-card__identity"><span>{row.code}</span><h3>{row.name}</h3></div><div className="inventory-warehouse-card__location"><MapPin size={14} /><span>{row.location || 'Ubicación pendiente de registrar'}</span></div><div className="inventory-warehouse-card__foot"><span><span aria-hidden="true" />Disponible para movimientos</span><small>ID {row.id}</small></div></article>)}{isAdmin && <button type="button" onClick={() => setModal('warehouse')} className="inventory-add-warehouse"><span className="inventory-add-warehouse__icon"><Plus size={18} /></span><strong>Añadir almacén</strong><small>Crea otra ubicación para distribuir existencias.</small></button>}</>}</div></section>}

      {tab === 'transfers' && <section className="inventory-panel"><PanelHeading eyebrow="Movimiento interno" title="Transferencias entre almacenes" description="Mueve existencias sin perder la trazabilidad del almacén de origen y destino." /><div className="inventory-transfer-empty"><div className="inventory-transfer-route" aria-hidden="true"><span><Warehouse size={18} /></span><i /><span><ArrowLeftRight size={18} /></span><i /><span><Warehouse size={18} /></span></div><EmptyState icon={<ArrowLeftRight size={22} />} title="Mueve stock entre almacenes" description="Cada transferencia genera una salida y una entrada enlazadas en el kardex." actionLabel={canOperate && warehouses.length > 1 && stock.length ? 'Nueva transferencia' : undefined} onAction={() => setModal('transfer')} />{warehouses.length < 2 && <p>Necesitas al menos dos almacenes activos.</p>}</div></section>}

      {tab === 'returns' && <section className="inventory-panel"><PanelHeading eyebrow="Ingreso por devolución" title="Recepciones pendientes" description="Confirma únicamente las unidades que regresaron físicamente al almacén." meta={`${returns.length} pendientes`} /><div className="inventory-return-list">{returns.length === 0 ? <div className="p-4"><EmptyState icon={<RotateCcw size={22} />} title="No hay devoluciones pendientes" description="Las notas de crédito con devolución física aparecerán aquí después de ser aceptadas." /></div> : returns.map((row) => <article key={row.id} className="inventory-return-card"><div className="inventory-return-card__head"><div><p className="inventory-panel__eyebrow">Nota de crédito</p><h3>{row.credit_note_number || `Documento #${row.credit_note_id}`}</h3><span>{row.items.length} {row.items.length === 1 ? 'producto autorizado' : 'productos autorizados'}</span></div><div className="inventory-return-card__actions"><span className="inventory-return-status"><span aria-hidden="true" />{row.status === 'received' ? 'Recibida' : 'Pendiente de recepción'}</span>{canOperate && row.status !== 'received' && <Button onClick={() => openReceipt(row)}>Confirmar recepción</Button>}</div></div><div className="inventory-return-items">{row.items.map((item) => { const authorized = Number(item.authorized_quantity || 0); const received = Number(item.received_quantity || 0); const progress = authorized > 0 ? Math.min(100, (received / authorized) * 100) : 0; return <div key={item.id} className="inventory-return-item"><div><span className="inventory-return-item__icon" aria-hidden="true"><Boxes size={14} /></span><div><strong>{item.product_name || `Producto #${item.product_id}`}</strong><small>Recibido {qty(received)} de {qty(authorized)}</small></div></div><div className="inventory-return-progress" aria-label={`${Math.round(progress)}% recibido`}><span style={{ width: `${progress}%` }} /></div><b>{qty(Math.max(authorized - received, 0))} pendiente</b></div>; })}</div></article>)}</div></section>}

      <Drawer
        open={modal === 'stock'}
        onClose={() => setModal(null)}
        variant="inventory-stock"
        tone="primary"
        eyebrow="Entrada de inventario"
        status="Suma al stock"
        initialFocus="#inventory-stock-quantity"
        title="Agregar existencias"
        subtitle={selectedStockRow ? `${selectedStockRow.product_name} · ${selectedStockRow.warehouse_name}` : 'Registra una entrada para el producto seleccionado.'}
        icon={<PackageCheck size={20} />}
        footer={<><button type="button" className="btn-ghost" onClick={() => setModal(null)}>Cancelar</button><button type="submit" form="inventory-stock-form" className="btn-primary" disabled={saving || Number(form.quantity) <= 0}>{saving ? 'Guardando…' : 'Agregar al stock'}</button></>}
      >
        {selectedStockRow && (
          <form id="inventory-stock-form" className="inventory-stock-drawer" onSubmit={submitAdjustment}>
            <section className="inventory-stock-drawer__product" aria-labelledby="inventory-stock-product-title">
              <div className="inventory-stock-drawer__product-topline"><span>Producto seleccionado</span><StockStatus status={selectedStockRow.status} /></div>
              <div className="inventory-stock-drawer__product-main">
                <span className="inventory-stock-drawer__product-icon" aria-hidden="true"><Boxes size={19} /></span>
                <div><h3 id="inventory-stock-product-title">{selectedStockRow.product_name}</h3><p>{selectedStockRow.product_code || 'Sin SKU'} · {selectedStockRow.unit}</p></div>
              </div>
              <div className="inventory-stock-drawer__warehouse"><Warehouse size={15} aria-hidden="true" /><div><span>Almacén de destino</span><strong>{selectedStockRow.warehouse_name}</strong></div></div>
            </section>

            <section className="inventory-stock-drawer__balance" aria-labelledby="inventory-stock-balance-title">
              <div className="inventory-stock-drawer__section-heading"><div><p className="inventory-panel__eyebrow">Actualización de saldo</p><h3 id="inventory-stock-balance-title">Cantidad que ingresa</h3></div><span>Solo suma</span></div>
              <label htmlFor="inventory-stock-quantity">Unidades a agregar</label>
              <div className="inventory-stock-drawer__quantity"><Plus size={18} aria-hidden="true" /><input id="inventory-stock-quantity" required type="number" min="0.0001" step="0.0001" inputMode="decimal" value={form.quantity} onChange={(event) => setForm({ ...form, quantity: event.target.value })} placeholder="0" /><span>{selectedStockRow.unit}</span></div>
              <dl className="inventory-stock-drawer__projection"><div><dt>Stock actual</dt><dd>{qty(selectedStockRow.on_hand)}</dd></div><div><dt>Después del ingreso</dt><dd>{qty(projectedStock)}</dd></div></dl>
            </section>

            <section className="inventory-stock-drawer__reason" aria-labelledby="inventory-stock-reason-title">
              <div className="inventory-stock-drawer__section-heading"><div><p className="inventory-panel__eyebrow">Trazabilidad</p><h3 id="inventory-stock-reason-title">Motivo del ingreso</h3></div></div>
              <label htmlFor="inventory-stock-reason" className="sr-only">Motivo del ingreso</label>
              <textarea id="inventory-stock-reason" required minLength={3} value={form.reason} onChange={(event) => setForm({ ...form, reason: event.target.value })} placeholder="Describe el origen de estas existencias" />
              <p>Este texto aparecerá en el kardex para identificar el movimiento.</p>
            </section>

            <p className="inventory-stock-drawer__notice"><ClipboardList size={15} aria-hidden="true" />La entrada quedará registrada en el kardex y no reemplazará el saldo existente.</p>
          </form>
        )}
      </Drawer>

      <Drawer open={modal === 'adjust'} onClose={() => setModal(null)} variant="inventory-action" eyebrow="Kardex manual" status="Entrada o salida" initialFocus=".ink-select-trigger" title="Registrar movimiento" subtitle="Ajusta existencias con un motivo que quedará visible en el kardex." icon={<Plus size={20} />} footer={<><button type="button" className="btn-ghost" onClick={() => setModal(null)}>Cancelar</button><button type="submit" form="adjust-form" className="btn-primary" disabled={saving}>{saving ? 'Guardando…' : 'Guardar movimiento'}</button></>}>
        <form id="adjust-form" onSubmit={submitAdjustment} className="inventory-action-form">
          <section className="inventory-form-section"><div className="inventory-form-section__heading"><span>01</span><div><h3>Destino del movimiento</h3><p>Selecciona dónde y sobre qué producto se aplicará.</p></div></div><label>Almacén<CustomSelect required ariaLabel="Almacén" value={form.warehouse_id} onChange={(value) => setForm({ ...form, warehouse_id: value })} placeholder="Selecciona un almacén" options={warehouses.map((row) => ({ value: row.id, label: row.name }))} /></label><label>Producto<CustomSelect required searchable searchPlaceholder="Buscar producto o SKU" ariaLabel="Producto" value={form.product_id} onChange={(value) => setForm({ ...form, product_id: value })} placeholder="Selecciona un producto" options={uniqueProducts.map((row) => ({ value: row.product_id, label: row.product_name, searchText: `${row.product_name} ${row.product_code || ''}` }))} /></label></section>
          <section className="inventory-form-section"><div className="inventory-form-section__heading"><span>02</span><div><h3>Cantidad y sustento</h3><p>Usa valores negativos únicamente para registrar una salida.</p></div></div><label>Cantidad<input required type="number" step="0.0001" className="input mt-1" value={form.quantity} onChange={(event) => setForm({ ...form, quantity: event.target.value })} placeholder="Ej. 25 o -5" /></label><label>Motivo<textarea required minLength={3} className="input mt-1 min-h-24" value={form.reason} onChange={(event) => setForm({ ...form, reason: event.target.value })} placeholder="Describe el origen del ajuste" /></label></section>
        </form>
      </Drawer>

      <Drawer open={modal === 'warehouse'} onClose={() => setModal(null)} variant="inventory-action" eyebrow="Red de almacenes" status="Nueva ubicación" initialFocus="input" title="Crear almacén" subtitle="Añade una ubicación para organizar stock y realizar transferencias." icon={<Warehouse size={20} />} footer={<><button type="button" className="btn-ghost" onClick={() => setModal(null)}>Cancelar</button><button type="submit" form="warehouse-form" className="btn-primary" disabled={saving}>{saving ? 'Creando…' : 'Crear almacén'}</button></>}>
        <form id="warehouse-form" onSubmit={submitWarehouse} className="inventory-action-form"><section className="inventory-form-section"><div className="inventory-form-section__heading"><span>01</span><div><h3>Identificación</h3><p>Usa un código corto que permita reconocer esta ubicación.</p></div></div><label>Código<input required maxLength={30} className="input mt-1 uppercase" value={warehouseForm.code} onChange={(event) => setWarehouseForm({ ...warehouseForm, code: event.target.value.toUpperCase() })} placeholder="TIENDA-01" /></label><label>Nombre<input required minLength={2} className="input mt-1" value={warehouseForm.name} onChange={(event) => setWarehouseForm({ ...warehouseForm, name: event.target.value })} placeholder="Tienda principal" /></label><label>Ubicación <small>(opcional)</small><input className="input mt-1" value={warehouseForm.location} onChange={(event) => setWarehouseForm({ ...warehouseForm, location: event.target.value })} placeholder="Dirección o referencia" /></label></section><label className="inventory-drawer-check"><input type="checkbox" checked={warehouseForm.is_default} onChange={(event) => setWarehouseForm({ ...warehouseForm, is_default: event.target.checked })} /><span><strong>Usar como almacén principal</strong><small>Será la ubicación sugerida en nuevas operaciones.</small></span></label></form>
      </Drawer>

      <Drawer open={modal === 'config'} onClose={() => setModal(null)} variant="inventory-action" eyebrow="Catálogo comercial" status="Control de stock" initialFocus=".ink-select-trigger" title="Configurar producto" subtitle="Define cómo se comporta un producto dentro del inventario." icon={<PackageCheck size={20} />} footer={<><button type="button" className="btn-ghost" onClick={() => setModal(null)}>Cancelar</button><button type="submit" form="config-form" className="btn-primary" disabled={saving}>{saving ? 'Guardando…' : 'Guardar configuración'}</button></>}>
        <form id="config-form" onSubmit={submitConfig} className="inventory-action-form"><section className="inventory-form-section"><div className="inventory-form-section__heading"><span>01</span><div><h3>Producto del catálogo</h3><p>Escribe en el selector y el catálogo se actualizará mientras buscas.</p></div></div><label>Producto<CustomSelect required searchable loading={productSearchLoading} onSearchChange={setProductQuery} searchPlaceholder="Buscar por nombre o SKU" ariaLabel="Buscar producto del catálogo" value={config.product_id} onChange={(value) => setConfig({ ...config, product_id: value })} placeholder="Busca y selecciona un producto" noResultsLabel={productQuery.trim().length < 2 ? 'Escribe al menos 2 caracteres para buscar.' : 'No encontramos productos con esa búsqueda.'} options={productOptions.map((product) => ({ value: product.id, label: `${product.nombre}${product.codigo_interno ? ` · ${product.codigo_interno}` : ''}`, searchText: `${product.nombre} ${product.codigo_interno || ''}` }))} /></label><p className="inventory-product-search-help">La búsqueda consulta el catálogo en tiempo real y muestra hasta 20 coincidencias.</p></section><section className="inventory-form-section"><div className="inventory-form-section__heading"><span>02</span><div><h3>Reglas de inventario</h3><p>Los servicios no generan ni consumen existencias.</p></div></div><label>Tipo<CustomSelect ariaLabel="Tipo de producto" value={config.item_type} onChange={(value) => setConfig({ ...config, item_type: value })} options={[{ value: 'inventory', label: 'Producto inventariable' }, { value: 'service', label: 'Servicio sin stock' }]} /></label>{config.item_type === 'inventory' && <><label>Almacén<CustomSelect required ariaLabel="Almacén del producto" value={config.warehouse_id} onChange={(value) => setConfig({ ...config, warehouse_id: value })} placeholder="Selecciona un almacén" options={warehouses.map((row) => ({ value: row.id, label: row.name }))} /></label><div className="inventory-form-grid"><label>Saldo inicial<input type="number" step="0.0001" className="input mt-1" value={config.opening_stock} onChange={(event) => setConfig({ ...config, opening_stock: event.target.value })} /></label><label>Stock mínimo<input type="number" min="0" step="0.0001" className="input mt-1" value={config.minimum_stock} onChange={(event) => setConfig({ ...config, minimum_stock: event.target.value })} /></label></div></>}</section></form>
      </Drawer>

      <Drawer open={modal === 'transfer'} onClose={() => setModal(null)} variant="inventory-action" tone="warning" eyebrow="Movimiento interno" status="Entre almacenes" initialFocus=".ink-select-trigger" title="Nueva transferencia" subtitle="La salida y la entrada quedarán enlazadas en el kardex." icon={<ArrowLeftRight size={20} />} footer={<><button type="button" className="btn-ghost" onClick={() => setModal(null)}>Cancelar</button><button type="submit" form="transfer-form" className="btn-primary" disabled={saving}>{saving ? 'Registrando…' : 'Registrar transferencia'}</button></>}>
        <form id="transfer-form" onSubmit={submitTransfer} className="inventory-action-form"><section className="inventory-form-section"><div className="inventory-form-section__heading"><span>01</span><div><h3>Ruta del stock</h3><p>El almacén de destino debe ser diferente al de origen.</p></div></div><div className="inventory-form-grid"><label>Origen<CustomSelect required ariaLabel="Almacén de origen" value={transfer.source_warehouse_id} onChange={(value) => setTransfer({ ...transfer, source_warehouse_id: value })} placeholder="Selecciona" options={warehouses.map((row) => ({ value: row.id, label: row.name }))} /></label><label>Destino<CustomSelect required ariaLabel="Almacén de destino" value={transfer.destination_warehouse_id} onChange={(value) => setTransfer({ ...transfer, destination_warehouse_id: value })} placeholder="Selecciona" options={warehouses.filter((row) => String(row.id) !== String(transfer.source_warehouse_id)).map((row) => ({ value: row.id, label: row.name }))} /></label></div></section><section className="inventory-form-section"><div className="inventory-form-section__heading"><span>02</span><div><h3>Detalle del traslado</h3><p>Indica qué producto y cuántas unidades se moverán.</p></div></div><label>Producto<CustomSelect required searchable searchPlaceholder="Buscar producto o SKU" ariaLabel="Producto a transferir" value={transfer.product_id} onChange={(value) => setTransfer({ ...transfer, product_id: value })} placeholder="Selecciona un producto" options={uniqueProducts.map((row) => ({ value: row.product_id, label: row.product_name, searchText: `${row.product_name} ${row.product_code || ''}` }))} /></label><label>Cantidad<input required type="number" min="0.0001" step="0.0001" className="input mt-1" value={transfer.quantity} onChange={(event) => setTransfer({ ...transfer, quantity: event.target.value })} /></label><label>Motivo<textarea required minLength={3} className="input mt-1 min-h-24" value={transfer.reason} onChange={(event) => setTransfer({ ...transfer, reason: event.target.value })} placeholder="Ej. Reposición de tienda" /></label></section></form>
      </Drawer>

      <Drawer open={modal === 'receipt' && Boolean(selectedReturn)} onClose={() => { setModal(null); setSelectedReturn(null); }} variant="inventory-action" tone="warning" eyebrow="Devolución física" status="Recepción pendiente" initialFocus="input" title="Confirmar recepción" subtitle={selectedReturn?.credit_note_number || 'Devolución autorizada'} icon={<RotateCcw size={20} />} footer={<><button type="button" className="btn-ghost" onClick={() => { setModal(null); setSelectedReturn(null); }}>Cancelar</button><button type="submit" form="receipt-form" className="btn-primary" disabled={saving || !Object.values(receipt).some((value) => Number(value) > 0)}>{saving ? 'Ingresando…' : 'Ingresar al stock'}</button></>}>
        <form id="receipt-form" onSubmit={submitReceipt} className="inventory-action-form"><section className="inventory-form-section"><div className="inventory-form-section__heading"><span>01</span><div><h3>Unidades recibidas</h3><p>Registra solo la cantidad que regresó físicamente al almacén.</p></div></div><div className="inventory-receipt-list">{selectedReturn?.items.map((item) => { const remaining = Number(item.authorized_quantity) - Number(item.received_quantity); return <label key={item.id}><span><strong>{item.product_name || `Producto #${item.product_id}`}</strong><small>Pendiente por recibir: {qty(remaining)}</small></span><input type="number" min="0" max={remaining} step="0.0001" className="input" value={receipt[item.id] || ''} onChange={(event) => setReceipt({ ...receipt, [item.id]: event.target.value })} aria-label={`Cantidad recibida de ${item.product_name || `producto ${item.product_id}`}`} /></label>; })}</div></section><p className="inventory-stock-drawer__notice"><RotateCcw size={15} aria-hidden="true" />Las cantidades confirmadas se sumarán al stock y no podrán superar el saldo pendiente.</p></form>
      </Drawer>
    </main>
  );
}
