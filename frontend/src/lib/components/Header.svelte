<script>
  import { auth, logout } from '$lib/stores/auth';
  import { Bell, LogOut, Menu, Search } from 'lucide-svelte';
  import { createEventDispatcher } from 'svelte';

  const dispatch = createEventDispatcher();

  function getInitials(name) {
    if (!name) return 'PF';
    return name
      .split(' ')
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0])
      .join('')
      .toUpperCase();
  }

  $: user = $auth.user;
</script>

<header class="sticky top-0 z-30 border-b border-slate-200 bg-white/80 backdrop-blur-md">
  <div class="flex h-20 items-center gap-3 px-4 sm:px-6 lg:px-8">
    <button
      class="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-slate-200 bg-white text-slate-700 shadow-sm transition-all duration-200 hover:border-emerald-200 hover:text-emerald-600 md:hidden"
      on:click={() => dispatch('toggleMobile')}
      aria-label="Abrir navegación"
    >
      <Menu class="h-5 w-5" strokeWidth={1.9} />
    </button>

    <div class="min-w-0 flex-1">
      <label class="sr-only" for="global-search">Buscador global</label>

      <div class="relative max-w-xl">
        <Search class="pointer-events-none absolute left-4 top-1/2 h-[18px] w-[18px] -translate-y-1/2 text-slate-400" strokeWidth={1.9} />
        <input
          id="global-search"
          type="text"
          placeholder="Buscar cotizaciones, clientes o órdenes..."
          class="h-11 w-full rounded-2xl border border-slate-200 bg-slate-50 pl-11 pr-4 text-sm text-slate-700 shadow-sm outline-none transition-all duration-200 placeholder:text-slate-400 focus:border-emerald-500 focus:bg-white focus:ring-4 focus:ring-emerald-500/10"
        />
      </div>
    </div>

    <div class="flex items-center gap-3">
      <button
        class="relative inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-slate-200 bg-white text-slate-600 shadow-sm transition-all duration-200 hover:border-emerald-200 hover:text-emerald-600"
        aria-label="Notificaciones"
      >
        <Bell class="h-5 w-5" strokeWidth={1.9} />
        <span class="absolute right-3 top-3 h-2 w-2 rounded-full bg-emerald-500"></span>
      </button>

      <div class="hidden h-10 w-px bg-slate-200 lg:block"></div>

      <div class="flex items-center gap-3 rounded-2xl border border-slate-200 bg-white px-3 py-2 shadow-sm">
        <div class="hidden min-w-0 text-right sm:block">
          <p class="truncate text-sm font-semibold tracking-tight text-slate-900">{user?.nombre_completo || 'Usuario PrintFlow'}</p>
          <p class="text-xs text-slate-500">{user?.is_superadmin ? 'Super Admin' : 'Operaciones'}</p>
        </div>

        <div class="flex h-11 w-11 items-center justify-center rounded-full bg-slate-900 text-sm font-semibold text-white">
          {getInitials(user?.nombre_completo)}
        </div>

        <button
          on:click={logout}
          class="inline-flex h-10 w-10 items-center justify-center rounded-xl text-slate-500 transition-all duration-200 hover:bg-slate-100 hover:text-slate-900"
          aria-label="Cerrar sesión"
          title="Cerrar sesión"
        >
          <LogOut class="h-[18px] w-[18px]" strokeWidth={1.9} />
        </button>
      </div>
    </div>
  </div>
</header>
