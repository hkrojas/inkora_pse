import React, { useState } from 'react';
import Sidebar from './Sidebar.jsx';
import { Menu, X, Search } from 'lucide-react';

const DashboardLayout = ({ children }) => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  return (
    <div className="flex h-screen bg-[#f8f9ff] text-[#0b1c30] font-['Inter'] overflow-hidden">
      
      {/* Overlay Móvil */}
      {isSidebarOpen && (
        <div 
          className="fixed inset-0 z-30 bg-[#0b1c30]/40 backdrop-blur-sm lg:hidden transition-opacity duration-300"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* Sidebar Desktop/Mobile */}
      <div className={`
        fixed inset-y-0 left-0 z-40 w-72 shrink-0 transform transition-transform duration-500 ease-out lg:static lg:translate-x-0
        ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
        <Sidebar onCloseMobile={() => setIsSidebarOpen(false)} />
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 h-screen overflow-hidden">
        
        {/* TopAppBar exact as Stitch provided */}
        <header className="sticky top-0 w-full z-20 bg-white/80 lg:bg-[#f8f9ff]/80 backdrop-blur-md shadow-sm lg:shadow-none">
          <div className="flex justify-between items-center px-6 py-4 w-full">
            <div className="flex items-center gap-4">
              <button 
                onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                className="lg:hidden text-[#0058be]"
              >
                {isSidebarOpen ? <X size={24} /> : <Menu size={24} />}
              </button>
              <Search className="text-[#0058be] hidden lg:block" size={24} />
            </div>
            
            <h1 className="lg:hidden text-[#0058be] font-extrabold tracking-tighter text-lg font-['Manrope']">PrintFlow</h1>
            
            <div className="w-8 h-8 rounded-full bg-[#dce9ff] flex items-center justify-center overflow-hidden font-bold text-[#0058be]">
              AD
            </div>
          </div>
        </header>

        {/* Scroll Area applying Stitch constraints dynamically */}
        <main className="flex-1 overflow-y-auto px-5 lg:px-12 pt-6 pb-32 custom-scrollbar">
          <div className="w-full max-w-5xl mx-auto">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
};

export default DashboardLayout;