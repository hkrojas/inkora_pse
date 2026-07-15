import { useCallback, useEffect, useMemo, useState } from 'react';
import { ArrowRight, CheckCircle2, Clock3, CreditCard, FileText, ReceiptText, RefreshCw, Search, XCircle, XOctagon } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { api } from '../lib/utils/api';
import { useToast } from '../components/ui/Toast';
import Drawer from '../components/ui/Drawer';
import Spinner from '../components/ui/Spinner';
import EmptyState from '../components/ui/EmptyState';
import { PageError } from '../components/ui/PageState';
import Badge from '../components/ui/Badge';
import { DocumentTypeBadge } from '../components/documents/DocumentType';
import { formatCurrency, getSunatStatus } from '../lib/utils/documents';
import { notas as notasService } from '../services/notas';

const PER_PAGE = 15;

const NOTE_TYPE_FILTERS = [
  { value: 'all', label: 'Todas las notas' },
  { value: 'nc', label: 'Notas de crédito' },
  { value: 'nd', label: 'Notas de débito' },
];

const STATUS_FILTERS = [
  { value: 'all', label: 'Todos los estados' },
  { value: 'aceptado', label: 'Aceptadas' },
  { value: 'pendiente', label: 'Pendientes' },
  { value: 'error', label: 'Observadas' },
  { value: 'anulado', label: 'Anuladas' },
];

function numberOf(document) {
  const number = document?.document_number || document?.number;
  if (number) return number;
  if (document?.serie || document?.correlativo !== undefined) {
    return `${document?.serie || ''}-${String(document?.correlativo || '').padStart(6, '0')}`;
  }
  return 'Sin correlativo';
}

function clientName(document) {
  return document?.cliente?.razon_social || document?.cliente?.nombre || 'Cliente sin nombre';
}

function clientDocument(document) {
  return document?.cliente?.numero_documento || document?.cliente?.ruc || document?.cliente?.dni || '';
}

function formatDate(value) {
  return value ? new Date(value).toLocaleDateString('es-PE') : '—';
}

function NoteStatus({ document }) {
  const status = getSunatStatus(document);
  if (!status) return <Badge variant="default">Sin estado</Badge>;
  return <Badge variant={status.variant === 'danger' ? 'error' : status.variant} title={status.tooltip}>{status.label}</Badge>;
}

export default function NotasPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const [section, setSection] = useState('emit');
  const [sourceDocuments, setSourceDocuments] = useState([]);
  const [sourceTotal, setSourceTotal] = useState(0);
  const [sourcePage, setSourcePage] = useState(1);
  const [sourceQuery, setSourceQuery] = useState('');
  const [sourceLoading, setSourceLoading] = useState(true);
  const [sourceError, setSourceError] = useState(null);
  const [notes, setNotes] = useState([]);
  const [notesTotal, setNotesTotal] = useState(0);
  const [notesPage, setNotesPage] = useState(1);
  const [notesQuery, setNotesQuery] = useState('');
  const [noteType, setNoteType] = useState('all');
  const [noteStatus, setNoteStatus] = useState('all');
  const [notesLoading, setNotesLoading] = useState(false);
  const [notesError, setNotesError] = useState(null);
  const [drawer, setDrawer] = useState({ open: false, document: null, type: 'credito', context: null, loading: false, error: null });

  const loadSources = useCallback(async () => {
    setSourceLoading(true);
    setSourceError(null);
    try {
      const params = new URLSearchParams({
        skip: String((sourcePage - 1) * PER_PAGE),
        limit: String(PER_PAGE),
        tab: 'emitted',
      });
      if (sourceQuery.trim()) params.set('q', sourceQuery.trim());
      const response = await api.get(`/facturas-emitidas/page?${params}`);
      setSourceDocuments(Array.isArray(response) ? response : response.items || []);
      setSourceTotal(Array.isArray(response) ? response.length : Number(response.total || 0));
    } catch (error) {
      setSourceDocuments([]);
      setSourceTotal(0);
      setSourceError(error);
    } finally {
      setSourceLoading(false);
    }
  }, [sourcePage, sourceQuery]);

  const loadNotes = useCallback(async () => {
    setNotesLoading(true);
    setNotesError(null);
    try {
      const params = new URLSearchParams({
        skip: String((notesPage - 1) * PER_PAGE),
        limit: String(PER_PAGE),
        tab: 'all',
      });
      if (notesQuery.trim()) params.set('q', notesQuery.trim());
      if (noteType !== 'all') params.set('tipo_nota', noteType);
      if (noteStatus !== 'all') params.set('estado', noteStatus);
      const response = await api.get(`/notas/page?${params}`);
      setNotes(Array.isArray(response) ? response : response.items || []);
      setNotesTotal(Array.isArray(response) ? response.length : Number(response.total || 0));
    } catch (error) {
      setNotes([]);
      setNotesTotal(0);
      setNotesError(error);
    } finally {
      setNotesLoading(false);
    }
  }, [noteStatus, noteType, notesPage, notesQuery]);

  useEffect(() => { if (section === 'emit') loadSources(); }, [loadSources, section]);
  useEffect(() => { if (section === 'history') loadNotes(); }, [loadNotes, section]);
  useEffect(() => { setSourcePage(1); }, [sourceQuery]);
  useEffect(() => { setNotesPage(1); }, [notesQuery, noteStatus, noteType]);

  const openDrawer = async (document, type) => {
    setDrawer({ open: true, document, type, context: null, loading: true, error: null });
    try {
      const context = await notasService.context(document.id);
      setDrawer((current) => current.document?.id === document.id && current.type === type
        ? { ...current, context, loading: false }
        : current);
    } catch (error) {
      setDrawer((current) => current.document?.id === document.id && current.type === type
        ? { ...current, loading: false, error }
        : current);
    }
  };

  const closeDrawer = () => setDrawer((current) => ({ ...current, open: false }));
  const context = drawer.context;
  const selectedMotives = context?.allowed_motives?.[drawer.type] || {};
  const canContinue = Boolean(context && Object.keys(selectedMotives).length);
  const sourcePages = Math.max(1, Math.ceil(sourceTotal / PER_PAGE));
  const historyPages = Math.max(1, Math.ceil(notesTotal / PER_PAGE));

  const historySummary = useMemo(() => notes.reduce((summary, note) => {
    const status = getSunatStatus(note)?.kind;
    if (status === 'ok') summary.accepted += 1;
    if (status === 'pending') summary.pending += 1;
    if (status === 'error') summary.error += 1;
    return summary;
  }, { accepted: 0, pending: 0, error: 0 }), [notes]);

  return (
    <div className="page-shell page-shell--dense notas-page">
      <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="eyebrow">Ajustes fiscales</p>
          <h1 className="page-title">Notas de crédito y débito</h1>
          <p className="page-subtitle">Selecciona un comprobante aceptado y prepara el ajuste con sus límites fiscales visibles.</p>
        </div>
      </header>

      <div className="mb-5 inline-flex rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-1" role="tablist" aria-label="Secciones de notas">
        <button type="button" role="tab" aria-selected={section === 'emit'} className={`segment ${section === 'emit' ? 'active' : ''}`} onClick={() => setSection('emit')}>Emitir nota</button>
        <button type="button" role="tab" aria-selected={section === 'history'} className={`segment ${section === 'history' ? 'active' : ''}`} onClick={() => setSection('history')}>Historial de notas</button>
      </div>

      {section === 'emit' ? (
        <section role="tabpanel" aria-label="Comprobantes elegibles para notas" className="panel overflow-hidden">
          <div className="border-b border-[var(--color-border)] p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="m-0 text-lg font-extrabold text-[var(--color-text)]">Comprobantes aceptados</h2>
                <p className="mt-1 text-sm text-[var(--color-text-muted)]">Facturas y boletas con CDR disponible para emitir una nota.</p>
              </div>
              <span className="document-list-table-pill"><CheckCircle2 size={14} />{sourceTotal} elegibles</span>
            </div>
            <label className="search-box mt-5 max-w-2xl">
              <Search size={16} />
              <input aria-label="Buscar comprobantes aceptados" value={sourceQuery} onChange={(event) => setSourceQuery(event.target.value)} placeholder="Buscar por serie, número, RUC o cliente..." />
            </label>
          </div>

          {sourceError ? <div className="p-5"><PageError error={sourceError} onRetry={loadSources} /></div>
            : sourceLoading ? <div className="flex min-h-64 items-center justify-center"><Spinner size="lg" /></div>
              : sourceDocuments.length === 0 ? <div className="p-5"><EmptyState variant="onboarding" icon={<ReceiptText size={22} />} title={sourceQuery ? 'No encontramos comprobantes aceptados' : 'Aún no hay comprobantes aceptados'} description={sourceQuery ? 'Prueba con otra serie, RUC o cliente.' : 'Cuando SUNAT acepte una factura o boleta, aparecerá aquí para que puedas emitir una nota.'} /></div>
                : <>
                  <div className="divide-y divide-[var(--color-border)]">
                    {sourceDocuments.map((document) => (
                      <article key={document.id} className="grid gap-4 p-5 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center">
                        <div className="grid min-w-0 gap-1 sm:grid-cols-[auto_minmax(0,1fr)_auto] sm:items-center sm:gap-x-4">
                          <DocumentTypeBadge tipo={document.tipo_comprobante} size="sm" />
                          <div className="min-w-0">
                            <p className="m-0 truncate font-mono text-sm font-extrabold text-[var(--color-text)]">{numberOf(document)}</p>
                            <p className="note-source-client mt-1 text-sm font-semibold text-[var(--color-text)]" title={clientName(document)}>{clientName(document)}</p>
                            <p className="mt-1 text-xs text-[var(--color-text-muted)]">{clientDocument(document) || 'Sin documento'} · {formatDate(document.fecha_emision)}</p>
                          </div>
                          <div className="mt-2 sm:mt-0 sm:text-right">
                            <p className="m-0 font-mono text-base font-extrabold text-[var(--color-text)]">{formatCurrency(document.total_venta, document.moneda)}</p>
                            <div className="mt-1"><NoteStatus document={document} /></div>
                          </div>
                        </div>
                        <div className="grid gap-2 sm:grid-cols-2">
                          <button type="button" className="btn-primary justify-center" onClick={() => openDrawer(document, 'credito')}><CreditCard size={16} />Nota de crédito</button>
                          <button type="button" className="btn-secondary justify-center" onClick={() => openDrawer(document, 'debito')}><FileText size={16} />Nota de débito</button>
                        </div>
                      </article>
                    ))}
                  </div>
                  <Pagination page={sourcePage} pages={sourcePages} total={sourceTotal} onChange={setSourcePage} />
                </>}
        </section>
      ) : (
        <section role="tabpanel" aria-label="Historial de notas" className="panel overflow-hidden">
          <div className="border-b border-[var(--color-border)] p-5">
            <div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="m-0 text-lg font-extrabold">Historial de notas</h2><p className="mt-1 text-sm text-[var(--color-text-muted)]">Borradores, notas en cola y documentos aceptados por SUNAT.</p></div><button type="button" className="btn-secondary" onClick={loadNotes}><RefreshCw size={15} />Actualizar</button></div>
            <div className="mt-5 grid gap-3 md:grid-cols-[minmax(0,1fr)_190px_190px]">
              <label className="search-box"><Search size={16} /><input aria-label="Buscar en el historial de notas" value={notesQuery} onChange={(event) => setNotesQuery(event.target.value)} placeholder="Buscar nota, comprobante o cliente..." /></label>
              <select className="input" aria-label="Tipo de nota" value={noteType} onChange={(event) => setNoteType(event.target.value)}>{NOTE_TYPE_FILTERS.map((filter) => <option key={filter.value} value={filter.value}>{filter.label}</option>)}</select>
              <select className="input" aria-label="Estado de nota" value={noteStatus} onChange={(event) => setNoteStatus(event.target.value)}>{STATUS_FILTERS.map((filter) => <option key={filter.value} value={filter.value}>{filter.label}</option>)}</select>
            </div>
          </div>
          {notesError ? <div className="p-5"><PageError error={notesError} onRetry={loadNotes} /></div>
            : notesLoading ? <div className="flex min-h-64 items-center justify-center"><Spinner size="lg" /></div>
              : notes.length === 0 ? <div className="p-5"><EmptyState icon={<FileText size={22} />} title="Aún no tienes notas emitidas" description="El historial aparecerá aquí cuando guardes o emitas una nota." action={<button type="button" className="btn-primary" onClick={() => setSection('emit')}>Ver comprobantes aceptados</button>} /></div>
                : <>
                  <div className="flex flex-wrap gap-2 border-b border-[var(--color-border)] px-5 py-3 text-xs text-[var(--color-text-muted)]"><span>{notesTotal} notas</span><span>·</span><span>{historySummary.accepted} aceptadas</span><span>·</span><span>{historySummary.pending} pendientes</span><span>·</span><span>{historySummary.error} observadas</span></div>
                  <div className="ink-table-scroll"><table className="ink-table ink-note-table"><thead><tr><th>Número</th><th>Tipo</th><th>Comprobante afectado</th><th>Cliente</th><th>Motivo</th><th>Estado SUNAT</th><th>Acciones</th></tr></thead><tbody>{notes.map((note) => {
                    const reference = note.nota_referencia || note.source_quote;
                    return <tr key={note.id}><td data-label="Número"><div className="ink-table-cell__primary document-list-folio">{note.estado === 'borrador' ? 'Sin correlativo' : numberOf(note)}</div><div className="ink-table-cell__meta">{formatDate(note.fecha_emision)}</div></td><td data-label="Tipo"><DocumentTypeBadge tipo={note.document_kind === 'credit_note' ? '07' : '08'} size="sm" /></td><td data-label="Comprobante afectado"><div className="ink-table-cell__primary">{reference ? numberOf(reference) : '—'}</div></td><td data-label="Cliente"><div className="ink-table-cell__primary">{clientName(note)}</div><div className="ink-table-cell__meta">{clientDocument(note)}</div></td><td data-label="Motivo"><div className="ink-table-cell__primary">{note.nota_motivo_descripcion || '—'}</div></td><td data-label="Estado SUNAT"><NoteStatus document={note} /></td><td data-label="Acciones">{note.estado === 'borrador' ? <button type="button" className="ink-row-btn" title="Continuar borrador" aria-label="Continuar borrador" onClick={() => navigate(`/notas/nueva?draft=${note.id}`)}><ArrowRight size={14} /></button> : null}</td></tr>;
                  })}</tbody></table></div>
                  <Pagination page={notesPage} pages={historyPages} total={notesTotal} onChange={setNotesPage} />
                </>}
        </section>
      )}

      <Drawer
        open={drawer.open}
        onClose={closeDrawer}
        icon={drawer.type === 'credito' ? <CreditCard size={18} /> : <FileText size={18} />}
        title={`Nota de ${drawer.type === 'credito' ? 'crédito' : 'débito'}`}
        subtitle={drawer.document ? `${numberOf(drawer.document)} · ${clientName(drawer.document)}` : ''}
        footer={<><button type="button" className="btn-secondary" onClick={closeDrawer}>Cancelar</button><button type="button" className="btn-primary" disabled={!canContinue || drawer.loading} onClick={() => navigate(`/notas/nueva?documento=${drawer.document.id}&tipo=${drawer.type}`)}>Continuar</button></>}
      >
        {drawer.loading ? <div className="flex min-h-48 items-center justify-center"><Spinner size="lg" /></div>
          : drawer.error ? <PageError error={drawer.error} onRetry={() => openDrawer(drawer.document, drawer.type)} />
            : context ? <div className="space-y-5"><section className="rounded-2xl border border-[var(--color-border)] p-4"><p className="eyebrow">Comprobante afectado</p><p className="mt-2 font-mono text-base font-extrabold">{numberOf(context.document)}</p><p className="mt-1 text-sm text-[var(--color-text-muted)]">{clientName(context.document)} · {formatCurrency(context.balance?.original, context.document?.moneda)}</p></section><dl className="space-y-3 text-sm"><div className="flex justify-between gap-4"><dt>Créditos aceptados</dt><dd>{formatCurrency(context.balance?.creditos_aceptados || 0)}</dd></div><div className="flex justify-between gap-4"><dt>Ajustes reservados</dt><dd>{formatCurrency(context.balance?.ajustes_reservados || 0)}</dd></div><div className="flex justify-between gap-4 border-t border-dashed border-[var(--color-border)] pt-3 font-extrabold"><dt>Saldo fiscal disponible</dt><dd>{formatCurrency(context.balance?.maximo_disponible || 0)}</dd></div></dl><section><h3 className="m-0 text-sm font-extrabold">Motivos disponibles</h3><p className="mt-1 text-xs text-[var(--color-text-muted)]">{Object.keys(selectedMotives).length ? `${Object.keys(selectedMotives).length} motivos SUNAT aplicables a este comprobante.` : 'Este tipo de nota no está disponible para el comprobante seleccionado.'}</p></section></div> : null}
      </Drawer>
    </div>
  );
}

function Pagination({ page, pages, total, onChange }) {
  return <div className="ink-table-footer"><span className="ink-table-count">Página <strong>{page}</strong> de <strong>{pages}</strong> · {total} registros</span><div className="pagination"><button type="button" className="page-btn" aria-label="Página anterior" disabled={page <= 1} onClick={() => onChange(page - 1)}>‹</button><span className="page-btn active" aria-current="page">{page}</span><button type="button" className="page-btn" aria-label="Página siguiente" disabled={page >= pages} onClick={() => onChange(page + 1)}>›</button></div></div>;
}
