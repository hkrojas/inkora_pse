import { s as sanitize_props, a as spread_props, b as slot, f as escape_html, h as ensure_array_like } from "../../../chunks/index2.js";
import { I as Icon } from "../../../chunks/Icon.js";
import { B as Building_2 } from "../../../chunks/building-2.js";
import { F as File_text } from "../../../chunks/file-text.js";
import { Z as Zap } from "../../../chunks/zap.js";
import { C as Credit_card } from "../../../chunks/credit-card.js";
import { T as Triangle_alert } from "../../../chunks/triangle-alert.js";
import { C as Circle_check_big } from "../../../chunks/circle-check-big.js";
import { U as Users } from "../../../chunks/users.js";
function Activity($$renderer, $$props) {
  const $$sanitized_props = sanitize_props($$props);
  const iconNode = [
    [
      "path",
      {
        "d": "M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2"
      }
    ]
  ];
  Icon($$renderer, spread_props([
    { name: "activity" },
    $$sanitized_props,
    {
      /**
       * @component @name Activity
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cGF0aCBkPSJNMjIgMTJoLTIuNDhhMiAyIDAgMCAwLTEuOTMgMS40NmwtMi4zNSA4LjM2YS4yNS4yNSAwIDAgMS0uNDggMEw5LjI0IDIuMThhLjI1LjI1IDAgMCAwLS40OCAwbC0yLjM1IDguMzZBMiAyIDAgMCAxIDQuNDkgMTJIMiIgLz4KPC9zdmc+Cg==) - https://lucide.dev/icons/activity
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
function Trending_up($$renderer, $$props) {
  const $$sanitized_props = sanitize_props($$props);
  const iconNode = [
    ["path", { "d": "M16 7h6v6" }],
    ["path", { "d": "m22 7-8.5 8.5-5-5L2 17" }]
  ];
  Icon($$renderer, spread_props([
    { name: "trending-up" },
    $$sanitized_props,
    {
      /**
       * @component @name TrendingUp
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cGF0aCBkPSJNMTYgN2g2djYiIC8+CiAgPHBhdGggZD0ibTIyIDctOC41IDguNS01LTVMMiAxNyIgLz4KPC9zdmc+Cg==) - https://lucide.dev/icons/trending-up
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
    let stats = {
      totalTenants: 0,
      activeTenants: 0,
      activeSubscriptions: 0,
      sunatConfigured: 0
    };
    let recentActivity = [];
    function formatNumber(num) {
      return new Intl.NumberFormat("es-PE").format(0);
    }
    $$renderer2.push(`<div class="space-y-8"><div class="flex items-center justify-between"><div><h1 class="text-2xl font-bold text-white">Dashboard</h1> <p class="text-slate-500 text-sm">Resumen global del sistema</p></div> <div class="flex items-center gap-2 text-xs text-emerald-400 bg-emerald-500/10 px-3 py-1.5 rounded-full">`);
    Activity($$renderer2, { size: 14 });
    $$renderer2.push(`<!----> Sistema activo</div></div> <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4"><div class="bg-slate-900 rounded-2xl border border-slate-800 p-6 hover:border-emerald-500/30 transition-all"><div class="flex items-start justify-between"><div><p class="text-slate-500 text-xs font-medium uppercase tracking-wider">Total Empresas</p> <p class="text-3xl font-black text-white mt-2">${escape_html(formatNumber())}</p> <p class="text-emerald-400 text-xs mt-1 flex items-center gap-1">`);
    Trending_up($$renderer2, { size: 12 });
    $$renderer2.push(`<!----> ${escape_html(stats.activeTenants)} activas</p></div> <div class="p-3 rounded-xl bg-blue-500/10">`);
    Building_2($$renderer2, { class: "text-blue-400", size: 24 });
    $$renderer2.push(`<!----></div></div></div> <div class="bg-slate-900 rounded-2xl border border-slate-800 p-6 hover:border-emerald-500/30 transition-all"><div class="flex items-start justify-between"><div><p class="text-slate-500 text-xs font-medium uppercase tracking-wider">Facturas Emitidas</p> <p class="text-3xl font-black text-white mt-2">${escape_html(formatNumber())}</p> <p class="text-slate-400 text-xs mt-1">este mes</p></div> <div class="p-3 rounded-xl bg-purple-500/10">`);
    File_text($$renderer2, { class: "text-purple-400", size: 24 });
    $$renderer2.push(`<!----></div></div></div> <div class="bg-slate-900 rounded-2xl border border-slate-800 p-6 hover:border-emerald-500/30 transition-all"><div class="flex items-start justify-between"><div><p class="text-slate-500 text-xs font-medium uppercase tracking-wider">Suscripciones</p> <p class="text-3xl font-black text-white mt-2">${escape_html(stats.activeSubscriptions)}</p> <p class="text-emerald-400 text-xs mt-1 flex items-center gap-1">`);
    Zap($$renderer2, { size: 12 });
    $$renderer2.push(`<!----> Plan Pro/Premium</p></div> <div class="p-3 rounded-xl bg-emerald-500/10">`);
    Credit_card($$renderer2, { class: "text-emerald-400", size: 24 });
    $$renderer2.push(`<!----></div></div></div> <div class="bg-slate-900 rounded-2xl border border-slate-800 p-6 hover:border-emerald-500/30 transition-all"><div class="flex items-start justify-between"><div><p class="text-slate-500 text-xs font-medium uppercase tracking-wider">SUNAT</p> <p class="text-3xl font-black text-white mt-2">${escape_html(stats.sunatConfigured)}</p> <p class="text-amber-400 text-xs mt-1 flex items-center gap-1">`);
    Triangle_alert($$renderer2, { size: 12 });
    $$renderer2.push(`<!----> ${escape_html(stats.totalTenants - stats.sunatConfigured)} pendientes</p></div> <div class="p-3 rounded-xl bg-amber-500/10">`);
    Circle_check_big($$renderer2, { class: "text-amber-400", size: 24 });
    $$renderer2.push(`<!----></div></div></div></div> <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">`);
    {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--> <div class="bg-slate-900 rounded-2xl border border-slate-800 p-6 lg:col-span-2"><h3 class="text-white font-semibold mb-4">Actividad Reciente</h3> <div class="space-y-4"><!--[-->`);
    const each_array = ensure_array_like(recentActivity);
    for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
      let activity = each_array[$$index];
      $$renderer2.push(`<div class="flex items-center gap-4 p-3 rounded-xl bg-slate-800/50"><div class="p-2 rounded-lg bg-slate-700">`);
      if (activity.icon) {
        $$renderer2.push("<!--[-->");
        activity.icon($$renderer2, { class: "text-slate-400", size: 16 });
        $$renderer2.push("<!--]-->");
      } else {
        $$renderer2.push("<!--[!-->");
        $$renderer2.push("<!--]-->");
      }
      $$renderer2.push(`</div> <div class="flex-1"><p class="text-white text-sm">${escape_html(activity.message)}</p> <p class="text-slate-500 text-xs">${escape_html(activity.time)}</p></div></div>`);
    }
    $$renderer2.push(`<!--]--></div></div></div> <div class="bg-slate-900 rounded-2xl border border-slate-800 p-6"><h3 class="text-white font-semibold mb-4">Accesos Rápidos</h3> <div class="grid grid-cols-2 md:grid-cols-4 gap-4"><a href="/admin/tenants" class="p-4 rounded-xl bg-slate-800/50 hover:bg-slate-800 border border-slate-700 hover:border-emerald-500/30 transition-all text-center group">`);
    Building_2($$renderer2, {
      class: "text-slate-400 group-hover:text-emerald-400 mx-auto mb-2",
      size: 24
    });
    $$renderer2.push(`<!----> <p class="text-white text-sm font-medium">Gestionar Empresas</p></a> <a href="/admin/usuarios" class="p-4 rounded-xl bg-slate-800/50 hover:bg-slate-800 border border-slate-700 hover:border-emerald-500/30 transition-all text-center group">`);
    Users($$renderer2, {
      class: "text-slate-400 group-hover:text-emerald-400 mx-auto mb-2",
      size: 24
    });
    $$renderer2.push(`<!----> <p class="text-white text-sm font-medium">Usuarios</p></a> <a href="/admin/config" class="p-4 rounded-xl bg-slate-800/50 hover:bg-slate-800 border border-slate-700 hover:border-emerald-500/30 transition-all text-center group">`);
    Credit_card($$renderer2, {
      class: "text-slate-400 group-hover:text-emerald-400 mx-auto mb-2",
      size: 24
    });
    $$renderer2.push(`<!----> <p class="text-white text-sm font-medium">Planes y Precios</p></a> <a href="/admin/audit" class="p-4 rounded-xl bg-slate-800/50 hover:bg-slate-800 border border-slate-700 hover:border-emerald-500/30 transition-all text-center group">`);
    Activity($$renderer2, {
      class: "text-slate-400 group-hover:text-emerald-400 mx-auto mb-2",
      size: 24
    });
    $$renderer2.push(`<!----> <p class="text-white text-sm font-medium">Auditoría</p></a></div></div></div>`);
  });
}
export {
  _page as default
};
