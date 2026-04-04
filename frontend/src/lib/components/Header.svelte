<script>
  import { api } from '$lib/utils/api';
  import { auth, logout } from '$lib/stores/auth';
  import {
    glassPanelClass,
    glassPanelStrongClass,
    premiumInputClass,
    premiumSecondaryButtonClass
  } from '$lib/utils/uiClasses';
  import { Bell, CircleAlert, LogOut, Menu, Search } from 'lucide-svelte';
  import { createEventDispatcher, onMount } from 'svelte';
  import { fade } from 'svelte/transition';

  const dispatch = createEventDispatcher();

  let notificationRoot;
  let showNotifications = false;
  let alertsLoading = false;
  let alertsError = '';
  let inventoryAlerts = [];

  function getInitials(name) {
    if (!name) return 'PF';
    return name
      .split(' ')
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0])
      .join('')
      .toUpperCase();
  }

  function formatRelativeDate(dateString) {
    if (!dateString) return 'Sin fecha';

    const timestamp = new Date(dateString).getTime();
    const diffMinutes = Math.max(Math.round((Date.now() - timestamp) / 60000), 0);

    if (diffMinutes < 1) return 'Ahora mismo';
    if (diffMinutes < 60) return `Hace ${diffMinutes} min`;

    const diffHours = Math.round(diffMinutes / 60);
    if (diffHours < 24) return `Hace ${diffHours} h`;

    const diffDays = Math.round(diffHours / 24);
    return `Hace ${diffDays} d`;
  }

  async function loadInventoryAlerts() {
    alertsLoading = true;
    alertsError = '';

    try {
      inventoryAlerts = await api.get('/alertas/inventario');
    } catch (error) {
      alertsError = error?.message || 'No se pudieron cargar las alertas de inventario.';
    } finally {
      alertsLoading = false;
    }
  }

  async function toggleNotifications() {
    showNotifications = !showNotifications;

    if (showNotifications) {
      await loadInventoryAlerts();
    }
  }

  onMount(() => {
    const handleDocumentClick = (event) => {
      if (showNotifications && notificationRoot && !notificationRoot.contains(event.target)) {
        showNotifications = false;
      }
    };

    document.addEventListener('click', handleDocumentClick, true);

    return () => {
      document.removeEventListener('click', handleDocumentClick, true);
    };
  });

  $: criticalAlertsCount = inventoryAlerts.length;
  $: user = $auth.user;
</script>

<svelte:window on:keydown={(event) => event.key === 'Escape' && (showNotifications = false)} />

<header class="sticky top-0 z-30">
  <div class={`flex h-20 items-center gap-3 rounded-[28px] px-4 sm:px-6 lg:px-8 ${glassPanelStrongClass}`}>
    <button
      class={`inline-flex h-11 w-11 items-center justify-center rounded-2xl ${premiumSecondaryButtonClass} text-slate-700 md:hidden`}
      on:click={() => dispatch('toggleMobile')}
      aria-label="Abrir navegación"
    >
      <Menu class="h-5 w-5" strokeWidth={1.9} />
    </button>

    <div class="min-w-0 flex-1">
      <label class="sr-only" for="global-search">Buscador global</label>

      <div class="relative max-w-xl">
        <Search class="pointer-events-none absolute left-4 top-1/2 h-[18px] w-[18px] -translate-y-1/2 text-slate-400" strokeWidth={1.9} />
        <input
          id="global-search"
          type="text"
          placeholder="Buscar cotizaciones, clientes o órdenes..."
          class={`h-11 w-full rounded-2xl pl-11 pr-4 text-sm text-slate-700 ${premiumInputClass}`}
        />
      </div>
    </div>

    <div class="flex items-center gap-3">
      <div class="relative" bind:this={notificationRoot}>
        <button
          on:click={toggleNotifications}
          class={`relative inline-flex h-11 w-11 items-center justify-center rounded-2xl ${premiumSecondaryButtonClass} text-slate-600 hover:text-slate-900`}
          aria-label="Notificaciones"
          aria-expanded={showNotifications}
          type="button"
        >
          <Bell class="h-5 w-5" strokeWidth={1.9} />
          {#if criticalAlertsCount > 0}
            <span class="absolute right-2.5 top-2.5 inline-flex min-h-[18px] min-w-[18px] items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-semibold text-white">
              {criticalAlertsCount > 9 ? '9+' : criticalAlertsCount}
            </span>
          {/if}
        </button>

        {#if showNotifications}
          <div
            class={`absolute right-0 top-[calc(100%+0.75rem)] z-40 w-[380px] max-w-[calc(100vw-2rem)] overflow-hidden rounded-[28px] ${glassPanelStrongClass}`}
            transition:fade={{ duration: 160 }}
          >
            <div class="border-b border-white/60 px-5 py-4">
              <div class="flex items-start justify-between gap-4">
                <div class="space-y-1">
                  <p class="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Alertas críticas</p>
                  <h3 class="text-base font-semibold tracking-tight text-slate-900">Inventario</h3>
                </div>

                <div class="rounded-full border border-white/70 bg-white/80 px-3 py-1 text-xs font-semibold text-slate-600 shadow-[0_8px_24px_rgba(15,23,42,0.05)]">
                  {criticalAlertsCount} activa{criticalAlertsCount === 1 ? '' : 's'}
                </div>
              </div>
            </div>

            <div class="max-h-[26rem] overflow-y-auto p-3">
              {#if alertsLoading}
                <div class="space-y-3 p-2" aria-hidden="true">
                  {#each Array.from({ length: 4 }, (_, index) => index) as _, index}
                    <div class={`animate-pulse rounded-2xl p-4 ${glassPanelClass}`}>
                      <div class="h-4 w-44 rounded-full bg-slate-200"></div>
                      <div class="mt-3 h-3 w-full rounded-full bg-slate-100"></div>
                      <div class="mt-2 h-3 w-24 rounded-full bg-slate-100"></div>
                    </div>
                  {/each}
                </div>
              {:else if alertsError}
                <div class="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  {alertsError}
                </div>
              {:else if inventoryAlerts.length > 0}
                <div class="space-y-2">
                  {#each inventoryAlerts as alert}
                    <div class="rounded-2xl border border-red-100/70 bg-white/90 p-4 shadow-[0_10px_30px_rgba(239,68,68,0.08)]">
                      <div class="flex items-start gap-3">
                        <div class="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-2xl bg-white text-red-500 shadow-sm">
                          <CircleAlert class="h-4 w-4" strokeWidth={1.9} />
                        </div>

                        <div class="min-w-0 flex-1 space-y-2">
                          <div class="flex items-start justify-between gap-3">
                            <div>
                              <p class="text-sm font-semibold text-slate-900">{alert.insumo?.nombre || 'Insumo sin referencia'}</p>
                              <p class="text-xs text-slate-500">{formatRelativeDate(alert.fecha_creacion)}</p>
                            </div>
                            <span class="rounded-full border border-red-100 bg-red-50 px-2.5 py-1 text-[11px] font-semibold text-red-700">
                              Stock crítico
                            </span>
                          </div>

                          <p class="text-sm leading-6 text-slate-600">{alert.mensaje}</p>

                          {#if alert.insumo}
                            <div class="flex flex-wrap gap-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                              <span class="rounded-full border border-white/80 bg-white/95 px-3 py-1 shadow-[0_6px_20px_rgba(15,23,42,0.04)]">
                                Stock: {alert.insumo.stock_actual} {alert.insumo.unidad_consumo}
                              </span>
                              <span class="rounded-full border border-white/80 bg-white/95 px-3 py-1 shadow-[0_6px_20px_rgba(15,23,42,0.04)]">
                                Mínimo: {alert.insumo.umbral_minimo}
                              </span>
                            </div>
                          {/if}
                        </div>
                      </div>
                    </div>
                  {/each}
                </div>
              {:else}
                <div class="flex flex-col items-center justify-center gap-3 px-5 py-10 text-center">
                  <div class="flex h-12 w-12 items-center justify-center rounded-2xl border border-white/80 bg-white/95 text-slate-700 shadow-[0_8px_24px_rgba(15,23,42,0.05)]">
                    <Bell class="h-5 w-5" strokeWidth={1.9} />
                  </div>
                  <div class="space-y-1">
                    <p class="text-sm font-semibold text-slate-900">Sin alertas críticas</p>
                    <p class="text-sm text-slate-500">El inventario no reporta quiebres de stock pendientes.</p>
                  </div>
                </div>
              {/if}
            </div>
          </div>
        {/if}
      </div>

      <div class="hidden h-10 w-px bg-white/70 lg:block"></div>

      <div class={`flex items-center gap-3 rounded-2xl px-3 py-2 ${glassPanelClass}`}>
        <div class="hidden min-w-0 text-right sm:block">
          <p class="truncate text-sm font-semibold tracking-tight text-slate-900">{user?.nombre_completo || 'Usuario PrintFlow'}</p>
          <p class="text-xs text-slate-500">{user?.is_superadmin ? 'Super Admin' : 'Operaciones'}</p>
        </div>

        <div class="flex h-11 w-11 items-center justify-center rounded-full bg-gradient-to-br from-slate-900 via-zinc-900 to-black text-sm font-semibold text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.08),0_12px_30px_rgba(15,23,42,0.25)]">
          {getInitials(user?.nombre_completo)}
        </div>

        <button
          on:click={logout}
          class="inline-flex h-10 w-10 items-center justify-center rounded-xl text-slate-500 transition-all duration-300 hover:bg-white/80 hover:text-slate-900"
          aria-label="Cerrar sesión"
          title="Cerrar sesión"
        >
          <LogOut class="h-[18px] w-[18px]" strokeWidth={1.9} />
        </button>
      </div>
    </div>
  </div>
</header>
