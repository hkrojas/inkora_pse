import { useEffect, useId, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { MoreHorizontal } from 'lucide-react';
import './actionMenu.css';

export default function ActionMenu({ label, children, disabled = false, onOpen, triggerLabel = 'Más' }) {
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState({});
  const trigger = useRef(null);
  const panel = useRef(null);
  const id = useId();

  useLayoutEffect(() => {
    if (!open) return undefined;
    const place = () => {
      const anchor = trigger.current?.getBoundingClientRect();
      if (!anchor || !panel.current) return;
      const width = Math.min(296, window.innerWidth - 24);
      const height = Math.min(panel.current.scrollHeight, window.innerHeight - 24, 480);
      const below = window.innerHeight - anchor.bottom - 12;
      const desiredTop = below >= height ? anchor.bottom + 6 : anchor.top - height - 6;
      const top = Math.max(12, Math.min(desiredTop, window.innerHeight - height - 12));
      setPosition({ width, left: Math.max(12, Math.min(anchor.right - width, window.innerWidth - width - 12)), top });
    };
    place();
    const observer = new ResizeObserver(place);
    observer.observe(panel.current);
    const scroll = (event) => { if (!panel.current?.contains(event.target)) place(); };
    window.addEventListener('resize', place);
    window.addEventListener('scroll', scroll, true);
    panel.current.querySelector('a, button:not(:disabled)')?.focus();
    return () => {
      observer.disconnect();
      window.removeEventListener('resize', place);
      window.removeEventListener('scroll', scroll, true);
    };
  }, [open]);

  useEffect(() => {
    if (!open) return undefined;
    const outside = (event) => {
      if (!panel.current?.contains(event.target) && !trigger.current?.contains(event.target)) setOpen(false);
    };
    const escape = (event) => {
      if (event.key === 'Escape') { event.stopPropagation(); setOpen(false); trigger.current?.focus(); }
    };
    document.addEventListener('pointerdown', outside);
    document.addEventListener('focusin', outside);
    document.addEventListener('keydown', escape);
    return () => {
      document.removeEventListener('pointerdown', outside);
      document.removeEventListener('focusin', outside);
      document.removeEventListener('keydown', escape);
    };
  }, [open]);

  return <>
    <button ref={trigger} type="button" className="history-action-button history-action-button--neutral"
      disabled={disabled} aria-label={label} aria-expanded={open} aria-controls={open ? id : undefined}
      onClick={() => { if (!open) onOpen?.(); setOpen(!open); }}>
      <MoreHorizontal size={15} aria-hidden="true" /><span>{triggerLabel}</span>
    </button>
    {open && createPortal(<div ref={panel} id={id} role="group" aria-label={label}
      className="ink-action-menu" style={position}
      onClick={(event) => {
        const action = event.target.closest('button, a');
        if (action && !action.disabled && !action.hasAttribute('data-keep-open')) setOpen(false);
      }}
      onKeyDown={(event) => {
        if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) return;
        const items = [...panel.current.querySelectorAll('a, button:not(:disabled)')];
        if (!items.length) return;
        event.preventDefault();
        const index = items.indexOf(document.activeElement);
        const next = event.key === 'Home' ? 0 : event.key === 'End' ? items.length - 1
          : (index + (event.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length;
        items[next].focus();
      }}>{children}</div>, document.body)}
  </>;
}
