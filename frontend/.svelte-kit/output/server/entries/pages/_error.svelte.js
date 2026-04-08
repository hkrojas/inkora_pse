import { s as sanitize_props, a as spread_props, b as slot, c as store_get, k as head, f as escape_html, u as unsubscribe_stores } from "../../chunks/index2.js";
import { p as page } from "../../chunks/stores.js";
import { T as Triangle_alert } from "../../chunks/triangle-alert.js";
import { I as Icon } from "../../chunks/Icon.js";
function House($$renderer, $$props) {
  const $$sanitized_props = sanitize_props($$props);
  const iconNode = [
    [
      "path",
      { "d": "M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8" }
    ],
    [
      "path",
      {
        "d": "M3 10a2 2 0 0 1 .709-1.528l7-6a2 2 0 0 1 2.582 0l7 6A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"
      }
    ]
  ];
  Icon($$renderer, spread_props([
    { name: "house" },
    $$sanitized_props,
    {
      /**
       * @component @name House
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cGF0aCBkPSJNMTUgMjF2LThhMSAxIDAgMCAwLTEtMWgtNGExIDEgMCAwIDAtMSAxdjgiIC8+CiAgPHBhdGggZD0iTTMgMTBhMiAyIDAgMCAxIC43MDktMS41MjhsNy02YTIgMiAwIDAgMSAyLjU4MiAwbDcgNkEyIDIgMCAwIDEgMjEgMTB2OWEyIDIgMCAwIDEtMiAySDVhMiAyIDAgMCAxLTItMnoiIC8+Cjwvc3ZnPgo=) - https://lucide.dev/icons/house
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
function Refresh_cw($$renderer, $$props) {
  const $$sanitized_props = sanitize_props($$props);
  const iconNode = [
    [
      "path",
      { "d": "M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8" }
    ],
    ["path", { "d": "M21 3v5h-5" }],
    [
      "path",
      { "d": "M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16" }
    ],
    ["path", { "d": "M8 16H3v5" }]
  ];
  Icon($$renderer, spread_props([
    { name: "refresh-cw" },
    $$sanitized_props,
    {
      /**
       * @component @name RefreshCw
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cGF0aCBkPSJNMyAxMmE5IDkgMCAwIDEgOS05IDkuNzUgOS43NSAwIDAgMSA2Ljc0IDIuNzRMMjEgOCIgLz4KICA8cGF0aCBkPSJNMjEgM3Y1aC01IiAvPgogIDxwYXRoIGQ9Ik0yMSAxMmE5IDkgMCAwIDEtOSA5IDkuNzUgOS43NSAwIDAgMS02Ljc0LTIuNzRMMyAxNiIgLz4KICA8cGF0aCBkPSJNOCAxNkgzdjUiIC8+Cjwvc3ZnPgo=) - https://lucide.dev/icons/refresh-cw
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
function _error($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    var $$store_subs;
    let statusCode, message, title, subtitle;
    statusCode = store_get($$store_subs ??= {}, "$page", page).status;
    message = store_get($$store_subs ??= {}, "$page", page).error?.message || "Ha ocurrido un error inesperado";
    title = statusCode === 404 ? "Página no encontrada" : statusCode === 500 ? "Error interno del servidor" : "Algo salió mal";
    subtitle = statusCode === 404 ? "La página que buscas no existe o fue movida." : statusCode === 500 ? "Nuestro equipo ha sido notificado. Intenta de nuevo en unos minutos." : message;
    head("1j96wlh", $$renderer2, ($$renderer3) => {
      $$renderer3.title(($$renderer4) => {
        $$renderer4.push(`<title>Error ${escape_html(statusCode)} | PrintFlow</title>`);
      });
    });
    $$renderer2.push(`<div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-surface-container-lowest via-background to-surface-container-low p-6"><div class="max-w-lg w-full text-center space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700"><div class="relative mx-auto w-28 h-28"><div class="absolute inset-0 bg-error/10 rounded-full animate-ping opacity-20"></div> <div class="relative w-28 h-28 bg-gradient-to-br from-error/20 to-error/5 rounded-full flex items-center justify-center border border-error/10">`);
    Triangle_alert($$renderer2, { size: 48, class: "text-error" });
    $$renderer2.push(`<!----></div></div> <div class="space-y-3"><p class="text-8xl font-black text-on-surface/10 tracking-tighter leading-none">${escape_html(statusCode)}</p> <h1 class="text-2xl sm:text-3xl font-bold text-on-surface tracking-tight">${escape_html(title)}</h1> <p class="text-on-surface-variant font-medium max-w-md mx-auto leading-relaxed">${escape_html(subtitle)}</p></div> <div class="flex flex-col sm:flex-row gap-3 justify-center pt-4"><a href="/dashboard" class="inline-flex items-center justify-center gap-2.5 px-8 py-4 rounded-2xl bg-primary text-white font-bold hover:shadow-xl hover:shadow-primary/20 transition-all active:scale-95">`);
    House($$renderer2, { size: 18 });
    $$renderer2.push(`<!----> Ir al Panel</a> <button class="inline-flex items-center justify-center gap-2.5 px-8 py-4 rounded-2xl bg-surface-container-high text-on-surface font-bold hover:bg-surface-container-highest transition-all active:scale-95">`);
    Refresh_cw($$renderer2, { size: 18 });
    $$renderer2.push(`<!----> Reintentar</button></div> <p class="text-xs text-on-surface-variant/60 font-medium pt-8">Si el problema persiste, contacta a <a href="mailto:soporte@printflow.com" class="text-primary hover:underline">soporte@printflow.com</a></p></div></div>`);
    if ($$store_subs) unsubscribe_stores($$store_subs);
  });
}
export {
  _error as default
};
