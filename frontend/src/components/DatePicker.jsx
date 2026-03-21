// Ruta: frontend/src/components/DatePicker.jsx
import React, { useState, useEffect, useRef } from 'react';
import { Calendar as CalendarIcon, ChevronLeft, ChevronRight } from 'lucide-react';

const DatePicker = ({ label, value, onChange, error }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [currentMonth, setCurrentMonth] = useState(value ? new Date(value + 'T12:00:00') : new Date());
  const containerRef = useRef(null);

  const selectedDate = value ? new Date(value + 'T12:00:00') : null;

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) setIsOpen(false);
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const months = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
  const days = ['Do', 'Lu', 'Ma', 'Mi', 'Ju', 'Vi', 'Sa'];

  const getDaysInMonth = (date) => {
    const year = date.getFullYear();
    const month = date.getMonth();
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const daysArray = [];

    for (let i = 0; i < firstDay.getDay(); i++) daysArray.push(null);
    for (let i = 1; i <= lastDay.getDate(); i++) daysArray.push(new Date(year, month, i));
    return daysArray;
  };

  const handleDateClick = (date) => {
    if (!date) return;
    const formatted = date.toISOString().split('T')[0];
    onChange(formatted);
    setIsOpen(false);
  };

  return (
    <div className="relative w-full group" ref={containerRef}>
      {label && <label className="block text-[11px] font-bold text-slate-400 dark:text-surface-400 uppercase tracking-[0.15em] mb-2.5 ml-1">{label}</label>}
      
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={`relative w-full text-left bg-[#fcfdfe] dark:bg-surface-900 border-2 rounded-2xl py-3.5 pl-12 pr-5 transition-all duration-300
          ${isOpen ? 'border-indigo-600 dark:border-indigo-500 ring-[6px] ring-indigo-600/5 bg-white dark:bg-surface-800' : 'border-slate-100 dark:border-surface-700 hover:border-slate-200 dark:hover:border-surface-600'}
          ${error ? 'border-red-500 dark:border-red-500' : ''}
        `}
      >
        <span className="absolute inset-y-0 left-0 flex items-center pl-4 pointer-events-none text-slate-400 dark:text-surface-500 group-focus-within:text-indigo-600">
          <CalendarIcon className={`w-[18px] h-[18px] transition-colors ${isOpen ? 'text-indigo-600 dark:text-indigo-400' : ''}`} strokeWidth={2.5} />
        </span>
        <span className={`block text-sm ${!value ? 'text-slate-400 dark:text-surface-500' : 'text-slate-900 dark:text-white font-medium'}`}>
          {value ? new Date(value + 'T12:00:00').toLocaleDateString('es-ES', { year: 'numeric', month: 'long', day: 'numeric' }) : 'Seleccionar fecha...'}
        </span>
      </button>

      {isOpen && (
        <div className="absolute z-50 mt-2 w-72 bg-white dark:bg-surface-800 shadow-2xl shadow-indigo-900/10 dark:shadow-black/50 rounded-2xl border border-slate-100 dark:border-surface-700 p-5 animate-fade-in origin-top-left">
          <div className="flex items-center justify-between mb-5">
            <button onClick={(e) => { e.stopPropagation(); setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1, 1)); }} type="button" className="p-1.5 hover:bg-slate-100 dark:hover:bg-surface-700 rounded-xl transition-colors">
              <ChevronLeft className="w-5 h-5 text-slate-600 dark:text-slate-300" />
            </button>
            <span className="font-bold text-slate-900 dark:text-white text-sm">
              {months[currentMonth.getMonth()]} {currentMonth.getFullYear()}
            </span>
            <button onClick={(e) => { e.stopPropagation(); setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 1)); }} type="button" className="p-1.5 hover:bg-slate-100 dark:hover:bg-surface-700 rounded-xl transition-colors">
              <ChevronRight className="w-5 h-5 text-slate-600 dark:text-slate-300" />
            </button>
          </div>

          <div className="grid grid-cols-7 mb-3">
            {days.map(d => <div key={d} className="text-center text-[10px] font-bold text-slate-400 uppercase">{d}</div>)}
          </div>

          <div className="grid grid-cols-7 gap-1.5">
            {getDaysInMonth(currentMonth).map((date, i) => {
              if (!date) return <div key={`empty-${i}`} />;
              
              const isSelected = selectedDate && date.getTime() === selectedDate.getTime();
              const isToday = new Date().toDateString() === date.toDateString();

              return (
                <button
                  key={i}
                  type="button"
                  onClick={(e) => { e.stopPropagation(); handleDateClick(date); }}
                  className={`
                    h-8 w-8 rounded-full flex items-center justify-center text-xs font-medium transition-all duration-200 mx-auto
                    ${isSelected 
                      ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30' 
                      : isToday 
                        ? 'text-indigo-600 dark:text-indigo-400 font-bold bg-indigo-50 dark:bg-indigo-500/10'
                        : 'text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-surface-700'
                    }
                  `}
                >
                  {date.getDate()}
                </button>
              );
            })}
          </div>
        </div>
      )}
      {error && <p className="mt-2.5 ml-1 text-xs font-bold text-red-500 animate-fade-in">{error}</p>}
    </div>
  );
};

export default DatePicker;