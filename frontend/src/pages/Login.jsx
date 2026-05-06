import { useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import {
  ArrowRight,
  Check,
  Eye,
  EyeOff,
  Loader2,
  LockKeyhole,
  Mail,
  ShieldCheck,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import AuthBrandPanel, { AuthInlineBrand } from '../components/auth/AuthBrandPanel';

export default function Login() {
  const { login, user, loading } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [remember, setRemember] = useState(false);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  if (loading) {
    return (
      <main className="auth-loading-screen">
        <Loader2 size={22} className="login-spin" />
        <span>Verificando sesion</span>
      </main>
    );
  }
  if (user) return <Navigate to={user.is_superadmin ? '/superadmin' : '/dashboard'} replace />;

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      const loggedUser = await login(email.trim().toLowerCase(), password, { remember });
      navigate(loggedUser?.is_superadmin ? '/superadmin' : '/dashboard');
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="login-shell">
      <AuthBrandPanel />

      <section className="login-form-panel">
        <form className="login-card" onSubmit={handleSubmit}>
          <AuthInlineBrand />

          <div className="login-card-header">
            <div className="login-card-icon">
              <ShieldCheck size={20} />
            </div>
            <div>
              <h2>Bienvenido de vuelta</h2>
              <p>Ingresa con tu usuario para continuar.</p>
            </div>
          </div>

          {error && (
            <div className="login-alert" role="alert">
              {error}
            </div>
          )}

          <label className="login-field">
            <span>Correo / Usuario</span>
            <div className="login-input-wrap">
              <Mail size={17} />
              <input
                type="email"
                required
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                autoComplete="username"
                autoFocus
                placeholder="admin@demo.inkora.pe"
              />
            </div>
          </label>

          <label className="login-field">
            <span>Contrasena</span>
            <div className="login-input-wrap">
              <LockKeyhole size={17} />
              <input
                type={showPassword ? 'text' : 'password'}
                required
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="current-password"
                placeholder="Ingresa tu clave"
              />
              <button
                type="button"
                className="login-eye-btn"
                onClick={() => setShowPassword((value) => !value)}
                aria-label={showPassword ? 'Ocultar contrasena' : 'Mostrar contrasena'}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </label>

          <div className="login-row">
            <label className="login-check">
              <input
                type="checkbox"
                checked={remember}
                onChange={(event) => setRemember(event.target.checked)}
              />
              <span aria-hidden="true">
                <Check size={12} />
              </span>
              Recordar dispositivo
            </label>
            <Link to="/recuperar-password" className="login-link">
              Olvide mi clave
            </Link>
          </div>

          <button type="submit" className="login-submit" disabled={submitting}>
            {submitting ? (
              <>
                <Loader2 size={17} className="login-spin" />
                Ingresando
              </>
            ) : (
              <>
                Acceder al dashboard
                <ArrowRight size={17} />
              </>
            )}
          </button>

          <p className="login-request">
            No tienes cuenta? <Link to="/solicitar-acceso">Solicitar acceso</Link>
          </p>
        </form>
      </section>
    </main>
  );
}
