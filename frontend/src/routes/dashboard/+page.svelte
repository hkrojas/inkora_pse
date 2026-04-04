<script>
  import { api } from '$lib/utils/api';
  import {
    glassPanelClass,
    glassPanelStrongClass,
    mutedGlassPanelClass,
    pageEyebrowClass,
    pageSubtitleClass,
    pageTitleClass,
    premiumRowHoverClass,
    premiumSecondaryButtonClass
  } from '$lib/utils/uiClasses';
  import {
    Calculator,
    CalendarDays,
    ChevronRight,
    CircleAlert,
    CircleCheckBig,
    FileText,
    Package,
    Truck
  } from 'lucide-svelte';
  import { onMount } from 'svelte';

  let loading = true;
  let error = '';
  let statsData = {
    ingresos_totales: 0,
    saldos_por_cobrar: 0,
    costos_tercerizacion: 0,
    top_productos: []
  };
  let cotizaciones = [];

  onMount(loadDashboard);

  async function loadDashboard() {
    loading = true;
    error = '';

    try {
      const [stats, docs] = await Promise.all([
        api.get('/analytics/dashboard'),
        api.get('/cotizaciones/?limit=100')
      ]);

      statsData = stats;
      cotizaciones = Array.isArray(docs) ? docs : [];
    } catch (loadError) {
      console.error('Error cargando dashboard:', loadError);
      error = 'No se pudo cargar el resumen del negocio.';
    } finally {
      loading = false;
    }
  }

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

  function formatCurrency(amount) {
    return new Intl.NumberFormat('es-PE', {
      style: 'currency',
      currency: 'PEN',
      maximumFractionDigits: 0
    }).format(Number(amount || 0));
  }

  function formatCompact(value) {
    return new Intl.NumberFormat('es-PE', {
      notation: 'compact',
      maximumFractionDigits: 1
    }).format(Number(value || 0));
  }

  function formatRelativeTime(dateStr) {
    if (!dateStr) return 'Sin fecha';

    const target = new Date(dateStr);
    if (Number.isNaN(target.getTime())) return 'Sin fecha';

    const diffMs = Date.now() - target.getTime();
    const diffMinutes = Math.max(Math.round(diffMs / 60000), 0);

    if (diffMinutes < 1) return 'Hace unos segundos';
    if (diffMinutes < 60) return `Hace ${diffMinutes} min`;

    const diffHours = Math.round(diffMinutes / 60);
    if (diffHours < 24) return `Hace ${diffHours} h`;

    const diffDays = Math.round(diffHours / 24);
    if (diffDays < 30) return `Hace ${diffDays} d`;

    return target.toLocaleDateString('es-PE', {
      day: '2-digit',
      month: 'short'
    });
  }

  function createMonthlySeries(items) {
    const now = new Date();
    const months = Array.from({ length: 6 }, (_, index) => {
      const date = new Date(now.getFullYear(), now.getMonth() - (5 - index), 1);
      const label = date
        .toLocaleDateString('es-PE', { month: 'short' })
        .replace('.', '')
        .toUpperCase();

      return {
        key: `${date.getFullYear()}-${date.getMonth()}`,
        label,
        revenue: 0,
        quotes: 0
      };
    });

    const monthMap = new Map(months.map((month) => [month.key, month]));

    for (const item of items) {
      const issuedAt = item?.fecha_emision ? new Date(item.fecha_emision) : null;
      if (!issuedAt || Number.isNaN(issuedAt.getTime())) continue;

      const bucket = monthMap.get(`${issuedAt.getFullYear()}-${issuedAt.getMonth()}`);
      if (!bucket) continue;

      bucket.revenue += Number(item.total_venta || 0);
      bucket.quotes += 1;
    }

    return months;
  }

  function getActivityMeta(cotizacion) {
    const variant = normalizeStatus(cotizacion?.estado);

    if (variant === 'approved') {
      return {
        icon: CircleCheckBig,
        title: 'Cotizacion aprobada',
        tone: 'bg-emerald-50 text-emerald-700'
      };
    }

    if (variant === 'cancelled') {
      return {
        icon: CircleAlert,
        title: 'Cotizacion observada',
        tone: 'bg-red-50 text-red-700'
      };
    }

    return {
      icon: FileText,
      title: 'Nueva cotizacion creada',
      tone: 'bg-amber-50 text-amber-700'
    };
  }

  function formatDelta(value) {
    return `+${Math.max(0, Math.round(value))}%`;
  }

  $: approvedCount = cotizaciones.filter((cotizacion) => normalizeStatus(cotizacion?.estado) === 'approved').length;
  $: pendingCount = cotizaciones.filter((cotizacion) => normalizeStatus(cotizacion?.estado) === 'pending').length;
  $: quoteCount = cotizaciones.length;
  $: activeProducts = Array.isArray(statsData.top_productos) ? statsData.top_productos.length : 0;
  $: approvalRatio = quoteCount > 0 ? (approvedCount / quoteCount) * 100 : 0;
  $: pendingRatio = quoteCount > 0 ? (pendingCount / quoteCount) * 100 : 0;
  $: outsourcingRatio =
    Number(statsData.ingresos_totales || 0) > 0
      ? (Number(statsData.costos_tercerizacion || 0) / Number(statsData.ingresos_totales || 1)) * 100
      : 0;

  $: kpiCards = [
    {
      title: 'Ingresos cobrados',
      value: formatCurrency(statsData.ingresos_totales),
      delta: formatDelta(approvalRatio),
      caption: 'Cobro consolidado',
      icon: Calculator
    },
    {
      title: 'Saldos por cobrar',
      value: formatCurrency(statsData.saldos_por_cobrar),
      delta: formatDelta(pendingRatio),
      caption: 'Pipeline pendiente',
      icon: FileText
    },
    {
      title: 'Costo tercerizado',
      value: formatCurrency(statsData.costos_tercerizacion),
      delta: formatDelta(outsourcingRatio),
      caption: 'Carga operativa externa',
      icon: Truck
    },
    {
      title: 'Cotizaciones monitoreadas',
      value: formatCompact(quoteCount),
      delta: formatDelta(activeProducts * 4),
      caption: 'Base reciente de analisis',
      icon: Package
    }
  ];

  $: chartSeries = createMonthlySeries(cotizaciones);
  $: maxRevenue = Math.max(...chartSeries.map((point) => point.revenue), 1);
  $: maxQuotes = Math.max(...chartSeries.map((point) => point.quotes), 1);
  $: chartDots = chartSeries.map((point, index) => {
    const chartWidth = 560;
    const leftPadding = 28;
    const usableWidth = chartWidth - leftPadding * 2;
    const x = chartSeries.length > 1 ? leftPadding + (usableWidth / (chartSeries.length - 1)) * index : chartWidth / 2;
    const y = 182 - (point.revenue / maxRevenue) * 126;

    return {
      ...point,
      x,
      y
    };
  });
  $: chartLinePoints = chartDots.map((point) => `${point.x},${point.y}`).join(' ');
  $: activityItems = cotizaciones
    .slice()
    .sort((a, b) => new Date(b.fecha_emision || 0).getTime() - new Date(a.fecha_emision || 0).getTime())
    .slice(0, 5)
    .map((cotizacion) => {
      const meta = getActivityMeta(cotizacion);

      return {
        ...meta,
        client: cotizacion?.cliente?.razon_social || 'Cliente sin nombre',
        document: `${cotizacion?.serie || 'COT'}-${String(cotizacion?.correlativo || 0).padStart(6, '0')}`,
        amount: formatCurrency(cotizacion?.total_venta),
        timestamp: formatRelativeTime(cotizacion?.fecha_emision)
      };
    });
</script>

<div class="space-y-6">
  <section class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
    <div class="space-y-2">
      <p class={pageEyebrowClass}>Centro analitico</p>
      <div class="space-y-1">
        <h1 class={pageTitleClass}>Dashboard</h1>
        <p class={`max-w-2xl ${pageSubtitleClass}`}>
          Una lectura ejecutiva del negocio con ingresos, documentos y movimiento operativo reciente.
        </p>
      </div>
    </div>

    <button
      class={`inline-flex items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-medium ${premiumSecondaryButtonClass}`}
    >
      <CalendarDays class="h-4 w-4 text-slate-500" strokeWidth={2} />
      <span>Ultimos 30 dias</span>
    </button>
  </section>

  {#if error}
    <div class="rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
      {error}
    </div>
  {/if}

  <section class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
    {#if loading}
      {#each Array(4) as _}
        <div class={`h-40 animate-pulse rounded-[28px] ${glassPanelClass}`}></div>
      {/each}
    {:else}
      {#each kpiCards as card}
        {@const Icon = card.icon}
        <article class={`relative overflow-hidden rounded-[28px] p-5 ${glassPanelClass}`}>
          <div class="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(255,255,255,0.9),transparent_34%),radial-gradient(circle_at_bottom_left,rgba(59,130,246,0.08),transparent_28%)]"></div>
          <div class="mb-6 flex items-start justify-between gap-3">
            <div class="rounded-2xl border border-white/70 bg-white/80 p-3 text-slate-600 shadow-[0_12px_24px_rgba(15,23,42,0.05)]">
              <Icon class="h-5 w-5" strokeWidth={1.9} />
            </div>

            <span class="inline-flex rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700">
              {card.delta}
            </span>
          </div>

          <div class="relative space-y-2">
            <p class="text-sm font-medium text-slate-500">{card.title}</p>
            <p class="text-3xl font-semibold tracking-tight text-slate-900">{card.value}</p>
            <p class="text-xs uppercase tracking-[0.18em] text-slate-400">{card.caption}</p>
          </div>

          <div class="pointer-events-none absolute inset-x-0 bottom-0 h-1 bg-gradient-to-r from-emerald-500/0 via-emerald-500/40 to-emerald-500/0"></div>
        </article>
      {/each}
    {/if}
  </section>

  <section class="grid gap-6 xl:grid-cols-[minmax(0,1.7fr)_minmax(320px,1fr)]">
    <article class={`rounded-[30px] p-5 ${glassPanelStrongClass}`}>
      <div class="mb-6 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div class="space-y-1">
          <p class="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Panorama principal</p>
          <h2 class="text-lg font-semibold tracking-tight text-slate-900">Ingresos vs Cotizaciones</h2>
          <p class="text-sm leading-6 text-slate-500">
            Vista consolidada del volumen reciente de documentos frente al valor comercial generado.
          </p>
        </div>

        <div class="flex flex-wrap gap-3 text-xs font-semibold text-slate-500">
          <span class="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1.5">
            <span class="h-2.5 w-2.5 rounded-full bg-slate-300"></span>
            Cotizaciones
          </span>
          <span class="inline-flex items-center gap-2 rounded-full bg-emerald-50 px-3 py-1.5 text-emerald-700">
            <span class="h-2.5 w-2.5 rounded-full bg-emerald-500"></span>
            Ingresos
          </span>
        </div>
      </div>

      <div class={`relative overflow-hidden rounded-[28px] p-5 ${mutedGlassPanelClass}`}>
        <div class="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_right,_rgba(16,185,129,0.10),_transparent_38%)]"></div>

        {#if quoteCount === 0}
          <div class="flex h-[320px] flex-col items-center justify-center gap-4 text-center">
            <div class="rounded-2xl border border-slate-200 bg-white p-4 text-slate-400 shadow-sm">
              <Calculator class="h-8 w-8" strokeWidth={1.8} />
            </div>
            <div class="space-y-2">
              <p class="text-sm font-semibold text-slate-900">Sin movimiento suficiente para el grafico</p>
              <p class="max-w-md text-sm leading-6 text-slate-500">
                En cuanto entren nuevas cotizaciones, este panel mostrara la relacion entre ingresos y volumen comercial.
              </p>
            </div>
          </div>
        {:else}
          <div class="relative h-[320px]">
            <div class="absolute inset-0">
              {#each [0, 1, 2, 3] as step}
                <div
                  class="absolute inset-x-0 border-t border-dashed border-slate-200"
                  style={`top: ${step * 25}%`}
                ></div>
              {/each}
            </div>

            <div class="absolute inset-x-4 bottom-12 top-8 grid grid-cols-6 items-end gap-4">
              {#each chartSeries as point}
                <div class="flex h-full flex-col justify-end gap-3">
                  <div class="mx-auto w-full max-w-[56px] rounded-t-2xl bg-slate-200/90 transition-all duration-300">
                    <div
                      class="w-full rounded-t-2xl bg-slate-300/80"
                      style={`height: ${Math.max((point.quotes / maxQuotes) * 160, point.quotes ? 24 : 10)}px`}
                    ></div>
                  </div>
                </div>
              {/each}
            </div>

            <svg viewBox="0 0 560 220" class="absolute inset-x-4 top-4 h-[72%] w-auto overflow-visible">
              <polyline
                points={chartLinePoints}
                fill="none"
                stroke="rgb(5 150 105)"
                stroke-width="4"
                stroke-linecap="round"
                stroke-linejoin="round"
              />

              {#each chartDots as point}
                <circle cx={point.x} cy={point.y} r="6" fill="white" stroke="rgb(5 150 105)" stroke-width="3"></circle>
              {/each}
            </svg>

            <div class="absolute inset-x-4 bottom-0 grid grid-cols-6 gap-4">
              {#each chartSeries as point}
                <div class="space-y-1 text-center">
                  <p class="text-xs font-semibold text-slate-600">{point.label}</p>
                  <p class="text-[11px] text-slate-400">{point.quotes} docs</p>
                </div>
              {/each}
            </div>
          </div>
        {/if}
      </div>
    </article>

    <article class={`rounded-[30px] p-5 ${glassPanelStrongClass}`}>
      <div class="mb-5 space-y-1">
        <p class="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Pulso comercial</p>
        <h2 class="text-lg font-semibold tracking-tight text-slate-900">Actividad reciente</h2>
        <p class="text-sm leading-6 text-slate-500">
          Eventos recientes vinculados al flujo comercial y al estado de las cotizaciones.
        </p>
      </div>

      <div class="space-y-3">
        {#if loading}
          {#each Array(5) as _}
            <div class={`h-20 animate-pulse rounded-2xl ${mutedGlassPanelClass}`}></div>
          {/each}
        {:else if activityItems.length === 0}
          <div class="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-5 py-10 text-center">
            <p class="text-sm font-semibold text-slate-900">Todavia no hay actividad reciente</p>
            <p class="mt-2 text-sm leading-6 text-slate-500">
              El panel se llenara automaticamente cuando entren nuevas cotizaciones al sistema.
            </p>
          </div>
        {:else}
          {#each activityItems as item}
            {@const Icon = item.icon}
            <div class={`flex items-start gap-3 rounded-2xl px-4 py-3 ${mutedGlassPanelClass} ${premiumRowHoverClass}`}>
              <div class={`mt-0.5 rounded-2xl p-2.5 ${item.tone}`}>
                <Icon class="h-4 w-4" strokeWidth={2} />
              </div>

              <div class="min-w-0 flex-1 space-y-1">
                <div class="flex items-start justify-between gap-3">
                  <p class="text-sm font-semibold text-slate-900">{item.title}</p>
                  <span class="shrink-0 text-xs text-slate-400">{item.timestamp}</span>
                </div>

                <p class="text-sm text-slate-600">{item.client}</p>
                <div class="flex items-center justify-between gap-3 text-xs text-slate-400">
                  <span>{item.document}</span>
                  <span>{item.amount}</span>
                </div>
              </div>
            </div>
          {/each}
        {/if}
      </div>

      {#if !loading && activeProducts > 0}
        <div class={`mt-6 space-y-3 rounded-[24px] p-4 ${mutedGlassPanelClass}`}>
          <div class="flex items-center justify-between gap-3">
            <p class="text-sm font-semibold text-slate-900">Productos con mayor movimiento</p>
            <a href="/cotizaciones" class="inline-flex items-center gap-1 text-xs font-semibold text-emerald-700">
              Ver cotizaciones
              <ChevronRight class="h-3.5 w-3.5" strokeWidth={2.2} />
            </a>
          </div>

          <div class="flex flex-wrap gap-2">
            {#each statsData.top_productos as producto}
              <span class="inline-flex rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600">
                {producto}
              </span>
            {/each}
          </div>
        </div>
      {/if}
    </article>
  </section>
</div>
