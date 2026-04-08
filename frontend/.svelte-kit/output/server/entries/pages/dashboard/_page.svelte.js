import { s as sanitize_props, a as spread_props, b as slot, d as attr_class, m as clsx, h as ensure_array_like, n as attr_style, e as attr, f as escape_html } from "../../../chunks/index2.js";
import { e as pageEyebrowClass, f as pageTitleClass, h as pageSubtitleClass, p as premiumSecondaryButtonClass, b as glassPanelClass, g as glassPanelStrongClass, m as mutedGlassPanelClass } from "../../../chunks/uiClasses.js";
import { I as Icon } from "../../../chunks/Icon.js";
import { F as File_text } from "../../../chunks/file-text.js";
import { T as Truck } from "../../../chunks/truck.js";
import { P as Package } from "../../../chunks/package.js";
import { C as Calendar_days } from "../../../chunks/calendar-days.js";
import { C as Circle_check_big } from "../../../chunks/circle-check-big.js";
import { C as Circle_alert } from "../../../chunks/circle-alert.js";
function Calculator($$renderer, $$props) {
  const $$sanitized_props = sanitize_props($$props);
  const iconNode = [
    [
      "rect",
      { "width": "16", "height": "20", "x": "4", "y": "2", "rx": "2" }
    ],
    ["line", { "x1": "8", "x2": "16", "y1": "6", "y2": "6" }],
    ["line", { "x1": "16", "x2": "16", "y1": "14", "y2": "18" }],
    ["path", { "d": "M16 10h.01" }],
    ["path", { "d": "M12 10h.01" }],
    ["path", { "d": "M8 10h.01" }],
    ["path", { "d": "M12 14h.01" }],
    ["path", { "d": "M8 14h.01" }],
    ["path", { "d": "M12 18h.01" }],
    ["path", { "d": "M8 18h.01" }]
  ];
  Icon($$renderer, spread_props([
    { name: "calculator" },
    $$sanitized_props,
    {
      /**
       * @component @name Calculator
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cmVjdCB3aWR0aD0iMTYiIGhlaWdodD0iMjAiIHg9IjQiIHk9IjIiIHJ4PSIyIiAvPgogIDxsaW5lIHgxPSI4IiB4Mj0iMTYiIHkxPSI2IiB5Mj0iNiIgLz4KICA8bGluZSB4MT0iMTYiIHgyPSIxNiIgeTE9IjE0IiB5Mj0iMTgiIC8+CiAgPHBhdGggZD0iTTE2IDEwaC4wMSIgLz4KICA8cGF0aCBkPSJNMTIgMTBoLjAxIiAvPgogIDxwYXRoIGQ9Ik04IDEwaC4wMSIgLz4KICA8cGF0aCBkPSJNMTIgMTRoLjAxIiAvPgogIDxwYXRoIGQ9Ik04IDE0aC4wMSIgLz4KICA8cGF0aCBkPSJNMTIgMThoLjAxIiAvPgogIDxwYXRoIGQ9Ik04IDE4aC4wMSIgLz4KPC9zdmc+Cg==) - https://lucide.dev/icons/calculator
       * @see https://lucide.dev/guide/packages/lucide-svelte - Documentation
       *
       * @param {Object} props - Lucide icons props and any valid SVG attribute
       * @returns {FunctionalComponent} Svelte component
       *
       */
      iconNode,
      children: ($$renderer2) => {
        $$renderer2.push(`<!--[-->`);
        slot($$renderer2, $$props, "default", {});
        $$renderer2.push(`<!--]-->`);
      },
      $$slots: { default: true }
    }
  ]));
}
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let approvedCount, pendingCount, quoteCount, activeProducts, approvalRatio, pendingRatio, outsourcingRatio, chartSeries, maxRevenue, maxQuotes, chartDots, chartLinePoints;
    let statsData = {
      ingresos_totales: 0,
      saldos_por_cobrar: 0,
      costos_tercerizacion: 0,
      top_productos: []
    };
    let cotizaciones = [];
    function normalizeStatus(status) {
      const normalized = `${status || ""}`.trim().toLowerCase();
      if (["aprobada", "aprobado", "facturada", "emitida", "cerrada"].includes(normalized)) {
        return "approved";
      }
      if ([
        "cancelada",
        "cancelado",
        "rechazada",
        "rechazado",
        "anulada",
        "anulado"
      ].includes(normalized)) {
        return "cancelled";
      }
      return "pending";
    }
    function formatCurrency(amount) {
      return new Intl.NumberFormat("es-PE", { style: "currency", currency: "PEN", maximumFractionDigits: 0 }).format(Number(amount || 0));
    }
    function formatCompact(value) {
      return new Intl.NumberFormat("es-PE", { notation: "compact", maximumFractionDigits: 1 }).format(Number(value || 0));
    }
    function formatRelativeTime(dateStr) {
      if (!dateStr) return "Sin fecha";
      const target = new Date(dateStr);
      if (Number.isNaN(target.getTime())) return "Sin fecha";
      const diffMs = Date.now() - target.getTime();
      const diffMinutes = Math.max(Math.round(diffMs / 6e4), 0);
      if (diffMinutes < 1) return "Hace unos segundos";
      if (diffMinutes < 60) return `Hace ${diffMinutes} min`;
      const diffHours = Math.round(diffMinutes / 60);
      if (diffHours < 24) return `Hace ${diffHours} h`;
      const diffDays = Math.round(diffHours / 24);
      if (diffDays < 30) return `Hace ${diffDays} d`;
      return target.toLocaleDateString("es-PE", { day: "2-digit", month: "short" });
    }
    function createMonthlySeries(items) {
      const now = /* @__PURE__ */ new Date();
      const months = Array.from({ length: 6 }, (_, index) => {
        const date = new Date(now.getFullYear(), now.getMonth() - (5 - index), 1);
        const label = date.toLocaleDateString("es-PE", { month: "short" }).replace(".", "").toUpperCase();
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
      if (variant === "approved") {
        return {
          icon: Circle_check_big,
          title: "Cotizacion aprobada",
          tone: "bg-emerald-50 text-emerald-700"
        };
      }
      if (variant === "cancelled") {
        return {
          icon: Circle_alert,
          title: "Cotizacion observada",
          tone: "bg-red-50 text-red-700"
        };
      }
      return {
        icon: File_text,
        title: "Nueva cotizacion creada",
        tone: "bg-amber-50 text-amber-700"
      };
    }
    function formatDelta(value) {
      return `+${Math.max(0, Math.round(value))}%`;
    }
    approvedCount = cotizaciones.filter((cotizacion) => normalizeStatus(cotizacion?.estado) === "approved").length;
    pendingCount = cotizaciones.filter((cotizacion) => normalizeStatus(cotizacion?.estado) === "pending").length;
    quoteCount = cotizaciones.length;
    activeProducts = Array.isArray(statsData.top_productos) ? statsData.top_productos.length : 0;
    approvalRatio = quoteCount > 0 ? approvedCount / quoteCount * 100 : 0;
    pendingRatio = quoteCount > 0 ? pendingCount / quoteCount * 100 : 0;
    outsourcingRatio = Number(0) > 0 ? Number(0) / Number(1) * 100 : 0;
    [
      {
        title: "Ingresos cobrados",
        value: formatCurrency(statsData.ingresos_totales),
        delta: formatDelta(approvalRatio),
        caption: "Cobro consolidado",
        icon: Calculator
      },
      {
        title: "Saldos por cobrar",
        value: formatCurrency(statsData.saldos_por_cobrar),
        delta: formatDelta(pendingRatio),
        caption: "Pipeline pendiente",
        icon: File_text
      },
      {
        title: "Costo tercerizado",
        value: formatCurrency(statsData.costos_tercerizacion),
        delta: formatDelta(outsourcingRatio),
        caption: "Carga operativa externa",
        icon: Truck
      },
      {
        title: "Cotizaciones monitoreadas",
        value: formatCompact(quoteCount),
        delta: formatDelta(activeProducts * 4),
        caption: "Base reciente de analisis",
        icon: Package
      }
    ];
    chartSeries = createMonthlySeries(cotizaciones);
    maxRevenue = Math.max(...chartSeries.map((point) => point.revenue), 1);
    maxQuotes = Math.max(...chartSeries.map((point) => point.quotes), 1);
    chartDots = chartSeries.map((point, index) => {
      const chartWidth = 560;
      const leftPadding = 28;
      const usableWidth = chartWidth - leftPadding * 2;
      const x = chartSeries.length > 1 ? leftPadding + usableWidth / (chartSeries.length - 1) * index : chartWidth / 2;
      const y = 182 - point.revenue / maxRevenue * 126;
      return { ...point, x, y };
    });
    chartLinePoints = chartDots.map((point) => `${point.x},${point.y}`).join(" ");
    cotizaciones.slice().sort((a, b) => new Date(b.fecha_emision || 0).getTime() - new Date(a.fecha_emision || 0).getTime()).slice(0, 5).map((cotizacion) => {
      const meta = getActivityMeta(cotizacion);
      return {
        ...meta,
        client: cotizacion?.cliente?.razon_social || "Cliente sin nombre",
        document: `${cotizacion?.serie || "COT"}-${String(cotizacion?.correlativo || 0).padStart(6, "0")}`,
        amount: formatCurrency(cotizacion?.total_venta),
        timestamp: formatRelativeTime(cotizacion?.fecha_emision)
      };
    });
    $$renderer2.push(`<div class="space-y-6"><section class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between"><div class="space-y-2"><p${attr_class(clsx(pageEyebrowClass))}>Centro analitico</p> <div class="space-y-1"><h1${attr_class(clsx(pageTitleClass))}>Dashboard</h1> <p${attr_class(`max-w-2xl ${pageSubtitleClass}`)}>Una lectura ejecutiva del negocio con ingresos, documentos y movimiento operativo reciente.</p></div></div> <button${attr_class(`inline-flex items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-medium ${premiumSecondaryButtonClass}`)}>`);
    Calendar_days($$renderer2, { class: "h-4 w-4 text-slate-500", strokeWidth: 2 });
    $$renderer2.push(`<!----> <span>Ultimos 30 dias</span></button></section> `);
    {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--> <section class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">`);
    {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<!--[-->`);
      const each_array = ensure_array_like(Array(4));
      for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
        each_array[$$index];
        $$renderer2.push(`<div${attr_class(`h-40 animate-pulse rounded-[28px] ${glassPanelClass}`)}></div>`);
      }
      $$renderer2.push(`<!--]-->`);
    }
    $$renderer2.push(`<!--]--></section> <section class="grid gap-6 xl:grid-cols-[minmax(0,1.7fr)_minmax(320px,1fr)]"><article${attr_class(`rounded-[30px] p-5 ${glassPanelStrongClass}`)}><div class="mb-6 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between"><div class="space-y-1"><p class="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Panorama principal</p> <h2 class="text-lg font-semibold tracking-tight text-slate-900">Ingresos vs Cotizaciones</h2> <p class="text-sm leading-6 text-slate-500">Vista consolidada del volumen reciente de documentos frente al valor comercial generado.</p></div> <div class="flex flex-wrap gap-3 text-xs font-semibold text-slate-500"><span class="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1.5"><span class="h-2.5 w-2.5 rounded-full bg-slate-300"></span> Cotizaciones</span> <span class="inline-flex items-center gap-2 rounded-full bg-emerald-50 px-3 py-1.5 text-emerald-700"><span class="h-2.5 w-2.5 rounded-full bg-emerald-500"></span> Ingresos</span></div></div> <div${attr_class(`relative overflow-hidden rounded-[28px] p-5 ${mutedGlassPanelClass}`)}><div class="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_right,_rgba(16,185,129,0.10),_transparent_38%)]"></div> `);
    if (quoteCount === 0) {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<div class="flex h-[320px] flex-col items-center justify-center gap-4 text-center"><div class="rounded-2xl border border-slate-200 bg-white p-4 text-slate-400 shadow-sm">`);
      Calculator($$renderer2, { class: "h-8 w-8", strokeWidth: 1.8 });
      $$renderer2.push(`<!----></div> <div class="space-y-2"><p class="text-sm font-semibold text-slate-900">Sin movimiento suficiente para el grafico</p> <p class="max-w-md text-sm leading-6 text-slate-500">En cuanto entren nuevas cotizaciones, este panel mostrara la relacion entre ingresos y volumen comercial.</p></div></div>`);
    } else {
      $$renderer2.push("<!--[-1-->");
      $$renderer2.push(`<div class="relative h-[320px]"><div class="absolute inset-0"><!--[-->`);
      const each_array_2 = ensure_array_like([0, 1, 2, 3]);
      for (let $$index_2 = 0, $$length = each_array_2.length; $$index_2 < $$length; $$index_2++) {
        let step = each_array_2[$$index_2];
        $$renderer2.push(`<div class="absolute inset-x-0 border-t border-dashed border-slate-200"${attr_style(`top: ${step * 25}%`)}></div>`);
      }
      $$renderer2.push(`<!--]--></div> <div class="absolute inset-x-4 bottom-12 top-8 grid grid-cols-6 items-end gap-4"><!--[-->`);
      const each_array_3 = ensure_array_like(chartSeries);
      for (let $$index_3 = 0, $$length = each_array_3.length; $$index_3 < $$length; $$index_3++) {
        let point = each_array_3[$$index_3];
        $$renderer2.push(`<div class="flex h-full flex-col justify-end gap-3"><div class="mx-auto w-full max-w-[56px] rounded-t-2xl bg-slate-200/90 transition-all duration-300"><div class="w-full rounded-t-2xl bg-slate-300/80"${attr_style(`height: ${Math.max(point.quotes / maxQuotes * 160, point.quotes ? 24 : 10)}px`)}></div></div></div>`);
      }
      $$renderer2.push(`<!--]--></div> <svg viewBox="0 0 560 220" class="absolute inset-x-4 top-4 h-[72%] w-auto overflow-visible"><polyline${attr("points", chartLinePoints)} fill="none" stroke="rgb(5 150 105)" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"></polyline><!--[-->`);
      const each_array_4 = ensure_array_like(chartDots);
      for (let $$index_4 = 0, $$length = each_array_4.length; $$index_4 < $$length; $$index_4++) {
        let point = each_array_4[$$index_4];
        $$renderer2.push(`<circle${attr("cx", point.x)}${attr("cy", point.y)} r="6" fill="white" stroke="rgb(5 150 105)" stroke-width="3"></circle>`);
      }
      $$renderer2.push(`<!--]--></svg> <div class="absolute inset-x-4 bottom-0 grid grid-cols-6 gap-4"><!--[-->`);
      const each_array_5 = ensure_array_like(chartSeries);
      for (let $$index_5 = 0, $$length = each_array_5.length; $$index_5 < $$length; $$index_5++) {
        let point = each_array_5[$$index_5];
        $$renderer2.push(`<div class="space-y-1 text-center"><p class="text-xs font-semibold text-slate-600">${escape_html(point.label)}</p> <p class="text-[11px] text-slate-400">${escape_html(point.quotes)} docs</p></div>`);
      }
      $$renderer2.push(`<!--]--></div></div>`);
    }
    $$renderer2.push(`<!--]--></div></article> <article${attr_class(`rounded-[30px] p-5 ${glassPanelStrongClass}`)}><div class="mb-5 space-y-1"><p class="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Pulso comercial</p> <h2 class="text-lg font-semibold tracking-tight text-slate-900">Actividad reciente</h2> <p class="text-sm leading-6 text-slate-500">Eventos recientes vinculados al flujo comercial y al estado de las cotizaciones.</p></div> <div class="space-y-3">`);
    {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<!--[-->`);
      const each_array_6 = ensure_array_like(Array(5));
      for (let $$index_6 = 0, $$length = each_array_6.length; $$index_6 < $$length; $$index_6++) {
        each_array_6[$$index_6];
        $$renderer2.push(`<div${attr_class(`h-20 animate-pulse rounded-2xl ${mutedGlassPanelClass}`)}></div>`);
      }
      $$renderer2.push(`<!--]-->`);
    }
    $$renderer2.push(`<!--]--></div> `);
    {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--></article></section></div>`);
  });
}
export {
  _page as default
};
