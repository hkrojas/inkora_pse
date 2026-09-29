import { useEffect, useMemo, useState } from 'react';
import { createPortal } from 'react-dom';
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
  X,
} from 'lucide-react';
import '../styles/dashboardMockup.css';

const MONTHS = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep'];
const MONTH_NAMES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre'];
const SALES = [4600, 5900, 7000, 8100, 10800, 11300, 13900, 16300, 9800];
const QUOTED = [5700, 8200, 10500, 9200, 12900, 11500, 10100, 14500, 11100];
const DATA_CUTOFF = new Date(2026, 8, 26);
const CUTOFF_DAY = DATA_CUTOFF.getDate();
const CUTOFF_MONTH = new Intl.DateTimeFormat('es-PE', { month: 'long' }).format(DATA_CUTOFF);
const CUTOFF_MONTH_LABEL = `${CUTOFF_MONTH[0].toUpperCase()}${CUTOFF_MONTH.slice(1)}`;
const CURRENT_MONTH_INDEX = DATA_CUTOFF.getMonth();
const PREVIOUS_MATCHED_SALES = 14800;

const KPI_ITEMS = [
  {
    label: 'Ventas registradas',
    value: 'S/ 10,000',
    detail: '20 ventas emitidas',
    trend: '+12.4 %',
    trendLabel: 'vs. agosto',
    note: 'De este total, S/ 1,200 esperan respuesta de SUNAT.',
    icon: ShoppingBag,
    tone: 'success',
  },
  {
    label: 'Clientes que compraron',
    value: '14',
    detail: '4 nuevos · 10 que volvieron',
    icon: UsersRound,
    tone: 'primary',
  },
  {
    label: 'Promedio por venta',
    value: 'S/ 500',
    detail: 'Por cada venta registrada',
    icon: ReceiptText,
    tone: 'primary',
  },
  {
    label: 'Por cobrar fuera de plazo',
    value: 'S/ 2,750',
    detail: '6 clientes · al día de hoy',
    icon: CircleDollarSign,
    tone: 'danger',
  },
];

const PRODUCTS = [
  { name: 'Papel bond A4', quantity: '16 cajas', amount: 'S/ 3,200', amountValue: 3200, change: '+18 %', changeValue: 18, positive: true },
  { name: 'Papel bond A3', quantity: '10 cajas', amount: 'S/ 2,600', amountValue: 2600, change: '−9 %', changeValue: -9, positive: false },
  { name: 'Cartulina blanca', quantity: '50 paquetes', amount: 'S/ 1,900', amountValue: 1900, change: '+6 %', changeValue: 6, positive: true },
];

const CLIENTS = [
  { name: 'Comercial Norte', amount: 'S/ 2,500', purchases: 3, last: '25 sep 2026' },
  { name: 'Imprenta Horizonte', amount: 'S/ 1,800', purchases: 2, last: '24 sep 2026' },
  { name: 'Papelería Central', amount: 'S/ 1,400', purchases: 2, last: '22 sep 2026' },
];

const FOLLOW_UP = {
  quotes: {
    label: 'Cotizaciones sin una venta',
    count: 12,
    rows: [
      { client: 'Imprenta Horizonte', quote: 'COT-000318', amount: 'S/ 2,000', age: '16 días' },
      { client: 'Comercial Norte', quote: 'COT-000319', amount: 'S/ 1,500', age: '14 días' },
      { client: 'Distribuciones Sol', quote: 'COT-000325', amount: 'S/ 800', age: '6 días' },
    ],
  },
  declining: {
    label: 'Compraron menos',
    count: 5,
    rows: [
      { client: 'Gráfica Andina', quote: 'Última compra', amount: 'S/ 600', age: '24 días' },
      { client: 'Oficinas Sur', quote: 'Última compra', amount: 'S/ 480', age: '31 días' },
      { client: 'Editorial Azul', quote: 'Última compra', amount: 'S/ 390', age: '18 días' },
    ],
  },
  inactive: {
    label: 'Sin compras en 60 días',
    count: 9,
    rows: [
      { client: 'Servicios Delta', quote: 'Última compra', amount: 'S/ 900', age: '68 días' },
      { client: 'Librería Punto', quote: 'Última compra', amount: 'S/ 720', age: '74 días' },
      { client: 'Comercial Vega', quote: 'Última compra', amount: 'S/ 550', age: '82 días' },
    ],
  },
};

function ScopeChip({ children, icon: Icon, wide = false }) {
  return (
    <span className={`business-dashboard__filter${wide ? ' business-dashboard__filter--wide' : ''}`}>
      {Icon && <Icon aria-hidden="true" size={16} strokeWidth={2} />}
      <span>{children}</span>
    </span>
  );
}

function AnimatedMetricValue({ value, delay = 0 }) {
  const target = Number(value.replace(/[^0-9]/g, ''));
  const prefix = value.startsWith('S/') ? 'S/ ' : '';
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
        setDisplayValue(Math.round(target * eased));
        if (progress < 1) frameId = window.requestAnimationFrame(animate);
      };
      frameId = window.requestAnimationFrame(animate);
    }, delay);

    return () => {
      window.clearTimeout(startTimer);
      window.cancelAnimationFrame(frameId);
    };
  }, [delay, target]);

  return (
    <span aria-label={value}>
      <span aria-hidden="true">{prefix}{new Intl.NumberFormat('es-PE').format(displayValue)}</span>
    </span>
  );
}

function MetricCard({ item, index }) {
  const Icon = item.icon;
  return (
    <article className={`business-metric business-metric--${item.tone}`} style={{ '--metric-order': index }}>
      <div className="business-metric__topline">
        <span className="business-metric__icon"><Icon aria-hidden="true" size={20} strokeWidth={2.1} /></span>
        <span className="business-metric__label">{item.label}</span>
      </div>
      <p className="business-metric__value"><AnimatedMetricValue value={item.value} delay={170 + (index * 75)} /></p>
      {item.trend ? (
        <p className="business-metric__trend">
          <TrendingUp aria-hidden="true" size={15} />
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
    x: padding.left + (index * plotWidth) / (values.length - 1),
    y: padding.top + plotHeight - (value / maxValue) * plotHeight,
  }));
}

function pathFromPoints(points) {
  return points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`).join(' ');
}

function formatSoles(value) {
  return `S/ ${new Intl.NumberFormat('es-PE').format(value)}`;
}

function SalesChart({ showQuoted, onExploreMonth }) {
  const [activePoint, setActivePoint] = useState(null);
  const width = 920;
  const height = 320;
  const maxValue = 20000;
  const plotTop = 22;
  const plotBottom = height - 44;
  const plotHeight = plotBottom - plotTop;
  const salesPoints = useMemo(() => buildPoints(SALES, width, height, maxValue), []);
  const quotedPoints = useMemo(() => buildPoints(QUOTED, width, height, maxValue), []);
  const yTicks = [0, 5000, 10000, 15000, 20000];

  return (
    <div className="business-chart" role="region" aria-labelledby="sales-chart-title" aria-describedby="sales-chart-description">
      <p id="sales-chart-description" className="sr-only">
        Historial mensual de enero a septiembre. Las ventas registradas suben de S/ 4,600 en enero a un máximo de S/ 16,300 en agosto y cierran septiembre, aún en curso, en S/ 9,800.
      </p>
      <div className="business-chart__viewport">
        <div className="business-chart__canvas">
          <svg className="business-chart__svg" viewBox={`0 0 ${width} ${height}`} aria-hidden="true">
        <defs>
          <linearGradient id="salesArea" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="var(--dashboard-green)" stopOpacity="0.17" />
            <stop offset="100%" stopColor="var(--dashboard-green)" stopOpacity="0" />
          </linearGradient>
        </defs>
        <rect className="business-chart__current" x="804" y={plotTop} width="96" height={plotHeight} rx="10" />
        {yTicks.map((tick) => {
          const y = plotTop + plotHeight - (tick / maxValue) * plotHeight;
          return (
            <g key={tick}>
              <line className="business-chart__grid" x1="58" x2="900" y1={y} y2={y} />
              <text className="business-chart__axis-label" x="48" y={y + 4} textAnchor="end">
                {tick === 0 ? 'S/ 0' : `S/ ${tick / 1000} mil`}
              </text>
            </g>
          );
        })}
        <path
          className="business-chart__area"
          d={`${pathFromPoints(salesPoints)} L ${salesPoints.at(-1).x} ${plotBottom} L ${salesPoints[0].x} ${plotBottom} Z`}
        />
        <path className="business-chart__line business-chart__line--sales" d={pathFromPoints(salesPoints)} pathLength="1" />
        <g className={`business-chart__quoted${showQuoted ? ' is-visible' : ''}`}>
          <path className="business-chart__line business-chart__line--quoted" d={pathFromPoints(quotedPoints)} pathLength="1" />
          {quotedPoints.map((point, index) => (
            <circle key={MONTHS[index]} className="business-chart__point business-chart__point--quoted" cx={point.x} cy={point.y} r="4" />
          ))}
        </g>
        {salesPoints.map((point, index) => (
          <g key={MONTHS[index]} className={activePoint === index ? 'is-active' : ''}>
            <circle className="business-chart__point-halo" cx={point.x} cy={point.y} r="8" />
            <circle className="business-chart__point business-chart__point--sales" cx={point.x} cy={point.y} r="4.5" />
            <text className="business-chart__month" x={point.x} y="306" textAnchor="middle">{MONTHS[index]}</text>
          </g>
        ))}
        <text className="business-chart__current-label" x="852" y="40" textAnchor="middle">
          <tspan x="852">{CUTOFF_MONTH_LABEL}</tspan>
          <tspan x="852" dy="12">hasta el día {CUTOFF_DAY}</tspan>
        </text>
          </svg>
          {salesPoints.map((point, index) => (
            <button
              key={`hotspot-${MONTHS[index]}`}
              className="business-chart__hotspot"
              type="button"
              style={{ '--point-x': `${(point.x / width) * 100}%`, '--point-y': `${(point.y / height) * 100}%` }}
              aria-label={`${MONTH_NAMES[index]}: ventas ${formatSoles(SALES[index])}${showQuoted ? `, importe cotizado ${formatSoles(QUOTED[index])}` : ''}. Ver registros.`}
              aria-describedby={activePoint === index ? 'business-chart-tooltip' : undefined}
              onMouseEnter={() => setActivePoint(index)}
              onMouseLeave={() => setActivePoint(null)}
              onFocus={() => setActivePoint(index)}
              onBlur={() => setActivePoint(null)}
              onClick={() => {
                setActivePoint(index);
                onExploreMonth(index);
              }}
            />
          ))}
          {activePoint !== null && (
            <div
              id="business-chart-tooltip"
              className={`business-chart__tooltip${Math.min(salesPoints[activePoint].y, quotedPoints[activePoint].y) < 105 ? ' business-chart__tooltip--below' : ''}`}
              style={{
                '--tooltip-x': `${(salesPoints[activePoint].x / width) * 100}%`,
                '--tooltip-y': `${(Math.min(salesPoints[activePoint].y, showQuoted ? quotedPoints[activePoint].y : salesPoints[activePoint].y) / height) * 100}%`,
              }}
              role="tooltip"
            >
              <strong>{MONTH_NAMES[activePoint]}{activePoint === CURRENT_MONTH_INDEX ? ` · hasta el día ${CUTOFF_DAY}` : ''}</strong>
              <span><i className="business-chart__tooltip-dot business-chart__tooltip-dot--sales" />Ventas registradas <b>{formatSoles(SALES[activePoint])}</b></span>
              {showQuoted && <span><i className="business-chart__tooltip-dot business-chart__tooltip-dot--quoted" />Importe cotizado <b>{formatSoles(QUOTED[activePoint])}</b></span>}
              {activePoint === CURRENT_MONTH_INDEX && (
                <span className="business-chart__tooltip-compare">
                  Mismo tramo de agosto <b>{formatSoles(PREVIOUS_MATCHED_SALES)}</b>
                </span>
              )}
            </div>
          )}
        </div>
      </div>
      <div className="business-chart__legend" aria-hidden="true">
        <span><i className="business-chart__legend-line business-chart__legend-line--sales" />Ventas totales</span>
        <span className={showQuoted ? '' : 'is-muted'}><i className="business-chart__legend-line business-chart__legend-line--quoted" />Importe cotizado</span>
      </div>
    </div>
  );
}

function RankingTable({ type, onExplore }) {
  const navigate = useNavigate();
  const isProducts = type === 'products';
  const [productOrder, setProductOrder] = useState('sales');
  const rows = useMemo(() => {
    if (!isProducts) return CLIENTS;
    if (productOrder === 'decline') return [...PRODUCTS].sort((a, b) => a.changeValue - b.changeValue);
    return [...PRODUCTS].sort((a, b) => b.amountValue - a.amountValue);
  }, [isProducts, productOrder]);
  const decliningProduct = PRODUCTS.reduce((lowest, product) => (
    product.changeValue < lowest.changeValue ? product : lowest
  ), PRODUCTS[0]);

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
            {rows.map((row) => (
              <tr key={row.name}>
                <td data-label={isProducts ? 'Producto' : 'Cliente'}>
                  <button className="business-ranking__entity" type="button" onClick={() => onExplore(isProducts ? 'product' : 'client', row)}>
                    {row.name}
                  </button>
                </td>
                <td data-label={isProducts ? 'Cantidad' : 'Ventas'}>{isProducts ? row.quantity : row.amount}</td>
                <td data-label={isProducts ? 'Ventas' : 'Compras'}>{isProducts ? row.amount : row.purchases}</td>
                <td data-label={isProducts ? 'Cambio' : 'Última compra'}>
                  {isProducts ? (
                    <span className={`business-ranking__change ${row.positive ? 'is-positive' : 'is-negative'}`}>
                      {row.positive ? <TrendingUp aria-hidden="true" size={14} /> : <TrendingDown aria-hidden="true" size={14} />}
                      {row.change}
                    </span>
                  ) : row.last}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className={`business-ranking__insight${isProducts ? ' business-ranking__insight--neutral' : ''}`}>
        {isProducts
          ? `Las ventas de ${decliningProduct.name} bajaron ${Math.abs(decliningProduct.changeValue)} %.`
          : 'Comercial Norte representa el 25 % de las ventas.'}
      </p>
    </section>
  );
}

function buildExplorerData(kind, item) {
  if (kind === 'month') {
    const total = SALES[item.index];
    const first = Math.round(total * 0.4);
    const second = Math.round(total * 0.34);
    const third = total - first - second;
    const current = item.index === CURRENT_MONTH_INDEX;
    return {
      kind,
      title: `Ventas de ${MONTH_NAMES[item.index]}`,
      subtitle: current ? `Datos acumulados hasta el día ${CUTOFF_DAY}.` : 'Mes completo dentro del historial.',
      total: formatSoles(total),
      scope: [current ? `1–${CUTOFF_DAY} ${MONTHS[item.index].toLowerCase()} 2026` : `${MONTH_NAMES[item.index]} 2026`, 'Todos los clientes', 'Todos los productos', 'Soles'],
      columns: ['Comprobante', 'Fecha', 'Cliente', 'Importe'],
      rows: [
        [`F001-000${82 + item.index}`, `${current ? 8 : 6} ${MONTHS[item.index].toLowerCase()}`, 'Comercial Norte', formatSoles(first)],
        [`B001-000${41 + item.index}`, `${current ? 17 : 14} ${MONTHS[item.index].toLowerCase()}`, 'Imprenta Horizonte', formatSoles(second)],
        [`F001-000${97 + item.index}`, `${current ? CUTOFF_DAY : 25} ${MONTHS[item.index].toLowerCase()}`, 'Papelería Central', formatSoles(third)],
      ],
      destination: `/facturas?month=${item.index + 1}&year=2026`,
    };
  }

  if (kind === 'product') {
    const first = Math.round(item.amountValue * 0.44);
    const second = Math.round(item.amountValue * 0.33);
    return {
      kind,
      title: item.name,
      subtitle: 'Ventas que explican el importe mostrado.',
      total: item.amount,
      scope: [`1–${CUTOFF_DAY} sep 2026`, item.name, 'Todos los clientes', 'Soles'],
      columns: ['Comprobante', 'Cliente', 'Cantidad', 'Importe'],
      rows: [
        ['F001-000102', 'Comercial Norte', item.quantity, formatSoles(first)],
        ['B001-000064', 'Imprenta Horizonte', '4 unidades', formatSoles(second)],
        ['F001-000118', 'Papelería Central', '3 unidades', formatSoles(item.amountValue - first - second)],
      ],
      destination: `/productos?q=${encodeURIComponent(item.name)}`,
    };
  }

  const amountValue = Number(item.amount.replace(/[^0-9]/g, ''));
  const first = Math.round(amountValue * 0.52);
  return {
    kind,
    title: item.name,
    subtitle: 'Compras que explican el importe mostrado.',
    total: item.amount,
    scope: [`1–${CUTOFF_DAY} sep 2026`, item.name, 'Todos los productos', 'Soles'],
    columns: ['Comprobante', 'Fecha', 'Productos', 'Importe'],
    rows: [
      ['F001-000106', '12 sep', 'Papel bond A4', formatSoles(first)],
      ['B001-000071', item.last.replace('2026', '').trim(), 'Papel bond A3', formatSoles(amountValue - first)],
    ],
    destination: `/clientes?q=${encodeURIComponent(item.name)}`,
  };
}

function ExplorerPanel({ data, onClose, onOpenAll }) {
  useEffect(() => {
    const closeOnEscape = (event) => {
      if (event.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', closeOnEscape);
    return () => document.removeEventListener('keydown', closeOnEscape);
  }, [onClose]);

  if (!data) return null;

  return createPortal(
    <div className="business-explorer" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className="business-explorer__panel" role="dialog" aria-modal="true" aria-labelledby="business-explorer-title">
        <div className="business-explorer__header">
          <div>
            <span>Datos de ejemplo</span>
            <h2 id="business-explorer-title">{data.title}</h2>
            <p>{data.subtitle}</p>
          </div>
          <button type="button" onClick={onClose} aria-label="Cerrar detalle"><X aria-hidden="true" size={19} /></button>
        </div>
        <div className="business-explorer__total"><span>Total consultado</span><strong>{data.total}</strong></div>
        <div className="business-explorer__scope" aria-label="Filtros aplicados">
          {data.scope.map((scope) => <span key={scope}>{scope}</span>)}
        </div>
        <div className="business-explorer__table-wrap">
          <table>
            <thead><tr>{data.columns.map((column) => <th key={column}>{column}</th>)}</tr></thead>
            <tbody>
              {data.rows.map((row) => (
                <tr key={row[0]}>{row.map((cell, index) => <td key={`${row[0]}-${data.columns[index]}`} data-label={data.columns[index]}>{cell}</td>)}</tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="business-explorer__footer">
          <p>Estos registros son ilustrativos y se reemplazarán por datos reales al conectar el dashboard.</p>
          <button type="button" onClick={onOpenAll}>Abrir lista completa <ArrowRight aria-hidden="true" size={15} /></button>
        </div>
      </section>
    </div>,
    document.body,
  );
}

export default function DashboardMockup() {
  const navigate = useNavigate();
  const [showQuoted, setShowQuoted] = useState(true);
  const [activeFollowUp, setActiveFollowUp] = useState('quotes');
  const [explorerData, setExplorerData] = useState(null);
  const activeRows = FOLLOW_UP[activeFollowUp].rows;
  const activeFollowUpLabels = activeFollowUp === 'quotes'
    ? { action: 'Ver cotización', all: 'Ver todas las cotizaciones' }
    : { action: 'Ver cliente', all: 'Ver todos los clientes' };

  const openExplorer = (kind, item) => setExplorerData(buildExplorerData(kind, item));
  const openFollowUpRow = (row) => {
    if (activeFollowUp === 'quotes') navigate(`/cotizaciones?q=${encodeURIComponent(row.quote)}`);
    else navigate(`/clientes?q=${encodeURIComponent(row.client)}`);
  };
  const openFollowUpAll = () => navigate(activeFollowUp === 'quotes' ? '/cotizaciones' : '/clientes');

  return (
    <div className="business-dashboard" data-testid="dashboard-business-mockup">
      <header className="business-dashboard__intro ink-enter-1">
        <div>
          <span className="business-dashboard__rule" aria-hidden="true" />
          <div className="business-dashboard__title-row">
            <h1>Tu negocio, de un vistazo</h1>
            <span className="business-dashboard__sample">Datos de ejemplo</span>
          </div>
          <p>Ventas, clientes y oportunidades para decidir qué hacer hoy.</p>
        </div>
        <div className="business-dashboard__updated">
          <span>Actualizado al {CUTOFF_DAY} sep 2026</span>
          <small>Comparado con 1–{CUTOFF_DAY} ago 2026</small>
        </div>
      </header>

      <section className="business-dashboard__filters ink-enter-2" aria-label="Filtros del resumen">
        <div className="business-dashboard__filter-label">
          <span>Periodo analizado</span>
          <ScopeChip icon={CalendarDays} wide>1–{CUTOFF_DAY} sep 2026</ScopeChip>
        </div>
        <ScopeChip>Todos los clientes</ScopeChip>
        <ScopeChip>Todos los productos</ScopeChip>
        <ScopeChip>Moneda: Soles</ScopeChip>
        <p className="business-dashboard__currency-note">Los importes muestran únicamente operaciones registradas en soles.</p>
      </section>

      <section className="business-dashboard__metrics ink-enter-3" aria-label="Indicadores del negocio">
        {KPI_ITEMS.map((item, index) => <MetricCard key={item.label} item={item} index={index} />)}
      </section>

      <section className="business-panel business-sales ink-enter-4">
        <div className="business-panel__heading business-sales__heading">
          <div>
            <h2 id="sales-chart-title">Ventas y cotizaciones</h2>
            <p>Ventas registradas en Inkora</p>
          </div>
          <div className="business-sales__controls">
            <span className="business-sales__range-label">Historial</span>
            <ScopeChip>Ene – sep 2026</ScopeChip>
            <ScopeChip>Por mes</ScopeChip>
            <label className="business-toggle">
              <input type="checkbox" checked={showQuoted} onChange={(event) => setShowQuoted(event.target.checked)} />
              <span className="business-toggle__track" aria-hidden="true"><span /></span>
              <span>Mostrar importe cotizado</span>
            </label>
          </div>
        </div>
        <SalesChart showQuoted={showQuoted} onExploreMonth={(index) => openExplorer('month', { index })} />
        <p className="business-sales__footnote">Incluye IGV. Descuenta notas de crédito y suma notas de débito.</p>
        <div className="business-sales__conversion">
          <div className="business-sales__conversion-rate">
            <strong>40 %</strong>
            <span>Terminaron en venta</span>
          </div>
          <div className="business-sales__conversion-copy">
            <strong>8 de 20 cotizaciones emitidas del 1 al 26 de septiembre terminaron en venta.</strong>
            <span>Resultado actualizado al 26 de septiembre.</span>
          </div>
        </div>
      </section>

      <div className="business-dashboard__rankings ink-enter-5">
        <RankingTable type="products" onExplore={openExplorer} />
        <RankingTable type="clients" onExplore={openExplorer} />
      </div>

      <section className="business-panel business-followup ink-enter-6">
        <div className="business-panel__heading">
          <div>
            <h2>Para hacer seguimiento</h2>
            <p>Oportunidades que aún pueden convertirse en venta.</p>
          </div>
          <button className="business-button business-button--primary" type="button" onClick={() => navigate('/cotizaciones')}>
            Crear cotización <Plus aria-hidden="true" size={16} />
          </button>
        </div>
        <div className="business-followup__tabs" role="tablist" aria-label="Tipos de seguimiento">
          {Object.entries(FOLLOW_UP).map(([key, item]) => (
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
              {item.label} <span>{item.count}</span>
            </button>
          ))}
        </div>
        <div id="followup-panel" className="business-followup__table-wrap" role="tabpanel" aria-labelledby={`followup-tab-${activeFollowUp}`} key={activeFollowUp}>
          <table>
            <thead>
              <tr>
                <th>Cliente</th>
                <th>{activeFollowUp === 'quotes' ? 'Cotización' : 'Referencia'}</th>
                <th>Monto</th>
                <th>{activeFollowUp === 'quotes' ? 'Emitida hace' : 'Hace'}</th>
                <th>Acción</th>
              </tr>
            </thead>
            <tbody>
              {activeRows.map((row) => (
                <tr key={`${activeFollowUp}-${row.client}`}>
                  <td data-label="Cliente"><strong>{row.client}</strong></td>
                  <td data-label="Cotización">{row.quote}</td>
                  <td data-label="Monto">{row.amount}</td>
                  <td data-label="Emitida hace">{row.age}</td>
                  <td data-label="Acción"><button type="button" onClick={() => openFollowUpRow(row)}>{activeFollowUpLabels.action}</button></td>
                </tr>
              ))}
            </tbody>
          </table>
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
          <span className="business-dashboard__pending-count">3</span>
          <div><strong>productos con pocas existencias</strong><span>Conviene revisar antes de la próxima venta.</span></div>
          <button type="button" onClick={() => navigate('/inventario')}>Ver inventario <ArrowRight aria-hidden="true" size={15} /></button>
        </div>
        <div className="business-dashboard__pending-item business-dashboard__pending-item--danger">
          <span className="business-dashboard__pending-count"><AlertCircle aria-hidden="true" size={19} /></span>
          <div><strong>1 comprobante rechazado por SUNAT</strong><span>Necesita una corrección antes de volver a enviarlo.</span></div>
          <button type="button" onClick={() => navigate('/facturas')}>Corregir ahora <ArrowRight aria-hidden="true" size={15} /></button>
        </div>
        <p className="business-dashboard__pending-note">Estos avisos muestran la situación actual y no cambian con el periodo analizado.</p>
      </section>
      <ExplorerPanel
        data={explorerData}
        onClose={() => setExplorerData(null)}
        onOpenAll={() => explorerData && navigate(explorerData.destination)}
      />
    </div>
  );
}
