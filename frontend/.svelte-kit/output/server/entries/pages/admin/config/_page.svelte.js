import { s as sanitize_props, a as spread_props, b as slot, h as ensure_array_like, f as escape_html, e as attr } from "../../../../chunks/index2.js";
import { C as Credit_card } from "../../../../chunks/credit-card.js";
import { Z as Zap } from "../../../../chunks/zap.js";
import { I as Icon } from "../../../../chunks/Icon.js";
function Save($$renderer, $$props) {
  const $$sanitized_props = sanitize_props($$props);
  const iconNode = [
    [
      "path",
      {
        "d": "M15.2 3a2 2 0 0 1 1.4.6l3.8 3.8a2 2 0 0 1 .6 1.4V19a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z"
      }
    ],
    ["path", { "d": "M17 21v-7a1 1 0 0 0-1-1H8a1 1 0 0 0-1 1v7" }],
    ["path", { "d": "M7 3v4a1 1 0 0 0 1 1h7" }]
  ];
  Icon($$renderer, spread_props([
    { name: "save" },
    $$sanitized_props,
    {
      /**
       * @component @name Save
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cGF0aCBkPSJNMTUuMiAzYTIgMiAwIDAgMSAxLjQuNmwzLjggMy44YTIgMiAwIDAgMSAuNiAxLjRWMTlhMiAyIDAgMCAxLTIgMkg1YTIgMiAwIDAgMS0yLTJWNWEyIDIgMCAwIDEgMi0yeiIgLz4KICA8cGF0aCBkPSJNMTcgMjF2LTdhMSAxIDAgMCAwLTEtMUg4YTEgMSAwIDAgMC0xIDF2NyIgLz4KICA8cGF0aCBkPSJNNyAzdjRhMSAxIDAgMCAwIDEgMWg3IiAvPgo8L3N2Zz4K) - https://lucide.dev/icons/save
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
function Settings($$renderer, $$props) {
  const $$sanitized_props = sanitize_props($$props);
  const iconNode = [
    [
      "path",
      {
        "d": "M9.671 4.136a2.34 2.34 0 0 1 4.659 0 2.34 2.34 0 0 0 3.319 1.915 2.34 2.34 0 0 1 2.33 4.033 2.34 2.34 0 0 0 0 3.831 2.34 2.34 0 0 1-2.33 4.033 2.34 2.34 0 0 0-3.319 1.915 2.34 2.34 0 0 1-4.659 0 2.34 2.34 0 0 0-3.32-1.915 2.34 2.34 0 0 1-2.33-4.033 2.34 2.34 0 0 0 0-3.831A2.34 2.34 0 0 1 6.35 6.051a2.34 2.34 0 0 0 3.319-1.915"
      }
    ],
    ["circle", { "cx": "12", "cy": "12", "r": "3" }]
  ];
  Icon($$renderer, spread_props([
    { name: "settings" },
    $$sanitized_props,
    {
      /**
       * @component @name Settings
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cGF0aCBkPSJNOS42NzEgNC4xMzZhMi4zNCAyLjM0IDAgMCAxIDQuNjU5IDAgMi4zNCAyLjM0IDAgMCAwIDMuMzE5IDEuOTE1IDIuMzQgMi4zNCAwIDAgMSAyLjMzIDQuMDMzIDIuMzQgMi4zNCAwIDAgMCAwIDMuODMxIDIuMzQgMi4zNCAwIDAgMS0yLjMzIDQuMDMzIDIuMzQgMi4zNCAwIDAgMC0zLjMxOSAxLjkxNSAyLjM0IDIuMzQgMCAwIDEtNC42NTkgMCAyLjM0IDIuMzQgMCAwIDAtMy4zMi0xLjkxNSAyLjM0IDIuMzQgMCAwIDEtMi4zMy00LjAzMyAyLjM0IDIuMzQgMCAwIDAgMC0zLjgzMUEyLjM0IDIuMzQgMCAwIDEgNi4zNSA2LjA1MWEyLjM0IDIuMzQgMCAwIDAgMy4zMTktMS45MTUiIC8+CiAgPGNpcmNsZSBjeD0iMTIiIGN5PSIxMiIgcj0iMyIgLz4KPC9zdmc+Cg==) - https://lucide.dev/icons/settings
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
    let saving = false;
    let plans = [
      {
        name: "Free",
        price: 0,
        invoice_limit: 50,
        features: ["50 facturas/mes", "1 usuario", "Soporte email"]
      },
      {
        name: "Pro",
        price: 99,
        invoice_limit: 500,
        features: [
          "500 facturas/mes",
          "5 usuarios",
          "Soporte prioritario",
          "API Access"
        ]
      },
      {
        name: "Premium",
        price: 299,
        invoice_limit: 999999,
        features: [
          "Facturas ilimitadas",
          "Usuarios ilimitados",
          "Soporte 24/7",
          "API Access",
          "Integraciones"
        ]
      }
    ];
    let config = {
      global_dniruc_token: "",
      gemini_api_key: "",
      default_plan: "Free",
      allow_signup: true,
      maintenance_mode: false
    };
    $$renderer2.push(`<div class="space-y-8"><div><h1 class="text-2xl font-bold text-white">Configuración</h1> <p class="text-slate-500 text-sm">Configuración global del sistema SaaS</p></div> <div class="space-y-4"><h2 class="text-lg font-semibold text-white flex items-center gap-2">`);
    Credit_card($$renderer2, { size: 20 });
    $$renderer2.push(`<!----> Planes de Suscripción</h2> <div class="grid grid-cols-1 md:grid-cols-3 gap-4"><!--[-->`);
    const each_array = ensure_array_like(plans);
    for (let $$index_1 = 0, $$length = each_array.length; $$index_1 < $$length; $$index_1++) {
      let plan = each_array[$$index_1];
      $$renderer2.push(`<div class="bg-slate-900 rounded-2xl border border-slate-800 p-6 hover:border-emerald-500/30 transition-all"><div class="flex items-center justify-between mb-4"><h3 class="text-lg font-bold text-white">${escape_html(plan.name)}</h3> `);
      if (plan.name === "Pro") {
        $$renderer2.push("<!--[0-->");
        $$renderer2.push(`<span class="px-2 py-1 rounded-lg bg-emerald-500/10 text-emerald-400 text-xs font-medium">Popular</span>`);
      } else {
        $$renderer2.push("<!--[-1-->");
      }
      $$renderer2.push(`<!--]--></div> <p class="text-3xl font-black text-white mb-4">S/ ${escape_html(plan.price)} <span class="text-sm font-normal text-slate-500">/mes</span></p> <ul class="space-y-2 mb-6"><!--[-->`);
      const each_array_1 = ensure_array_like(plan.features);
      for (let $$index = 0, $$length2 = each_array_1.length; $$index < $$length2; $$index++) {
        let feature = each_array_1[$$index];
        $$renderer2.push(`<li class="flex items-center gap-2 text-slate-400 text-sm">`);
        Zap($$renderer2, { size: 14, class: "text-emerald-400" });
        $$renderer2.push(`<!----> ${escape_html(feature)}</li>`);
      }
      $$renderer2.push(`<!--]--></ul> <div class="pt-4 border-t border-slate-800"><p class="text-xs text-slate-500">Límite: ${escape_html(plan.invoice_limit === 999999 ? "Ilimitado" : plan.invoice_limit)} facturas/mes</p></div></div>`);
    }
    $$renderer2.push(`<!--]--></div></div> <div class="space-y-4"><h2 class="text-lg font-semibold text-white flex items-center gap-2">`);
    Settings($$renderer2, { size: 20 });
    $$renderer2.push(`<!----> Configuración General</h2> <div class="bg-slate-900 rounded-2xl border border-slate-800 p-6 space-y-6"><div class="grid grid-cols-1 md:grid-cols-2 gap-6"><div class="space-y-2"><label class="text-xs text-slate-400">Token DNIRUC API (Global)</label> <input type="text"${attr("value", config.global_dniruc_token)} placeholder="Token de APIsPeru" class="w-full h-11 px-4 bg-slate-800 border border-slate-700 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"/> <p class="text-[10px] text-slate-500">Token compartido para todas las empresas sin token propio</p></div> <div class="space-y-2"><label class="text-xs text-slate-400">Gemini API Key</label> <input type="password"${attr("value", config.gemini_api_key)} placeholder="AIza..." class="w-full h-11 px-4 bg-slate-800 border border-slate-700 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"/> <p class="text-[10px] text-slate-500">API key para funcionalidades de IA</p></div> <div class="space-y-2"><label class="text-xs text-slate-400">Plan por Defecto</label> `);
    $$renderer2.select(
      {
        value: config.default_plan,
        class: "w-full h-11 px-4 bg-slate-800 border border-slate-700 rounded-xl text-white focus:outline-none focus:border-emerald-500"
      },
      ($$renderer3) => {
        $$renderer3.option({ value: "Free" }, ($$renderer4) => {
          $$renderer4.push(`Free`);
        });
        $$renderer3.option({ value: "Pro" }, ($$renderer4) => {
          $$renderer4.push(`Pro`);
        });
        $$renderer3.option({ value: "Premium" }, ($$renderer4) => {
          $$renderer4.push(`Premium`);
        });
      }
    );
    $$renderer2.push(`</div></div> <div class="flex flex-col gap-4 pt-4 border-t border-slate-800"><div class="flex items-center justify-between"><div><p class="text-white font-medium">Permitir registros</p> <p class="text-slate-500 text-xs">Nuevas empresas pueden registrarse</p></div> <label class="relative inline-flex items-center cursor-pointer"><input type="checkbox"${attr("checked", config.allow_signup, true)} class="sr-only peer"/> <div class="w-11 h-6 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-500"></div></label></div> <div class="flex items-center justify-between"><div><p class="text-white font-medium">Modo mantenimiento</p> <p class="text-slate-500 text-xs">Bloquea el acceso a todas las empresas</p></div> <label class="relative inline-flex items-center cursor-pointer"><input type="checkbox"${attr("checked", config.maintenance_mode, true)} class="sr-only peer"/> <div class="w-11 h-6 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-amber-500"></div></label></div></div> <div class="flex justify-end pt-4"><button${attr("disabled", saving, true)} class="px-6 h-12 rounded-xl bg-emerald-500 text-slate-900 font-semibold hover:bg-emerald-400 transition-colors flex items-center gap-2 disabled:opacity-50">`);
    {
      $$renderer2.push("<!--[-1-->");
      Save($$renderer2, { size: 18 });
    }
    $$renderer2.push(`<!--]--> Guardar Configuración</button></div></div></div></div>`);
  });
}
export {
  _page as default
};
