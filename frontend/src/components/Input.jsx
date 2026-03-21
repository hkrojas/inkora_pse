// Ruta: frontend/src/components/Input.jsx
import React, { forwardRef, useState } from 'react';
import { Eye, EyeOff } from 'lucide-react';

const Input = forwardRef(({ label, error, icon: Icon, className = '', type, ...props }, ref) => {
  const [showPassword, setShowPassword] = useState(false);
  const isPassword = type === 'password';
  const inputType = isPassword ? (showPassword ? 'text' : 'password') : type;

  const togglePasswordVisibility = () => setShowPassword(!showPassword);

  return (
    <div className={`w-full group ${className}`}>
      {label && (
        <label className="block text-[11px] font-bold text-slate-400 dark:text-surface-400 uppercase tracking-[0.15em] mb-2.5 ml-1">
          {label}
        </label>
      )}
      <div className="relative">
        {Icon && (
          <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-400 dark:text-surface-500 group-focus-within:text-indigo-600 dark:group-focus-within:text-indigo-400 transition-colors duration-300">
            <Icon size={18} strokeWidth={2.5} />
          </div>
        )}
        <input
          ref={ref}
          type={inputType}
          className={`
            w-full bg-[#fcfdfe] dark:bg-surface-900 border-2 border-slate-100 dark:border-surface-700 text-slate-900 dark:text-white text-sm rounded-2xl 
            placeholder:text-slate-400 dark:placeholder:text-surface-500 outline-none transition-all duration-300
            py-3.5 ${Icon ? 'pl-12' : 'pl-5'} ${isPassword ? 'pr-12' : 'pr-5'}
            focus:border-indigo-600 dark:focus:border-indigo-500 focus:bg-white dark:focus:bg-surface-800 focus:ring-[6px] focus:ring-indigo-600/5 dark:focus:ring-indigo-500/10
            ${error ? 'border-red-500 dark:border-red-500 bg-red-50/20 dark:bg-red-900/10' : 'hover:border-slate-200 dark:hover:border-surface-600'}
          `}
          {...props}
        />
        
        {isPassword && (
          <button
            type="button"
            onClick={togglePasswordVisibility}
            className="absolute inset-y-0 right-0 pr-4 flex items-center text-slate-400 dark:text-surface-500 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors duration-300 focus:outline-none"
          >
            {showPassword ? <EyeOff size={18} strokeWidth={2.5} /> : <Eye size={18} strokeWidth={2.5} />}
          </button>
        )}
      </div>
      {error && (
        <p className="mt-2.5 ml-1 text-xs font-bold text-red-500 dark:text-red-400 flex items-center gap-1 animate-in fade-in slide-in-from-top-1">
          {error}
        </p>
      )}
    </div>
  );
});

Input.displayName = 'Input';
export default Input;