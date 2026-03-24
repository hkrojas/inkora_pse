import React, { useState, useEffect } from 'react';
import FacturacionModal from './FacturacionModal.jsx';

const TallerProduccion = () => {
  const [ordenes, setOrdenes] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedOrdenId, setSelectedOrdenId] = useState(null);

  useEffect(() => {
    const fetchOrdenes = async () => {
      try {
        const url = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        const response = await fetch(`${url}/api/ordenes-produccion`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        });
        
        if (!response.ok) {
          throw new Error('No se pudieron cargar las órdenes');
        }
        
        const data = await response.json();
        setOrdenes(Array.isArray(data) ? data : []);
      } catch (err) {
        console.error("Error cargando órdenes:", err);
        setError("Error de conexión al cargar el taller.");
      } finally {
        setIsLoading(false);
      }
    };

    fetchOrdenes();
  }, []);

  const openFacturacion = (ordenId) => {
    setSelectedOrdenId(ordenId);
    setIsModalOpen(true);
  };

  const ordenesInternas = ordenes.filter(o => o.tipo_produccion === 'interna');
  const ordenesTercerizadas = ordenes.filter(o => o.tipo_produccion === 'tercerizada');

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64 text-[#424754] font-['Inter']">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#0058be] mr-3"></div>
        Cargando órdenes desde el taller...
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-[#ffdad6] text-[#93000a] rounded-xl font-['Inter']">
        <p className="font-bold">{error}</p>
      </div>
    );
  }

  return (
    <>
      <div className="mb-8 font-['Inter']">
        <h2 className="font-['Manrope'] text-2xl lg:text-3xl font-bold text-[#0b1c30]">Taller</h2>
        <p className="text-sm text-[#424754]">Gestión de Producción y Tercerización</p>
      </div>

      {/* Section: Producción Interna */}
      <div className="mb-6 space-y-4 font-['Inter']">
        <div className="flex items-center justify-between px-1">
          <span className="font-['Manrope'] font-semibold text-sm uppercase tracking-wider text-[#0058be]">Producción Interna</span>
          <span className="text-[10px] font-bold bg-[#2170e4] text-[#fefcff] px-2 py-0.5 rounded-full">
            {ordenesInternas.length} ACTIVAS
          </span>
        </div>

        {ordenesInternas.length === 0 ? (
          <p className="text-sm text-[#727785] italic px-1">No hay órdenes internas en proceso.</p>
        ) : (
          ordenesInternas.map(orden => (
            <div key={orden.id} className="bg-[#ffffff] rounded-xl p-5 shadow-[0_4px_6px_-1px_rgba(11,28,48,0.05)] relative overflow-hidden group">
              <div className="absolute left-0 top-0 bottom-0 w-1.5 bg-[#0058be]"></div>
              
              <div className="flex justify-between items-start mb-4">
                <div>
                  <span className="text-[10px] font-bold text-[#727785] uppercase tracking-tighter">COT-{orden.cotizacion_id}</span>
                  <h3 className="font-['Manrope'] font-bold text-lg leading-tight text-[#0b1c30]">
                    Orden #{orden.id}
                  </h3>
                </div>
                <div className="text-right">
                  <span className="block text-xs font-semibold text-[#0058be] uppercase">{orden.estado}</span>
                </div>
              </div>

              <div className="mb-5">
                <div className="w-full bg-[#e5eeff] h-2 rounded-full overflow-hidden">
                  <div className="bg-[#0058be] h-full w-[85%] rounded-full"></div>
                </div>
                <div className="flex justify-between mt-2">
                  <span className="text-[10px] font-medium text-[#424754] italic">Avance estimado</span>
                  <span className="text-[10px] font-bold text-[#424754]">Plazo: Variable</span>
                </div>
              </div>

              <div className="bg-[#eff4ff] rounded-lg p-3">
                <div className="flex justify-between items-center">
                  <span className="text-[10px] font-bold text-[#c2c6d6] uppercase tracking-widest">Acciones</span>
                  <button 
                    onClick={() => openFacturacion(orden.cotizacion_id)}
                    className="text-xs font-bold text-[#0058be] hover:text-[#2170e4] transition-colors"
                  >
                    Facturar Orden →
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Section: Tercerización (Broker) */}
      <div className="mb-6 space-y-4 font-['Inter']">
        <div className="flex items-center justify-between px-1">
          <span className="font-['Manrope'] font-semibold text-sm uppercase tracking-wider text-[#6b38d4]">Tercerización</span>
          <span className="text-[10px] font-bold bg-[#8455ef]/20 text-[#6b38d4] px-2 py-0.5 rounded-full">
            {ordenesTercerizadas.length} EN CURSO
          </span>
        </div>

        {ordenesTercerizadas.length === 0 ? (
          <p className="text-sm text-[#727785] italic px-1">No hay órdenes tercerizadas en proceso.</p>
        ) : (
          ordenesTercerizadas.map(orden => (
            <div key={orden.id} className="bg-[#ffffff] rounded-xl p-5 shadow-[0_4px_6px_-1px_rgba(11,28,48,0.05)] relative overflow-hidden">
              <div className="absolute left-0 top-0 bottom-0 w-1.5 bg-[#6b38d4]"></div>
              
              <div className="flex justify-between items-start mb-3">
                <div>
                  <span className="text-[10px] font-bold text-[#727785] uppercase tracking-tighter">COT-{orden.cotizacion_id}</span>
                  <h3 className="font-['Manrope'] font-bold text-lg leading-tight text-[#0b1c30]">
                    Orden #{orden.id}
                  </h3>
                </div>
                <div className="bg-[#e9ddff] text-[#5516be] px-2 py-1 rounded text-[9px] font-extrabold uppercase tracking-tighter">
                  Externo
                </div>
              </div>

              <div className="flex justify-between items-center mt-4 pt-3 border-t border-dashed border-[#c2c6d6]">
                <div className="flex flex-col">
                  <span className="text-[10px] font-medium text-[#424754]">Costo Tercerización</span>
                  <span className="text-lg font-['Manrope'] font-extrabold text-[#0b1c30]">
                    S/ {orden.costo_tercerizado || '0.00'}
                  </span>
                </div>
                <button 
                  onClick={() => openFacturacion(orden.cotizacion_id)}
                  className="bg-[#6b38d4] hover:bg-[#5516be] text-white text-xs font-bold py-2 px-4 rounded-lg transition-colors shadow-sm shadow-[#6b38d4]/30"
                >
                  Facturar
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      <FacturacionModal 
        isOpen={isModalOpen} 
        onClose={() => setIsModalOpen(false)} 
        cotizacionId={selectedOrdenId}
      />
    </>
  );
};

export default TallerProduccion;
