import React, { useState } from 'react';
import FacturacionModal from './FacturacionModal';

const ordenesMock = [
  {
    id: 'ORD-001',
    cliente: 'Corporación Alpha',
    producto: 'Revista Corporativa Q4',
    tipo: 'interna',
    estado: 'En Producción',
    bom: [
      { insumo: 'Papel Couché 150g', cantidad: '12 Resmas', merma: '5%' },
      { insumo: 'Tintas CMYK Premium', cantidad: '4.5 Litros', merma: '2%' }
    ]
  },
  {
    id: 'ORD-002',
    cliente: 'Boutique Elegance',
    producto: 'Packaging Rígido Lujo',
    tipo: 'tercerizada',
    estado: 'Derivada',
    proveedor: 'Cartonajes del Sur S.A.',
    costo_tercerizado: 'S/ 1,450.00'
  }
];

export default function TallerProduccion() {
  const [modalOpen, setModalOpen] = useState(false);
  const [ordenActiva, setOrdenActiva] = useState(null);

  const handleOpenFacturacion = (orden) => {
    setOrdenActiva(orden);
    setModalOpen(true);
  };

  return (
    <div className="min-h-screen bg-[#f8f9ff] font-['Inter'] text-[#0b1c30] p-4 md:p-8">
      {/* Header */}
      <header className="mb-10">
        <h1 className="text-3xl md:text-4xl font-bold font-['Manrope'] tracking-tight mb-2">Taller y Producción</h1>
        <p className="text-[#424754] text-sm">Gestión de tableros de producción interna y tercerización (Broker).</p>
      </header>

      {/* Grid de Órdenes */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {ordenesMock.map((orden) => (
          <div 
            key={orden.id} 
            className="bg-white rounded-xl p-5 border border-transparent hover:shadow-[0_10px_15px_-3px_rgba(11,28,48,0.05)] transition-shadow duration-300 flex flex-col"
            style={{ backgroundColor: '#ffffff', boxShadow: '0 4px 6px -1px rgba(11, 28, 48, 0.03)' }}
          >
            {/* Header del Card */}
            <div className="flex justify-between items-start mb-4">
              <div>
                <span className="text-xs font-semibold text-[#6b38d4] bg-[#e9ddff] px-2 py-1 rounded-md mb-2 inline-block">
                  {orden.id}
                </span>
                <h3 className="text-lg font-bold font-['Manrope']">{orden.producto}</h3>
                <p className="text-xs text-[#424754]">{orden.cliente}</p>
              </div>
              
              {orden.tipo === 'tercerizada' && (
                <span className="text-xs font-medium text-[#924700] bg-[#ffdcc6] px-2 py-1 rounded-full whitespace-nowrap">
                  Tercerizada
                </span>
              )}
              {orden.tipo === 'interna' && (
                <span className="text-xs font-medium text-[#004395] bg-[#d8e2ff] px-2 py-1 rounded-full whitespace-nowrap">
                  Interna
                </span>
              )}
            </div>

            {/* Cuerpo del Card / Variante */}
            <div className="bg-[#eff4ff] rounded-lg p-4 mb-6 flex-grow">
              {orden.tipo === 'interna' ? (
                <div>
                  <h4 className="text-[11px] font-bold text-[#0058be] mb-3 uppercase tracking-wider">Receta (BOM) & Mermas</h4>
                  <ul className="space-y-3">
                    {orden.bom.map((item, idx) => (
                      <li key={idx} className="flex justify-between items-center text-sm border-b border-[#dce9ff] pb-2 last:border-0 last:pb-0">
                        <span className="font-medium">{item.insumo}</span>
                        <div className="text-right">
                          <span className="block">{item.cantidad}</span>
                          <span className="text-[10px] bg-white px-1.5 py-0.5 rounded text-[#424754] mt-1 shadow-sm inline-block">Merma: {item.merma}</span>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : (
                <div className="flex flex-col justify-center h-full">
                  <h4 className="text-[11px] font-bold text-[#b75b00] mb-3 uppercase tracking-wider">Detalles de Proveedor (Broker)</h4>
                  <div className="bg-white p-3 rounded shadow-sm">
                    <p className="text-sm font-medium mb-1 flex justify-between"><span className="text-[#424754]">Proveedor:</span> <span>{orden.proveedor}</span></p>
                    <p className="text-sm font-bold flex justify-between"><span className="text-[#424754]">Costo Acordado:</span> <span className="text-[#924700]">{orden.costo_tercerizado}</span></p>
                  </div>
                </div>
              )}
            </div>

            {/* Acciones */}
            <div className="flex items-center gap-3 mt-auto">
              <button 
                onClick={() => handleOpenFacturacion(orden)}
                className="flex-1 bg-gradient-to-br from-[#0058be] to-[#2170e4] text-white py-2.5 rounded-xl text-sm font-semibold hover:opacity-90 transition-opacity shadow-sm"
              >
                Facturar Orden
              </button>
              <button className="px-4 py-2.5 bg-[#e5eeff] text-[#0058be] rounded-xl text-sm font-semibold hover:bg-[#dce9ff] transition-colors">
                Ver Ficha
              </button>
            </div>
          </div>
        ))}
      </div>

      <FacturacionModal 
        isOpen={modalOpen} 
        onClose={() => setModalOpen(false)} 
        orden={ordenActiva} 
      />
    </div>
  );
}
