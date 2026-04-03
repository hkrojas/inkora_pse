<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/utils/api';

  let ordenes = [];
  let loading = true;
  let error = null;

  let columns = [
    { id: 'en_cola', name: 'En Cola', icon: 'schedule', color: 'bg-surface-container-low' },
    { id: 'en_proceso', name: 'En Proceso', icon: 'play_circle', color: 'bg-primary/5' },
    { id: 'finalizada', name: 'Finalizada', icon: 'check_circle', color: 'bg-secondary/5' },
    { id: 'tercerizada', name: 'Tercerizada', icon: 'moving', color: 'bg-tertiary/5' }
  ];

  async function fetchOrdenes() {
    loading = true;
    try {
      const data = await api.get('/ordenes-produccion');
      ordenes = data;
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  async function cambiarEstado(ordenId, nuevoEstado) {
    try {
      await api.patch(`/ordenes-produccion/${ordenId}/status?nuevo_estado=${nuevoEstado}`, {});
      await fetchOrdenes();
    } catch (e) {
      alert('Error al actualizar estado: ' + e.message);
    }
  }

  onMount(fetchOrdenes);

  $: getItemsByColumn = (columnId) => {
    if (columnId === 'tercerizada') {
      return ordenes.filter(o => o.tipo_produccion === 'tercerizada' && o.estado !== 'finalizada');
    }
    return ordenes.filter(o => o.estado === columnId && o.tipo_produccion !== 'tercerizada');
  };

  const formatCurrency = (value) => {
    if (value === null || value === undefined) return 'N/A';
    return new Intl.NumberFormat('es-PE', { style: 'currency', currency: 'PEN' }).format(value);
  };
</script>

<div class="space-y-8 h-full flex flex-col">
  <!-- Header -->
  <div class="flex flex-col sm:flex-row sm:justify-between sm:items-end gap-4">
    <div>
      <h1 class="font-manrope text-3xl font-extrabold text-primary tracking-tight">Tablero de Producción</h1>
      <p class="text-outline font-medium mt-1">Monitorea el flujo de trabajo en tiempo real.</p>
    </div>
    <button 
      on:click={fetchOrdenes}
      class="px-5 py-2.5 bg-surface-container-lowest border border-outline-variant/30 text-primary font-bold text-sm rounded-xl flex items-center gap-2 hover:bg-surface-container-low transition-colors"
    >
      <span class="material-symbols-outlined text-lg">refresh</span>
      Actualizar Tablero
    </button>
  </div>

  {#if loading}
    <div class="flex-1 flex items-center justify-center">
      <div class="flex flex-col items-center gap-4">
        <div class="w-12 h-12 border-4 border-primary/10 border-t-primary rounded-full animate-spin"></div>
        <p class="text-outline font-bold tracking-[0.2em] text-xs uppercase">Cargando tablero...</p>
      </div>
    </div>
  {:else if error}
    <div class="flex-1 flex items-center justify-center">
      <div class="bg-error-container/30 p-6 rounded-xl border border-error/20 flex items-center gap-3">
        <span class="material-symbols-outlined text-error">error</span>
        <p class="text-error font-bold">Error: {error}</p>
      </div>
    </div>
  {:else}
    <div class="flex-1 overflow-x-auto pb-6 custom-scrollbar snap-x snap-mandatory md:snap-none">
      <div class="flex gap-6 min-w-max h-full px-1">
        {#each columns as column}
          {@const items = getItemsByColumn(column.id)}
          <div class="w-72 sm:w-80 flex flex-col gap-4 snap-center">
            <!-- Column Header -->
            <div class="flex items-center justify-between px-2">
              <h3 class="font-manrope font-bold text-on-surface flex items-center gap-2">
                <span class="material-symbols-outlined text-lg text-primary">{column.icon}</span>
                {column.name}
                <span class="text-[10px] bg-surface-container-high px-2 py-1 rounded-full text-outline font-bold">
                  {items.length}
                </span>
              </h3>
              <button class="text-outline hover:text-primary transition-colors">
                <span class="material-symbols-outlined text-xl">more_horiz</span>
              </button>
            </div>
            
            <!-- Column Body -->
            <div class="flex-1 flex flex-col gap-3 p-4 rounded-2xl {column.color} min-h-[400px] sm:min-h-[500px] border border-outline-variant/10">
              {#each items as item}
                <div class="bg-surface-container-lowest p-5 rounded-2xl shadow-sm border border-outline-variant/10 hover:shadow-lg transition-all group relative overflow-hidden">
                  {#if item.tipo_produccion === 'tercerizada'}
                    <div class="absolute top-0 right-0 p-1 bg-tertiary text-[8px] font-bold text-white rounded-bl-lg px-2 uppercase tracking-wider">Ext.</div>
                  {/if}
                  
                  <div class="flex justify-between items-start mb-3">
                    <span class="text-[10px] font-bold uppercase tracking-widest text-outline">OP-{item.id}</span>
                    <span class="material-symbols-outlined text-outline text-base">schedule</span>
                  </div>
                  
                  <h4 class="font-bold text-on-surface leading-tight mb-2 group-hover:text-primary transition-colors text-sm">
                    COT-{item.cotizacion_id}
                  </h4>
                  
                  <p class="text-xs font-medium text-outline mb-4">
                    {item.proveedor ? item.proveedor.razon_social : 'Producción Interna'}
                  </p>

                  <div class="pt-3 border-t border-outline-variant/10 flex flex-col gap-3">
                    {#if item.tipo_produccion === 'tercerizada'}
                      <div class="text-[10px] font-bold text-tertiary">Costo: {formatCurrency(item.costo_tercerizado)}</div>
                    {/if}
                    
                    <div class="flex justify-between items-center">
                       {#if item.estado === 'en_cola'}
                         <button 
                           on:click={() => cambiarEstado(item.id, 'en_proceso')}
                           class="flex items-center gap-2 px-3 py-1.5 bg-primary/10 text-primary rounded-xl text-[10px] font-bold hover:bg-primary hover:text-white transition-all"
                         >
                           <span class="material-symbols-outlined text-sm">play_arrow</span> INICIAR
                         </button>
                       {:else if item.estado === 'en_proceso'}
                         <button 
                           on:click={() => cambiarEstado(item.id, 'finalizada')}
                           class="flex items-center gap-2 px-3 py-1.5 bg-secondary/10 text-secondary rounded-xl text-[10px] font-bold hover:bg-secondary hover:text-white transition-all"
                         >
                           <span class="material-symbols-outlined text-sm">check_circle</span> FINALIZAR
                         </button>
                       {/if}
                       
                       <a 
                         href="/cotizaciones" 
                         class="p-2 rounded-lg bg-surface-container-low text-outline hover:text-primary transition-colors"
                         title="Ver detalles"
                       >
                         <span class="material-symbols-outlined text-base">open_in_new</span>
                       </a>
                    </div>
                  </div>
                </div>
              {/each}
              
              {#if items.length === 0}
                <div class="flex-1 flex items-center justify-center border-2 border-dashed border-outline-variant/10 rounded-2xl">
                  <p class="text-[10px] font-bold text-outline uppercase tracking-widest opacity-40">Vacío</p>
                </div>
              {/if}
            </div>
          </div>
        {/each}
      </div>
    </div>
  {/if}
</div>

<style>
  .custom-scrollbar::-webkit-scrollbar {
    height: 8px;
  }
  .custom-scrollbar::-webkit-scrollbar-track {
    background: transparent;
  }
  .custom-scrollbar::-webkit-scrollbar-thumb {
    background: rgba(195, 198, 209, 0.2);
    border-radius: 9999px;
  }
  .custom-scrollbar::-webkit-scrollbar-thumb:hover {
    background: rgba(195, 198, 209, 0.4);
  }
</style>
