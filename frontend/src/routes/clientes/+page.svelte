<script>
  import { api } from '$lib/utils/api';
  import {
    glassPanelClass,
    glassPanelStrongClass,
    mutedGlassPanelClass,
    pageEyebrowClass,
    pageSubtitleClass,
    pageTitleClass,
    premiumInputClass,
    premiumRowHoverClass
  } from '$lib/utils/uiClasses';
  import { Building2, CalendarDays, Mail, MapPin, Phone, Search, ShieldCheck } from 'lucide-svelte';
  import { onMount } from 'svelte';

  let isLoading = true;
  let error = '';
  let search = '';
  let clientes = [];
  let cotizaciones = [];
  let selectedClientId = null;

  function normalizeText(value) {
    return `${value || ''}`
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .trim();
  }

  function formatCurrency(amount) {
    return new Intl.NumberFormat('es-PE', {
      style: 'currency',
      currency: 'PEN'
    }).format(Number(amount || 0));
  }

  function formatDate(value) {
    if (!value) return 'Sin fecha';
    return new Date(value).toLocaleDateString('es-PE', {
      day: '2-digit',
      month: 'short',
      year: 'numeric'
    });
  }

  function getDocumentLabel(tipo) {
    if (`${tipo}` === '6') return 'RUC';
    if (`${tipo}` === '1') return 'DNI';
    return 'Documento';
  }

  async function loadClientesView() {
    isLoading = true;
    error = '';

    try {
      const [clientesResponse, cotizacionesResponse] = await Promise.all([
        api.get('/clientes/'),
        api.get('/cotizaciones/')
      ]);

      clientes = clientesResponse;
      cotizaciones = cotizacionesResponse;
      selectedClientId = clientesResponse[0]?.id ?? null;
    } catch (loadError) {
      error = loadError?.message || 'No se pudo cargar el directorio de clientes.';
    } finally {
      isLoading = false;
    }
  }

  onMount(loadClientesView);

  $: filteredClientes = clientes.filter((cliente) => {
    const term = normalizeText(search);
    if (!term) return true;

    return [cliente.razon_social, cliente.nombre_comercial, cliente.numero_documento, cliente.email, cliente.telefono]
      .filter(Boolean)
      .map(normalizeText)
      .some((value) => value.includes(term));
  });

  $: if (filteredClientes.length > 0 && !filteredClientes.some((cliente) => cliente.id === selectedClientId)) {
    selectedClientId = filteredClientes[0].id;
  }

  $: selectedClient = filteredClientes.find((cliente) => cliente.id === selectedClientId)
    || clientes.find((cliente) => cliente.id === selectedClientId)
    || null;

  $: clientHistory = selectedClient
    ? cotizaciones
      .filter((cotizacion) => cotizacion.cliente?.id === selectedClient.id)
      .sort((a, b) => new Date(b.fecha_emision).getTime() - new Date(a.fecha_emision).getTime())
    : [];

  $: totalPipeline = clientHistory.reduce((sum, cotizacion) => sum + Number(cotizacion.total_venta || 0), 0);
  $: approvedCount = clientHistory.filter((cotizacion) => ['aprobada', 'aprobado', 'facturada', 'emitida'].includes(`${cotizacion.estado || ''}`.toLowerCase())).length;
  $: lastQuote = clientHistory[0] || null;
</script>

<div class="space-y-6">
  <section class="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
    <div class="space-y-2">
      <p class={pageEyebrowClass}>CRM operativo</p>
      <div class="space-y-1">
        <h1 class={pageTitleClass}>Clientes</h1>
        <p class={`max-w-3xl ${pageSubtitleClass}`}>
          Centraliza la ficha fiscal, el contacto operativo y el historial comercial de cada cuenta en una sola vista.
        </p>
      </div>
    </div>
  </section>

  {#if isLoading}
    <section class="grid gap-6 xl:grid-cols-[22rem_minmax(0,1fr)]">
      <div class={`rounded-[30px] p-5 ${glassPanelClass}`}>
        <div class="h-11 w-full animate-pulse rounded-2xl bg-slate-100"></div>
        <div class="mt-4 space-y-3">
          {#each Array.from({ length: 6 }, (_, index) => index) as _, index}
            <div class="animate-pulse rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <div class="h-4 w-40 rounded-full bg-slate-200"></div>
              <div class="mt-3 h-3 w-24 rounded-full bg-slate-100"></div>
            </div>
          {/each}
        </div>
      </div>

      <div class={`rounded-[30px] p-6 ${glassPanelClass}`}>
        <div class="space-y-4">
          <div class="h-6 w-48 animate-pulse rounded-full bg-slate-200"></div>
          <div class="grid gap-4 md:grid-cols-2">
            {#each Array.from({ length: 4 }, (_, index) => index) as _, index}
              <div class="animate-pulse rounded-2xl border border-slate-200 bg-slate-50 p-5">
                <div class="h-3 w-24 rounded-full bg-slate-100"></div>
                <div class="mt-3 h-4 w-36 rounded-full bg-slate-200"></div>
              </div>
            {/each}
          </div>
        </div>
      </div>
    </section>
  {:else if error}
    <section class={`flex min-h-[320px] flex-col items-center justify-center gap-4 rounded-[30px] px-6 py-10 text-center ${glassPanelStrongClass}`}>
      <div class="flex h-14 w-14 items-center justify-center rounded-2xl border border-red-200 bg-red-50 text-red-600">
        <ShieldCheck class="h-6 w-6" strokeWidth={1.9} />
      </div>
      <div class="space-y-2">
        <p class="text-lg font-semibold tracking-tight text-slate-900">No se pudo cargar el CRM</p>
        <p class="max-w-md text-sm leading-6 text-slate-500">{error}</p>
      </div>
    </section>
  {:else}
    <section class="grid gap-6 xl:grid-cols-[22rem_minmax(0,1fr)]">
      <aside class={`rounded-[30px] p-5 ${glassPanelStrongClass}`}>
        <div class="space-y-4">
          <div class="relative">
            <Search class="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" strokeWidth={1.9} />
            <input
              bind:value={search}
              type="text"
              placeholder="Buscar por razón social, RUC o correo..."
              class={`h-11 w-full rounded-2xl pl-11 pr-4 text-sm text-slate-700 ${premiumInputClass}`}
            />
          </div>

          <div class="space-y-2">
            {#if filteredClientes.length > 0}
              {#each filteredClientes as cliente}
                <button
                  type="button"
                  on:click={() => selectedClientId = cliente.id}
                  class={`w-full rounded-2xl border px-4 py-4 text-left transition-all duration-200 ${
                    selectedClient?.id === cliente.id
                      ? 'border-slate-900/10 bg-white/95 shadow-[0_12px_30px_rgba(15,23,42,0.06)]'
                      : 'border-white/70 bg-white/70'
                  } ${premiumRowHoverClass}`}
                >
                  <div class="space-y-2">
                    <div class="flex items-start justify-between gap-3">
                      <div class="min-w-0">
                        <p class="truncate text-sm font-semibold text-slate-900">{cliente.razon_social}</p>
                        <p class="mt-1 text-xs text-slate-500">{getDocumentLabel(cliente.tipo_documento)} {cliente.numero_documento}</p>
                      </div>

                      <span class="rounded-full bg-white px-2.5 py-1 text-[11px] font-semibold text-slate-600">
                        {cotizaciones.filter((cotizacion) => cotizacion.cliente?.id === cliente.id).length} cot.
                      </span>
                    </div>

                    <p class="truncate text-xs text-slate-500">{cliente.email || cliente.telefono || 'Sin contacto registrado'}</p>
                  </div>
                </button>
              {/each}
            {:else}
              <div class={`rounded-2xl px-4 py-8 text-center text-sm text-slate-500 ${mutedGlassPanelClass}`}>
                No hay clientes que coincidan con esa búsqueda.
              </div>
            {/if}
          </div>
        </div>
      </aside>

      <div class="space-y-6">
        {#if selectedClient}
          <section class={`rounded-[30px] p-6 ${glassPanelStrongClass}`}>
            <div class="flex flex-col gap-6 xl:flex-row xl:items-start xl:justify-between">
              <div class="space-y-4">
                <div class="space-y-2">
                  <p class="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Ficha del cliente</p>
                  <div class="space-y-1">
                    <h2 class="text-2xl font-bold tracking-tight text-slate-900">{selectedClient.razon_social}</h2>
                    <p class="text-sm text-slate-500">{selectedClient.nombre_comercial || 'Sin nombre comercial registrado'}</p>
                  </div>
                </div>

                <div class="flex flex-wrap gap-2">
                  <span class="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
                    {getDocumentLabel(selectedClient.tipo_documento)} {selectedClient.numero_documento}
                  </span>
                  <span class="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
                    {clientHistory.length} cotización{clientHistory.length === 1 ? '' : 'es'}
                  </span>
                </div>
              </div>

              <div class="grid gap-3 sm:grid-cols-3">
                <div class={`rounded-2xl px-4 py-3 ${mutedGlassPanelClass}`}>
                  <p class="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Pipeline</p>
                  <p class="mt-2 text-lg font-semibold text-slate-900">{formatCurrency(totalPipeline)}</p>
                </div>
                <div class={`rounded-2xl px-4 py-3 ${mutedGlassPanelClass}`}>
                  <p class="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Aprobadas</p>
                  <p class="mt-2 text-lg font-semibold text-slate-900">{approvedCount}</p>
                </div>
                <div class={`rounded-2xl px-4 py-3 ${mutedGlassPanelClass}`}>
                  <p class="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Última actividad</p>
                  <p class="mt-2 text-lg font-semibold text-slate-900">{lastQuote ? formatDate(lastQuote.fecha_emision) : 'Sin historial'}</p>
                </div>
              </div>
            </div>
          </section>

          <section class="grid gap-6 lg:grid-cols-[0.95fr_1.05fr]">
            <article class={`rounded-[30px] p-6 ${glassPanelClass}`}>
              <div class="mb-5 flex items-center gap-3">
                <div class="flex h-10 w-10 items-center justify-center rounded-2xl bg-slate-50 text-slate-600">
                  <Building2 class="h-5 w-5" strokeWidth={1.9} />
                </div>
                <div>
                  <p class="text-sm font-semibold text-slate-900">Información fiscal</p>
                  <p class="text-xs text-slate-500">Datos tributarios y administrativos del cliente.</p>
                </div>
              </div>

              <div class="grid gap-4 md:grid-cols-2">
                <div class={`rounded-2xl p-4 ${mutedGlassPanelClass}`}>
                  <p class="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Documento</p>
                  <p class="mt-2 text-sm font-medium text-slate-900">{getDocumentLabel(selectedClient.tipo_documento)} {selectedClient.numero_documento}</p>
                </div>
                <div class={`rounded-2xl p-4 ${mutedGlassPanelClass}`}>
                  <p class="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Ubigeo</p>
                  <p class="mt-2 text-sm font-medium text-slate-900">{selectedClient.ubigeo || 'No registrado'}</p>
                </div>
                <div class={`rounded-2xl p-4 md:col-span-2 ${mutedGlassPanelClass}`}>
                  <p class="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Dirección fiscal</p>
                  <div class="mt-2 flex items-start gap-2 text-sm text-slate-700">
                    <MapPin class="mt-0.5 h-4 w-4 shrink-0 text-slate-400" strokeWidth={1.9} />
                    <span>{selectedClient.direccion || 'Sin dirección registrada'}</span>
                  </div>
                </div>
                <div class={`rounded-2xl p-4 ${mutedGlassPanelClass}`}>
                  <p class="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Correo</p>
                  <div class="mt-2 flex items-start gap-2 text-sm text-slate-700">
                    <Mail class="mt-0.5 h-4 w-4 shrink-0 text-slate-400" strokeWidth={1.9} />
                    <span>{selectedClient.email || 'No registrado'}</span>
                  </div>
                </div>
                <div class={`rounded-2xl p-4 ${mutedGlassPanelClass}`}>
                  <p class="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Teléfono</p>
                  <div class="mt-2 flex items-start gap-2 text-sm text-slate-700">
                    <Phone class="mt-0.5 h-4 w-4 shrink-0 text-slate-400" strokeWidth={1.9} />
                    <span>{selectedClient.telefono || 'No registrado'}</span>
                  </div>
                </div>
              </div>
            </article>

            <article class={`rounded-[30px] p-6 ${glassPanelClass}`}>
              <div class="mb-5 flex items-center gap-3">
                <div class="flex h-10 w-10 items-center justify-center rounded-2xl bg-slate-50 text-slate-600">
                  <CalendarDays class="h-5 w-5" strokeWidth={1.9} />
                </div>
                <div>
                  <p class="text-sm font-semibold text-slate-900">Historial comercial</p>
                  <p class="text-xs text-slate-500">Cotizaciones recientes y evolución de la relación comercial.</p>
                </div>
              </div>

              {#if clientHistory.length > 0}
                <div class="space-y-3">
                  {#each clientHistory as cotizacion}
                    <div class={`rounded-2xl p-4 ${mutedGlassPanelClass} ${premiumRowHoverClass}`}>
                      <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                        <div class="space-y-1">
                          <p class="text-sm font-semibold text-slate-900">
                            {cotizacion.serie}-{String(cotizacion.correlativo).padStart(6, '0')}
                          </p>
                          <p class="text-xs text-slate-500">{formatDate(cotizacion.fecha_emision)}</p>
                        </div>

                        <div class="flex flex-wrap gap-2">
                          <span class="rounded-full bg-white px-3 py-1 text-xs font-semibold text-slate-600">
                            {cotizacion.estado}
                          </span>
                          <span class="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
                            {formatCurrency(cotizacion.total_venta)}
                          </span>
                        </div>
                      </div>

                      {#if cotizacion.items?.length > 0}
                        <div class="mt-3 border-t border-slate-200 pt-3">
                          <p class="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Items</p>
                          <div class="mt-2 space-y-2">
                            {#each cotizacion.items.slice(0, 3) as item}
                              <div class="flex items-start justify-between gap-3 text-sm text-slate-700">
                                <span class="min-w-0 flex-1">{item.descripcion}</span>
                                <span class="shrink-0 text-slate-500">{item.cantidad} u.</span>
                              </div>
                            {/each}
                          </div>
                        </div>
                      {/if}
                    </div>
                  {/each}
                </div>
              {:else}
                <div class={`flex min-h-[260px] flex-col items-center justify-center gap-4 rounded-2xl px-6 py-10 text-center ${mutedGlassPanelClass}`}>
                  <div class="flex h-14 w-14 items-center justify-center rounded-2xl border border-slate-200 bg-white text-slate-400">
                    <CalendarDays class="h-6 w-6" strokeWidth={1.9} />
                  </div>
                  <div class="space-y-2">
                    <p class="text-lg font-semibold tracking-tight text-slate-900">Sin historial comercial</p>
                    <p class="max-w-md text-sm leading-6 text-slate-500">Este cliente aún no tiene cotizaciones registradas en el sistema.</p>
                  </div>
                </div>
              {/if}
            </article>
          </section>
        {:else}
          <div class={`flex min-h-[420px] flex-col items-center justify-center gap-4 rounded-[30px] px-6 py-10 text-center ${glassPanelStrongClass}`}>
            <div class={`flex h-14 w-14 items-center justify-center rounded-2xl text-slate-400 ${mutedGlassPanelClass}`}>
              <Building2 class="h-6 w-6" strokeWidth={1.9} />
            </div>
            <div class="space-y-2">
              <p class="text-lg font-semibold tracking-tight text-slate-900">No hay clientes disponibles</p>
              <p class="max-w-md text-sm leading-6 text-slate-500">Carga clientes en la base para empezar a usar el directorio CRM.</p>
            </div>
          </div>
        {/if}
      </div>
    </section>
  {/if}
</div>
