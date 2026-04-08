import { s as sanitize_props, a as spread_props, b as slot, e as attr, h as ensure_array_like } from "../../../chunks/index2.js";
import { I as Icon } from "../../../chunks/Icon.js";
import { P as Package } from "../../../chunks/package.js";
import { C as Circle_check_big } from "../../../chunks/circle-check-big.js";
import { S as Search } from "../../../chunks/search.js";
function Layers($$renderer, $$props) {
  const $$sanitized_props = sanitize_props($$props);
  const iconNode = [
    [
      "path",
      {
        "d": "M12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83z"
      }
    ],
    [
      "path",
      {
        "d": "M2 12a1 1 0 0 0 .58.91l8.6 3.91a2 2 0 0 0 1.65 0l8.58-3.9A1 1 0 0 0 22 12"
      }
    ],
    [
      "path",
      {
        "d": "M2 17a1 1 0 0 0 .58.91l8.6 3.91a2 2 0 0 0 1.65 0l8.58-3.9A1 1 0 0 0 22 17"
      }
    ]
  ];
  Icon($$renderer, spread_props([
    { name: "layers" },
    $$sanitized_props,
    {
      /**
       * @component @name Layers
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cGF0aCBkPSJNMTIuODMgMi4xOGEyIDIgMCAwIDAtMS42NiAwTDIuNiA2LjA4YTEgMSAwIDAgMCAwIDEuODNsOC41OCAzLjkxYTIgMiAwIDAgMCAxLjY2IDBsOC41OC0zLjlhMSAxIDAgMCAwIDAtMS44M3oiIC8+CiAgPHBhdGggZD0iTTIgMTJhMSAxIDAgMCAwIC41OC45MWw4LjYgMy45MWEyIDIgMCAwIDAgMS42NSAwbDguNTgtMy45QTEgMSAwIDAgMCAyMiAxMiIgLz4KICA8cGF0aCBkPSJNMiAxN2ExIDEgMCAwIDAgLjU4LjkxbDguNiAzLjkxYTIgMiAwIDAgMCAxLjY1IDBsOC41OC0zLjlBMSAxIDAgMCAwIDIyIDE3IiAvPgo8L3N2Zz4K) - https://lucide.dev/icons/layers
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
    let cotizacionMap, filteredOrders;
    let ordenes = [];
    let cotizaciones = [];
    let searchTerm = "";
    const columns = [
      {
        id: "preprensa",
        title: "Pre-prensa",
        subtitle: "Validacion y cola",
        icon: Layers
      },
      {
        id: "impresion",
        title: "Impresion",
        subtitle: "Maquina o proveedor",
        icon: Package
      },
      {
        id: "acabado",
        title: "Acabado",
        subtitle: "Cierre y entrega",
        icon: Circle_check_big
      }
    ];
    function getStage(order) {
      if (order?.estado === "finalizada") return "acabado";
      if (order?.estado === "en_proceso") return "impresion";
      return "preprensa";
    }
    function getStateLabel(order) {
      if (order?.estado === "finalizada") return "Lista para entrega";
      if (order?.estado === "en_proceso") return order?.tipo_produccion === "tercerizada" ? "Produccion externa" : "En impresion";
      return "Esperando liberacion";
    }
    function getQuote(order) {
      return cotizacionMap.get(`${order?.cotizacion_id}`) || null;
    }
    function getClientName(order) {
      return getQuote(order)?.cliente?.razon_social || "Cliente no disponible";
    }
    function matchesSearch(order) {
      const term = searchTerm.trim().toLowerCase();
      if (!term) return true;
      const quote = getQuote(order);
      const haystack = [
        `OP-${order?.id || ""}`,
        `COT-${order?.cotizacion_id || ""}`,
        getClientName(order),
        quote?.cliente?.numero_documento,
        order?.proveedor?.razon_social,
        order?.tipo_produccion,
        getStateLabel(order)
      ].filter(Boolean).join(" ").toLowerCase();
      return haystack.includes(term);
    }
    cotizacionMap = new Map(cotizaciones.map((cotizacion) => [`${cotizacion.id}`, cotizacion]));
    filteredOrders = ordenes.filter(matchesSearch);
    columns.map((column) => ({
      ...column,
      items: filteredOrders.filter((order) => getStage(order) === column.id)
    }));
    $$renderer2.push(`<div class="space-y-6"><section class="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between"><div class="space-y-2"><p class="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Centro operativo</p> <div class="space-y-1"><h1 class="text-2xl font-bold tracking-tight text-slate-900">Produccion</h1> <p class="max-w-2xl text-sm leading-6 text-slate-500">Gestiona el flujo de ordenes y detecta rapido los cuellos de botella entre pre-prensa, impresion y acabado.</p></div></div> <div class="flex flex-col gap-3 sm:flex-row"><div class="relative">`);
    Search($$renderer2, {
      class: "pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400",
      strokeWidth: 1.9
    });
    $$renderer2.push(`<!----> <input type="text"${attr("value", searchTerm)} placeholder="Buscar por OP, cliente o proveedor..." class="h-12 w-full min-w-[280px] rounded-xl border border-slate-200 bg-white pl-11 pr-4 text-sm text-slate-700 outline-none transition-all duration-200 placeholder:text-slate-400 focus:border-emerald-500 focus:ring-4 focus:ring-emerald-500/10"/></div> <button class="inline-flex items-center justify-center rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm font-medium text-slate-700 shadow-sm transition-colors hover:bg-slate-50">Actualizar</button></div></section> `);
    {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--> `);
    {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<section class="grid gap-5 xl:grid-cols-3"><!--[-->`);
      const each_array = ensure_array_like(Array(3));
      for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
        each_array[$$index];
        $$renderer2.push(`<div class="min-h-[520px] animate-pulse rounded-2xl border border-slate-200 bg-slate-100/50"></div>`);
      }
      $$renderer2.push(`<!--]--></section>`);
    }
    $$renderer2.push(`<!--]--></div>`);
  });
}
export {
  _page as default
};
