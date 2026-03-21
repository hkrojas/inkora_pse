// Ruta: frontend/src/components/CustomSelect.jsx
import React, { useState, useRef, useEffect } from 'react';
import { ChevronDown, Check } from 'lucide-react';

const CustomSelect = ({ label, options, value, onChange, placeholder = "Seleccionar..." }) => {
  const [isOpen, setIsOpen] = useState(false);
  const wrapperRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const selectedOption = options.find(o => String(o.value) === String(value));

  return (
    <div className="relative w-full group" ref={wrapperRef}>
      {label && (
        <label className="block text-[11px] font-bold text-slate-400 dark:text-surface-400 uppercase tracking-[0.15em] mb-2.5 ml-1">
          {label}
        </label>
      )}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={`w-full flex items-center justify-between bg-[#fcfdfe] dark:bg-surface-900 border-2 text-sm rounded-2xl py-3.5 px-5 outline-none transition-all duration-300
          ${isOpen 
            ? 'border-indigo-600 dark:border-indigo-500 ring-[6px] ring-indigo-600/5 bg-white dark:bg-surface-800' 
            : 'border-slate-100 dark:border-surface-700 hover:border-slate-200 dark:hover:border-surface-600'
          }
        `}
      >
        <span className={selectedOption ? 'text-slate-900 dark:text-white font-medium' : 'text-slate-400 dark:text-surface-500'}>
          {selectedOption ? selectedOption.label : placeholder}
        </span>
        <ChevronDown className={`w-5 h-5 text-slate-400 transition-transform duration-300 ${isOpen ? 'rotate-180 text-indigo-600 dark:text-indigo-400' : ''}`} />
      </button>

      {isOpen && (
        <div className="absolute z-50 w-full mt-2 bg-white dark:bg-surface-800 border border-slate-100 dark:border-surface-700 rounded-xl shadow-2xl shadow-indigo-900/10 dark:shadow-black/50 max-h-60 overflow-y-auto animate-fade-in origin-top">
          <ul className="py-2">
            {options.map((opt) => (
              <li
                key={opt.value}
                onClick={() => { onChange(opt.value); setIsOpen(false); }}
                className={`px-5 py-3 mx-2 rounded-lg cursor-pointer flex items-center justify-between transition-colors text-sm
                  ${String(opt.value) === String(value) 
                    ? 'bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 font-bold' 
                    : 'text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-surface-700'
                  }
                `}
              >
                {opt.label}
                {String(opt.value) === String(value) && <Check className="w-4 h-4" />}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default CustomSelect;