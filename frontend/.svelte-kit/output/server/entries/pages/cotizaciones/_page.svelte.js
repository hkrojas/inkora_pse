import { s as sanitize_props, a as spread_props, b as slot, g as fallback, d as attr_class, f as escape_html, j as stringify, e as attr, n as attr_style, h as ensure_array_like, i as bind_props, m as clsx } from "../../../chunks/index2.js";
import { a as api } from "../../../chunks/api.js";
import { a as premiumInputClass, g as glassPanelStrongClass, p as premiumSecondaryButtonClass, m as mutedGlassPanelClass, b as glassPanelClass, i as premiumPrimaryButtonClass, e as pageEyebrowClass, f as pageTitleClass, h as pageSubtitleClass } from "../../../chunks/uiClasses.js";
import { X } from "../../../chunks/x.js";
import { C as Calendar_days } from "../../../chunks/calendar-days.js";
import { I as Icon } from "../../../chunks/Icon.js";
import { F as File_text } from "../../../chunks/file-text.js";
import { C as Circle_alert } from "../../../chunks/circle-alert.js";
import { C as Circle_check_big } from "../../../chunks/circle-check-big.js";
import { L as Loader_circle } from "../../../chunks/loader-circle.js";
import { P as Plus } from "../../../chunks/plus.js";
function Check($$renderer, $$props) {
  const $$sanitized_props = sanitize_props($$props);
  const iconNode = [["path", { "d": "M20 6 9 17l-5-5" }]];
  Icon($$renderer, spread_props([
    { name: "check" },
    $$sanitized_props,
    {
      /**
       * @component @name Check
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cGF0aCBkPSJNMjAgNiA5IDE3bC01LTUiIC8+Cjwvc3ZnPgo=) - https://lucide.dev/icons/check
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
function Chevron_right($$renderer, $$props) {
  const $$sanitized_props = sanitize_props($$props);
  const iconNode = [["path", { "d": "m9 18 6-6-6-6" }]];
  Icon($$renderer, spread_props([
    { name: "chevron-right" },
    $$sanitized_props,
    {
      /**
       * @component @name ChevronRight
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cGF0aCBkPSJtOSAxOCA2LTYtNi02IiAvPgo8L3N2Zz4K) - https://lucide.dev/icons/chevron-right
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
function Wallet($$renderer, $$props) {
  const $$sanitized_props = sanitize_props($$props);
  const iconNode = [
    [
      "path",
      {
        "d": "M19 7V4a1 1 0 0 0-1-1H5a2 2 0 0 0 0 4h15a1 1 0 0 1 1 1v4h-3a2 2 0 0 0 0 4h3a1 1 0 0 0 1-1v-2a1 1 0 0 0-1-1"
      }
    ],
    ["path", { "d": "M3 5v14a2 2 0 0 0 2 2h15a1 1 0 0 0 1-1v-4" }]
  ];
  Icon($$renderer, spread_props([
    { name: "wallet" },
    $$sanitized_props,
    {
      /**
       * @component @name Wallet
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cGF0aCBkPSJNMTkgN1Y0YTEgMSAwIDAgMC0xLTFINWEyIDIgMCAwIDAgMCA0aDE1YTEgMSAwIDAgMSAxIDF2NGgtM2EyIDIgMCAwIDAgMCA0aDNhMSAxIDAgMCAwIDEtMXYtMmExIDEgMCAwIDAtMS0xIiAvPgogIDxwYXRoIGQ9Ik0zIDV2MTRhMiAyIDAgMCAwIDIgMmgxNWExIDEgMCAwIDAgMS0xdi00IiAvPgo8L3N2Zz4K) - https://lucide.dev/icons/wallet
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
function CotizacionDetailModal($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let progressPercent, canRegisterPayment;
    let show = fallback($$props["show"], false);
    let cotizacionId = fallback($$props["cotizacionId"], null);
    let detail = null;
    let pagos = [];
    let isLoading = false;
    let loadError = "";
    let lastLoadedId = null;
    let showPaymentModal = false;
    let paymentSaving = false;
    let paymentError = "";
    let paymentForm = getInitialPaymentForm();
    function getInitialPaymentForm() {
      return {
        monto_pagado: "",
        metodo_pago: "Transferencia",
        referencia_operacion: "",
        tipo: "adelanto"
      };
    }
    function formatCurrency(amount) {
      return new Intl.NumberFormat("es-PE", { style: "currency", currency: "PEN" }).format(Number(amount || 0));
    }
    function formatDate(dateString, withTime = false) {
      if (!dateString) return "Sin fecha";
      return new Date(dateString).toLocaleDateString("es-PE", {
        day: "2-digit",
        month: "short",
        year: "numeric",
        ...withTime ? { hour: "2-digit", minute: "2-digit" } : {}
      });
    }
    function getProgressPercent() {
      const total = Number(detail?.total_venta || 0);
      const paid = Number(detail?.monto_pagado || 0);
      if (total <= 0) return 0;
      return Math.max(0, Math.min(100, Math.round(paid / total * 100)));
    }
    function getStatusBadge(status) {
      const normalized = `${status || ""}`.trim().toLowerCase();
      if (["aprobada", "aprobado", "facturada", "emitida", "cerrada"].includes(normalized)) {
        return "bg-emerald-50 text-emerald-700 border border-emerald-200";
      }
      if ([
        "cancelada",
        "cancelado",
        "rechazada",
        "rechazado",
        "anulada",
        "anulado"
      ].includes(normalized)) {
        return "bg-red-50 text-red-700 border border-red-200";
      }
      return "bg-amber-50 text-amber-700 border border-amber-200";
    }
    async function loadDetail(force = false) {
      if (!show || !cotizacionId) return;
      if (!force && lastLoadedId === cotizacionId) return;
      isLoading = true;
      loadError = "";
      try {
        const [cotizacionResponse, pagosResponse] = await Promise.all([
          api.get(`/cotizaciones/${cotizacionId}`),
          api.get(`/cotizaciones/${cotizacionId}/pagos`)
        ]);
        detail = { ...cotizacionResponse, pagos: pagosResponse };
        pagos = pagosResponse;
        lastLoadedId = cotizacionId;
      } catch (error) {
        loadError = error?.message || "No se pudo cargar el detalle de la cotizacion.";
      } finally {
        isLoading = false;
      }
    }
    if (!show) {
      detail = null;
      pagos = [];
      loadError = "";
      lastLoadedId = null;
      showPaymentModal = false;
      paymentError = "";
      paymentForm = getInitialPaymentForm();
    }
    if (show && cotizacionId && lastLoadedId !== cotizacionId) {
      void loadDetail();
    }
    progressPercent = getProgressPercent();
    canRegisterPayment = Number(detail?.saldo_pendiente || 0) > 0;
    if (show) {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<div class="fixed inset-0 z-40 bg-slate-950/45 backdrop-blur-sm"></div> <div class="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6"><div${attr_class(`flex max-h-[92vh] w-full max-w-5xl flex-col overflow-hidden rounded-[32px] ${glassPanelStrongClass} shadow-2xl shadow-slate-900/10`)}><div class="flex items-start justify-between gap-4 border-b border-white/60 px-6 py-5 sm:px-8"><div class="space-y-2"><p class="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Detalle comercial</p> <div class="flex flex-wrap items-center gap-3"><h2 class="text-2xl font-bold tracking-tight text-slate-900">`);
      if (detail) {
        $$renderer2.push("<!--[0-->");
        $$renderer2.push(`${escape_html(detail.serie)}-${escape_html(String(detail.correlativo).padStart(6, "0"))}`);
      } else {
        $$renderer2.push("<!--[-1-->");
        $$renderer2.push(`Cotizacion`);
      }
      $$renderer2.push(`<!--]--></h2> `);
      if (detail) {
        $$renderer2.push("<!--[0-->");
        $$renderer2.push(`<span${attr_class(`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${stringify(getStatusBadge(detail.estado))}`)}>${escape_html(detail.estado)}</span>`);
      } else {
        $$renderer2.push("<!--[-1-->");
      }
      $$renderer2.push(`<!--]--></div></div> <button type="button"${attr_class(`inline-flex h-11 w-11 items-center justify-center rounded-2xl ${premiumSecondaryButtonClass} text-slate-500 hover:text-slate-900`)} aria-label="Cerrar detalle">`);
      X($$renderer2, { class: "h-5 w-5", strokeWidth: 1.9 });
      $$renderer2.push(`<!----></button></div> <div class="min-h-0 flex-1 overflow-y-auto px-6 py-6 sm:px-8">`);
      if (isLoading) {
        $$renderer2.push("<!--[0-->");
        $$renderer2.push(`<div class="flex min-h-[420px] items-center justify-center"><div${attr_class(`flex items-center gap-3 rounded-2xl px-5 py-4 text-sm text-slate-600 ${mutedGlassPanelClass}`)}>`);
        Loader_circle($$renderer2, {
          class: "h-5 w-5 animate-spin text-emerald-600",
          strokeWidth: 1.9
        });
        $$renderer2.push(`<!----> <span>Cargando detalle y pagos...</span></div></div>`);
      } else if (loadError) {
        $$renderer2.push("<!--[1-->");
        $$renderer2.push(`<div class="rounded-3xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">${escape_html(loadError)}</div>`);
      } else if (detail) {
        $$renderer2.push("<!--[2-->");
        $$renderer2.push(`<div class="space-y-6"><section class="grid gap-4 xl:grid-cols-[1.4fr_1fr]"><div${attr_class(`rounded-[30px] p-5 ${mutedGlassPanelClass}`)}><div class="flex flex-wrap items-start justify-between gap-4"><div class="space-y-2"><p class="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Cliente</p> <div class="space-y-1"><p class="text-lg font-semibold tracking-tight text-slate-900">${escape_html(detail.cliente?.razon_social || "Cliente sin nombre")}</p> <p class="text-sm text-slate-500">${escape_html(detail.cliente?.numero_documento || "Sin documento")} · ${escape_html(detail.cliente?.email || "Sin correo")}</p> <p class="text-sm text-slate-500">${escape_html(detail.cliente?.direccion || "Sin direccion registrada")}</p></div></div> <div${attr_class(`rounded-2xl px-4 py-3 ${glassPanelClass}`)}><div class="flex items-center gap-2 text-sm text-slate-600">`);
        Calendar_days($$renderer2, { class: "h-4 w-4 text-slate-400", strokeWidth: 1.9 });
        $$renderer2.push(`<!----> <span>Emitida: ${escape_html(formatDate(detail.fecha_emision))}</span></div> <p class="mt-2 text-sm text-slate-500">Vence: ${escape_html(detail.fecha_vencimiento ? formatDate(detail.fecha_vencimiento) : "Sin vencimiento")}</p></div></div> <div class="mt-5 grid gap-3 md:grid-cols-3"><div${attr_class(`rounded-2xl p-4 ${glassPanelClass}`)}><p class="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Total</p> <p class="mt-2 text-2xl font-bold tracking-tight text-slate-900">${escape_html(formatCurrency(detail.total_venta))}</p></div> <div${attr_class(`rounded-2xl p-4 ${glassPanelClass}`)}><p class="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Abonado</p> <p class="mt-2 text-2xl font-bold tracking-tight text-emerald-700">${escape_html(formatCurrency(detail.monto_pagado))}</p></div> <div${attr_class(`rounded-2xl p-4 ${glassPanelClass}`)}><p class="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Saldo</p> <p class="mt-2 text-2xl font-bold tracking-tight text-slate-900">${escape_html(formatCurrency(detail.saldo_pendiente))}</p></div></div> <div${attr_class(`mt-5 rounded-2xl p-4 ${glassPanelClass}`)}><div class="flex flex-wrap items-center justify-between gap-3"><div><p class="text-sm font-semibold text-slate-900">Progreso de cobranza</p> <p class="text-sm text-slate-500">${escape_html(progressPercent)}% abonado · saldo pendiente ${escape_html(formatCurrency(detail.saldo_pendiente))}</p></div> <button type="button"${attr_class(`inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold transition-all ${canRegisterPayment ? premiumPrimaryButtonClass : "cursor-not-allowed border border-white/60 bg-white/60 text-slate-400"}`)}${attr("disabled", !canRegisterPayment, true)}>`);
        Wallet($$renderer2, { class: "h-4 w-4", strokeWidth: 1.9 });
        $$renderer2.push(`<!----> <span>${escape_html(canRegisterPayment ? "Registrar pago / adelanto" : "Documento cubierto")}</span></button></div> <div class="mt-4 h-3 overflow-hidden rounded-full bg-slate-100"><div class="h-full rounded-full bg-gradient-to-r from-emerald-500 to-emerald-600 transition-all duration-300"${attr_style(`width: ${progressPercent}%`)}></div></div></div></div> <div${attr_class(`rounded-[30px] p-5 ${glassPanelClass}`)}><div class="flex items-start gap-3"><div class="flex h-11 w-11 items-center justify-center rounded-2xl bg-slate-100 text-slate-700">`);
        Wallet($$renderer2, { class: "h-5 w-5", strokeWidth: 1.9 });
        $$renderer2.push(`<!----></div> <div class="min-w-0 flex-1 space-y-2"><p class="text-sm font-semibold text-slate-900">Historial de pagos</p> <p class="text-sm leading-6 text-slate-500">Registra adelantos y monitorea el saldo pendiente del documento.</p></div></div> <div class="mt-5 space-y-3">`);
        if (pagos.length > 0) {
          $$renderer2.push("<!--[0-->");
          $$renderer2.push(`<!--[-->`);
          const each_array = ensure_array_like(pagos);
          for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
            let pago = each_array[$$index];
            $$renderer2.push(`<div${attr_class(`rounded-2xl p-4 ${mutedGlassPanelClass}`)}><div class="flex items-start justify-between gap-3"><div><p class="text-sm font-semibold text-slate-900">${escape_html(formatCurrency(pago.monto_pagado))}</p> <p class="mt-1 text-xs uppercase tracking-[0.18em] text-slate-500">${escape_html(pago.tipo)} · ${escape_html(pago.metodo_pago)}</p></div> <p class="text-xs text-slate-500">${escape_html(formatDate(pago.fecha_pago, true))}</p></div> `);
            if (pago.referencia_operacion) {
              $$renderer2.push("<!--[0-->");
              $$renderer2.push(`<p class="mt-3 text-sm text-slate-600">Ref: ${escape_html(pago.referencia_operacion)}</p>`);
            } else {
              $$renderer2.push("<!--[-1-->");
            }
            $$renderer2.push(`<!--]--></div>`);
          }
          $$renderer2.push(`<!--]-->`);
        } else {
          $$renderer2.push("<!--[-1-->");
          $$renderer2.push(`<div class="rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-4 py-6 text-center"><p class="text-sm font-semibold text-slate-900">Sin pagos registrados</p> <p class="mt-1 text-sm text-slate-500">Aun no se ha abonado ningun importe a esta cotizacion.</p></div>`);
        }
        $$renderer2.push(`<!--]--></div></div></section> <section${attr_class(`rounded-[30px] ${glassPanelClass}`)}><div class="flex items-center justify-between gap-4 border-b border-white/60 px-5 py-4"><div class="flex items-center gap-3"><div class="flex h-10 w-10 items-center justify-center rounded-2xl bg-slate-100 text-slate-700">`);
        File_text($$renderer2, { class: "h-5 w-5", strokeWidth: 1.9 });
        $$renderer2.push(`<!----></div> <div><p class="text-sm font-semibold text-slate-900">Items de la cotizacion</p> <p class="text-sm text-slate-500">${escape_html(detail.items.length)} linea${escape_html(detail.items.length === 1 ? "" : "s")} comerciales</p></div></div> <div class="rounded-full border border-white/70 bg-white/80 px-3 py-1 text-xs font-semibold text-slate-600 shadow-[0_8px_24px_rgba(15,23,42,0.04)]">${escape_html(formatCurrency(detail.total_venta))}</div></div> <div class="overflow-x-auto"><table class="min-w-full border-separate border-spacing-0"><thead><tr class="bg-slate-50/70"><th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Descripcion</th><th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Cantidad</th><th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">P. unitario</th><th class="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wider text-slate-500">Total</th></tr></thead><tbody><!--[-->`);
        const each_array_1 = ensure_array_like(detail.items);
        for (let index = 0, $$length = each_array_1.length; index < $$length; index++) {
          let item = each_array_1[index];
          $$renderer2.push(`<tr><td${attr_class(`px-5 py-4 text-sm text-slate-700 ${stringify(index === detail.items.length - 1 ? "" : "border-b border-slate-200/70")}`)}>${escape_html(item.descripcion)}</td><td${attr_class(`px-5 py-4 text-sm text-slate-600 ${stringify(index === detail.items.length - 1 ? "" : "border-b border-slate-200/70")}`)}>${escape_html(item.cantidad)}</td><td${attr_class(`px-5 py-4 text-sm text-slate-600 ${stringify(index === detail.items.length - 1 ? "" : "border-b border-slate-200/70")}`)}>${escape_html(formatCurrency(item.precio_unitario))}</td><td${attr_class(`px-5 py-4 text-right text-sm font-semibold text-slate-900 ${stringify(index === detail.items.length - 1 ? "" : "border-b border-slate-200/70")}`)}>${escape_html(formatCurrency(item.total_item))}</td></tr>`);
        }
        $$renderer2.push(`<!--]--></tbody></table></div></section></div>`);
      } else {
        $$renderer2.push("<!--[-1-->");
      }
      $$renderer2.push(`<!--]--></div></div></div> `);
      if (showPaymentModal) {
        $$renderer2.push("<!--[0-->");
        $$renderer2.push(`<div class="fixed inset-0 z-[60] bg-slate-950/50 backdrop-blur-sm"></div> <div class="fixed inset-0 z-[70] flex items-center justify-center p-4"><div${attr_class(`w-full max-w-lg rounded-[30px] ${glassPanelStrongClass} shadow-2xl shadow-slate-900/10`)}><div class="flex items-start justify-between gap-4 border-b border-white/60 px-6 py-5"><div class="space-y-2"><p class="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Caja comercial</p> <h3 class="text-xl font-bold tracking-tight text-slate-900">Registrar pago / adelanto</h3></div> <button type="button"${attr_class(`inline-flex h-10 w-10 items-center justify-center rounded-2xl ${premiumSecondaryButtonClass} text-slate-500 hover:text-slate-900`)} aria-label="Cerrar formulario de pago">`);
        X($$renderer2, { class: "h-4 w-4", strokeWidth: 1.9 });
        $$renderer2.push(`<!----></button></div> <div class="space-y-4 px-6 py-5"><div${attr_class(`rounded-2xl px-4 py-3 text-sm text-slate-700 ${mutedGlassPanelClass}`)}>Saldo disponible para registrar: <span class="font-semibold">${escape_html(formatCurrency(detail?.saldo_pendiente))}</span></div> <div class="grid gap-4 sm:grid-cols-2"><div class="space-y-2"><label for="payment-amount" class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Monto</label> <input id="payment-amount" type="number" min="0.01" step="0.01"${attr("value", paymentForm.monto_pagado)}${attr_class(`h-12 w-full rounded-2xl px-4 text-sm text-slate-700 ${premiumInputClass}`)}/></div> <div class="space-y-2"><label for="payment-type" class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Tipo</label> `);
        $$renderer2.select(
          {
            id: "payment-type",
            value: paymentForm.tipo,
            class: `h-12 w-full rounded-2xl px-4 text-sm text-slate-700 ${premiumInputClass}`
          },
          ($$renderer3) => {
            $$renderer3.option({ value: "adelanto" }, ($$renderer4) => {
              $$renderer4.push(`Adelanto`);
            });
            $$renderer3.option({ value: "pago" }, ($$renderer4) => {
              $$renderer4.push(`Pago`);
            });
          }
        );
        $$renderer2.push(`</div> <div class="space-y-2"><label for="payment-method" class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Metodo</label> `);
        $$renderer2.select(
          {
            id: "payment-method",
            value: paymentForm.metodo_pago,
            class: `h-12 w-full rounded-2xl px-4 text-sm text-slate-700 ${premiumInputClass}`
          },
          ($$renderer3) => {
            $$renderer3.option({ value: "Transferencia" }, ($$renderer4) => {
              $$renderer4.push(`Transferencia`);
            });
            $$renderer3.option({ value: "Yape" }, ($$renderer4) => {
              $$renderer4.push(`Yape`);
            });
            $$renderer3.option({ value: "Efectivo" }, ($$renderer4) => {
              $$renderer4.push(`Efectivo`);
            });
          }
        );
        $$renderer2.push(`</div> <div class="space-y-2"><label for="payment-reference" class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Referencia</label> <input id="payment-reference" type="text"${attr("value", paymentForm.referencia_operacion)} placeholder="Operacion, voucher o nota"${attr_class(`h-12 w-full rounded-2xl px-4 text-sm text-slate-700 ${premiumInputClass}`)}/></div></div> `);
        if (paymentError) {
          $$renderer2.push("<!--[0-->");
          $$renderer2.push(`<div class="flex items-start gap-3 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">`);
          Circle_alert($$renderer2, { class: "mt-0.5 h-4 w-4 shrink-0", strokeWidth: 1.9 });
          $$renderer2.push(`<!----> <span>${escape_html(paymentError)}</span></div>`);
        } else {
          $$renderer2.push("<!--[-1-->");
        }
        $$renderer2.push(`<!--]--></div> <div class="flex items-center justify-between gap-3 border-t border-white/60 px-6 py-4"><button type="button" class="rounded-xl px-4 py-2 text-sm font-semibold text-slate-500 transition-colors hover:bg-white/80 hover:text-slate-900">Cancelar</button> <button type="button"${attr_class(`inline-flex items-center gap-2 rounded-xl px-5 py-3 text-sm font-semibold ${premiumPrimaryButtonClass} disabled:cursor-not-allowed disabled:opacity-60`)}${attr("disabled", paymentSaving, true)}>`);
        {
          $$renderer2.push("<!--[-1-->");
          Circle_check_big($$renderer2, { class: "h-4 w-4", strokeWidth: 1.9 });
          $$renderer2.push(`<!----> <span>Guardar pago</span>`);
        }
        $$renderer2.push(`<!--]--></button></div></div></div>`);
      } else {
        $$renderer2.push("<!--[-1-->");
      }
      $$renderer2.push(`<!--]-->`);
    } else {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]-->`);
    bind_props($$props, { show, cotizacionId });
  });
}
function CotizacionSlideOver($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let selectedClient, selectedProduct, activeFinishes, paperConfig, quantity, width, height, baseUnitPrice, dimensionFactor, primaryButtonLabel;
    let show = fallback($$props["show"], false);
    const steps = [
      { id: 1, title: "Cliente", subtitle: "Cuenta y contacto" },
      {
        id: 2,
        title: "Especificaciones",
        subtitle: "Formato y producción"
      },
      { id: 3, title: "Costos", subtitle: "Acabados y total" }
    ];
    const paperOptions = [
      { label: "Couché 150g", multiplier: 1 },
      { label: "Couché 250g", multiplier: 1.12 },
      { label: "Bond 90g", multiplier: 0.92 },
      { label: "Kraft 200g", multiplier: 1.18 }
    ];
    const finishOptions = [
      { id: "laminado_mate", label: "Laminado Mate", cost: 42 },
      { id: "barniz_uv", label: "Barniz UV", cost: 65 },
      { id: "troquelado", label: "Troquelado", cost: 88 },
      { id: "hot_stamping", label: "Hot Stamping", cost: 120 }
    ];
    let saving = false;
    let currentStep = 1;
    let clientes = [];
    let productos = [];
    let clientSearch = "";
    let formData = createInitialState();
    function createInitialState() {
      return {
        cliente_id: "",
        moneda: "PEN",
        producto_id: "",
        descripcion: "",
        ancho: "",
        alto: "",
        papel: "Couché 150g",
        cantidad: 1e3,
        acabados: [],
        flete: 0,
        margen: 20
      };
    }
    function toNumber(value) {
      const parsed = Number(value);
      return Number.isFinite(parsed) ? parsed : 0;
    }
    function buildLineDescription() {
      const parts = [];
      if (selectedProduct?.nombre) parts.push(selectedProduct.nombre);
      const cleanDescription = formData.descripcion.trim();
      if (cleanDescription && cleanDescription !== selectedProduct?.nombre && cleanDescription !== selectedProduct?.descripcion) {
        parts.push(cleanDescription);
      }
      if (toNumber(formData.ancho) > 0 && toNumber(formData.alto) > 0) {
        parts.push(`${toNumber(formData.ancho)} x ${toNumber(formData.alto)} cm`);
      }
      parts.push(formData.papel);
      if (activeFinishes.length) {
        parts.push(`Acabados: ${activeFinishes.map((finish) => finish.label).join(", ")}`);
      }
      return parts.join(" · ") || "Servicio de impresión personalizado";
    }
    selectedClient = clientes.find((cliente) => `${cliente.id}` === `${formData.cliente_id}`) || null;
    selectedProduct = productos.find((producto) => `${producto.id}` === `${formData.producto_id}`) || null;
    if (selectedClient) {
      selectedClient.razon_social || "";
      selectedClient.numero_documento || "";
      [selectedClient.email, selectedClient.telefono].filter(Boolean).join(" · ") || "Sin datos de contacto";
      selectedClient.direccion || "Dirección no registrada";
    }
    clientes.filter((cliente) => {
      const searchTerm = clientSearch.trim().toLowerCase();
      if (!searchTerm) return true;
      return [
        cliente.razon_social,
        cliente.numero_documento,
        cliente.email,
        cliente.telefono
      ].filter(Boolean).some((value) => `${value}`.toLowerCase().includes(searchTerm));
    }).slice(0, 6);
    activeFinishes = finishOptions.filter((finish) => formData.acabados.includes(finish.id));
    paperConfig = paperOptions.find((paper) => paper.label === formData.papel) || paperOptions[0];
    quantity = Math.max(toNumber(formData.cantidad), 0);
    width = Math.max(toNumber(formData.ancho), 0);
    height = Math.max(toNumber(formData.alto), 0);
    baseUnitPrice = Math.max(toNumber(selectedProduct?.precio_unitario), 0);
    dimensionFactor = width > 0 && height > 0 ? Math.max(width * height / 600, 1) : 1;
    baseUnitPrice * paperConfig.multiplier * dimensionFactor * quantity;
    activeFinishes.reduce((sum, finish) => sum + finish.cost, 0);
    primaryButtonLabel = "Siguiente";
    buildLineDescription();
    if (show) {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<div class="fixed inset-0 z-40 bg-slate-900/20 backdrop-blur-sm" role="button" tabindex="-1"></div> <div${attr_class(`fixed inset-y-0 right-0 z-50 flex h-full w-full max-w-2xl flex-col ${glassPanelStrongClass} shadow-2xl shadow-slate-900/10`)} aria-modal="true" role="dialog" aria-label="Crear cotización"><div class="border-b border-white/60 px-6 py-6 sm:px-8"><div class="flex items-start justify-between gap-4"><div class="space-y-2"><p class="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Asistente comercial</p> <div class="space-y-1"><h2 class="text-2xl font-bold tracking-tight text-slate-900">Nueva Cotización</h2> <p class="max-w-xl text-sm leading-6 text-slate-500">Construye el documento paso a paso con cliente, especificaciones y costos consolidados.</p></div></div> <button${attr_class(`inline-flex h-11 w-11 items-center justify-center rounded-2xl ${premiumSecondaryButtonClass} text-slate-500 hover:text-slate-900`)} aria-label="Cerrar asistente">`);
      X($$renderer2, { class: "h-5 w-5", strokeWidth: 1.9 });
      $$renderer2.push(`<!----></button></div> <div class="mt-6 grid grid-cols-3 gap-3"><!--[-->`);
      const each_array = ensure_array_like(steps);
      for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
        let step = each_array[$$index];
        $$renderer2.push(`<div${attr_class(`rounded-2xl border px-4 py-3 transition-all duration-300 ${currentStep === step.id ? "border-slate-900/10 bg-gradient-to-b from-zinc-800 to-zinc-950 shadow-[inset_0px_1px_0px_rgba(255,255,255,0.1),0px_1px_2px_rgba(0,0,0,0.4)]" : currentStep > step.id ? "border-white/70 bg-white/80 shadow-[0_8px_24px_rgba(15,23,42,0.04)]" : "border-white/70 bg-white/60 shadow-[0_8px_24px_rgba(15,23,42,0.03)]"}`)}><div class="flex items-center gap-3"><div${attr_class(`flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold ${currentStep === step.id ? "bg-white/10 text-white" : currentStep > step.id ? "bg-slate-900 text-white" : "bg-slate-200 text-slate-500"}`)}>`);
        if (currentStep > step.id) {
          $$renderer2.push("<!--[0-->");
          Check($$renderer2, { class: "h-4 w-4", strokeWidth: 2.4 });
        } else {
          $$renderer2.push("<!--[-1-->");
          $$renderer2.push(`${escape_html(step.id)}`);
        }
        $$renderer2.push(`<!--]--></div> <div class="min-w-0"><p${attr_class(`truncate text-sm font-semibold tracking-tight ${currentStep === step.id ? "text-white" : currentStep > step.id ? "text-slate-900" : "text-slate-500"}`)}>${escape_html(step.title)}</p> <p${attr_class(`truncate text-xs ${currentStep === step.id ? "text-white/65" : currentStep >= step.id ? "text-slate-500" : "text-slate-400"}`)}>${escape_html(step.subtitle)}</p></div></div></div>`);
      }
      $$renderer2.push(`<!--]--></div></div> <div class="flex-1 overflow-y-auto px-6 py-6 sm:px-8 sm:py-7">`);
      {
        $$renderer2.push("<!--[0-->");
        $$renderer2.push(`<div class="flex min-h-full flex-col items-center justify-center gap-5 text-center"><div class="flex h-14 w-14 items-center justify-center rounded-2xl border border-blue-100 bg-blue-50"><div class="h-8 w-8 animate-spin rounded-full border-[3px] border-slate-200 border-t-blue-500"></div></div> <div class="space-y-2"><p class="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">Preparando asistente</p> <p class="text-sm text-slate-500">Cargando clientes y productos...</p></div></div>`);
      }
      $$renderer2.push(`<!--]--></div> <div class="sticky bottom-0 border-t border-white/60 bg-white/70 p-4 backdrop-blur-xl sm:px-8 sm:py-5"><div class="space-y-4">`);
      {
        $$renderer2.push("<!--[-1-->");
      }
      $$renderer2.push(`<!--]--> <div class="flex flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-between"><button${attr_class(`inline-flex items-center justify-center rounded-xl px-4 py-3 text-sm font-medium ${premiumSecondaryButtonClass}`)}>Cancelar</button> <div class="flex flex-col gap-3 sm:flex-row">`);
      {
        $$renderer2.push("<!--[-1-->");
      }
      $$renderer2.push(`<!--]--> <button${attr("disabled", saving, true)}${attr_class(`inline-flex min-w-[220px] items-center justify-center gap-2 rounded-xl px-5 py-3 text-sm font-semibold ${premiumPrimaryButtonClass} disabled:cursor-not-allowed disabled:opacity-70`)}><span>${escape_html(primaryButtonLabel)}</span> `);
      {
        $$renderer2.push("<!--[0-->");
        Chevron_right($$renderer2, { class: "h-4 w-4", strokeWidth: 2.2 });
      }
      $$renderer2.push(`<!--]--></button></div></div></div></div></div>`);
    } else {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]-->`);
    bind_props($$props, { show });
  });
}
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let cotizaciones = [];
    let showModal = false;
    let showDetailModal = false;
    let selectedCotizacionId = null;
    let activeFilter = "todas";
    const skeletonRows = Array.from({ length: 6 }, (_, index) => index);
    const quickFilters = [
      { id: "todas", label: "Todas" },
      { id: "pendientes", label: "Pendientes" },
      { id: "aprobadas", label: "Aprobadas" }
    ];
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
    function matchesFilter(cotizacion, filterId) {
      const variant = normalizeStatus(cotizacion?.estado);
      if (filterId === "aprobadas") return variant === "approved";
      if (filterId === "pendientes") return variant === "pending";
      return true;
    }
    function getFilterCount(filterId) {
      return cotizaciones.filter((cotizacion) => matchesFilter(cotizacion, filterId)).length;
    }
    cotizaciones.filter((cotizacion) => matchesFilter(cotizacion, activeFilter));
    let $$settled = true;
    let $$inner_renderer;
    function $$render_inner($$renderer3) {
      $$renderer3.push(`<div class="space-y-6"><section class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between"><div class="space-y-2"><p${attr_class(clsx(pageEyebrowClass))}>Centro comercial</p> <div class="space-y-1"><h1${attr_class(clsx(pageTitleClass))}>Cotizaciones</h1> <p${attr_class(`max-w-2xl ${pageSubtitleClass}`)}>Supervisa el pipeline de documentos y revisa rápidamente el estado de cada propuesta comercial.</p></div></div> <button${attr_class(`inline-flex items-center justify-center gap-2 rounded-xl px-5 py-3 text-sm font-semibold ${premiumPrimaryButtonClass}`)}>`);
      Plus($$renderer3, { class: "h-4 w-4", strokeWidth: 2.2 });
      $$renderer3.push(`<!----> <span>Nueva Cotización</span></button></section> <section class="flex flex-wrap gap-2"><!--[-->`);
      const each_array = ensure_array_like(quickFilters);
      for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
        let filter = each_array[$$index];
        $$renderer3.push(`<button${attr_class(`inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-medium transition-all duration-300 ${stringify(activeFilter === filter.id ? "border-slate-900/10 bg-gradient-to-b from-zinc-800 to-zinc-950 text-white shadow-[inset_0px_1px_0px_rgba(255,255,255,0.1),0px_1px_2px_rgba(0,0,0,0.4)]" : "border-white/70 bg-white/70 text-slate-600 shadow-[0_8px_24px_rgba(15,23,42,0.04)] hover:bg-white/90 hover:text-slate-900")}`)}><span>${escape_html(filter.label)}</span> <span${attr_class(`rounded-full px-2 py-0.5 text-[11px] font-semibold ${stringify(activeFilter === filter.id ? "bg-white/10 text-white" : "bg-slate-100 text-slate-500")}`)}>${escape_html(getFilterCount(filter.id))}</span></button>`);
      }
      $$renderer3.push(`<!--]--></section> <section${attr_class(`overflow-hidden rounded-[30px] ${glassPanelStrongClass}`)}>`);
      {
        $$renderer3.push("<!--[0-->");
        $$renderer3.push(`<div class="overflow-x-auto" aria-hidden="true"><table class="min-w-full border-separate border-spacing-0"><thead><tr class="bg-slate-50/50"><th class="px-6 pb-3 pt-5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Documento</th><th class="px-6 pb-3 pt-5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Cliente</th><th class="px-6 pb-3 pt-5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Fecha</th><th class="px-6 pb-3 pt-5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Total</th><th class="px-6 pb-3 pt-5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Estado</th><th class="px-6 pb-3 pt-5 text-right text-xs font-semibold uppercase tracking-wider text-slate-500">Detalle</th></tr></thead><tbody><!--[-->`);
        const each_array_1 = ensure_array_like(skeletonRows);
        for (let index = 0, $$length = each_array_1.length; index < $$length; index++) {
          each_array_1[index];
          $$renderer3.push(`<tr class="animate-pulse"><td${attr_class(`px-6 py-4 ${stringify(index === skeletonRows.length - 1 ? "border-b-0" : "border-b border-slate-200/70")}`)}><div class="space-y-2"><div class="h-4 w-28 rounded-full bg-slate-200"></div> <div class="h-3 w-20 rounded-full bg-slate-100"></div></div></td><td${attr_class(`px-6 py-4 ${stringify(index === skeletonRows.length - 1 ? "border-b-0" : "border-b border-slate-200/70")}`)}><div class="space-y-2"><div class="h-4 w-40 rounded-full bg-slate-200"></div> <div class="h-3 w-24 rounded-full bg-slate-100"></div></div></td><td${attr_class(`px-6 py-4 ${stringify(index === skeletonRows.length - 1 ? "border-b-0" : "border-b border-slate-200/70")}`)}><div class="h-4 w-24 rounded-full bg-slate-200"></div></td><td${attr_class(`px-6 py-4 ${stringify(index === skeletonRows.length - 1 ? "border-b-0" : "border-b border-slate-200/70")}`)}><div class="h-4 w-20 rounded-full bg-slate-200"></div></td><td${attr_class(`px-6 py-4 ${stringify(index === skeletonRows.length - 1 ? "border-b-0" : "border-b border-slate-200/70")}`)}><div class="h-7 w-24 rounded-full bg-slate-100"></div></td><td${attr_class(`px-6 py-4 text-right ${stringify(index === skeletonRows.length - 1 ? "border-b-0" : "border-b border-slate-200/70")}`)}><div class="ml-auto h-4 w-14 rounded-full bg-slate-200"></div></td></tr>`);
        }
        $$renderer3.push(`<!--]--></tbody></table></div>`);
      }
      $$renderer3.push(`<!--]--></section></div> `);
      CotizacionSlideOver($$renderer3, {
        get show() {
          return showModal;
        },
        set show($$value) {
          showModal = $$value;
          $$settled = false;
        }
      });
      $$renderer3.push(`<!----> `);
      CotizacionDetailModal($$renderer3, {
        cotizacionId: selectedCotizacionId,
        get show() {
          return showDetailModal;
        },
        set show($$value) {
          showDetailModal = $$value;
          $$settled = false;
        }
      });
      $$renderer3.push(`<!---->`);
    }
    do {
      $$settled = true;
      $$inner_renderer = $$renderer2.copy();
      $$render_inner($$inner_renderer);
    } while (!$$settled);
    $$renderer2.subsume($$inner_renderer);
  });
}
export {
  _page as default
};
