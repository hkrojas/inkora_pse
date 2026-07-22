import { useEffect, useMemo, useRef, useState } from 'react';
import { ArrowLeft, Check, FileSearch, Loader2, Save, Send } from 'lucide-react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useToast } from '../components/ui/Toast';
import CustomSelect from '../components/ui/CustomSelect';
import { api } from '../lib/utils/api';
import { formatCurrency } from '../lib/utils/documents';
import { notas } from '../services/notas';

const STEPS = ['Comprobante', 'Tipo y motivo', 'Ajuste', 'Revisión'];
const FULL_CODES = new Set(['01', '02', '06']);
const LINE_CODES = new Set(['03', '05', '07', '08']);
const GLOBAL_CODES = new Set(['04', '09', '10', '13']);
const INVENTORY_CODES = new Set(['01', '06', '07']);

const initialForm = {
  tipo_nota: 'credito', cod_motivo: '', descripcion_motivo: '',
  input_type: 'amount', input_value: '', inventory_impact: 'none',
  inventory_return_warehouse_id: '', payment_due: '', payment_amount: '',
};

function money(value) {
  const number = Number(value || 0);
  return Number.isFinite(number) ? number : 0;
}

function modeFor(form) {
  if (form.tipo_nota === 'debito') return 'charge';
  if (FULL_CODES.has(form.cod_motivo)) return 'full';
  if (LINE_CODES.has(form.cod_motivo)) return 'lines';
  if (GLOBAL_CODES.has(form.cod_motivo)) return form.cod_motivo === '13' ? 'payment_terms' : 'global';
  return 'global';
}

export default function NotaNuevaPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const draftId = searchParams.get('draft');
  const sourceDocumentId = searchParams.get('documento');
  const requestedType = searchParams.get('tipo');
  const lockedSource = Boolean(sourceDocumentId && !draftId);
  const selectedType = requestedType === 'debito' ? 'debito' : 'credito';
  const toast = useToast();
  const pollRef = useRef(null);
  const [query, setQuery] = useState('');
  const [documents, setDocuments] = useState([]);
  const [searching, setSearching] = useState(false);
  const [context, setContext] = useState(null);
  const [form, setForm] = useState(initialForm);
  const [lineValues, setLineValues] = useState({});
  const [draft, setDraft] = useState(null);
  const [busy, setBusy] = useState(false);
  const [jobStatus, setJobStatus] = useState('');
  const [error, setError] = useState('');

  useEffect(() => () => clearTimeout(pollRef.current), []);

  useEffect(() => {
    if (!draftId) return;
    let active = true;
    (async () => {
      setBusy(true);
      try {
        const saved = await notas.get(draftId);
        if (saved.estado !== 'borrador') throw new Error('Esta nota ya no es editable.');
        const next = await notas.context(saved.comprobante_afectado_id);
        if (!active) return;
        const adjustment = saved.adjustment || {};
        const persistedLines = Object.fromEntries((adjustment.lines || []).map((line) => [line.source_item_id, line]));
        setContext(next);
        setDocuments((current) => current.some((item) => item.id === next.document.id) ? current : [next.document, ...current]);
        setForm({
          ...initialForm,
          tipo_nota: saved.tipo_nota,
          cod_motivo: saved.cod_motivo,
          descripcion_motivo: saved.descripcion_motivo,
          input_type: adjustment.input_type || 'amount',
          input_value: adjustment.input_value ?? '',
          inventory_impact: saved.inventory_impact || 'none',
          inventory_return_warehouse_id: saved.inventory_return_warehouse_id || '',
          payment_due: adjustment.payment_terms?.due_date || '',
          payment_amount: adjustment.payment_terms?.pending_amount ?? '',
        });
        setLineValues(Object.fromEntries(next.lines.map((line) => {
          const persisted = persistedLines[line.id] || {};
          return [line.id, {
            selected: Boolean(persistedLines[line.id]),
            quantity: persisted.quantity ?? '', percentage: persisted.percentage ?? '',
            amount: persisted.amount ?? '', description: persisted.description || line.descripcion,
          }];
        })));
        setDraft(saved);
      } catch (requestError) {
        if (active) setError(requestError.message);
      } finally {
        if (active) setBusy(false);
      }
    })();
    return () => { active = false; };
  }, [draftId]);

  useEffect(() => {
    if (draftId || !sourceDocumentId) return undefined;
    let active = true;
    (async () => {
      setBusy(true);
      setError('');
      try {
        const next = await notas.context(sourceDocumentId);
        if (!active) return;
        setContext(next);
        setDocuments([next.document]);
        setForm({ ...initialForm, tipo_nota: selectedType });
        setLineValues(Object.fromEntries(next.lines.map((line) => [line.id, {
          selected: false, quantity: '', percentage: '', amount: '', description: line.descripcion,
        }])));
      } catch (requestError) {
        if (active) setError(requestError.message);
      } finally {
        if (active) setBusy(false);
      }
    })();
    return () => { active = false; };
  }, [draftId, selectedType, sourceDocumentId]);

  useEffect(() => {
    if (lockedSource) return undefined;
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      setSearching(true);
      try {
        const params = new URLSearchParams({ limit: '30', tab: 'emitted' });
        if (query.trim()) params.set('q', query.trim());
        const response = await api.get(`/facturas-emitidas/page?${params}`, { signal: controller.signal });
        setDocuments(Array.isArray(response) ? response : response.items || []);
      } catch (requestError) {
        if (!requestError.isCanceled) setError(requestError.message);
      } finally {
        setSearching(false);
      }
    }, 280);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [lockedSource, query]);

  const selectDocument = async (id) => {
    if (!id) { setContext(null); return; }
    setBusy(true);
    setError('');
    try {
      const next = await notas.context(id);
      setContext(next);
      setForm(initialForm);
      setLineValues(Object.fromEntries(next.lines.map((line) => [line.id, {
        selected: false, quantity: '', percentage: '', amount: '', description: line.descripcion,
      }])));
      setDraft(null);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  };

  const motives = context?.allowed_motives?.[form.tipo_nota] || {};
  const adjustmentMode = modeFor(form);
  const original = money(context?.balance?.original);
  const estimatedTotal = useMemo(() => {
    if (!context) return 0;
    if (adjustmentMode === 'full') return original;
    if (adjustmentMode === 'payment_terms') {
      return Math.max(0, money(context?.balance?.saldo_fiscal) - money(form.payment_amount));
    }
    if (adjustmentMode === 'global' || adjustmentMode === 'charge') {
      return form.input_type === 'percentage'
        ? original * money(form.input_value) / 100
        : money(form.input_value);
    }
    return context.lines.reduce((sum, line) => {
      const input = lineValues[line.id];
      if (!input?.selected) return sum;
      if (form.cod_motivo === '07') return sum + money(input.quantity) * money(line.precio_unitario);
      if (['03', '08'].includes(form.cod_motivo)) return sum + money(line.total);
      return form.input_type === 'percentage'
        ? sum + money(line.total) * money(input.percentage) / 100
        : sum + money(input.amount);
    }, 0);
  }, [adjustmentMode, context, form.cod_motivo, form.input_type, form.input_value, form.payment_amount, lineValues, original]);

  const setField = (name, value) => {
    setForm((current) => ({ ...current, [name]: value }));
    setDraft(null);
  };
  const setLine = (id, patch) => {
    setLineValues((current) => ({ ...current, [id]: { ...current[id], ...patch } }));
    setDraft(null);
  };

  const payload = () => ({
    comprobante_afectado_id: context.document.id,
    tipo_nota: form.tipo_nota,
    cod_motivo: form.cod_motivo,
    descripcion_motivo: form.descripcion_motivo,
    adjustment_mode: adjustmentMode,
    input_type: ['global', 'payment_terms', 'charge'].includes(adjustmentMode) ? form.input_type : null,
    input_value: ['global', 'charge'].includes(adjustmentMode) ? money(form.input_value) : (adjustmentMode === 'payment_terms' ? estimatedTotal : null),
    lines: context.lines.flatMap((line) => {
      const input = lineValues[line.id];
      if (!input?.selected) return [];
      return [{
        source_item_id: line.id,
        quantity: input.quantity ? money(input.quantity) : null,
        amount: input.amount ? money(input.amount) : null,
        percentage: input.percentage ? money(input.percentage) : null,
        description: input.description || null,
      }];
    }),
    payment_terms: form.cod_motivo === '13' ? {
      due_date: form.payment_due || null,
      pending_amount: money(form.payment_amount || form.input_value),
    } : null,
    inventory_impact: form.inventory_impact,
    inventory_return_warehouse_id: form.inventory_return_warehouse_id
      ? Number(form.inventory_return_warehouse_id) : null,
  });

  const saveDraft = async () => {
    if (!context || !form.cod_motivo || form.descripcion_motivo.trim().length < 3) {
      setError('Selecciona comprobante y motivo, y escribe un sustento de al menos 3 caracteres.');
      return null;
    }
    setBusy(true);
    setError('');
    try {
      const saved = draft
        ? await notas.update(draft.id, payload())
        : await notas.create(payload(), crypto.randomUUID());
      setDraft(saved);
      toast('Borrador guardado', 'success');
      return saved;
    } catch (requestError) {
      setError(requestError.message);
      return null;
    } finally {
      setBusy(false);
    }
  };

  const pollJob = async (jobId) => {
    try {
      const job = await notas.job(jobId);
      setJobStatus(job.status);
      if (['queued', 'processing', 'retry'].includes(job.status)) {
        pollRef.current = setTimeout(() => pollJob(jobId), 1800);
      } else if (job.status === 'succeeded') {
        toast('Aceptada por SUNAT', 'success');
        navigate('/notas');
      } else {
        setError(job.last_error || 'SUNAT rechazó la nota. El borrador no se duplicó.');
      }
    } catch (requestError) {
      setError(requestError.message);
    }
  };

  const emit = async () => {
    const saved = draft || await saveDraft();
    if (!saved) return;
    setBusy(true);
    setError('');
    try {
      const response = await notas.emit(saved.id);
      setJobStatus(response.status || 'queued');
      toast('Nota en cola para emisión fiscal', 'success');
      pollJob(response.job_id);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  };

  const progress = [Boolean(context), Boolean(context && form.cod_motivo), estimatedTotal > 0, Boolean(draft)];
  const canSave = Boolean(context && form.cod_motivo && form.descripcion_motivo.trim().length >= 3 && estimatedTotal > 0);

  return (
    <div className="page-shell pb-28 lg:pb-8">
      <header className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <button type="button" className="mb-2 inline-flex items-center gap-2 text-sm text-[var(--color-text-muted)] hover:text-[var(--color-text)]" onClick={() => navigate('/notas')}>
            <ArrowLeft size={16} aria-hidden="true" /> Volver a notas
          </button>
          <h1 className="page-title">Nueva nota de crédito o débito</h1>
          <p className="page-subtitle">Guarda el ajuste como borrador y emítelo solo después de revisar el cálculo.</p>
        </div>
        {jobStatus && <span className="badge badge-warning" role="status">{jobStatus === 'retry' ? 'Reintentando' : jobStatus}</span>}
      </header>

      <nav aria-label="Progreso de la nota" className="mb-6 grid grid-cols-2 gap-2 rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-3 md:grid-cols-4">
        {STEPS.map((step, index) => <div key={step} className="flex items-center gap-2 text-sm font-semibold">
          <span className={`grid h-7 w-7 place-items-center rounded-full ${progress[index] ? 'bg-emerald-100 text-emerald-700' : 'bg-[var(--color-surface-muted)] text-[var(--color-text-muted)]'}`}>
            {progress[index] ? <Check size={15} aria-hidden="true" /> : index + 1}
          </span>{step}
        </div>)}
      </nav>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
        <main className="space-y-5">
          <section className="card p-5" aria-labelledby="source-title">
            <h2 id="source-title" className="text-lg font-bold">1. Comprobante afectado</h2>
            <p className="mb-4 text-sm text-[var(--color-text-muted)]">Solo aparecen facturas y boletas aceptadas por SUNAT.</p>
            {lockedSource ? (
              <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-4">
                <p className="m-0 font-mono text-sm font-extrabold">{context?.document?.document_number || 'Cargando comprobante...'}</p>
                {context?.document && <p className="mt-1 text-sm text-[var(--color-text-muted)]">{context.document.cliente?.razon_social || context.document.cliente?.nombre || 'Cliente'} · {formatCurrency(context.document.total_venta, context.document.moneda)}</p>}
                <button type="button" className="btn-ghost mt-3" onClick={() => navigate('/notas')}>Cambiar comprobante</button>
              </div>
            ) : <>
              <label className="form-label" htmlFor="document-search">Buscar por serie, número, RUC o cliente</label>
              <div className="relative mb-3">
                <FileSearch className="pointer-events-none absolute left-3 top-3 text-[var(--color-text-muted)]" size={18} />
                <input id="document-search" className="input w-full pl-10" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Ej. F001-152 o 20123456789" />
                {searching && <Loader2 className="absolute right-3 top-3 animate-spin" size={18} aria-label="Buscando" />}
              </div>
              <label className="form-label" htmlFor="source-document">Seleccionar comprobante</label>
              <CustomSelect id="source-document" searchable searchPlaceholder="Buscar serie, cliente o documento" ariaLabel="Seleccionar comprobante" value={context?.document?.id || ''} onChange={selectDocument} placeholder="Selecciona un comprobante aceptado" options={documents.map((doc) => { const number = doc.document_number || `${doc.serie}-${String(doc.correlativo).padStart(6, '0')}`; const client = doc.cliente?.razon_social || doc.cliente?.nombre || 'Cliente'; return { value: doc.id, label: `${number} · ${client} · ${formatCurrency(doc.total_venta, doc.moneda)}`, searchText: `${number} ${client} ${doc.cliente?.numero_documento || ''}` }; })} />
            </>}
          </section>

          <section className="card p-5" aria-labelledby="reason-title">
            <h2 id="reason-title" className="mb-4 text-lg font-bold">2. Tipo y motivo SUNAT</h2>
            <div className="grid gap-4 md:grid-cols-2">
              <div><label className="form-label" htmlFor="note-type">Tipo de nota</label><CustomSelect id="note-type" ariaLabel="Tipo de nota" value={form.tipo_nota} onChange={(value) => { setField('tipo_nota', value); setField('cod_motivo', ''); }} options={[{ value: 'credito', label: 'Nota de crédito (07)' }, { value: 'debito', label: 'Nota de débito (08)' }]} /></div>
              <div><label className="form-label" htmlFor="note-reason">Motivo</label><CustomSelect id="note-reason" searchable searchPlaceholder="Buscar código o motivo" ariaLabel="Motivo SUNAT" disabled={!context} value={form.cod_motivo} onChange={(value) => setField('cod_motivo', value)} placeholder="Selecciona el motivo" options={Object.entries(motives).map(([code, label]) => ({ value: code, label: `${code} · ${label}`, searchText: `${code} ${label}` }))} /></div>
            </div>
            <label className="form-label mt-4" htmlFor="reason-detail">Sustento del ajuste</label>
            <textarea id="reason-detail" className="input min-h-24 w-full" value={form.descripcion_motivo} onChange={(event) => setField('descripcion_motivo', event.target.value)} aria-describedby="reason-help" placeholder="Explica claramente por qué se emite esta nota" />
            <p id="reason-help" className="mt-1 text-xs text-[var(--color-text-muted)]">Este texto se enviará en el documento fiscal.</p>
          </section>

          {context && form.cod_motivo && <section className="card p-5" aria-labelledby="adjustment-title">
            <h2 id="adjustment-title" className="text-lg font-bold">3. Ajuste</h2>
            {adjustmentMode === 'full' && <p className="mt-3 rounded-xl bg-amber-50 p-4 text-sm text-amber-900 dark:bg-amber-950/30 dark:text-amber-100">Este motivo ajusta el comprobante completo. Total de la nota: <strong>{formatCurrency(original)}</strong>.</p>}
            {['global', 'payment_terms', 'charge'].includes(adjustmentMode) && <div className="mt-4 grid gap-4 md:grid-cols-2">
              {adjustmentMode === 'global' && <div><label className="form-label" htmlFor="input-type">Calcular por</label><CustomSelect id="input-type" ariaLabel="Calcular ajuste por" value={form.input_type} onChange={(value) => setField('input_type', value)} options={[{ value: 'amount', label: 'Monto' }, { value: 'percentage', label: 'Porcentaje' }]} /></div>}
              {adjustmentMode !== 'payment_terms' && <div><label className="form-label" htmlFor="input-value">{form.input_type === 'percentage' ? 'Porcentaje (%)' : 'Importe'}</label><input id="input-value" type="number" min="0" max={form.input_type === 'percentage' ? 100 : undefined} step="0.01" className="input w-full" value={form.input_value} onChange={(event) => setField('input_value', event.target.value)} /></div>}
              {form.cod_motivo === '13' && <><div><label className="form-label" htmlFor="payment-due">Nuevo vencimiento</label><input id="payment-due" type="date" className="input w-full" value={form.payment_due} onChange={(event) => setField('payment_due', event.target.value)} /></div><div><label className="form-label" htmlFor="payment-amount">Nuevo monto pendiente</label><input id="payment-amount" type="number" min="0" step="0.01" className="input w-full" value={form.payment_amount} onChange={(event) => setField('payment_amount', event.target.value)} /></div></>}
            </div>}
            {adjustmentMode === 'lines' && <div className="mt-4">{form.cod_motivo === '05' && <div className="mb-3 max-w-xs"><label className="form-label" htmlFor="line-input-type">Descontar cada línea por</label><CustomSelect id="line-input-type" ariaLabel="Descontar cada línea por" value={form.input_type} onChange={(value) => setField('input_type', value)} options={[{ value: 'amount', label: 'Monto' }, { value: 'percentage', label: 'Porcentaje' }]} /></div>}<div className="overflow-x-auto"><table className="w-full min-w-[720px] text-sm"><thead><tr className="border-b text-left text-[var(--color-text-muted)]"><th className="p-3">Incluir</th><th className="p-3">Descripción</th><th className="p-3">Original</th><th className="p-3">Máximo</th><th className="p-3">Ajuste</th></tr></thead><tbody>{context.lines.map((line) => { const input = lineValues[line.id] || {}; return <tr key={line.id} className="border-b border-[var(--color-border)]"><td className="p-3"><input type="checkbox" aria-label={`Incluir ${line.descripcion}`} checked={Boolean(input.selected)} onChange={(event) => setLine(line.id, { selected: event.target.checked })} /></td><td className="p-3 font-medium">{form.cod_motivo === '03' && input.selected ? <input className="input min-w-64" aria-label={`Descripción corregida de ${line.descripcion}`} value={input.description || ''} onChange={(event) => setLine(line.id, { description: event.target.value })} /> : line.descripcion}</td><td className="p-3">{line.cantidad} × {formatCurrency(line.precio_unitario)}</td><td className="p-3">{form.cod_motivo === '07' ? line.cantidad_devolvible : formatCurrency(line.total)}</td><td className="p-3">{form.cod_motivo === '07' ? <input type="number" className="input w-28" min="0" max={line.cantidad_devolvible} step="0.0001" aria-label={`Cantidad a devolver de ${line.descripcion}`} value={input.quantity || ''} onChange={(event) => setLine(line.id, { quantity: event.target.value })} /> : ['03', '08'].includes(form.cod_motivo) ? 'Total de línea' : <input type="number" className="input w-28" min="0" max={form.input_type === 'percentage' ? 100 : line.total} step="0.01" aria-label={`${form.input_type === 'percentage' ? 'Porcentaje' : 'Monto'} de ${line.descripcion}`} value={form.input_type === 'percentage' ? (input.percentage || '') : (input.amount || '')} onChange={(event) => setLine(line.id, form.input_type === 'percentage' ? { percentage: event.target.value, amount: '' } : { amount: event.target.value, percentage: '' })} placeholder={form.input_type === 'percentage' ? '%' : 'S/'} />}</td></tr>; })}</tbody></table></div></div>}
            {form.tipo_nota === 'credito' && INVENTORY_CODES.has(form.cod_motivo) && <fieldset className="mt-5 border-t border-[var(--color-border)] pt-4"><legend className="font-semibold">Impacto físico de inventario</legend><div className="mt-3 grid gap-3 md:grid-cols-3">{[['none', 'Sin movimiento físico'], ['undelivered', 'Mercadería no entregada'], ['physical_return', 'Devolución física pendiente']].map(([value, label]) => <label key={value} className="flex cursor-pointer gap-2 rounded-xl border border-[var(--color-border)] p-3"><input type="radio" name="inventory" value={value} checked={form.inventory_impact === value} onChange={(event) => setField('inventory_impact', event.target.value)} /><span>{label}</span></label>)}</div></fieldset>}
            {form.inventory_impact === 'physical_return' && <div className="mt-4"><label className="form-label" htmlFor="return-warehouse">Almacén que recibirá la devolución</label><CustomSelect id="return-warehouse" ariaLabel="Almacén que recibirá la devolución" value={form.inventory_return_warehouse_id} onChange={(value) => setField('inventory_return_warehouse_id', value)} placeholder="Selecciona un almacén" options={(context.warehouses || []).map((warehouse) => ({ value: warehouse.id, label: `${warehouse.name}${warehouse.is_default ? ' · Principal' : ''}` }))} /></div>}
          </section>}
          {error && <div className="rounded-xl border border-red-300 bg-red-50 p-4 text-sm text-red-800 dark:bg-red-950/30 dark:text-red-200" role="alert">{error}</div>}
        </main>

        <aside className="h-fit rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5 xl:sticky xl:top-24" aria-label="Resumen de la nota">
          <h2 className="text-lg font-bold">Resumen</h2>
          <dl className="mt-4 space-y-3 text-sm">
            <div className="flex justify-between"><dt>Total original</dt><dd className="font-semibold">{formatCurrency(original)}</dd></div>
            <div className="flex justify-between"><dt>Créditos aceptados</dt><dd>{formatCurrency(context?.balance?.creditos_aceptados || 0)}</dd></div>
            <div className="flex justify-between"><dt>Ajustes reservados</dt><dd>{formatCurrency(context?.balance?.ajustes_reservados || 0)}</dd></div>
            <div className="flex justify-between"><dt>Máximo disponible</dt><dd>{formatCurrency(context?.balance?.maximo_disponible || 0)}</dd></div>
            <div className="border-t border-dashed border-[var(--color-border)] pt-3"><div className="flex justify-between text-base font-bold"><dt>Total de esta nota</dt><dd>{formatCurrency(estimatedTotal)}</dd></div><div className="mt-2 flex justify-between text-[var(--color-text-muted)]"><dt>Saldo fiscal resultante</dt><dd>{formatCurrency(Math.max(0, money(context?.balance?.saldo_fiscal) + (form.tipo_nota === 'debito' ? estimatedTotal : -estimatedTotal)))}</dd></div></div>
          </dl>
          <div className="mt-5 grid gap-2"><button type="button" className="btn-secondary justify-center" disabled={!canSave || busy || jobStatus} onClick={saveDraft}>{busy ? <Loader2 className="animate-spin" size={17} /> : <Save size={17} />} Guardar borrador</button><button type="button" className="btn-primary justify-center" disabled={!canSave || busy || Boolean(jobStatus)} onClick={emit}><Send size={17} /> Emitir a SUNAT</button></div>
        </aside>
      </div>

      <div className="fixed inset-x-0 bottom-0 z-30 flex items-center justify-between gap-3 border-t border-[var(--color-border)] bg-[var(--color-surface)] p-3 shadow-2xl xl:hidden"><div><span className="block text-xs text-[var(--color-text-muted)]">Total de la nota</span><strong>{formatCurrency(estimatedTotal)}</strong></div><button type="button" className="btn-primary" disabled={!canSave || busy || Boolean(jobStatus)} onClick={emit}>{busy ? <Loader2 className="animate-spin" size={17} /> : <Send size={17} />} Emitir</button></div>
    </div>
  );
}
