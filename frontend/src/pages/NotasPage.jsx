import { useCallback, useEffect, useMemo, useState } from 'react';
import { ArrowRight, CheckCircle2, CreditCard, FileText, ReceiptText, RefreshCw, Search } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { api } from '../lib/utils/api';
import Drawer from '../components/ui/Drawer';
import Spinner from '../components/ui/Spinner';
import EmptyState from '../components/ui/EmptyState';
import { PageError } from '../components/ui/PageState';
import Badge from '../components/ui/Badge';
import Pagination from '../components/ui/Pagination';
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
  return document?.cliente?.numero_documento || document?.cliente?.documento || document?.cliente?.ruc || document?.cliente?.dni || '';
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
  const selectedMotivesEntries = Object.entries(selectedMotives);
  const canContinue = Boolean(context && Object.keys(selectedMotives).length);
  const isCreditNote = drawer.type === 'credito';
  const noteTypeLabel = isCreditNote ? 'crédito' : 'débito';
  const originalAmount = Number(context?.balance?.original || 0);
  const availableAmount = Number(context?.balance?.maximo_disponible || 0);
  const availablePercent = originalAmount > 0
    ? Math.min(100, Math.max(0, (availableAmount / originalAmount) * 100))
    : 0;
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
      <header className="notes-page-header">
        <div className="notes-page-header__intro">
          <p className="eyebrow">Flujo de ajuste</p>
          <h1 className="page-title">Notas de crédito y débito</h1>
          <p className="page-subtitle">Selecciona un comprobante aceptado y prepara el ajuste con sus límites fiscales visibles.</p>
        </div>
        <ol className="notes-flow" aria-label="Pasos para preparar una nota">
          <li className="is-current"><span>01</span><div><strong>Selecciona</strong><small>el comprobante</small></div></li>
          <li><span>02</span><div><strong>Define</strong><small>el ajuste</small></div></li>
          <li><span>03</span><div><strong>Revisa</strong><small>y emite</small></div></li>
        </ol>
        <div className="notes-page-tabs" role="tablist" aria-label="Secciones de notas">
          <button id="notes-emit-tab" type="button" role="tab" aria-controls="notes-emit-panel" aria-selected={section === 'emit'} className={`segment ${section === 'emit' ? 'active' : ''}`} onClick={() => setSection('emit')}>Emitir nota</button>
          <button id="notes-history-tab" type="button" role="tab" aria-controls="notes-history-panel" aria-selected={section === 'history'} className={`segment ${section === 'history' ? 'active' : ''}`} onClick={() => setSection('history')}>Historial de notas</button>
        </div>
      </header>

      {section === 'emit' ? (
        <section id="notes-emit-panel" role="tabpanel" aria-labelledby="notes-emit-tab" className="panel notes-source-panel overflow-hidden">
          <div className="notes-source-panel__header">
            <div className="notes-source-panel__heading">
              <div>
                <h2 className="m-0 text-lg font-extrabold text-[var(--color-text)]">Comprobantes aceptados</h2>
                <p className="mt-1 text-sm text-[var(--color-text-muted)]">Elige el comprobante que necesitas ajustar. La nota se prepara en el siguiente paso.</p>
              </div>
              <div className="notes-source-panel__actions">
                <span className="notes-source-ready"><CheckCircle2 size={15} aria-hidden="true" />{sourceTotal} listos para ajustar</span>
                <button type="button" className="btn-ghost notes-source-refresh" onClick={loadSources}><RefreshCw size={15} />Actualizar</button>
              </div>
            </div>
            <div className="notes-source-search-row">
              <label className="search-box notes-source-search">
                <Search size={16} />
                <input aria-label="Buscar comprobantes aceptados" value={sourceQuery} onChange={(event) => setSourceQuery(event.target.value)} placeholder="Buscar por serie, número, RUC o cliente..." />
              </label>
              <p>Solo se muestran documentos validados por SUNAT.</p>
            </div>
          </div>

          {sourceError ? <div className="p-5"><PageError error={sourceError} onRetry={loadSources} /></div>
            : sourceLoading ? <div className="flex min-h-64 items-center justify-center"><Spinner size="lg" /></div>
              : sourceDocuments.length === 0 ? <div className="p-5"><EmptyState variant="onboarding" icon={<ReceiptText size={22} />} title={sourceQuery ? 'No encontramos comprobantes aceptados' : 'Aún no hay comprobantes aceptados'} description={sourceQuery ? 'Prueba con otra serie, RUC o cliente.' : 'Cuando SUNAT acepte una factura o boleta, aparecerá aquí para que puedas emitir una nota.'} /></div>
                : <>
                  <div className="notes-source-list">
                    {sourceDocuments.map((document) => (
                      <article key={document.id} className="note-source-row">
                        <div className="note-source-document">
                          <div className="note-source-document__identity">
                            <DocumentTypeBadge tipo={document.tipo_comprobante} size="sm" />
                            <div className="min-w-0">
                              <div className="note-source-folio-row">
                                <p className="note-source-folio">{numberOf(document)}</p>
                                <span className="note-source-verified" title="Validado por SUNAT" aria-label="Validado por SUNAT"><CheckCircle2 size={14} aria-hidden="true" /></span>
                              </div>
                              <p className="note-source-client" title={clientName(document)}>{clientName(document)}</p>
                              <p className="note-source-meta">{clientDocument(document) || 'Sin documento'} <span aria-hidden="true">·</span> {formatDate(document.fecha_emision)}</p>
                            </div>
                          </div>
                          <div className="note-source-amount">
                            <span>Total emitido</span>
                            <p>{formatCurrency(document.total_venta, document.moneda)}</p>
                          </div>
                        </div>
                        <div className="note-source-actions" role="group" aria-label={`Acciones para ${numberOf(document)}`}>
                          <button type="button" className="btn-primary note-source-action" onClick={() => openDrawer(document, 'credito')}><CreditCard size={16} />Crear nota de crédito</button>
                          <button type="button" className="btn-secondary note-source-action" onClick={() => openDrawer(document, 'debito')}><FileText size={16} />Crear nota de débito</button>
                        </div>
                      </article>
                    ))}
                  </div>
                  <div className="ink-table-footer">
                    <span className="ink-table-count">Página <strong>{sourcePage}</strong> de <strong>{sourcePages}</strong> · {sourceTotal} registros</span>
                    <Pagination page={sourcePage} totalPages={sourcePages} onPageChange={setSourcePage} ariaLabel="Paginación de comprobantes para notas" />
                  </div>
                </>}
        </section>
      ) : (
        <section id="notes-history-panel" role="tabpanel" aria-labelledby="notes-history-tab" className="panel overflow-hidden">
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
                  <div className="note-history-summary" aria-label="Resumen del historial"><span><strong>{notesTotal}</strong> notas</span><span><strong>{historySummary.accepted}</strong> aceptadas</span><span><strong>{historySummary.pending}</strong> en proceso</span><span className={historySummary.error ? 'is-attention' : ''}><strong>{historySummary.error}</strong> observadas</span></div>
                  <div className="ink-table-scroll"><table className="ink-table ink-note-table"><thead><tr><th>Número</th><th>Tipo</th><th>Comprobante afectado</th><th>Cliente</th><th>Motivo</th><th>Estado SUNAT</th><th>Acciones</th></tr></thead><tbody>{notes.map((note) => {
                    const reference = note.nota_referencia || note.source_quote;
                    return <tr key={note.id}><td data-label="Número"><div className="ink-table-cell__primary document-list-folio">{note.estado === 'borrador' ? 'Sin correlativo' : numberOf(note)}</div><div className="ink-table-cell__meta">{formatDate(note.fecha_emision)}</div></td><td data-label="Tipo"><DocumentTypeBadge tipo={note.document_kind === 'credit_note' ? '07' : '08'} size="sm" /></td><td data-label="Comprobante afectado"><div className="ink-table-cell__primary">{reference ? numberOf(reference) : '—'}</div></td><td data-label="Cliente"><div className="ink-table-cell__primary">{clientName(note)}</div><div className="ink-table-cell__meta">{clientDocument(note)}</div></td><td data-label="Motivo"><div className="ink-table-cell__primary">{note.nota_motivo_descripcion || '—'}</div></td><td data-label="Estado SUNAT"><NoteStatus document={note} /></td><td data-label="Acciones">{note.estado === 'borrador' ? <button type="button" className="ink-row-btn" title="Continuar borrador" aria-label="Continuar borrador" onClick={() => navigate(`/notas/nueva?draft=${note.id}`)}><ArrowRight size={14} /></button> : null}</td></tr>;
                  })}</tbody></table></div>
                  <div className="ink-table-footer">
                    <span className="ink-table-count">Página <strong>{notesPage}</strong> de <strong>{historyPages}</strong> · {notesTotal} registros</span>
                    <Pagination page={notesPage} totalPages={historyPages} onPageChange={setNotesPage} ariaLabel="Paginación del historial de notas" />
                  </div>
                </>}
        </section>
      )}

      <Drawer
        open={drawer.open}
        onClose={closeDrawer}
        variant={`note-context note-context--${drawer.type}`}
        tone={drawer.type === 'debito' ? 'warning' : 'primary'}
        icon={drawer.type === 'credito' ? <CreditCard size={18} /> : <FileText size={18} />}
        title={`Preparar nota de ${noteTypeLabel}`}
        subtitle={drawer.document ? `Ajuste sobre ${numberOf(drawer.document)}` : ''}
        footer={<><button type="button" className="btn-ghost" onClick={closeDrawer}>Cancelar</button><button type="button" className="btn-primary" disabled={!canContinue || drawer.loading} onClick={() => navigate(`/notas/nueva?documento=${drawer.document.id}&tipo=${drawer.type}`)}>Preparar nota de {noteTypeLabel}</button></>}
      >
        {drawer.loading ? <div className="flex min-h-48 items-center justify-center"><Spinner size="lg" /></div>
          : drawer.error ? <PageError error={drawer.error} onRetry={() => openDrawer(drawer.document, drawer.type)} />
            : context ? <div className="note-context">
              <section className="note-context-document">
                <div className="note-context-document__topline"><span>Comprobante afectado</span><span className="note-context-document__verified"><CheckCircle2 size={14} aria-hidden="true" />Validado por SUNAT</span></div>
                <div className="note-context-document__main"><DocumentTypeBadge tipo={context.document?.tipo_comprobante} size="sm" /><p>{numberOf(context.document)}</p></div>
                <p className="note-context-document__client">{clientName(context.document)}</p>
                <p className="note-context-document__meta">{clientDocument(context.document) || 'Sin documento'} <span aria-hidden="true">·</span> Emitido el {formatDate(context.document?.fecha_emision)}</p>
                <div className="note-context-document__total"><span>Total original</span><strong>{formatCurrency(context.balance?.original || 0, context.document?.moneda)}</strong></div>
              </section>

              <section className="note-context-balance" aria-labelledby="note-context-balance-title">
                <div className="note-context-balance__heading"><div><p className="eyebrow">Disponibilidad fiscal</p><h3 id="note-context-balance-title">Saldo que puedes ajustar</h3></div><strong>{formatCurrency(context.balance?.maximo_disponible || 0, context.document?.moneda)}</strong></div>
                <div className="note-context-balance__bar" role="progressbar" aria-label="Saldo fiscal disponible" aria-valuemin="0" aria-valuemax={originalAmount} aria-valuenow={availableAmount}><span style={{ width: `${availablePercent}%` }} /></div>
                <dl className="note-context-balance__breakdown"><div><dt>Créditos aceptados</dt><dd>{formatCurrency(context.balance?.creditos_aceptados || 0, context.document?.moneda)}</dd></div><div><dt>Ajustes en cola</dt><dd>{formatCurrency(context.balance?.ajustes_reservados || 0, context.document?.moneda)}</dd></div></dl>
              </section>

              <section className="note-context-motives" aria-labelledby="note-context-motives-title">
                <div><p className="eyebrow">Siguiente paso</p><h3 id="note-context-motives-title">Motivos disponibles</h3></div>
                {selectedMotivesEntries.length ? <><p>Podrás elegir el motivo SUNAT y definir el ajuste en la siguiente pantalla.</p><div className="note-context-motive-list">{selectedMotivesEntries.slice(0, 4).map(([code, label]) => <span key={code}><b>{code}</b>{label}</span>)}</div>{selectedMotivesEntries.length > 4 ? <p className="note-context-motives__more">Y {selectedMotivesEntries.length - 4} motivos más disponibles.</p> : null}</> : <p className="note-context-motives__unavailable">Este tipo de nota no está disponible para el comprobante seleccionado.</p>}
              </section>
              <p className="note-context-disclaimer">Aún no se creará ni emitirá una nota. Primero revisarás y guardarás el borrador.</p>
            </div> : null}
      </Drawer>
    </div>
  );
}
