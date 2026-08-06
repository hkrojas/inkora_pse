import CustomSelect from '../ui/CustomSelect';

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
    <section className={`inventory-initial-fields${compact ? ' inventory-initial-fields--compact' : ''}`}>
      <button
        type="button"
        className={`inventory-initial-fields__toggle${enabled ? ' is-active' : ''}`}
        role="switch"
        aria-checked={enabled}
        disabled={disabled}
        onClick={() => onChange(!enabled ? {
            warehouse_id: String(warehouses.find((warehouse) => warehouse.is_default)?.id || ''),
            opening_stock: '0',
            minimum_stock: '0',
          } : null)}
      >
        <span className="inventory-initial-fields__switch" aria-hidden="true"><span /></span>
        <span className="inventory-initial-fields__copy">
          <span>Controlar inventario</span>
          <small>Registra el saldo inicial en el kardex con trazabilidad.</small>
        </span>
      </button>
      {enabled && (
        <div className="inventory-initial-fields__grid">
          <label className="text-sm font-bold">Almacén
            <CustomSelect
              value={value.warehouse_id || ''}
              onChange={(warehouse_id) => update({ warehouse_id: String(warehouse_id || '') })}
              disabled={disabled || warehouses.length === 0}
              placeholder={warehouses.length === 0 ? 'Se creará el almacén principal' : 'Selecciona un almacén'}
              options={warehouses.map((warehouse) => ({ value: String(warehouse.id), label: `${warehouse.name}${warehouse.is_default ? ' · Principal' : ''}` }))}
            />
          </label>
          <label className="text-sm font-bold">Stock inicial
            <input className="input inventory-initial-fields__number" type="number" min="0" step="0.0001" inputMode="decimal" value={value.opening_stock ?? '0'} onChange={(event) => update({ opening_stock: event.target.value })} disabled={disabled} />
          </label>
          <label className="text-sm font-bold">Stock mínimo
            <input className="input inventory-initial-fields__number" type="number" min="0" step="0.0001" inputMode="decimal" value={value.minimum_stock ?? '0'} onChange={(event) => update({ minimum_stock: event.target.value })} disabled={disabled} />
          </label>
        </div>
      )}
    </section>
  );
}
