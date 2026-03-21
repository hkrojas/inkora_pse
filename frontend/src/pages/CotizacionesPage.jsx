// Ruta: frontend/src/pages/CotizacionFormPage.jsx
import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm, useFieldArray } from 'react-hook-form';
import DashboardLayout from '../components/DashboardLayout.jsx';
import { ArrowLeft, Plus, Trash2, Save, FileText, Search, X, Check } from 'lucide-react';
import Button from '../components/Button.jsx';
import Input from '../components/Input.jsx';
import DatePicker from '../components/DatePicker.jsx';
import CustomSelect from '../components/CustomSelect.jsx';
import { getClientes, getProductos, createCotizacion } from '../utils/apiUtils.js';
import { useToast } from '../context/ToastContext.jsx';
import ClienteModal from '../components/ClienteModal.jsx';
import ProductoModal from '../components/ProductoModal.jsx';

// BÚSQUEDA INTELIGENTE
const SearchableSelect = ({ options, value, onSelect, placeholder, filterFn, renderItem, getDisplayValue }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const wrapperRef = useRef(null);

  useEffect(() => {
    if (value && options.length > 0) {
      const selected = options.find(o => o.id === value);
      if (selected) setSearchTerm(getDisplayValue(selected));
    } else if (!value) setSearchTerm('');
  }, [value, options]);

  useEffect(() => {
    function handleClickOutside(event) {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target)) {
        setIsOpen(false);
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
    <div className="relative w-full group" ref={wrapperRef}>
      <div className="relative">
        <div className={`absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none transition-colors duration-300 ${isOpen ? 'text-indigo-500' : 'text-slate-400 dark:text-surface-500'}`}>
          <Search className="w-5 h-5" strokeWidth={2.5} />
        </div>
        <input
          type="text"
          className={`
            w-full pl-12 pr-12 py-3.5 bg-[#fcfdfe] dark:bg-surface-900 border-2 text-sm rounded-2xl outline-none transition-all duration-300 text-slate-900 dark:text-white
            ${isOpen ? 'border-indigo-600 dark:border-indigo-500 ring-[6px] ring-indigo-600/5 bg-white dark:bg-surface-800' : 'border-slate-100 dark:border-surface-700 hover:border-slate-200 dark:hover:border-surface-600'}
          `}
          placeholder={placeholder}
          value={searchTerm}
          onChange={(e) => {
            setSearchTerm(e.target.value);
            setIsOpen(true);
            if (e.target.value === '') onSelect(null);
          }}
          onFocus={() => setIsOpen(true)}
        />
        <div className="absolute inset-y-0 right-0 pr-4 flex items-center">
          {searchTerm && (
            <button type="button" onClick={() => { setSearchTerm(''); onSelect(null); }} className="text-slate-300 hover:text-red-500 transition-colors p-1.5 rounded-full hover:bg-red-50 dark:hover:bg-red-900/20">
              <X className="w-4 h-4" strokeWidth={3} />
            </button>
          )}
        </div>
      </div>

      {isOpen && (
        <div className="absolute z-50 w-full mt-2 bg-white dark:bg-surface-800 border border-slate-100 dark:border-surface-700 rounded-xl shadow-2xl shadow-indigo-900/10 dark:shadow-black/50 max-h-72 overflow-y-auto animate-fade-in origin-top py-2">
          {filteredOptions.length > 0 ? (
            <ul>
              {filteredOptions.map((item) => {
                const isSelected = item.id === value;
                return (
                  <li
                    key={item.id}
                    onClick={() => handleSelect(item)}
                    className={`
                      relative px-5 py-3 mx-2 rounded-xl cursor-pointer transition-all duration-200
                      ${isSelected ? 'bg-indigo-50 dark:bg-indigo-500/10' : 'hover:bg-slate-50 dark:hover:bg-surface-700'}
                    `}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1">{renderItem(item)}</div>
                      {isSelected && <Check className="w-5 h-5 text-indigo-600 dark:text-indigo-400 mt-1" strokeWidth={3} />}
                    </div>
                  </li>
                );
              })}
            </ul>
          ) : (
            <div className="px-4 py-8 text-center flex flex-col items-center justify-center text-slate-400 dark:text-surface-500">
              <div className="w-12 h-12 bg-slate-50 dark:bg-surface-900 rounded-full flex items-center justify-center mb-3">
                <Search className="w-5 h-5 opacity-50" />
              </div>
              <p className="text-xs font-bold uppercase tracking-wider">Sin resultados</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const CotizacionFormPage = () => {
  const navigate = useNavigate();
  const { showToast } = useToast();
  const { register, control, handleSubmit, watch, setValue } = useForm({
    defaultValues: {
      items: [{ producto_id: '', descripcion: '', cantidad: 1, precio_unitario: 0 }],
      moneda: 'PEN',
      fecha_vencimiento: ''
    }
  });

  const { fields, append, remove } = useFieldArray({ control, name: "items" });

  const [clientes, setClientes] = useState([]);
  const [productos, setProductos] = useState([]);
  const [showClienteModal, setShowClienteModal] = useState(false);
  const [showProductoModal, setShowProductoModal] = useState(false);

  const loadData = async () => {
    try {
      const [c, p] = await Promise.all([getClientes(), getProductos()]);
      setClientes(c);
      setProductos(p);
    } catch (err) { showToast('Error cargando datos', 'error'); }
  };

  useEffect(() => { loadData(); }, []);

  const items = watch('items');
  const moneda = watch('moneda');
  const fechaVencimiento = watch('fecha_vencimiento');
  
  const total = items.reduce((sum, item) => sum + (item.cantidad * item.precio_unitario), 0);
  const igv = total * 0.18;
  const subtotal = total / 1.18;

  const onSubmit = async (data) => {
    if (!data.cliente_id) return showToast('Debe seleccionar un cliente', 'error');
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
      showToast('Documento generado', 'success');
      navigate('/cotizaciones');
    } catch (error) { showToast(error.message, 'error'); }
  };

  return (
    <div className="pb-32">
      <button onClick={() => navigate('/cotizaciones')} className="flex items-center text-slate-500 dark:text-surface-400 hover:text-slate-800 dark:hover:text-white mb-8 transition-colors group font-bold text-sm">
        <div className="p-2 rounded-full bg-white dark:bg-surface-800 shadow-sm border border-slate-100 dark:border-surface-700 group-hover:bg-slate-50 dark:group-hover:bg-surface-700 mr-3 transition-all">
          <ArrowLeft className="w-4 h-4" strokeWidth={2.5} />
        </div>
        Volver al listado
      </button>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-8">
        
        {/* Sección Cliente */}
        <div className="card p-8 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-50 dark:bg-indigo-500/5 rounded-full blur-3xl -z-10 translate-x-1/2 -translate-y-1/2"></div>
          
          <h3 className="text-xl font-black text-slate-900 dark:text-white mb-8 flex items-center gap-3">
            <div className="p-2.5 bg-indigo-600 text-white rounded-xl shadow-lg shadow-indigo-600/30">
              <FileText className="w-5 h-5" />
            </div>
            Información del Cliente
          </h3>
          
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div>
              <label className="block text-[11px] font-bold text-slate-400 dark:text-surface-400 uppercase tracking-[0.15em] mb-2.5 ml-1">Buscar Cliente</label>
              <div className="flex gap-3">
                <SearchableSelect
                  options={clientes}
                  value={watch('cliente_id')}
                  onSelect={(c) => setValue('cliente_id', c ? c.id : '')}
                  placeholder="Escriba nombre o RUC..."
                  getDisplayValue={(c) => c.razon_social}
                  filterFn={(item, q) => item.razon_social.toLowerCase().includes(q.toLowerCase()) || item.numero_documento.includes(q)}
                  renderItem={(c) => (
                    <div>
                      <div className="font-bold text-slate-800 dark:text-white">{c.razon_social}</div>
                      <div className="flex items-center gap-2 mt-1">
                        <span className={`text-[9px] px-2 py-0.5 rounded-md font-bold uppercase tracking-wider ${c.tipo_documento === '6' ? 'bg-indigo-100 text-indigo-700 dark:bg-indigo-500/20 dark:text-indigo-300' : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300'}`}>
                          {c.tipo_documento === '6' ? 'RUC' : 'DNI'}
                        </span>
                        <span className="text-xs text-slate-500 dark:text-surface-400 font-mono">{c.numero_documento}</span>
                      </div>
                    </div>
                  )}
                />
                <button type="button" onClick={() => setShowClienteModal(true)} className="p-3.5 bg-indigo-600 text-white rounded-2xl hover:bg-indigo-700 active:scale-95 transition-all shadow-lg shadow-indigo-600/20 shrink-0">
                  <Plus size={20} strokeWidth={2.5} />
                </button>
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-6">
              <DatePicker 
                label="Fecha Vencimiento" 
                value={fechaVencimiento} 
                onChange={(val) => setValue('fecha_vencimiento', val)} 
              />
              <CustomSelect
                label="Moneda"
                options={[{value: 'PEN', label: 'Soles (S/)'}, {value: 'USD', label: 'Dólares ($)'}]}
                value={moneda}
                onChange={(val) => setValue('moneda', val)}
              />
            </div>
          </div>
        </div>

        {/* Sección Productos */}
        <div className="card p-8">
          <div className="flex justify-between items-end mb-8">
            <h3 className="text-xl font-black text-slate-900 dark:text-white">Detalle de Cotización</h3>
            <Button type="button" variant="secondary" onClick={() => setShowProductoModal(true)} icon={Plus}>
              Crear Producto
            </Button>
          </div>
          
          <div className="space-y-4">
            {fields.map((field, index) => (
              <div key={field.id} className="flex flex-col lg:flex-row gap-4 items-start p-5 bg-slate-50/50 dark:bg-surface-950/50 rounded-3xl border border-slate-100 dark:border-surface-800 relative group transition-all hover:bg-white dark:hover:bg-surface-900 hover:shadow-xl hover:shadow-slate-200/50 dark:hover:shadow-black/50 hover:border-indigo-100 dark:hover:border-indigo-900/50">
                
                <div className="flex-1 min-w-[300px]">
                  <label className="block text-[11px] font-bold text-slate-400 dark:text-surface-400 uppercase tracking-[0.15em] mb-2.5 ml-1">Producto</label>
                  <div className="flex gap-2">
                    <SearchableSelect
                      options={productos}
                      value={watch(`items.${index}.producto_id`)}
                      onSelect={(p) => {
                        if(p) {
                          setValue(`items.${index}.producto_id`, p.id);
                          setValue(`items.${index}.descripcion`, p.nombre);
                          setValue(`items.${index}.precio_unitario`, p.precio_unitario);
                        } else setValue(`items.${index}.producto_id`, '');
                      }}
                      placeholder="Buscar producto..."
                      getDisplayValue={(p) => p.nombre}
                      filterFn={(item, q) => item.nombre.toLowerCase().includes(q.toLowerCase()) || (item.codigo_interno && item.codigo_interno.toLowerCase().includes(q.toLowerCase()))}
                      renderItem={(p) => (
                        <div className="flex justify-between items-center w-full">
                          <div className="flex-1 min-w-0 pr-4">
                            <div className="font-bold text-slate-800 dark:text-white truncate">{p.nombre}</div>
                            {p.codigo_interno && <div className="text-[10px] text-slate-400 dark:text-surface-500 font-mono mt-1 uppercase">COD: {p.codigo_interno}</div>}
                          </div>
                          <div className="flex flex-col items-end shrink-0">
                            <div className="text-sm font-black text-indigo-600 dark:text-indigo-400">S/ {p.precio_unitario.toFixed(2)}</div>
                            <span className="text-[9px] text-slate-400 font-bold uppercase">inc. IGV</span>
                          </div>
                        </div>
                      )}
                    />
                  </div>
                </div>
                
                <div className="flex-[2] w-full">
                  <Input label="Descripción" {...register(`items.${index}.descripcion`, { required: true })} placeholder="Detalle adicional..." />
                </div>

                <div className="w-full lg:w-28 shrink-0">
                  <Input label="Cant." type="number" step="0.01" {...register(`items.${index}.cantidad`, { required: true, min: 0.01 })} className="text-center font-mono font-bold" />
                </div>

                <div className="w-full lg:w-36 shrink-0">
                  <Input label="P. Unit" type="number" step="0.01" {...register(`items.${index}.precio_unitario`, { required: true, min: 0 })} className="text-right font-mono font-bold text-indigo-600 dark:text-indigo-400" />
                </div>

                <div className="pt-8">
                  <button type="button" onClick={() => remove(index)} className="p-3.5 text-slate-300 dark:text-surface-600 hover:text-red-500 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-2xl transition-all">
                    <Trash2 size={20} strokeWidth={2.5} />
                  </button>
                </div>
              </div>
            ))}
          </div>

          <button
            type="button"
            onClick={() => append({ descripcion: '', cantidad: 1, precio_unitario: 0 })}
            className="mt-6 w-full py-5 border-2 border-dashed border-slate-200 dark:border-surface-700 rounded-3xl text-slate-500 dark:text-surface-400 font-bold hover:border-indigo-400 dark:hover:border-indigo-500 hover:text-indigo-600 dark:hover:text-indigo-400 hover:bg-indigo-50/50 dark:hover:bg-indigo-900/10 transition-all flex items-center justify-center gap-3 group"
          >
            <div className="p-1.5 rounded-full bg-slate-100 dark:bg-surface-800 group-hover:bg-indigo-100 dark:group-hover:bg-indigo-500/20 transition-colors">
              <Plus size={18} strokeWidth={3} className="text-slate-500 dark:text-surface-400 group-hover:text-indigo-600 dark:group-hover:text-indigo-400" />
            </div>
            AGREGAR LÍNEA ADICIONAL
          </button>
        </div>

        {/* Panel Inferior Flotante */}
        <div className="fixed bottom-0 right-0 left-0 lg:left-72 bg-white/80 dark:bg-surface-900/80 backdrop-blur-xl border-t border-slate-200/50 dark:border-surface-800 p-5 shadow-[0_-10px_40px_rgba(0,0,0,0.03)] dark:shadow-[0_-10px_40px_rgba(0,0,0,0.2)] z-40 transition-colors duration-300">
          <div className="max-w-7xl mx-auto flex flex-col sm:flex-row justify-between items-center gap-6">
            
            <div className="hidden sm:flex items-center gap-2 px-4 py-2 bg-slate-50 dark:bg-surface-800 rounded-xl">
              <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
              <span className="text-xs font-bold text-slate-500 dark:text-surface-400 uppercase tracking-wider">Cálculo Automático</span>
            </div>

            <div className="flex flex-col sm:flex-row items-center gap-8 w-full sm:w-auto">
              <div className="flex gap-10 text-sm text-slate-600 dark:text-surface-300 w-full justify-between sm:w-auto">
                <div className="flex flex-col items-end">
                  <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">Op. Gravada</span>
                  <span className="font-mono font-medium text-slate-900 dark:text-white text-lg">{moneda === 'PEN' ? 'S/' : '$'} {subtotal.toFixed(2)}</span>
                </div>
                <div className="flex flex-col items-end">
                  <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">IGV (18%)</span>
                  <span className="font-mono font-medium text-slate-900 dark:text-white text-lg">{moneda === 'PEN' ? 'S/' : '$'} {igv.toFixed(2)}</span>
                </div>
                <div className="flex flex-col items-end">
                  <span className="text-[10px] font-bold uppercase tracking-widest text-indigo-600 dark:text-indigo-400">Total a Pagar</span>
                  <span className="font-mono text-3xl font-black text-slate-900 dark:text-white leading-none">{moneda === 'PEN' ? 'S/' : '$'} {total.toFixed(2)}</span>
                </div>
              </div>
              
              <Button type="submit" size="lg" icon={Save} className="w-full sm:w-auto px-10 py-4 text-base shadow-xl shadow-indigo-600/20">
                GENERAR DOCUMENTO
              </Button>
            </div>
          </div>
        </div>
      </form>

      <ClienteModal isOpen={showClienteModal} onClose={() => setShowClienteModal(false)} onSuccess={loadData} />
      <ProductoModal isOpen={showProductoModal} onClose={() => setShowProductoModal(false)} onSuccess={loadData} />
    </div>
  );
};

export default CotizacionFormPage;