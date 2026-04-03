<script>
  import { X, Plus, Trash2, Save, Loader2, UserPlus, Package } from 'lucide-svelte';
  import { onMount, createEventDispatcher } from 'svelte';
  import { api } from '$lib/utils/api';

  export let show = false;
  const dispatch = createEventDispatcher();

  let loading = false;
  let subtotal = 0;
  let igv = 0;
  let total = 0;

  let clientes = [];
  let productos = [];

  let formData = {
    cliente_id: '',
    moneda: 'PEN',
    items: [
      { producto_id: '', descripcion: '', cantidad: 1, precio_unitario: 0 }
    ]
  };

  onMount(async () => {
    try {
      const [resClientes, resProductos] = await Promise.all([
        api.get('/clientes/'),
        api.get('/productos/')
      ]);
      clientes = resClientes;
      productos = resProductos;
    } catch (error) {
      console.error('Error cargando catálogos:', error);
    }
  });

  $: {
    subtotal = formData.items.reduce((acc, item) => acc + (Number(item.cantidad) * Number(item.precio_unitario)), 0);
    igv = subtotal * 0.18;
    total = subtotal + igv;
  }

  function addItem() {
    formData.items = [...formData.items, { producto_id: '', descripcion: '', cantidad: 1, precio_unitario: 0 }];
  }

  function removeItem(index) {
    if (formData.items.length > 1) {
      formData.items = formData.items.filter((_, i) => i !== index);
    }
  }

  function onProductChange(index) {
    const item = formData.items[index];
    const product = productos.find(p => p.id == item.producto_id);
    if (product) {
      item.descripcion = product.nombre;
      item.precio_unitario = Number(product.precio_unitario);
      formData.items = [...formData.items];
    }
  }

  async function handleSubmit() {
    if (!formData.cliente_id) return alert('Seleccione un cliente');
    if (formData.items.some(i => !i.descripcion || Number(i.precio_unitario) <= 0)) return alert('Complete los items correctamente');

    loading = true;
    try {
      const payload = {
        ...formData,
        cliente_id: Number(formData.cliente_id),
        items: formData.items.map(i => ({
          ...i,
          producto_id: i.producto_id ? Number(i.producto_id) : null,
          cantidad: Number(i.cantidad),
          precio_unitario: Number(i.precio_unitario)
        }))
      };
      await api.post('/cotizaciones/', payload);
      dispatch('success');
      close();
    } catch (error) {
      alert('Error al crear cotización: ' + (error.message || 'Error desconocido'));
    } finally {
      loading = false;
    }
  }

  function close() {
    show = false;
    dispatch('close');
    // Reset form
    formData = {
      cliente_id: '',
      moneda: 'PEN',
      items: [{ producto_id: '', descripcion: '', cantidad: 1, precio_unitario: 0 }]
    };
  }
</script>

{#if show}
  <div class="fixed inset-0 z-[100] flex items-center justify-center p-4 backdrop-blur-md bg-on-surface/20 animate-in fade-in duration-300">
    <div class="bg-surface-container-lowest w-full max-w-5xl max-h-[90vh] rounded-2xl sm:rounded-[2.5rem] shadow-2xl border border-outline-variant/10 flex flex-col overflow-hidden animate-in zoom-in-95 slide-in-from-bottom-4 duration-500">
      
      <!-- Header -->
      <div class="p-4 sm:p-8 border-b border-outline-variant/5 flex justify-between items-center bg-surface-container-low/30">
        <div>
          <h2 class="text-xl sm:text-3xl font-bold text-on-surface tracking-tight">Nueva Cotización</h2>
          <p class="text-on-surface-variant text-sm mt-1">Completa los datos para generar el documento.</p>
        </div>
        <button on:click={close} class="p-3 rounded-2xl hover:bg-surface-container-high transition-all text-on-surface-variant">
          <X size={24} />
        </button>
      </div>

      <div class="flex-1 overflow-y-auto p-4 sm:p-6 md:p-10 space-y-8 sm:space-y-10">
        <!-- Cliente y General -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div class="space-y-3">
            <label class="text-sm font-bold text-on-surface-variant uppercase tracking-widest ml-1" for="cliente">Cliente</label>
            <div class="relative group">
               <UserPlus size={18} class="absolute left-4 top-3.5 text-on-surface-variant group-focus-within:text-primary transition-colors" />
               <select 
                 id="cliente"
                 bind:value={formData.cliente_id}
                 class="w-full h-12 pl-12 pr-6 rounded-2xl bg-surface-container-low border-none focus:ring-2 focus:ring-primary/20 text-sm font-medium focus:bg-surface-container-lowest transition-all"
               >
                 <option value="" disabled>Seleccionar cliente...</option>
                 {#each clientes as cliente}
                   <option value={cliente.id}>{cliente.razon_social} ({cliente.numero_documento})</option>
                 {/each}
               </select>
            </div>
          </div>
          <div class="space-y-3">
            <label class="text-sm font-bold text-on-surface-variant uppercase tracking-widest ml-1" for="moneda">Moneda</label>
            <select 
              id="moneda"
              bind:value={formData.moneda}
               class="w-full h-12 px-6 rounded-2xl bg-surface-container-low border-none focus:ring-2 focus:ring-primary/20 text-sm font-medium focus:bg-surface-container-lowest transition-all"
            >
              <option value="PEN">Soles (PEN)</option>
              <option value="USD">Dólares (USD)</option>
            </select>
          </div>
        </div>

        <!-- Items -->
        <div class="space-y-6">
          <div class="flex justify-between items-center px-2">
            <h3 class="text-xl font-bold text-on-surface flex items-center gap-3">
              <Package size={22} class="text-primary" />
              Items de Cotización
            </h3>
            <button 
              on:click={addItem}
              class="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-primary shadow-lg shadow-primary/20 text-white font-bold text-sm hover:scale-105 transition-all"
            >
              <Plus size={18} />
              Agregar Item
            </button>
          </div>

          <div class="space-y-4">
            {#each formData.items as item, i}
          <div class="grid grid-cols-12 gap-4 items-end bg-surface-container-low/40 p-5 rounded-[2rem] border border-outline-variant/10 group hover:border-primary/20 transition-all">
                <div class="col-span-12 md:col-span-5 space-y-2">
                  <label class="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest ml-1" for="prod-{i}">Producto / Descripción</label>
                  <select 
                    id="prod-{i}"
                    bind:value={item.producto_id} 
                    on:change={() => onProductChange(i)}
                    class="w-full h-11 px-4 rounded-xl bg-surface-container-lowest border-none text-sm font-medium focus:ring-2 focus:ring-primary/10"
                  >
                    <option value="">Servicio Personalizado...</option>
                    {#each productos as prod}
                      <option value={prod.id}>{prod.nombre} (S/ {prod.precio_unitario})</option>
                    {/each}
                  </select>
                  <input 
                    type="text" 
                    bind:value={item.descripcion}
                    placeholder="Descripción detallada del trabajo..."
                    class="w-full h-11 px-4 rounded-xl bg-surface-container-lowest border-none text-sm focus:ring-2 focus:ring-primary/10"
                  />
                </div>
                <div class="col-span-4 md:col-span-2 space-y-2">
                  <label class="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest ml-1" for="cant-{i}">Cant.</label>
                  <input 
                    id="cant-{i}"
                    type="number" 
                    bind:value={item.cantidad}
                    min="1"
                    class="w-full h-11 px-4 rounded-xl bg-surface-container-lowest border-none text-sm focus:ring-2 focus:ring-primary/10"
                  />
                </div>
                <div class="col-span-5 md:col-span-3 space-y-2">
                  <label class="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest ml-1" for="prec-{i}">Precio Unit.</label>
                  <div class="relative">
                    <span class="absolute left-4 top-3 text-xs font-bold text-on-surface-variant">S/</span>
                    <input 
                      id="prec-{i}"
                      type="number" 
                      step="0.01"
                      bind:value={item.precio_unitario}
                      class="w-full h-11 pl-9 pr-4 rounded-xl bg-surface-container-lowest border-none text-sm font-bold focus:ring-2 focus:ring-primary/10"
                    />
                  </div>
                </div>
                <div class="col-span-3 md:col-span-2 flex justify-end">
                   <button 
                    on:click={() => removeItem(i)}
                    class="p-3 rounded-xl text-on-surface-variant hover:text-error hover:bg-error/10 transition-all"
                    disabled={formData.items.length === 1}
                   >
                     <Trash2 size={20} />
                   </button>
                </div>
              </div>
            {/each}
          </div>
        </div>
      </div>

      <!-- Footer / Totales -->
      <div class="p-4 sm:p-8 bg-surface-container-low border-t border-outline-variant/10 flex flex-col md:flex-row justify-between items-center gap-6 sm:gap-8">
        <div class="flex flex-wrap gap-6 sm:gap-12 text-on-surface justify-center md:justify-start w-full md:w-auto">
          <div>
            <p class="text-[10px] uppercase font-bold text-on-surface-variant tracking-widest mb-1">Subtotal</p>
            <p class="text-xl font-bold">S/ {subtotal.toFixed(2)}</p>
          </div>
          <div>
            <p class="text-[10px] uppercase font-bold text-on-surface-variant tracking-widest mb-1">IGV (18%)</p>
            <p class="text-xl font-bold text-tertiary">S/ {igv.toFixed(2)}</p>
          </div>
          <div class="bg-primary/5 px-6 py-2 rounded-2xl border border-primary/10 shadow-inner">
            <p class="text-[10px] uppercase font-bold text-primary tracking-widest mb-1">Total a Pagar</p>
            <p class="text-3xl font-black text-primary">S/ {total.toFixed(2)}</p>
          </div>
        </div>

        <div class="flex gap-4 w-full md:w-auto">
          <button 
            on:click={close}
            class="flex-1 md:flex-none px-8 py-4 rounded-2xl font-bold text-on-surface-variant hover:bg-surface-container-highest transition-all"
          >
            Cancelar
          </button>
          <button 
            on:click={handleSubmit}
            disabled={loading}
            class="flex-1 md:flex-none btn-primary flex items-center justify-center gap-3 min-w-[200px]"
          >
            {#if loading}
              <Loader2 size={20} class="animate-spin" />
              Procesando...
            {:else}
              <Save size={20} />
              Guardar Cotización
            {/if}
          </button>
        </div>
      </div>
    </div>
  </div>
{/if}

<style>
  input[type="number"]::-webkit-inner-spin-button,
  input[type="number"]::-webkit-outer-spin-button {
    -webkit-appearance: none;
    margin: 0;
  }
</style>
