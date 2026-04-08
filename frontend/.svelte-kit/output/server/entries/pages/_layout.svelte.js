import { s as sanitize_props, a as spread_props, b as slot, c as store_get, d as attr_class, e as attr, f as escape_html, u as unsubscribe_stores, g as fallback, h as ensure_array_like, i as bind_props, j as stringify } from "../../chunks/index2.js";
/* empty css               */
import { a as auth, g as goto } from "../../chunks/auth.js";
import { p as page } from "../../chunks/stores.js";
import { g as glassPanelStrongClass, p as premiumSecondaryButtonClass, a as premiumInputClass, b as glassPanelClass, d as darkGlassPanelClass, c as appShellBackgroundClass } from "../../chunks/uiClasses.js";
import { I as Icon } from "../../chunks/Icon.js";
import { S as Search } from "../../chunks/search.js";
import { F as File_text } from "../../chunks/file-text.js";
import { U as Users } from "../../chunks/users.js";
import { T as Truck } from "../../chunks/truck.js";
import { w as writable } from "../../chunks/index.js";
import { T as Triangle_alert } from "../../chunks/triangle-alert.js";
import { C as Circle_alert } from "../../chunks/circle-alert.js";
import { C as Circle_check_big } from "../../chunks/circle-check-big.js";
import { X } from "../../chunks/x.js";
function Bell($$renderer, $$props) {
  const $$sanitized_props = sanitize_props($$props);
  const iconNode = [
    ["path", { "d": "M10.268 21a2 2 0 0 0 3.464 0" }],
    [
      "path",
      {
        "d": "M3.262 15.326A1 1 0 0 0 4 17h16a1 1 0 0 0 .74-1.673C19.41 13.956 18 12.499 18 8A6 6 0 0 0 6 8c0 4.499-1.411 5.956-2.738 7.326"
      }
    ]
  ];
  Icon($$renderer, spread_props([
    { name: "bell" },
    $$sanitized_props,
    {
      /**
       * @component @name Bell
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cGF0aCBkPSJNMTAuMjY4IDIxYTIgMiAwIDAgMCAzLjQ2NCAwIiAvPgogIDxwYXRoIGQ9Ik0zLjI2MiAxNS4zMjZBMSAxIDAgMCAwIDQgMTdoMTZhMSAxIDAgMCAwIC43NC0xLjY3M0MxOS40MSAxMy45NTYgMTggMTIuNDk5IDE4IDhBNiA2IDAgMCAwIDYgOGMwIDQuNDk5LTEuNDExIDUuOTU2LTIuNzM4IDcuMzI2IiAvPgo8L3N2Zz4K) - https://lucide.dev/icons/bell
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
function Boxes($$renderer, $$props) {
  const $$sanitized_props = sanitize_props($$props);
  const iconNode = [
    [
      "path",
      {
        "d": "M2.97 12.92A2 2 0 0 0 2 14.63v3.24a2 2 0 0 0 .97 1.71l3 1.8a2 2 0 0 0 2.06 0L12 19v-5.5l-5-3-4.03 2.42Z"
      }
    ],
    ["path", { "d": "m7 16.5-4.74-2.85" }],
    ["path", { "d": "m7 16.5 5-3" }],
    ["path", { "d": "M7 16.5v5.17" }],
    [
      "path",
      {
        "d": "M12 13.5V19l3.97 2.38a2 2 0 0 0 2.06 0l3-1.8a2 2 0 0 0 .97-1.71v-3.24a2 2 0 0 0-.97-1.71L17 10.5l-5 3Z"
      }
    ],
    ["path", { "d": "m17 16.5-5-3" }],
    ["path", { "d": "m17 16.5 4.74-2.85" }],
    ["path", { "d": "M17 16.5v5.17" }],
    [
      "path",
      {
        "d": "M7.97 4.42A2 2 0 0 0 7 6.13v4.37l5 3 5-3V6.13a2 2 0 0 0-.97-1.71l-3-1.8a2 2 0 0 0-2.06 0l-3 1.8Z"
      }
    ],
    ["path", { "d": "M12 8 7.26 5.15" }],
    ["path", { "d": "m12 8 4.74-2.85" }],
    ["path", { "d": "M12 13.5V8" }]
  ];
  Icon($$renderer, spread_props([
    { name: "boxes" },
    $$sanitized_props,
    {
      /**
       * @component @name Boxes
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cGF0aCBkPSJNMi45NyAxMi45MkEyIDIgMCAwIDAgMiAxNC42M3YzLjI0YTIgMiAwIDAgMCAuOTcgMS43MWwzIDEuOGEyIDIgMCAwIDAgMi4wNiAwTDEyIDE5di01LjVsLTUtMy00LjAzIDIuNDJaIiAvPgogIDxwYXRoIGQ9Im03IDE2LjUtNC43NC0yLjg1IiAvPgogIDxwYXRoIGQ9Im03IDE2LjUgNS0zIiAvPgogIDxwYXRoIGQ9Ik03IDE2LjV2NS4xNyIgLz4KICA8cGF0aCBkPSJNMTIgMTMuNVYxOWwzLjk3IDIuMzhhMiAyIDAgMCAwIDIuMDYgMGwzLTEuOGEyIDIgMCAwIDAgLjk3LTEuNzF2LTMuMjRhMiAyIDAgMCAwLS45Ny0xLjcxTDE3IDEwLjVsLTUgM1oiIC8+CiAgPHBhdGggZD0ibTE3IDE2LjUtNS0zIiAvPgogIDxwYXRoIGQ9Im0xNyAxNi41IDQuNzQtMi44NSIgLz4KICA8cGF0aCBkPSJNMTcgMTYuNXY1LjE3IiAvPgogIDxwYXRoIGQ9Ik03Ljk3IDQuNDJBMiAyIDAgMCAwIDcgNi4xM3Y0LjM3bDUgMyA1LTNWNi4xM2EyIDIgMCAwIDAtLjk3LTEuNzFsLTMtMS44YTIgMiAwIDAgMC0yLjA2IDBsLTMgMS44WiIgLz4KICA8cGF0aCBkPSJNMTIgOCA3LjI2IDUuMTUiIC8+CiAgPHBhdGggZD0ibTEyIDggNC43NC0yLjg1IiAvPgogIDxwYXRoIGQ9Ik0xMiAxMy41VjgiIC8+Cjwvc3ZnPgo=) - https://lucide.dev/icons/boxes
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
function Info($$renderer, $$props) {
  const $$sanitized_props = sanitize_props($$props);
  const iconNode = [
    ["circle", { "cx": "12", "cy": "12", "r": "10" }],
    ["path", { "d": "M12 16v-4" }],
    ["path", { "d": "M12 8h.01" }]
  ];
  Icon($$renderer, spread_props([
    { name: "info" },
    $$sanitized_props,
    {
      /**
       * @component @name Info
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8Y2lyY2xlIGN4PSIxMiIgY3k9IjEyIiByPSIxMCIgLz4KICA8cGF0aCBkPSJNMTIgMTZ2LTQiIC8+CiAgPHBhdGggZD0iTTEyIDhoLjAxIiAvPgo8L3N2Zz4K) - https://lucide.dev/icons/info
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
function Layout_dashboard($$renderer, $$props) {
  const $$sanitized_props = sanitize_props($$props);
  const iconNode = [
    [
      "rect",
      { "width": "7", "height": "9", "x": "3", "y": "3", "rx": "1" }
    ],
    [
      "rect",
      { "width": "7", "height": "5", "x": "14", "y": "3", "rx": "1" }
    ],
    [
      "rect",
      { "width": "7", "height": "9", "x": "14", "y": "12", "rx": "1" }
    ],
    [
      "rect",
      { "width": "7", "height": "5", "x": "3", "y": "16", "rx": "1" }
    ]
  ];
  Icon($$renderer, spread_props([
    { name: "layout-dashboard" },
    $$sanitized_props,
    {
      /**
       * @component @name LayoutDashboard
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cmVjdCB3aWR0aD0iNyIgaGVpZ2h0PSI5IiB4PSIzIiB5PSIzIiByeD0iMSIgLz4KICA8cmVjdCB3aWR0aD0iNyIgaGVpZ2h0PSI1IiB4PSIxNCIgeT0iMyIgcng9IjEiIC8+CiAgPHJlY3Qgd2lkdGg9IjciIGhlaWdodD0iOSIgeD0iMTQiIHk9IjEyIiByeD0iMSIgLz4KICA8cmVjdCB3aWR0aD0iNyIgaGVpZ2h0PSI1IiB4PSIzIiB5PSIxNiIgcng9IjEiIC8+Cjwvc3ZnPgo=) - https://lucide.dev/icons/layout-dashboard
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
function Log_out($$renderer, $$props) {
  const $$sanitized_props = sanitize_props($$props);
  const iconNode = [
    ["path", { "d": "m16 17 5-5-5-5" }],
    ["path", { "d": "M21 12H9" }],
    ["path", { "d": "M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" }]
  ];
  Icon($$renderer, spread_props([
    { name: "log-out" },
    $$sanitized_props,
    {
      /**
       * @component @name LogOut
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cGF0aCBkPSJtMTYgMTcgNS01LTUtNSIgLz4KICA8cGF0aCBkPSJNMjEgMTJIOSIgLz4KICA8cGF0aCBkPSJNOSAyMUg1YTIgMiAwIDAgMS0yLTJWNWEyIDIgMCAwIDEgMi0yaDQiIC8+Cjwvc3ZnPgo=) - https://lucide.dev/icons/log-out
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
function Menu($$renderer, $$props) {
  const $$sanitized_props = sanitize_props($$props);
  const iconNode = [
    ["path", { "d": "M4 5h16" }],
    ["path", { "d": "M4 12h16" }],
    ["path", { "d": "M4 19h16" }]
  ];
  Icon($$renderer, spread_props([
    { name: "menu" },
    $$sanitized_props,
    {
      /**
       * @component @name Menu
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cGF0aCBkPSJNNCA1aDE2IiAvPgogIDxwYXRoIGQ9Ik00IDEyaDE2IiAvPgogIDxwYXRoIGQ9Ik00IDE5aDE2IiAvPgo8L3N2Zz4K) - https://lucide.dev/icons/menu
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
function Printer($$renderer, $$props) {
  const $$sanitized_props = sanitize_props($$props);
  const iconNode = [
    [
      "path",
      {
        "d": "M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"
      }
    ],
    ["path", { "d": "M6 9V3a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v6" }],
    [
      "rect",
      { "x": "6", "y": "14", "width": "12", "height": "8", "rx": "1" }
    ]
  ];
  Icon($$renderer, spread_props([
    { name: "printer" },
    $$sanitized_props,
    {
      /**
       * @component @name Printer
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cGF0aCBkPSJNNiAxOEg0YTIgMiAwIDAgMS0yLTJ2LTVhMiAyIDAgMCAxIDItMmgxNmEyIDIgMCAwIDEgMiAydjVhMiAyIDAgMCAxLTIgMmgtMiIgLz4KICA8cGF0aCBkPSJNNiA5VjNhMSAxIDAgMCAxIDEtMWgxMGExIDEgMCAwIDEgMSAxdjYiIC8+CiAgPHJlY3QgeD0iNiIgeT0iMTQiIHdpZHRoPSIxMiIgaGVpZ2h0PSI4IiByeD0iMSIgLz4KPC9zdmc+Cg==) - https://lucide.dev/icons/printer
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
function Settings_2($$renderer, $$props) {
  const $$sanitized_props = sanitize_props($$props);
  const iconNode = [
    ["path", { "d": "M14 17H5" }],
    ["path", { "d": "M19 7h-9" }],
    ["circle", { "cx": "17", "cy": "17", "r": "3" }],
    ["circle", { "cx": "7", "cy": "7", "r": "3" }]
  ];
  Icon($$renderer, spread_props([
    { name: "settings-2" },
    $$sanitized_props,
    {
      /**
       * @component @name Settings2
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cGF0aCBkPSJNMTQgMTdINSIgLz4KICA8cGF0aCBkPSJNMTkgN2gtOSIgLz4KICA8Y2lyY2xlIGN4PSIxNyIgY3k9IjE3IiByPSIzIiAvPgogIDxjaXJjbGUgY3g9IjciIGN5PSI3IiByPSIzIiAvPgo8L3N2Zz4K) - https://lucide.dev/icons/settings-2
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
function Header($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    var $$store_subs;
    let criticalAlertsCount, user;
    let showNotifications = false;
    let inventoryAlerts = [];
    function getInitials(name) {
      if (!name) return "PF";
      return name.split(" ").filter(Boolean).slice(0, 2).map((part) => part[0]).join("").toUpperCase();
    }
    criticalAlertsCount = inventoryAlerts.length;
    user = store_get($$store_subs ??= {}, "$auth", auth).user;
    $$renderer2.push(`<header class="sticky top-0 z-30"><div${attr_class(`flex h-20 items-center gap-3 rounded-[28px] px-4 sm:px-6 lg:px-8 ${glassPanelStrongClass}`)}><button${attr_class(`inline-flex h-11 w-11 items-center justify-center rounded-2xl ${premiumSecondaryButtonClass} text-slate-700 md:hidden`)} aria-label="Abrir navegación">`);
    Menu($$renderer2, { class: "h-5 w-5", strokeWidth: 1.9 });
    $$renderer2.push(`<!----></button> <div class="min-w-0 flex-1"><label class="sr-only" for="global-search">Buscador global</label> <div class="relative max-w-xl">`);
    Search($$renderer2, {
      class: "pointer-events-none absolute left-4 top-1/2 h-[18px] w-[18px] -translate-y-1/2 text-slate-400",
      strokeWidth: 1.9
    });
    $$renderer2.push(`<!----> <input id="global-search" type="text" placeholder="Buscar cotizaciones, clientes o órdenes..."${attr_class(`h-11 w-full rounded-2xl pl-11 pr-4 text-sm text-slate-700 ${premiumInputClass}`)}/></div></div> <div class="flex items-center gap-3"><div class="relative"><button${attr_class(`relative inline-flex h-11 w-11 items-center justify-center rounded-2xl ${premiumSecondaryButtonClass} text-slate-600 hover:text-slate-900`)} aria-label="Notificaciones"${attr("aria-expanded", showNotifications)} type="button">`);
    Bell($$renderer2, { class: "h-5 w-5", strokeWidth: 1.9 });
    $$renderer2.push(`<!----> `);
    if (criticalAlertsCount > 0) {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<span class="absolute right-2.5 top-2.5 inline-flex min-h-[18px] min-w-[18px] items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-semibold text-white">${escape_html(criticalAlertsCount > 9 ? "9+" : criticalAlertsCount)}</span>`);
    } else {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--></button> `);
    {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--></div> <div class="hidden h-10 w-px bg-white/70 lg:block"></div> <div${attr_class(`flex items-center gap-3 rounded-2xl px-3 py-2 ${glassPanelClass}`)}><div class="hidden min-w-0 text-right sm:block"><p class="truncate text-sm font-semibold tracking-tight text-slate-900">${escape_html(user?.nombre_completo || "Usuario PrintFlow")}</p> <p class="text-xs text-slate-500">${escape_html(user?.is_superadmin ? "Super Admin" : "Operaciones")}</p></div> <div class="flex h-11 w-11 items-center justify-center rounded-full bg-gradient-to-br from-slate-900 via-zinc-900 to-black text-sm font-semibold text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.08),0_12px_30px_rgba(15,23,42,0.25)]">${escape_html(getInitials(user?.nombre_completo))}</div> <button class="inline-flex h-10 w-10 items-center justify-center rounded-xl text-slate-500 transition-all duration-300 hover:bg-white/80 hover:text-slate-900" aria-label="Cerrar sesión" title="Cerrar sesión">`);
    Log_out($$renderer2, { class: "h-[18px] w-[18px]", strokeWidth: 1.9 });
    $$renderer2.push(`<!----></button></div></div></div></header>`);
    if ($$store_subs) unsubscribe_stores($$store_subs);
  });
}
function Sidebar($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    var $$store_subs;
    let currentPath;
    let mobileOpen = fallback($$props["mobileOpen"], false);
    const menuItems = [
      { name: "Dashboard", href: "/dashboard", icon: Layout_dashboard },
      { name: "Cotizaciones", href: "/cotizaciones", icon: File_text },
      { name: "Clientes", href: "/clientes", icon: Users },
      { name: "Almacen", href: "/almacen", icon: Boxes },
      { name: "Despachos", href: "/despachos", icon: Truck },
      { name: "Produccion", href: "/produccion", icon: Printer },
      {
        name: "Configuracion",
        href: "/configuracion",
        icon: Settings_2
      }
    ];
    function isActive(href, pathname) {
      return pathname === href || pathname.startsWith(`${href}/`);
    }
    currentPath = store_get($$store_subs ??= {}, "$page", page).url.pathname;
    if (mobileOpen) {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<div class="fixed inset-0 z-40 bg-slate-950/60 backdrop-blur-sm md:hidden" role="button" tabindex="-1"></div>`);
    } else {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--> <aside${attr_class(`fixed inset-y-0 left-0 z-50 flex w-72 flex-col overflow-hidden ${darkGlassPanelClass} transition-transform duration-300 md:static md:z-auto ${mobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"}`)}><div class="pointer-events-none absolute inset-0"><div class="absolute left-[-4rem] top-[-4rem] h-36 w-36 rounded-full bg-white/8 blur-3xl"></div> <div class="absolute right-[-5rem] top-32 h-44 w-44 rounded-full bg-blue-400/10 blur-3xl"></div> <div class="absolute bottom-[-4rem] left-10 h-40 w-40 rounded-full bg-slate-300/8 blur-3xl"></div></div> <div class="relative z-10 border-b border-white/10 px-6 py-7"><a href="/dashboard" class="flex items-center gap-4"><div class="flex h-11 w-11 items-center justify-center rounded-2xl border border-white/15 bg-white/10 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)]">`);
    Printer($$renderer2, { class: "h-5 w-5 text-white", strokeWidth: 1.9 });
    $$renderer2.push(`<!----></div> <div class="min-w-0"><p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">Midnight Forest</p> <h1 class="truncate text-lg font-semibold tracking-tight text-white">PrintFlow</h1></div></a></div> <nav class="relative z-10 flex-1 px-4 py-6"><p class="px-4 text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-500">Navegacion</p> <div class="mt-4 space-y-1.5"><!--[-->`);
    const each_array = ensure_array_like(menuItems);
    for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
      let item = each_array[$$index];
      $$renderer2.push(`<a${attr("href", item.href)}${attr_class(`group flex items-center gap-3 rounded-2xl border border-transparent px-4 py-3 text-sm font-medium tracking-tight transition-all duration-300 ${isActive(item.href, currentPath) ? "border-white/15 bg-white/10 text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.06),0_12px_28px_rgba(15,23,42,0.22)]" : "text-slate-300 hover:bg-white/6 hover:text-white"}`)}>`);
      if (item.icon) {
        $$renderer2.push("<!--[-->");
        item.icon($$renderer2, {
          class: `h-5 w-5 shrink-0 ${isActive(item.href, currentPath) ? "text-white" : "text-slate-400 group-hover:text-slate-200"}`,
          strokeWidth: 1.9
        });
        $$renderer2.push("<!--]-->");
      } else {
        $$renderer2.push("<!--[!-->");
        $$renderer2.push("<!--]-->");
      }
      $$renderer2.push(` <span>${escape_html(item.name)}</span></a>`);
    }
    $$renderer2.push(`<!--]--></div></nav> <div class="relative z-10 border-t border-white/10 px-6 py-6"><div class="rounded-3xl border border-white/10 bg-white/5 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]"><p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">Base Operativa</p> <p class="mt-2 text-sm leading-6 text-slate-300">Acceso rapido al flujo comercial y de produccion con una navegacion limpia y persistente.</p></div></div></aside>`);
    if ($$store_subs) unsubscribe_stores($$store_subs);
    bind_props($$props, { mobileOpen });
  });
}
function Toast($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    const toasts = writable([]);
    let toastList = [];
    toasts.subscribe((v) => toastList = v);
    function addToast(message, type = "success", duration = 4e3) {
      const id = Date.now();
      toasts.update((t) => [...t, { id, message, type }]);
      if (duration > 0) {
        setTimeout(() => removeToast(id), duration);
      }
    }
    function removeToast(id) {
      toasts.update((t) => t.filter((toast) => toast.id !== id));
    }
    const icons = {
      success: Circle_check_big,
      error: Circle_alert,
      warning: Triangle_alert,
      info: Info
    };
    const styles = {
      success: "bg-success/10 border-success/20 text-success",
      error: "bg-error/10 border-error/20 text-error",
      warning: "bg-warning/10 border-warning/20 text-warning",
      info: "bg-info/10 border-info/20 text-info"
    };
    $$renderer2.push(`<div class="fixed top-4 right-4 z-[100] flex flex-col gap-3 max-w-sm w-full pointer-events-none"><!--[-->`);
    const each_array = ensure_array_like(toastList);
    for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
      let toast = each_array[$$index];
      $$renderer2.push(`<div${attr_class(`pointer-events-auto flex items-start gap-3 p-4 rounded-2xl border backdrop-blur-xl shadow-lg ${stringify(styles[toast.type] || styles.info)}`)}>`);
      if (icons[toast.type] || icons.info) {
        $$renderer2.push("<!--[-->");
        (icons[toast.type] || icons.info)($$renderer2, { size: 20, class: "shrink-0 mt-0.5" });
        $$renderer2.push("<!--]-->");
      } else {
        $$renderer2.push("<!--[!-->");
        $$renderer2.push("<!--]-->");
      }
      $$renderer2.push(` <p class="text-sm font-semibold flex-1">${escape_html(toast.message)}</p> <button class="shrink-0 p-0.5 rounded-lg hover:bg-black/5 transition-colors">`);
      X($$renderer2, { size: 14 });
      $$renderer2.push(`<!----></button></div>`);
    }
    $$renderer2.push(`<!--]--></div>`);
    bind_props($$props, { toasts, addToast });
  });
}
function _layout($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    var $$store_subs;
    let pathname, isLoginPage, isAdminLoginPage, isShelllessPage;
    let mobileOpen = false;
    pathname = store_get($$store_subs ??= {}, "$page", page).url.pathname;
    isLoginPage = pathname === "/login";
    isAdminLoginPage = pathname === "/admin/login";
    isShelllessPage = isLoginPage || isAdminLoginPage;
    if (!store_get($$store_subs ??= {}, "$auth", auth).loading && !store_get($$store_subs ??= {}, "$auth", auth).isAuthenticated && !isShelllessPage) {
      if (typeof window !== "undefined") {
        goto();
      }
    }
    if (!store_get($$store_subs ??= {}, "$auth", auth).loading && store_get($$store_subs ??= {}, "$auth", auth).isAuthenticated && isLoginPage) {
      if (typeof window !== "undefined") {
        goto();
      }
    }
    let $$settled = true;
    let $$inner_renderer;
    function $$render_inner($$renderer3) {
      if (store_get($$store_subs ??= {}, "$auth", auth).loading) {
        $$renderer3.push("<!--[0-->");
        $$renderer3.push(`<div class="flex min-h-screen items-center justify-center bg-slate-50"><div class="flex flex-col items-center gap-5 text-center"><div class="flex h-14 w-14 items-center justify-center rounded-2xl border border-emerald-100 bg-white shadow-sm"><div class="h-8 w-8 animate-spin rounded-full border-[3px] border-slate-200 border-t-emerald-500"></div></div> <div class="space-y-2"><p class="text-xs font-semibold uppercase tracking-[0.32em] text-slate-500">PrintFlow</p> <p class="text-sm text-slate-600">Cargando entorno operativo...</p></div></div></div>`);
      } else if (isShelllessPage) {
        $$renderer3.push("<!--[1-->");
        $$renderer3.push(`<!--[-->`);
        slot($$renderer3, $$props, "default", {});
        $$renderer3.push(`<!--]-->`);
      } else if (store_get($$store_subs ??= {}, "$auth", auth).isAuthenticated) {
        $$renderer3.push("<!--[2-->");
        $$renderer3.push(`<div${attr_class(`relative min-h-screen overflow-hidden ${appShellBackgroundClass} selection:bg-blue-100 selection:text-blue-900 md:grid md:grid-cols-[18rem_minmax(0,1fr)]`)}><div class="pointer-events-none absolute inset-0 overflow-hidden"><div class="absolute left-[-8rem] top-[-6rem] h-72 w-72 rounded-full bg-white/80 blur-3xl"></div> <div class="absolute right-[-7rem] top-16 h-80 w-80 rounded-full bg-blue-200/25 blur-3xl"></div> <div class="absolute bottom-[-9rem] left-[28%] h-96 w-96 rounded-full bg-slate-300/20 blur-3xl"></div></div> <div class="relative z-10">`);
        Sidebar($$renderer3, {
          get mobileOpen() {
            return mobileOpen;
          },
          set mobileOpen($$value) {
            mobileOpen = $$value;
            $$settled = false;
          }
        });
        $$renderer3.push(`<!----></div> <div class="relative z-10 flex h-screen min-w-0 flex-col">`);
        Header($$renderer3);
        $$renderer3.push(`<!----> <main class="min-h-0 flex-1 overflow-y-auto px-2 pb-3 pt-2 sm:px-3 lg:px-4"><div${attr_class(`mx-auto w-full max-w-[96rem] rounded-[32px] ${glassPanelClass} min-h-full px-4 py-5 sm:px-6 lg:px-8 lg:py-8`)}><!---->`);
        {
          $$renderer3.push(`<div><!--[-->`);
          slot($$renderer3, $$props, "default", {});
          $$renderer3.push(`<!--]--></div>`);
        }
        $$renderer3.push(`<!----></div></main></div></div>`);
      } else {
        $$renderer3.push("<!--[-1-->");
        $$renderer3.push(`<div class="min-h-screen bg-slate-50"></div>`);
      }
      $$renderer3.push(`<!--]--> `);
      Toast($$renderer3, {});
      $$renderer3.push(`<!---->`);
    }
    do {
      $$settled = true;
      $$inner_renderer = $$renderer2.copy();
      $$render_inner($$inner_renderer);
    } while (!$$settled);
    $$renderer2.subsume($$inner_renderer);
    if ($$store_subs) unsubscribe_stores($$store_subs);
  });
}
export {
  _layout as default
};
