import { useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { ArrowRight, Check, Eye, EyeOff, Loader2, LockKeyhole, Mail } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import AuthBrandPanel from '../components/auth/AuthBrandPanel';

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
        <span>Verificando sesión</span>
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
    <main className="auth-expedition">
      <AuthBrandPanel mode="login" />

      <section className="auth-sheet" aria-labelledby="login-title">
        <span className="auth-sheet-fold" aria-hidden="true" />
        <div className="auth-sheet-scroll">
          <header className="auth-sheet-header">
            <div>
              <p className="auth-sheet-code">ACCESO / USUARIO</p>
              <h2 id="login-title">Bienvenido de vuelta.</h2>
              <p>Ingresa con el correo asociado a tu espacio de trabajo.</p>
            </div>
            <span className="auth-status-stamp"><i /> SESIÓN SEGURA</span>
          </header>

          <form className="auth-login-form" onSubmit={handleSubmit}>
            {error && <div className="auth-alert" role="alert">{error}</div>}

            <label className="auth-field">
              <span>Correo electrónico</span>
              <span className="auth-field-control">
                <Mail size={18} aria-hidden="true" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  autoComplete="username"
                  autoFocus
                  placeholder="usuario@empresa.pe"
                />
              </span>
            </label>

            <label className="auth-field">
              <span>Contraseña</span>
              <span className="auth-field-control">
                <LockKeyhole size={18} aria-hidden="true" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  autoComplete="current-password"
                  placeholder="Ingresa tu contraseña"
                />
                <button
                  type="button"
                  className="auth-icon-button"
                  onClick={() => setShowPassword((value) => !value)}
                  aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </span>
            </label>

            <div className="auth-form-row">
              <label className="auth-check">
                <input type="checkbox" checked={remember} onChange={(event) => setRemember(event.target.checked)} />
                <span aria-hidden="true"><Check size={12} /></span>
                Recordar este dispositivo
              </label>
              <Link to="/recuperar-password" className="auth-text-link">Olvidé mi contraseña</Link>
            </div>

            <button type="submit" className="auth-primary-action" disabled={submitting}>
              <span>{submitting ? 'Ingresando…' : 'Iniciar sesión'}</span>
              {submitting ? <Loader2 size={18} className="login-spin" /> : <ArrowRight size={18} />}
            </button>

            <p className="auth-switch-copy">
              ¿Tu empresa todavía no tiene acceso? <Link to="/solicitar-acceso">Solicitar acceso</Link>
            </p>
          </form>

          <footer className="auth-sheet-footer"><span>INKORA · ACCESO</span><span>01 / 01</span></footer>
        </div>
      </section>
    </main>
  );
}
