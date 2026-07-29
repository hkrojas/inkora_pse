/*
THESIS: Inkora is one continuous operating thread, not a collection of disconnected modules.
OWN-WORLD: A deployable commercial document whose folds, records and status stamps make progress tangible.
STORY: Quote becomes fiscal document, stock movement and collection while its evidence remains attached.
FIRST VIEWPORT: Split editorial promise and a horizontal lime route through four concrete artifacts.
FORM: Cold paper surfaces, green infrastructure, precise lines, clipped folds, Mona Sans and data-only Recursive Mono. Concept seed 03c82e6c; composition A selected.
*/
import { useEffect, useRef, useState } from 'react';
import {
  ArrowDown,
  ArrowRight,
  Asterisk,
  Building2,
  Boxes,
  Check,
  CheckCircle2,
  ChevronDown,
  CircleX,
  Clock3,
  CircleDollarSign,
  ExternalLink,
  FileCheck2,
  FileText,
  Menu,
  Moon,
  PackageCheck,
  Printer,
  ReceiptText,
  Search,
  ShieldCheck,
  Store,
  Sun,
  X,
} from 'lucide-react';
import { publicReceipts } from '../services/publicReceipts';
import { DocumentTypeSelect, IssueDatePicker } from '../components/landing/ReceiptLookupControls';
import '../styles/landing.css';

const navigation = [
  { id: 'que-resuelve', label: 'Qué resuelve' },
  { id: 'recorrido', label: 'Cómo funciona' },
  { id: 'confianza', label: 'Confianza' },
  { id: 'consulta', label: 'Consulta' },
  { id: 'precios', label: 'Precio' },
];

const routeItems = [
  { type: 'Cotización', value: 'COT-00072', detail: 'Lista para enviar', icon: FileText },
  { type: 'Comprobante', value: 'F001-00184', detail: 'Aceptado por SUNAT', icon: ReceiptText },
  { type: 'Inventario', value: 'Stock actualizado', detail: '12 → 11 unidades', icon: Boxes },
  { type: 'Cobranza', value: 'S/ 498 cobrado', detail: 'Saldo S/ 0.00', icon: CircleDollarSign },
];

const journey = [
  {
    label: 'Cotiza',
    title: 'La venta empieza con contexto.',
    copy: 'Cliente, condiciones y productos quedan listos para continuar la operación sin volver a digitarlos.',
    eyebrow: 'COTIZACIÓN',
    folio: 'COT-00072',
    rows: [['Cliente', 'Comercial Andina SAC'], ['Entrega', '3 días hábiles'], ['Total', 'S/ 498.00']],
    status: 'LISTA PARA ENVIAR',
  },
  {
    label: 'Emite',
    title: 'El estado fiscal se ve, no se adivina.',
    copy: 'El comprobante conserva la operación de origen y muestra su avance hasta la aceptación.',
    eyebrow: 'FACTURA ELECTRÓNICA',
    folio: 'F001-00184',
    rows: [['Proveedor fiscal', 'Envío completado'], ['SUNAT', 'Aceptado'], ['Evidencia', 'XML + CDR']],
    status: 'ACEPTADA',
  },
  {
    label: 'Controla',
    title: 'El inventario responde a la venta.',
    copy: 'El movimiento deja rastro en almacén y Kardex para que el stock cuente la misma historia.',
    eyebrow: 'MOVIMIENTO DE STOCK',
    folio: 'SAL-000184',
    rows: [['Producto', 'Papel adhesivo A3'], ['Almacén', 'Principal'], ['Existencias', '12 → 11']],
    status: 'ACTUALIZADO',
  },
  {
    label: 'Cobra',
    title: 'Emitir no es lo mismo que cobrar.',
    copy: 'Cada pago se aplica a la venta y el saldo pendiente queda visible para el seguimiento.',
    eyebrow: 'PAGO APLICADO',
    folio: 'PAG-00096',
    rows: [['Método', 'Transferencia'], ['Importe', 'S/ 498.00'], ['Saldo', 'S/ 0.00']],
    status: 'COBRADO',
  },
];

const faqs = [
  ['¿Inkora cumple con SUNAT?', 'Inkora conecta la emisión electrónica con el proveedor fiscal configurado y muestra el estado reportado para cada documento, junto con sus evidencias disponibles.'],
  ['¿Necesito instalar un programa?', 'No. Inkora funciona desde el navegador y concentra la operación en el espacio de trabajo de tu empresa.'],
  ['¿Puedo trabajar con productos y servicios?', 'Sí. Puedes organizar productos inventariables y servicios que no afectan el stock dentro del mismo flujo comercial.'],
  ['¿Cómo solicito el alta?', 'Completa la solicitud de acceso con los datos básicos de tu empresa. La habilitación está sujeta a revisión y aprobación.'],
  ['¿Qué ocurre después de solicitar acceso?', 'Revisamos la información enviada. Si la solicitud es aprobada, habilitamos el espacio de trabajo y podrás iniciar sesión.'],
  ['¿Cuánto cuesta Inkora?', 'Inkora tendrá un único plan. Como todavía no hay una tarifa pública confirmada, la condición comercial vigente se informa durante la revisión, antes de habilitar el espacio de trabajo.'],
  ['¿Mis clientes podrán consultar sus comprobantes?', 'Sí. Con los datos exactos del documento pueden verificar facturas, boletas y sus notas de crédito o débito emitidas mediante Inkora.'],
];

const emptyLookup = {
  ruc: '',
  documentType: '',
  series: '',
  number: '',
  issueDate: '',
  amount: '',
};

function Brand() {
  return (
    <span className="landing-brand" aria-label="Inkora">
      <span className="landing-brand__mark" aria-hidden="true"><Asterisk size={25} strokeWidth={3.4} /></span>
      <strong>Inkora</strong>
    </span>
  );
}

function RouteAction({ children, iconSize = 17 }) {
  return (
    <>
      <span className="landing-button__label">{children}</span>
      <span className="landing-button__route-icon" aria-hidden="true"><ArrowRight size={iconSize} /></span>
    </>
  );
}

function ThemeToggle({ theme, onToggle, compact = false }) {
  const isDark = theme === 'dark';
  return (
    <button className={`landing-theme-toggle${compact ? ' is-compact' : ''}`} type="button" onClick={onToggle} aria-label={`Cambiar a modo ${isDark ? 'claro' : 'oscuro'}`} aria-pressed={isDark}>
      {isDark ? <Sun size={16} /> : <Moon size={16} />}
      <span>{isDark ? 'Claro' : 'Oscuro'}</span>
    </button>
  );
}

function Header({ theme, onToggleTheme }) {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [active, setActive] = useState('');
  const menuButton = useRef(null);
  const menuPanel = useRef(null);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  useEffect(() => {
    const sections = navigation.map(({ id }) => document.getElementById(id)).filter(Boolean);
    const observer = new IntersectionObserver((entries) => {
      const visible = entries.filter((entry) => entry.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
      if (visible) setActive(visible.target.id);
    }, { rootMargin: '-18% 0px -64% 0px', threshold: [0, 0.2, 0.6] });
    sections.forEach((section) => observer.observe(section));
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!open) return undefined;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const focusable = [...menuPanel.current.querySelectorAll('a[href], button:not([disabled])')];
    focusable[0]?.focus();
    const keepFocusInside = (event) => {
      if (event.key === 'Escape') {
        setOpen(false);
        menuButton.current?.focus();
        return;
      }
      if (event.key !== 'Tab' || focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener('keydown', keepFocusInside);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener('keydown', keepFocusInside);
    };
  }, [open]);

  const close = () => setOpen(false);
  const navigateTo = (event, id) => {
    event.preventDefault();
    close();
    const target = document.getElementById(id);
    if (!target) return;
    window.history.pushState(null, '', `#${id}`);
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    window.requestAnimationFrame(() => window.requestAnimationFrame(() => target.scrollIntoView({ behavior: reducedMotion ? 'auto' : 'smooth', block: 'start' })));
  };

  return (
    <header className={`landing-header${scrolled ? ' is-scrolled' : ''}`}>
      <div className="landing-shell landing-header__inner">
        <a className="landing-logo-link" href="#inicio" aria-label="Inkora, ir al inicio" onClick={(event) => navigateTo(event, 'inicio')}><Brand /></a>
        <nav ref={menuPanel} id="landing-mobile-menu" className={`landing-nav${open ? ' is-open' : ''}`} aria-label="Navegación principal">
          {navigation.map(({ id, label }) => (
            <a key={id} href={`#${id}`} className={active === id ? 'is-active' : ''} onClick={(event) => navigateTo(event, id)}>{label}</a>
          ))}
          <div className="landing-nav__mobile-actions">
            <ThemeToggle theme={theme} onToggle={onToggleTheme} compact />
            <a href="/login" onClick={close}>Iniciar sesión</a>
            <a href="/solicitar-acceso" onClick={close}>Solicitar acceso <ArrowRight size={15} /></a>
          </div>
        </nav>
        <div className="landing-header__actions">
          <ThemeToggle theme={theme} onToggle={onToggleTheme} />
          <a href="/login" className="landing-login-link">Iniciar sesión</a>
          <a href="/solicitar-acceso" className="landing-button landing-button--primary landing-button--route"><RouteAction iconSize={15}>Solicitar acceso</RouteAction></a>
        </div>
        <button ref={menuButton} type="button" className="landing-menu-button" onClick={() => setOpen((value) => !value)} aria-expanded={open} aria-controls="landing-mobile-menu" aria-label={open ? 'Cerrar menú' : 'Abrir menú'}>
          {open ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>
    </header>
  );
}

function HeroRoute() {
  return (
    <div className="landing-hero-route" aria-label="Demostración: una operación conectada desde la cotización hasta el cobro">
      <div className="landing-demo-label">Demostración del producto</div>
      <svg className="landing-route-line landing-route-line--hero" viewBox="0 0 760 172" preserveAspectRatio="none" aria-hidden="true" focusable="false">
        <path d="M35 86 H725" />
      </svg>
      <ol>
        {routeItems.map(({ type, value, detail, icon: Icon }, index) => (
          <li key={value} style={{ '--route-order': index }}>
            <span className="landing-route-node"><Icon size={19} /></span>
            <article>
              <small>{type}</small>
              <strong className={type === 'Inventario' ? undefined : 'landing-mono'}>{value}</strong>
              <span><Check size={12} /> {detail}</span>
            </article>
          </li>
        ))}
      </ol>
    </div>
  );
}

function Hero() {
  return (
    <section className="landing-hero is-visible" id="inicio">
      <div className="landing-shell landing-hero__grid">
        <div className="landing-hero__copy">
          <p className="landing-kicker">Gestión comercial para pymes peruanas</p>
          <h1>De la cotización al cobro, <span>sin perder el hilo.</span></h1>
          <p className="landing-hero__lead">Inkora conecta ventas, comprobantes electrónicos, inventario y cobranza en una sola operación.</p>
          <div className="landing-hero__actions">
            <a href="/solicitar-acceso" className="landing-button landing-button--primary landing-button--route"><RouteAction>Solicitar acceso</RouteAction></a>
            <a href="#recorrido" className="landing-button landing-button--text">Ver cómo funciona <ArrowDown size={16} /></a>
          </div>
          <p className="landing-hero__note"><span aria-hidden="true">↳</span> Una solicitud inicia el proceso de revisión; el acceso está sujeto a aprobación.</p>
        </div>
        <HeroRoute />
      </div>
    </section>
  );
}

function JourneyPreview({ step }) {
  return (
    <div className="landing-journey-preview" role="tabpanel" id="journey-panel" aria-labelledby={`journey-tab-${step}`} tabIndex="0">
      <div className="landing-sheet-fold" aria-hidden="true" />
      <div className="landing-demo-label">Datos sintéticos · demostración</div>
      <p>{journey[step].eyebrow}</p>
      <strong className="landing-folio">{journey[step].folio}</strong>
      <dl>
        {journey[step].rows.map(([term, value]) => <div key={term}><dt>{term}</dt><dd className={['Total', 'Importe', 'Saldo', 'SUNAT', 'Evidencia'].includes(term) ? 'landing-mono' : undefined}>{value}</dd></div>)}
      </dl>
      <span className="landing-status"><CheckCircle2 size={14} /> {journey[step].status}</span>
    </div>
  );
}

function Journey() {
  const [step, setStep] = useState(0);
  const [direction, setDirection] = useState('forward');
  const tabs = useRef([]);

  const changeStep = (next, nextDirection = next >= step ? 'forward' : 'backward') => {
    if (next === step) return;
    setDirection(nextDirection);
    setStep(next);
  };

  const selectByKey = (event, index) => {
    let next = index;
    let nextDirection = 'forward';
    if (event.key === 'ArrowRight' || event.key === 'ArrowDown') next = (index + 1) % journey.length;
    else if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') { next = (index - 1 + journey.length) % journey.length; nextDirection = 'backward'; }
    else if (event.key === 'Home') { next = 0; nextDirection = 'backward'; }
    else if (event.key === 'End') next = journey.length - 1;
    else return;
    event.preventDefault();
    changeStep(next, nextDirection);
    tabs.current[next]?.focus();
  };

  return (
    <section className="landing-journey landing-reveal" id="recorrido" aria-labelledby="journey-title">
      <div className="landing-shell">
        <header className="landing-section-heading">
          <div><p>Cómo funciona</p><h2 id="journey-title">El hilo de una venta.</h2></div>
          <p>Una operación avanza. Su contexto y su evidencia avanzan con ella.</p>
        </header>
        <div className="landing-journey__layout">
          <div className="landing-journey__steps" role="tablist" aria-label="Etapas de una venta" aria-orientation="horizontal">
            {journey.map((item, index) => (
              <button
                key={item.label}
                ref={(element) => { tabs.current[index] = element; }}
                type="button"
                role="tab"
                id={`journey-tab-${index}`}
                aria-selected={step === index}
                aria-controls="journey-panel"
                tabIndex={step === index ? 0 : -1}
                className={step === index ? 'is-active' : ''}
                onClick={() => changeStep(index)}
                onKeyDown={(event) => selectByKey(event, index)}
              >
                <span>{String(index + 1).padStart(2, '0')}</span>
                <strong>{item.label}</strong>
              </button>
            ))}
          </div>
          <div className="landing-journey__story" data-direction={direction} aria-live="polite">
            <div className="landing-journey__copy" key={`copy-${step}`}><p>{journey[step].label}</p><h3>{journey[step].title}</h3><span>{journey[step].copy}</span></div>
            <JourneyPreview key={`preview-${step}`} step={step} />
          </div>
        </div>
      </div>
    </section>
  );
}

function Connected() {
  return (
    <section className="landing-connected landing-reveal" id="que-resuelve" aria-labelledby="connected-title">
      <div className="landing-shell">
        <header className="landing-section-heading landing-section-heading--wide">
          <div><p>Qué resuelve</p><h2 id="connected-title">Lo que permanece conectado.</h2></div>
          <p>Inkora evita que la información se corte justo cuando una venta cambia de etapa.</p>
        </header>
        <div className="landing-connected__editorial">
          <article className="landing-connected__fiscal">
            <div><FileCheck2 size={24} /><span>Estado fiscal</span></div>
            <h3>La respuesta de SUNAT conserva sus evidencias.</h3>
            <p>El estado del comprobante, el XML y el CDR permanecen vinculados a la operación que los originó.</p>
            <div className="landing-evidence" aria-label="Ejemplo de evidencias disponibles">
              <span><b>XML</b><small>Generado</small></span><i /><span><b>CDR</b><small>Disponible</small></span><i /><span><b>SUNAT</b><small>Aceptado</small></span>
            </div>
          </article>
          <article className="landing-connected__inventory">
            <div><PackageCheck size={22} /><span>Inventario</span></div>
            <h3>El stock cambia con la operación.</h3>
            <p>Almacén, existencias y Kardex conservan el movimiento asociado.</p>
            <dl><div><dt>Antes</dt><dd>12</dd></div><div><dt>Ahora</dt><dd>11</dd></div></dl>
          </article>
          <article className="landing-connected__collection">
            <div><CircleDollarSign size={22} /><span>Cobranza</span></div>
            <h3>El saldo dice lo que falta, no lo que se emitió.</h3>
            <p>Pagos y cuotas se leen separados del total facturado.</p>
            <div className="landing-balance"><span>Total <b>S/ 498.00</b></span><span>Pagado <b>S/ 498.00</b></span><span>Saldo <b>S/ 0.00</b></span></div>
          </article>
        </div>
      </div>
    </section>
  );
}

function Trust() {
  const events = [
    ['09:42', 'Documento creado', 'La factura conserva la cotización de origen.'],
    ['09:43', 'Enviado al proveedor fiscal', 'El envío queda registrado para seguimiento.'],
    ['09:44', 'Aceptado por SUNAT', 'El estado fiscal se actualiza en la operación.'],
    ['09:44', 'XML y CDR disponibles', 'Las evidencias quedan asociadas al comprobante.'],
  ];
  return (
    <section className="landing-trust landing-reveal" id="confianza" aria-labelledby="trust-title">
      <div className="landing-shell landing-trust__layout">
        <header>
          <p>Confianza mediante producto</p>
          <h2 id="trust-title">Cada estado deja rastro.</h2>
          <span>La confianza no se presenta como una promesa abstracta: se ve en el recorrido del documento y en sus evidencias.</span>
          <div className="landing-trust__stamp"><ShieldCheck size={21} /><span>TRAZABILIDAD VISIBLE</span></div>
        </header>
        <ol className="landing-trace">
          {events.map(([time, title, copy], index) => (
            <li key={title}>
              <span className="landing-trace__node">{index === events.length - 1 ? <Check size={15} /> : index + 1}</span>
              <time>{time}</time>
              <div><strong>{title}</strong><p>{copy}</p></div>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

function ForWhom() {
  const profiles = [
    [Printer, 'Imprentas', 'Cotizaciones, productos y servicios que deben continuar hasta el comprobante y el cobro.'],
    [Store, 'Comercios', 'Ventas con inventario, documentos electrónicos y saldos que necesitan una sola lectura.'],
    [Building2, 'Equipos pequeños', 'Personas que comparten la operación y necesitan saber qué ocurrió sin reconstruirla.'],
  ];
  return (
    <section className="landing-fit landing-reveal" aria-labelledby="fit-title">
      <div className="landing-shell landing-fit__layout">
        <header><p>Para quién es</p><h2 id="fit-title">Para negocios que ya venden y necesitan ordenar lo que sigue.</h2></header>
        <div className="landing-fit__profiles">
          {profiles.map(([Icon, title, copy]) => (
            <article key={title}><Icon size={24} /><div><h3>{title}</h3><p>{copy}</p></div></article>
          ))}
        </div>
      </div>
    </section>
  );
}

function GettingStarted() {
  const steps = [
    ['Envía tu solicitud', 'Comparte los datos básicos de tu empresa desde el formulario de acceso.'],
    ['Revisamos la información', 'Verificamos los datos enviados antes de habilitar el espacio de trabajo.'],
    ['Habilitamos tu espacio', 'Si la solicitud es aprobada, podrás iniciar sesión y comenzar a operar.'],
  ];
  return (
    <section className="landing-start landing-reveal" aria-labelledby="start-title">
      <div className="landing-shell">
        <header className="landing-section-heading"><div><p>Cómo empezar</p><h2 id="start-title">Tres pasos antes de operar.</h2></div><p>La solicitud no activa una cuenta de forma automática: queda sujeta a revisión y aprobación.</p></header>
        <ol>
          {steps.map(([title, copy], index) => <li key={title}><span>{index + 1}</span><div><h3>{title}</h3><p>{copy}</p></div>{index < 2 && <ArrowRight aria-hidden="true" />}</li>)}
        </ol>
        <a href="/solicitar-acceso" className="landing-button landing-button--primary landing-button--route"><RouteAction>Solicitar acceso</RouteAction></a>
      </div>
    </section>
  );
}

function DocumentLookup() {
  const [fields, setFields] = useState(emptyLookup);
  const [errors, setErrors] = useState({});
  const [resultState, setResultState] = useState('waiting');
  const [result, setResult] = useState(null);
  const formRef = useRef(null);
  const resultRef = useRef(null);
  const lookupRequestRef = useRef(null);
  const resultType = result?.tipo_comprobante || fields.documentType;
  const documentLabel = { '01': 'FACTURA ELECTRÓNICA', '03': 'BOLETA ELECTRÓNICA', '07': 'NOTA DE CRÉDITO', '08': 'NOTA DE DÉBITO' }[resultType] || 'COMPROBANTE ELECTRÓNICO';
  const ResultStatusIcon = ['ANULADO', 'RECHAZADO'].includes(result?.estado) ? CircleX : result?.estado === 'EN_PROCESO' ? Clock3 : CheckCircle2;
  const formattedDate = result?.fecha_emision
    ? new Intl.DateTimeFormat('es-PE', { day: '2-digit', month: '2-digit', year: 'numeric', timeZone: 'UTC' }).format(new Date(`${result.fecha_emision}T00:00:00Z`))
    : '—';
  const formattedAmount = result
    ? new Intl.NumberFormat('es-PE', { style: 'currency', currency: result.moneda || 'PEN' }).format(Number(result.importe_total))
    : '—';

  useEffect(() => () => lookupRequestRef.current?.abort(), []);

  const update = (name, value) => {
    lookupRequestRef.current?.abort();
    const normalized = name === 'series' ? value.toUpperCase() : value;
    setFields((current) => ({ ...current, [name]: normalized }));
    setErrors((current) => ({ ...current, [name]: '' }));
    setResult(null);
    setResultState('waiting');
  };

  const validate = () => {
    const next = {};
    if (!/^\d{11}$/.test(fields.ruc)) next.ruc = 'Ingresa los 11 dígitos del RUC emisor.';
    if (!fields.documentType) next.documentType = 'Selecciona el tipo de comprobante.';
    if (!/^[A-Z0-9]{4}$/.test(fields.series)) next.series = 'Ingresa una serie de 4 caracteres.';
    if (!/^\d{1,8}$/.test(fields.number) || Number(fields.number) <= 0) next.number = 'Ingresa un correlativo válido sin guiones.';
    if (!fields.issueDate) next.issueDate = 'Selecciona la fecha de emisión.';
    if (!/^\d+(\.\d{1,2})?$/.test(fields.amount) || Number(fields.amount) <= 0) next.amount = 'Ingresa el importe total con hasta 2 decimales.';
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const submit = async (event) => {
    event.preventDefault();
    if (!validate()) {
      window.requestAnimationFrame(() => formRef.current?.querySelector('[aria-invalid="true"]')?.focus());
      return;
    }

    lookupRequestRef.current?.abort();
    const controller = new AbortController();
    lookupRequestRef.current = controller;
    setResult(null);
    setResultState('loading');
    let shouldFocusResult = true;

    try {
      const data = await publicReceipts.lookup({
        ruc: fields.ruc,
        tipo_comprobante: fields.documentType,
        serie: fields.series,
        correlativo: fields.number,
        fecha_emision: fields.issueDate,
        importe_total: fields.amount,
      }, { signal: controller.signal });
      setResult(data);
      setResultState('success');
    } catch (error) {
      if (error?.isCanceled) {
        shouldFocusResult = false;
        return;
      }
      if (error?.status === 404) setResultState('not-found');
      else if (error?.status === 429) setResultState('rate-limited');
      else setResultState('error');
    } finally {
      if (lookupRequestRef.current === controller) lookupRequestRef.current = null;
      if (shouldFocusResult) window.requestAnimationFrame(() => resultRef.current?.focus());
    }
  };

  const clearLookup = () => {
    lookupRequestRef.current?.abort();
    setFields(emptyLookup);
    setErrors({});
    setResult(null);
    setResultState('waiting');
    window.requestAnimationFrame(() => formRef.current?.querySelector('input')?.focus());
  };

  return (
    <section className="landing-lookup landing-reveal" id="consulta" aria-labelledby="lookup-title">
      <div className="landing-shell">
        <header className="landing-section-heading">
          <div><p>Consulta de comprobantes</p><h2 id="lookup-title">Cinco datos. Una respuesta legible.</h2></div>
          <p>Verifica facturas, boletas y sus notas relacionadas emitidas mediante Inkora. Los cinco datos deben coincidir con el comprobante.</p>
        </header>
        <div className="landing-lookup__desk">
          <form ref={formRef} className="landing-lookup__form" onSubmit={submit} noValidate>
            <div className="landing-lookup__form-heading">
              <div><span>VENTANILLA DE CONSULTA</span><h3>Datos del comprobante</h3></div>
              <span className="landing-plan__status">CONSULTA EN INKORA</span>
            </div>
            <div className="landing-lookup__fields">
              <label className="landing-field landing-field--wide">
                <span>RUC del emisor</span>
                <input value={fields.ruc} onChange={(event) => update('ruc', event.target.value.replace(/\D/g, '').slice(0, 11))} inputMode="numeric" autoComplete="off" maxLength="11" aria-invalid={Boolean(errors.ruc)} aria-describedby={errors.ruc ? 'lookup-ruc-error' : undefined} />
                {errors.ruc && <small id="lookup-ruc-error">{errors.ruc}</small>}
              </label>
              <DocumentTypeSelect value={fields.documentType} onChange={(value) => update('documentType', value)} invalid={Boolean(errors.documentType)} describedBy={errors.documentType ? 'lookup-type-error' : undefined} />
              <fieldset className="landing-document-number">
                <legend>Número del comprobante</legend>
                <div className="landing-document-number__fields">
                  <label className="landing-field">
                    <span>Serie</span>
                    <input value={fields.series} onChange={(event) => update('series', event.target.value.replace(/[^a-z0-9]/gi, '').slice(0, 4))} autoComplete="off" maxLength="4" aria-invalid={Boolean(errors.series)} aria-describedby={errors.series ? 'lookup-series-error' : undefined} />
                    {errors.series && <small id="lookup-series-error">{errors.series}</small>}
                  </label>
                  <label className="landing-field">
                    <span>Correlativo</span>
                    <input value={fields.number} onChange={(event) => update('number', event.target.value.replace(/\D/g, '').slice(0, 8))} inputMode="numeric" autoComplete="off" maxLength="8" aria-invalid={Boolean(errors.number)} aria-describedby={errors.number ? 'lookup-number-error' : undefined} />
                    {errors.number && <small id="lookup-number-error">{errors.number}</small>}
                  </label>
                </div>
              </fieldset>
              <IssueDatePicker value={fields.issueDate} onChange={(value) => update('issueDate', value)} invalid={Boolean(errors.issueDate)} describedBy={errors.issueDate ? 'lookup-date-error' : undefined} />
              <label className="landing-field">
                <span>Importe total</span>
                <span className="landing-money-input"><b>S/</b><input value={fields.amount} onChange={(event) => update('amount', event.target.value.replace(/[^\d.]/g, '').slice(0, 15))} inputMode="decimal" autoComplete="off" aria-invalid={Boolean(errors.amount)} aria-describedby={errors.amount ? 'lookup-amount-error' : undefined} /></span>
                {errors.amount && <small id="lookup-amount-error">{errors.amount}</small>}
              </label>
            </div>
            <div className="landing-lookup__actions">
              <button type="submit" className="landing-button landing-button--primary" disabled={resultState === 'loading'}><Search size={17} /> {resultState === 'loading' ? 'Consultando…' : 'Consultar comprobante'}</button>
              <button type="button" className="landing-button landing-button--text" onClick={clearLookup} disabled={resultState === 'loading'}>Limpiar formulario</button>
            </div>
            <a className="landing-lookup__source" href="https://ww1.sunat.gob.pe/ol-ti-itconsvalicpe/ConsValiCpe.htm" target="_blank" rel="noreferrer">Ver consulta oficial de SUNAT <ExternalLink size={13} /></a>
          </form>
          <div className="landing-lookup__result" ref={resultRef} tabIndex="-1" aria-live="polite" aria-atomic="true" aria-busy={resultState === 'loading'}>
            {resultState === 'success' && result ? (
              <>
                <div className="landing-lookup__result-top"><span className={`landing-status landing-status--${result.estado.toLowerCase().replace('_', '-')}`}><ResultStatusIcon size={14} /> {result.estado.replace('_', ' ')}</span><small>Resultado de Inkora</small></div>
                <div><p>{documentLabel}</p><strong className="landing-folio">{result.numero}</strong><span>{result.emisor}</span></div>
                <dl>
                  <div><dt>Estado del documento</dt><dd>{result.estado.replace('_', ' ')}</dd></div><div><dt>Fecha de emisión</dt><dd>{formattedDate}</dd></div><div><dt>Importe total</dt><dd>{formattedAmount}</dd></div>
                </dl>
                <div className="landing-lookup__evidence">
                  {Object.entries(result.evidencias).map(([type, available]) => <span className={available ? 'is-available' : 'is-unavailable'} key={type} aria-label={`${type.toUpperCase()}: ${available ? 'disponible' : 'no disponible'}`}>{available ? <Check size={11} /> : <X size={11} />}{type.toUpperCase()}</span>)}
                  <p>Disponibilidad registrada en Inkora. Esta consulta no descarga ni expone archivos fiscales.</p>
                </div>
              </>
            ) : resultState === 'loading' ? <div className="landing-lookup__waiting"><Search size={42} /><strong>Buscando coincidencia exacta…</strong><p>Estamos verificando los cinco datos en los comprobantes emitidos mediante Inkora.</p></div>
              : resultState === 'not-found' ? <div className="landing-lookup__waiting"><ReceiptText size={42} /><strong>No encontramos una coincidencia.</strong><p>Revisa el RUC del emisor, tipo, serie, correlativo, fecha e importe tal como aparecen en el comprobante.</p><button type="button" className="landing-button landing-button--dark" onClick={() => formRef.current?.querySelector('input')?.focus()}>Revisar datos</button></div>
                : resultState === 'rate-limited' ? <div className="landing-lookup__waiting"><ReceiptText size={42} /><strong>Alcanzaste el límite temporal.</strong><p>Espera un minuto antes de volver a consultar desde este dispositivo.</p></div>
                  : resultState === 'error' ? <div className="landing-lookup__waiting"><ReceiptText size={42} /><strong>No pudimos completar la consulta.</strong><p>Conservamos tus datos en el formulario. Revisa tu conexión e inténtalo nuevamente.</p><button type="button" className="landing-button landing-button--dark" onClick={() => formRef.current?.requestSubmit()}>Intentar de nuevo</button></div>
                    : <div className="landing-lookup__waiting"><ReceiptText size={42} /><strong>Completa la ficha y consulta.</strong><p>La respuesta aparecerá en esta misma hoja, sin mostrar datos del cliente ni abrir otra ventana.</p></div>}
          </div>
        </div>
      </div>
    </section>
  );
}

function Pricing() {
  const included = [
    'Cotizaciones y clientes',
    'Facturas, boletas y documentos electrónicos',
    'Productos, servicios e inventario',
    'Pagos, cuotas y saldos pendientes',
    'Reportes y trazabilidad documental',
  ];
  return (
    <section className="landing-pricing landing-reveal" id="precios" aria-labelledby="pricing-title">
      <div className="landing-shell landing-pricing__layout">
        <header>
          <p>Precio</p>
          <h2 id="pricing-title">Un solo plan para mantener la operación conectada.</h2>
          <span>Sin una tabla de niveles que te obligue a decidir qué parte del flujo dejar fuera.</span>
        </header>
        <article className="landing-plan">
          <div className="landing-plan__top">
            <div><span>PLAN INKORA</span><h3>Precio confirmado durante la revisión</h3></div>
            <span className="landing-plan__status">TARIFA AÚN NO PUBLICADA</span>
          </div>
          <ul>{included.map((item) => <li key={item}><Check size={16} /> <span>{item}</span></li>)}</ul>
          <div className="landing-plan__action">
            <p>Solicita acceso para conocer la condición comercial vigente antes de la habilitación.</p>
            <a href="/solicitar-acceso" className="landing-button landing-button--primary landing-button--route"><RouteAction>Solicitar acceso</RouteAction></a>
          </div>
        </article>
      </div>
    </section>
  );
}

function FAQ() {
  return (
    <section className="landing-faq landing-reveal" aria-labelledby="faq-title">
      <div className="landing-shell landing-faq__layout">
        <header><p>Preguntas frecuentes</p><h2 id="faq-title">Antes de solicitar acceso.</h2><span>Respuestas directas sobre el producto y el proceso de alta.</span></header>
        <div>{faqs.map(([question, answer]) => <details key={question}><summary>{question}<ChevronDown size={19} /></summary><div className="landing-faq__answer"><p>{answer}</p></div></details>)}</div>
      </div>
    </section>
  );
}

function FinalCTA() {
  return (
    <section className="landing-final" aria-labelledby="final-title">
      <div className="landing-shell landing-final__inner">
        <svg viewBox="0 0 1100 150" preserveAspectRatio="none" aria-hidden="true" focusable="false"><path d="M0 76 H760 Q820 76 820 122 H1070" /><circle cx="1070" cy="122" r="10" /></svg>
        <div><p>El siguiente paso</p><h2 id="final-title">Que tu próxima venta no pierda el hilo.</h2></div>
        <div><a href="/solicitar-acceso" className="landing-button landing-button--dark landing-button--route"><RouteAction iconSize={18}>Solicitar acceso</RouteAction></a><span>Sujeto a revisión y aprobación.</span></div>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="landing-footer">
      <div className="landing-shell landing-footer__inner">
        <div><Brand /><p>Gestión comercial para pymes peruanas.</p></div>
        <nav aria-label="Enlaces del producto"><strong>Producto</strong><a href="#que-resuelve">Qué resuelve</a><a href="#recorrido">Cómo funciona</a><a href="#confianza">Confianza</a><a href="#consulta">Consulta</a><a href="#precios">Precio</a></nav>
        <nav aria-label="Enlaces de acceso"><strong>Acceso</strong><a href="/login">Iniciar sesión</a><a href="/solicitar-acceso">Solicitar acceso</a></nav>
      </div>
      <div className="landing-shell landing-footer__bottom"><span>© {new Date().getFullYear()} Inkora</span><span>Operación conectada, de la cotización al cobro.</span></div>
    </footer>
  );
}

function useLandingMetadata() {
  useEffect(() => {
    const previousTitle = document.title;
    document.title = 'Inkora | Gestión comercial para pymes peruanas';
    const records = [];
    const setMeta = (selector, attributes) => {
      let element = document.head.querySelector(selector);
      const created = !element;
      if (!element) { element = document.createElement(attributes.tag || 'meta'); document.head.appendChild(element); }
      const previous = {};
      Object.entries(attributes).forEach(([key, value]) => {
        if (key === 'tag') return;
        previous[key] = element.getAttribute(key);
        element.setAttribute(key, value);
      });
      records.push({ element, created, previous });
    };
    setMeta('meta[name="description"]', { name: 'description', content: 'Inkora conecta ventas, comprobantes electrónicos, inventario y cobranza para pymes peruanas.' });
    setMeta('meta[property="og:title"]', { property: 'og:title', content: 'Inkora | De la cotización al cobro' });
    setMeta('meta[property="og:description"]', { property: 'og:description', content: 'Una sola operación para vender, emitir, controlar y cobrar.' });
    setMeta('meta[property="og:type"]', { property: 'og:type', content: 'website' });
    setMeta('link[rel="canonical"]', { tag: 'link', rel: 'canonical', href: `${window.location.origin}/` });
    return () => {
      document.title = previousTitle;
      records.forEach(({ element, created, previous }) => {
        if (created) element.remove();
        else Object.entries(previous).forEach(([key, value]) => value === null ? element.removeAttribute(key) : element.setAttribute(key, value));
      });
    };
  }, []);
}

function useRouteReveal() {
  useEffect(() => {
    const page = document.querySelector('.landing-page');
    const heroRoute = document.querySelector('.landing-hero-route');
    if (!page || !heroRoute || !('IntersectionObserver' in window)) { page?.classList.add('route-visible'); return undefined; }
    const observer = new IntersectionObserver(([entry]) => {
      if (!entry.isIntersecting) return;
      page.classList.add('route-visible');
      observer.disconnect();
    }, { threshold: 0.08 });
    observer.observe(heroRoute);
    return () => observer.disconnect();
  }, []);
}

export default function LandingPage() {
  const [theme, setTheme] = useState(() => {
    const saved = window.localStorage.getItem('inkora-landing-theme');
    if (saved === 'light' || saved === 'dark') return saved;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  });
  useLandingMetadata();
  useRouteReveal();

  useEffect(() => {
    window.localStorage.setItem('inkora-landing-theme', theme);
  }, [theme]);

  const navigateFromPageLink = (event) => {
    if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    const anchor = event.target.closest('a[href^="#"]');
    if (!anchor) return;
    const id = anchor.getAttribute('href')?.slice(1);
    const target = id ? document.getElementById(id) : null;
    if (!target) return;
    event.preventDefault();
    window.history.pushState(null, '', `#${id}`);
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    target.scrollIntoView({ behavior: reducedMotion ? 'auto' : 'smooth', block: 'start' });
  };

  return (
    <div className="landing-page" data-theme={theme} onClick={navigateFromPageLink}>
      <a className="landing-skip" href="#contenido">Saltar al contenido</a>
      <Header theme={theme} onToggleTheme={() => setTheme((current) => current === 'dark' ? 'light' : 'dark')} />
      <main id="contenido">
        <Hero />
        <Journey />
        <Connected />
        <ForWhom />
        <Trust />
        <GettingStarted />
        <DocumentLookup />
        <Pricing />
        <FAQ />
        <FinalCTA />
      </main>
      <Footer />
    </div>
  );
}
