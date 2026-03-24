// Ruta: frontend/src/components/Sidebar.jsx
import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import { LayoutDashboard, FileText, Users, Package, Settings, LogOut, ChevronRight, Factory } from 'lucide-react';
import ThemeToggle from './ThemeToggle.jsx';

const Sidebar = ({ onCloseMobile }) => {
  const { pathname } = useLocation();
  const { logout, user } = useAuth();

  const menuItems = [
    { path: '/', icon: LayoutDashboard, label: 'Resumen' },
    { path: '/cotizaciones', icon: FileText, label: 'Ventas y Doc.' },
    { path: '/clientes', icon: Users, label: 'Clientes' },
    { path: '/productos', icon: Package, label: 'Productos' },
    { path: '/produccion', icon: Factory, label: 'Taller/Prod.' },
    { path: '/configuracion', icon: Settings, label: 'Configuración' },
  ];

  const isActive = (path) => pathname === path || (path !== '/' && pathname.startsWith(path));

  return (
    <aside className="h-full flex flex-col bg-white dark:bg-surface-900 border-r border-[#eff4ff] dark:border-surface-800 transition-colors duration-300">
      <div className="h-20 flex items-center px-6 border-b border-[#eff4ff] dark:border-surface-800">
        <div className="flex items-center gap-3 font-bold font-['Manrope'] text-xl text-[#0b1c30] dark:text-white tracking-tight">
          <div className="w-9 h-9 bg-gradient-to-br from-[#0058be] to-[#2170e4] rounded-xl flex items-center justify-center text-white shadow-lg shadow-[#0058be]/30 transform -rotate-3 text-lg">
            P
          </div>
          <span>PrintFlow</span>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto py-8 px-4 space-y-2">
        <div className="px-3 mb-4 text-[10px] font-bold text-slate-400 dark:text-surface-500 uppercase tracking-[0.2em]">
          Menu Principal
        </div>
        
        {menuItems.map((item) => {
          const active = isActive(item.path);
          return (
            <Link
              key={item.path}
              to={item.path}
              onClick={onCloseMobile}
              className={`
                flex items-center justify-between px-4 py-3 rounded-xl text-sm font-semibold font-['Inter'] transition-all duration-300 group
                ${active 
                  ? 'bg-[#eaf1ff] dark:bg-[#0058be]/10 text-[#0058be] dark:text-[#adc6ff] shadow-sm' 
                  : 'text-[#424754] dark:text-slate-400 hover:bg-[#f8f9ff] dark:hover:bg-surface-800 hover:text-[#0b1c30] dark:hover:text-white'}
              `}
            >
              <div className="flex items-center gap-3">
                <item.icon size={18} strokeWidth={active ? 2.5 : 2} className={active ? 'text-[#0058be] dark:text-[#adc6ff]' : 'text-[#8591a5] group-hover:text-[#0058be]'} />
                <span>{item.label}</span>
              </div>
              {active && <ChevronRight size={16} className="text-[#0058be] dark:text-[#adc6ff]" />}
            </Link>
          );
        })}
      </nav>

      <div className="p-5 border-t border-[#eff4ff] dark:border-surface-800 bg-white dark:bg-surface-900">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-[#0058be] to-[#2170e4] flex items-center justify-center text-white font-bold shadow-sm">
              {user?.nombre_completo?.charAt(0) || 'U'}
            </div>
            <div className="flex-1 min-w-0 font-['Inter']">
              <p className="text-sm font-bold text-[#0b1c30] dark:text-white truncate">
                {user?.nombre_completo || 'Usuario'}
              </p>
              <p className="text-[10px] text-[#424754] dark:text-surface-400 truncate uppercase tracking-wider font-semibold">
                {user?.rol || 'Administrador'}
              </p>
            </div>
          </div>
          <ThemeToggle />
        </div>
        
        <button
          onClick={logout}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-bold text-red-600 dark:text-red-400 bg-white dark:bg-surface-800 border-2 border-red-50 dark:border-red-900/30 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-xl transition-all"
        >
          <LogOut size={16} strokeWidth={2.5} />
          <span>Cerrar Sesión</span>
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;