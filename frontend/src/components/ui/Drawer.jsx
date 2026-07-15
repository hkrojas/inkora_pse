import { useCallback, useEffect, useId, useRef, useState } from 'react';
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
  variant = 'editor',
  tone = 'primary',
  eyebrow,
  status,
  initialFocus,
  bodyClassName,
  footerClassName,
}) {
  const [visible, setVisible] = useState(false);
  const [animating, setAnimating] = useState(false);
  const drawerRef = useRef(null);
  const previousFocusRef = useRef(null);
  const titleId = useId();
  const descriptionId = useId();
  const dismissOnEscape = useCallback((event) => {
    if (event.key !== 'Escape' || event.defaultPrevented) return;
    event.preventDefault();
    onClose();
  }, [onClose]);

  useEffect(() => {
    if (open) {
      previousFocusRef.current = document.activeElement;
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
    document.addEventListener('keydown', dismissOnEscape);
    return () => document.removeEventListener('keydown', dismissOnEscape);
  }, [open, dismissOnEscape]);

  useEffect(() => {
    if (!open) return undefined;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [open]);

  useEffect(() => {
    if (!open || !visible) return undefined;
    const drawer = drawerRef.current;
    const selector = [
      'a[href]',
      'button:not([disabled])',
      'input:not([disabled])',
      'select:not([disabled])',
      'textarea:not([disabled])',
      '[tabindex]:not([tabindex="-1"])',
    ].join(',');
    const isFocusable = (element) => element
      && !element.matches('input[type="hidden"], [hidden], [aria-hidden="true"]')
      && element.getClientRects().length > 0;
    const focusFirst = () => {
      const preferred = initialFocus ? drawer?.querySelector(initialFocus) : null;
      const first = isFocusable(preferred)
        ? preferred
        : [...(drawer?.querySelectorAll(selector) || [])].find(isFocusable);
      (first || drawer)?.focus();
    };
    const trapFocus = (event) => {
      if (event.key !== 'Tab' || !drawer) return;
      const elements = [...drawer.querySelectorAll(selector)];
      if (!elements.length) {
        event.preventDefault();
        drawer.focus();
        return;
      }
      const first = elements[0];
      const last = elements[elements.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    focusFirst();
    document.addEventListener('keydown', trapFocus);
    return () => {
      document.removeEventListener('keydown', trapFocus);
      if (previousFocusRef.current instanceof HTMLElement) previousFocusRef.current.focus();
    };
  }, [open, visible]);

  if (!visible) return null;

  return createPortal(
    <>
      <div
        className={cn('ink-drawer-overlay', animating && 'is-visible')}
        onClick={onClose}
      />
      <aside
        ref={drawerRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={subtitle ? descriptionId : undefined}
        tabIndex={-1}
        className={cn(
          'ink-drawer',
          size === 'wide' && 'ink-drawer--wide',
          `ink-drawer--${variant}`,
          tone && `ink-drawer--tone-${tone}`,
          animating && 'is-open',
        )}
        onClick={(event) => event.stopPropagation()}
        onKeyDownCapture={dismissOnEscape}
      >
        <div className="ink-drawer-header">
          <div className="ink-drawer-title">
            {icon && <div className="ink-drawer-icon">{icon}</div>}
            <div>
              {(eyebrow || status) && (
                <div className="ink-drawer-title-meta">
                  {eyebrow ? <span className="ink-drawer-eyebrow">{eyebrow}</span> : null}
                  {status ? <span className="ink-drawer-status">{status}</span> : null}
                </div>
              )}
              <h3 id={titleId}>{title}</h3>
              {subtitle ? <p id={descriptionId}>{subtitle}</p> : null}
            </div>
          </div>
          <button type="button" className="ink-drawer-close" onClick={onClose} aria-label="Cerrar">
            <X size={18} />
          </button>
        </div>
        <div className={cn('ink-drawer-body', bodyClassName)}>{children}</div>
        {footer ? <div className={cn('ink-drawer-footer', footerClassName)}>{footer}</div> : null}
      </aside>
    </>,
    document.body,
  );
}
