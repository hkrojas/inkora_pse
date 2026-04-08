import { c as store_get, u as unsubscribe_stores } from "../../../chunks/index2.js";
/* empty css                  */
import { g as goto, a as auth } from "../../../chunks/auth.js";
import { p as page } from "../../../chunks/stores.js";
function _layout($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    var $$store_subs;
    let isLoginPage;
    let loading = true;
    isLoginPage = store_get($$store_subs ??= {}, "$page", page).url.pathname === "/admin/login";
    if (!store_get($$store_subs ??= {}, "$auth", auth).loading && !store_get($$store_subs ??= {}, "$auth", auth).isAuthenticated && !isLoginPage) {
      goto();
    }
    if (!store_get($$store_subs ??= {}, "$auth", auth).loading && store_get($$store_subs ??= {}, "$auth", auth).isAuthenticated && !store_get($$store_subs ??= {}, "$auth", auth).user?.is_superadmin && !isLoginPage) {
      goto();
    }
    if (!store_get($$store_subs ??= {}, "$auth", auth).loading && store_get($$store_subs ??= {}, "$auth", auth).isAuthenticated && isLoginPage) {
      goto();
    }
    store_get($$store_subs ??= {}, "$page", page).url.pathname;
    if (store_get($$store_subs ??= {}, "$auth", auth).loading || loading) {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<div class="min-h-screen bg-slate-900 flex items-center justify-center"><div class="flex flex-col items-center gap-4"><div class="w-12 h-12 border-3 border-slate-600 border-t-emerald-500 rounded-full animate-spin"></div> <p class="text-slate-400 text-sm font-medium">Verificando acceso administrativo...</p></div></div>`);
    }
    $$renderer2.push(`<!--]-->`);
    if ($$store_subs) unsubscribe_stores($$store_subs);
  });
}
export {
  _layout as default
};
