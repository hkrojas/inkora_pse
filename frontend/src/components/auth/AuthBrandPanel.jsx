import { Asterisk, CheckCircle2 } from 'lucide-react';

const assuranceItems = [
  'Datos separados por empresa',
  'Permisos por rol',
  'Credenciales fiscales protegidas',
];

export default function AuthBrandPanel() {
  return (
    <section className="login-brand-panel" aria-label="Inkora">
      <div className="login-brand-mark">
        <Asterisk size={22} />
        <span>Inkora</span>
      </div>

      <div className="login-brand-copy">
        <p className="login-kicker">Gestion comercial para pymes</p>
        <h1>Toda tu operacion comercial, clara y conectada.</h1>
        <p>
          Cotiza, emite comprobantes, controla inventario y organiza tus cobros
          desde un solo lugar.
        </p>
      </div>

      <div className="login-brand-stage">
        <div className="login-status-card">
          <div>
            <span className="login-status-dot" />
            <span className="login-status-label">Acceso seguro</span>
          </div>
          <strong>Acceso fiscal protegido</strong>
          <p>Sesion por usuario, datos por tenant y trazabilidad lista para operar.</p>
          <ul className="login-assurance-list" aria-label="Controles de acceso">
            {assuranceItems.map((item) => (
              <li key={item}>
                <CheckCircle2 size={13} />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}

export function AuthInlineBrand() {
  return (
    <div className="login-card-brand" aria-label="Inkora">
      <Asterisk size={18} />
      <span>Inkora</span>
    </div>
  );
}
