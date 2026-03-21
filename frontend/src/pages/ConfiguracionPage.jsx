// Ruta: frontend/src/pages/ConfiguracionPage.jsx
import React, { useEffect, useState } from 'react';
import { useForm, useFieldArray } from 'react-hook-form';
import DashboardLayout from '../components/DashboardLayout.jsx';
import { Save, Upload, Trash2, Building, Palette, CreditCard, Lock, Plus } from 'lucide-react';
import Button from '../components/Button.jsx';
import Input from '../components/Input.jsx';
import CustomSelect from '../components/CustomSelect.jsx';
import { useToast } from '../context/ToastContext.jsx';
import { getUserProfile, updateUserProfile, uploadLogo } from '../utils/apiUtils.js';
import { config } from '../config.js';

const ConfiguracionPage = () => {
  const { register, control, handleSubmit, setValue, watch } = useForm();
  const { fields, append, remove } = useFieldArray({ control, name: "bank_accounts" });
  
  const [loading, setLoading] = useState(false);
  const [logoPreview, setLogoPreview] = useState(null);
  const { showToast } = useToast();

  const primaryColor = watch('primary_color', '#4f46e5');

  useEffect(() => { fetchProfile(); }, []);

  const fetchProfile = async () => {
    try {
      const user = await getUserProfile();
      setValue('business_name', user.business_name || '');
      setValue('business_ruc', user.business_ruc || '');
      setValue('business_address', user.business_address || '');
      setValue('business_phone', user.business_phone || '');
      setValue('primary_color', user.primary_color || '#4f46e5');
      setValue('apisperu_token', user.apisperu_token || '');
      setValue('apisperu_url', user.apisperu_url || '');
      setValue('pdf_note_1', user.pdf_note_1 || '');
      setValue('pdf_note_1_color', user.pdf_note_1_color || '#ef4444');
      setValue('pdf_note_2', user.pdf_note_2 || '');
      setValue('bank_accounts', Array.isArray(user.bank_accounts) ? user.bank_accounts : []);
      if (user.logo_filename) setLogoPreview(`${config.API_URL}/logos/${user.logo_filename}`);
    } catch (error) { showToast('Error al cargar perfil', 'error'); }
  };

  const handleLogoUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onloadend = () => setLogoPreview(reader.result);
    reader.readAsDataURL(file);
    try {
      await uploadLogo(file);
      showToast('Logo subido correctamente', 'success');
    } catch (error) { showToast('Error al subir logo', 'error'); }
  };

  const onSubmit = async (data) => {
    setLoading(true);
    try {
      await updateUserProfile(data);
      showToast('Configuración guardada', 'success');
    } catch (error) { showToast('Error al guardar', 'error'); } 
    finally { setLoading(false); }
  };

  return (
    <DashboardLayout title="Configuración">
      <form onSubmit={handleSubmit(onSubmit)} className="max-w-4xl mx-auto space-y-8 pb-10">
        
        <div className="card p-8">
          <div className="flex items-center gap-3 mb-6 border-b border-slate-100 dark:border-surface-800 pb-4">
            <div className="p-2 bg-blue-50 dark:bg-blue-500/10 text-blue-600 dark:text-blue-400 rounded-lg"><Building size={20} /></div>
            <h3 className="text-lg font-black text-slate-900 dark:text-white">Identidad Empresarial</h3>
          </div>
          <div className="flex flex-col md:flex-row gap-10">
            <div className="flex flex-col items-center gap-4 w-full md:w-48 shrink-0">
              <div className="w-40 h-40 rounded-3xl border-2 border-dashed border-slate-200 dark:border-surface-700 flex items-center justify-center overflow-hidden bg-[#fcfdfe] dark:bg-surface-900 relative group transition-colors hover:border-indigo-400 dark:hover:border-indigo-500">
                {logoPreview ? <img src={logoPreview} alt="Logo" className="w-full h-full object-contain p-4" /> : (
                  <div className="text-center text-slate-400"><Upload className="w-8 h-8 mx-auto mb-2" /><span className="text-xs font-bold uppercase">Subir Logo</span></div>
                )}
                <input type="file" accept="image/png, image/jpeg" onChange={handleLogoUpload} className="absolute inset-0 opacity-0 cursor-pointer" />
              </div>
              <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider text-center">PNG o JPG <br/>Max 2MB</p>
            </div>
            <div className="flex-1 space-y-5">
              <Input label="Razón Social / Nombre" {...register('business_name')} />
              <div className="grid grid-cols-2 gap-5">
                <Input label="RUC" {...register('business_ruc')} />
                <Input label="Teléfono" {...register('business_phone')} />
              </div>
              <Input label="Dirección Fiscal" {...register('business_address')} />
            </div>
          </div>
        </div>

        <div className="card p-8">
          <div className="flex items-center gap-3 mb-6 border-b border-slate-100 dark:border-surface-800 pb-4">
            <div className="p-2 bg-purple-50 dark:bg-purple-500/10 text-purple-600 dark:text-purple-400 rounded-lg"><Palette size={20} /></div>
            <h3 className="text-lg font-black text-slate-900 dark:text-white">Diseño PDF</h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div>
              <label className="block text-[11px] font-bold text-slate-400 dark:text-surface-400 uppercase tracking-widest mb-3">Color de Marca</label>
              <div className="flex items-center gap-4 p-3 bg-slate-50 dark:bg-surface-900 rounded-2xl border border-slate-100 dark:border-surface-800">
                <input type="color" {...register('primary_color')} className="w-12 h-12 rounded-xl cursor-pointer border-0 bg-transparent" />
                <span className="text-sm font-mono text-slate-600 dark:text-surface-300 font-bold">{primaryColor}</span>
              </div>
            </div>
            <div className="space-y-5">
              <div className="flex gap-4 items-end">
                 <div className="flex-1">
                   <Input label="Nota al Pie 1" {...register('pdf_note_1')} />
                 </div>
                 <div className="mb-2">
                   <input type="color" {...register('pdf_note_1_color')} className="w-10 h-10 rounded-lg cursor-pointer" title="Color de la nota" />
                 </div>
              </div>
              <Input label="Nota Secundaria" {...register('pdf_note_2')} />
            </div>
          </div>
        </div>

        <div className="card p-8">
          <div className="flex items-center justify-between mb-6 border-b border-slate-100 dark:border-surface-800 pb-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 rounded-lg"><CreditCard size={20} /></div>
              <h3 className="text-lg font-black text-slate-900 dark:text-white">Cuentas Bancarias</h3>
            </div>
            <button type="button" onClick={() => append({ banco: '', moneda: 'Soles', cuenta: '', cci: '' })} className="text-xs font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 hover:text-emerald-700 bg-emerald-50 dark:bg-emerald-500/10 px-4 py-2 rounded-xl flex items-center transition-colors">
              <Plus className="w-4 h-4 mr-1.5" strokeWidth={3} /> Añadir
            </button>
          </div>
          <div className="space-y-4">
            {fields.map((field, index) => (
              <div key={field.id} className="flex flex-col md:flex-row gap-4 p-5 bg-slate-50 dark:bg-surface-900/50 rounded-3xl border border-slate-100 dark:border-surface-800 relative group items-start">
                <div className="flex-1 w-full"><Input label="Banco" {...register(`bank_accounts.${index}.banco`)} /></div>
                <div className="w-full md:w-36"><CustomSelect label="Moneda" options={[{value:'Soles', label:'Soles'}, {value:'Dólares', label:'Dólares'}]} value={watch(`bank_accounts.${index}.moneda`)} onChange={(v) => setValue(`bank_accounts.${index}.moneda`, v)} /></div>
                <div className="flex-1 w-full"><Input label="N° Cuenta" {...register(`bank_accounts.${index}.cuenta`)} /></div>
                <div className="flex-1 w-full"><Input label="CCI" {...register(`bank_accounts.${index}.cci`)} /></div>
                <div className="pt-8">
                  <button type="button" onClick={() => remove(index)} className="p-3.5 text-slate-300 dark:text-surface-600 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-2xl transition-all">
                    <Trash2 size={20} strokeWidth={2.5} />
                  </button>
                </div>
              </div>
            ))}
            {fields.length === 0 && <p className="text-sm text-slate-400 text-center py-6 font-medium">No has registrado cuentas bancarias.</p>}
          </div>
        </div>

        <div className="card p-8 border-amber-100 dark:border-amber-900/30">
          <div className="flex items-center gap-3 mb-6 border-b border-slate-100 dark:border-surface-800 pb-4">
            <div className="p-2 bg-amber-50 dark:bg-amber-500/10 text-amber-600 dark:text-amber-400 rounded-lg"><Lock size={20} /></div>
            <h3 className="text-lg font-black text-slate-900 dark:text-white">API Facturación (SUNAT)</h3>
          </div>
          <div className="grid grid-cols-1 gap-6">
             <Input label="Token Bearer (APIsPERU)" type="password" {...register('apisperu_token')} placeholder="Token de producción..." />
             <Input label="URL Endpoint (Opcional)" {...register('apisperu_url')} placeholder="https://facturacion..." />
          </div>
        </div>

        <div className="flex justify-end pt-4">
          <Button type="submit" size="lg" icon={Save} isLoading={loading} className="px-10 py-4 shadow-xl shadow-indigo-600/20">
            GUARDAR CAMBIOS
          </Button>
        </div>
      </form>
    </DashboardLayout>
  );
};

export default ConfiguracionPage;