import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowRight,
  Boxes,
  Check,
  CheckCircle2,
  ChevronDown,
  CircleDollarSign,
  FileCheck2,
  FileText,
  Menu,
  PackageCheck,
  ReceiptText,
  ShieldCheck,
  Sparkles,
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
    eyebrow: 'Ventas',
    title: 'De la conversación al comprobante.',
    copy: 'Clientes, productos y cotizaciones permanecen conectados para que cada venta avance sin trabajo duplicado.',
    icon: FileText,
    accent: 'paper',
    detail: <MiniQuote />,
  },
  {
    eyebrow: 'Facturación electrónica',
    title: 'El estado fiscal, explicado con claridad.',
    copy: 'Facturas, boletas y documentos relacionados con estados visibles y evidencia fiscal disponible para tu equipo.',
    icon: FileCheck2,
    accent: 'ink',
    detail: <FiscalPulse />,
  },
  {
    eyebrow: 'Inventario',
    title: 'Stock que cuenta la historia completa.',
    copy: 'Existencias, movimientos, almacenes y Kardex para saber qué tienes, dónde está y cómo cambió.',
    icon: Boxes,
    accent: 'sage',
    detail: <StockBars />,
  },
  {
    eyebrow: 'Cobranza',
    title: 'Vender no termina al emitir.',
    copy: 'Cuotas, pagos y saldos pendientes en una vista diseñada para decidir a quién dar seguimiento.',
    icon: CircleDollarSign,
    accent: 'clay',
    detail: <CollectionCard />,
  },
];

const faqs = [
  ['¿Inkora es solo un facturador?', 'No. Inkora conecta cotizaciones, ventas, comprobantes electrónicos, inventario y cobranza en un mismo recorrido comercial.'],
  ['¿Cómo se relaciona Inkora con SUNAT?', 'Inkora procesa la emisión mediante el proveedor fiscal configurado y muestra el estado de cada documento para que tu equipo sepa qué fue aceptado y qué necesita atención.'],
  ['¿Necesito instalar un programa?', 'No. Inkora funciona desde el navegador para que tu equipo pueda trabajar con una única fuente de información.'],
  ['¿Puedo controlar productos y servicios?', 'Sí. Puedes organizar tu catálogo y diferenciar productos inventariables de servicios que no afectan stock.'],
  ['¿Cómo empiezo?', 'Solicita acceso y revisaremos la información básica de tu empresa antes de habilitar tu espacio de trabajo.'],
];

function Brand({ light = false }) {
  return (
    <span className={`landing-brand${light ? ' landing-brand--light' : ''}`} aria-label="Inkora">
      <img src="/favicon.svg" alt="" aria-hidden="true" />
      <strong>Inkora</strong>
    </span>
  );
}

function MiniQuote() {
  return (
    <div className="landing-mini-quote" aria-hidden="true">
      <div><span>COTIZACIÓN</span><strong>COT-00072</strong></div>
      <p>Identidad comercial</p>
      <p>100 tarjetas corporativas</p>
      <footer><span>Total</span><strong>S/ 480.00</strong></footer>
    </div>
  );
}

function FiscalPulse() {
  return (
    <div className="landing-fiscal-pulse" aria-hidden="true">
      <span className="landing-fiscal-pulse__ring"><Check size={18} /></span>
      <div><small>FACTURA F001-000184</small><strong>Aceptada</strong><span>Con evidencia fiscal</span></div>
    </div>
  );
}

function StockBars() {
  return (
    <div className="landing-stock-bars" aria-hidden="true">
      <div><span><i style={{ width: '82%' }} />Papel couché</span><strong>246</strong></div>
      <div><span><i style={{ width: '54%' }} />Tinta negra</span><strong>54</strong></div>
      <div><span><i style={{ width: '28%' }} />Cajas kraft</span><strong>18</strong></div>
    </div>
  );
}

function CollectionCard() {
  return (
    <div className="landing-collection-card" aria-hidden="true">
      <div><small>PENDIENTE POR COBRAR</small><strong>S/ 2,340.00</strong></div>
      <span><i />3 documentos requieren seguimiento</span>
    </div>
  );
}

function LandingHeader() {
  const [open, setOpen] = useState(false);

  const close = () => setOpen(false);
  return (
    <header className="landing-header">
      <div className="landing-header__inner">
        <a href="#inicio" className="landing-header__brand" onClick={close}><Brand /></a>
        <nav className={`landing-nav${open ? ' is-open' : ''}`} aria-label="Navegación principal">
          <a href="#recorrido" onClick={close}>Cómo funciona</a>
          <a href="#producto" onClick={close}>Producto</a>
          <a href="#seguridad" onClick={close}>Confianza</a>
          <a href="#preguntas" onClick={close}>Preguntas</a>
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

function HeroDesk() {
  return (
    <div className="landing-desk" aria-label="Una venta organizada en Inkora">
      <div className="landing-desk__caption"><span>UNA VENTA, UNA SOLA HISTORIA</span><i /></div>
      <article className="landing-document-card landing-document-card--quote">
        <div className="landing-document-card__top"><span>COTIZACIÓN</span><small>01 / 05</small></div>
        <strong>COT-00072</strong>
        <p>María convierte una consulta en una propuesta lista para enviar.</p>
        <div className="landing-document-lines"><i /><i /><i /></div>
        <footer><span>Total</span><b>S/ 480.00</b></footer>
      </article>
      <article className="landing-document-card landing-document-card--invoice">
        <span className="landing-live-dot" />
        <small>FACTURA F001-000184</small>
        <div className="landing-accepted"><CheckCircle2 size={19} /><strong>Aceptada</strong></div>
        <p>El equipo ya sabe que el comprobante cuenta con respuesta fiscal.</p>
      </article>
      <article className="landing-document-card landing-document-card--stock">
        <PackageCheck size={20} />
        <div><small>INVENTARIO</small><strong>− 100 unidades</strong><span>Salida trazada en Kardex</span></div>
      </article>
      <article className="landing-document-card landing-document-card--paid">
        <small>COBRANZA</small>
        <strong>Pago registrado</strong>
        <span><i /> Saldo al día</span>
      </article>
      <div className="landing-desk__scribble" aria-hidden="true">todo conectado</div>
    </div>
  );
}

export default function LandingPage() {
  useEffect(() => {
    const previousTitle = document.title;
    document.title = 'Inkora | Gestión comercial para pymes peruanas';
    return () => { document.title = previousTitle; };
  }, []);

  return (
    <div className="landing-page">
      <a className="landing-skip" href="#contenido">Saltar al contenido</a>
      <LandingHeader />
      <main id="contenido">
        <section className="landing-hero" id="inicio">
          <div className="landing-shell landing-hero__grid">
            <div className="landing-hero__copy">
              <p className="landing-kicker"><Sparkles size={14} /> Gestión comercial para pymes peruanas</p>
              <h1>Vender es difícil.<br /><em>Ordenarlo</em> no debería serlo.</h1>
              <p className="landing-hero__lead">Cotiza, emite comprobantes electrónicos, sigue su estado SUNAT y controla inventario y cobros sin repartir la operación entre sistemas desconectados.</p>
              <div className="landing-hero__actions">
                <Link to="/solicitar-acceso" className="landing-button landing-button--lime">Solicitar acceso <ArrowRight size={17} /></Link>
                <a href="#recorrido" className="landing-text-link">Conoce el recorrido <ArrowRight size={16} /></a>
              </div>
              <div className="landing-hero__promise">
                <span><Check size={14} /> Sin instalaciones</span>
                <span><Check size={14} /> Información centralizada</span>
                <span><Check size={14} /> Pensado para Perú</span>
              </div>
            </div>
            <HeroDesk />
          </div>
        </section>

        <div className="landing-marquee" aria-label="Funciones principales">
          <div><span>Cotizaciones</span><i /> <span>Facturación electrónica</span><i /> <span>Seguimiento SUNAT</span><i /> <span>Inventario y Kardex</span><i /> <span>Cobranza</span><i /> <span>Guías y documentos</span></div>
        </div>

        <section className="landing-statement">
          <div className="landing-shell landing-statement__grid">
            <p className="landing-section-index">01 — EL PROBLEMA</p>
            <div>
              <h2>Tu negocio no necesita <span>más pantallas.</span> Necesita que cada dato llegue a donde corresponde.</h2>
              <p>Inkora conecta el recorrido comercial para que una cotización no quede aislada de la factura, el stock no quede separado de la venta y el cobro no dependa de la memoria.</p>
            </div>
          </div>
        </section>

        <section className="landing-workflow" id="recorrido">
          <div className="landing-shell">
            <div className="landing-section-heading">
              <div><p className="landing-section-index">02 — CÓMO FUNCIONA</p><h2>Una venta, de principio a fin.</h2></div>
              <p>Cada etapa conserva el contexto de la anterior. Menos tareas repetidas, más claridad para decidir.</p>
            </div>
            <ol className="landing-workflow__list">
              {workflow.map((item) => (
                <li key={item.number}>
                  <span>{item.number}</span>
                  <div><strong>{item.title}</strong><p>{item.copy}</p></div>
                  <ArrowRight size={18} aria-hidden="true" />
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="landing-product" id="producto">
          <div className="landing-shell">
            <div className="landing-section-heading landing-section-heading--product">
              <div><p className="landing-section-index">03 — EL PRODUCTO</p><h2>Control sin la complejidad de un ERP.</h2></div>
              <p>Herramientas concretas para los procesos que una pyme repite todos los días.</p>
            </div>
            <div className="landing-module-grid">
              {modules.map(({ eyebrow, title, copy, icon: Icon, accent, detail }) => (
                <article className={`landing-module landing-module--${accent}`} key={title}>
                  <div className="landing-module__head"><span><Icon size={18} /></span><p>{eyebrow}</p></div>
                  <h3>{title}</h3>
                  <p>{copy}</p>
                  <div className="landing-module__visual">{detail}</div>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="landing-audience">
          <div className="landing-shell landing-audience__grid">
            <div className="landing-audience__copy">
              <p className="landing-section-index">04 — HECHO PARA OPERAR</p>
              <h2>Para empresas que venden productos, servicios o ambos.</h2>
              <p>No necesitas adaptar tu negocio a un sistema contable enorme. Inkora organiza el flujo comercial que comparten comercios, distribuidoras y empresas de servicios.</p>
              <Link to="/solicitar-acceso" className="landing-text-link">Cuéntanos cómo trabaja tu empresa <ArrowRight size={16} /></Link>
            </div>
            <div className="landing-audience__ledger" aria-hidden="true">
              <div className="landing-ledger-row landing-ledger-row--head"><span>EJEMPLO DE VISTA DIARIA</span><small>TODO CONECTADO</small></div>
              <div className="landing-ledger-row"><span>12 cotizaciones activas</span><b>Comercial</b></div>
              <div className="landing-ledger-row"><span>8 comprobantes aceptados</span><b>Fiscal</b></div>
              <div className="landing-ledger-row"><span>3 productos bajo mínimo</span><b>Inventario</b></div>
              <div className="landing-ledger-row"><span>4 cobros por revisar</span><b>Cobranza</b></div>
            </div>
          </div>
        </section>

        <section className="landing-consultation" aria-labelledby="consultation-title">
          <div className="landing-shell landing-consultation__card">
            <div>
              <p className="landing-section-index">CONSULTA DE COMPROBANTES</p>
              <h2 id="consultation-title">Tus clientes también merecen claridad.</h2>
              <p>Estamos preparando un acceso seguro para consultar y recuperar los comprobantes emitidos desde Inkora.</p>
            </div>
            <div className="landing-consultation__status">
              <span><ReceiptText size={19} /></span>
              <div><small>PRÓXIMAMENTE</small><strong>Consulta segura de documentos</strong><p>Esta función aún no recibe ni consulta datos.</p></div>
            </div>
          </div>
        </section>

        <section className="landing-trust" id="seguridad">
          <div className="landing-shell landing-trust__grid">
            <div>
              <p className="landing-section-index">05 — CONFIANZA OPERATIVA</p>
              <h2>La tranquilidad también forma parte del producto.</h2>
              <p>Inkora hace visible qué ocurrió, quién puede operar y en qué estado se encuentra cada documento.</p>
              <Link to="/solicitar-acceso" className="landing-button landing-button--light">Hablar sobre Inkora <ArrowRight size={16} /></Link>
            </div>
            <div className="landing-trust__list">
              <article><ShieldCheck size={21} /><div><strong>Información separada por empresa</strong><p>Cada organización trabaja dentro de su propio espacio y con accesos controlados.</p></div></article>
              <article><FileCheck2 size={21} /><div><strong>Trazabilidad documental</strong><p>Estados, relaciones y evidencias ayudan a entender el recorrido de cada operación.</p></div></article>
              <article><PackageCheck size={21} /><div><strong>Operación basada en estados reales</strong><p>Las alertas distinguen lo pendiente, lo procesado y lo que requiere atención.</p></div></article>
            </div>
          </div>
        </section>

        <section className="landing-faq" id="preguntas">
          <div className="landing-shell landing-faq__grid">
            <div><p className="landing-section-index">06 — PREGUNTAS</p><h2>Antes de empezar.</h2></div>
            <div className="landing-faq__list">
              {faqs.map(([question, answer]) => (
                <details key={question}>
                  <summary>{question}<ChevronDown size={18} /></summary>
                  <p>{answer}</p>
                </details>
              ))}
            </div>
          </div>
        </section>

        <section className="landing-final-cta">
          <div className="landing-shell landing-final-cta__inner">
            <p>MENOS PAPELEO. MÁS NEGOCIO.</p>
            <h2>Ordena hoy la próxima etapa de tu empresa.</h2>
            <div><Link to="/solicitar-acceso" className="landing-button landing-button--lime">Solicitar acceso <ArrowRight size={17} /></Link><Link to="/login" className="landing-button landing-button--outline">Ya uso Inkora</Link></div>
          </div>
        </section>
      </main>

      <footer className="landing-footer">
        <div className="landing-shell landing-footer__top">
          <div><Brand light /><p>Gestión comercial para pymes peruanas.</p></div>
          <div><strong>Producto</strong><a href="#recorrido">Cómo funciona</a><a href="#producto">Módulos</a><a href="#seguridad">Confianza</a></div>
          <div><strong>Acceso</strong><Link to="/solicitar-acceso">Solicitar acceso</Link><Link to="/login">Iniciar sesión</Link></div>
        </div>
        <div className="landing-shell landing-footer__bottom"><span>© {new Date().getFullYear()} Inkora</span><span>Hecho para negocios que quieren avanzar con orden.</span></div>
      </footer>
    </div>
  );
}
