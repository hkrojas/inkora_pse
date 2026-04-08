import { s as sanitize_props, a as spread_props, b as slot, f as escape_html, h as ensure_array_like, d as attr_class, n as attr_style, j as stringify } from "../../../chunks/index2.js";
import "../../../chunks/auth.js";
import "@sveltejs/kit/internal";
import "../../../chunks/url.js";
import "../../../chunks/utils.js";
import "@sveltejs/kit/internal/server";
import "../../../chunks/root.js";
import "../../../chunks/exports.js";
import "../../../chunks/state.svelte.js";
import { I as Icon } from "../../../chunks/Icon.js";
import { B as Building_2 } from "../../../chunks/building-2.js";
import { C as Credit_card } from "../../../chunks/credit-card.js";
import { S as Search } from "../../../chunks/search.js";
import { C as Circle_alert } from "../../../chunks/circle-alert.js";
function Circle_check($$renderer, $$props) {
  const $$sanitized_props = sanitize_props($$props);
  const iconNode = [
    ["circle", { "cx": "12", "cy": "12", "r": "10" }],
    ["path", { "d": "m9 12 2 2 4-4" }]
  ];
  Icon($$renderer, spread_props([
    { name: "circle-check" },
    $$sanitized_props,
    {
      /**
       * @component @name CircleCheck
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8Y2lyY2xlIGN4PSIxMiIgY3k9IjEyIiByPSIxMCIgLz4KICA8cGF0aCBkPSJtOSAxMiAyIDIgNC00IiAvPgo8L3N2Zz4K) - https://lucide.dev/icons/circle-check
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
function Clock($$renderer, $$props) {
  const $$sanitized_props = sanitize_props($$props);
  const iconNode = [
    ["circle", { "cx": "12", "cy": "12", "r": "10" }],
    ["path", { "d": "M12 6v6l4 2" }]
  ];
  Icon($$renderer, spread_props([
    { name: "clock" },
    $$sanitized_props,
    {
      /**
       * @component @name Clock
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8Y2lyY2xlIGN4PSIxMiIgY3k9IjEyIiByPSIxMCIgLz4KICA8cGF0aCBkPSJNMTIgNnY2bDQgMiIgLz4KPC9zdmc+Cg==) - https://lucide.dev/icons/clock
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
function File_check($$renderer, $$props) {
  const $$sanitized_props = sanitize_props($$props);
  const iconNode = [
    [
      "path",
      {
        "d": "M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z"
      }
    ],
    ["path", { "d": "M14 2v5a1 1 0 0 0 1 1h5" }],
    ["path", { "d": "m9 15 2 2 4-4" }]
  ];
  Icon($$renderer, spread_props([
    { name: "file-check" },
    $$sanitized_props,
    {
      /**
       * @component @name FileCheck
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cGF0aCBkPSJNNiAyMmEyIDIgMCAwIDEtMi0yVjRhMiAyIDAgMCAxIDItMmg4YTIuNCAyLjQgMCAwIDEgMS43MDQuNzA2bDMuNTg4IDMuNTg4QTIuNCAyLjQgMCAwIDEgMjAgOHYxMmEyIDIgMCAwIDEtMiAyeiIgLz4KICA8cGF0aCBkPSJNMTQgMnY1YTEgMSAwIDAgMCAxIDFoNSIgLz4KICA8cGF0aCBkPSJtOSAxNSAyIDIgNC00IiAvPgo8L3N2Zz4K) - https://lucide.dev/icons/file-check
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
function Shield_check($$renderer, $$props) {
  const $$sanitized_props = sanitize_props($$props);
  const iconNode = [
    [
      "path",
      {
        "d": "M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"
      }
    ],
    ["path", { "d": "m9 12 2 2 4-4" }]
  ];
  Icon($$renderer, spread_props([
    { name: "shield-check" },
    $$sanitized_props,
    {
      /**
       * @component @name ShieldCheck
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cGF0aCBkPSJNMjAgMTNjMCA1LTMuNSA3LjUtNy42NiA4Ljk1YTEgMSAwIDAgMS0uNjctLjAxQzcuNSAyMC41IDQgMTggNCAxM1Y2YTEgMSAwIDAgMSAxLTFjMiAwIDQuNS0xLjIgNi4yNC0yLjcyYTEuMTcgMS4xNyAwIDAgMSAxLjUyIDBDMTQuNTEgMy44MSAxNyA1IDE5IDVhMSAxIDAgMCAxIDEgMXoiIC8+CiAgPHBhdGggZD0ibTkgMTIgMiAyIDQtNCIgLz4KPC9zdmc+Cg==) - https://lucide.dev/icons/shield-check
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
function Square_pen($$renderer, $$props) {
  const $$sanitized_props = sanitize_props($$props);
  const iconNode = [
    [
      "path",
      {
        "d": "M12 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"
      }
    ],
    [
      "path",
      {
        "d": "M18.375 2.625a1 1 0 0 1 3 3l-9.013 9.014a2 2 0 0 1-.853.505l-2.873.84a.5.5 0 0 1-.62-.62l.84-2.873a2 2 0 0 1 .506-.852z"
      }
    ]
  ];
  Icon($$renderer, spread_props([
    { name: "square-pen" },
    $$sanitized_props,
    {
      /**
       * @component @name SquarePen
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cGF0aCBkPSJNMTIgM0g1YTIgMiAwIDAgMC0yIDJ2MTRhMiAyIDAgMCAwIDIgMmgxNGEyIDIgMCAwIDAgMi0ydi03IiAvPgogIDxwYXRoIGQ9Ik0xOC4zNzUgMi42MjVhMSAxIDAgMCAxIDMgM2wtOS4wMTMgOS4wMTRhMiAyIDAgMCAxLS44NTMuNTA1bC0yLjg3My44NGEuNS41IDAgMCAxLS42Mi0uNjJsLjg0LTIuODczYTIgMiAwIDAgMSAuNTA2LS44NTJ6IiAvPgo8L3N2Zz4K) - https://lucide.dev/icons/square-pen
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
    let tenants = [];
    function getPlanColor(plan) {
      switch (plan?.toLowerCase()) {
        case "premium":
          return "text-purple-600 bg-purple-50 border-purple-100";
        case "pro":
          return "text-blue-600 bg-blue-50 border-blue-100";
        default:
          return "text-gray-600 bg-gray-50 border-gray-100";
      }
    }
    function isExpired(date) {
      if (!date) return false;
      return new Date(date) < /* @__PURE__ */ new Date();
    }
    $$renderer2.push(`<div class="p-8 max-w-7xl mx-auto space-y-8"><div class="flex flex-col md:flex-row md:items-center justify-between gap-4"><div><h1 class="text-3xl font-bold text-on-surface flex items-center gap-3">`);
    Shield_check($$renderer2, { class: "text-primary", size: 32 });
    $$renderer2.push(`<!----> Torre de Control SaaS</h1> <p class="text-on-surface-variant text-sm mt-1">Gestión global de imprentas, planes y cumplimiento SUNAT.</p></div> <div class="flex items-center gap-2 text-xs font-medium px-3 py-1.5 rounded-full bg-primary/10 text-primary uppercase tracking-wider">Superadmin Mode Active</div></div> <div class="grid grid-cols-1 md:grid-cols-3 gap-6"><div class="p-6 rounded-3xl bg-surface-container-low border border-outline-variant/10"><div class="flex items-center gap-4"><div class="p-3 rounded-2xl bg-primary/10 text-primary">`);
    Building_2($$renderer2, { size: 24 });
    $$renderer2.push(`<!----></div> <div><p class="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Total Imprentas</p> <p class="text-2xl font-black text-on-surface">${escape_html(tenants.length)}</p></div></div></div> <div class="p-6 rounded-3xl bg-surface-container-low border border-outline-variant/10"><div class="flex items-center gap-4"><div class="p-3 rounded-2xl bg-secondary/10 text-secondary">`);
    File_check($$renderer2, { size: 24 });
    $$renderer2.push(`<!----></div> <div><p class="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Facturas del Mes</p> <p class="text-2xl font-black text-on-surface">${escape_html(tenants.reduce((acc, t) => acc + (t.invoices_used || 0), 0))}</p></div></div></div> <div class="p-6 rounded-3xl bg-surface-container-low border border-outline-variant/10"><div class="flex items-center gap-4"><div class="p-3 rounded-2xl bg-tertiary/10 text-tertiary">`);
    Credit_card($$renderer2, { size: 24 });
    $$renderer2.push(`<!----></div> <div><p class="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Suscripciones Active</p> <p class="text-2xl font-black text-on-surface">${escape_html(tenants.filter((t) => t.plan_type !== "Free").length)}</p></div></div></div></div> <div class="bg-surface rounded-[2.5rem] border border-outline-variant/10 overflow-hidden shadow-sm"><div class="p-6 border-b border-outline-variant/5 flex items-center justify-between bg-surface-container-lowest/50"><h2 class="font-bold text-on-surface tracking-tight">Directorio de Clientes SaaS</h2> <div class="relative max-w-xs w-full">`);
    Search($$renderer2, {
      class: "absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant",
      size: 16
    });
    $$renderer2.push(`<!----> <input type="text" placeholder="Filtrar por RUC o Nombre..." class="w-full pl-10 pr-4 py-2 bg-surface-container-low border-none rounded-2xl text-xs focus:ring-2 focus:ring-primary/20"/></div></div> <div class="overflow-x-auto"><table class="w-full text-left border-collapse"><thead class="bg-surface-container-low/50"><tr><th class="px-6 py-4 text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Imprenta</th><th class="px-6 py-4 text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Plan &amp; Vencimiento</th><th class="px-6 py-4 text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Uso de Facturas</th><th class="px-6 py-4 text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">SUNAT Config</th><th class="px-6 py-4 text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Acciones</th></tr></thead><tbody class="divide-y divide-outline-variant/5"><!--[-->`);
    const each_array = ensure_array_like(tenants);
    for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
      let tenant = each_array[$$index];
      $$renderer2.push(`<tr class="hover:bg-surface-container-lowest transition-colors group"><td class="px-6 py-5"><div class="flex items-center gap-3"><div class="w-10 h-10 rounded-xl bg-surface-container-high flex items-center justify-center text-primary font-bold">${escape_html(tenant.business_name[0])}</div> <div class="flex flex-col"><span class="text-sm font-semibold text-on-surface group-hover:text-primary transition-colors">${escape_html(tenant.business_name)}</span> <span class="text-[10px] text-on-surface-variant">RUC: ${escape_html(tenant.business_ruc)}</span></div></div></td><td class="px-6 py-5"><div class="flex flex-col gap-1.5"><span${attr_class(`px-2 py-0.5 rounded-lg text-[10px] font-bold w-fit border ${getPlanColor(tenant.plan_type)}`)}>${escape_html(tenant.plan_type)}</span> <span${attr_class(`text-[10px] flex items-center gap-1 ${isExpired(tenant.plan_end_date) ? "text-error" : "text-on-surface-variant"}`)}>`);
      Clock($$renderer2, { size: 10 });
      $$renderer2.push(`<!----> ${escape_html(tenant.plan_end_date ? new Date(tenant.plan_end_date).toLocaleDateString() : "Sin fecha")}</span></div></td><td class="px-6 py-5"><div class="w-full max-w-[120px] space-y-1.5"><div class="flex justify-between text-[10px] font-medium"><span class="text-on-surface-variant">${escape_html(tenant.invoices_used || 0)} / ${escape_html(tenant.invoice_limit || 50)}</span> <span class="text-primary">${escape_html(Math.round(tenant.invoices_used / tenant.invoice_limit * 100) || 0)}%</span></div> <div class="h-1.5 w-full bg-surface-container-high rounded-full overflow-hidden"><div class="h-full bg-primary rounded-full"${attr_style(`width: ${stringify(Math.min(tenant.invoices_used / tenant.invoice_limit * 100, 100))}%`)}></div></div></div></td><td class="px-6 py-5">`);
      if (tenant.sunat_usuario_sol && tenant.sunat_cert_url) {
        $$renderer2.push("<!--[0-->");
        $$renderer2.push(`<div class="flex items-center gap-1.5 text-success font-bold text-[10px]">`);
        Circle_check($$renderer2, { size: 12 });
        $$renderer2.push(`<!----> LISTO</div>`);
      } else {
        $$renderer2.push("<!--[-1-->");
        $$renderer2.push(`<div class="flex items-center gap-1.5 text-error font-bold text-[10px]">`);
        Circle_alert($$renderer2, { size: 12 });
        $$renderer2.push(`<!----> PENDIENTE</div>`);
      }
      $$renderer2.push(`<!--]--></td><td class="px-6 py-5"><button class="p-2 rounded-xl bg-surface-container-low text-on-surface-variant hover:text-primary hover:bg-primary/10 transition-all border border-transparent hover:border-primary/20">`);
      Square_pen($$renderer2, { size: 16 });
      $$renderer2.push(`<!----></button></td></tr>`);
    }
    $$renderer2.push(`<!--]--></tbody></table></div></div></div> `);
    {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]-->`);
  });
}
export {
  _page as default
};
