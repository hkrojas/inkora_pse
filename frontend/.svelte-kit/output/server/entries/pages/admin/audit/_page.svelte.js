import { s as sanitize_props, a as spread_props, b as slot, e as attr, h as ensure_array_like, f as escape_html } from "../../../../chunks/index2.js";
import { I as Icon } from "../../../../chunks/Icon.js";
import { S as Search } from "../../../../chunks/search.js";
import { L as Loader_circle } from "../../../../chunks/loader-circle.js";
function Download($$renderer, $$props) {
  const $$sanitized_props = sanitize_props($$props);
  const iconNode = [
    ["path", { "d": "M12 15V3" }],
    ["path", { "d": "M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" }],
    ["path", { "d": "m7 10 5 5 5-5" }]
  ];
  Icon($$renderer, spread_props([
    { name: "download" },
    $$sanitized_props,
    {
      /**
       * @component @name Download
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cGF0aCBkPSJNMTIgMTVWMyIgLz4KICA8cGF0aCBkPSJNMjEgMTV2NGEyIDIgMCAwIDEtMiAySDVhMiAyIDAgMCAxLTItMnYtNCIgLz4KICA8cGF0aCBkPSJtNyAxMCA1IDUgNS01IiAvPgo8L3N2Zz4K) - https://lucide.dev/icons/download
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
    let searchQuery = "";
    let filterAction = "all";
    const actionTypes = [
      { value: "all", label: "Todas las acciones" },
      { value: "create", label: "Crear" },
      { value: "update", label: "Actualizar" },
      { value: "delete", label: "Eliminar" },
      { value: "login", label: "Inicio de sesión" },
      { value: "config_change", label: "Cambio de configuración" }
    ];
    $$renderer2.push(`<div class="space-y-6"><div class="flex flex-col md:flex-row md:items-center justify-between gap-4"><div><h1 class="text-2xl font-bold text-white">Auditoría</h1> <p class="text-slate-500 text-sm">Registro de todas las acciones administrativas</p></div> <button class="inline-flex items-center gap-2 px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-white font-medium rounded-xl transition-all">`);
    Download($$renderer2, { size: 18 });
    $$renderer2.push(`<!----> Exportar</button></div> <div class="flex flex-col md:flex-row gap-4"><div class="relative flex-1">`);
    Search($$renderer2, {
      class: "absolute left-4 top-1/2 -translate-y-1/2 text-slate-500",
      size: 18
    });
    $$renderer2.push(`<!----> <input type="text"${attr("value", searchQuery)} placeholder="Buscar en detalles..." class="w-full h-12 pl-12 pr-4 bg-slate-900 border border-slate-800 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"/></div> `);
    $$renderer2.select(
      {
        value: filterAction,
        class: "h-12 px-4 bg-slate-900 border border-slate-800 rounded-xl text-white focus:outline-none focus:border-emerald-500"
      },
      ($$renderer3) => {
        $$renderer3.push(`<!--[-->`);
        const each_array = ensure_array_like(actionTypes);
        for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
          let type = each_array[$$index];
          $$renderer3.option({ value: type.value }, ($$renderer4) => {
            $$renderer4.push(`${escape_html(type.label)}`);
          });
        }
        $$renderer3.push(`<!--]-->`);
      }
    );
    $$renderer2.push(`</div> <div class="bg-slate-900 rounded-2xl border border-slate-800 overflow-hidden">`);
    {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<div class="p-12 flex items-center justify-center">`);
      Loader_circle($$renderer2, { class: "text-emerald-500 animate-spin", size: 32 });
      $$renderer2.push(`<!----></div>`);
    }
    $$renderer2.push(`<!--]--></div> <div class="bg-slate-900/50 rounded-xl p-4 border border-slate-800"><p class="text-slate-500 text-xs"><strong class="text-slate-400">Nota:</strong> Los logs de auditoría se almacenan durante 90 días. 
      Esta información es útil para cumplimiento legal y resolución de problemas.</p></div></div>`);
  });
}
export {
  _page as default
};
