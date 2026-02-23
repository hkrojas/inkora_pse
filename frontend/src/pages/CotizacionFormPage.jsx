import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm, useFieldArray } from 'react-hook-form';
import DashboardLayout from '../components/DashboardLayout.jsx';
import { ArrowLeft, Plus, Trash2, Save, FileText, Search, X, ChevronDown, Check } from 'lucide-react';
import Button from '../components/Button.jsx';
import Input from '../components/Input.jsx';
import { getClientes, getProductos, createCotizacion } from '../utils/apiUtils.js';
import { useToast } from '../context/ToastContext.jsx';
import ClienteModal from '../components/ClienteModal.jsx';
import ProductoModal from '../components/ProductoModal.jsx';

// --- COMPONENTE DE BÚSQUEDA INTELIGENTE CON ANIMACIONES ---
const SearchableSelect = ({ 
  options, 
  value, 
  onSelect, 
  placeholder, 
  filterFn, 
  renderItem, 
  getDisplayValue,
  disabled 
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const wrapperRef = useRef(null);

  // Sincronizar el texto del input cuando cambia el valor seleccionado externamente
  useEffect(() => {
    if (value && options.length > 0) {
      const selected = options.find(o => o.id === value);
      if (selected) {
        setSearchTerm(getDisplayValue(selected));
      }
    } else if (!value) {
      setSearchTerm('');
    }
  }, [value, options]);

  // Cerrar al hacer clic fuera
  useEffect(() => {
    function handleClickOutside(event) {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target)) {
        setIsOpen(false);
        // Si el usuario escribió algo pero no seleccionó, revertir al valor actual válido o limpiar
        if (value) {
           const selected = options.find(o => o.id === value);
           if (selected) setSearchTerm(getDisplayValue(selected));
        } else {
           setSearchTerm('');
        }
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [wrapperRef, value, options]);

  const filteredOptions = options.filter(item => filterFn(item, searchTerm));

  const handleSelect = (item) => {
    onSelect(item);
    setSearchTerm(getDisplayValue(item));
    setIsOpen(false);
  };

  return (
    <div className="relative w-full" ref={wrapperRef}>
      <div className="relative group">
        <div className={`absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none transition-colors duration-300 ${isOpen ? 'text-blue-500' : 'text-gray-400'}`}>
          <Search className="w-4 h-4" />
        </div>
        <input
          type="text"
          className={`
            w-full pl-10 pr-10 py-2.5 
            bg-white border text-sm rounded-xl outline-none transition-all duration-300
            ${isOpen 
              ? 'border-blue-500 ring-4 ring-blue-500/10 shadow-lg' 
              : 'border-gray-200 hover:border-gray-300'
            }
            disabled:bg-gray-50 disabled:text-gray-400
          `}
          placeholder={placeholder}
          value={searchTerm}
          onChange={(e) => {
            setSearchTerm(e.target.value);
            setIsOpen(true);
            if (e.target.value === '') onSelect(null);
          }}
          onFocus={() => setIsOpen(true)}
          disabled={disabled}
        />
        
        <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
          {searchTerm && !disabled ? (
            <button 
              type="button"
              onClick={() => { setSearchTerm(''); onSelect(null); }}
              className="text-gray-300 hover:text-red-500 transition-colors p-1 rounded-full hover:bg-red-50"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          ) : (
            <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform duration-300 ${isOpen ? 'rotate-180 text-blue-500' : ''}`} />
          )}
        </div>
      </div>

      {/* Lista Desplegable Animada */}
      {isOpen && (
        <div className="absolute z-50 w-full mt-2 bg-white border border-gray-100 rounded-xl shadow-2xl shadow-blue-900/10 max-h-72 overflow-y-auto animate-fade-in origin-top">
          {filteredOptions.length > 0 ? (
            <ul className="py-1.5">
              {filteredOptions.map((item) => {
                const isSelected = item.id === value;
                return (
                  <li
                    key={item.id}
                    onClick={() => handleSelect(item)}
                    className={`
                      relative px-4 py-3 cursor-pointer transition-all duration-200
                      border-l-4 
                      ${isSelected 
                        ? 'bg-blue-50 border-blue-500' 
                        : 'border-transparent hover:bg-slate-50 hover:border-blue-300 hover:pl-5'
                      }
                    `}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1">
                        {renderItem(item)}
                      </div>
                      {isSelected && <Check className="w-4 h-4 text-blue-600 mt-1" />}
                    </div>
                  </li>
                );
              })}
            </ul>
          ) : (
            <div className="px-4 py-8 text-center flex flex-col items-center justify-center text-gray-400">
              <div className="w-12 h-12 bg-gray-50 rounded-full flex items-center justify-center mb-2">
                <Search className="w-5 h-5 opacity-40" />
              </div>
              <p className="text-xs font-medium">No se encontraron resultados.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// --- PÁGINA PRINCIPAL ---
const CotizacionFormPage = () => {
  const navigate = useNavigate();
  const { showToast } = useToast();
  const { register, control, handleSubmit, watch, setValue, formState: { errors } } = useForm({
    defaultValues: {
      items: [{ producto_id: '', descripcion: '', cantidad: 1, precio_unitario: 0 }],
      moneda: 'PEN' // Valor por defecto
    }
  });

  const { fields, append, remove } = useFieldArray({ control, name: "items" });

  const [clientes, setClientes] = useState([]);
  const [productos, setProductos] = useState([]);
  const [showClienteModal, setShowClienteModal] = useState(false);
  const [showProductoModal, setShowProductoModal] = useState(false);

  // Cargar datos
  const loadData = async () => {
    try {
      const [c, p] = await Promise.all([getClientes(), getProductos()]);
      setClientes(c);
      setProductos(p);
    } catch (err) {
      showToast('Error cargando datos', 'error');
    }
  };

  useEffect(() => { loadData(); }, []);

  // Cálculos
  const items = watch('items');
  const moneda = watch('moneda'); // Observar cambios en la moneda
  const total = items.reduce((sum, item) => sum + (item.cantidad * item.precio_unitario), 0);
  const igv = total * 0.18;
  const subtotal = total / 1.18;

  // Manejadores de Selección Inteligente
  const handleClienteSelect = (cliente) => {
    if (cliente) {
      setValue('cliente_id', cliente.id);
    } else {
      setValue('cliente_id', '');
    }
  };

  const handleProductoSelect = (index, producto) => {
    if (producto) {
      setValue(`items.${index}.producto_id`, producto.id);
      setValue(`items.${index}.descripcion`, producto.nombre);
      setValue(`items.${index}.precio_unitario`, producto.precio_unitario);
    } else {
      setValue(`items.${index}.producto_id`, '');
    }
  };

  const onSubmit = async (data) => {
    if (!data.cliente_id) return showToast('Debe seleccionar un cliente válido', 'error');
    if (items.length === 0) return showToast('Agregue al menos un ítem', 'error');

    try {
      await createCotizacion({
        cliente_id: parseInt(data.cliente_id),
        fecha_vencimiento: data.fecha_vencimiento || null,
        moneda: data.moneda || 'PEN',
        items: data.items.map(i => ({
          producto_id: i.producto_id ? parseInt(i.producto_id) : null,
          descripcion: i.descripcion,
          cantidad: parseFloat(i.cantidad),
          precio_unitario: parseFloat(i.precio_unitario)
        }))
      });
      showToast('Cotización guardada exitosamente', 'success');
      navigate('/cotizaciones');
    } catch (error) {
      showToast(error.message, 'error');
    }
  };

  return (
    <DashboardLayout title="Nueva Cotización">
      <div className="max-w-5xl mx-auto pb-24">
        <button 
          onClick={() => navigate('/cotizaciones')} 
          className="flex items-center text-gray-500 hover:text-gray-700 mb-6 transition-colors group"
        >
          <div className="p-1 rounded-full group-hover:bg-gray-100 mr-2 transition-colors">
            <ArrowLeft className="w-4 h-4" />
          </div>
          <span className="font-medium">Volver al listado</span>
        </button>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* --- DATOS DEL CLIENTE --- */}
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100/80">
            <div className="flex justify-between items-center mb-6 border-b border-gray-50 pb-4">
              <h3 className="text-lg font-bold text-gray-800 flex items-center gap-2">
                <div className="p-2 bg-indigo-50 rounded-xl text-indigo-600">
                  <FileText className="w-5 h-5" />
                </div>
                Información del Cliente
              </h3>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div>
                <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-2 ml-1">
                  Buscar Cliente
                </label>
                <div className="flex gap-2">
                  <input type="hidden" {...register('cliente_id', { required: true })} />
                  
                  <SearchableSelect
                    options={clientes}
                    value={watch('cliente_id')}
                    onSelect={handleClienteSelect}
                    placeholder="Escriba nombre, RUC o DNI..."
                    getDisplayValue={(c) => c.razon_social}
                    filterFn={(item, query) => 
                      item.razon_social.toLowerCase().includes(query.toLowerCase()) || 
                      item.numero_documento.includes(query)
                    }
                    renderItem={(c) => (
                      <div>
                        <div className="font-semibold text-gray-800">{c.razon_social}</div>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className={`text-[10px] px-1.5 py-0.5 rounded border ${c.tipo_documento === '6' ? 'bg-blue-50 text-blue-600 border-blue-100' : 'bg-green-50 text-green-600 border-green-100'}`}>
                            {c.tipo_documento === '6' ? 'RUC' : 'DNI'}
                          </span>
                          <span className="text-xs text-gray-500 font-mono tracking-wide">{c.numero_documento}</span>
                        </div>
                      </div>
                    )}
                  />
                  
                  <button
                    type="button"
                    onClick={() => setShowClienteModal(true)}
                    className="p-3 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 active:scale-95 transition-all shadow-lg shadow-indigo-600/20"
                    title="Crear Nuevo Cliente"
                  >
                    <Plus size={20} />
                  </button>
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                 <Input label="Fecha Vencimiento" type="date" {...register('fecha_vencimiento')} />
                 
                 {/* --- SELECTOR DE MONEDA CORREGIDO --- */}
                 <div>
                    <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-2 ml-1">Moneda</label>
                    <div className="relative">
                      <select 
                        {...register('moneda')} 
                        className="w-full px-4 py-2.5 border border-gray-200 rounded-xl bg-white focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none appearance-none cursor-pointer"
                      >
                        <option value="PEN">Soles (S/)</option>
                        <option value="USD">Dólares ($)</option>
                      </select>
                      <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
                    </div>
                 </div>
              </div>
            </div>
          </div>

          {/* --- ITEMS / PRODUCTOS --- */}
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100/80">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-lg font-bold text-gray-800">Detalle de la Cotización</h3>
              {/* Botón para crear productos rápidamente */}
              <Button type="button" variant="secondary" size="sm" onClick={() => setShowProductoModal(true)} icon={Plus}>
                Nuevo Producto
              </Button>
            </div>
            
            <div className="space-y-4">
              {fields.map((field, index) => (
                <div key={field.id} className="flex flex-col md:flex-row gap-4 items-start p-4 bg-slate-50/50 rounded-2xl border border-slate-100 relative group transition-all hover:bg-white hover:shadow-md hover:border-indigo-100">
                  
                  {/* Selector Inteligente de Producto */}
                  <div className="flex-1 min-w-[280px]">
                    <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1.5 block ml-1">Producto</label>
                    <div className="flex gap-2">
                      <input type="hidden" {...register(`items.${index}.producto_id`)} />
                      
                      <SearchableSelect
                        options={productos}
                        value={watch(`items.${index}.producto_id`)}
                        onSelect={(prod) => handleProductoSelect(index, prod)}
                        placeholder="Buscar producto..."
                        getDisplayValue={(p) => p.nombre}
                        filterFn={(item, query) => 
                          item.nombre.toLowerCase().includes(query.toLowerCase()) || 
                          (item.codigo_interno && item.codigo_interno.toLowerCase().includes(query.toLowerCase()))
                        }
                        renderItem={(p) => (
                          <div className="flex justify-between items-center w-full">
                            <div className="flex-1 min-w-0 pr-4">
                              <div className="font-medium text-gray-800 truncate">{p.nombre}</div>
                              {p.codigo_interno && (
                                <div className="text-[10px] text-gray-400 font-mono mt-0.5">COD: {p.codigo_interno}</div>
                              )}
                            </div>
                            <div className="flex flex-col items-end">
                              <div className="text-sm font-bold text-indigo-600">S/ {p.precio_unitario.toFixed(2)}</div>
                              <span className="text-[10px] text-gray-400">inc. IGV</span>
                            </div>
                          </div>
                        )}
                      />
                      
                      <button
                        type="button"
                        onClick={() => setShowProductoModal(true)}
                        className="p-2.5 bg-indigo-50 border border-indigo-100 text-indigo-600 rounded-xl hover:bg-indigo-600 hover:text-white transition-colors"
                        title="Crear Nuevo Producto"
                      >
                        <Plus size={20} />
                      </button>
                    </div>
                  </div>
                  
                  <div className="flex-[2]">
                    <Input 
                      label="Descripción / Detalle" 
                      {...register(`items.${index}.descripcion`, { required: true })} 
                      placeholder="Descripción personalizada..."
                      className="bg-white"
                    />
                  </div>

                  <div className="w-24">
                    <Input 
                      label="Cant." 
                      type="number" 
                      step="0.01"
                      {...register(`items.${index}.cantidad`, { required: true, min: 0.01 })} 
                      className="bg-white text-center font-semibold"
                    />
                  </div>

                  <div className="w-32">
                    <Input 
                      label="P. Unit" 
                      type="number" 
                      step="0.01"
                      {...register(`items.${index}.precio_unitario`, { required: true, min: 0 })} 
                      className="bg-white text-right font-semibold"
                    />
                  </div>

                  <div className="pt-8">
                    <button 
                      type="button" 
                      onClick={() => remove(index)}
                      className="p-2.5 text-gray-300 hover:text-red-500 hover:bg-red-50 rounded-xl transition-colors"
                      title="Eliminar ítem"
                    >
                      <Trash2 size={18} />
                    </button>
                  </div>
                </div>
              ))}
            </div>

            <button
              type="button"
              onClick={() => append({ descripcion: '', cantidad: 1, precio_unitario: 0 })}
              className="mt-6 w-full py-4 border-2 border-dashed border-gray-200 rounded-2xl text-gray-500 font-semibold hover:border-indigo-400 hover:text-indigo-600 hover:bg-indigo-50/50 transition-all flex items-center justify-center gap-2 group"
            >
              <div className="p-1 rounded-full bg-gray-100 group-hover:bg-indigo-200 transition-colors">
                <Plus size={16} className="text-gray-500 group-hover:text-indigo-700" />
              </div>
              <span>Agregar línea adicional</span>
            </button>
          </div>

          {/* --- TOTALES FLOTANTES --- */}
          <div className="fixed bottom-0 right-0 left-0 lg:left-64 bg-white/90 backdrop-blur-md border-t border-gray-200 p-4 shadow-[0_-4px_20px_rgba(0,0,0,0.05)] z-40">
            <div className="max-w-5xl mx-auto flex flex-col sm:flex-row justify-between items-center gap-6">
              
              <div className="hidden sm:block text-xs text-gray-400">
                * Los montos incluyen IGV
              </div>

              <div className="flex flex-col sm:flex-row items-center gap-6 w-full sm:w-auto">
                <div className="flex gap-8 text-sm text-gray-600 w-full justify-between sm:w-auto sm:justify-start">
                  <div className="flex flex-col items-end">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400">Op. Gravada</span>
                    <span className="font-mono font-medium text-gray-900">
                      {moneda === 'PEN' ? 'S/' : '$'} {subtotal.toFixed(2)}
                    </span>
                  </div>
                  <div className="flex flex-col items-end">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400">IGV (18%)</span>
                    <span className="font-mono font-medium text-gray-900">
                      {moneda === 'PEN' ? 'S/' : '$'} {igv.toFixed(2)}
                    </span>
                  </div>
                  <div className="flex flex-col items-end">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-600">Total a Pagar</span>
                    <span className="font-mono text-2xl font-bold text-gray-900">
                      {moneda === 'PEN' ? 'S/' : '$'} {total.toFixed(2)}
                    </span>
                  </div>
                </div>
                
                <Button type="submit" size="lg" icon={Save} className="w-full sm:w-auto px-8 shadow-xl shadow-indigo-500/20 hover:shadow-indigo-500/30">
                  Generar Documento
                </Button>
              </div>
            </div>
          </div>
        </form>

        {/* --- MODALES --- */}
        <ClienteModal 
          isOpen={showClienteModal} 
          onClose={() => setShowClienteModal(false)}
          onSuccess={async () => { await loadData(); }}
        />

        <ProductoModal
          isOpen={showProductoModal}
          onClose={() => setShowProductoModal(false)}
          onSuccess={async () => { await loadData(); }}
        />
      </div>
    </DashboardLayout>
  );
};

export default CotizacionFormPage;