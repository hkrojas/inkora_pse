import { useEffect, useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import {
  ArrowLeft, Building2, CheckCircle2, Clock3, IdCard, LockKeyhole,
  Mail, MapPin, Phone, Search, Send, UserRound, XCircle,
} from 'lucide-react';
import AuthBrandPanel, { AuthInlineBrand } from '../components/auth/AuthBrandPanel';
import Spinner from '../components/ui/Spinner';
import { useAuth } from '../context/AuthContext';
import { accessRequests } from '../services/accessRequests';

const REQUEST_TOKEN_KEY = 'inkora_access_request_token';
const initialForm = {
  business_ruc: '', business_name: '', business_address: '', business_phone: '',
  contact_name: '', email: '', password: '', confirm_password: '',
};

const statusCopy = {
  pending: {
    icon: Clock3,
    title: 'Solicitud en revisión',
    description: 'El superadministrador de Inkora revisará la empresa y el contacto antes de habilitar el acceso.',
    tone: 'text-[var(--color-warning)] bg-[var(--color-warning-soft)]',
  },
  approved: {
    icon: CheckCircle2,
    title: 'Alta aprobada',
    description: 'Tu empresa y usuario administrador ya están activos. Ingresa con el correo y la contraseña que registraste.',
    tone: 'text-[var(--color-success)] bg-[var(--color-success-soft)]',
  },
  rejected: {
    icon: XCircle,
    title: 'Solicitud denegada',
    description: 'La solicitud no fue aprobada. Revisa el motivo antes de enviar una nueva.',
    tone: 'text-[var(--color-danger)] bg-[var(--color-danger-soft)]',
  },
};

function StatusView({ status, onRestart }) {
  const copy = statusCopy[status.status] || statusCopy.pending;
  const Icon = copy.icon;
  return (
    <div className="space-y-5" aria-live="polite">
      <div className={`grid h-12 w-12 place-items-center rounded-2xl ${copy.tone}`}><Icon size={22} /></div>
      <div>
        <p className="text-xs font-black uppercase tracking-[0.14em] text-[var(--color-text-muted)]">{status.business_name}</p>
        <h2 className="mt-2 text-2xl font-black tracking-[-0.04em]">{copy.title}</h2>
        <p className="mt-2 text-sm leading-6 text-[var(--color-text-muted)]">{copy.description}</p>
      </div>
      <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface-soft)] p-4 text-sm">
        <p><span className="text-[var(--color-text-muted)]">Correo:</span> <b>{status.email}</b></p>
        {status.review_notes && <p className="mt-2"><span className="text-[var(--color-text-muted)]">Revisión:</span> {status.review_notes}</p>}
      </div>
      {status.status === 'approved' && <Link to="/login" className="login-submit inline-flex w-full items-center justify-center">Ingresar a Inkora</Link>}
      {status.status === 'rejected' && <button type="button" className="login-submit w-full" onClick={onRestart}>Enviar nueva solicitud</button>}
      {status.status === 'pending' && <p className="text-center text-xs text-[var(--color-text-muted)]">Puedes volver a esta pantalla para consultar el estado.</p>}
    </div>
  );
}

export default function AccessRequestPage() {
  const { user, loading } = useAuth();
  const [form, setForm] = useState(initialForm);
  const [submitting, setSubmitting] = useState(false);
  const [checking, setChecking] = useState(true);
  const [requestStatus, setRequestStatus] = useState(null);
  const [error, setError] = useState('');
  const [lookingUpRuc, setLookingUpRuc] = useState(false);
  const [rucFeedback, setRucFeedback] = useState(null);

  useEffect(() => {
    const token = localStorage.getItem(REQUEST_TOKEN_KEY);
    if (!token) {
      setChecking(false);
      return;
    }
    accessRequests.status(token)
      .then(setRequestStatus)
      .catch(() => localStorage.removeItem(REQUEST_TOKEN_KEY))
      .finally(() => setChecking(false));
  }, []);

  if (!loading && user) return <Navigate to={user.is_superadmin ? '/superadmin' : '/dashboard'} replace />;

  const setField = (key) => (event) => {
    let value = event.target.value;
    if (key === 'business_ruc') {
      value = value.replace(/\D/g, '').slice(0, 11);
      setRucFeedback(null);
    }
    setForm((current) => ({ ...current, [key]: value }));
  };

  const lookupRuc = async () => {
    if (!/^20\d{9}$/.test(form.business_ruc)) {
      setRucFeedback({ tone: 'error', message: 'Ingresa un RUC válido de 11 dígitos que empiece por 20.' });
      return;
    }
    setLookingUpRuc(true);
    setRucFeedback(null);
    try {
      const result = await accessRequests.lookupRuc(form.business_ruc);
      setForm((current) => ({
        ...current,
        business_name: result.business_name || current.business_name,
        business_address: result.business_address || current.business_address,
      }));
      setRucFeedback({ tone: 'success', message: 'Datos fiscales encontrados y completados.' });
    } catch (lookupError) {
      setRucFeedback({ tone: 'error', message: lookupError.message || 'No pudimos consultar este RUC.' });
    } finally {
      setLookingUpRuc(false);
    }
  };

  const submit = async (event) => {
    event.preventDefault();
    setError('');
    if (form.password !== form.confirm_password) {
      setError('Las contraseñas no coinciden.');
      return;
    }
    setSubmitting(true);
    try {
      const result = await accessRequests.create(form);
      localStorage.setItem(REQUEST_TOKEN_KEY, result.request_token);
      setRequestStatus({
        status: result.status,
        business_name: form.business_name,
        email: form.email,
        review_notes: null,
      });
      setForm(initialForm);
    } catch (requestError) {
      setError(requestError.message || 'No se pudo enviar la solicitud.');
    } finally {
      setSubmitting(false);
    }
  };

  const restart = () => {
    localStorage.removeItem(REQUEST_TOKEN_KEY);
    setRequestStatus(null);
    setError('');
  };

  return (
    <main className="login-shell auth-support-shell">
      <AuthBrandPanel />
      <section className="login-form-panel">
        <div className="login-card auth-support-card">
          <AuthInlineBrand />
          <Link to="/login" className="auth-back-link"><ArrowLeft size={15} />Volver al login</Link>
          {checking ? <div className="grid min-h-64 place-items-center"><Spinner label="Consultando solicitud" /></div> : requestStatus ? (
            <StatusView status={requestStatus} onRestart={restart} />
          ) : (
            <form onSubmit={submit} className="auth-request-form">
              <div className="login-card-header">
                <div className="login-card-icon"><Building2 size={20} /></div>
                <div><h2>Solicitar alta en Inkora</h2><p>Registra la empresa y el usuario que será su administrador.</p></div>
              </div>

              <div className="auth-request-groups">
                <fieldset className="auth-request-group">
                  <legend className="auth-request-group__title"><Building2 size={16} /><span>Datos del negocio</span></legend>
                  <div className="login-field">
                    <label htmlFor="access-business-ruc">RUC</label>
                    <div className="login-input-wrap login-input-wrap--action">
                      <IdCard size={17} />
                      <input id="access-business-ruc" required inputMode="numeric" maxLength={11} value={form.business_ruc} onChange={setField('business_ruc')} placeholder="20XXXXXXXXX" aria-describedby={rucFeedback ? 'access-ruc-feedback' : undefined} />
                      <button type="button" className="auth-ruc-lookup" onClick={lookupRuc} disabled={lookingUpRuc || form.business_ruc.length !== 11} aria-label="Consultar datos del RUC"><Search size={15} /><span>{lookingUpRuc ? 'Consultando…' : 'Consultar'}</span></button>
                    </div>
                    {rucFeedback && <span id="access-ruc-feedback" className={`auth-ruc-feedback auth-ruc-feedback--${rucFeedback.tone}`} role="status" aria-live="polite">{rucFeedback.message}</span>}
                  </div>
                  <label className="login-field"><span>Empresa</span><div className="login-input-wrap"><Building2 size={17} /><input required value={form.business_name} onChange={setField('business_name')} placeholder="Razón social" /></div></label>
                  <label className="login-field"><span>Dirección fiscal <small>(opcional)</small></span><div className="login-input-wrap"><MapPin size={17} /><input value={form.business_address} onChange={setField('business_address')} placeholder="Dirección de la empresa" /></div></label>
                  <label className="login-field"><span>Teléfono operativo <small>(opcional)</small></span><div className="login-input-wrap"><Phone size={17} /><input inputMode="tel" value={form.business_phone} onChange={setField('business_phone')} placeholder="987654321" /></div></label>
                </fieldset>

                <fieldset className="auth-request-group">
                  <legend className="auth-request-group__title"><UserRound size={16} /><span>Datos del administrador</span></legend>
                  <label className="login-field"><span>Administrador</span><div className="login-input-wrap"><UserRound size={17} /><input required value={form.contact_name} onChange={setField('contact_name')} placeholder="Nombre y apellido" /></div></label>
                  <label className="login-field"><span>Correo</span><div className="login-input-wrap"><Mail size={17} /><input required type="email" autoComplete="email" value={form.email} onChange={setField('email')} placeholder="contacto@empresa.pe" /></div></label>
                  <label className="login-field"><span>Contraseña</span><div className="login-input-wrap"><LockKeyhole size={17} /><input required type="password" minLength={10} maxLength={64} autoComplete="new-password" value={form.password} onChange={setField('password')} /></div></label>
                  <label className="login-field"><span>Confirmar contraseña</span><div className="login-input-wrap"><LockKeyhole size={17} /><input required type="password" minLength={10} maxLength={64} autoComplete="new-password" value={form.confirm_password} onChange={setField('confirm_password')} /></div></label>
                </fieldset>
              </div>

              <div className="auth-static-notice"><Clock3 size={15} /><div><strong>Alta sujeta a aprobación</strong><p>No se creará una empresa ni un usuario activo hasta que el superadministrador apruebe la solicitud.</p></div></div>
              {error && <p role="alert" className="rounded-xl bg-[var(--color-danger-soft)] p-3 text-sm font-semibold text-[var(--color-danger)]">{error}</p>}
              <div className="auth-request-submit-bar"><button type="submit" className="login-submit inline-flex w-full items-center justify-center gap-2" disabled={submitting}>{submitting ? <Spinner size="sm" /> : <Send size={17} />}{submitting ? 'Enviando solicitud...' : 'Enviar solicitud'}</button></div>
            </form>
          )}
        </div>
      </section>
    </main>
  );
}
