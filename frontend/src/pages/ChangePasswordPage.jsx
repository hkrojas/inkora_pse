import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { KeyRound, Eye, EyeOff, ShieldCheck } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../lib/utils/api';

function PasswordInput({ label, value, onChange, required }) {
  const [show, setShow] = useState(false);
  return (
    <div>
      <label className="label">{label}</label>
      <div className="relative">
        <input
          type={show ? 'text' : 'password'}
          className="input pr-10"
          value={value}
          onChange={onChange}
          required={required}
          minLength={10}
        />
        <button
          type="button"
          className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--text-tertiary)] hover:text-[var(--text-secondary)]"
          onClick={() => setShow((s) => !s)}
          tabIndex={-1}
        >
          {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
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
      // Mantiene la preferencia de sesion al reemplazar el token sin must_change_password.
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
          <ShieldCheck className="h-12 w-12 text-green-600 mx-auto" />
          <p className="font-semibold text-lg">Contraseña actualizada</p>
          <p className="text-sm text-[var(--text-secondary)]">Redirigiendo...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-[60vh] items-center justify-center p-4">
      <div className="w-full max-w-md space-y-6">
        {isFirstLogin && (
          <div className="ink-inline-alert ink-inline-alert-warning">
            <div>
              <p className="font-bold text-sm">Debes cambiar tu contraseña antes de continuar</p>
              <p className="text-xs mt-1 opacity-80">
                Es la primera vez que accedes con esta cuenta. Elige una contraseña segura que solo tú conozcas.
              </p>
            </div>
          </div>
        )}

        <div className="card-raw p-6 space-y-5">
          <div className="flex items-center gap-3">
            <KeyRound className="h-5 w-5 text-[var(--text-secondary)]" />
            <h2 className="font-semibold text-lg">
              {isFirstLogin ? 'Crear contraseña' : 'Cambiar contraseña'}
            </h2>
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

            <p className="text-xs text-[var(--text-tertiary)]">
              Mínimo 10 caracteres, al menos una letra y un número.
            </p>

            {error && (
              <div className="ink-inline-alert ink-inline-alert-error">
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
