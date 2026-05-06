import { Link, Navigate } from 'react-router-dom';
import { ArrowLeft, Building2, Clock3, IdCard, Mail, Phone, UserRound } from 'lucide-react';
import AuthBrandPanel, { AuthInlineBrand } from '../components/auth/AuthBrandPanel';
import { useAuth } from '../context/AuthContext';

export default function AccessRequestPage() {
  const { user, loading } = useAuth();

  if (!loading && user) {
    return <Navigate to={user.is_superadmin ? '/superadmin' : '/dashboard'} replace />;
  }

  return (
    <main className="login-shell auth-support-shell">
      <AuthBrandPanel />

      <section className="login-form-panel">
        <form className="login-card auth-support-card" onSubmit={(event) => event.preventDefault()}>
          <AuthInlineBrand />

          <Link to="/login" className="auth-back-link">
            <ArrowLeft size={15} />
            Volver al login
          </Link>

          <div className="login-card-header">
            <div className="login-card-icon">
              <Building2 size={20} />
            </div>
            <div>
              <h2>Solicitar acceso</h2>
              <p>Dejamos preparada la pantalla; el envio se conectara al sistema de correos.</p>
            </div>
          </div>

          <div className="auth-request-grid">
            <label className="login-field">
              <span>RUC</span>
              <div className="login-input-wrap">
                <IdCard size={17} />
                <input inputMode="numeric" maxLength={11} placeholder="20XXXXXXXXX" />
              </div>
            </label>

            <label className="login-field">
              <span>Empresa</span>
              <div className="login-input-wrap">
                <Building2 size={17} />
                <input placeholder="Razon social" />
              </div>
            </label>

            <label className="login-field">
              <span>Contacto</span>
              <div className="login-input-wrap">
                <UserRound size={17} />
                <input placeholder="Nombre y apellido" />
              </div>
            </label>

            <label className="login-field">
              <span>Correo</span>
              <div className="login-input-wrap">
                <Mail size={17} />
                <input type="email" placeholder="contacto@empresa.pe" />
              </div>
            </label>

            <label className="login-field auth-request-grid__full">
              <span>Telefono operativo</span>
              <div className="login-input-wrap">
                <Phone size={17} />
                <input inputMode="tel" placeholder="Opcional" />
              </div>
            </label>
          </div>

          <div className="auth-static-notice">
            <Clock3 size={15} />
            <div>
              <strong>Solicitud pendiente de activar</strong>
              <p>
                Esta pantalla no registra datos todavia. Cuando conectemos correos,
                el equipo interno recibira la solicitud desde aqui.
              </p>
            </div>
          </div>

          <button type="button" className="login-submit auth-submit-pending" disabled>
            Envio por correo pendiente
          </button>
        </form>
      </section>
    </main>
  );
}
