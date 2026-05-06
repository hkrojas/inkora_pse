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
        <p className="login-kicker">Facturacion electronica</p>
        <h1>
          Operacion fiscal simple para imprentas que necesitan avanzar.
        </h1>
        <p>
          Cotiza, emite comprobantes y revisa cobranza diaria desde un panel
          compacto conectado a tu operacion.
        </p>
      </div>

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
