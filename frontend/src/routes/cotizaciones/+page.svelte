<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/utils/api';
  import CotizacionModal from '$lib/components/CotizacionModal.svelte';

  let loading = true;
  let cotizaciones = [];
  let showModal = false;

  const fetchCotizaciones = async () => {
    loading = true;
    try {
      cotizaciones = await api.get('/cotizaciones/');
    } catch (error) {
      console.error('Error cargando cotizaciones:', error);
    } finally {
      loading = false;
    }
  };

  onMount(fetchCotizaciones);

  const getStatusBadge = (status) => {
    switch (status.toLowerCase()) {
      case 'facturada': return { bg: 'bg-secondary-container/20 text-on-secondary-container', dot: 'bg-secondary', border: 'border-secondary' };
      case 'pendiente': return { bg: 'bg-tertiary-container/10 text-on-tertiary-container', dot: 'bg-tertiary', border: 'border-tertiary' };
      case 'anulada': return { bg: 'bg-error-container/20 text-error', dot: 'bg-error', border: 'border-error' };
      default: return { bg: 'bg-surface-container text-on-surface-variant', dot: 'bg-outline', border: 'border-outline' };
    }
  };

  function formatCurrency(amount) {
    return new Intl.NumberFormat('es-PE', { style: 'currency', currency: 'PEN' }).format(amount);
  }

  function formatDate(dateStr) {
    return new Date(dateStr).toLocaleDateString('es-PE', { 
      day: '2-digit', 
      month: 'short', 
      year: 'numeric' 
    });
  }
</script>

<div class="space-y-8">
  <!-- Header -->
  <div class="flex flex-col sm:flex-row sm:justify-between sm:items-end gap-4">
    <div>
      <h1 class="font-manrope text-3xl font-extrabold text-primary tracking-tight">Cotizaciones</h1>
      <p class="text-outline font-medium mt-1">Gestiona y emite documentos de venta multitenant.</p>
    </div>
    <button 
      on:click={() => showModal = true}
      class="btn-primary flex items-center justify-center gap-2 w-full sm:w-auto"
    >
      <span class="material-symbols-outlined text-lg">add_circle</span>
      Nueva Cotización
    </button>
  </div>

  <!-- Filters Bar -->
  <div class="bg-surface-container-low p-4 sm:p-5 rounded-2xl flex flex-col sm:flex-row flex-wrap gap-3 sm:gap-4 items-stretch sm:items-center justify-between border border-outline-variant/10">
    <div class="flex gap-3 items-center flex-1 min-w-0">
      <div class="relative w-full">
        <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline text-lg">search</span>
        <input type="text" placeholder="Buscar por cliente o número..." class="w-full h-11 pl-10 pr-6 rounded-full bg-surface-container-lowest border-none text-sm focus:ring-2 focus:ring-primary/20 transition-all placeholder:text-outline/60" />
      </div>
      <button class="p-3 rounded-xl bg-surface-container-lowest text-on-surface-variant hover:bg-surface-container-high transition-all flex items-center gap-2 border border-outline-variant/10 shrink-0">
        <span class="material-symbols-outlined text-lg">filter_list</span>
        <span class="text-sm font-semibold hidden sm:inline">Filtros</span>
      </button>
    </div>
    <div class="flex items-center gap-2">
      <span class="text-[10px] font-bold text-outline uppercase tracking-widest hidden sm:inline">Mostrar:</span>
      <select class="bg-surface-container-lowest border-none rounded-xl text-sm font-semibold px-4 h-11 focus:ring-2 focus:ring-primary/20 w-full sm:w-auto">
        <option>Últimos 30 días</option>
        <option>Este año</option>
      </select>
    </div>
  </div>

  <!-- Table -->
  <div class="bg-surface-container-lowest rounded-3xl overflow-hidden shadow-sm border border-outline-variant/10">
    <div class="overflow-x-auto">
    {#if loading}
      <div class="p-20 flex flex-col items-center justify-center gap-6">
        <div class="w-12 h-12 border-4 border-primary/10 border-t-primary rounded-full animate-spin"></div>
        <p class="text-outline font-bold tracking-[0.2em] text-xs uppercase animate-pulse">Cargando Historial...</p>
      </div>
    {:else}
      <table class="w-full text-left border-collapse">
        <thead>
          <tr class="bg-surface-container-low/50">
            <th class="px-8 py-4 text-[10px] font-bold text-outline uppercase tracking-wider">Número</th>
            <th class="px-8 py-4 text-[10px] font-bold text-outline uppercase tracking-wider">Cliente</th>
            <th class="px-8 py-4 text-[10px] font-bold text-outline uppercase tracking-wider">Fecha</th>
            <th class="px-8 py-4 text-[10px] font-bold text-outline uppercase tracking-wider">Total</th>
            <th class="px-8 py-4 text-[10px] font-bold text-outline uppercase tracking-wider text-center">Estado</th>
            <th class="px-8 py-4 text-[10px] font-bold text-outline uppercase tracking-wider text-right">Acciones</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-outline-variant/5">
          {#each cotizaciones as cot (cot.id)}
            {@const status = getStatusBadge(cot.estado)}
            <tr class="group hover:bg-surface-container-low/30 transition-colors">
              <td class="px-8 py-5 border-l-4 {status.border}">
                <span class="text-sm font-bold text-on-surface">{cot.serie}-{String(cot.correlativo).padStart(6, '0')}</span>
              </td>
              <td class="px-8 py-5">
                <p class="text-sm font-semibold text-on-surface">{cot.cliente?.razon_social || 'Cliente sin nombre'}</p>
                <p class="text-[10px] text-outline">{cot.cliente?.numero_documento || 'S/D'}</p>
              </td>
              <td class="px-8 py-5">
                <span class="text-xs font-medium text-outline">{formatDate(cot.fecha_emision)}</span>
              </td>
              <td class="px-8 py-5">
                <p class="text-sm font-bold text-on-surface">{formatCurrency(cot.total_venta)}</p>
              </td>
              <td class="px-8 py-5 text-center">
                <span class="inline-flex items-center gap-1.5 px-3 py-1 {status.bg} rounded-full text-[10px] font-bold">
                  <span class="w-1.5 h-1.5 rounded-full {status.dot}"></span>
                  {cot.estado}
                </span>
              </td>
              <td class="px-8 py-5 text-right">
                <div class="flex justify-end gap-1.5 md:opacity-0 md:group-hover:opacity-100 transition-opacity">
                  <button class="p-2 text-outline hover:text-primary rounded-lg transition-colors" title="Descargar PDF">
                    <span class="material-symbols-outlined text-lg">download</span>
                  </button>
                  <button class="p-2 text-outline hover:text-primary rounded-lg transition-colors hidden sm:block" title="Compartir">
                    <span class="material-symbols-outlined text-lg">share</span>
                  </button>
                  <button class="p-2 text-outline hover:text-primary rounded-lg transition-colors">
                    <span class="material-symbols-outlined text-lg">more_vert</span>
                  </button>
                </div>
              </td>
            </tr>
          {/each}
          {#if cotizaciones.length === 0}
            <tr>
              <td colspan="6" class="p-20 text-center">
                <div class="flex flex-col items-center gap-5 text-on-surface-variant">
                  <div class="p-6 rounded-full bg-primary/5">
                    <span class="material-symbols-outlined text-5xl text-primary/30">description</span>
                  </div>
                  <div class="space-y-1">
                    <p class="font-bold text-on-surface text-lg">Sin cotizaciones aún</p>
                    <p class="text-sm font-medium">Crea tu primera cotización para empezar a facturar.</p>
                  </div>
                  <button 
                    on:click={() => showModal = true}
                    class="mt-2 px-6 py-3 rounded-xl bg-primary text-white font-bold text-sm hover:shadow-lg hover:shadow-primary/20 transition-all flex items-center gap-2 active:scale-95"
                  >
                    <span class="material-symbols-outlined text-sm">add_circle</span>
                    Crear Primera Cotización
                  </button>
                </div>
              </td>
            </tr>
          {/if}
        </tbody>
      </table>
    {/if}
    </div>
  </div>
</div>

<CotizacionModal bind:show={showModal} on:success={fetchCotizaciones} />
