import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Asterisk,
  ArrowRight,
  BarChart3,
  Bell,
  Boxes,
  Check,
  CheckCircle2,
  ChevronDown,
  CircleDollarSign,
  Download,
  FileCheck2,
  FileSearch,
  FileText,
  LayoutDashboard,
  Menu,
  PackageCheck,
  ReceiptText,
  Search,
  ShieldCheck,
  UserRound,
  Users,
  Warehouse,
  X,
} from 'lucide-react';
import '../styles/landing.css';

const workflow = [
  { number: '01', title: 'Cotiza', copy: 'Prepara una propuesta clara y reutiliza los datos de tu cliente.' },
  { number: '02', title: 'Vende', copy: 'Convierte la operación sin volver a escribir productos ni condiciones.' },
  { number: '03', title: 'Emite', copy: 'Sigue el envío fiscal y reconoce cuándo el comprobante fue aceptado.' },
  { number: '04', title: 'Controla', copy: 'Mantén existencias, almacenes y Kardex conectados con la venta.' },
  { number: '05', title: 'Cobra', copy: 'Registra pagos y distingue lo cobrado de lo que aún está pendiente.' },
];

const modules = [
  {
    index: '01',
    eyebrow: 'Ventas',
    title: 'De la conversación al comprobante.',
    copy: 'Clientes, productos y cotizaciones permanecen conectados para que cada venta avance sin trabajo duplicado.',
    icon: FileText,
    tone: 'light',
  },
  {
    index: '02',
    eyebrow: 'Facturación electrónica',
    title: 'El estado fiscal, explicado con claridad.',
    copy: 'Facturas, boletas y documentos relacionados con estados visibles y evidencia fiscal disponible para tu equipo.',
    icon: FileCheck2,
    tone: 'green',
  },
  {
    index: '03',
    eyebrow: 'Inventario',
    title: 'Stock que cuenta la historia completa.',
    copy: 'Existencias, movimientos, almacenes y Kardex para saber qué tienes, dónde está y cómo cambió.',
    icon: Boxes,
    tone: 'mist',
  },
  {
    index: '04',
    eyebrow: 'Cobranza',
    title: 'Vender no termina al emitir.',
    copy: 'Cuotas, pagos y saldos pendientes en una vista diseñada para decidir a quién dar seguimiento.',
    icon: CircleDollarSign,
    tone: 'dark',
  },
];

const faqs = [
  ['¿Inkora es solo un facturador?', 'No. Inkora conecta cotizaciones, ventas, comprobantes electrónicos, inventario y cobranza en un mismo recorrido comercial.'],
  ['¿Cómo se relaciona Inkora con SUNAT?', 'Inkora procesa la emisión mediante el proveedor fiscal configurado y muestra el estado de cada documento para que tu equipo sepa qué fue aceptado y qué necesita atención.'],
  ['¿Necesito instalar un programa?', 'No. Inkora funciona desde el navegador para que tu equipo pueda trabajar con una única fuente de información.'],
  ['¿Puedo controlar productos y servicios?', 'Sí. Puedes organizar tu catálogo y diferenciar productos inventariables de servicios que no afectan stock.'],
  ['¿Cómo empiezo?', 'Solicita acceso y revisaremos la información básica de tu empresa antes de habilitar tu espacio de trabajo.'],
];

const navigationSections = [
  { id: 'producto', label: 'Producto' },
  { id: 'recorrido', label: 'Cómo funciona' },
  { id: 'negocios', label: 'Para tu negocio' },
  { id: 'seguridad', label: 'Confianza' },
];

function Brand({ inverse = false }) {
  return (
    <span className={`landing-brand${inverse ? ' landing-brand--inverse' : ''}`} aria-label="Inkora">
      <span className="landing-brand__mark" aria-hidden="true"><Asterisk size={30} strokeWidth={3.4} /></span>
      <strong>Inkora</strong>
    </span>
  );
}

function useInView() {
  const ref = useRef(null);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const element = ref.current;
    if (!element || !('IntersectionObserver' in window)) {
      setIsVisible(true);
      return undefined;
    }

    const observer = new IntersectionObserver(([entry]) => {
      if (!entry.isIntersecting) return;
      setIsVisible(true);
      observer.unobserve(entry.target);
    }, { threshold: 0.14, rootMargin: '0px 0px -6% 0px' });

    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  return { ref, isVisible };
}

function RevealSection({ as: Tag = 'section', children, className = '', ...props }) {
  const { ref, isVisible } = useInView();
  return <Tag ref={ref} className={`${className} landing-reveal${isVisible ? ' is-visible' : ''}`.trim()} {...props}>{children}</Tag>;
}

function DashboardPreview({ compact = false }) {
  return (
    <div className={`landing-app${compact ? ' landing-app--compact' : ''}`} aria-label="Vista demostrativa del dashboard de Inkora">
      <aside className="landing-app__rail" aria-hidden="true">
        <span className="landing-app__logo" aria-hidden="true"><Asterisk size={22} strokeWidth={3.4} /></span>
        <span className="is-active"><LayoutDashboard size={15} /></span>
        <span><FileText size={15} /></span>
        <span><Users size={15} /></span>
        <span><Boxes size={15} /></span>
        <span><BarChart3 size={15} /></span>
      </aside>
      <div className="landing-app__body" aria-hidden="true">
        <header className="landing-app__top">
          <div><strong>Dashboard</strong><small>Centro de control diario</small></div>
          <div className="landing-app__search"><Search size={13} /><span>Buscar en Inkora...</span></div>
          <span className="landing-app__sunat"><i /> SUNAT</span>
          <span className="landing-app__round"><Bell size={13} /></span>
          <span className="landing-app__round"><UserRound size={13} /></span>
        </header>
        <main className="landing-app__content">
          <div className="landing-app__welcome">
            <div><small>RESUMEN DE HOY</small><strong>Tu negocio, en una sola vista.</strong></div>
            <span>Miércoles, 23 de julio</span>
          </div>
          <div className="landing-app__metrics">
            <article><span>Ventas emitidas</span><strong>S/ 4,800.40</strong><small>Este mes</small></article>
            <article><span>Cobrado</span><strong>S/ 3,420.00</strong><small>Pagos aplicados</small></article>
            <article><span>Pendiente</span><strong>S/ 1,380.40</strong><small>Por cobrar</small></article>
          </div>
          <div className="landing-app__grid">
            <article className="landing-app__chart">
              <div><strong>Actividad comercial</strong><span>Últimos 7 días</span></div>
              <div className="landing-app__bars" aria-hidden="true">
                {[35, 58, 44, 78, 63, 86, 70].map((height, index) => <i key={index} style={{ height: `${height}%` }} />)}
              </div>
              <footer><span>L</span><span>M</span><span>M</span><span>J</span><span>V</span><span>S</span><span>D</span></footer>
            </article>
            <article className="landing-app__recent">
              <div><strong>Últimos documentos</strong><span>Ver todos</span></div>
              <p><span>F001-00184</span><b>S/ 480.00</b><em>Aceptada</em></p>
              <p><span>B001-00072</span><b>S/ 130.00</b><em>Aceptada</em></p>
              <p><span>COT-00061</span><b>S/ 580.00</b><em className="is-pending">Pendiente</em></p>
            </article>
          </div>
        </main>
      </div>
      {!compact && (
        <>
          <div className="landing-app__float landing-app__float--sunat" aria-hidden="true"><CheckCircle2 size={16} /><span>Estado fiscal<strong>Factura aceptada</strong></span></div>
          <div className="landing-app__float landing-app__float--stock" aria-hidden="true"><PackageCheck size={16} /><span>Inventario<strong>Stock actualizado</strong></span></div>
        </>
      )}
    </div>
  );
}

function QuoteScreen() {
  return (
    <div className="landing-quote-screen" aria-hidden="true">
      <header><span>Cotización nueva</span><b>COT-00072</b></header>
      <div className="landing-quote-screen__fields"><i /><i /><i /></div>
      <div className="landing-quote-screen__line"><span>100 tarjetas corporativas</span><b>S/ 480.00</b></div>
      <footer><span>Total</span><strong>S/ 480.00</strong></footer>
    </div>
  );
}

function InventoryScreen() {
  const rows = [
    ['Papel couché A4', '246', 'ok'],
    ['Tinta negra', '54', 'ok'],
    ['Cajas kraft', '18', 'low'],
  ];
  return (
    <div className="landing-inventory-screen" aria-hidden="true">
      <header><Warehouse size={16} /><span>Inventario · Almacén principal</span></header>
      {rows.map(([name, stock, state]) => (
        <p key={name}><i className={state} /><span>{name}</span><b>{stock}</b></p>
      ))}
    </div>
  );
}

function FiscalScreen() {
  return (
    <div className="landing-fiscal-screen" aria-hidden="true">
      <span><Check size={18} /></span>
      <div><small>FACTURA F001-000184</small><strong>Aceptada por SUNAT</strong><p>CDR y XML disponibles</p></div>
    </div>
  );
}

function CollectionScreen() {
  return (
    <div className="landing-collection-screen" aria-hidden="true">
      <div><small>SALDO PENDIENTE</small><strong>S/ 2,340.00</strong></div>
      <div className="landing-collection-screen__track"><i /></div>
      <span>3 documentos requieren seguimiento</span>
    </div>
  );
}

function SaleScreen() {
  return (
    <div className="landing-sale-screen" aria-hidden="true">
      <header><span>Venta en preparación</span><b>01</b></header>
      <div className="landing-sale-screen__client"><span>Cliente</span><strong>Comercial Andina S.A.C.</strong></div>
      <div className="landing-sale-screen__items"><p><span>Tarjetas corporativas</span><b>S/ 480.00</b></p><p><span>Delivery</span><b>S/ 18.00</b></p></div>
      <footer><span>Total por emitir</span><strong>S/ 498.00</strong></footer>
    </div>
  );
}

function OperationFlowVisual() {
  const items = [
    { label: 'Cotización', detail: 'COT-00072', icon: FileText },
    { label: 'Comprobante', detail: 'F001-00184', icon: FileCheck2 },
    { label: 'Inventario', detail: '−100 unidades', icon: Boxes },
    { label: 'Cobranza', detail: 'S/ 498.00', icon: CircleDollarSign },
  ];

  return (
    <div className="landing-operation-flow" aria-label="Flujo conectado desde la cotización hasta la cobranza">
      <div className="landing-operation-flow__header"><span>RECORRIDO DE UNA VENTA</span><strong>Todo conserva su contexto</strong></div>
      <div className="landing-operation-flow__track" aria-hidden="true">
        {items.map(({ label, detail, icon: Icon }, index) => (
          <article key={label} style={{ '--flow-order': index }}>
            <span><Icon size={18} /></span>
            <small>{label}</small>
            <strong>{detail}</strong>
            {index < items.length - 1 && <i />}
          </article>
        ))}
      </div>
      <footer><CheckCircle2 size={16} /><span>Una sola operación · cuatro áreas actualizadas</span></footer>
    </div>
  );
}

function WorkflowPreview({ activeStep }) {
  const previews = [
    { eyebrow: '01 · Cotiza', title: 'Propuesta lista para compartir', visual: <QuoteScreen /> },
    { eyebrow: '02 · Vende', title: 'Datos preparados para la emisión', visual: <SaleScreen /> },
    { eyebrow: '03 · Emite', title: 'Estado fiscal visible para el equipo', visual: <FiscalScreen /> },
    { eyebrow: '04 · Controla', title: 'Existencias actualizadas con cada salida', visual: <InventoryScreen /> },
    { eyebrow: '05 · Cobra', title: 'El saldo pendiente no se pierde de vista', visual: <CollectionScreen /> },
  ];
  const current = previews[activeStep] || previews[0];

  return (
    <aside className="landing-workflow-preview" aria-live="polite" aria-label={`Vista de la etapa ${current.eyebrow}`}>
      <header><span>{current.eyebrow}</span><i>Vista de producto</i></header>
      <h3>{current.title}</h3>
      <div className="landing-workflow-preview__screen" key={activeStep}>{current.visual}</div>
      <footer><span>Inkora mantiene el hilo</span><strong>{String(activeStep + 1).padStart(2, '0')} / 05</strong></footer>
    </aside>
  );
}

function DocumentLookupPreview() {
  return (
    <div className="landing-lookup-preview" aria-label="Vista conceptual de consulta de comprobantes">
      <header><span><FileSearch size={17} /> Consulta de documentos</span><b>PRÓXIMAMENTE</b></header>
      <div className="landing-lookup-preview__search"><Search size={16} /><span>F001-00184 · 20601234567</span><button type="button" disabled>Buscar</button></div>
      <article>
        <div><small>FACTURA ELECTRÓNICA</small><strong>F001-00184</strong><span>Comercial Andina S.A.C.</span></div>
        <div><em><CheckCircle2 size={13} /> Aceptada</em><strong>S/ 498.00</strong></div>
      </article>
      <footer><span><FileText size={15} /> PDF disponible</span><span><Download size={15} /> Descarga segura</span></footer>
    </div>
  );
}

function AuditTrailPreview() {
  const events = [
    ['09:42', 'Factura creada', 'Usuario autorizado'],
    ['09:43', 'Enviada al proveedor fiscal', 'Job fiscal #184'],
    ['09:44', 'Aceptada por SUNAT', 'CDR disponible'],
  ];
  return (
    <div className="landing-audit-preview" aria-label="Ejemplo de trazabilidad documental con información ficticia">
      <header><span>TRAZABILIDAD · F001-00184</span><em><i /> Evidencia completa</em></header>
      <div>
        {events.map(([time, title, detail], index) => (
          <article key={title}><span>{time}</span><i className={index === events.length - 1 ? 'is-current' : ''} /><p><strong>{title}</strong><small>{detail}</small></p></article>
        ))}
      </div>
      <footer><ShieldCheck size={16} /><span>Información sintética para demostración</span></footer>
    </div>
  );
}

function FinalProductComposition() {
  return (
    <div className="landing-final-product" aria-hidden="true">
      <div className="landing-final-product__dashboard">
        <header><Asterisk size={21} strokeWidth={3.4} aria-hidden="true" /><span>Resumen operativo</span></header>
        <div><small>Ventas del mes</small><strong>S/ 4,800.40</strong></div>
        <p><i style={{ height: '42%' }} /><i style={{ height: '68%' }} /><i style={{ height: '55%' }} /><i style={{ height: '86%' }} /><i style={{ height: '73%' }} /></p>
      </div>
      <div className="landing-final-product__document"><small>FACTURA ELECTRÓNICA</small><strong>F001-00184</strong><span><CheckCircle2 size={14} /> Aceptada por SUNAT</span></div>
    </div>
  );
}

function ModuleVisual({ tone }) {
  if (tone === 'light') return <QuoteScreen />;
  if (tone === 'green') return <FiscalScreen />;
  if (tone === 'mist') return <InventoryScreen />;
  return <CollectionScreen />;
}

function LandingHeader() {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [activeSection, setActiveSection] = useState('inicio');
  const close = () => setOpen(false);

  useEffect(() => {
    let frameId;
    const updateScrollState = () => {
      window.cancelAnimationFrame(frameId);
      frameId = window.requestAnimationFrame(() => setScrolled(window.scrollY > 24));
    };
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') setOpen(false);
    };
    const sections = ['inicio', ...navigationSections.map(({ id }) => id)]
      .map((id) => document.getElementById(id))
      .filter(Boolean);
    const observer = new IntersectionObserver((entries) => {
      const visible = entries.filter((entry) => entry.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio);
      if (visible[0]) setActiveSection(visible[0].target.id);
    }, { rootMargin: '-28% 0px -58% 0px', threshold: [0, .15, .4] });

    sections.forEach((section) => observer.observe(section));
    updateScrollState();
    window.addEventListener('scroll', updateScrollState, { passive: true });
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.cancelAnimationFrame(frameId);
      observer.disconnect();
      window.removeEventListener('scroll', updateScrollState);
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, []);

  useEffect(() => setOpen(false), [activeSection]);

  return (
    <header className={`landing-header${scrolled ? ' is-scrolled' : ''}`}>
      <div className="landing-header__inner">
        <a href="#inicio" className="landing-header__brand" onClick={close}><Brand inverse /></a>
        <nav className={`landing-nav${open ? ' is-open' : ''}`} aria-label="Navegación principal">
          {navigationSections.map(({ id, label }) => <a className={activeSection === id ? 'is-active' : ''} href={`#${id}`} onClick={close} aria-current={activeSection === id ? 'location' : undefined} key={id}>{label}</a>)}
          <div className="landing-nav__mobile-actions">
            <Link to="/login" onClick={close}>Iniciar sesión</Link>
            <Link to="/solicitar-acceso" onClick={close}>Solicitar acceso</Link>
          </div>
        </nav>
        <div className="landing-header__actions">
          <Link to="/login" className="landing-login-link">Iniciar sesión</Link>
          <Link to="/solicitar-acceso" className="landing-button landing-button--dark">Solicitar acceso <ArrowRight size={16} /></Link>
        </div>
        <button type="button" className="landing-menu-button" onClick={() => setOpen((value) => !value)} aria-expanded={open} aria-label={open ? 'Cerrar menú' : 'Abrir menú'}>
          {open ? <X size={21} /> : <Menu size={21} />}
        </button>
      </div>
    </header>
  );
}

export default function LandingPage() {
  const [activeWorkflowStep, setActiveWorkflowStep] = useState(0);
  const workflowRefs = useRef([]);

  useEffect(() => {
    const previousTitle = document.title;
    document.title = 'Inkora | Gestión comercial para pymes peruanas';
    return () => { document.title = previousTitle; };
  }, []);

  useEffect(() => {
    const elements = workflowRefs.current.filter(Boolean);
    const observer = new IntersectionObserver((entries) => {
      const candidate = entries.filter((entry) => entry.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
      if (candidate) setActiveWorkflowStep(Number(candidate.target.dataset.step));
    }, { rootMargin: '-32% 0px -44% 0px', threshold: [0, .2, .55] });
    elements.forEach((element) => observer.observe(element));
    return () => observer.disconnect();
  }, []);

  return (
    <div className="landing-page">
      <a className="landing-skip" href="#contenido">Saltar al contenido</a>
      <LandingHeader />

      <main id="contenido">
        <section className="landing-hero landing-reveal is-visible" id="inicio">
          <div className="landing-shell landing-hero__grid">
            <div className="landing-hero__copy">
              <p className="landing-kicker"><i /> Gestión comercial para pymes peruanas</p>
              <h1>Vender es difícil.<br /><span>Ordenarlo</span> no debería serlo.</h1>
              <p className="landing-hero__lead">Cotiza, emite comprobantes electrónicos, sigue su estado SUNAT y controla inventario y cobros sin repartir la operación entre sistemas desconectados.</p>
              <div className="landing-hero__actions">
                <Link to="/solicitar-acceso" className="landing-button landing-button--primary">Solicitar acceso <ArrowRight size={17} /></Link>
                <a href="#recorrido" className="landing-button landing-button--secondary">Ver cómo funciona</a>
              </div>
              <div className="landing-hero__promise" aria-label="Beneficios principales">
                <span><Check size={13} /> Sin instalaciones</span>
                <span><Check size={13} /> Información centralizada</span>
                <span><Check size={13} /> Pensado para Perú</span>
              </div>
            </div>
            <div className="landing-hero__product">
              <span className="landing-hero__orb landing-hero__orb--one" aria-hidden="true" />
              <span className="landing-hero__orb landing-hero__orb--two" aria-hidden="true" />
              <DashboardPreview />
            </div>
          </div>
        </section>

        <div className="landing-capability-rail" aria-label="Funciones principales">
          <div className="landing-shell">
            <span>Cotizaciones</span><i />
            <span>Facturación electrónica</span><i />
            <span>Seguimiento SUNAT</span><i />
            <span>Inventario y Kardex</span><i />
            <span>Cobranza</span>
          </div>
        </div>

        <RevealSection className="landing-statement">
          <div className="landing-shell landing-statement__grid">
            <p className="landing-section-label">Una operación conectada</p>
            <div className="landing-statement__copy">
              <h2>Tu negocio no necesita más pantallas. <span>Necesita que cada dato llegue a donde corresponde.</span></h2>
              <p>Inkora conecta el recorrido comercial para que una cotización no quede aislada de la factura, el stock no quede separado de la venta y el cobro no dependa de la memoria.</p>
            </div>
            <OperationFlowVisual />
          </div>
        </RevealSection>

        <RevealSection className="landing-product" id="producto">
          <div className="landing-shell">
            <div className="landing-section-heading">
              <div><p className="landing-section-label">El producto</p><h2>Control sin la complejidad de un ERP.</h2></div>
              <p>Herramientas concretas para los procesos que una pyme repite todos los días.</p>
            </div>
            <div className="landing-module-grid">
              {modules.map(({ index, eyebrow, title, copy, icon: Icon, tone }) => (
                <article className={`landing-module landing-module--${tone}`} key={title} style={{ '--reveal-order': Number(index) }}>
                  <div className="landing-module__meta"><span>{index}</span><p><Icon size={14} /> {eyebrow}</p></div>
                  <h3>{title}</h3>
                  <p>{copy}</p>
                  <div className="landing-module__visual"><ModuleVisual tone={tone} /></div>
                </article>
              ))}
            </div>
          </div>
        </RevealSection>

        <RevealSection className="landing-workflow" id="recorrido">
          <div className="landing-shell">
            <div className="landing-section-heading">
              <div><p className="landing-section-label">Cómo funciona</p><h2>Una venta, de principio a fin.</h2></div>
              <p>Cada etapa conserva el contexto de la anterior. Menos tareas repetidas, más claridad para decidir.</p>
            </div>
            <div className="landing-workflow__body">
              <ol className="landing-workflow__list">
                {workflow.map((item, itemIndex) => (
                  <li className={activeWorkflowStep === itemIndex ? 'is-active' : ''} data-step={itemIndex} key={item.number} onFocus={() => setActiveWorkflowStep(itemIndex)} onMouseEnter={() => setActiveWorkflowStep(itemIndex)} ref={(element) => { workflowRefs.current[itemIndex] = element; }} style={{ '--reveal-order': itemIndex + 1 }} tabIndex="0">
                    <span>{item.number}</span>
                    <strong>{item.title}</strong>
                    <p>{item.copy}</p>
                    <ArrowRight size={17} aria-hidden="true" />
                  </li>
                ))}
              </ol>
              <WorkflowPreview activeStep={activeWorkflowStep} />
            </div>
          </div>
        </RevealSection>

        <RevealSection className="landing-audience" id="negocios">
          <div className="landing-shell landing-audience__grid">
            <div className="landing-audience__copy">
              <p className="landing-section-label">Pensado para el trabajo real</p>
              <h2>Para empresas que venden productos, servicios o ambos.</h2>
              <p>No necesitas adaptar tu negocio a un sistema contable enorme. Inkora organiza el flujo comercial que comparten comercios, distribuidoras y empresas de servicios.</p>
              <div className="landing-audience__tags" aria-label="Negocios que pueden usar Inkora">
                <span>Comercios</span>
                <span>Distribuidoras</span>
                <span>Servicios</span>
              </div>
              <Link to="/solicitar-acceso" className="landing-inline-link">Cuéntanos cómo trabaja tu empresa <ArrowRight size={16} /></Link>
            </div>
            <div className="landing-photo-story">
              <figure className="landing-photo-story__primary">
                <img src="/landing/pyme-tienda.webp" alt="Emprendedora peruana organizando su negocio desde una laptop" loading="lazy" width="1536" height="1024" />
                <figcaption><span>Comercio conectado</span><strong>Más tiempo para atender. Menos para ordenar archivos.</strong></figcaption>
              </figure>
              <figure className="landing-photo-story__secondary">
                <img src="/landing/pyme-inventario.webp" alt="Equipo de una pyme peruana revisando inventario y pedidos" loading="lazy" width="1536" height="1024" />
                <figcaption><Warehouse size={15} /><span>Inventario visible para todo el equipo</span></figcaption>
              </figure>
              <div className="landing-photo-story__badge"><span>01</span><strong>Tu operación</strong><small>Productos · documentos · cobros</small></div>
            </div>
          </div>
        </RevealSection>

        <RevealSection className="landing-consultation" aria-labelledby="consultation-title">
          <div className="landing-shell landing-consultation__card">
            <div>
              <p className="landing-section-label">Consulta de comprobantes</p>
              <h2 id="consultation-title">Tus clientes también merecen claridad.</h2>
              <p>Estamos preparando un acceso seguro para consultar y recuperar los comprobantes emitidos desde Inkora.</p>
            </div>
            <div><div className="landing-consultation__status"><span><ReceiptText size={20} /></span><div><small>PRÓXIMAMENTE</small><strong>Consulta segura de documentos</strong><p>Esta función aún no recibe ni consulta datos.</p></div></div><DocumentLookupPreview /></div>
          </div>
        </RevealSection>

        <RevealSection className="landing-trust" id="seguridad">
          <div className="landing-shell">
            <div className="landing-section-heading landing-section-heading--inverse">
              <div><p className="landing-section-label">Confianza operativa</p><h2>La tranquilidad también forma parte del producto.</h2></div>
              <p>Inkora hace visible qué ocurrió, quién puede operar y en qué estado se encuentra cada documento.</p>
            </div>
            <div className="landing-trust__grid">
              <article><span>01</span><ShieldCheck size={20} /><strong>Información separada por empresa</strong><p>Cada organización trabaja dentro de su propio espacio y con accesos controlados.</p></article>
              <article><span>02</span><FileCheck2 size={20} /><strong>Trazabilidad documental</strong><p>Estados, relaciones y evidencias ayudan a entender el recorrido de cada operación.</p></article>
              <article><span>03</span><PackageCheck size={20} /><strong>Estados reales y visibles</strong><p>Las alertas distinguen lo pendiente, lo procesado y lo que requiere atención.</p></article>
            </div>
            <AuditTrailPreview />
          </div>
        </RevealSection>

        <RevealSection className="landing-faq" id="preguntas">
          <div className="landing-shell landing-faq__grid">
            <div><p className="landing-section-label">Preguntas frecuentes</p><h2>Antes de empezar.</h2></div>
            <div className="landing-faq__list">
              {faqs.map(([question, answer]) => (
                <details key={question}>
                  <summary>{question}<ChevronDown size={18} /></summary>
                  <p>{answer}</p>
                </details>
              ))}
            </div>
          </div>
        </RevealSection>

        <RevealSection className="landing-final-cta">
          <div className="landing-shell landing-final-cta__inner">
            <div className="landing-final-cta__copy">
              <p>Una nueva forma de trabajar</p>
              <h2>Ordena hoy la próxima etapa de tu empresa.</h2>
              <div>
                <Link to="/solicitar-acceso" className="landing-button landing-button--primary">Solicitar acceso <ArrowRight size={17} /></Link>
                <Link to="/login" className="landing-button landing-button--secondary">Ya uso Inkora</Link>
              </div>
            </div>
            <FinalProductComposition />
          </div>
        </RevealSection>
      </main>

      <footer className="landing-footer">
        <div className="landing-shell landing-footer__top">
          <div><Brand inverse /><p>Gestión comercial para pymes peruanas.</p></div>
          <div><strong>Producto</strong><a href="#producto">Módulos</a><a href="#recorrido">Cómo funciona</a><a href="#seguridad">Confianza</a></div>
          <div><strong>Acceso</strong><Link to="/solicitar-acceso">Solicitar acceso</Link><Link to="/login">Iniciar sesión</Link></div>
        </div>
        <div className="landing-shell landing-footer__bottom"><span>© {new Date().getFullYear()} Inkora</span><span>Hecho para negocios que quieren avanzar con orden.</span></div>
      </footer>
    </div>
  );
}
