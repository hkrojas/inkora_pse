import { useState, useRef, useEffect, useId } from 'react';
import { createPortal } from 'react-dom';
import { ChevronLeft, ChevronRight, Calendar } from 'lucide-react';

const DAYS = ['Lu', 'Ma', 'Mi', 'Ju', 'Vi', 'Sa', 'Do'];
const MONTHS = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];

function parseDate(val, monthOnly = false) {
  if (!val) return null;
  const d = new Date((monthOnly ? `${val.slice(0, 7)}-01` : val) + 'T00:00:00');
  return Number.isNaN(d.getTime()) ? null : d;
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
  id,
  value,
  onChange,
  placeholder = 'dd/mm/aaaa',
  disabled = false,
  required = false,
  compact = false,
  mode = 'day',
  min,
  max,
  ariaLabel,
  ariaLabelledby,
}) {
  const monthOnly = mode === 'month';
  const selected = parseDate(value, monthOnly);
  const minDate = parseDate(min, monthOnly);
  const maxDate = parseDate(max, monthOnly);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const generatedId = useId();
  const triggerId = id || `ink-date-${generatedId}`;
  const calendarId = `${triggerId}-calendar`;

  const [open, setOpen] = useState(false);
  const [viewYear, setViewYear] = useState((selected || today).getFullYear());
  const [viewMonth, setViewMonth] = useState((selected || today).getMonth());
  const [pos, setPos] = useState({ top: 0, left: 0, width: 0, maxHeight: 360 });

  const triggerRef = useRef(null);
  const calendarRef = useRef(null);

  const isOutsideRange = (date) => Boolean((minDate && date < minDate) || (maxDate && date > maxDate));
  const closeCalendar = () => {
    setOpen(false);
    triggerRef.current?.focus();
  };

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
    let initialDate = selected || today;
    if (minDate && initialDate < minDate) initialDate = minDate;
    if (maxDate && initialDate > maxDate) initialDate = maxDate;
    setViewYear(initialDate.getFullYear());
    setViewMonth(initialDate.getMonth());
    setOpen(true);
  };

  useEffect(() => {
    if (!open) return;
    const handler = (e) => {
      if (!triggerRef.current?.contains(e.target) && !calendarRef.current?.contains(e.target)) setOpen(false);
    };
    const keyHandler = (e) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        closeCalendar();
      }
    };
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
  }, [open, compact, viewMonth, viewYear, monthOnly]);

  useEffect(() => {
    if (!open) return;
    const calendar = calendarRef.current;
    const selectedButton = calendar?.querySelector('.ink-date-day.is-selected:not(:disabled)');
    const firstButton = calendar?.querySelector('.ink-date-day:not(:disabled)');
    (selectedButton || firstButton)?.focus({ preventScroll: true });
  }, [open]);

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
    if (isOutsideRange(d)) return;
    onChange(toISO(d));
    closeCalendar();
  };

  const selectMonth = (month) => {
    const date = new Date(viewYear, month, 1);
    if (isOutsideRange(date)) return;
    onChange(toISO(date).slice(0, 7));
    closeCalendar();
  };

  const handleGridKeyDown = (event) => {
    const offsets = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: monthOnly ? -3 : -7, ArrowDown: monthOnly ? 3 : 7 };
    const offset = offsets[event.key];
    if (!offset || !event.target.matches('.ink-date-day')) return;
    event.preventDefault();
    const buttons = Array.from(event.currentTarget.querySelectorAll('.ink-date-day'));
    const currentIndex = buttons.indexOf(event.target);
    let nextIndex = currentIndex + offset;
    while (nextIndex >= 0 && nextIndex < buttons.length) {
      if (!buttons[nextIndex].disabled) {
        buttons[nextIndex].focus();
        return;
      }
      nextIndex += Math.sign(offset);
    }
  };

  const previousPeriodEnd = monthOnly
    ? new Date(viewYear - 1, 11, 1)
    : new Date(viewYear, viewMonth, 0);
  const nextPeriodStart = monthOnly
    ? new Date(viewYear + 1, 0, 1)
    : new Date(viewYear, viewMonth + 1, 1);
  const previousDisabled = Boolean(minDate && previousPeriodEnd < minDate);
  const nextDisabled = Boolean(maxDate && nextPeriodStart > maxDate);
  const todayValue = monthOnly ? new Date(today.getFullYear(), today.getMonth(), 1) : today;

  const daysInMonth = getDaysInMonth(viewYear, viewMonth);
  const firstWeekday = getFirstWeekday(viewYear, viewMonth);
  const cells = Array(firstWeekday).fill(null).concat(Array.from({ length: daysInMonth }, (_, i) => i + 1));

  const isToday = (day) => day === today.getDate() && viewMonth === today.getMonth() && viewYear === today.getFullYear();
  const isSelected = (day) => selected && day === selected.getDate() && viewMonth === selected.getMonth() && viewYear === selected.getFullYear();

  return (
    <>
      <button
        id={triggerId}
        ref={triggerRef}
        type="button"
        disabled={disabled}
        aria-required={required}
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-controls={open ? calendarId : undefined}
        aria-label={ariaLabel}
        aria-labelledby={ariaLabelledby}
        onClick={open ? () => setOpen(false) : openCalendar}
        className={`ink-date-trigger ${compact ? 'ink-date-trigger--compact' : ''} ${open ? 'is-open' : ''}`}
      >
        <span className={`${monthOnly ? '' : 'font-mono'} ${selected ? '' : 'text-[var(--text-tertiary)]'}`}>
          {selected ? (monthOnly ? `${MONTHS[selected.getMonth()]} ${selected.getFullYear()}` : formatDisplay(selected)) : placeholder}
        </span>
        <Calendar
          size={compact ? 13 : 15}
          className={`shrink-0 ${open ? 'text-[var(--color-primary)]' : 'text-[var(--text-tertiary)]'}`}
        />
      </button>

      {open && createPortal(
        <div
          ref={calendarRef}
          id={calendarId}
          className="ink-date-popover"
          role="dialog"
          aria-modal="false"
          aria-label={monthOnly ? 'Seleccionar mes' : 'Seleccionar fecha'}
          style={{
            top: pos.top,
            left: pos.left,
            width: pos.width,
            maxHeight: pos.maxHeight,
          }}
        >
          <div className="ink-date-header">
            <button type="button" aria-label={monthOnly ? 'Año anterior' : 'Mes anterior'} disabled={previousDisabled} onClick={() => monthOnly ? setViewYear((year) => year - 1) : prevMonth()} className="ink-date-nav">
              <ChevronLeft size={14} />
            </button>
            <span className="ink-date-title">
              {monthOnly ? viewYear : `${MONTHS[viewMonth]} ${viewYear}`}
            </span>
            <button type="button" aria-label={monthOnly ? 'Año siguiente' : 'Mes siguiente'} disabled={nextDisabled} onClick={() => monthOnly ? setViewYear((year) => year + 1) : nextMonth()} className="ink-date-nav">
              <ChevronRight size={14} />
            </button>
          </div>

          {monthOnly ? (
            <div className="ink-date-grid ink-date-month-grid" onKeyDown={handleGridKeyDown}>
              {MONTHS.map((month, index) => {
                const candidate = new Date(viewYear, index, 1);
                const selectedMonth = selected && selected.getMonth() === index && selected.getFullYear() === viewYear;
                const currentMonth = today.getMonth() === index && today.getFullYear() === viewYear;
                return (
                  <button
                    type="button"
                    key={month}
                    onClick={() => selectMonth(index)}
                    className={`ink-date-day ink-date-month ${selectedMonth ? 'is-selected' : ''} ${currentMonth ? 'is-today' : ''}`}
                    aria-label={`${month} ${viewYear}`}
                    aria-pressed={Boolean(selectedMonth)}
                    disabled={isOutsideRange(candidate)}
                  >
                    {month}
                  </button>
                );
              })}
            </div>
          ) : (
            <>
              <div className="ink-date-grid">
                {DAYS.map((day) => (
                  <div key={day} className="ink-date-weekday">
                    {day}
                  </div>
                ))}
              </div>

              <div className="ink-date-grid pt-0" onKeyDown={handleGridKeyDown}>
                {cells.map((day, index) => {
                  if (!day) return <div key={`e-${index}`} />;
                  const selectedDay = isSelected(day);
                  const todayDay = isToday(day);
                  const candidate = new Date(viewYear, viewMonth, day);
                  const isDisabled = isOutsideRange(candidate);
                  return (
                    <button
                      type="button"
                      key={day}
                      onClick={() => selectDay(day)}
                      className={`ink-date-day ${selectedDay ? 'is-selected' : ''} ${todayDay ? 'is-today' : ''}`}
                      aria-label={candidate.toLocaleDateString('es-PE', { day: 'numeric', month: 'long', year: 'numeric' })}
                      aria-pressed={Boolean(selectedDay)}
                      disabled={isDisabled}
                    >
                      {day}
                    </button>
                  );
                })}
              </div>
            </>
          )}

          <div className="ink-date-footer">
            {required ? <span /> : (
              <button type="button" onClick={() => { onChange(''); closeCalendar(); }} className="ink-date-link">
                Borrar
              </button>
            )}
            <button
              type="button"
              disabled={isOutsideRange(todayValue)}
              onClick={() => {
                onChange(monthOnly ? toISO(todayValue).slice(0, 7) : toISO(today));
                closeCalendar();
                setViewYear(today.getFullYear());
                setViewMonth(today.getMonth());
              }}
              className="ink-date-link"
            >
              {monthOnly ? 'Este mes' : 'Hoy'}
            </button>
          </div>
        </div>,
        document.body,
      )}
    </>
  );
}
