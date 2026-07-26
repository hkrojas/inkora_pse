import { useEffect, useRef, useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import {
  ArrowLeft, ArrowRight, Asterisk, CheckCircle2, Clock3, Eye, EyeOff,
  LockKeyhole, Search, Send, XCircle,
} from 'lucide-react';
import AuthBrandPanel from '../components/auth/AuthBrandPanel';
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
    className: 'is-pending',
  },
  approved: {
    icon: CheckCircle2,
    title: 'Alta aprobada',
    description: 'Tu empresa y usuario administrador ya están activos. Ingresa con el correo y la contraseña que registraste.',
    className: 'is-approved',
  },
  rejected: {
    icon: XCircle,
    title: 'Solicitud denegada',
    description: 'La solicitud no fue aprobada. Revisa el motivo antes de enviar una nueva.',
    className: 'is-rejected',
  },
};

function StatusView({ status, onRestart }) {
  const copy = statusCopy[status.status] || statusCopy.pending;
  const Icon = copy.icon;
  return (
    <section className={`auth-request-status ${copy.className}`} aria-live="polite" tabIndex={-1}>
      <span className="auth-success-mark"><Icon size={28} /></span>
      <p className="auth-sheet-code">SOLICITUD / ESTADO</p>
      <h3>{copy.title}</h3>
      <p>{copy.description}</p>
      <dl>
        <div><dt>Empresa</dt><dd>{status.business_name}</dd></div>
        <div><dt>Correo</dt><dd>{status.email}</dd></div>
        {status.review_notes && <div><dt>Revisión</dt><dd>{status.review_notes}</dd></div>}
      </dl>
      {status.status === 'approved' && <Link to="/login" className="auth-primary-action auth-primary-action--center">Ingresar a Inkora</Link>}
      {status.status === 'rejected' && <button type="button" className="auth-primary-action auth-primary-action--center" onClick={onRestart}>Enviar nueva solicitud</button>}
      {status.status === 'pending' && <p className="auth-request-status__note">Puedes volver a esta pantalla para consultar el estado.</p>}
    </section>
  );
}

export default function AccessRequestPage() {
  const { user, loading } = useAuth();
  const formRef = useRef(null);
  const [form, setForm] = useState(initialForm);
  const [step, setStep] = useState(1);
  const [furthestStep, setFurthestStep] = useState(1);
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [checking, setChecking] = useState(true);
  const [requestStatus, setRequestStatus] = useState(null);
  const [error, setError] = useState('');
  const [lookingUpRuc, setLookingUpRuc] = useState(false);
  const [rucFeedback, setRucFeedback] = useState(null);

  useEffect(() => {
    if (requestStatus) {
      window.requestAnimationFrame(() => document.querySelector('.auth-request-status')?.focus());
    }
  }, [requestStatus]);

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
    setError('');
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

  const validateStep = (currentStep) => {
    const scope = formRef.current?.querySelector(`[data-request-step="${currentStep}"]`);
    const invalidField = [...(scope?.querySelectorAll('[required]') || [])].find((field) => !field.checkValidity());
    if (invalidField) {
      const revealInvalidField = () => {
        invalidField.reportValidity();
        invalidField.focus();
      };
      if (currentStep !== step) {
        setStep(currentStep);
        window.requestAnimationFrame(revealInvalidField);
      } else {
        revealInvalidField();
      }
      return false;
    }
    if (currentStep === 2 && form.password !== form.confirm_password) {
      setError('Las contraseñas no coinciden. Revísalas antes de continuar.');
      const focusConfirmation = () => document.querySelector('#access-confirm-password')?.focus();
      if (step !== 2) {
        setStep(2);
        window.requestAnimationFrame(focusConfirmation);
      } else {
        focusConfirmation();
      }
      return false;
    }
    return true;
  };

  const moveToStep = (nextStep) => {
    setStep(nextStep);
    window.requestAnimationFrame(() => {
      formRef.current?.querySelector(`[data-request-step="${nextStep}"] legend`)?.focus();
    });
  };

  const nextStep = () => {
    setError('');
    if (!validateStep(step)) return;
    const next = Math.min(3, step + 1);
    moveToStep(next);
    setFurthestStep((current) => Math.max(current, next));
  };

  const submit = async (event) => {
    event.preventDefault();
    setError('');
    if (!validateStep(1) || !validateStep(2)) return;
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
    setForm(initialForm);
    setStep(1);
    setFurthestStep(1);
    setError('');
  };

  return (
    <main className="auth-expedition auth-expedition--request">
      <AuthBrandPanel mode="request" />

      <section className="auth-sheet" aria-labelledby="request-title">
        <span className="auth-sheet-fold" aria-hidden="true" />
        <div className="auth-sheet-scroll">
          <header className="auth-sheet-header auth-request-header">
            <div>
              <p className="auth-sheet-code">SOLICITUD / NUEVA EMPRESA</p>
              <h2 id="request-title">Prepara tu espacio de trabajo.</h2>
              <p>Completa los datos de la empresa y del responsable. La activación requiere revisión.</p>
            </div>
            <div className="auth-request-header__actions">
              <span className="auth-status-stamp auth-status-stamp--review"><i /> SUJETO A APROBACIÓN</span>
              <Link to="/login" className="auth-text-link"><ArrowLeft size={13} /> Iniciar sesión</Link>
            </div>
          </header>

          {checking ? (
            <div className="auth-request-loading"><Spinner label="Consultando solicitud" /></div>
          ) : requestStatus ? (
            <StatusView status={requestStatus} onRestart={restart} />
          ) : (
            <>
              <ol className="auth-request-steps" aria-label="Progreso de la solicitud">
                {['Empresa', 'Responsable', 'Confirmación'].map((label, index) => {
                  const itemStep = index + 1;
                  const isCurrent = step === itemStep;
                  const isComplete = furthestStep > itemStep;
                  return (
                    <li className={isCurrent ? 'is-current' : isComplete ? 'is-complete' : ''} key={label}>
                      <button
                        type="button"
                        onClick={() => moveToStep(itemStep)}
                        disabled={itemStep > furthestStep}
                        aria-current={isCurrent ? 'step' : undefined}
                      >
                        <span>0{itemStep}</span><strong>{label}</strong>
                      </button>
                    </li>
                  );
                })}
              </ol>

              <form ref={formRef} onSubmit={submit} className="auth-request-form" noValidate>
                <fieldset className="auth-request-step" data-request-step="1" hidden={step !== 1}>
                  <legend tabIndex={-1}>Datos de la empresa</legend>
                  <p className="auth-step-help">Empezamos por el RUC para reducir la digitación y mantener la razón social correcta.</p>
                  <div className="auth-field-grid">
                    <label className="auth-field auth-field--wide">
                      <span>RUC</span>
                      <span className="auth-field-control auth-field-control--action">
                        <input id="access-business-ruc" required inputMode="numeric" minLength={11} maxLength={11} pattern="20[0-9]{9}" title="Ingresa un RUC válido de 11 dígitos que empiece por 20" value={form.business_ruc} onChange={setField('business_ruc')} placeholder="20XXXXXXXXX" aria-describedby="access-ruc-feedback" />
                        <button type="button" className="auth-inline-action" onClick={lookupRuc} disabled={lookingUpRuc || form.business_ruc.length !== 11}>
                          <Search size={15} />{lookingUpRuc ? 'Consultando…' : 'Consultar RUC'}
                        </button>
                      </span>
                      <small id="access-ruc-feedback" className={rucFeedback ? `is-${rucFeedback.tone}` : ''}>{rucFeedback?.message || 'Ingresa los 11 dígitos del RUC.'}</small>
                    </label>
                    <label className="auth-field auth-field--wide"><span>Razón social</span><span className="auth-field-control"><input required value={form.business_name} onChange={setField('business_name')} placeholder="Nombre registrado de la empresa" /></span></label>
                    <label className="auth-field"><span>Dirección fiscal <em>Opcional</em></span><span className="auth-field-control"><input value={form.business_address} onChange={setField('business_address')} placeholder="Dirección de la empresa" /></span></label>
                    <label className="auth-field"><span>Teléfono operativo <em>Opcional</em></span><span className="auth-field-control"><input inputMode="tel" value={form.business_phone} onChange={setField('business_phone')} placeholder="987 654 321" /></span></label>
                  </div>
                </fieldset>

                <fieldset className="auth-request-step" data-request-step="2" hidden={step !== 2}>
                  <legend tabIndex={-1}>Responsable del acceso</legend>
                  <p className="auth-step-help">Esta persona administrará inicialmente el espacio de trabajo de la empresa.</p>
                  <div className="auth-field-grid">
                    <label className="auth-field auth-field--wide"><span>Nombre y apellido</span><span className="auth-field-control"><input required value={form.contact_name} onChange={setField('contact_name')} placeholder="Responsable de la cuenta" /></span></label>
                    <label className="auth-field auth-field--wide"><span>Correo electrónico</span><span className="auth-field-control"><input required type="email" autoComplete="email" value={form.email} onChange={setField('email')} placeholder="contacto@empresa.pe" /></span></label>
                    <label className="auth-field" htmlFor="access-password"><span>Contraseña</span><span className="auth-field-control"><LockKeyhole size={17} /><input id="access-password" required type={showPassword ? 'text' : 'password'} minLength={10} maxLength={64} autoComplete="new-password" value={form.password} onChange={setField('password')} /><button type="button" className="auth-icon-button" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}>{showPassword ? <EyeOff size={17} /> : <Eye size={17} />}</button></span><small>Usa entre 10 y 64 caracteres.</small></label>
                    <label className="auth-field" htmlFor="access-confirm-password"><span>Confirmar contraseña</span><span className="auth-field-control"><LockKeyhole size={17} /><input id="access-confirm-password" required type="password" minLength={10} maxLength={64} autoComplete="new-password" value={form.confirm_password} onChange={setField('confirm_password')} /></span><small>Debe coincidir con la contraseña anterior.</small></label>
                  </div>
                </fieldset>

                <fieldset className="auth-request-step" data-request-step="3" hidden={step !== 3}>
                  <legend tabIndex={-1}>Revisa antes de enviar</legend>
                  <p className="auth-step-help">Estos datos se usarán para revisar la solicitud. Todavía no se creará una cuenta activa.</p>
                  <dl className="auth-review-list">
                    <div><dt>Empresa</dt><dd>{form.business_name}</dd></div>
                    <div><dt>RUC</dt><dd>{form.business_ruc}</dd></div>
                    <div><dt>Responsable</dt><dd>{form.contact_name}</dd></div>
                    <div><dt>Correo de acceso</dt><dd>{form.email}</dd></div>
                  </dl>
                  <div className="auth-approval-note"><span aria-hidden="true"><Asterisk size={18} /></span><div><strong>La solicitud queda en revisión</strong><p>Inkora verificará los datos antes de habilitar la empresa y el usuario administrador.</p></div></div>
                </fieldset>

                {error && <p role="alert" className="auth-alert auth-alert--request">{error}</p>}

                <div className="auth-request-actions">
                  <button type="button" className="auth-secondary-action" onClick={() => moveToStep(Math.max(1, step - 1))} disabled={step === 1}><ArrowLeft size={16} />Anterior</button>
                  <p><span>Paso {step} de 3</span><small>Alta sujeta a aprobación.</small></p>
                  {step < 3 ? (
                    <button type="button" className="auth-primary-action auth-primary-action--compact" onClick={nextStep}>Continuar<ArrowRight size={17} /></button>
                  ) : (
                    <button type="submit" className="auth-primary-action auth-primary-action--compact" disabled={submitting}>{submitting ? <Spinner size="sm" /> : <Send size={17} />}{submitting ? 'Enviando…' : 'Enviar solicitud'}</button>
                  )}
                </div>
              </form>
            </>
          )}

          <footer className="auth-sheet-footer"><span>INKORA · SOLICITUD DE ACCESO</span><span>0{step} / 03</span></footer>
        </div>
      </section>
    </main>
  );
}
