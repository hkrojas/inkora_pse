import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import {
  AlertCircle,
  Calendar,
  CheckCircle2,
  CreditCard,
  DollarSign,
  Eye,
  Search,
} from 'lucide-react';
import { cobranza } from '../services/cobranza';
import Spinner from '../components/ui/Spinner';
import { PageError } from '../components/ui/PageState';
import EmptyState from '../components/ui/EmptyState';
import { useToast } from '../components/ui/Toast';
import OperationalPageHeader from '../components/ui/OperationalPageHeader';
import Modal from '../components/ui/Modal';
import CustomSelect from '../components/ui/CustomSelect';

const AVATAR_COLORS = ['a-green', 'a-blue', 'a-purple', 'a-yellow', 'a-red'];
const PAYMENT_METHODS = ['Yape', 'Efectivo', 'Transferencia', 'BCP', 'Interbank', 'BBVA', 'Tarjeta']
  .map((method) => ({ value: method, label: method }));

function fmt(v) {
  return Number(v || 0).toLocaleString('es-PE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function fmtDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('es-PE', { day: '2-digit', month: 'short', year: 'numeric' });
}

function getAgingPill(dias) {
  const d = Number(dias ?? 0);
  if (d > 30) return { cls: 'risk',    label: `+${d}d mora` };
  if (d > 0)  return { cls: 'credit',  label: `+${d}d vencido` };
  if (d === 0) return { cls: 'person', label: 'Vence hoy' };
  return { cls: 'ok', label: `En ${Math.abs(d)}d` };
}

function getAgingAvatar(dias) {
  const d = Number(dias ?? 0);
  if (d > 30) return 'a-red';
  if (d > 0)  return 'a-yellow';
  return 'a-green';
}

function getInitials(name) {
  if (!name) return '??';
  const parts = String(name).split(/\s+/).filter(Boolean);
  if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  return parts[0].slice(0, 2).toUpperCase();
}

function getDocLabel(item) {
  if (item.internal_order_number) return item.internal_order_number;
  if (item.document_number) return item.document_number;
  if (item.serie && item.correlativo) return `${item.serie}-${String(item.correlativo).padStart(6, '0')}`;
  return `#${item.cotizacion_id || item.id}`;
}

function getClientName(item) {
  return item.cliente_nombre || item.cliente?.razon_social || item.cliente?.nombre || 'Cliente sin nombre';
}

export default function CobranzaPage() {
  const toast = useToast();
  const [searchParams] = useSearchParams();
  const [vencidas, setVencidas] = useState([]);
  const [resumen, setResumen] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState(() => searchParams.get('q') || '');
  const [segment, setSegment] = useState('all');
  const [quickPayItem, setQuickPayItem] = useState(null);
  const [quickPayMethod, setQuickPayMethod] = useState('Yape');
  const [quickPayReference, setQuickPayReference] = useState('');
  const [quickPaySaving, setQuickPaySaving] = useState(false);

  const loadCobranza = useCallback(() => {
    setLoading(true);
    setError(null);
    Promise.all([cobranza.vencidas(), cobranza.resumen()])
      .then(([vencidasRes, resumenRes]) => {
        setVencidas(Array.isArray(vencidasRes) ? vencidasRes : []);
        setResumen(resumenRes);
      })
      .catch((err) => {
        setError(err);
        toast(err.message || 'No se pudo cargar la información. Revisa tu conexión e inténtalo nuevamente.', 'error');
      })
      .finally(() => setLoading(false));
  }, [toast]);

  useEffect(() => {
    loadCobranza();
  }, [loadCobranza]);

  useEffect(() => {
    const query = searchParams.get('q') || '';
    setSearch((current) => (current === query ? current : query));
  }, [searchParams]);

  const openQuickPay = (item) => {
    setQuickPayItem(item);
    setQuickPayMethod('Yape');
    setQuickPayReference('');
  };

  const closeQuickPay = () => {
    if (quickPaySaving) return;
    setQuickPayItem(null);
    setQuickPayReference('');
  };

  const handleQuickPay = async (event) => {
    event.preventDefault();
    if (!quickPayItem) return;

    const documentId = quickPayItem.cotizacion_id || quickPayItem.id;
    const amount = Number(quickPayItem.saldo_pendiente || 0);
    if (!documentId || !Number.isFinite(amount) || amount <= 0) {
      toast('El documento ya no tiene un saldo válido para cobrar.', 'error');
      setQuickPayItem(null);
      loadCobranza();
      return;
    }

    setQuickPaySaving(true);
    try {
      await cobranza.saldar(documentId, {
        monto_pagado: amount,
        metodo_pago: quickPayMethod,
        tipo: 'pago',
        referencia_operacion: quickPayReference.trim(),
      });
      toast(`Cuenta saldada por S/ ${fmt(amount)}.`, 'success');
      setQuickPayItem(null);
      setQuickPayReference('');
      loadCobranza();
    } catch (err) {
      toast(err.message || 'No se pudo registrar el pago total. Actualiza la cobranza e inténtalo nuevamente.', 'error');
      setQuickPayItem(null);
      loadCobranza();
    } finally {
      setQuickPaySaving(false);
    }
  };

  const counts = useMemo(() => ({
    all:      vencidas.length,
    vencidos: vencidas.filter((i) => Number(i.dias_vencido ?? 0) > 0).length,
    criticos: vencidas.filter((i) => Number(i.dias_vencido ?? 0) > 30).length,
    hoy:      vencidas.filter((i) => Number(i.dias_vencido ?? 0) === 0).length,
    proximos: vencidas.filter((i) => Number(i.dias_vencido ?? 0) < 0).length,
  }), [vencidas]);

  const filtered = useMemo(() => {
    let base = vencidas;

    const q = search.trim().toLowerCase();
    if (q) {
      base = base.filter((i) =>
        [getClientName(i), i.cliente_documento, i.cliente?.numero_documento, getDocLabel(i)]
          .filter(Boolean)
          .some((v) => String(v).toLowerCase().includes(q)),
      );
    }

    if (segment === 'vencidos') return base.filter((i) => Number(i.dias_vencido ?? 0) > 0);
    if (segment === 'criticos') return base.filter((i) => Number(i.dias_vencido ?? 0) > 30);
    if (segment === 'hoy')      return base.filter((i) => Number(i.dias_vencido ?? 0) === 0);
    if (segment === 'proximos') return base.filter((i) => Number(i.dias_vencido ?? 0) < 0);
    return base;
  }, [vencidas, search, segment]);

  const segments = [
    { key: 'all',      label: `Todos ${counts.all}` },
    { key: 'vencidos', label: `Vencidos ${counts.vencidos}` },
    { key: 'criticos', label: `Críticos ${counts.criticos}` },
    { key: 'hoy',      label: `Vence hoy ${counts.hoy}` },
    { key: 'proximos', label: `Por vencer ${counts.proximos}` },
  ];

  return (
    <div className="cobranza-page">
      <OperationalPageHeader
        variant="monitoring"
        eyebrow="Seguimiento de pagos"
        title="Cobranza"
        description={`${loading ? '—' : vencidas.length} documentos en seguimiento activo.`}
        meta={<span className="operational-page-header__scope">Saldo fiscal neto por cobrar</span>}
      />

      {/* ── Stats ── */}
      <section className="stats-row ink-enter-2">
        <article className="stat">
          <div className="stat-label">Saldo total pendiente</div>
          <div className="stat-value">
            {loading ? '—' : `S/ ${fmt(resumen?.total_por_cobrar)}`}
          </div>
          <div className="stat-foot warn">Todos los documentos pendientes</div>
        </article>
        <article className="stat">
          <div className="stat-label">Docs. vencidos</div>
          <div className="stat-value">
            {loading ? '—' : (resumen?.documentos_vencidos ?? counts.vencidos)}
          </div>
          <div className="stat-foot bad">Acción inmediata requerida</div>
        </article>
        <article className="stat">
          <div className="stat-label">Cobrado este mes</div>
          <div className="stat-value">
            {loading ? '—' : `S/ ${fmt(resumen?.total_pagado_mes)}`}
          </div>
          <div className="stat-foot good">Monto recuperado</div>
        </article>
        <article className="stat">
          <div className="stat-label">En seguimiento</div>
          <div className="stat-value">{loading ? '—' : vencidas.length}</div>
          <div className="stat-foot">Documentos monitoreados</div>
        </article>
      </section>

      {/* ── Panel principal ── */}
      <article className="panel ink-enter-3">
        <div className="toolbar">
          <label className="search-box">
            <Search size={16} />
            <input
              placeholder="Buscar por cliente o numero de documento..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </label>
          <div className="toolbar-actions">
            <div className="cobranza-aging-legend">
              <span className="pill risk">Critico &gt;30d</span>
              <span className="pill credit">Vencido</span>
              <span className="pill person">Vence hoy</span>
              <span className="pill ok">Al dia</span>
            </div>
          </div>
        </div>

        <div className="segments-row">
          <div className="segments">
            {segments.map(({ key, label }) => (
              <button
                key={key}
                type="button"
                className={`segment ${segment === key ? 'active' : ''}`}
                onClick={() => setSegment(key)}
              >
                {label}
              </button>
            ))}
          </div>
          <div className="sort-text">
            Ordenar por: <strong>Dias de mora</strong>
          </div>
        </div>

        {error ? (
          <div style={{ padding: '40px 18px' }}>
            <PageError error={error} onRetry={loadCobranza} />
          </div>
        ) : loading ? (
          <div style={{ padding: '40px 18px' }}>
            <Spinner />
          </div>
        ) : filtered.length === 0 ? (
          <div style={{ padding: '40px 18px' }}>
            <EmptyState
              title="Sin vencimientos"
              description={
                search || segment !== 'all'
                  ? 'No hay resultados con los filtros actuales.'
                  : 'No hay documentos en seguimiento de cobranza.'
              }
            />
          </div>
        ) : (
          <>
            <div className="cobranza-list">
              <div className="cobranza-list-head">
                <div>Cliente / Documento</div>
                <div>Vencimiento</div>
                <div>Saldo pendiente</div>
                <div>Mora</div>
                <div style={{ textAlign: 'right' }}>Accion</div>
              </div>

              {filtered.map((item) => {
                const aging = getAgingPill(item.dias_vencido);
                const avatarColor = getAgingAvatar(item.dias_vencido);
                const dias = Number(item.dias_vencido ?? 0);
                return (
                  <div key={item.cotizacion_id || item.id} className="cobranza-row">
                    <div className="client-main">
                      <div className={`client-avatar ${avatarColor}`}>
                        {getInitials(getClientName(item))}
                      </div>
                      <div style={{ minWidth: 0 }}>
                        <div className="client-name">{getClientName(item)}</div>
                        <div className="meta" style={{ fontFamily: 'var(--font-mono)', fontSize: '11px' }}>
                          {getDocLabel(item)}
                        </div>
                      </div>
                    </div>

                    <div className="contact-block">
                      <strong style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                        <Calendar size={12} style={{ flexShrink: 0, color: 'var(--color-text-muted)' }} />
                        {fmtDate(item.fecha_vencimiento)}
                      </strong>
                    </div>

                    <div className="activity-block">
                      <strong
                        style={{
                          fontSize: '15px',
                          color: dias > 0 ? 'var(--color-danger)' : 'var(--color-text)',
                        }}
                      >
                        S/ {fmt(item.saldo_pendiente)}
                      </strong>
                      {dias > 0 && (
                        <span style={{ color: 'var(--color-danger)', fontSize: '11px' }}>
                          Con mora acumulada
                        </span>
                      )}
                    </div>

                    <div>
                      <span className={`pill ${aging.cls}`}>{aging.label}</span>
                    </div>

                    <div className="actions-col">
                      <button
                        type="button"
                        className="cobranza-quick-pay-btn"
                        onClick={() => openQuickPay(item)}
                        aria-label={`Saldar ${getDocLabel(item)} por S/ ${fmt(item.saldo_pendiente)}`}
                      >
                        <CheckCircle2 size={14} aria-hidden="true" />
                        Saldar
                      </button>
                      <Link
                        to={`/cotizaciones/${item.cotizacion_id || item.id}`}
                        className="edit-btn"
                        aria-label={`Ver detalle de ${getDocLabel(item)}`}
                      >
                        <Eye size={13} />
                        Ver
                      </Link>
                      <Link
                        to={`/cotizaciones/${item.cotizacion_id || item.id}`}
                        className="more-btn"
                        title="Registrar pago manual"
                        aria-label={`Registrar pago manual de ${getDocLabel(item)}`}
                      >
                        <DollarSign size={14} />
                      </Link>
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="table-footer">
              <div>
                Mostrando <strong>{filtered.length}</strong> de{' '}
                <strong>{vencidas.length}</strong> documentos
              </div>
              <div className="cobranza-total-footer">
                <AlertCircle size={13} style={{ color: 'var(--color-danger)' }} />
                <span>
                  Saldo de los {filtered.length} documentos visibles:{' '}
                  <strong>
                    S/{' '}
                    {fmt(filtered.reduce((sum, i) => sum + Number(i.saldo_pendiente || 0), 0))}
                  </strong>
                </span>
              </div>
            </div>
          </>
        )}
      </article>

      <Modal
        open={Boolean(quickPayItem)}
        onClose={closeQuickPay}
        title="Saldar cuenta"
        subtitle="Registra el saldo completo sin digitar el importe."
        icon={CreditCard}
        size="sm"
      >
        {quickPayItem && (
          <form onSubmit={handleQuickPay} className="cobranza-quick-pay-form">
            <div className="cobranza-quick-pay-summary">
              <div>
                <span>Cliente</span>
                <strong>{getClientName(quickPayItem)}</strong>
                <small>{getDocLabel(quickPayItem)}</small>
              </div>
              <div className="cobranza-quick-pay-amount">
                <span>Total a saldar</span>
                <strong>S/ {fmt(quickPayItem.saldo_pendiente)}</strong>
              </div>
            </div>

            <label className="cobranza-quick-pay-field">
              <span>Método de pago</span>
              <CustomSelect
                value={quickPayMethod}
                onChange={setQuickPayMethod}
                options={PAYMENT_METHODS}
                ariaLabel="Método de pago para saldar la cuenta"
              />
            </label>

            <label className="cobranza-quick-pay-field">
              <span>Referencia <small>(opcional)</small></span>
              <input
                className="input"
                value={quickPayReference}
                onChange={(event) => setQuickPayReference(event.target.value)}
                placeholder="Número de operación"
              />
            </label>

            <p className="cobranza-quick-pay-notice">
              <AlertCircle size={15} aria-hidden="true" />
              Este pago dejará el saldo fiscal del documento en S/ 0.00.
            </p>

            <div className="responsive-form-actions">
              <button type="button" className="btn-secondary" onClick={closeQuickPay} disabled={quickPaySaving}>
                Cancelar
              </button>
              <button type="submit" className="btn-primary" disabled={quickPaySaving}>
                {quickPaySaving ? <Spinner size={14} /> : <CheckCircle2 size={15} aria-hidden="true" />}
                {quickPaySaving ? 'Registrando...' : `Confirmar S/ ${fmt(quickPayItem.saldo_pendiente)}`}
              </button>
            </div>
          </form>
        )}
      </Modal>
    </div>
  );
}
