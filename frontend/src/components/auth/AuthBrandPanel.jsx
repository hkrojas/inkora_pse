import { Asterisk, Check, Moon, Sun } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useTheme } from '../../context/ThemeContext';

const routeItems = [
  { type: 'COTIZACIÓN', value: 'COT-00072', detail: 'Contexto listo', complete: true },
  { type: 'COMPROBANTE', value: 'F001-00184', detail: 'Aceptado por SUNAT', complete: true },
  { type: 'ESPACIO DE TRABAJO', value: 'Acceso protegido', detail: 'Empresa y permisos conectados' },
];

const panelCopy = {
  login: {
    title: 'Tu operación continúa desde aquí.',
    description: 'Vuelve al punto exacto donde quedaron tus ventas, comprobantes, inventario y cobranza.',
  },
  request: {
    title: 'Una empresa. Un expediente claro.',
    description: 'Registra los datos necesarios para revisar el alta sin confundir solicitud, aprobación y acceso activo.',
  },
};

export default function AuthBrandPanel({ mode = 'login' }) {
  const { resolvedTheme, toggleTheme } = useTheme();
  const copy = panelCopy[mode] || panelCopy.login;
  const isDark = resolvedTheme === 'dark';

  return (
    <aside className="auth-route-panel login-brand-panel" aria-label="Contexto de acceso">
      <Link className="auth-route-brand" to="/" aria-label="Inkora, ir al inicio">
        <span className="auth-route-brand__mark" aria-hidden="true"><Asterisk size={22} /></span>
        <strong>Inkora</strong>
      </Link>

      <button
        className="auth-theme-toggle"
        type="button"
        onClick={toggleTheme}
        aria-label={isDark ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'}
      >
        {isDark ? <Sun size={17} /> : <Moon size={17} />}
        <span>{isDark ? 'Claro' : 'Oscuro'}</span>
      </button>

      <div className="auth-route-intro">
        <p className="auth-route-label">GESTIÓN COMERCIAL · PERÚ</p>
        <h1>{copy.title}</h1>
        <p>{copy.description}</p>
      </div>

      <div className="auth-operation-route" aria-label="Ruta operativa de Inkora">
        <span className="auth-route-thread" aria-hidden="true" />
        {routeItems.map((item) => (
          <article className="auth-route-event" key={item.type}>
            <span className="auth-route-node" aria-hidden="true">
              {item.complete ? <Check size={16} /> : <Asterisk size={16} />}
            </span>
            <div>
              <small>{item.type}</small>
              <strong>{item.value}</strong>
              <p>{item.detail}</p>
            </div>
          </article>
        ))}
      </div>

      <div className="auth-route-assurance">
        <span>CONTROL DE ACCESO</span>
        <p>La empresa se determina desde la sesión autenticada. Los permisos se aplican por usuario.</p>
      </div>
    </aside>
  );
}

export function AuthInlineBrand() {
  return (
    <Link className="auth-inline-brand login-card-brand" to="/" aria-label="Inkora, ir al inicio">
      <span aria-hidden="true"><Asterisk size={18} /></span>
      <strong>Inkora</strong>
    </Link>
  );
}
