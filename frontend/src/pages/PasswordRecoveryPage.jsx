import { Link, Navigate } from 'react-router-dom';
import { ArrowLeft, Clock3, Mail, ShieldCheck } from 'lucide-react';
import AuthBrandPanel, { AuthInlineBrand } from '../components/auth/AuthBrandPanel';
import { useAuth } from '../context/AuthContext';

export default function PasswordRecoveryPage() {
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
              <ShieldCheck size={20} />
            </div>
            <div>
              <h2>Recuperar acceso</h2>
              <p>La pantalla queda lista para el envio por correo que conectaremos despues.</p>
            </div>
          </div>

          <label className="login-field">
            <span>Correo del usuario</span>
            <div className="login-input-wrap">
              <Mail size={17} />
              <input
                type="email"
                autoComplete="username"
                placeholder="usuario@empresa.pe"
              />
            </div>
          </label>

          <div className="auth-static-notice">
            <Clock3 size={15} />
            <div>
              <strong>Envio pendiente de activar</strong>
              <p>
                Por ahora el superadmin debe resetear la clave desde el panel interno.
                Esta pagina no envia correos ni llama al backend.
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
