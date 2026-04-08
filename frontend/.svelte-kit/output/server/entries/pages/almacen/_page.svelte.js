import { d as attr_class, m as clsx, f as escape_html, e as attr, h as ensure_array_like, j as stringify } from "../../../chunks/index2.js";
import "@sveltejs/kit/internal";
import "../../../chunks/url.js";
import "../../../chunks/utils.js";
import "@sveltejs/kit/internal/server";
import "../../../chunks/root.js";
import "../../../chunks/exports.js";
import "../../../chunks/state.svelte.js";
import { e as pageEyebrowClass, f as pageTitleClass, h as pageSubtitleClass, p as premiumSecondaryButtonClass, i as premiumPrimaryButtonClass, b as glassPanelClass, g as glassPanelStrongClass, a as premiumInputClass } from "../../../chunks/uiClasses.js";
import { U as Upload } from "../../../chunks/upload.js";
import { P as Plus } from "../../../chunks/plus.js";
import { S as Search } from "../../../chunks/search.js";
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let criticalCount, averageCost;
    const typeFilters = [
      { id: "todos", label: "Todos" },
      { id: "pliegos", label: "Pliegos" },
      { id: "tintas", label: "Tintas" },
      { id: "acabados", label: "Acabados" }
    ];
    let saving = false;
    let search = "";
    let activeFilter = "todos";
    let insumos = [];
    let form = createInitialForm();
    function createInitialForm() {
      return {
        nombre: "",
        unidad_compra: "Resma",
        unidad_consumo: "Pliego",
        factor_conversion: "1",
        costo_promedio: "0",
        stock_actual: "0",
        umbral_minimo: "50"
      };
    }
    function normalizeText(value) {
      return `${value || ""}`.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").trim();
    }
    function classifyInsumo(nombre) {
      const value = normalizeText(nombre);
      if ([
        "papel",
        "pliego",
        "resma",
        "couche",
        "bond",
        "kraft",
        "cartulina"
      ].some((keyword) => value.includes(keyword))) {
        return "pliegos";
      }
      if ([
        "tinta",
        "toner",
        "cyan",
        "magenta",
        "amarillo",
        "black",
        "negro"
      ].some((keyword) => value.includes(keyword))) {
        return "tintas";
      }
      if ([
        "laminado",
        "barniz",
        "troquel",
        "foil",
        "hot",
        "acabado",
        "anillado"
      ].some((keyword) => value.includes(keyword))) {
        return "acabados";
      }
      return "otros";
    }
    function formatDecimal(value, digits = 2) {
      return new Intl.NumberFormat("es-PE", { minimumFractionDigits: digits, maximumFractionDigits: digits }).format(Number(value || 0));
    }
    function getFilterCount(filterId) {
      return insumos.filter((insumo) => filterId === "todos" || classifyInsumo(insumo.nombre) === filterId).length;
    }
    insumos.filter((insumo) => {
      const matchesType = activeFilter === "todos";
      const term = normalizeText(search);
      if (!term) return matchesType;
      const haystack = [insumo.nombre, insumo.unidad_compra, insumo.unidad_consumo].filter(Boolean).map(normalizeText);
      return haystack.some((value) => value.includes(term));
    });
    criticalCount = insumos.filter((insumo) => Number(insumo.stock_actual || 0) <= Number(insumo.umbral_minimo || 0)).length;
    averageCost = insumos.length > 0 ? insumos.reduce((sum, insumo) => sum + Number(insumo.costo_promedio || 0), 0) / insumos.length : 0;
    $$renderer2.push(`<div class="space-y-6"><section class="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between"><div class="space-y-2"><p${attr_class(clsx(pageEyebrowClass))}>Gestión de inventario</p> <div class="space-y-1"><h1${attr_class(clsx(pageTitleClass))}>Almacén</h1> <p${attr_class(`max-w-3xl ${pageSubtitleClass}`)}>Controla materias primas, detecta quiebres de stock y mantén listo el catálogo operativo para producción y compras.</p></div></div> <div class="flex flex-col gap-3 sm:flex-row"><button type="button"${attr_class(`inline-flex items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-medium ${premiumSecondaryButtonClass}`)}>`);
    Upload($$renderer2, { class: "h-4 w-4", strokeWidth: 2 });
    $$renderer2.push(`<!----> <span>OCR de compras</span></button> <button type="button"${attr_class(`inline-flex items-center justify-center gap-2 rounded-xl px-5 py-3 text-sm font-semibold ${premiumPrimaryButtonClass}`)}>`);
    Plus($$renderer2, { class: "h-4 w-4", strokeWidth: 2.2 });
    $$renderer2.push(`<!----> <span>Nuevo insumo</span></button></div></section> <section class="grid gap-4 md:grid-cols-3"><article${attr_class(`rounded-[30px] p-5 ${glassPanelClass}`)}><p class="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">SKU operativos</p> <p class="mt-3 text-3xl font-bold tracking-tight text-slate-900">${escape_html(insumos.length)}</p> <p class="mt-2 text-sm text-slate-500">Insumos activos disponibles para planificación y consumo.</p></article> <article class="rounded-[30px] border border-red-100/70 bg-white/85 p-5 shadow-[0_18px_40px_rgba(239,68,68,0.08)] backdrop-blur-xl"><p class="text-xs font-semibold uppercase tracking-[0.22em] text-red-600">Stock crítico</p> <p class="mt-3 text-3xl font-bold tracking-tight text-red-700">${escape_html(criticalCount)}</p> <p class="mt-2 text-sm text-red-700/80">Items por debajo del mínimo que requieren reposición inmediata.</p></article> <article${attr_class(`rounded-[30px] p-5 ${glassPanelClass}`)}><p class="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Costo promedio</p> <p class="mt-3 text-3xl font-bold tracking-tight text-slate-900">S/ ${escape_html(formatDecimal(averageCost))}</p> <p class="mt-2 text-sm text-slate-500">Lectura rápida del ticket medio de materia prima en catálogo.</p></article></section> <section class="grid gap-6 xl:grid-cols-[minmax(0,1.35fr)_22rem]"><div class="space-y-4"><div${attr_class(`flex flex-col gap-3 rounded-[30px] p-5 lg:flex-row lg:items-center lg:justify-between ${glassPanelStrongClass}`)}><div class="relative max-w-xl flex-1">`);
    Search($$renderer2, {
      class: "pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400",
      strokeWidth: 1.9
    });
    $$renderer2.push(`<!----> <input${attr("value", search)} type="text" placeholder="Buscar por insumo o unidad..."${attr_class(`h-11 w-full rounded-2xl pl-11 pr-4 text-sm text-slate-700 ${premiumInputClass}`)}/></div> <div class="flex flex-wrap gap-2"><!--[-->`);
    const each_array = ensure_array_like(typeFilters);
    for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
      let filter = each_array[$$index];
      $$renderer2.push(`<button type="button"${attr_class(`inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-medium transition-all duration-200 ${stringify(activeFilter === filter.id ? "border-emerald-200 bg-emerald-50 text-emerald-700 shadow-sm" : "border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-100 hover:text-slate-900")}`)}><span>${escape_html(filter.label)}</span> <span${attr_class(`rounded-full px-2 py-0.5 text-[11px] font-semibold ${stringify(activeFilter === filter.id ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-500")}`)}>${escape_html(getFilterCount(filter.id))}</span></button>`);
    }
    $$renderer2.push(`<!--]--></div></div> <section${attr_class(`overflow-hidden rounded-[30px] ${glassPanelStrongClass}`)}>`);
    {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<div class="overflow-x-auto" aria-hidden="true"><table class="min-w-full border-separate border-spacing-0"><thead><tr class="bg-slate-50/60"><th class="px-6 pb-3 pt-5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Insumo</th><th class="px-6 pb-3 pt-5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Unidades</th><th class="px-6 pb-3 pt-5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Stock</th><th class="px-6 pb-3 pt-5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Costo</th><th class="px-6 pb-3 pt-5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Estado</th><th class="px-6 pb-3 pt-5 text-right text-xs font-semibold uppercase tracking-wider text-slate-500">Acciones</th></tr></thead><tbody><!--[-->`);
      const each_array_1 = ensure_array_like(Array.from({ length: 6 }, (_, index) => index));
      for (let index = 0, $$length = each_array_1.length; index < $$length; index++) {
        each_array_1[index];
        $$renderer2.push(`<tr class="animate-pulse"><td${attr_class(`px-6 py-4 ${stringify(index === 5 ? "border-b-0" : "border-b border-slate-200/70")}`)}><div class="h-4 w-40 rounded-full bg-slate-200"></div></td><td${attr_class(`px-6 py-4 ${stringify(index === 5 ? "border-b-0" : "border-b border-slate-200/70")}`)}><div class="h-4 w-28 rounded-full bg-slate-200"></div></td><td${attr_class(`px-6 py-4 ${stringify(index === 5 ? "border-b-0" : "border-b border-slate-200/70")}`)}><div class="h-4 w-24 rounded-full bg-slate-200"></div></td><td${attr_class(`px-6 py-4 ${stringify(index === 5 ? "border-b-0" : "border-b border-slate-200/70")}`)}><div class="h-4 w-20 rounded-full bg-slate-200"></div></td><td${attr_class(`px-6 py-4 ${stringify(index === 5 ? "border-b-0" : "border-b border-slate-200/70")}`)}><div class="h-7 w-24 rounded-full bg-slate-100"></div></td><td${attr_class(`px-6 py-4 text-right ${stringify(index === 5 ? "border-b-0" : "border-b border-slate-200/70")}`)}><div class="ml-auto h-4 w-16 rounded-full bg-slate-200"></div></td></tr>`);
      }
      $$renderer2.push(`<!--]--></tbody></table></div>`);
    }
    $$renderer2.push(`<!--]--></section></div> <aside${attr_class(`rounded-[30px] p-5 ${glassPanelStrongClass}`)}><div class="space-y-5"><div class="space-y-1"><p class="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">${escape_html("Alta rápida")}</p> <h2 class="text-lg font-semibold tracking-tight text-slate-900">${escape_html("Nuevo insumo")}</h2></div> <div class="space-y-4"><div class="space-y-2"><label class="block text-xs font-semibold uppercase tracking-[0.22em] text-slate-500" for="nombre-insumo">Nombre</label> <input id="nombre-insumo"${attr("value", form.nombre)} type="text" placeholder="Ej. Pliego couché 250g"${attr_class(`h-11 w-full rounded-2xl px-4 text-sm text-slate-700 ${premiumInputClass}`)}/></div> <div class="grid grid-cols-2 gap-3"><div class="space-y-2"><label class="block text-xs font-semibold uppercase tracking-[0.22em] text-slate-500" for="unidad-compra">Unidad compra</label> <input id="unidad-compra"${attr("value", form.unidad_compra)} type="text"${attr_class(`h-11 w-full rounded-2xl px-4 text-sm text-slate-700 ${premiumInputClass}`)}/></div> <div class="space-y-2"><label class="block text-xs font-semibold uppercase tracking-[0.22em] text-slate-500" for="unidad-consumo">Unidad consumo</label> <input id="unidad-consumo"${attr("value", form.unidad_consumo)} type="text"${attr_class(`h-11 w-full rounded-2xl px-4 text-sm text-slate-700 ${premiumInputClass}`)}/></div></div> <div class="grid grid-cols-2 gap-3"><div class="space-y-2"><label class="block text-xs font-semibold uppercase tracking-[0.22em] text-slate-500" for="factor-conversion">Factor conversión</label> <input id="factor-conversion"${attr("value", form.factor_conversion)} type="number" min="0.0001" step="0.0001"${attr_class(`h-11 w-full rounded-2xl px-4 text-sm text-slate-700 ${premiumInputClass}`)}/></div> <div class="space-y-2"><label class="block text-xs font-semibold uppercase tracking-[0.22em] text-slate-500" for="costo-promedio">Costo promedio</label> <input id="costo-promedio"${attr("value", form.costo_promedio)} type="number" min="0" step="0.01"${attr_class(`h-11 w-full rounded-2xl px-4 text-sm text-slate-700 ${premiumInputClass}`)}/></div></div> <div class="grid grid-cols-2 gap-3"><div class="space-y-2"><label class="block text-xs font-semibold uppercase tracking-[0.22em] text-slate-500" for="stock-actual">Stock actual</label> <input id="stock-actual"${attr("value", form.stock_actual)} type="number" min="0" step="0.01"${attr_class(`h-11 w-full rounded-2xl px-4 text-sm text-slate-700 ${premiumInputClass}`)}/></div> <div class="space-y-2"><label class="block text-xs font-semibold uppercase tracking-[0.22em] text-slate-500" for="umbral-minimo">Stock mínimo</label> <input id="umbral-minimo"${attr("value", form.umbral_minimo)} type="number" min="0" step="0.01"${attr_class(`h-11 w-full rounded-2xl px-4 text-sm text-slate-700 ${premiumInputClass}`)}/></div></div></div> `);
    {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--> <div class="flex flex-col gap-3"><button type="button"${attr("disabled", saving, true)}${attr_class(`inline-flex items-center justify-center rounded-xl px-4 py-3 text-sm font-semibold ${premiumPrimaryButtonClass} disabled:cursor-not-allowed disabled:opacity-70`)}>${escape_html("Crear insumo")}</button> `);
    {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--></div></div></aside></section></div>`);
  });
}
export {
  _page as default
};
