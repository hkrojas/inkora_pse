import { useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { Eye, EyeOff, ArrowRight, Sun, Moon, CheckCircle2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';

export default function Login() {
  const { login, user, loading } = useAuth();
  const { resolvedTheme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [remember, setRemember] = useState(false);
  const [showAccessHelp, setShowAccessHelp] = useState(false);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  if (loading) return null;
  if (user) return <Navigate to="/dashboard" replace />;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      await login(email.trim().toLowerCase(), password, { remember });
      navigate('/dashboard');
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const isDark = resolvedTheme === 'dark';

  return (
    <div className="flex min-h-screen bg-[var(--color-bg)]">
      {/* ── Panel izquierdo ─────────────────────────────────── */}
      <div
        className="hidden lg:flex lg:w-1/2 xl:w-5/12 flex-col justify-between p-10 relative overflow-hidden"
        style={{
          background: isDark
            ? 'linear-gradient(160deg, #0f172a 0%, #1e1b4b 100%)'
            : 'linear-gradient(160deg, #f0f4ff 0%, #e0e7ff 100%)',
        }}
      >
        <div className="relative z-10">
          <div className="flex items-center gap-3">
            <img src="/logo-icon.png" alt="Inkora" className="h-10 w-10 object-contain" />
            <span className="text-xl font-extrabold tracking-tight text-[var(--color-text)]">Inkora</span>
          </div>
        </div>

        <div className="relative z-10 space-y-8">
          <div className="space-y-4">
            <h1 className="text-4xl font-extrabold tracking-tight text-[var(--color-text)] leading-tight">
              Facturación de<br />
              <span className="text-[var(--color-primary)]">alto rendimiento.</span>
            </h1>
            <p className="text-base text-[var(--color-text-muted)] max-w-sm leading-relaxed">
              Plataforma segura de facturación y gestión comercial para imprentas y negocios gráficos en Perú.
            </p>
          </div>

          <div className="flex gap-4">
            <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4 shadow-[var(--shadow-soft)]">
              <p className="text-xs font-bold text-[var(--color-text-soft)] uppercase tracking-wider">Emisión promedio</p>
              <p className="mt-1 text-2xl font-extrabold text-[var(--color-text)]">3.2s</p>
            </div>
            <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4 shadow-[var(--shadow-soft)]">
              <p className="text-xs font-bold text-[var(--color-text-soft)] uppercase tracking-wider">Uptime SUNAT</p>
              <p className="mt-1 text-2xl font-extrabold text-[var(--color-text)]">99.2%</p>
            </div>
          </div>
        </div>

        <div className="relative z-10 flex items-center gap-2 text-sm text-[var(--color-text-muted)]">
          <CheckCircle2 size={16} className="text-[var(--color-success)]" />
          <span>Gateway SUNAT conectado</span>
        </div>
      </div>

      {/* ── Panel derecho ───────────────────────────────────── */}
      <div className="flex flex-1 flex-col items-center justify-center p-6 sm:p-10">
        <div className="w-full max-w-sm">
          <div className="flex justify-end mb-6">
            <button
              type="button"
              onClick={toggleTheme}
              className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text-muted)] hover:text-[var(--color-text)] transition-colors"
              aria-label="Cambiar tema"
            >
              {isDark ? <Sun size={18} /> : <Moon size={18} />}
            </button>
          </div>

          <div className="mb-8">
            <h2 className="text-2xl font-extrabold tracking-tight text-[var(--color-text)]">
              Bienvenido de nuevo
            </h2>
            <p className="mt-2 text-sm text-[var(--color-text-muted)] leading-relaxed">
              Ingresa al panel de tu imprenta para emitir comprobantes, revisar cobranza y continuar tus cotizaciones.
            </p>
          </div>

          {error && (
            <div
              className="mb-5 rounded-2xl border border-[var(--color-danger-soft)] bg-[var(--color-danger-soft)] px-4 py-3 text-sm font-semibold text-[var(--color-danger-text)]"
              role="alert"
            >
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-2">
              <label htmlFor="login-email" className="block text-sm font-extrabold text-[var(--color-text)]">
                Correo o usuario
              </label>
              <input
                id="login-email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="username"
                autoFocus
                placeholder="admin@demo.inkora.pe"
                className="w-full min-h-[44px] rounded-[14px] border border-[var(--color-border)] bg-[var(--color-surface)] px-4 text-sm text-[var(--color-text)] outline-none transition-all focus:border-[var(--color-primary)] focus:shadow-[0_0_0_4px_rgba(37,99,235,0.09)]"
              />
            </div>

            <div className="space-y-2">
              <label htmlFor="login-password" className="block text-sm font-extrabold text-[var(--color-text)]">
                Contraseña
              </label>
              <div className="relative">
                <input
                  id="login-password"
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  placeholder="••••••••"
                  className="w-full min-h-[44px] rounded-[14px] border border-[var(--color-border)] bg-[var(--color-surface)] px-4 pr-10 text-sm text-[var(--color-text)] outline-none transition-all focus:border-[var(--color-primary)] focus:shadow-[0_0_0_4px_rgba(37,99,235,0.09)]"
                />
                <button
                  type="button"
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)] hover:text-[var(--color-text)]"
                  onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2 text-sm text-[var(--color-text-muted)] cursor-pointer">
                <input
                  type="checkbox"
                  checked={remember}
                  onChange={(e) => setRemember(e.target.checked)}
                  className="h-4 w-4 rounded border-[var(--color-border)] text-[var(--color-primary)]"
                />
                <span>Mantener sesión en este equipo</span>
              </label>
              <button
                type="button"
                className="text-sm font-semibold text-[var(--color-primary)] hover:underline"
                onClick={() => setShowAccessHelp((c) => !c)}
              >
                ¿Olvidaste tu contraseña?
              </button>
            </div>

            {showAccessHelp && (
              <div
                className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface-soft)] p-4 text-sm text-[var(--color-text-muted)] leading-relaxed"
                role="status"
              >
                Si perdiste tu contraseña: 1) tu administrador la resetea, 2) recibes una
                contraseña temporal, 3) al entrar Inkora te obliga a crear una nueva.
                Si eres admin y no puedes entrar, soporte debe resetear tu acceso con tu
                RUC y correo registrado.
              </div>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="w-full inline-flex items-center justify-center gap-2 rounded-[13px] bg-[var(--color-primary)] px-5 py-3 text-sm font-extrabold text-[var(--color-primary-text)] shadow-[var(--shadow-primary)] transition-all hover:bg-[var(--color-primary-hover)] hover:-translate-y-px disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {submitting ? (
                <>
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                  Entrando…
                </>
              ) : (
                <>
                  Entrar al dashboard
                  <ArrowRight size={16} />
                </>
              )}
            </button>
          </form>

          <p className="mt-6 text-center text-xs text-[var(--color-text-soft)]">
            Acceso protegido. Recomendado para cuentas con verificación en dos pasos y registro de actividad por usuario.
          </p>
        </div>
      </div>
    </div>
  );
}
