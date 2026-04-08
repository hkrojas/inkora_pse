import { d as attr_class, h as ensure_array_like, j as stringify, f as escape_html } from "../../../../chunks/index2.js";
import { U as Upload } from "../../../../chunks/upload.js";
import { F as File_text } from "../../../../chunks/file-text.js";
import { P as Package } from "../../../../chunks/package.js";
import { C as Circle_alert } from "../../../../chunks/circle-alert.js";
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let previewItems = [];
    $$renderer2.push(`<div class="space-y-6"><section class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between"><div class="space-y-2"><p class="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Almacén inteligente</p> <div class="space-y-1"><h1 class="text-2xl font-bold tracking-tight text-slate-900">Compras</h1> <p class="max-w-3xl text-sm leading-6 text-slate-500">Carga facturas de proveedor en PDF o imagen y deja que la IA prepare una lectura preliminar de los insumos comprados.</p></div></div></section> <section class="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]"><div${attr_class(`rounded-3xl border border-dashed p-6 transition-all duration-200 ${stringify("border-slate-300 bg-white shadow-sm")}`)} role="button" tabindex="0" aria-label="Zona para cargar factura de proveedor"><div class="flex min-h-[260px] flex-col items-center justify-center gap-5 text-center"><div class="flex h-16 w-16 items-center justify-center rounded-2xl border border-emerald-100 bg-emerald-50 text-emerald-600">`);
    Upload($$renderer2, { class: "h-8 w-8", strokeWidth: 1.9 });
    $$renderer2.push(`<!----></div> <div class="space-y-2"><h2 class="text-lg font-semibold tracking-tight text-slate-900">Arrastra una factura aquí</h2> <p class="max-w-md text-sm leading-6 text-slate-500">También puedes hacer clic para seleccionar un PDF, JPG, PNG o WEBP y enviarlo al OCR inteligente.</p></div> <button type="button" class="inline-flex items-center justify-center rounded-xl bg-emerald-600 px-5 py-3 text-sm font-semibold text-white shadow-sm shadow-emerald-900/10 ring-1 ring-inset ring-emerald-500/70 transition-all duration-200 hover:bg-emerald-500">Seleccionar archivo</button> <p class="text-xs font-medium uppercase tracking-[0.24em] text-slate-400">Formatos admitidos: PDF, JPG, PNG, WEBP</p></div> <input type="file" accept=".pdf,image/*" class="hidden"/></div> <aside class="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm"><div class="space-y-5"><div class="space-y-1"><p class="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Estado de carga</p> <h2 class="text-lg font-semibold tracking-tight text-slate-900">Lectura preliminar del documento</h2></div> <div class="rounded-2xl border border-slate-200 bg-slate-50 p-4"><p class="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Archivo actual</p> `);
    {
      $$renderer2.push("<!--[-1-->");
      $$renderer2.push(`<p class="mt-3 text-sm text-slate-500">Todavía no has cargado una factura.</p>`);
    }
    $$renderer2.push(`<!--]--></div> <div class="rounded-2xl border border-slate-200 bg-slate-50 p-4"><p class="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Checklist</p> <div class="mt-3 space-y-3 text-sm text-slate-600"><div class="flex items-start gap-3"><div class="mt-0.5 flex h-7 w-7 items-center justify-center rounded-full bg-white shadow-sm">`);
    File_text($$renderer2, { class: "h-4 w-4 text-slate-500", strokeWidth: 1.9 });
    $$renderer2.push(`<!----></div> <p>Sube un documento legible con el detalle de productos o insumos comprados.</p></div> <div class="flex items-start gap-3"><div class="mt-0.5 flex h-7 w-7 items-center justify-center rounded-full bg-white shadow-sm">`);
    Package($$renderer2, { class: "h-4 w-4 text-slate-500", strokeWidth: 1.9 });
    $$renderer2.push(`<!----></div> <p>La tabla mostrará una lectura preliminar para que revises nombre y cantidad antes de registrar stock.</p></div></div></div> `);
    {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--></div></aside></section> <section class="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm"><div class="border-b border-slate-200 px-6 py-5"><div class="space-y-1"><p class="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Previsualización OCR</p> <h2 class="text-lg font-semibold tracking-tight text-slate-900">Ítems extraídos</h2></div></div> `);
    if (previewItems.length > 0) {
      $$renderer2.push("<!--[1-->");
      $$renderer2.push(`<div class="overflow-x-auto"><table class="min-w-full border-separate border-spacing-0"><thead><tr class="bg-slate-50/60"><th class="px-6 pb-3 pt-5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Insumo</th><th class="px-6 pb-3 pt-5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Cantidad</th></tr></thead><tbody><!--[-->`);
      const each_array_1 = ensure_array_like(previewItems);
      for (let index = 0, $$length = each_array_1.length; index < $$length; index++) {
        let item = each_array_1[index];
        $$renderer2.push(`<tr class="transition-colors hover:bg-slate-50"><td${attr_class(`px-6 py-4 text-sm font-medium text-slate-900 ${stringify(index === previewItems.length - 1 ? "border-b-0" : "border-b border-slate-200/70")}`)}>${escape_html(item.nombre)}</td><td${attr_class(`px-6 py-4 text-sm text-slate-600 ${stringify(index === previewItems.length - 1 ? "border-b-0" : "border-b border-slate-200/70")}`)}>${escape_html(item.cantidad)}</td></tr>`);
      }
      $$renderer2.push(`<!--]--></tbody></table></div>`);
    } else {
      $$renderer2.push("<!--[-1-->");
      $$renderer2.push(`<div class="flex min-h-[260px] flex-col items-center justify-center gap-4 px-6 py-10 text-center"><div class="flex h-14 w-14 items-center justify-center rounded-2xl border border-slate-200 bg-slate-50 text-slate-400">`);
      Circle_alert($$renderer2, { class: "h-7 w-7", strokeWidth: 1.9 });
      $$renderer2.push(`<!----></div> <div class="space-y-2"><h3 class="text-lg font-semibold tracking-tight text-slate-900">Aún no hay lectura disponible</h3> <p class="max-w-md text-sm leading-6 text-slate-500">Carga una factura de proveedor para generar una tabla preliminar con los insumos detectados por el OCR.</p></div></div>`);
    }
    $$renderer2.push(`<!--]--></section></div>`);
  });
}
export {
  _page as default
};
