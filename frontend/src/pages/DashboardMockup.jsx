import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertCircle,
  ArrowRight,
  CalendarDays,
  Check,
  ChevronDown,
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
import '../styles/dashboardMockup.css';

const MONTHS = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep'];
const MONTH_NAMES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre'];
const SALES = [4600, 5900, 7000, 8100, 10800, 11300, 13900, 16300, 9800];
const QUOTED = [5700, 8200, 10500, 9200, 12900, 11500, 10100, 14500, 11100];

const KPI_ITEMS = [
  {
    label: 'Ventas registradas',
    value: 'S/ 10,000',
    detail: '20 ventas emitidas',
    trend: '+12.4 %',
    trendLabel: 'frente al periodo anterior',
    note: 'S/ 1,200 esperan respuesta de SUNAT',
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
  { name: 'Papel bond A4', quantity: '16 cajas', amount: 'S/ 3,200', change: '+18 %', positive: true },
  { name: 'Papel bond A3', quantity: '10 cajas', amount: 'S/ 2,600', change: '−9 %', positive: false },
  { name: 'Cartulina blanca', quantity: '50 paquetes', amount: 'S/ 1,900', change: '+6 %', positive: true },
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

function FilterButton({ children, icon: Icon, wide = false }) {
  return (
    <button className={`business-dashboard__filter${wide ? ' business-dashboard__filter--wide' : ''}`} type="button">
      {Icon && <Icon aria-hidden="true" size={16} strokeWidth={2} />}
      <span>{children}</span>
      <ChevronDown aria-hidden="true" className="business-dashboard__filter-chevron" size={15} />
    </button>
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
  const padding = { left: 58, right: 20, top: 20, bottom: 42 };
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

function SalesChart({ showQuoted }) {
  const [activePoint, setActivePoint] = useState(null);
  const width = 920;
  const height = 290;
  const maxValue = 20000;
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
        <rect className="business-chart__current" x="804" y="20" width="96" height="228" rx="10" />
        {yTicks.map((tick) => {
          const y = 20 + 228 - (tick / maxValue) * 228;
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
          d={`${pathFromPoints(salesPoints)} L ${salesPoints.at(-1).x} 248 L ${salesPoints[0].x} 248 Z`}
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
            <text className="business-chart__month" x={point.x} y="276" textAnchor="middle">{MONTHS[index]}</text>
          </g>
        ))}
        <text className="business-chart__current-label" x="852" y="38" textAnchor="middle">Mes en curso</text>
          </svg>
          {salesPoints.map((point, index) => (
            <button
              key={`hotspot-${MONTHS[index]}`}
              className="business-chart__hotspot"
              type="button"
              style={{ '--point-x': `${(point.x / width) * 100}%`, '--point-y': `${(point.y / height) * 100}%` }}
              aria-label={`${MONTH_NAMES[index]}: ventas ${formatSoles(SALES[index])}${showQuoted ? `, importe cotizado ${formatSoles(QUOTED[index])}` : ''}`}
              aria-describedby={activePoint === index ? 'business-chart-tooltip' : undefined}
              onMouseEnter={() => setActivePoint(index)}
              onMouseLeave={() => setActivePoint(null)}
              onFocus={() => setActivePoint(index)}
              onBlur={() => setActivePoint(null)}
              onClick={() => setActivePoint(index)}
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
              <strong>{MONTH_NAMES[activePoint]}{activePoint === MONTHS.length - 1 ? ' · mes en curso' : ''}</strong>
              <span><i className="business-chart__tooltip-dot business-chart__tooltip-dot--sales" />Ventas registradas <b>{formatSoles(SALES[activePoint])}</b></span>
              {showQuoted && <span><i className="business-chart__tooltip-dot business-chart__tooltip-dot--quoted" />Importe cotizado <b>{formatSoles(QUOTED[activePoint])}</b></span>}
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

function RankingTable({ type }) {
  const navigate = useNavigate();
  const isProducts = type === 'products';
  const rows = isProducts ? PRODUCTS : CLIENTS;

  return (
    <section className="business-panel business-ranking">
      <div className="business-panel__heading business-panel__heading--compact">
        <div>
          <h2>{isProducts ? 'Productos más vendidos' : 'Clientes que más compran'}</h2>
          <p>{isProducts ? 'Ordenados por venta en soles' : 'Compras dentro del periodo analizado'}</p>
        </div>
        <button className="business-link" type="button" onClick={() => navigate(isProducts ? '/productos' : '/clientes')}>
          Ver todos <ArrowRight aria-hidden="true" size={15} />
        </button>
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
                <td data-label={isProducts ? 'Producto' : 'Cliente'}><strong>{row.name}</strong></td>
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
      <p className="business-ranking__insight">
        {isProducts ? 'Papel bond A3 vendió menos que en el periodo anterior.' : 'Comercial Norte representa el 25 % de las ventas.'}
      </p>
    </section>
  );
}

export default function DashboardMockup() {
  const navigate = useNavigate();
  const [showQuoted, setShowQuoted] = useState(true);
  const [activeFollowUp, setActiveFollowUp] = useState('quotes');
  const activeRows = FOLLOW_UP[activeFollowUp].rows;

  return (
    <div className="business-dashboard" data-testid="dashboard-business-mockup">
      <header className="business-dashboard__intro ink-enter-1">
        <div>
          <span className="business-dashboard__rule" aria-hidden="true" />
          <div className="business-dashboard__title-row">
            <h1>Tu negocio, de un vistazo</h1>
            <span className="business-dashboard__sample">Datos ilustrativos</span>
          </div>
          <p>Ventas, clientes y oportunidades para decidir qué hacer hoy.</p>
        </div>
        <div className="business-dashboard__updated">
          <span>Actualizado al 26 sep 2026</span>
          <small>Comparado con 1–26 ago 2026</small>
        </div>
      </header>

      <section className="business-dashboard__filters ink-enter-2" aria-label="Filtros del resumen">
        <div className="business-dashboard__filter-label">
          <span>Periodo analizado</span>
          <FilterButton icon={CalendarDays} wide>1–26 sep 2026</FilterButton>
        </div>
        <FilterButton>Todos los clientes</FilterButton>
        <FilterButton>Todos los productos</FilterButton>
        <FilterButton>Moneda: Soles</FilterButton>
        <button className="business-dashboard__clear" type="button">Limpiar filtros</button>
        <p className="business-dashboard__currency-note">Los importes muestran únicamente operaciones registradas en soles.</p>
      </section>

      <section className="business-dashboard__metrics ink-enter-3" aria-label="Indicadores del negocio">
        {KPI_ITEMS.map((item, index) => <MetricCard key={item.label} item={item} index={index} />)}
      </section>

      <aside className="business-dashboard__critical ink-enter-3" aria-label="Aviso importante">
        <span className="business-dashboard__critical-icon"><AlertCircle aria-hidden="true" size={21} /></span>
        <div>
          <strong>Requiere atención</strong>
          <span>1 comprobante fue rechazado por SUNAT.</span>
        </div>
        <button type="button" onClick={() => navigate('/facturas')}>
          Corregir ahora <ArrowRight aria-hidden="true" size={16} />
        </button>
      </aside>

      <section className="business-panel business-sales ink-enter-4">
        <div className="business-panel__heading business-sales__heading">
          <div>
            <h2 id="sales-chart-title">Ventas y cotizaciones</h2>
            <p>Ventas registradas en Inkora</p>
          </div>
          <div className="business-sales__controls">
            <span className="business-sales__range-label">Historial</span>
            <FilterButton>Ene – sep 2026</FilterButton>
            <FilterButton>Por mes</FilterButton>
            <label className="business-toggle">
              <input type="checkbox" checked={showQuoted} onChange={(event) => setShowQuoted(event.target.checked)} />
              <span className="business-toggle__track" aria-hidden="true"><span /></span>
              <span>Mostrar importe cotizado</span>
            </label>
          </div>
        </div>
        <SalesChart showQuoted={showQuoted} />
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
          <span className="business-sales__conversion-check"><Check aria-hidden="true" size={18} /></span>
        </div>
      </section>

      <div className="business-dashboard__rankings ink-enter-5">
        <RankingTable type="products" />
        <RankingTable type="clients" />
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
              <tr><th>Cliente</th><th>Cotización</th><th>Monto</th><th>Emitida hace</th><th>Acción</th></tr>
            </thead>
            <tbody>
              {activeRows.map((row) => (
                <tr key={`${activeFollowUp}-${row.client}`}>
                  <td data-label="Cliente"><strong>{row.client}</strong></td>
                  <td data-label="Cotización">{row.quote}</td>
                  <td data-label="Monto">{row.amount}</td>
                  <td data-label="Emitida hace">{row.age}</td>
                  <td data-label="Acción"><button type="button" onClick={() => navigate('/cotizaciones')}>Ver detalle</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <button className="business-link business-followup__all" type="button" onClick={() => navigate('/cotizaciones')}>
          Ver todas las oportunidades <ArrowRight aria-hidden="true" size={15} />
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
        <p className="business-dashboard__pending-note">Estos avisos muestran la situación actual y no cambian con el periodo analizado.</p>
      </section>
    </div>
  );
}
