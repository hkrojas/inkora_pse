/** Stock setup shared by catalog and quick product creation flows. */
export default function InventoryInitialFields({ value, onChange, warehouses = [], disabled = false, compact = false }) {
  const enabled = Boolean(value);
  const update = (patch) => onChange({
    warehouse_id: value?.warehouse_id || String(warehouses.find((warehouse) => warehouse.is_default)?.id || ''),
    opening_stock: value?.opening_stock ?? '0',
    minimum_stock: value?.minimum_stock ?? '0',
    ...patch,
  });

  return (
    <section className={compact ? 'rounded-xl border border-[var(--color-border)] p-3' : 'ink-form-section'}>
      <label className="flex cursor-pointer items-start gap-3">
        <input
          type="checkbox"
          checked={enabled}
          disabled={disabled}
          onChange={(event) => onChange(event.target.checked ? {
            warehouse_id: String(warehouses.find((warehouse) => warehouse.is_default)?.id || ''),
            opening_stock: '0',
            minimum_stock: '0',
          } : null)}
        />
        <span>
          <span className="block text-sm font-bold text-[var(--color-text)]">Controlar inventario</span>
          <span className="block text-xs text-[var(--color-text-muted)]">Registra el saldo inicial en el kardex con trazabilidad.</span>
        </span>
      </label>
      {enabled && (
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          <label className="text-sm font-bold">Almacén
            <select className="input mt-1" value={value.warehouse_id || ''} onChange={(event) => update({ warehouse_id: event.target.value })} disabled={disabled || warehouses.length === 0}>
              {warehouses.length === 0 ? <option value="">Se creará el almacén principal</option> : warehouses.map((warehouse) => <option key={warehouse.id} value={warehouse.id}>{warehouse.name}{warehouse.is_default ? ' · Principal' : ''}</option>)}
            </select>
          </label>
          <label className="text-sm font-bold">Stock inicial
            <input className="input mt-1" type="number" min="0" step="0.0001" inputMode="decimal" value={value.opening_stock ?? '0'} onChange={(event) => update({ opening_stock: event.target.value })} disabled={disabled} />
          </label>
          <label className="text-sm font-bold">Stock mínimo
            <input className="input mt-1" type="number" min="0" step="0.0001" inputMode="decimal" value={value.minimum_stock ?? '0'} onChange={(event) => update({ minimum_stock: event.target.value })} disabled={disabled} />
          </label>
        </div>
      )}
    </section>
  );
}
