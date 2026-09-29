import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertCircle,
  ArrowRight,
  CalendarDays,
  CircleDollarSign,
  Clock3,
  PackageSearch,
  Plus,
  ReceiptText,
  ShoppingBag,
  TrendingDown,
  TrendingUp,
  UsersRound,
} from 'lucide-react';
import Spinner from '../components/ui/Spinner';
import { dashboard } from '../services/dashboard';
import '../styles/dashboardMockup.css';

const MONTH_NAMES = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
];
const MONTH_SHORT = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
const FOLLOW_UP_LABELS = {
  quotes: 'Cotizaciones sin una venta',
  declining: 'Compraron menos',
  inactive: 'Sin compras en 60 días',
};
const UNAVAILABLE_REASON = 'Inkora aún no puede distinguir las cotizaciones comerciales de las creadas al emitir un comprobante.';

function asNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : 0;
}

function formatMoney(value, currency = 'PEN') {
  const amount = asNumber(value);
  const symbol = currency === 'USD' ? '$' : 'S/';
  const hasCents = Math.abs(amount % 1) > 0.0001;
  return `${symbol} ${new Intl.NumberFormat('es-PE', {
    minimumFractionDigits: hasCents ? 2 : 0,
    maximumFractionDigits: 2,
  }).format(amount)}`;
}

function formatPercent(value) {
  if (value === null || value === undefined) return null;
  const number = asNumber(value);
  if (number === 0) return '0 %';
  const sign = number > 0 ? '+' : '−';
  return `${sign}${new Intl.NumberFormat('es-PE', { maximumFractionDigits: 1 }).format(Math.abs(number))} %`;
}

function formatQuantity(value, unit) {
  const quantity = asNumber(value);
  return `${new Intl.NumberFormat('es-PE', { maximumFractionDigits: 4 }).format(quantity)} ${unit || 'NIU'}`;
}

function parseDate(value) {
  if (!value) return null;
  const dateOnly = /^\d{4}-\d{2}-\d{2}$/.test(value);
  const parsed = new Date(dateOnly ? `${value}T00:00:00` : value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function formatDate(value, options = {}) {
  const parsed = parseDate(value);
  if (!parsed) return 'Sin fecha';
  return new Intl.DateTimeFormat('es-PE', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    ...options,
  }).format(parsed);
}

function formatPeriod(period) {
  if (!period?.start || !period?.end) return 'Periodo no disponible';
  const start = parseDate(period.start);
  const end = parseDate(period.end);
  if (!start || !end) return period.label || 'Periodo no disponible';
  const sameMonth = start.getFullYear() === end.getFullYear() && start.getMonth() === end.getMonth();
  if (sameMonth) {
    return `${start.getDate()}–${end.getDate()} ${MONTH_SHORT[end.getMonth()].toLowerCase()} ${end.getFullYear()}`;
  }
  return `${formatDate(period.start)} – ${formatDate(period.end)}`;
}

function formatUpdated(value) {
  const parsed = parseDate(value);
  if (!parsed) return 'Actualización no disponible';
  return `Actualizado ${new Intl.DateTimeFormat('es-PE', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'America/Lima',
  }).format(parsed)}`;
}

function buildPath(path, params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') query.set(key, value);
  });
  return query.size ? `${path}?${query.toString()}` : path;
}

function monthBounds(point) {
  const month = String(point.month).padStart(2, '0');
  const lastDay = new Date(point.year, point.month, 0).getDate();
  const endDay = point.is_partial && point.cutoff_day ? point.cutoff_day : lastDay;
  return {
    desde: `${point.year}-${month}-01`,
    hasta: `${point.year}-${month}-${String(endDay).padStart(2, '0')}`,
  };
}

function isEmptyDashboard(data) {
  if (!data) return true;
  const summary = data.summary || {};
  const followUp = data.follow_up || {};
  return asNumber(summary.sales_amount) === 0
    && asNumber(summary.pending_sunat_amount) === 0
    && asNumber(summary.overdue_amount) === 0
    && (data.products || []).length === 0
    && (data.clients || []).length === 0
    && asNumber(followUp.declining?.count) === 0
    && asNumber(followUp.inactive?.count) === 0
    && asNumber(data.pending?.low_stock_products) === 0
    && asNumber(data.pending?.fiscal_documents_with_errors) === 0;
}

function ScopeChip({ children, icon: Icon, wide = false }) {
  return (
    <span className={`business-dashboard__filter${wide ? ' business-dashboard__filter--wide' : ''}`}>
      {Icon && <Icon aria-hidden="true" size={16} strokeWidth={2} />}
      <span>{children}</span>
    </span>
  );
}

function AnimatedMetricValue({ value, currency = null, delay = 0 }) {
  const target = asNumber(value);
  const [displayValue, setDisplayValue] = useState(target);

  useEffect(() => {
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduceMotion) {
      setDisplayValue(target);
      return undefined;
    }

    let frameId;
    let startTime;
    const duration = 720;
    setDisplayValue(0);
    const startTimer = window.setTimeout(() => {
      const animate = (time) => {
        if (!startTime) startTime = time;
        const progress = Math.min((time - startTime) / duration, 1);
        const eased = 1 - ((1 - progress) ** 4);
        setDisplayValue(target * eased);
        if (progress < 1) frameId = window.requestAnimationFrame(animate);
      };
      frameId = window.requestAnimationFrame(animate);
    }, delay);

    return () => {
      window.clearTimeout(startTimer);
      window.cancelAnimationFrame(frameId);
    };
  }, [delay, target]);

  const formatted = currency
    ? formatMoney(displayValue, currency)
    : new Intl.NumberFormat('es-PE', { maximumFractionDigits: 0 }).format(displayValue);
  const finalValue = currency
    ? formatMoney(target, currency)
    : new Intl.NumberFormat('es-PE', { maximumFractionDigits: 0 }).format(target);

  return <span aria-label={finalValue}><span aria-hidden="true">{formatted}</span></span>;
}

function MetricCard({ item, index }) {
  const Icon = item.icon;
  const TrendIcon = item.trendValue < 0 ? TrendingDown : TrendingUp;
  return (
    <article className={`business-metric business-metric--${item.tone}`} style={{ '--metric-order': index }}>
      <div className="business-metric__topline">
        <span className="business-metric__icon"><Icon aria-hidden="true" size={20} strokeWidth={2.1} /></span>
        <span className="business-metric__label">{item.label}</span>
      </div>
      <p className="business-metric__value">
        <AnimatedMetricValue value={item.value} currency={item.currency} delay={170 + (index * 75)} />
      </p>
      {item.trend ? (
        <p className={`business-metric__trend${item.trendValue < 0 ? ' is-negative' : ''}`}>
          <TrendIcon aria-hidden="true" size={15} />
          <strong>{item.trend}</strong>
          <span>{item.trendLabel}</span>
        </p>
      ) : (
        <p className="business-metric__detail">{item.detail}</p>
      )}
      {item.trend && <p className="business-metric__detail">{item.detail}</p>}
      {item.note && (
        <p className="business-metric__note">
          <Clock3 aria-hidden="true" size={14} />
          {item.note}
        </p>
      )}
    </article>
  );
}

function buildPoints(values, width, height, maxValue) {
  const padding = { left: 58, right: 20, top: 22, bottom: 44 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  return values.map((value, index) => ({
    value,
    x: values.length === 1 ? padding.left + (plotWidth / 2) : padding.left + (index * plotWidth) / (values.length - 1),
    y: padding.top + plotHeight - (value / maxValue) * plotHeight,
  }));
}

function pathFromPoints(points) {
  return points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`).join(' ');
}

function chartScale(values) {
  const maximum = Math.max(...values, 1);
  const roughStep = maximum / 4;
  const magnitude = 10 ** Math.floor(Math.log10(roughStep));
  const normalized = roughStep / magnitude;
  const multiplier = normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10;
  const step = multiplier * magnitude;
  return { maxValue: step * 4, ticks: [0, step, step * 2, step * 3, step * 4] };
}

function formatAxis(value, currency) {
  if (value === 0) return formatMoney(0, currency);
  if (value >= 1000) return `${currency === 'USD' ? '$' : 'S/'} ${new Intl.NumberFormat('es-PE', { maximumFractionDigits: 1 }).format(value / 1000)} mil`;
  return formatMoney(value, currency);
}

function SalesChart({ history, currency, onExploreMonth }) {
  const [activePoint, setActivePoint] = useState(null);
  const width = 920;
  const height = 320;
  const plotTop = 22;
  const plotBottom = height - 44;
  const plotHeight = plotBottom - plotTop;
  const salesValues = useMemo(() => history.map((point) => asNumber(point.sales_amount)), [history]);
  const { maxValue, ticks: yTicks } = useMemo(() => chartScale(salesValues), [salesValues]);
  const salesPoints = useMemo(() => buildPoints(salesValues, width, height, maxValue), [salesValues, maxValue]);
  const latestIndex = history.length - 1;
  const latest = history[latestIndex];
  const latestPoint = salesPoints[latestIndex];
  const highlightWidth = Math.min(96, (width - 78) / Math.max(history.length, 1));
  const highlightX = Math.max(58, Math.min((latestPoint?.x || 58) - (highlightWidth / 2), 900 - highlightWidth));
  const description = history.map((point, index) => (
    `${MONTH_NAMES[point.month - 1]} ${point.year}: ${formatMoney(salesValues[index], currency)}`
  )).join('. ');

  return (
    <div className="business-chart" role="region" aria-labelledby="sales-chart-title" aria-describedby="sales-chart-description">
      <p id="sales-chart-description" className="sr-only">Historial mensual de ventas. {description}.</p>
      <div className="business-chart__viewport">
        <div className="business-chart__canvas">
          <svg className="business-chart__svg" viewBox={`0 0 ${width} ${height}`} aria-hidden="true">
            <defs>
              <linearGradient id="salesArea" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor="var(--dashboard-green)" stopOpacity="0.17" />
                <stop offset="100%" stopColor="var(--dashboard-green)" stopOpacity="0" />
              </linearGradient>
            </defs>
            {latestPoint && <rect className="business-chart__current" x={highlightX} y={plotTop} width={highlightWidth} height={plotHeight} rx="10" />}
            {yTicks.map((tick) => {
              const y = plotTop + plotHeight - (tick / maxValue) * plotHeight;
              return (
                <g key={tick}>
                  <line className="business-chart__grid" x1="58" x2="900" y1={y} y2={y} />
                  <text className="business-chart__axis-label" x="48" y={y + 4} textAnchor="end">{formatAxis(tick, currency)}</text>
                </g>
              );
            })}
            {salesPoints.length > 0 && (
              <>
                <path className="business-chart__area" d={`${pathFromPoints(salesPoints)} L ${salesPoints.at(-1).x} ${plotBottom} L ${salesPoints[0].x} ${plotBottom} Z`} />
                <path className="business-chart__line business-chart__line--sales" d={pathFromPoints(salesPoints)} pathLength="1" />
              </>
            )}
            {salesPoints.map((point, index) => (
              <g key={`${history[index].year}-${history[index].month}`} className={activePoint === index ? 'is-active' : ''}>
                <circle className="business-chart__point-halo" cx={point.x} cy={point.y} r="8" />
                <circle className="business-chart__point business-chart__point--sales" cx={point.x} cy={point.y} r="4.5" />
                <text className="business-chart__month" x={point.x} y="306" textAnchor="middle">{MONTH_SHORT[history[index].month - 1]}</text>
              </g>
            ))}
            {latestPoint && (
              <text className="business-chart__current-label" x={latestPoint.x} y="40" textAnchor="middle">
                <tspan x={latestPoint.x}>{MONTH_NAMES[latest.month - 1]}</tspan>
                {latest.is_partial && <tspan x={latestPoint.x} dy="12">hasta el día {latest.cutoff_day}</tspan>}
              </text>
            )}
          </svg>
          {salesPoints.map((point, index) => {
            const item = history[index];
            return (
              <button
                key={`hotspot-${item.year}-${item.month}`}
                className="business-chart__hotspot"
                type="button"
                style={{
                  '--point-x': `${(point.x / width) * 100}%`,
                  '--point-y': `${(point.y / height) * 100}%`,
                  width: `${Math.min(32, 90 / Math.max(history.length, 1))}%`,
                }}
                aria-label={`${MONTH_NAMES[item.month - 1]} ${item.year}: ventas ${formatMoney(item.sales_amount, currency)}. Abrir lista filtrada.`}
                aria-describedby={activePoint === index ? 'business-chart-tooltip' : undefined}
                onMouseEnter={() => setActivePoint(index)}
                onMouseLeave={() => setActivePoint(null)}
                onFocus={() => setActivePoint(index)}
                onBlur={() => setActivePoint(null)}
                onClick={() => onExploreMonth(item)}
              />
            );
          })}
          {activePoint !== null && history[activePoint] && (
            <div
              id="business-chart-tooltip"
              className={`business-chart__tooltip${salesPoints[activePoint].y < 105 ? ' business-chart__tooltip--below' : ''}`}
              style={{
                '--tooltip-x': `${(salesPoints[activePoint].x / width) * 100}%`,
                '--tooltip-y': `${(salesPoints[activePoint].y / height) * 100}%`,
              }}
              role="tooltip"
            >
              <strong>
                {MONTH_NAMES[history[activePoint].month - 1]} {history[activePoint].year}
                {history[activePoint].is_partial ? ` · hasta el día ${history[activePoint].cutoff_day}` : ''}
              </strong>
              <span><i className="business-chart__tooltip-dot business-chart__tooltip-dot--sales" />Ventas registradas <b>{formatMoney(history[activePoint].sales_amount, currency)}</b></span>
              {history[activePoint].previous_matched_sales !== null && history[activePoint].previous_matched_sales !== undefined && (
                <span className="business-chart__tooltip-compare">
                  Mismo tramo anterior <b>{formatMoney(history[activePoint].previous_matched_sales, currency)}</b>
                </span>
              )}
            </div>
          )}
        </div>
      </div>
      <div className="business-chart__legend" aria-hidden="true">
        <span><i className="business-chart__legend-line business-chart__legend-line--sales" />Ventas totales</span>
      </div>
    </div>
  );
}

function RankingTable({ type, rows, currency, onExplore }) {
  const navigate = useNavigate();
  const isProducts = type === 'products';
  const [productOrder, setProductOrder] = useState('sales');
  const visibleRows = useMemo(() => {
    if (!isProducts) return rows.slice(0, 3);
    const sorted = [...rows];
    if (productOrder === 'decline') {
      sorted.sort((a, b) => {
        if (a.change_percent === null || a.change_percent === undefined) return 1;
        if (b.change_percent === null || b.change_percent === undefined) return -1;
        return asNumber(a.change_percent) - asNumber(b.change_percent);
      });
    } else {
      sorted.sort((a, b) => asNumber(b.amount) - asNumber(a.amount));
    }
    return sorted.slice(0, 3);
  }, [isProducts, productOrder, rows]);
  const decliningProduct = rows
    .filter((row) => row.change_percent !== null && asNumber(row.change_percent) < 0)
    .sort((a, b) => asNumber(a.change_percent) - asNumber(b.change_percent))[0];
  const leadingClient = rows[0];

  return (
    <section className="business-panel business-ranking">
      <div className="business-panel__heading business-panel__heading--compact">
        <div>
          <h2>{isProducts ? 'Productos más vendidos' : 'Clientes que más compran'}</h2>
          <p>{isProducts ? 'Ordenados por venta en soles' : 'Compras dentro del periodo analizado'}</p>
        </div>
        <div className="business-ranking__actions">
          {isProducts && (
            <label className="business-ranking__sort">
              <span className="sr-only">Ordenar productos</span>
              <select aria-label="Ordenar productos" value={productOrder} onChange={(event) => setProductOrder(event.target.value)}>
                <option value="sales">Mayor venta</option>
                <option value="decline">Mayor caída</option>
              </select>
            </label>
          )}
          <button className="business-link" type="button" onClick={() => navigate(isProducts ? '/productos' : '/clientes')}>
            Ver todos <ArrowRight aria-hidden="true" size={15} />
          </button>
        </div>
      </div>
      <div className="business-ranking__table-wrap">
        <table>
          <thead>
            <tr>
              <th>{isProducts ? 'Producto' : 'Cliente'}</th>
              <th>{isProducts ? 'Cantidad' : 'Ventas'}</th>
              <th>{isProducts ? 'Ventas' : 'Compras'}</th>
              <th>{isProducts ? 'Cambio' : 'Última compra'}</th>
            </tr>
          </thead>
          <tbody>
            {visibleRows.length === 0 && (
              <tr><td colSpan="4" className="business-table__empty">No hay datos en este periodo.</td></tr>
            )}
            {visibleRows.map((row) => {
              const change = formatPercent(row.change_percent);
              const positive = asNumber(row.change_percent) >= 0;
              return (
                <tr key={`${type}-${row.id ?? row.name}`}>
                  <td data-label={isProducts ? 'Producto' : 'Cliente'}>
                    <button className="business-ranking__entity" type="button" onClick={() => onExplore(row)}>{row.name}</button>
                  </td>
                  <td data-label={isProducts ? 'Cantidad' : 'Ventas'}>{isProducts ? formatQuantity(row.quantity, row.unit) : formatMoney(row.amount, currency)}</td>
                  <td data-label={isProducts ? 'Ventas' : 'Compras'}>{isProducts ? formatMoney(row.amount, currency) : row.purchases}</td>
                  <td data-label={isProducts ? 'Cambio' : 'Última compra'}>
                    {isProducts ? (
                      change ? (
                        <span className={`business-ranking__change ${positive ? 'is-positive' : 'is-negative'}`}>
                          {positive ? <TrendingUp aria-hidden="true" size={14} /> : <TrendingDown aria-hidden="true" size={14} />}
                          {change}
                        </span>
                      ) : 'Sin base anterior'
                    ) : formatDate(row.last_purchase)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {visibleRows.length > 0 && (
        <p className={`business-ranking__insight${isProducts ? ' business-ranking__insight--neutral' : ''}`}>
          {isProducts
            ? decliningProduct
              ? `Las ventas de ${decliningProduct.name} bajaron ${Math.abs(asNumber(decliningProduct.change_percent)).toLocaleString('es-PE', { maximumFractionDigits: 1 })} %.`
              : 'No se registran caídas comparables entre los productos mostrados.'
            : `${leadingClient.name} representa ${asNumber(leadingClient.share_percent).toLocaleString('es-PE', { maximumFractionDigits: 1 })} % de las ventas.`}
        </p>
      )}
    </section>
  );
}

function DashboardState({ kind, onRetry }) {
  if (kind === 'loading') {
    return (
      <section className="business-panel business-dashboard__state">
        <Spinner size="lg" label="Cargando resumen" hint="Consultando ventas, clientes y pendientes." />
      </section>
    );
  }
  if (kind === 'error') {
    return (
      <section className="business-panel business-dashboard__state" role="alert">
        <AlertCircle aria-hidden="true" size={30} />
        <div><h2>No pudimos cargar el resumen</h2><p>Revisa la conexión e inténtalo nuevamente.</p></div>
        <button className="business-button business-button--primary" type="button" onClick={onRetry}>Reintentar</button>
      </section>
    );
  }
  return null;
}

export default function DashboardMockup() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [status, setStatus] = useState('loading');
  const [reloadKey, setReloadKey] = useState(0);
  const [activeFollowUp, setActiveFollowUp] = useState('quotes');
  const requestRef = useRef(null);
  const abortTimerRef = useRef(null);

  useEffect(() => {
    if (abortTimerRef.current) window.clearTimeout(abortTimerRef.current);
    let active = true;
    setStatus('loading');
    if (!requestRef.current || requestRef.current.key !== reloadKey) {
      const controller = new AbortController();
      requestRef.current = {
        key: reloadKey,
        controller,
        promise: dashboard.business({}, { signal: controller.signal }),
      };
    }
    const request = requestRef.current;
    request.promise
      .then((payload) => {
        if (!active) return;
        if (!payload?.meta || !payload?.summary || !Array.isArray(payload.history)) {
          throw new Error('El dashboard devolvió una respuesta incompleta.');
        }
        setData(payload);
        setStatus('ready');
      })
      .catch((error) => {
        if (!error?.isCanceled) setStatus('error');
      });
    return () => {
      active = false;
      abortTimerRef.current = window.setTimeout(() => {
        if (requestRef.current === request) {
          request.controller.abort('dashboard-unmounted');
          requestRef.current = null;
        }
      }, 0);
    };
  }, [reloadKey]);

  if (status !== 'ready') {
    return (
      <div className="business-dashboard" data-testid="dashboard-business-mockup">
        <DashboardState kind={status} onRetry={() => setReloadKey((value) => value + 1)} />
      </div>
    );
  }

  const { meta, summary, conversion, pending } = data;
  const currency = meta.currency || 'PEN';
  const periodLabel = formatPeriod(meta.period);
  const comparisonLabel = formatPeriod(meta.comparison);
  const historyLabel = formatPeriod(meta.history);
  const salesTrend = formatPercent(summary.sales_change_percent);
  const kpis = [
    {
      label: 'Ventas registradas',
      value: summary.sales_amount,
      currency,
      detail: `${summary.sales_count} ${summary.sales_count === 1 ? 'venta registrada' : 'ventas registradas'}`,
      trend: salesTrend,
      trendValue: asNumber(summary.sales_change_percent),
      trendLabel: `vs. ${comparisonLabel}`,
      note: asNumber(summary.pending_sunat_amount) > 0
        ? `De este total, ${formatMoney(summary.pending_sunat_amount, currency)} esperan respuesta de SUNAT.`
        : 'No hay ventas esperando respuesta de SUNAT.',
      icon: ShoppingBag,
      tone: 'success',
    },
    {
      label: 'Clientes que compraron',
      value: summary.customers_count,
      detail: `${summary.new_customers_count} nuevos · ${summary.returning_customers_count} que volvieron`,
      icon: UsersRound,
      tone: 'primary',
    },
    {
      label: 'Promedio por venta',
      value: summary.average_sale,
      currency,
      detail: 'Por cada venta registrada',
      icon: ReceiptText,
      tone: 'primary',
    },
    {
      label: 'Por cobrar fuera de plazo',
      value: summary.overdue_amount,
      currency,
      detail: `${summary.overdue_customers_count} ${summary.overdue_customers_count === 1 ? 'cliente' : 'clientes'} · al día de hoy`,
      icon: CircleDollarSign,
      tone: 'danger',
    },
  ];
  const followUp = data.follow_up || {};
  const activeGroup = followUp[activeFollowUp] || { available: true, count: 0, rows: [] };
  const activeRows = activeGroup.rows || [];
  const activeFollowUpLabels = activeFollowUp === 'quotes'
    ? { action: 'Ver cotización', all: 'Ver todas las cotizaciones' }
    : { action: 'Ver cliente', all: 'Ver todos los clientes' };
  const noData = isEmptyDashboard(data);

  const openMonth = (point) => navigate(buildPath('/cotizaciones', {
    view: 'fiscal',
    ...monthBounds(point),
    moneda: currency,
  }));
  const openProduct = (row) => navigate(buildPath('/productos', { q: row.name, product_id: row.id }));
  const openClient = (row) => navigate(buildPath('/clientes', { q: row.name, client_id: row.id }));
  const openFollowUpRow = (row) => {
    if (activeFollowUp === 'quotes') navigate(buildPath('/cotizaciones', { q: row.reference }));
    else navigate(buildPath('/clientes', { q: row.client, client_id: row.client_id }));
  };
  const openFollowUpAll = () => navigate(activeFollowUp === 'quotes' ? '/cotizaciones' : '/clientes');

  return (
    <div className="business-dashboard" data-testid="dashboard-business-mockup">
      <header className="business-dashboard__intro ink-enter-1">
        <div>
          <span className="business-dashboard__rule" aria-hidden="true" />
          <div className="business-dashboard__title-row"><h1>Tu negocio, de un vistazo</h1></div>
          <p>Ventas, clientes y oportunidades para decidir qué hacer hoy.</p>
        </div>
        <div className="business-dashboard__updated">
          <span>{formatUpdated(meta.generated_at)}</span>
          <small>Comparado con {comparisonLabel}</small>
        </div>
      </header>

      <section className="business-dashboard__filters ink-enter-2" aria-label="Filtros del resumen">
        <div className="business-dashboard__filter-label">
          <span>Periodo analizado</span>
          <ScopeChip icon={CalendarDays} wide>{periodLabel}</ScopeChip>
        </div>
        <ScopeChip>{meta.client_id ? `Cliente #${meta.client_id}` : 'Todos los clientes'}</ScopeChip>
        <ScopeChip>{meta.product_id ? `Producto #${meta.product_id}` : 'Todos los productos'}</ScopeChip>
        <ScopeChip>Moneda: {currency === 'PEN' ? 'Soles' : currency}</ScopeChip>
        <p className="business-dashboard__currency-note">Los importes muestran únicamente operaciones registradas en soles.</p>
      </section>

      {noData ? (
        <section className="business-panel business-dashboard__state business-dashboard__state--empty">
          <ReceiptText aria-hidden="true" size={34} />
          <div>
            <h2>Aún no hay actividad para mostrar</h2>
            <p>Cuando registres ventas, clientes o movimientos pendientes, el resumen aparecerá aquí.</p>
          </div>
          <button className="business-button business-button--primary" type="button" onClick={() => navigate('/comprobantes/nuevo')}>Registrar venta</button>
        </section>
      ) : (
        <>
          <section className="business-dashboard__metrics ink-enter-3" aria-label="Indicadores del negocio">
            {kpis.map((item, index) => <MetricCard key={item.label} item={item} index={index} />)}
          </section>

          <section className="business-panel business-sales ink-enter-4">
            <div className="business-panel__heading business-sales__heading">
              <div><h2 id="sales-chart-title">Ventas</h2><p>Ventas registradas en Inkora</p></div>
              <div className="business-sales__controls">
                <span className="business-sales__range-label">Historial</span>
                <ScopeChip>{historyLabel}</ScopeChip>
                <ScopeChip>Por mes</ScopeChip>
                <label className="business-toggle is-disabled" title={UNAVAILABLE_REASON}>
                  <input type="checkbox" checked={false} disabled />
                  <span className="business-toggle__track" aria-hidden="true"><span /></span>
                  <span>Importe cotizado no disponible</span>
                </label>
              </div>
            </div>
            <SalesChart history={data.history} currency={currency} onExploreMonth={openMonth} />
            <p className="business-sales__footnote">Incluye IGV. Descuenta notas de crédito y suma notas de débito.</p>
            <div className="business-sales__conversion">
              <div className="business-sales__conversion-rate">
                <strong>{conversion.available ? formatPercent(conversion.rate_percent) : '—'}</strong>
                <span>{conversion.available ? 'Terminaron en venta' : 'Conversión no disponible'}</span>
              </div>
              <div className="business-sales__conversion-copy">
                {conversion.available ? (
                  <>
                    <strong>{conversion.linked_sales_count} de {conversion.quote_count} cotizaciones terminaron en venta.</strong>
                    <span>Resultado actualizado con el periodo analizado.</span>
                  </>
                ) : (
                  <><strong>{UNAVAILABLE_REASON}</strong><span>Las ventas mostradas arriba sí provienen de registros reales.</span></>
                )}
              </div>
            </div>
          </section>

          <div className="business-dashboard__rankings ink-enter-5">
            <RankingTable type="products" rows={data.products || []} currency={currency} onExplore={openProduct} />
            <RankingTable type="clients" rows={data.clients || []} currency={currency} onExplore={openClient} />
          </div>

          <section className="business-panel business-followup ink-enter-6">
            <div className="business-panel__heading">
              <div><h2>Para hacer seguimiento</h2><p>Señales comerciales calculadas con la actividad registrada.</p></div>
              <button className="business-button business-button--primary" type="button" onClick={() => navigate('/cotizaciones')}>
                Crear cotización <Plus aria-hidden="true" size={16} />
              </button>
            </div>
            <div className="business-followup__tabs" role="tablist" aria-label="Tipos de seguimiento">
              {Object.entries(FOLLOW_UP_LABELS).map(([key, label]) => {
                const group = followUp[key] || { available: true, count: 0 };
                return (
                  <button
                    key={key}
                    id={`followup-tab-${key}`}
                    type="button"
                    role="tab"
                    aria-selected={activeFollowUp === key}
                    aria-controls="followup-panel"
                    className={activeFollowUp === key ? 'is-active' : ''}
                    onClick={() => setActiveFollowUp(key)}
                  >
                    {label} <span>{group.available === false ? '—' : group.count}</span>
                  </button>
                );
              })}
            </div>
            <div id="followup-panel" className="business-followup__table-wrap" role="tabpanel" aria-labelledby={`followup-tab-${activeFollowUp}`} key={activeFollowUp}>
              {activeGroup.available === false ? (
                <p className="business-followup__notice">{UNAVAILABLE_REASON}</p>
              ) : (
                <table>
                  <thead><tr><th>Cliente</th><th>Referencia</th><th>Monto</th><th>Hace</th><th>Acción</th></tr></thead>
                  <tbody>
                    {activeRows.length === 0 && <tr><td colSpan="5" className="business-table__empty">No hay casos para revisar.</td></tr>}
                    {activeRows.map((row) => (
                      <tr key={`${activeFollowUp}-${row.client_id ?? row.client}-${row.reference}`}>
                        <td data-label="Cliente"><strong>{row.client}</strong></td>
                        <td data-label="Referencia">{row.reference}</td>
                        <td data-label="Monto">{formatMoney(row.amount, currency)}</td>
                        <td data-label="Hace">{row.age_days} {row.age_days === 1 ? 'día' : 'días'}</td>
                        <td data-label="Acción"><button type="button" onClick={() => openFollowUpRow(row)}>{activeFollowUpLabels.action}</button></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
            <button className="business-link business-followup__all" type="button" onClick={openFollowUpAll}>
              {activeFollowUpLabels.all} <ArrowRight aria-hidden="true" size={15} />
            </button>
          </section>

          <section className="business-dashboard__pending ink-enter-6" aria-labelledby="pending-title">
            <div className="business-dashboard__pending-title">
              <PackageSearch aria-hidden="true" size={22} />
              <div><h2 id="pending-title">Pendientes por revisar</h2><p>Situación actual del negocio</p></div>
            </div>
            <div className="business-dashboard__pending-item">
              <span className="business-dashboard__pending-count">{pending.low_stock_products}</span>
              <div>
                <strong>{pending.low_stock_products === 1 ? 'producto con pocas existencias' : 'productos con pocas existencias'}</strong>
                <span>Conviene revisar antes de la próxima venta.</span>
              </div>
              <button type="button" onClick={() => navigate(buildPath('/inventario', { stock_status: 'low' }))}>Ver inventario <ArrowRight aria-hidden="true" size={15} /></button>
            </div>
            <div className="business-dashboard__pending-item business-dashboard__pending-item--danger">
              <span className="business-dashboard__pending-count"><AlertCircle aria-hidden="true" size={19} /></span>
              <div>
                <strong>{pending.fiscal_documents_with_errors} {pending.fiscal_documents_with_errors === 1 ? 'comprobante con error fiscal' : 'comprobantes con errores fiscales'}</strong>
                <span>{pending.fiscal_documents_with_errors ? 'Necesitan revisión antes de volver a enviarlos.' : 'No hay errores fiscales pendientes.'}</span>
              </div>
              <button type="button" onClick={() => navigate(buildPath('/cotizaciones', { view: 'fiscal' }))}>Revisar comprobantes <ArrowRight aria-hidden="true" size={15} /></button>
            </div>
            <p className="business-dashboard__pending-note">Estos avisos muestran la situación actual y no cambian con el periodo analizado.</p>
          </section>
        </>
      )}
    </div>
  );
}
