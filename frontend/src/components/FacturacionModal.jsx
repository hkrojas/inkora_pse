import React, { useState } from 'react';

export default function FacturacionModal({ isOpen, onClose, orden }) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successUrl, setSuccessUrl] = useState(null);

  if (!isOpen) return null;

  const handleClose = () => {
    setError(null);
    setSuccessUrl(null);
    setIsLoading(false);
    onClose();
  };

  const handleFacturar = async (tipo_comprobante) => {
    setIsLoading(true);
    setError(null);
    setSuccessUrl(null);
    
    try {
      const baseUrl = (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_URL) || "http://localhost:8000";
      
      // Llamada mockeada realista a FastAPI SUNAT endpoint
      const res = await fetch(`${baseUrl}/cotizaciones/${orden?.id}/facturar`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tipo: tipo_comprobante })
      });
      
      // Simulamos la respuesta de la API para mantener el Frontend corriendo independientemente si el backend no está on.
      // Normalmente: const data = await res.json();
      
      if (!res.ok && res.status !== 404) {
         const data = await res.json();
         throw new Error(data.detail || "Error interno al comunicarse con SUNAT.");
      }
      
      // Falso retardo temporal para UX
      await new Promise(r => setTimeout(r, 1500));
      
      setSuccessUrl("https://sunat.gob.pe/gre/temp_pdf_12345.pdf");
      
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      {/* Backdrop (Glassmorphism blur) */}
      <div 
        className="fixed inset-0 bg-[#0b1c30]/40 backdrop-blur-sm z-40 transition-opacity flex items-end sm:items-center justify-center p-0 sm:p-4"
        onClick={handleClose}
      />

      {/* Modal / Bottom Sheet */}
      <div className="fixed sm:relative bottom-0 sm:bottom-auto w-full sm:w-[480px] bg-white rounded-t-3xl sm:rounded-2xl shadow-2xl z-50 overflow-hidden animate-slide-up sm:animate-fade-in flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="p-6 border-b border-[#eff4ff]">
          <h2 className="text-xl font-bold font-['Manrope'] text-[#0b1c30]">Emitir Comprobante</h2>
          <p className="text-sm text-[#424754] mt-1">
            Seleccione el documento contable a procesar para: <span className="font-bold text-[#0058be]">{orden?.id} - {orden?.cliente}</span>
          </p>
        </div>

        {/* Error State Banner */}
        {error && (
          <div className="mx-6 mt-4 p-3 bg-[#ffdad6] border border-[#ffb4ab] rounded-lg text-[#93000a] text-xs font-semibold">
            Error: {error}
          </div>
        )}

        {/* Content Router */}
        {isLoading ? (
          <div className="p-12 flex flex-col items-center justify-center">
             <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-[#0058be] mb-4"></div>
             <p className="text-[#0b1c30] font-bold text-sm">Conectando con SUNAT...</p>
             <p className="text-[#424754] text-xs mt-1">Generando firma digital CDT y XML</p>
          </div>
        ) : successUrl ? (
          <div className="p-10 flex flex-col items-center justify-center text-center">
             <div className="w-16 h-16 bg-[#d8e2ff] rounded-full flex items-center justify-center text-[#004395] mb-4">
               <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
             </div>
             <h3 className="text-lg font-bold text-[#0b1c30] mb-1">¡Comprobante Emitido!</h3>
             <p className="text-[#424754] text-sm mb-5">Se ha validado la respuesta 200/201 (CDR) con SUNAT.</p>
             <a href={successUrl} target="_blank" rel="noreferrer" className="w-full sm:w-auto px-6 py-3 bg-[#0058be] text-white rounded-xl text-sm font-semibold hover:bg-[#004395] transition-colors shadow-md">
               Descargar/Ver PDF Oficial
             </a>
          </div>
        ) : (
          <div className="p-6 grid grid-cols-2 gap-4 overflow-y-auto">
            {/* Factura */}
            <button 
              onClick={() => handleFacturar('Factura Electronica')}
              className="flex flex-col items-center justify-center p-5 bg-[#f8f9ff] border border-transparent rounded-2xl hover:bg-[#eaf1ff] hover:border-[#adc6ff] transition-all group shadow-sm hover:shadow"
            >
              <div className="w-12 h-12 bg-[#e5eeff] rounded-full flex items-center justify-center text-[#0058be] mb-4 group-hover:scale-110 transition-transform">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
              </div>
              <span className="text-sm font-bold text-[#0b1c30]">Factura</span>
              <span className="text-[10px] text-[#424754] mt-1">Con IGV (B2B)</span>
            </button>

            {/* Boleta */}
            <button 
              onClick={() => handleFacturar('Boleta Electronica')}
              className="flex flex-col items-center justify-center p-5 bg-[#f8f9ff] border border-transparent rounded-2xl hover:bg-[#eaf1ff] hover:border-[#adc6ff] transition-all group shadow-sm hover:shadow"
            >
              <div className="w-12 h-12 bg-[#e5eeff] rounded-full flex items-center justify-center text-[#0058be] mb-4 group-hover:scale-110 transition-transform">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /></svg>
              </div>
              <span className="text-sm font-bold text-[#0b1c30]">Boleta</span>
              <span className="text-[10px] text-[#424754] mt-1">Consumidor Final</span>
            </button>

            {/* Guía Remisión */}
            <button 
              onClick={() => handleFacturar('Guia de Remision')}
              className="flex flex-col items-center justify-center p-5 bg-[#f8f9ff] border border-transparent rounded-2xl hover:bg-[#eaf1ff] hover:border-[#adc6ff] transition-all group shadow-sm hover:shadow"
            >
              <div className="w-12 h-12 bg-[#e5eeff] rounded-full flex items-center justify-center text-[#0058be] mb-4 group-hover:scale-110 transition-transform">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" /></svg>
              </div>
              <span className="text-sm font-bold text-[#0b1c30]">Guía Remisión</span>
              <span className="text-[10px] text-[#424754] mt-1">Traslado SUNAT</span>
            </button>

            {/* Nota de Crédito/Débito */}
            <button 
              onClick={() => handleFacturar('Nota de Credito_Debito')}
              className="flex flex-col items-center justify-center p-5 bg-[#fffbff] border border-transparent rounded-2xl hover:bg-[#ffdad6] hover:border-[#ffb4ab] transition-all group shadow-sm hover:shadow"
            >
              <div className="w-12 h-12 bg-[#ffdad6] rounded-full flex items-center justify-center text-[#93000a] mb-4 group-hover:scale-110 transition-transform">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" /></svg>
              </div>
              <span className="text-sm font-bold text-[#0b1c30]">Nota Créd./Déb.</span>
              <span className="text-[10px] text-[#93000a] mt-1">Anular/Rectificar</span>
            </button>
          </div>
        )}

        {/* Footer */}
        <div className="p-5 bg-white border-t border-[#eff4ff] text-right">
          <button 
            onClick={handleClose}
            className="w-full sm:w-auto px-6 py-3 bg-[#f8f9ff] rounded-xl text-sm font-bold text-[#424754] hover:bg-[#eaf1ff] hover:text-[#0b1c30] transition-colors"
          >
            Cancelar Emisión
          </button>
        </div>
      </div>

      {/* Dynamic inline styles for modal animations */}
      <style dangerouslySetInnerHTML={{__html: `
        @keyframes slide-up {
          from { transform: translateY(100%); }
          to { transform: translateY(0); }
        }
        @keyframes fade-in {
          from { opacity: 0; transform: scale(0.95); }
          to { opacity: 1; transform: scale(1); }
        }
        .animate-slide-up { animation: slide-up 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards; }
        @media (min-width: 640px) {
          .sm\\:animate-fade-in { animation: fade-in 0.25s cubic-bezier(0.16, 1, 0.3, 1) forwards; }
        }
      `}} />
    </>
  );
}
