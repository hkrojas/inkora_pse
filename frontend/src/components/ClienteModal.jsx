// Ruta: frontend/src/components/ClienteModal.jsx
import React, { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { X, Search, Save, Loader2 } from 'lucide-react';
import Input from './Input.jsx';
import Button from './Button.jsx';
import CustomSelect from './CustomSelect.jsx';
import { createCliente, updateCliente, consultarRucDni } from '../utils/apiUtils.js';
import { useToast } from '../context/ToastContext.jsx';

const ClienteModal = ({ isOpen, onClose, clienteToEdit, onSuccess }) => {
  const { register, handleSubmit, reset, setValue, watch, formState: { errors } } = useForm();
  const [loading, setLoading] = useState(false);
  const [consulting, setConsulting] = useState(false);
  const { showToast } = useToast();

  const tipoDoc = watch('tipo_documento', '6');

  useEffect(() => {
    if (isOpen) {
      if (clienteToEdit) reset(clienteToEdit);
      else reset({ tipo_documento: '6', numero_documento: '', razon_social: '', direccion: '', email: '', telefono: '' });
    }
  }, [isOpen, clienteToEdit, reset]);

  const handleConsultar = async () => {
    const num = watch('numero_documento');
    if (!num || (tipoDoc === '1' && num.length !== 8) || (tipoDoc === '6' && num.length !== 11)) {
      return showToast('Ingrese un número válido para consultar', 'warning');
    }
    setConsulting(true);
    try {
      const data = await consultarRucDni(num);
      setValue('razon_social', data.razon_social || '');
      setValue('direccion', data.direccion || '');
      showToast('Datos encontrados', 'success');
    } catch (error) { showToast('No se encontraron datos', 'error'); } 
    finally { setConsulting(false); }
  };

  const onSubmit = async (data) => {
    setLoading(true);
    try {
      if (clienteToEdit) { await updateCliente(clienteToEdit.id, data); showToast('Cliente actualizado', 'success'); } 
      else { await createCliente(data); showToast('Cliente creado', 'success'); }
      onSuccess(); onClose();
    } catch (error) { showToast(error.message, 'error'); } 
    finally { setLoading(false); }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 dark:bg-black/60 backdrop-blur-sm animate-in fade-in">
      <div className="bg-white dark:bg-surface-900 rounded-3xl shadow-2xl w-full max-w-lg overflow-hidden animate-slide-up border border-slate-100 dark:border-surface-800">
        <div className="flex justify-between items-center p-6 border-b border-slate-100 dark:border-surface-800 bg-slate-50/50 dark:bg-surface-950/50">
          <h3 className="text-lg font-black text-slate-900 dark:text-white">
            {clienteToEdit ? 'Editar Cliente' : 'Nuevo Cliente'}
          </h3>
          <button onClick={onClose} className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-surface-800 rounded-xl transition-all">
            <X size={20} strokeWidth={3} />
          </button>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="p-6 space-y-5">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
            <div className="sm:col-span-1">
              <CustomSelect
                label="Tipo Doc"
                options={[{value: '6', label: 'RUC'}, {value: '1', label: 'DNI'}]}
                value={tipoDoc}
                onChange={(val) => setValue('tipo_documento', val)}
              />
            </div>
            
            <div className="sm:col-span-2 relative">
               <div className="flex items-end gap-3 h-full">
                 <div className="flex-1">
                    <Input
                      label="Número de Documento"
                      {...register('numero_documento', { required: 'Requerido' })}
                      placeholder={tipoDoc === '6' ? '20123456789' : '12345678'}
                    />
                 </div>
                 <button
                   type="button"
                   onClick={handleConsultar}
                   disabled={consulting}
                   className="h-[52px] px-5 bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 rounded-2xl hover:bg-indigo-100 dark:hover:bg-indigo-500/20 font-bold transition-all flex items-center justify-center border-2 border-transparent"
                 >
                   {consulting ? <Loader2 className="w-5 h-5 animate-spin" /> : <Search className="w-5 h-5" strokeWidth={3} />}
                 </button>
               </div>
            </div>
          </div>

          <Input label="Razón Social / Nombre" error={errors.razon_social?.message} {...register('razon_social', { required: 'Requerido' })} />
          <Input label="Dirección" {...register('direccion')} />

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            <Input label="Email" type="email" {...register('email')} />
            <Input label="Teléfono" {...register('telefono')} />
          </div>

          <div className="flex gap-4 pt-4 mt-2 border-t border-slate-100 dark:border-surface-800">
            <Button type="button" variant="secondary" onClick={onClose} className="w-full">Cancelar</Button>
            <Button type="submit" isLoading={loading} icon={Save} className="w-full">Guardar</Button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ClienteModal;