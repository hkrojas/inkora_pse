import { useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { Eye, EyeOff, ShieldCheck, Zap } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function Login() {
  const { login, user, loading } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  if (loading) return null;
  if (user) return <Navigate to="/dashboard" replace />;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      await login(email, password);
      navigate('/dashboard');
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="lp-shell">
      <div className="lp-grid">

        {/* ── Panel izquierdo ── */}
        <section className="lp-brand">
          <div className="lp-brand-inner">
            {/* Logo */}
            <div className="lp-logo-row">
              <img src="/logo-icon.png" alt="Inkora" className="lp-logo-icon" />
              <span className="lp-wordmark">Inkora</span>
            </div>

            {/* Heading */}
            <h1 className="lp-heading">
              Sistema de Facturación<br />para Imprentas
            </h1>
            <p className="lp-desc">
              Cotiza, emite y controla tu operación fiscal desde una interfaz directa,
              con jerarquía fuerte y menos fricción para el operador.
            </p>

            {/* Chips */}
            <div className="lp-chips">
              <span className="lp-chip"><span className="lp-chip-dot" />Tenant aislado</span>
              <span className="lp-chip"><span className="lp-chip-dot" />Emisión fiscal estable</span>
              <span className="lp-chip"><span className="lp-chip-dot" />Flujo comercial continuo</span>
            </div>

            {/* Proof cards */}
            <div className="lp-proof-row">
              <div className="lp-proof-card">
                <div className="lp-proof-label">
                  <Zap className="lp-proof-icon" />
                  Emisión
                </div>
                <div className="lp-proof-num">3.2s</div>
                <p className="lp-proof-desc">
                  Tiempo promedio estimado para disparar la operación documental base.
                </p>
              </div>
              <div className="lp-proof-card">
                <div className="lp-proof-label">
                  <ShieldCheck className="lp-proof-icon" />
                  Confianza
                </div>
                <div className="lp-proof-num">99.2%</div>
                <p className="lp-proof-desc">
                  Aceptación fiscal histórica del flujo central de Inkora.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* ── Panel derecho — formulario ── */}
        <section className="lp-form-panel">
          <div className="lp-card">
            {/* Chip ACCESO */}
            <span className="lp-card-badge">Acceso</span>

            <h2 className="lp-form-title">Bienvenido de vuelta</h2>
            <p className="lp-form-sub">
              Ingresa con tu correo y contraseña para continuar la operación.
            </p>

            <form onSubmit={handleSubmit} className="lp-form">
              {error && (
                <div className="lp-error">
                  <span className="lp-error-dot" />
                  <span>{error}</span>
                </div>
              )}

              <div className="lp-field">
                <label className="lp-label">Correo electrónico</label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="lp-input"
                  placeholder="admin@demo.inkora.pe"
                />
              </div>

              <div className="lp-field">
                <label className="lp-label">Contraseña</label>
                <div className="lp-pw-wrap">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="lp-input lp-input-pw"
                    placeholder="••••••••"
                  />
                  <button
                    type="button"
                    className="lp-pw-eye"
                    onClick={() => setShowPassword((v) => !v)}
                    aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                  >
                    {showPassword
                      ? <EyeOff className="h-4 w-4" />
                      : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              <div className="lp-trust">
                <span className="lp-trust-dot" />
                <span>SUNAT activa · cifrado E2E · tenant aislado</span>
              </div>

              <button type="submit" disabled={submitting} className="lp-btn">
                {submitting && <span className="lp-btn-ring" />}
                {submitting ? 'Accediendo…' : 'Acceder a mis facturas →'}
              </button>
            </form>

            <p className="lp-footnote">
              Acceso centrado en continuidad operativa y menos fricción en el primer segundo.
            </p>
          </div>
        </section>

      </div>
    </div>
  );
}
