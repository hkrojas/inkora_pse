import { createContext, useCallback, useContext, useRef, useState, useEffect } from 'react';
import { AlertTriangle, CheckCircle, Info, X, XCircle } from 'lucide-react';

const ToastContext = createContext(null);

const ICON_MAP = {
  error: <XCircle className="h-4 w-4 shrink-0 text-[var(--color-error)]" />,
  warning: <AlertTriangle className="h-4 w-4 shrink-0 text-[var(--color-warning)]" />,
  info: <Info className="h-4 w-4 shrink-0 text-[var(--color-info)]" />,
  success: <CheckCircle className="h-4 w-4 shrink-0 text-[var(--color-success)]" />,
};

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const nextIdRef = useRef(0);

  const push = useCallback((message, type = 'success') => {
    const id = `${Date.now()}-${nextIdRef.current++}`;
    setToasts((prev) => [...prev, { id, message, type, exiting: false }]);
    setTimeout(() => {
      setToasts((prev) => prev.map((t) => t.id === id ? { ...t, exiting: true } : t));
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, 300);
    }, 3700);
  }, []);

  const remove = useCallback((id) => {
    setToasts((prev) => prev.map((t) => t.id === id ? { ...t, exiting: true } : t));
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 300);
  }, []);

  return (
    <ToastContext.Provider value={push}>
      {children}
      <div className="toast-container">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`toast-item toast-item--${toast.type} ${toast.exiting ? 'anim-slide-out' : ''}`}
            style={toast.exiting ? { animation: 'slide-out-right 300ms ease-in both' } : undefined}
          >
            {ICON_MAP[toast.type]}
            <span className="flex-1">{toast.message}</span>
            <button
              onClick={() => remove(toast.id)}
              className="btn-ghost p-0 min-h-[24px]"
              aria-label="Cerrar"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  return useContext(ToastContext);
}
