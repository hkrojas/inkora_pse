import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import { LayoutDashboard, FileText, Users, Package, Settings, LogOut, ChevronRight, Factory } from 'lucide-react';

const Sidebar = ({ onCloseMobile }) => {
  const { user, logout } = useAuth();
  const location = useLocation();
  const pathname = location.pathname;

  const menuItems = [
    { path: '/', icon: LayoutDashboard, label: 'Inicio' },
    { path: '/cotizaciones', icon: FileText, label: 'Ventas y Doc.' },
    { path: '/clientes', icon: Users, label: 'Clientes' },
    { path: '/productos', icon: Package, label: 'Productos' },
    { path: '/produccion', icon: Factory, label: 'Taller' },
    { path: '/configuracion', icon: Settings, label: 'Configuración' },
  ];

  const isActive = (path) => pathname === path || (path !== '/' && pathname.startsWith(path));

  return (
    <aside className="h-full flex flex-col bg-[#f8f9ff] lg:bg-white border-r border-[#e5eeff] transition-colors duration-300">
      
      {/* Sidebar Brand Header */}
      <div className="h-20 flex items-center px-6">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-[#dce9ff] flex items-center justify-center overflow-hidden">
             <span className="text-[#0058be] font-extrabold font-['Manrope']">P</span>
          </div>
          <h1 className="text-[#0058be] font-extrabold tracking-tighter text-lg font-['Manrope']">PrintFlow</h1>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-4 px-4 space-y-2">
        {menuItems.map((item) => {
          const active = isActive(item.path);
          return (
            <Link
              key={item.path}
              to={item.path}
              onClick={onCloseMobile}
              className={`
                flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold font-['Inter'] transition-all duration-300
                ${active 
                  ? 'bg-[#eff4ff] text-[#0058be] shadow-sm' 
                  : 'text-[#424754] hover:bg-[#eaf1ff] hover:text-[#0b1c30]'}
              `}
            >
              <item.icon size={20} className={active ? "text-[#0058be]" : "text-[#727785]"} strokeWidth={active ? 2.5 : 2} />
              <span className="tracking-tight">{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Footer / Profile */}
      <div className="p-5 border-t border-[#e5eeff] bg-[#f8f9ff] lg:bg-white">
        <button
          onClick={logout}
          className="flex items-center gap-3 px-4 py-3 w-full rounded-xl text-sm font-semibold font-['Inter'] text-[#ba1a1a] hover:bg-[#ffdad6] transition-all"
        >
          <LogOut size={20} />
          <span>Cerrar Sesión</span>
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;