import { useCallback, useEffect, useMemo, useState } from 'react';
import CustomSelect from '../ui/CustomSelect';
import { clientes } from '../../services/clientes';
import { productos } from '../../services/productos';

export default function DashboardEntityFilter({ kind, selected, onChange }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [rows, setRows] = useState([]);
  const [status, setStatus] = useState('idle');
  const [retry, setRetry] = useState(0);
  const isClient = kind === 'client';
  const handleOpen = useCallback((value) => {
    setOpen(value);
    if (!value) setQuery('');
  }, []);

  useEffect(() => {
    if (!open) return undefined;
    let active = true;
    const controller = new AbortController();
    setStatus('loading');
    setRows([]);
    const timer = window.setTimeout(() => {
      const service = kind === 'client' ? clientes : productos;
      service.search(query.trim(), 20, { signal: controller.signal })
        .then((items) => {
          if (!active) return;
          setRows(Array.isArray(items) ? items : []);
          setStatus('ready');
        })
        .catch((error) => {
          if (active && !error?.isCanceled) { setRows([]); setStatus('error'); }
        });
    }, 250);
    return () => { active = false; window.clearTimeout(timer); controller.abort(); };
  }, [kind, open, query, retry]);

  const options = useMemo(() => {
    const found = rows.map((row) => ({
      value: String(row.id),
      label: isClient ? row.razon_social || row.nombre_comercial || `Cliente #${row.id}` : row.nombre || row.descripcion || `Producto #${row.id}`,
    }));
    if (selected && !found.some((row) => row.value === String(selected.id))) found.unshift({ value: String(selected.id), label: selected.name });
    return [{ value: '', label: isClient ? 'Todos los clientes' : 'Todos los productos' }, ...found];
  }, [isClient, rows, selected]);

  return (
    <div className="business-period-control business-entity-filter">
      <span>{isClient ? 'Cliente' : 'Producto incluido en la venta'}</span>
      <CustomSelect
        ariaLabel={isClient ? 'Filtrar por cliente' : 'Filtrar por producto'}
        value={selected ? String(selected.id) : ''}
        options={options}
        searchable
        searchPlaceholder={isClient ? 'Buscar cliente' : 'Buscar producto'}
        onSearchChange={setQuery}
        onOpenChange={handleOpen}
        loading={status === 'loading'}
        filterOption={(option) => option.value === '' || option.value !== String(selected?.id) || option.label.toLowerCase().includes(query.toLowerCase())}
        onChange={(value) => {
          const option = options.find((item) => item.value === value);
          onChange(value ? { id: Number(value), name: option.label } : null);
        }}
        noResultsLabel="No hay resultados. Prueba otro nombre."
      />
      {open && status === 'error' && <p className="business-period-error" role="alert">No pudimos buscar. <button type="button" onMouseDown={(event) => event.stopPropagation()} onClick={() => setRetry((value) => value + 1)}>Reintentar</button></p>}
      {open && status === 'ready' && rows.length === 0 && query && <p role="status" className="business-filter-hint">No hay coincidencias. Prueba otro nombre.</p>}
    </div>
  );
}
