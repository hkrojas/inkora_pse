<script>
  import { api } from '$lib/utils/api';
  import {
    ChevronRight,
    CircleAlert,
    CircleCheckBig,
    Layers3,
    Package,
    Search,
    Truck
  } from 'lucide-svelte';
  import { onMount } from 'svelte';

  let ordenes = [];
  let cotizaciones = [];
  let loading = true;
  let error = '';
  let searchTerm = '';
  let updatingOrderId = null;

  const columns = [
    {
      id: 'preprensa',
      title: 'Pre-prensa',
      subtitle: 'Validacion y cola',
      icon: Layers3
    },
    {
      id: 'impresion',
      title: 'Impresion',
      subtitle: 'Maquina o proveedor',
      icon: Package
    },
    {
      id: 'acabado',
      title: 'Acabado',
      subtitle: 'Cierre y entrega',
      icon: CircleCheckBig
    }
  ];

  onMount(loadBoard);

  async function loadBoard() {
    loading = true;
    error = '';

    try {
      const [ordenesData, cotizacionesData] = await Promise.all([
        api.get('/ordenes-produccion'),
        api.get('/cotizaciones/?limit=100')
      ]);

      ordenes = Array.isArray(ordenesData) ? ordenesData : [];
      cotizaciones = Array.isArray(cotizacionesData) ? cotizacionesData : [];
    } catch (loadError) {
      console.error('Error cargando tablero de produccion:', loadError);
      error = loadError?.message || 'No se pudo cargar el tablero operativo.';
    } finally {
      loading = false;
    }
  }

  async function advanceOrder(order) {
    const nextStatus = order?.estado === 'en_cola' ? 'en_proceso' : order?.estado === 'en_proceso' ? 'finalizada' : null;
    if (!nextStatus) return;

    updatingOrderId = order.id;
    error = '';

    try {
      await api.patch(`/ordenes-produccion/${order.id}/status?nuevo_estado=${nextStatus}`, {});
      await loadBoard();
    } catch (updateError) {
      console.error('Error actualizando orden:', updateError);
      error = updateError?.message || 'No se pudo actualizar el estado de la orden.';
    } finally {
      updatingOrderId = null;
    }
  }

  function formatCurrency(value) {
    if (value === null || value === undefined) return 'Sin costo';

    return new Intl.NumberFormat('es-PE', {
      style: 'currency',
      currency: 'PEN',
      maximumFractionDigits: 0
    }).format(Number(value || 0));
  }

  function formatDate(dateStr) {
    if (!dateStr) return 'Sin fecha';

    const date = new Date(dateStr);
    if (Number.isNaN(date.getTime())) return 'Sin fecha';

    return date.toLocaleDateString('es-PE', {
      day: '2-digit',
      month: 'short'
    });
  }

  function formatRelativeDate(dateStr) {
    if (!dateStr) return 'Hoy';

    const target = new Date(dateStr);
    if (Number.isNaN(target.getTime())) return 'Hoy';

    const diffDays = Math.max(Math.round((Date.now() - target.getTime()) / 86400000), 0);

    if (diffDays === 0) return 'Hoy';
    if (diffDays === 1) return 'Hace 1 dia';
    return `Hace ${diffDays} dias`;
  }

  function getStage(order) {
    if (order?.estado === 'finalizada') return 'acabado';
    if (order?.estado === 'en_proceso') return 'impresion';
    return 'preprensa';
  }

  function getProgress(order) {
    if (order?.estado === 'finalizada') return 100;
    if (order?.estado === 'en_proceso') return order?.tipo_produccion === 'tercerizada' ? 72 : 66;
    return 28;
  }

  function getUrgency(order) {
    const startedAt = order?.fecha_inicio ? new Date(order.fecha_inicio) : null;
    const ageDays = startedAt && !Number.isNaN(startedAt.getTime()) ? Math.max(Math.floor((Date.now() - startedAt.getTime()) / 86400000), 0) : 0;

    if (order?.estado !== 'finalizada' && ageDays >= 5) {
      return {
        accent: 'border-t-red-400',
        badge: 'border-red-200 bg-red-50 text-red-700',
        bar: 'bg-red-400',
        label: 'Retrasada'
      };
    }

    if (order?.tipo_produccion === 'tercerizada' && order?.estado !== 'finalizada') {
      return {
        accent: 'border-t-amber-400',
        badge: 'border-amber-200 bg-amber-50 text-amber-700',
        bar: 'bg-amber-400',
        label: 'Externa'
      };
    }

    return {
      accent: 'border-t-emerald-400',
      badge: 'border-emerald-200 bg-emerald-50 text-emerald-700',
      bar: 'bg-emerald-400',
      label: 'En tiempo'
    };
  }

  function getStateLabel(order) {
    if (order?.estado === 'finalizada') return 'Lista para entrega';
    if (order?.estado === 'en_proceso') return order?.tipo_produccion === 'tercerizada' ? 'Produccion externa' : 'En impresion';
    return 'Esperando liberacion';
  }

  function getOrderActionLabel(order) {
    if (order?.estado === 'en_cola') return 'Mover a impresion';
    if (order?.estado === 'en_proceso') return 'Marcar acabado';
    return 'Completada';
  }

  $: cotizacionMap = new Map(cotizaciones.map((cotizacion) => [`${cotizacion.id}`, cotizacion]));

  function getQuote(order) {
    return cotizacionMap.get(`${order?.cotizacion_id}`) || null;
  }

  function getClientName(order) {
    return getQuote(order)?.cliente?.razon_social || 'Cliente no disponible';
  }

  function matchesSearch(order) {
    const term = searchTerm.trim().toLowerCase();
    if (!term) return true;

    const quote = getQuote(order);
    const haystack = [
      `OP-${order?.id || ''}`,
      `COT-${order?.cotizacion_id || ''}`,
      getClientName(order),
      quote?.cliente?.numero_documento,
      order?.proveedor?.razon_social,
      order?.tipo_produccion,
      getStateLabel(order)
    ]
      .filter(Boolean)
      .join(' ')
      .toLowerCase();

    return haystack.includes(term);
  }

  $: filteredOrders = ordenes.filter(matchesSearch);
  $: boardColumns = columns.map((column) => ({
    ...column,
    items: filteredOrders.filter((order) => getStage(order) === column.id)
  }));
</script>

<div class="space-y-6">
  <section class="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
    <div class="space-y-2">
      <p class="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Centro operativo</p>
      <div class="space-y-1">
        <h1 class="text-2xl font-bold tracking-tight text-slate-900">Produccion</h1>
        <p class="max-w-2xl text-sm leading-6 text-slate-500">
          Gestiona el flujo de ordenes y detecta rapido los cuellos de botella entre pre-prensa, impresion y acabado.
        </p>
      </div>
    </div>

    <div class="flex flex-col gap-3 sm:flex-row">
      <div class="relative">
        <Search class="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" strokeWidth={1.9} />
        <input
          type="text"
          bind:value={searchTerm}
          placeholder="Buscar por OP, cliente o proveedor..."
          class="h-12 w-full min-w-[280px] rounded-xl border border-slate-200 bg-white pl-11 pr-4 text-sm text-slate-700 outline-none transition-all duration-200 placeholder:text-slate-400 focus:border-emerald-500 focus:ring-4 focus:ring-emerald-500/10"
        />
      </div>

      <button
        on:click={loadBoard}
        class="inline-flex items-center justify-center rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm font-medium text-slate-700 shadow-sm transition-colors hover:bg-slate-50"
      >
        Actualizar
      </button>
    </div>
  </section>

  {#if error}
    <div class="rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
      {error}
    </div>
  {/if}

  {#if loading}
    <section class="grid gap-5 xl:grid-cols-3">
      {#each Array(3) as _}
        <div class="min-h-[520px] animate-pulse rounded-2xl border border-slate-200 bg-slate-100/50"></div>
      {/each}
    </section>
  {:else}
    <section class="grid gap-5 xl:grid-cols-3">
      {#each boardColumns as column}
        {@const Icon = column.icon}
        <article class="rounded-2xl border border-slate-200 bg-slate-100/50 p-4">
          <div class="mb-4 flex items-start justify-between gap-3">
            <div class="space-y-1">
              <div class="flex items-center gap-2">
                <div class="rounded-2xl bg-white p-2 text-slate-600 shadow-sm">
                  <Icon class="h-4 w-4" strokeWidth={1.9} />
                </div>
                <h2 class="text-base font-semibold tracking-tight text-slate-900">{column.title}</h2>
                <span class="inline-flex rounded-full bg-white px-2.5 py-1 text-xs font-semibold text-slate-500 shadow-sm">
                  {column.items.length}
                </span>
              </div>
              <p class="text-sm text-slate-500">{column.subtitle}</p>
            </div>
          </div>

          <div class="space-y-3">
            {#if column.items.length === 0}
              <div class="flex min-h-[220px] items-center justify-center rounded-2xl border border-dashed border-slate-200 bg-white/70 px-5 text-center">
                <div class="space-y-2">
                  <p class="text-sm font-semibold text-slate-900">Sin ordenes en esta etapa</p>
                  <p class="text-sm leading-6 text-slate-500">
                    Cuando una orden avance en el flujo, aparecera aqui automaticamente.
                  </p>
                </div>
              </div>
            {:else}
              {#each column.items as item}
                {@const urgency = getUrgency(item)}
                {@const quote = getQuote(item)}
                <div class={`rounded-2xl border border-slate-200 border-t-4 bg-white p-4 shadow-sm transition-transform duration-200 hover:-translate-y-0.5 ${urgency.accent}`}>
                  <div class="flex items-start justify-between gap-3">
                    <div class="space-y-1">
                      <p class="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">OP-{item.id}</p>
                      <h3 class="text-sm font-semibold text-slate-900">{getClientName(item)}</h3>
                      <p class="text-xs text-slate-500">
                        COT-{item.cotizacion_id} {quote?.serie ? `- ${quote.serie}-${String(quote.correlativo || 0).padStart(6, '0')}` : ''}
                      </p>
                    </div>

                    <span class={`inline-flex rounded-full border px-2.5 py-1 text-[11px] font-semibold ${urgency.badge}`}>
                      {urgency.label}
                    </span>
                  </div>

                  <div class="mt-4 space-y-3">
                    <div class="rounded-2xl bg-slate-50 px-3 py-3">
                      <div class="flex items-center justify-between gap-3 text-xs text-slate-500">
                        <span>Estado actual</span>
                        <span>{formatRelativeDate(item.fecha_inicio)}</span>
                      </div>
                      <p class="mt-1 text-sm font-medium text-slate-900">{getStateLabel(item)}</p>
                    </div>

                    <div class="grid gap-3 sm:grid-cols-2">
                      <div class="rounded-2xl border border-slate-200 bg-slate-50 px-3 py-3">
                        <p class="text-xs uppercase tracking-[0.2em] text-slate-400">Produccion</p>
                        <div class="mt-2 flex items-center gap-2 text-sm font-medium text-slate-900">
                          {#if item.tipo_produccion === 'tercerizada'}
                            <Truck class="h-4 w-4 text-amber-500" strokeWidth={2} />
                          {:else}
                            <Package class="h-4 w-4 text-emerald-600" strokeWidth={2} />
                          {/if}
                          <span>{item.tipo_produccion === 'tercerizada' ? 'Proveedor externo' : 'Interna'}</span>
                        </div>
                      </div>

                      <div class="rounded-2xl border border-slate-200 bg-slate-50 px-3 py-3">
                        <p class="text-xs uppercase tracking-[0.2em] text-slate-400">Costo</p>
                        <p class="mt-2 text-sm font-medium text-slate-900">{formatCurrency(item.costo_tercerizado)}</p>
                      </div>
                    </div>

                    <div class="space-y-2">
                      <div class="flex items-center justify-between gap-3 text-xs text-slate-500">
                        <span>Avance estimado</span>
                        <span>{getProgress(item)}%</span>
                      </div>
                      <div class="h-1.5 overflow-hidden rounded-full bg-slate-100">
                        <div class={`h-full rounded-full ${urgency.bar}`} style={`width: ${getProgress(item)}%`}></div>
                      </div>
                    </div>

                    <div class="flex items-center justify-between gap-3 pt-1">
                      <div class="text-xs text-slate-400">
                        <p>{item.proveedor?.razon_social || 'Sin proveedor asignado'}</p>
                        <p>{formatDate(item.fecha_fin)}</p>
                      </div>

                      {#if item.estado !== 'finalizada'}
                        <button
                          on:click={() => advanceOrder(item)}
                          disabled={updatingOrderId === item.id}
                          class="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-3.5 py-2 text-xs font-semibold text-white shadow-sm transition-colors hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-70"
                        >
                          <span>{updatingOrderId === item.id ? 'Actualizando...' : getOrderActionLabel(item)}</span>
                          <ChevronRight class="h-3.5 w-3.5" strokeWidth={2.2} />
                        </button>
                      {:else}
                        <div class="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-3.5 py-2 text-xs font-semibold text-white">
                          <CircleCheckBig class="h-3.5 w-3.5" strokeWidth={2.2} />
                          <span>Lista</span>
                        </div>
                      {/if}
                    </div>
                  </div>
                </div>
              {/each}
            {/if}
          </div>
        </article>
      {/each}
    </section>

    {#if filteredOrders.length === 0}
      <div class="rounded-2xl border border-dashed border-slate-200 bg-white px-6 py-10 text-center shadow-sm">
        <div class="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl border border-slate-200 bg-slate-50 text-slate-400">
          <CircleAlert class="h-6 w-6" strokeWidth={1.9} />
        </div>
        <p class="mt-4 text-sm font-semibold text-slate-900">No hay coincidencias para esa busqueda</p>
        <p class="mt-2 text-sm leading-6 text-slate-500">
          Ajusta el termino de busqueda para volver a ver las ordenes activas del tablero.
        </p>
      </div>
    {/if}
  {/if}
</div>
