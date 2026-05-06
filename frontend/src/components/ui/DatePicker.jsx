import { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { ChevronLeft, ChevronRight, Calendar } from 'lucide-react';

const DAYS = ['Lu', 'Ma', 'Mi', 'Ju', 'Vi', 'Sa', 'Do'];
const MONTHS = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];

function parseDate(val) {
  if (!val) return null;
  const d = new Date(val + 'T00:00:00');
  return Number.isNaN(d) ? null : d;
}

function toISO(d) {
  if (!d) return '';
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function formatDisplay(d) {
  if (!d) return '';
  return `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}/${d.getFullYear()}`;
}

function getDaysInMonth(year, month) {
  return new Date(year, month + 1, 0).getDate();
}

function getFirstWeekday(year, month) {
  const day = new Date(year, month, 1).getDay();
  return day === 0 ? 6 : day - 1;
}

export default function DatePicker({
  value,
  onChange,
  placeholder = 'dd/mm/aaaa',
  disabled = false,
  required = false,
  compact = false,
}) {
  const selected = parseDate(value);
  const today = new Date();

  const [open, setOpen] = useState(false);
  const [viewYear, setViewYear] = useState((selected || today).getFullYear());
  const [viewMonth, setViewMonth] = useState((selected || today).getMonth());
  const [pos, setPos] = useState({ top: 0, left: 0, width: 0, maxHeight: 360 });

  const triggerRef = useRef(null);
  const calendarRef = useRef(null);

  const syncCalendarPosition = () => {
    const trigger = triggerRef.current;
    if (!trigger || typeof window === 'undefined') return;

    const rect = trigger.getBoundingClientRect();
    const viewportPadding = 12;
    const scrollX = window.scrollX;
    const scrollY = window.scrollY;
    const calendarWidth = Math.min(
      Math.max(rect.width, compact ? 248 : 292),
      window.innerWidth - viewportPadding * 2,
    );
    const measuredHeight = calendarRef.current?.offsetHeight || 320;
    const spaceBelow = window.innerHeight - rect.bottom - viewportPadding;
    const spaceAbove = rect.top - viewportPadding;
    const placeAbove = spaceBelow < Math.min(measuredHeight, 320) && spaceAbove > spaceBelow;
    const availableHeight = Math.max(220, placeAbove ? spaceAbove : spaceBelow);
    const renderedHeight = Math.min(measuredHeight, availableHeight);
    const minLeft = scrollX + viewportPadding;
    const maxLeft = scrollX + window.innerWidth - viewportPadding - calendarWidth;
    const left = Math.min(Math.max(rect.left + scrollX, minLeft), Math.max(minLeft, maxLeft));

    setPos({
      top: placeAbove
        ? rect.top + scrollY - renderedHeight - 6
        : rect.bottom + scrollY + 6,
      left,
      width: calendarWidth,
      maxHeight: availableHeight,
    });
  };

  const openCalendar = () => {
    if (disabled) return;
    if (selected) {
      setViewYear(selected.getFullYear());
      setViewMonth(selected.getMonth());
    }
    setOpen(true);
  };

  useEffect(() => {
    if (!open) return;
    const handler = (e) => {
      if (!triggerRef.current?.contains(e.target) && !calendarRef.current?.contains(e.target)) setOpen(false);
    };
    const keyHandler = (e) => { if (e.key === 'Escape') setOpen(false); };
    const handleViewport = () => syncCalendarPosition();
    syncCalendarPosition();
    document.addEventListener('mousedown', handler);
    document.addEventListener('keydown', keyHandler);
    window.addEventListener('resize', handleViewport);
    window.addEventListener('scroll', handleViewport, true);
    return () => {
      document.removeEventListener('mousedown', handler);
      document.removeEventListener('keydown', keyHandler);
      window.removeEventListener('resize', handleViewport);
      window.removeEventListener('scroll', handleViewport, true);
    };
  }, [open, compact, viewMonth, viewYear]);

  const prevMonth = () => {
    if (viewMonth === 0) {
      setViewMonth(11);
      setViewYear((y) => y - 1);
    } else {
      setViewMonth((m) => m - 1);
    }
  };

  const nextMonth = () => {
    if (viewMonth === 11) {
      setViewMonth(0);
      setViewYear((y) => y + 1);
    } else {
      setViewMonth((m) => m + 1);
    }
  };

  const selectDay = (day) => {
    const d = new Date(viewYear, viewMonth, day);
    onChange(toISO(d));
    setOpen(false);
  };

  const daysInMonth = getDaysInMonth(viewYear, viewMonth);
  const firstWeekday = getFirstWeekday(viewYear, viewMonth);
  const cells = Array(firstWeekday).fill(null).concat(Array.from({ length: daysInMonth }, (_, i) => i + 1));

  const isToday = (day) => day === today.getDate() && viewMonth === today.getMonth() && viewYear === today.getFullYear();
  const isSelected = (day) => selected && day === selected.getDate() && viewMonth === selected.getMonth() && viewYear === selected.getFullYear();

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        disabled={disabled}
        aria-required={required}
        onClick={open ? () => setOpen(false) : openCalendar}
        className={`ink-date-trigger ${compact ? 'ink-date-trigger--compact' : ''} ${open ? 'is-open' : ''}`}
      >
        <span className={`font-mono ${selected ? '' : 'text-[var(--text-tertiary)]'}`}>
          {selected ? formatDisplay(selected) : placeholder}
        </span>
        <Calendar
          size={compact ? 13 : 15}
          className={`shrink-0 ${open ? 'text-[var(--color-primary)]' : 'text-[var(--text-tertiary)]'}`}
        />
      </button>

      {open && createPortal(
        <div
          ref={calendarRef}
          className="ink-date-popover"
          style={{
            top: pos.top,
            left: pos.left,
            width: pos.width,
            maxHeight: pos.maxHeight,
          }}
        >
          <div className="ink-date-header">
            <button type="button" onMouseDown={(e) => { e.preventDefault(); prevMonth(); }} className="ink-date-nav">
              <ChevronLeft size={14} />
            </button>
            <span className="ink-date-title">
              {MONTHS[viewMonth]} {viewYear}
            </span>
            <button type="button" onMouseDown={(e) => { e.preventDefault(); nextMonth(); }} className="ink-date-nav">
              <ChevronRight size={14} />
            </button>
          </div>

          <div className="ink-date-grid">
            {DAYS.map((day) => (
              <div key={day} className="ink-date-weekday">
                {day}
              </div>
            ))}
          </div>

          <div className="ink-date-grid pt-0">
            {cells.map((day, index) => {
              if (!day) return <div key={`e-${index}`} />;
              const selectedDay = isSelected(day);
              const todayDay = isToday(day);
              return (
                <div
                  key={day}
                  onMouseDown={(e) => { e.preventDefault(); selectDay(day); }}
                  className={`ink-date-day ${selectedDay ? 'is-selected' : ''} ${todayDay ? 'is-today' : ''}`}
                >
                  {day}
                </div>
              );
            })}
          </div>

          <div className="ink-date-footer">
            <button type="button" onMouseDown={(e) => { e.preventDefault(); onChange(''); setOpen(false); }} className="ink-date-link">
              Borrar
            </button>
            <button
              type="button"
              onMouseDown={(e) => {
                e.preventDefault();
                onChange(toISO(today));
                setOpen(false);
                setViewYear(today.getFullYear());
                setViewMonth(today.getMonth());
              }}
              className="ink-date-link"
            >
              Hoy
            </button>
          </div>
        </div>,
        document.body,
      )}
    </>
  );
}
