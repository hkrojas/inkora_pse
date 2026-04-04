<script>
  import CotizacionSlideOver from '$lib/components/CotizacionSlideOver.svelte';
  import { api } from '$lib/utils/api';
  import { CalendarDays, ChevronRight, CircleAlert, CircleCheckBig, FileText, Plus } from 'lucide-svelte';
  import { onMount } from 'svelte';

  let loading = true;
  let cotizaciones = [];
  let showModal = false;
  let activeFilter = 'todas';

  const quickFilters = [
    { id: 'todas', label: 'Todas' },
    { id: 'pendientes', label: 'Pendientes' },
    { id: 'aprobadas', label: 'Aprobadas' }
  ];

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

  $: filteredCotizaciones = cotizaciones.filter((cotizacion) => matchesFilter(cotizacion, activeFilter));
</script>

<div class="space-y-6">
  <section class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
    <div class="space-y-2">
      <p class="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Centro comercial</p>
      <div class="space-y-1">
        <h1 class="text-2xl font-bold tracking-tight text-slate-900">Cotizaciones</h1>
        <p class="max-w-2xl text-sm leading-6 text-slate-500">
          Supervisa el pipeline de documentos y revisa rápidamente el estado de cada propuesta comercial.
        </p>
      </div>
    </div>

    <button
      on:click={() => showModal = true}
      class="inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-600 px-5 py-3 text-sm font-semibold text-white shadow-sm shadow-emerald-900/10 ring-1 ring-inset ring-emerald-500/70 transition-all duration-200 hover:bg-emerald-500"
    >
      <Plus class="h-4 w-4" strokeWidth={2.2} />
      <span>Nueva Cotización</span>
    </button>
  </section>

  <section class="flex flex-wrap gap-2">
    {#each quickFilters as filter}
      <button
        on:click={() => activeFilter = filter.id}
        class="inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-medium transition-all duration-200
          {activeFilter === filter.id
            ? 'border-emerald-200 bg-emerald-50 text-emerald-700 shadow-sm'
            : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-100 hover:text-slate-900'}"
      >
        <span>{filter.label}</span>
        <span
          class="rounded-full px-2 py-0.5 text-[11px] font-semibold
            {activeFilter === filter.id ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500'}"
        >
          {getFilterCount(filter.id)}
        </span>
      </button>
    {/each}
  </section>

  <section class="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
    {#if loading}
      <div class="flex min-h-[320px] flex-col items-center justify-center gap-5 px-6 py-12 text-center">
        <div class="flex h-14 w-14 items-center justify-center rounded-2xl border border-emerald-100 bg-emerald-50">
          <div class="h-8 w-8 animate-spin rounded-full border-[3px] border-slate-200 border-t-emerald-500"></div>
        </div>
        <div class="space-y-2">
          <p class="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">Cargando datos</p>
          <p class="text-sm text-slate-500">Preparando la vista de cotizaciones...</p>
        </div>
      </div>
    {:else if filteredCotizaciones.length === 0}
      <div class="flex min-h-[320px] flex-col items-center justify-center gap-5 px-6 py-12 text-center">
        <div class="flex h-16 w-16 items-center justify-center rounded-2xl border border-slate-200 bg-slate-50">
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
          class="inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-600 px-5 py-3 text-sm font-semibold text-white shadow-sm shadow-emerald-900/10 ring-1 ring-inset ring-emerald-500/70 transition-all duration-200 hover:bg-emerald-500"
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
              <tr
                class="cursor-pointer transition-colors hover:bg-slate-50"
              >
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
