import { useEffect, useMemo, useRef, useState } from 'react';
import { CalendarDays, Check, ChevronDown, ChevronLeft, ChevronRight } from 'lucide-react';

const DOCUMENT_TYPES = [
  { value: '01', label: 'Factura electrónica', code: '01' },
  { value: '03', label: 'Boleta electrónica', code: '03' },
  { value: '07', label: 'Nota de crédito', code: '07' },
  { value: '08', label: 'Nota de débito', code: '08' },
];

const MONTHS = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
const WEEKDAYS = ['L', 'M', 'X', 'J', 'V', 'S', 'D'];

function toIsoDate(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function fromIsoDate(value) {
  if (!value) return null;
  const [year, month, day] = value.split('-').map(Number);
  return new Date(year, month - 1, day);
}

function addDays(date, amount) {
  const next = new Date(date);
  next.setDate(next.getDate() + amount);
  return next;
}

function addMonths(date, amount) {
  const day = date.getDate();
  const next = new Date(date.getFullYear(), date.getMonth() + amount, 1);
  const lastDay = new Date(next.getFullYear(), next.getMonth() + 1, 0).getDate();
  next.setDate(Math.min(day, lastDay));
  return next;
}

function useOutsideDismiss(ref, open, onDismiss) {
  useEffect(() => {
    if (!open) return undefined;
    const dismiss = (event) => {
      if (!ref.current?.contains(event.target)) onDismiss();
    };
    document.addEventListener('pointerdown', dismiss);
    return () => document.removeEventListener('pointerdown', dismiss);
  }, [onDismiss, open, ref]);
}

export function DocumentTypeSelect({ value, onChange, invalid, describedBy }) {
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const rootRef = useRef(null);
  const triggerRef = useRef(null);
  const selected = DOCUMENT_TYPES.find((option) => option.value === value);

  useOutsideDismiss(rootRef, open, () => setOpen(false));

  const openMenu = (preferredIndex) => {
    const selectedIndex = DOCUMENT_TYPES.findIndex((option) => option.value === value);
    setActiveIndex(preferredIndex ?? Math.max(selectedIndex, 0));
    setOpen(true);
  };

  useEffect(() => {
    if (open) rootRef.current?.querySelector(`[data-option-index="${activeIndex}"]`)?.focus();
  }, [activeIndex, open]);

  const choose = (option) => {
    onChange(option.value);
    setOpen(false);
    window.requestAnimationFrame(() => triggerRef.current?.focus());
  };

  const onTriggerKeyDown = (event) => {
    if (['ArrowDown', 'ArrowUp', 'Enter', ' '].includes(event.key)) {
      event.preventDefault();
      openMenu(event.key === 'ArrowUp' ? DOCUMENT_TYPES.length - 1 : undefined);
    }
  };

  const onOptionKeyDown = (event, index) => {
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      const delta = event.key === 'ArrowDown' ? 1 : -1;
      setActiveIndex((index + delta + DOCUMENT_TYPES.length) % DOCUMENT_TYPES.length);
    } else if (event.key === 'Home' || event.key === 'End') {
      event.preventDefault();
      setActiveIndex(event.key === 'Home' ? 0 : DOCUMENT_TYPES.length - 1);
    } else if (event.key === 'Escape') {
      event.preventDefault();
      setOpen(false);
      triggerRef.current?.focus();
    } else if (event.key === 'Tab') {
      setOpen(false);
    }
  };

  return (
    <div className="landing-field landing-control" ref={rootRef}>
      <span id="lookup-type-label">Tipo de comprobante</span>
      <button ref={triggerRef} type="button" className={`landing-control__trigger${selected ? ' has-value' : ''}`} aria-labelledby="lookup-type-label lookup-type-value" aria-haspopup="listbox" aria-expanded={open} aria-controls="lookup-type-options" aria-invalid={invalid} aria-describedby={describedBy} onClick={() => (open ? setOpen(false) : openMenu())} onKeyDown={onTriggerKeyDown}>
        <span id="lookup-type-value">{selected?.label || 'Selecciona'}</span>
        <ChevronDown size={18} aria-hidden="true" />
      </button>
      {open && (
        <div className="landing-select-menu" id="lookup-type-options" role="listbox" aria-labelledby="lookup-type-label">
          <div className="landing-select-menu__heading"><span>DOCUMENTO</span><small>Tipo SUNAT</small></div>
          {DOCUMENT_TYPES.map((option, index) => (
            <button type="button" role="option" aria-selected={option.value === value} className={option.value === value ? 'is-selected' : ''} data-option-index={index} key={option.value} onClick={() => choose(option)} onKeyDown={(event) => onOptionKeyDown(event, index)}>
              <span><b>{option.code}</b>{option.label}</span>
              {option.value === value && <Check size={16} aria-hidden="true" />}
            </button>
          ))}
        </div>
      )}
      {invalid && <small id="lookup-type-error">Selecciona el tipo de comprobante.</small>}
    </div>
  );
}

export function IssueDatePicker({ value, onChange, invalid, describedBy }) {
  const [open, setOpen] = useState(false);
  const selectedDate = fromIsoDate(value);
  const [visibleMonth, setVisibleMonth] = useState(() => selectedDate || new Date());
  const [focusedDate, setFocusedDate] = useState(() => selectedDate || new Date());
  const rootRef = useRef(null);
  const triggerRef = useRef(null);

  useOutsideDismiss(rootRef, open, () => setOpen(false));

  const calendarDays = useMemo(() => {
    const monthStart = new Date(visibleMonth.getFullYear(), visibleMonth.getMonth(), 1);
    const mondayOffset = (monthStart.getDay() + 6) % 7;
    const gridStart = addDays(monthStart, -mondayOffset);
    return Array.from({ length: 42 }, (_, index) => addDays(gridStart, index));
  }, [visibleMonth]);

  useEffect(() => {
    if (open) rootRef.current?.querySelector(`[data-date="${toIsoDate(focusedDate)}"]`)?.focus();
  }, [focusedDate, open, visibleMonth]);

  const show = () => {
    const start = selectedDate || new Date();
    setVisibleMonth(start);
    setFocusedDate(start);
    setOpen(true);
  };

  const moveFocus = (next) => {
    setFocusedDate(next);
    if (next.getMonth() !== visibleMonth.getMonth() || next.getFullYear() !== visibleMonth.getFullYear()) setVisibleMonth(next);
  };

  const changeMonth = (amount) => {
    const next = addMonths(focusedDate, amount);
    setVisibleMonth(next);
    setFocusedDate(next);
  };

  const selectDate = (date) => {
    onChange(toIsoDate(date));
    setOpen(false);
    window.requestAnimationFrame(() => triggerRef.current?.focus());
  };

  const onDayKeyDown = (event, date) => {
    const movements = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 };
    if (movements[event.key]) {
      event.preventDefault();
      moveFocus(addDays(date, movements[event.key]));
    } else if (event.key === 'Home' || event.key === 'End') {
      event.preventDefault();
      const weekday = (date.getDay() + 6) % 7;
      moveFocus(addDays(date, event.key === 'Home' ? -weekday : 6 - weekday));
    } else if (event.key === 'PageUp' || event.key === 'PageDown') {
      event.preventDefault();
      moveFocus(addMonths(date, event.key === 'PageUp' ? -1 : 1));
    } else if (event.key === 'Tab') {
      setOpen(false);
    }
  };

  const formattedValue = selectedDate ? new Intl.DateTimeFormat('es-PE', { day: '2-digit', month: '2-digit', year: 'numeric' }).format(selectedDate) : 'dd/mm/aaaa';
  const todayIso = toIsoDate(new Date());

  return (
    <div className="landing-field landing-control" ref={rootRef}>
      <span id="lookup-date-label">Fecha de emisión</span>
      <button ref={triggerRef} type="button" className={`landing-control__trigger${selectedDate ? ' has-value' : ''}`} aria-labelledby="lookup-date-label lookup-date-value" aria-haspopup="dialog" aria-expanded={open} aria-controls="lookup-date-calendar" aria-invalid={invalid} aria-describedby={describedBy} onClick={() => (open ? setOpen(false) : show())} onKeyDown={(event) => { if (!open && ['ArrowDown', 'Enter', ' '].includes(event.key)) { event.preventDefault(); show(); } }}>
        <span id="lookup-date-value">{formattedValue}</span>
        <CalendarDays size={18} aria-hidden="true" />
      </button>
      {open && (
        <div className="landing-calendar" id="lookup-date-calendar" role="dialog" aria-modal="false" aria-label="Seleccionar fecha de emisión" onKeyDown={(event) => { if (event.key === 'Escape') { event.preventDefault(); setOpen(false); triggerRef.current?.focus(); } }}>
          <div className="landing-calendar__header">
            <div><span>FECHA DE EMISIÓN</span><strong>{MONTHS[visibleMonth.getMonth()]} de {visibleMonth.getFullYear()}</strong></div>
            <div><button type="button" aria-label="Mes anterior" onClick={() => changeMonth(-1)}><ChevronLeft size={18} /></button><button type="button" aria-label="Mes siguiente" onClick={() => changeMonth(1)}><ChevronRight size={18} /></button></div>
          </div>
          <div className="landing-calendar__weekdays" role="row">{WEEKDAYS.map((day, index) => <span role="columnheader" aria-label={['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo'][index]} key={day}>{day}</span>)}</div>
          <div className="landing-calendar__grid" role="grid" aria-label={`${MONTHS[visibleMonth.getMonth()]} de ${visibleMonth.getFullYear()}`}>
            {calendarDays.map((date) => {
              const iso = toIsoDate(date);
              const outside = date.getMonth() !== visibleMonth.getMonth();
              return <button type="button" role="gridcell" data-date={iso} tabIndex={iso === toIsoDate(focusedDate) ? 0 : -1} aria-label={new Intl.DateTimeFormat('es-PE', { dateStyle: 'full' }).format(date)} aria-selected={iso === value} className={`${outside ? 'is-outside' : ''}${iso === todayIso ? ' is-today' : ''}`} key={iso} onClick={() => selectDate(date)} onKeyDown={(event) => onDayKeyDown(event, date)}>{date.getDate()}</button>;
            })}
          </div>
          <div className="landing-calendar__footer"><button type="button" onClick={() => { onChange(''); setOpen(false); triggerRef.current?.focus(); }}>Borrar</button><button type="button" onClick={() => selectDate(new Date())}>Hoy</button></div>
        </div>
      )}
      {invalid && <small id="lookup-date-error">Selecciona la fecha de emisión.</small>}
    </div>
  );
}
