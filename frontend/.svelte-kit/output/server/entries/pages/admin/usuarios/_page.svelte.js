import { e as attr } from "../../../../chunks/index2.js";
import { P as Plus } from "../../../../chunks/plus.js";
import { S as Search } from "../../../../chunks/search.js";
import { L as Loader_circle } from "../../../../chunks/loader-circle.js";
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let searchQuery = "";
    let filterRol = "all";
    $$renderer2.push(`<div class="space-y-6"><div class="flex flex-col md:flex-row md:items-center justify-between gap-4"><div><h1 class="text-2xl font-bold text-white">Usuarios</h1> <p class="text-slate-500 text-sm">Gestiona todos los usuarios del sistema</p></div> <button class="inline-flex items-center gap-2 px-4 py-2.5 bg-emerald-500 hover:bg-emerald-400 text-slate-900 font-semibold rounded-xl transition-all">`);
    Plus($$renderer2, { size: 18 });
    $$renderer2.push(`<!----> Nuevo Usuario</button></div> <div class="flex flex-col md:flex-row gap-4"><div class="relative flex-1">`);
    Search($$renderer2, {
      class: "absolute left-4 top-1/2 -translate-y-1/2 text-slate-500",
      size: 18
    });
    $$renderer2.push(`<!----> <input type="text"${attr("value", searchQuery)} placeholder="Buscar por email o nombre..." class="w-full h-12 pl-12 pr-4 bg-slate-900 border border-slate-800 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"/></div> `);
    $$renderer2.select(
      {
        value: filterRol,
        class: "h-12 px-4 bg-slate-900 border border-slate-800 rounded-xl text-white focus:outline-none focus:border-emerald-500"
      },
      ($$renderer3) => {
        $$renderer3.option({ value: "all" }, ($$renderer4) => {
          $$renderer4.push(`Todos los roles`);
        });
        $$renderer3.option({ value: "superadmin" }, ($$renderer4) => {
          $$renderer4.push(`Superadmin`);
        });
        $$renderer3.option({ value: "admin" }, ($$renderer4) => {
          $$renderer4.push(`Admin`);
        });
        $$renderer3.option({ value: "vendedor" }, ($$renderer4) => {
          $$renderer4.push(`Vendedor`);
        });
      }
    );
    $$renderer2.push(`</div> <div class="bg-slate-900 rounded-2xl border border-slate-800 overflow-hidden">`);
    {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<div class="p-12 flex items-center justify-center">`);
      Loader_circle($$renderer2, { class: "text-emerald-500 animate-spin", size: 32 });
      $$renderer2.push(`<!----></div>`);
    }
    $$renderer2.push(`<!--]--></div></div> `);
    {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--> `);
    {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]-->`);
  });
}
export {
  _page as default
};
