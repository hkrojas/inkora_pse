import { d as attr_class, m as clsx, h as ensure_array_like } from "../../../chunks/index2.js";
import { e as pageEyebrowClass, f as pageTitleClass, h as pageSubtitleClass, b as glassPanelClass } from "../../../chunks/uiClasses.js";
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let filteredClientes, selectedClient, clientHistory;
    let search = "";
    let clientes = [];
    let cotizaciones = [];
    let selectedClientId = null;
    function normalizeText(value) {
      return `${value || ""}`.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").trim();
    }
    filteredClientes = clientes.filter((cliente) => {
      const term = normalizeText(search);
      if (!term) return true;
      return [
        cliente.razon_social,
        cliente.nombre_comercial,
        cliente.numero_documento,
        cliente.email,
        cliente.telefono
      ].filter(Boolean).map(normalizeText).some((value) => value.includes(term));
    });
    if (filteredClientes.length > 0 && !filteredClientes.some((cliente) => cliente.id === selectedClientId)) {
      selectedClientId = filteredClientes[0].id;
    }
    selectedClient = filteredClientes.find((cliente) => cliente.id === selectedClientId) || clientes.find((cliente) => cliente.id === selectedClientId) || null;
    clientHistory = selectedClient ? cotizaciones.filter((cotizacion) => cotizacion.cliente?.id === selectedClient.id).sort((a, b) => new Date(b.fecha_emision).getTime() - new Date(a.fecha_emision).getTime()) : [];
    clientHistory.reduce((sum, cotizacion) => sum + Number(cotizacion.total_venta || 0), 0);
    clientHistory.filter((cotizacion) => ["aprobada", "aprobado", "facturada", "emitida"].includes(`${cotizacion.estado || ""}`.toLowerCase())).length;
    clientHistory[0] || null;
    $$renderer2.push(`<div class="space-y-6"><section class="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between"><div class="space-y-2"><p${attr_class(clsx(pageEyebrowClass))}>CRM operativo</p> <div class="space-y-1"><h1${attr_class(clsx(pageTitleClass))}>Clientes</h1> <p${attr_class(`max-w-3xl ${pageSubtitleClass}`)}>Centraliza la ficha fiscal, el contacto operativo y el historial comercial de cada cuenta en una sola vista.</p></div></div></section> `);
    {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<section class="grid gap-6 xl:grid-cols-[22rem_minmax(0,1fr)]"><div${attr_class(`rounded-[30px] p-5 ${glassPanelClass}`)}><div class="h-11 w-full animate-pulse rounded-2xl bg-slate-100"></div> <div class="mt-4 space-y-3"><!--[-->`);
      const each_array = ensure_array_like(Array.from({ length: 6 }, (_, index) => index));
      for (let index = 0, $$length = each_array.length; index < $$length; index++) {
        each_array[index];
        $$renderer2.push(`<div class="animate-pulse rounded-2xl border border-slate-200 bg-slate-50 p-4"><div class="h-4 w-40 rounded-full bg-slate-200"></div> <div class="mt-3 h-3 w-24 rounded-full bg-slate-100"></div></div>`);
      }
      $$renderer2.push(`<!--]--></div></div> <div${attr_class(`rounded-[30px] p-6 ${glassPanelClass}`)}><div class="space-y-4"><div class="h-6 w-48 animate-pulse rounded-full bg-slate-200"></div> <div class="grid gap-4 md:grid-cols-2"><!--[-->`);
      const each_array_1 = ensure_array_like(Array.from({ length: 4 }, (_, index) => index));
      for (let index = 0, $$length = each_array_1.length; index < $$length; index++) {
        each_array_1[index];
        $$renderer2.push(`<div class="animate-pulse rounded-2xl border border-slate-200 bg-slate-50 p-5"><div class="h-3 w-24 rounded-full bg-slate-100"></div> <div class="mt-3 h-4 w-36 rounded-full bg-slate-200"></div></div>`);
      }
      $$renderer2.push(`<!--]--></div></div></div></section>`);
    }
    $$renderer2.push(`<!--]--></div>`);
  });
}
export {
  _page as default
};
