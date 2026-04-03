<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/utils/api';
  import { auth } from '$lib/stores/auth';
  import { fly } from 'svelte/transition';

  let loading = true;
  let statsData = {
    ingresos_totales: 0,
    saldos_por_cobrar: 0,
    costos_tercerizacion: 0,
    top_productos: []
  };
  let recentJobs = [];

  onMount(async () => {
    try {
      const [stats, cotizaciones] = await Promise.all([
        api.get('/analytics/dashboard'),
        api.get('/cotizaciones/?limit=5')
      ]);
      statsData = stats;
      recentJobs = cotizaciones.map(c => ({
        id: `${c.serie}-${c.correlativo}`,
        client: c.cliente.razon_social,
        ruc: c.cliente.ruc || '',
        status: c.estado,
        total: c.total_venta
      }));
    } catch (error) {
      console.error('Error cargando dashboard:', error);
    } finally {
      loading = false;
    }
  });

  function formatCurrency(amount) {
    return new Intl.NumberFormat('es-PE', { style: 'currency', currency: 'PEN' }).format(amount);
  }

  function formatUSD(amount) {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount / 3.742);
  }

  const getStatusBadge = (status) => {
    switch (status.toLowerCase()) {
      case 'facturada': return { bg: 'bg-secondary-container/20 text-on-secondary-container', dot: 'bg-secondary', label: 'Aceptado' };
      case 'pendiente': return { bg: 'bg-tertiary-container/10 text-on-tertiary-container', dot: 'bg-tertiary', label: 'Pendiente' };
      case 'anulada': return { bg: 'bg-error-container/20 text-error', dot: 'bg-error', label: 'Anulado' };
      default: return { bg: 'bg-surface-container text-on-surface-variant', dot: 'bg-outline', label: status };
    }
  };

  const getStatusBorder = (status) => {
    switch (status.toLowerCase()) {
      case 'facturada': return 'border-secondary';
      case 'pendiente': return 'border-tertiary';
      case 'anulada': return 'border-error';
      default: return 'border-outline';
    }
  };
</script>

<div class="space-y-8">
  <!-- Header Section -->
  <div class="flex flex-col md:flex-row md:items-end justify-between gap-6" in:fly={{ y: 10, duration: 400 }}>
    <div>
      <h2 class="font-manrope text-3xl font-extrabold text-primary tracking-tight">Panel de Control</h2>
      <p class="text-outline font-medium mt-1">Bienvenido de nuevo. Aquí está el resumen de tu producción hoy.</p>
    </div>
    <div class="flex gap-3">
      <button class="px-5 py-2.5 bg-surface-container-lowest border border-outline-variant/30 text-primary font-bold text-sm rounded-xl flex items-center gap-2 hover:bg-surface-container-low transition-colors">
        <span class="material-symbols-outlined text-lg">calendar_today</span>
        Últimos 30 días
      </button>
      <button class="px-5 py-2.5 bg-primary text-white font-bold text-sm rounded-xl flex items-center gap-2 shadow-lg shadow-primary/20 hover:scale-[1.02] active:scale-95 transition-all">
        <span class="material-symbols-outlined text-lg">download</span>
        Reporte Mensual
      </button>
    </div>
  </div>

  <!-- Bento Grid: Top Stats -->
  {#if loading}
    <div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
      {#each [1, 2, 3, 4] as _}
        <div class="bg-surface-container-low h-44 rounded-2xl border border-outline-variant/10 animate-pulse"></div>
      {/each}
    </div>
  {:else}
    <div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
      <!-- Currency Card: Soles -->
      <div class="lg:col-span-2 p-6 bg-surface-container-lowest rounded-2xl border border-outline-variant/10 shadow-sm relative overflow-hidden group" in:fly={{ y: 20, duration: 500 }}>
        <div class="absolute top-0 right-0 p-8 opacity-5 group-hover:scale-110 transition-transform duration-500">
          <span class="material-symbols-outlined text-primary" style="font-size: 8rem;">payments</span>
        </div>
        <div class="flex items-start justify-between mb-8">
          <div class="p-3 bg-primary/5 rounded-xl text-primary">
            <span class="material-symbols-outlined filled">account_balance</span>
          </div>
          <span class="flex items-center gap-1 text-secondary font-bold text-xs bg-secondary-container/30 px-2 py-1 rounded-full">
            <span class="material-symbols-outlined text-sm">trending_up</span>
            +12.5%
          </span>
        </div>
        <p class="text-outline text-xs font-bold uppercase tracking-widest mb-1">Ingresos Totales (PEN)</p>
        <div class="flex items-baseline gap-2">
          <h3 class="font-manrope text-4xl font-extrabold text-primary">{formatCurrency(statsData.ingresos_totales)}</h3>
          <span class="text-outline text-sm font-medium">acumulado</span>
        </div>
      </div>

      <!-- Currency Card: Saldos -->
      <div class="p-6 bg-surface-container-lowest rounded-2xl border border-outline-variant/10 shadow-sm relative overflow-hidden group" in:fly={{ y: 20, duration: 500, delay: 100 }}>
        <div class="flex items-start justify-between mb-8">
          <div class="p-3 bg-tertiary-container/20 rounded-xl text-tertiary">
            <span class="material-symbols-outlined filled">account_balance_wallet</span>
          </div>
        </div>
        <p class="text-outline text-xs font-bold uppercase tracking-widest mb-1">Saldos por Cobrar</p>
        <h3 class="font-manrope text-3xl font-extrabold text-on-surface">{formatCurrency(statsData.saldos_por_cobrar)}</h3>
        <div class="mt-4 flex items-center gap-2">
          <span class="material-symbols-outlined text-warning text-sm">schedule</span>
          <span class="text-[10px] text-outline font-bold">Pendientes de cobro</span>
        </div>
      </div>

      <!-- SUNAT Status Summary -->
      <div class="p-6 bg-primary-container rounded-2xl border border-primary text-white shadow-xl shadow-primary/10 flex flex-col justify-between" in:fly={{ y: 20, duration: 500, delay: 200 }}>
        <div>
          <div class="flex items-center justify-between mb-4">
            <span class="text-xs font-bold uppercase tracking-widest opacity-80">Estado SUNAT</span>
            <div class="w-2 h-2 rounded-full bg-secondary-fixed shadow-[0_0_8px_rgba(139,248,194,0.8)]"></div>
          </div>
          <h3 class="font-manrope text-2xl font-bold">100% Sincronizado</h3>
        </div>
        <div class="mt-4 pt-4 border-t border-white/10">
          <p class="text-[11px] opacity-70 mb-2">Comprobantes enviados hoy</p>
          <div class="flex items-end justify-between">
            <span class="text-3xl font-bold">—</span>
            <span class="text-xs font-medium text-secondary-fixed flex items-center gap-1">
              <span class="material-symbols-outlined text-sm">done_all</span>
              Sin errores
            </span>
          </div>
        </div>
      </div>
    </div>
  {/if}

  <!-- Middle Section: Chart & Stock -->
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
    <!-- Sales Chart Placeholder -->
    <div class="lg:col-span-2 bg-surface-container-low rounded-3xl p-8" in:fly={{ y: 20, duration: 500, delay: 150 }}>
      <div class="flex items-center justify-between mb-10">
        <h3 class="font-manrope text-xl font-extrabold text-primary">Tendencia de Ventas</h3>
        <div class="flex gap-4">
          <span class="flex items-center gap-2 text-xs font-bold text-outline">
            <span class="w-3 h-3 rounded-sm bg-primary"></span> Proyectado
          </span>
          <span class="flex items-center gap-2 text-xs font-bold text-outline">
            <span class="w-3 h-3 rounded-sm bg-secondary"></span> Real
          </span>
        </div>
      </div>
      <div class="h-64 flex items-end justify-between gap-4 px-2">
        {#each ['ENE', 'FEB', 'MAR', 'ABR', 'MAY', 'JUN'] as month, i}
          {@const heights = [32, 40, 48, 36, 56, 44]}
          {@const actuals = [24, 32, 44, 28, 52, 38]}
          <div class="flex-1 group flex flex-col items-center gap-3">
            <div 
              class="w-full bg-primary/10 rounded-t-lg relative group-hover:scale-y-105 transition-all duration-500 origin-bottom"
              style="height: {heights[i] * 4}px;"
            >
              <div class="absolute bottom-0 w-full bg-secondary rounded-t-lg" style="height: {actuals[i] * 4}px;"></div>
            </div>
            <span class="text-[10px] font-bold text-outline">{month}</span>
          </div>
        {/each}
      </div>
    </div>

    <!-- Tercerización Card -->
    <div class="bg-surface-container-lowest rounded-3xl border border-outline-variant/10 p-8 shadow-sm" in:fly={{ y: 20, duration: 500, delay: 200 }}>
      <div class="flex items-center justify-between mb-8">
        <h3 class="font-manrope text-xl font-extrabold text-primary">Costos Externos</h3>
        <span class="material-symbols-outlined text-tertiary">warehouse</span>
      </div>
      <div class="space-y-6">
        <div>
          <p class="text-outline text-xs font-bold uppercase tracking-widest mb-2">Tercerización Total</p>
          <h3 class="font-manrope text-3xl font-extrabold text-on-surface">{formatCurrency(statsData.costos_tercerizacion)}</h3>
        </div>

        {#if statsData.top_productos && statsData.top_productos.length > 0}
          <div class="space-y-4 pt-4 border-t border-outline-variant/10">
            <p class="text-[10px] font-bold text-outline uppercase tracking-widest">Top Productos</p>
            {#each statsData.top_productos.slice(0, 3) as producto}
              <div class="flex items-center gap-3">
                <div class="w-10 h-10 bg-slate-100 rounded-xl flex items-center justify-center">
                  <span class="material-symbols-outlined text-primary text-lg">inventory_2</span>
                </div>
                <div class="flex-1">
                  <p class="text-sm font-bold text-on-surface truncate">{producto.nombre}</p>
                  <p class="text-[10px] text-outline font-medium">{producto.cantidad} uds</p>
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>
      <a href="/cotizaciones" class="block w-full mt-8 py-3 border border-outline-variant/30 rounded-xl text-xs font-bold text-primary hover:bg-primary hover:text-white transition-all text-center">
        Ver Cotizaciones
      </a>
    </div>
  </div>

  <!-- Compliance Ledger: Recent Documents -->
  <section class="bg-surface-container-lowest rounded-3xl border border-outline-variant/10 shadow-sm overflow-hidden" in:fly={{ y: 20, duration: 500, delay: 250 }}>
    <div class="px-8 py-6 border-b border-outline-variant/10 flex items-center justify-between">
      <h3 class="font-manrope text-xl font-extrabold text-primary">Comprobantes Recientes</h3>
      <a href="/cotizaciones" class="text-xs font-bold text-primary flex items-center gap-1 hover:underline">
        Ver todo
        <span class="material-symbols-outlined text-sm">arrow_forward</span>
      </a>
    </div>

    {#if loading}
      <div class="p-8 space-y-3">
        {#each [1, 2, 3] as _}
          <div class="h-16 bg-surface-container-low rounded-xl animate-pulse"></div>
        {/each}
      </div>
    {:else if recentJobs.length === 0}
      <div class="py-20 flex flex-col items-center justify-center gap-4">
        <div class="p-4 rounded-full bg-surface-container text-on-surface-variant">
          <span class="material-symbols-outlined text-4xl">description</span>
        </div>
        <p class="text-on-surface-variant font-medium text-sm">No hay comprobantes recientes.</p>
        <a href="/cotizaciones" class="mt-2 px-5 py-2.5 rounded-xl bg-primary text-white text-sm font-bold hover:shadow-lg hover:shadow-primary/20 transition-all flex items-center gap-2">
          <span class="material-symbols-outlined text-sm">add_circle</span>
          Crear Primera Cotización
        </a>
      </div>
    {:else}
      <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="bg-surface-container-low/50">
              <th class="px-8 py-4 text-[10px] font-bold text-outline uppercase tracking-wider">Número</th>
              <th class="px-8 py-4 text-[10px] font-bold text-outline uppercase tracking-wider">Cliente</th>
              <th class="px-8 py-4 text-[10px] font-bold text-outline uppercase tracking-wider text-right">Monto</th>
              <th class="px-8 py-4 text-[10px] font-bold text-outline uppercase tracking-wider text-center">Estado</th>
              <th class="px-8 py-4 text-[10px] font-bold text-outline uppercase tracking-wider text-right">Acción</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-outline-variant/5">
            {#each recentJobs as job}
              {@const status = getStatusBadge(job.status)}
              <tr class="hover:bg-surface-container-low/30 transition-colors">
                <td class="px-8 py-5 border-l-4 {getStatusBorder(job.status)}">
                  <span class="text-sm font-bold text-on-surface">{job.id}</span>
                </td>
                <td class="px-8 py-5">
                  <p class="text-sm font-semibold text-on-surface">{job.client}</p>
                  {#if job.ruc}
                    <p class="text-[10px] text-outline">RUC: {job.ruc}</p>
                  {/if}
                </td>
                <td class="px-8 py-5 text-right">
                  <p class="text-sm font-bold text-on-surface">{formatCurrency(job.total)}</p>
                  <p class="text-[10px] text-outline font-medium">{formatUSD(job.total)}</p>
                </td>
                <td class="px-8 py-5 text-center">
                  <span class="inline-flex items-center gap-1.5 px-3 py-1 {status.bg} rounded-full text-[10px] font-bold">
                    <span class="w-1.5 h-1.5 rounded-full {status.dot}"></span>
                    {status.label}
                  </span>
                </td>
                <td class="px-8 py-5 text-right">
                  <button class="p-2 text-outline hover:text-primary transition-colors">
                    <span class="material-symbols-outlined text-lg">more_vert</span>
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
