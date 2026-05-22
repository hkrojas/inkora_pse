import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';
import { cn } from '../../lib/utils/cn';

export default function Drawer({
  open,
  onClose,
  title,
  subtitle,
  children,
  footer,
  icon,
  size = 'default',
}) {
  const [visible, setVisible] = useState(false);
  const [animating, setAnimating] = useState(false);

  useEffect(() => {
    if (open) {
      setVisible(true);
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          setAnimating(true);
        });
      });
    } else if (visible) {
      setAnimating(false);
      const timer = setTimeout(() => setVisible(false), 300);
      return () => clearTimeout(timer);
    }
  }, [open]);

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

  if (!visible) return null;

  return createPortal(
    <>
      <div
        className={cn('ink-drawer-overlay', animating && 'is-visible')}
        onClick={onClose}
      />
      <aside
        className={cn('ink-drawer', size === 'wide' && 'ink-drawer--wide', animating && 'is-open')}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="ink-drawer-header">
          <div className="ink-drawer-title">
            {icon && <div className="ink-drawer-icon">{icon}</div>}
            <div>
              <h3>{title}</h3>
              {subtitle ? <p>{subtitle}</p> : null}
            </div>
          </div>
          <button type="button" className="ink-drawer-close" onClick={onClose} aria-label="Cerrar">
            <X size={18} />
          </button>
        </div>
        <div className="ink-drawer-body">{children}</div>
        {footer ? <div className="ink-drawer-footer">{footer}</div> : null}
      </aside>
    </>,
    document.body,
  );
}
