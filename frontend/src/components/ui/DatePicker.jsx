import { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { ChevronLeft, ChevronRight, Calendar } from 'lucide-react';

const DAYS = ['Lu', 'Ma', 'Mi', 'Ju', 'Vi', 'Sa', 'Do'];
const MONTHS = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];

function parseDate(val) {
  if (!val) return null;
  const d = new Date(val + 'T00:00:00');
  return isNaN(d) ? null : d;
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
  return day === 0 ? 6 : day - 1; // Monday = 0
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
  const [pos, setPos] = useState({ top: 0, left: 0, width: 0 });

  const triggerRef = useRef(null);
  const calendarRef = useRef(null);

  const openCalendar = () => {
    if (disabled) return;
    const rect = triggerRef.current.getBoundingClientRect();
    setPos({
      top: rect.bottom + window.scrollY,
      left: rect.left + window.scrollX,
      width: Math.max(rect.width, compact ? 240 : 280),
    });
    if (selected) { setViewYear(selected.getFullYear()); setViewMonth(selected.getMonth()); }
    setOpen(true);
  };

  useEffect(() => {
    if (!open) return;
    const handler = (e) => {
      if (!triggerRef.current?.contains(e.target) && !calendarRef.current?.contains(e.target)) setOpen(false);
    };
    const keyHandler = (e) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('mousedown', handler);
    document.addEventListener('keydown', keyHandler);
    return () => { document.removeEventListener('mousedown', handler); document.removeEventListener('keydown', keyHandler); };
  }, [open]);

  const prevMonth = () => { if (viewMonth === 0) { setViewMonth(11); setViewYear(y => y - 1); } else setViewMonth(m => m - 1); };
  const nextMonth = () => { if (viewMonth === 11) { setViewMonth(0); setViewYear(y => y + 1); } else setViewMonth(m => m + 1); };

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
        onClick={open ? () => setOpen(false) : openCalendar}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '8px',
          width: '100%',
          minHeight: compact ? '36px' : '44px',
          padding: compact ? '8px 10px 8px 12px' : '10px 12px 10px 14px',
          background: open ? '#ffffff' : '#F8FAFC',
          border: open ? '1.5px solid #4F46E5' : '1.5px solid #E2E8F0',
          borderRadius: 0,
          boxShadow: open ? 'inset 0 0 0 1px #4F46E5' : 'none',
          color: selected ? 'var(--text-primary)' : '#94A3B8',
          fontSize: compact ? '13px' : '14px',
          fontFamily: 'var(--font-mono)',
          fontWeight: selected ? 600 : 400,
          letterSpacing: selected ? '0.05em' : '0',
          cursor: disabled ? 'not-allowed' : 'pointer',
          opacity: disabled ? 0.5 : 1,
          transition: 'border-color 150ms, box-shadow 150ms, background 150ms',
          textAlign: 'left',
        }}
        onMouseEnter={(e) => { if (!open && !disabled) e.currentTarget.style.borderColor = '#94A3B8'; }}
        onMouseLeave={(e) => { if (!open && !disabled) e.currentTarget.style.borderColor = open ? '#4F46E5' : '#E2E8F0'; }}
      >
        <span>{selected ? formatDisplay(selected) : placeholder}</span>
        <Calendar
          size={compact ? 13 : 15}
          style={{ color: open ? '#4F46E5' : '#94A3B8', flexShrink: 0, transition: 'color 150ms' }}
        />
      </button>

      {open && createPortal(
        <div
          ref={calendarRef}
          style={{
            position: 'absolute',
            top: pos.top,
            left: pos.left,
            width: pos.width,
            zIndex: 99999,
            background: '#ffffff',
            border: '1.5px solid #4F46E5',
            borderTop: 'none',
            boxShadow: '4px 4px 0px 0px rgba(99,102,241,0.35)',
            userSelect: 'none',
          }}
        >
          {/* Header */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 14px', borderBottom: '1px solid #E2E8F0', background: '#F8FAFC' }}>
            <button type="button" onMouseDown={(e) => { e.preventDefault(); prevMonth(); }} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: 28, height: 28, border: '1px solid #E2E8F0', background: '#fff', cursor: 'pointer', borderRadius: 0 }}>
              <ChevronLeft size={14} />
            </button>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: '#0F172A' }}>
              {MONTHS[viewMonth]} {viewYear}
            </span>
            <button type="button" onMouseDown={(e) => { e.preventDefault(); nextMonth(); }} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: 28, height: 28, border: '1px solid #E2E8F0', background: '#fff', cursor: 'pointer', borderRadius: 0 }}>
              <ChevronRight size={14} />
            </button>
          </div>

          {/* Days of week */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', padding: '8px 14px 4px', gap: 2 }}>
            {DAYS.map(d => (
              <div key={d} style={{ textAlign: 'center', fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#94A3B8', padding: '4px 0' }}>
                {d}
              </div>
            ))}
          </div>

          {/* Day cells */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', padding: '0 14px 12px', gap: 2 }}>
            {cells.map((day, i) => {
              if (!day) return <div key={`e-${i}`} />;
              const sel = isSelected(day);
              const tod = isToday(day);
              return (
                <div
                  key={day}
                  onMouseDown={(e) => { e.preventDefault(); selectDay(day); }}
                  style={{
                    textAlign: 'center',
                    padding: '6px 2px',
                    fontSize: '12px',
                    fontFamily: 'var(--font-mono)',
                    fontWeight: sel ? 700 : 400,
                    cursor: 'pointer',
                    background: sel ? '#4F46E5' : tod ? '#EEF2FF' : 'transparent',
                    color: sel ? '#ffffff' : tod ? '#4F46E5' : '#0F172A',
                    border: sel ? '1px solid #4F46E5' : tod ? '1px solid #C7D2FE' : '1px solid transparent',
                    transition: 'background 100ms',
                  }}
                  onMouseEnter={(e) => { if (!sel) { e.currentTarget.style.background = '#EEF2FF'; e.currentTarget.style.color = '#4F46E5'; }}}
                  onMouseLeave={(e) => { if (!sel) { e.currentTarget.style.background = tod ? '#EEF2FF' : 'transparent'; e.currentTarget.style.color = tod ? '#4F46E5' : '#0F172A'; }}}
                >
                  {day}
                </div>
              );
            })}
          </div>

          {/* Footer */}
          <div style={{ borderTop: '1px solid #E2E8F0', padding: '8px 14px', display: 'flex', justifyContent: 'space-between', background: '#F8FAFC' }}>
            <button type="button" onMouseDown={(e) => { e.preventDefault(); onChange(''); setOpen(false); }} style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#94A3B8', background: 'none', border: 'none', cursor: 'pointer' }}>
              Borrar
            </button>
            <button type="button" onMouseDown={(e) => { e.preventDefault(); selectDay(today.getDate()); setViewYear(today.getFullYear()); setViewMonth(today.getMonth()); }} style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#4F46E5', background: 'none', border: 'none', cursor: 'pointer' }}>
              Hoy
            </button>
          </div>
        </div>,
        document.body
      )}
    </>
  );
}
