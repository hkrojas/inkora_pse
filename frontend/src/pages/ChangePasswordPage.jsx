import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Eye, EyeOff, KeyRound, ShieldCheck } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../lib/utils/api';

function PasswordInput({ label, value, onChange, required }) {
  const [show, setShow] = useState(false);
  return (
    <div className="field">
      <label>{label}</label>
      <div className="relative">
        <input
          type={show ? 'text' : 'password'}
          className="control pr-10"
          value={value}
          onChange={onChange}
          required={required}
          minLength={10}
        />
        <button
          type="button"
          className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--color-text-soft)] hover:text-[var(--color-text-muted)]"
          onClick={() => setShow((s) => !s)}
          tabIndex={-1}
          aria-label={show ? 'Ocultar contraseña' : 'Mostrar contraseña'}
        >
          {show ? <EyeOff size={15} /> : <Eye size={15} />}
        </button>
      </div>
    </div>
  );
}

export default function ChangePasswordPage() {
  const { user, refreshUser } = useAuth();
  const isFirstLogin = Boolean(user?.must_change_password);
  const navigate = useNavigate();
  const [form, setForm] = useState({ current_password: '', new_password: '', confirm_password: '' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  const setField = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    if (form.new_password !== form.confirm_password) {
      setError('Las contraseñas nuevas no coinciden.');
      return;
    }
    if (form.new_password.length < 10) {
      setError('La contraseña debe tener al menos 10 caracteres.');
      return;
    }
    setSaving(true);
    try {
      const data = await api.post('/users/me/change-password', {
        current_password: form.current_password,
        new_password: form.new_password,
        confirm_password: form.confirm_password,
      });
      if (data.access_token) {
        const storage = localStorage.getItem('token') ? localStorage : sessionStorage;
        localStorage.removeItem('token');
        sessionStorage.removeItem('token');
        storage.setItem('token', data.access_token);
      }
      await refreshUser();
      setSuccess(true);
      setTimeout(() => navigate('/dashboard', { replace: true }), 1500);
    } catch (err) {
      setError(err.message || 'No se pudo cambiar la contraseña. Revisa tu conexión e inténtalo nuevamente.');
    } finally {
      setSaving(false);
    }
  };

  if (success) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="text-center space-y-3">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--color-success-soft)]">
            <ShieldCheck size={24} className="text-[var(--color-success)]" />
          </div>
          <p className="font-bold text-lg">Contraseña actualizada</p>
          <p className="text-sm text-[var(--color-text-muted)]">Redirigiendo...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-[60vh] items-center justify-center p-4">
      <div className="w-full max-w-md space-y-5">
        {isFirstLogin && (
          <div className="proto-alert warning">
            <ShieldCheck size={15} className="flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-bold text-sm">Debes cambiar tu contraseña antes de continuar</p>
              <p className="text-xs mt-1 opacity-80">
                Es la primera vez que accedes con esta cuenta. Elige una contraseña segura que solo tú conozcas.
              </p>
            </div>
          </div>
        )}

        <div
          className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-[var(--radius-2xl)] p-7 shadow-[var(--shadow-card)]"
        >
          <div className="flex items-center gap-3 mb-6">
            <div className="flex h-10 w-10 items-center justify-center rounded-[var(--radius-md)] bg-[var(--color-primary-soft)]">
              <KeyRound size={16} className="text-[var(--color-primary-text)]" />
            </div>
            <div>
              <h2 className="text-[16px] font-extrabold tracking-[-0.03em] text-[var(--color-text)]">
                {isFirstLogin ? 'Crear contraseña' : 'Cambiar contraseña'}
              </h2>
              <p className="text-[12px] text-[var(--color-text-muted)]">Seguridad de la cuenta</p>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <PasswordInput
              label={isFirstLogin ? 'Contraseña temporal (la que te enviaron)' : 'Contraseña actual'}
              value={form.current_password}
              onChange={setField('current_password')}
              required
            />
            <PasswordInput
              label="Nueva contraseña"
              value={form.new_password}
              onChange={setField('new_password')}
              required
            />
            <PasswordInput
              label="Confirmar nueva contraseña"
              value={form.confirm_password}
              onChange={setField('confirm_password')}
              required
            />

            <p className="text-[11px] text-[var(--color-text-soft)]">
              Mínimo 10 caracteres, al menos una letra y un número.
            </p>

            {error && (
              <div className="proto-alert danger">
                <p className="text-sm">{error}</p>
              </div>
            )}

            <div className="flex justify-end gap-2 pt-2">
              {!isFirstLogin && (
                <button type="button" className="btn-secondary" onClick={() => navigate(-1)}>
                  Cancelar
                </button>
              )}
              <button type="submit" disabled={saving} className="btn-primary">
                {saving ? 'Guardando...' : 'Cambiar contraseña'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
