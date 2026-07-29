import { NavLink } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';

const STAGES = [
  { number: '01', label: 'Cotiza', detail: 'Prepara la venta', to: '/cotizaciones' },
  { number: '02', label: 'Emite', detail: 'Genera el comprobante', to: '/comprobantes/nuevo' },
  { number: '03', label: 'Controla', detail: 'Actualiza existencias', to: '/inventario' },
  { number: '04', label: 'Cobra', detail: 'Sigue el saldo', to: '/cobranza' },
];

export default function OperationalRouteNav() {
  return (
    <nav className="operational-route ink-enter-2" aria-label="Ruta operativa de una venta">
      <div className="operational-route__heading">
        <span>Flujo conectado</span>
        <p>Accede a cada etapa sin perder el contexto de la operación.</p>
      </div>
      <ol className="operational-route__steps">
        {STAGES.map((stage, index) => (
          <li key={stage.to}>
            <NavLink to={stage.to} className="operational-route__step">
              <span className="operational-route__marker" aria-hidden="true">
                {stage.number}
              </span>
              <span className="operational-route__copy">
                <strong>{stage.label}</strong>
                <small>{stage.detail}</small>
              </span>
              {index < STAGES.length - 1 && (
                <ArrowRight className="operational-route__arrow" size={15} aria-hidden="true" />
              )}
            </NavLink>
          </li>
        ))}
      </ol>
    </nav>
  );
}
