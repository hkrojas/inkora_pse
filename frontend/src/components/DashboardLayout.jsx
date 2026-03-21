// Ruta: frontend/src/components/DashboardLayout.jsx
import React, { useState } from 'react';
import Sidebar from './Sidebar.jsx';
import { Menu, X } from 'lucide-react';
import ThemeToggle from './ThemeToggle.jsx';

const DashboardLayout = ({ children, title }) => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  return (
    <div className="flex h-screen bg-[#f8f9fb] dark:bg-surface-950 transition-colors duration-300 overflow-hidden">
      
      {/* Overlay Móvil para cerrar el menú haciendo clic afuera */}
      {isSidebarOpen && (
        <div 
          className="fixed inset-0 z-30 bg-slate-900/40 dark:bg-black/60 backdrop-blur-sm lg:hidden transition-opacity duration-300"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* Barra Lateral (Sidebar) */}
      <div className={`
        fixed inset-y-0 left-0 z-40 w-72 shrink-0 transform transition-transform duration-500 ease-out shadow-2xl lg:shadow-none lg:static lg:translate-x-0
        ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
        <Sidebar onCloseMobile={() => setIsSidebarOpen(false)} />
      </div>

      {/* Área Principal de Contenido */}
      <div className="flex-1 flex flex-col min-w-0 h-screen overflow-hidden">
        
        {/* Header Móvil */}
        <header className="lg:hidden shrink-0 bg-white dark:bg-surface-900 border-b border-slate-100 dark:border-surface-800 px-4 h-20 flex items-center justify-between transition-colors z-20">
          <div className="font-black text-xl text-indigo-600 dark:text-indigo-400 flex items-center gap-2">
            <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center text-white transform -rotate-3">F</div>
            FacturaPro
          </div>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <button 
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              className="p-2 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-surface-800 rounded-xl transition-colors"
            >
              {isSidebarOpen ? <X size={24} /> : <Menu size={24} />}
            </button>
          </div>
        </header>

        {/* Header Desktop (Títulos) */}
        <header className="hidden lg:flex px-8 py-8 items-center justify-between shrink-0 bg-[#f8f9fb] dark:bg-surface-950 transition-colors">
          <h1 className="text-3xl font-black text-slate-900 dark:text-white tracking-tight">{title}</h1>
        </header>

        {/* Título Móvil (se muestra debajo del Header Móvil) */}
        <div className="lg:hidden px-6 py-6 shrink-0 bg-[#f8f9fb] dark:bg-surface-950 transition-colors">
          <h1 className="text-2xl font-black text-slate-900 dark:text-white tracking-tight">{title}</h1>
        </div>

        {/* Área de Scroll (Contenido fluido a pantalla completa) */}
        <main className="flex-1 overflow-y-auto px-6 pb-12 lg:px-8 lg:pb-12 custom-scrollbar">
          <div className="w-full">
            {children}
          </div>
        </main>
        
      </div>
    </div>
  );
};

export default DashboardLayout;