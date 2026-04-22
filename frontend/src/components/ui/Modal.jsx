import { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';

export default function Modal({ open, onClose, title, children, size = 'md' }) {
  useEffect(() => {
    if (!open) return undefined;

    const handler = (event) => {
      if (event.key === 'Escape') onClose();
    };

    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [open, onClose]);

  useEffect(() => {
    if (!open) return undefined;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [open]);

  if (!open) return null;

  const panelClassName = `modal-panel modal-panel--${size}`;

  return createPortal(
    <div className="modal-backdrop" onClick={onClose}>
      <div className={panelClassName} onClick={(event) => event.stopPropagation()}>
        <div className="modal-header">
          <p className="modal-title">{title}</p>
          <button onClick={onClose} aria-label="Cerrar" className="modal-close-btn">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="modal-body">{children}</div>
      </div>
    </div>,
    document.body,
  );
}
