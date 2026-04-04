<script>
  import CotizacionDetailModal from '$lib/components/CotizacionDetailModal.svelte';
  import CotizacionSlideOver from '$lib/components/CotizacionSlideOver.svelte';
  import { api } from '$lib/utils/api';
  import {
    glassPanelClass,
    glassPanelStrongClass,
    mutedGlassPanelClass,
    pageEyebrowClass,
    pageSubtitleClass,
    pageTitleClass,
    premiumPrimaryButtonClass,
    premiumRowHoverClass
  } from '$lib/utils/uiClasses';
  import { CalendarDays, ChevronRight, CircleAlert, CircleCheckBig, FileText, Plus } from 'lucide-svelte';
  import { onMount } from 'svelte';

  let isLoading = true;
  let cotizaciones = [];
  let showModal = false;
  let showDetailModal = false;
  let selectedCotizacionId = null;
  let activeFilter = 'todas';
  const skeletonRows = Array.from({ length: 6 }, (_, index) => index);

  const quickFilters = [
    { id: 'todas', label: 'Todas' },
    { id: 'pendientes', label: 'Pendientes' },
    { id: 'aprobadas', label: 'Aprobadas' }
  ];

  const fetchCotizaciones = async () => {
    isLoading = true;

    try {
      cotizaciones = await api.get('/cotizaciones/');
    } catch (error) {
      console.error('Error cargando cotizaciones:', error);
    } finally {
      isLoading = false;
    }
  };

  onMount(fetchCotizaciones);

  function normalizeStatus(status) {
    const normalized = `${status || ''}`.trim().toLowerCase();

    if (['aprobada', 'aprobado', 'facturada', 'emitida', 'cerrada'].includes(normalized)) {
      return 'approved';
    }

    if (['cancelada', 'cancelado', 'rechazada', 'rechazado', 'anulada', 'anulado'].includes(normalized)) {
      return 'cancelled';
    }

    return 'pending';
  }

  function getStatusBadge(status) {
    const variant = normalizeStatus(status);

    if (variant === 'approved') {
      return 'bg-emerald-50 text-emerald-700 border border-emerald-200';
    }

    if (variant === 'cancelled') {
      return 'bg-red-50 text-red-700 border border-red-200';
    }

    return 'bg-amber-50 text-amber-700 border border-amber-200';
  }

  function matchesFilter(cotizacion, filterId) {
    const variant = normalizeStatus(cotizacion?.estado);

    if (filterId === 'aprobadas') return variant === 'approved';
    if (filterId === 'pendientes') return variant === 'pending';
    return true;
  }

  function getFilterCount(filterId) {
    return cotizaciones.filter((cotizacion) => matchesFilter(cotizacion, filterId)).length;
  }

  function formatCurrency(amount) {
    return new Intl.NumberFormat('es-PE', {
      style: 'currency',
      currency: 'PEN'
    }).format(Number(amount || 0));
  }

  function formatDate(dateStr) {
    if (!dateStr) return 'Sin fecha';

    return new Date(dateStr).toLocaleDateString('es-PE', {
      day: '2-digit',
      month: 'short',
      year: 'numeric'
    });
  }

  function openDetail(cotizacion) {
    selectedCotizacionId = cotizacion.id;
    showDetailModal = true;
  }

  $: filteredCotizaciones = cotizaciones.filter((cotizacion) => matchesFilter(cotizacion, activeFilter));
</script>

<div class="space-y-6">
  <section class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
    <div class="space-y-2">
      <p class={pageEyebrowClass}>Centro comercial</p>
      <div class="space-y-1">
        <h1 class={pageTitleClass}>Cotizaciones</h1>
        <p class={`max-w-2xl ${pageSubtitleClass}`}>
          Supervisa el pipeline de documentos y revisa rápidamente el estado de cada propuesta comercial.
        </p>
      </div>
    </div>

    <button
      on:click={() => showModal = true}
      class={`inline-flex items-center justify-center gap-2 rounded-xl px-5 py-3 text-sm font-semibold ${premiumPrimaryButtonClass}`}
    >
      <Plus class="h-4 w-4" strokeWidth={2.2} />
      <span>Nueva Cotización</span>
    </button>
  </section>

  <section class="flex flex-wrap gap-2">
    {#each quickFilters as filter}
      <button
        on:click={() => activeFilter = filter.id}
        class="inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-medium transition-all duration-300
          {activeFilter === filter.id
            ? 'border-slate-900/10 bg-gradient-to-b from-zinc-800 to-zinc-950 text-white shadow-[inset_0px_1px_0px_rgba(255,255,255,0.1),0px_1px_2px_rgba(0,0,0,0.4)]'
            : 'border-white/70 bg-white/70 text-slate-600 shadow-[0_8px_24px_rgba(15,23,42,0.04)] hover:bg-white/90 hover:text-slate-900'}"
      >
        <span>{filter.label}</span>
        <span
          class="rounded-full px-2 py-0.5 text-[11px] font-semibold
            {activeFilter === filter.id ? 'bg-white/10 text-white' : 'bg-slate-100 text-slate-500'}"
        >
          {getFilterCount(filter.id)}
        </span>
      </button>
    {/each}
  </section>

  <section class={`overflow-hidden rounded-[30px] ${glassPanelStrongClass}`}>
    {#if isLoading}
      <div class="overflow-x-auto" aria-hidden="true">
        <table class="min-w-full border-separate border-spacing-0">
          <thead>
            <tr class="bg-slate-50/50">
              <th class="px-6 pb-3 pt-5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Documento</th>
              <th class="px-6 pb-3 pt-5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Cliente</th>
              <th class="px-6 pb-3 pt-5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Fecha</th>
              <th class="px-6 pb-3 pt-5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Total</th>
              <th class="px-6 pb-3 pt-5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Estado</th>
              <th class="px-6 pb-3 pt-5 text-right text-xs font-semibold uppercase tracking-wider text-slate-500">Detalle</th>
            </tr>
          </thead>

          <tbody>
            {#each skeletonRows as _, index}
              <tr class="animate-pulse">
                <td class="px-6 py-4 {index === skeletonRows.length - 1 ? 'border-b-0' : 'border-b border-slate-200/70'}">
                  <div class="space-y-2">
                    <div class="h-4 w-28 rounded-full bg-slate-200"></div>
                    <div class="h-3 w-20 rounded-full bg-slate-100"></div>
                  </div>
                </td>

                <td class="px-6 py-4 {index === skeletonRows.length - 1 ? 'border-b-0' : 'border-b border-slate-200/70'}">
                  <div class="space-y-2">
                    <div class="h-4 w-40 rounded-full bg-slate-200"></div>
                    <div class="h-3 w-24 rounded-full bg-slate-100"></div>
                  </div>
                </td>

                <td class="px-6 py-4 {index === skeletonRows.length - 1 ? 'border-b-0' : 'border-b border-slate-200/70'}">
                  <div class="h-4 w-24 rounded-full bg-slate-200"></div>
                </td>

                <td class="px-6 py-4 {index === skeletonRows.length - 1 ? 'border-b-0' : 'border-b border-slate-200/70'}">
                  <div class="h-4 w-20 rounded-full bg-slate-200"></div>
                </td>

                <td class="px-6 py-4 {index === skeletonRows.length - 1 ? 'border-b-0' : 'border-b border-slate-200/70'}">
                  <div class="h-7 w-24 rounded-full bg-slate-100"></div>
                </td>

                <td class="px-6 py-4 text-right {index === skeletonRows.length - 1 ? 'border-b-0' : 'border-b border-slate-200/70'}">
                  <div class="ml-auto h-4 w-14 rounded-full bg-slate-200"></div>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {:else if filteredCotizaciones.length === 0}
      <div class="flex min-h-[320px] flex-col items-center justify-center gap-5 px-6 py-12 text-center">
        <div class={`flex h-16 w-16 items-center justify-center rounded-2xl ${mutedGlassPanelClass}`}>
          {#if activeFilter === 'aprobadas'}
            <CircleCheckBig class="h-8 w-8 text-emerald-600" strokeWidth={1.9} />
          {:else if activeFilter === 'pendientes'}
            <CircleAlert class="h-8 w-8 text-amber-500" strokeWidth={1.9} />
          {:else}
            <FileText class="h-8 w-8 text-slate-400" strokeWidth={1.9} />
          {/if}
        </div>

        <div class="space-y-2">
          <h2 class="text-lg font-semibold tracking-tight text-slate-900">
            {activeFilter === 'todas' ? 'No hay cotizaciones todavía' : `No hay registros en ${quickFilters.find((filter) => filter.id === activeFilter)?.label?.toLowerCase()}`}
          </h2>
          <p class="max-w-md text-sm leading-6 text-slate-500">
            {activeFilter === 'todas'
              ? 'Crea la primera cotización para empezar a poblar el historial comercial.'
              : 'Prueba cambiando de filtro o registra una nueva cotización para alimentar esta vista.'}
          </p>
        </div>

        <button
          on:click={() => showModal = true}
          class={`inline-flex items-center justify-center gap-2 rounded-xl px-5 py-3 text-sm font-semibold ${premiumPrimaryButtonClass}`}
        >
          <Plus class="h-4 w-4" strokeWidth={2.2} />
          <span>Crear Cotización</span>
        </button>
      </div>
    {:else}
      <div class="overflow-x-auto">
        <table class="min-w-full border-separate border-spacing-0">
          <thead>
            <tr class="bg-slate-50/50">
              <th class="px-6 pb-3 pt-5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Documento</th>
              <th class="px-6 pb-3 pt-5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Cliente</th>
              <th class="px-6 pb-3 pt-5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Fecha</th>
              <th class="px-6 pb-3 pt-5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Total</th>
              <th class="px-6 pb-3 pt-5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Estado</th>
              <th class="px-6 pb-3 pt-5 text-right text-xs font-semibold uppercase tracking-wider text-slate-500">Detalle</th>
            </tr>
          </thead>

          <tbody>
            {#each filteredCotizaciones as cotizacion, index (cotizacion.id)}
              <tr class={premiumRowHoverClass}>
                <td class="border-b border-slate-200/70 px-6 py-4 {index === filteredCotizaciones.length - 1 ? 'border-b-0' : ''}">
                  <div class="space-y-1">
                    <p class="text-sm font-semibold tracking-tight text-slate-900">
                      {cotizacion.serie}-{String(cotizacion.correlativo).padStart(6, '0')}
                    </p>
                    <p class="text-xs text-slate-500">Cotización comercial</p>
                  </div>
                </td>

                <td class="border-b border-slate-200/70 px-6 py-4 {index === filteredCotizaciones.length - 1 ? 'border-b-0' : ''}">
                  <div class="space-y-1">
                    <p class="text-sm font-medium text-slate-900">{cotizacion.cliente?.razon_social || 'Cliente sin nombre'}</p>
                    <p class="text-xs text-slate-500">{cotizacion.cliente?.numero_documento || 'Sin documento'}</p>
                  </div>
                </td>

                <td class="border-b border-slate-200/70 px-6 py-4 {index === filteredCotizaciones.length - 1 ? 'border-b-0' : ''}">
                  <div class="inline-flex items-center gap-2 text-sm text-slate-600">
                    <CalendarDays class="h-4 w-4 text-slate-400" strokeWidth={1.9} />
                    <span>{formatDate(cotizacion.fecha_emision)}</span>
                  </div>
                </td>

                <td class="border-b border-slate-200/70 px-6 py-4 {index === filteredCotizaciones.length - 1 ? 'border-b-0' : ''}">
                  <p class="text-sm font-semibold text-slate-900">{formatCurrency(cotizacion.total_venta)}</p>
                </td>

                <td class="border-b border-slate-200/70 px-6 py-4 {index === filteredCotizaciones.length - 1 ? 'border-b-0' : ''}">
                  <span class="inline-flex rounded-full px-3 py-1 text-xs font-semibold {getStatusBadge(cotizacion.estado)}">
                    {cotizacion.estado}
                  </span>
                </td>

                <td class="border-b border-slate-200/70 px-6 py-4 text-right {index === filteredCotizaciones.length - 1 ? 'border-b-0' : ''}">
                  <button
                    class="inline-flex items-center gap-2 text-sm font-medium text-slate-500 transition-colors hover:text-slate-900"
                    aria-label="Ver detalle de cotización"
                    type="button"
                    on:click={() => openDetail(cotizacion)}
                  >
                    <span>Ver</span>
                    <ChevronRight class="h-4 w-4" strokeWidth={2} />
                  </button>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </section>
</div>

<CotizacionSlideOver bind:show={showModal} on:success={fetchCotizaciones} />
<CotizacionDetailModal
  bind:show={showDetailModal}
  cotizacionId={selectedCotizacionId}
  on:updated={fetchCotizaciones}
/>
