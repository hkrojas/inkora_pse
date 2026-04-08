import { e as attr, h as ensure_array_like, d as attr_class, j as stringify, f as escape_html } from "../../../chunks/index2.js";
function _page($$renderer) {
  const sections = [
    { id: "empresa", name: "Datos de Empresa", icon: "business" },
    { id: "pagos", name: "Pagos e Impuestos", icon: "credit_card" },
    { id: "seguridad", name: "Seguridad y Roles", icon: "shield" },
    { id: "notificaciones", name: "Notificaciones", icon: "mail" }
  ];
  let activeSection = "empresa";
  let saving = false;
  $$renderer.push(`<div class="space-y-8"><div class="flex flex-col sm:flex-row sm:justify-between sm:items-end gap-4"><div><h1 class="font-manrope text-3xl font-extrabold text-primary tracking-tight">Configuración</h1> <p class="text-outline font-medium mt-1">Gestiona la identidad visual y los parámetros técnicos de PrintFlow.</p></div> <button${attr("disabled", saving, true)} class="btn-primary w-full sm:w-auto flex items-center justify-center gap-2 disabled:opacity-50">`);
  {
    $$renderer.push("<!--[-1-->");
    $$renderer.push(`<span class="material-symbols-outlined text-lg">save</span> Guardar Cambios`);
  }
  $$renderer.push(`<!--]--></button></div> <div class="grid grid-cols-1 lg:grid-cols-4 gap-6 lg:gap-10"><aside class="flex lg:flex-col gap-2 overflow-x-auto lg:overflow-x-visible pb-2 lg:pb-0"><!--[-->`);
  const each_array = ensure_array_like(sections);
  for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
    let section = each_array[$$index];
    $$renderer.push(`<button${attr_class(`w-full lg:w-auto flex items-center gap-3 lg:gap-4 p-3 lg:p-4 rounded-xl transition-all font-semibold whitespace-nowrap text-sm ${stringify(activeSection === section.id ? "bg-primary text-white shadow-lg shadow-primary/20" : "text-outline hover:bg-surface-container-high hover:text-on-surface")}`)}><span class="material-symbols-outlined text-lg">${escape_html(section.icon)}</span> ${escape_html(section.name)}</button>`);
  }
  $$renderer.push(`<!--]--></aside> <div class="lg:col-span-3 bg-surface-container-low p-6 sm:p-8 lg:p-10 rounded-2xl border border-outline-variant/10">`);
  {
    $$renderer.push("<!--[0-->");
    $$renderer.push(`<div class="space-y-8"><div class="flex flex-col sm:flex-row items-start sm:items-center gap-6 sm:gap-8"><div class="w-28 h-28 rounded-2xl bg-surface-container-lowest border-2 border-dashed border-outline-variant/20 flex flex-col items-center justify-center relative group overflow-hidden cursor-pointer hover:border-primary/30 transition-colors"><span class="material-symbols-outlined text-outline/40 mb-1 group-hover:text-primary transition-colors">upload</span> <span class="text-[9px] font-bold text-outline/40 text-center px-2 group-hover:text-primary transition-colors">Subir Logo</span> <div class="absolute inset-0 bg-primary/10 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center"><span class="material-symbols-outlined text-primary text-2xl">upload</span></div></div> <div><h3 class="font-manrope text-lg font-bold text-on-surface mb-1">Identidad Visual</h3> <p class="text-sm text-outline">Este logo aparecerá en todas tus cotizaciones y facturas.</p> <p class="text-xs text-outline/60 mt-1">Formatos: PNG, SVG. Máx 2MB.</p></div></div> <div class="grid grid-cols-1 md:grid-cols-2 gap-6"><div class="space-y-2"><label class="block font-label text-[10px] font-bold text-outline uppercase tracking-widest pl-1">Razón Social</label> <input type="text" value="PrintFlow Solutions S.A.C." class="w-full h-12 px-5 rounded-xl bg-surface-container-lowest border border-outline-variant/10 focus:border-primary/30 focus:ring-2 focus:ring-primary/10 font-medium text-sm transition-all"/></div> <div class="space-y-2"><label class="block font-label text-[10px] font-bold text-outline uppercase tracking-widest pl-1">RUC / Identificación</label> <input type="text" value="20123456789" class="w-full h-12 px-5 rounded-xl bg-surface-container-lowest border border-outline-variant/10 focus:border-primary/30 focus:ring-2 focus:ring-primary/10 font-medium text-sm transition-all"/></div> <div class="space-y-2"><label class="block font-label text-[10px] font-bold text-outline uppercase tracking-widest pl-1">Dirección Principal</label> <input type="text" value="Av. Industrial 456, Lima" class="w-full h-12 px-5 rounded-xl bg-surface-container-lowest border border-outline-variant/10 focus:border-primary/30 focus:ring-2 focus:ring-primary/10 font-medium text-sm transition-all"/></div> <div class="space-y-2"><label class="block font-label text-[10px] font-bold text-outline uppercase tracking-widest pl-1">Correo de Contacto</label> <input type="email" value="contacto@printflow.pe" class="w-full h-12 px-5 rounded-xl bg-surface-container-lowest border border-outline-variant/10 focus:border-primary/30 focus:ring-2 focus:ring-primary/10 font-medium text-sm transition-all"/></div></div></div>`);
  }
  $$renderer.push(`<!--]--> `);
  {
    $$renderer.push("<!--[-1-->");
  }
  $$renderer.push(`<!--]--> `);
  {
    $$renderer.push("<!--[-1-->");
  }
  $$renderer.push(`<!--]--> `);
  {
    $$renderer.push("<!--[-1-->");
  }
  $$renderer.push(`<!--]--></div></div></div>`);
}
export {
  _page as default
};
