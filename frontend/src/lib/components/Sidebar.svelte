<script>
  import { page } from '$app/stores';
  import { Boxes, FileText, LayoutDashboard, Printer, Settings2, Truck, Users } from 'lucide-svelte';
  import { darkGlassPanelClass } from '$lib/utils/uiClasses';
  import { fade } from 'svelte/transition';

  export let mobileOpen = false;

  const menuItems = [
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { name: 'Cotizaciones', href: '/cotizaciones', icon: FileText },
    { name: 'Clientes', href: '/clientes', icon: Users },
    { name: 'Almacen', href: '/almacen', icon: Boxes },
    { name: 'Despachos', href: '/despachos', icon: Truck },
    { name: 'Produccion', href: '/produccion', icon: Printer },
    { name: 'Configuracion', href: '/configuracion', icon: Settings2 }
  ];

  function closeMobile() {
    mobileOpen = false;
  }

  function isActive(href, pathname) {
    return pathname === href || pathname.startsWith(`${href}/`);
  }

  $: currentPath = $page.url.pathname;
</script>

{#if mobileOpen}
  <div
    class="fixed inset-0 z-40 bg-slate-950/60 backdrop-blur-sm md:hidden"
    on:click={closeMobile}
    on:keydown={(event) => event.key === 'Escape' && closeMobile()}
    role="button"
    tabindex="-1"
    transition:fade={{ duration: 150 }}
  ></div>
{/if}

<aside
  class={`fixed inset-y-0 left-0 z-50 flex w-72 flex-col overflow-hidden ${darkGlassPanelClass} transition-transform duration-300 md:static md:z-auto ${
    mobileOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
  }`}
>
  <div class="pointer-events-none absolute inset-0">
    <div class="absolute left-[-4rem] top-[-4rem] h-36 w-36 rounded-full bg-white/8 blur-3xl"></div>
    <div class="absolute right-[-5rem] top-32 h-44 w-44 rounded-full bg-blue-400/10 blur-3xl"></div>
    <div class="absolute bottom-[-4rem] left-10 h-40 w-40 rounded-full bg-slate-300/8 blur-3xl"></div>
  </div>

  <div class="relative z-10 border-b border-white/10 px-6 py-7">
    <a href="/dashboard" class="flex items-center gap-4" on:click={closeMobile}>
      <div class="flex h-11 w-11 items-center justify-center rounded-2xl border border-white/15 bg-white/10 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)]">
        <Printer class="h-5 w-5 text-white" strokeWidth={1.9} />
      </div>

      <div class="min-w-0">
        <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">Midnight Forest</p>
        <h1 class="truncate text-lg font-semibold tracking-tight text-white">PrintFlow</h1>
      </div>
    </a>
  </div>

  <nav class="relative z-10 flex-1 px-4 py-6">
    <p class="px-4 text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-500">Navegacion</p>

    <div class="mt-4 space-y-1.5">
      {#each menuItems as item}
        <a
          href={item.href}
          on:click={closeMobile}
          class={`group flex items-center gap-3 rounded-2xl border border-transparent px-4 py-3 text-sm font-medium tracking-tight transition-all duration-300 ${
            isActive(item.href, currentPath)
              ? 'border-white/15 bg-white/10 text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.06),0_12px_28px_rgba(15,23,42,0.22)]'
              : 'text-slate-300 hover:bg-white/6 hover:text-white'
          }`}
        >
          <svelte:component
            this={item.icon}
            class={`h-5 w-5 shrink-0 ${
              isActive(item.href, currentPath) ? 'text-white' : 'text-slate-400 group-hover:text-slate-200'
            }`}
            strokeWidth={1.9}
          />
          <span>{item.name}</span>
        </a>
      {/each}
    </div>
  </nav>

  <div class="relative z-10 border-t border-white/10 px-6 py-6">
    <div class="rounded-3xl border border-white/10 bg-white/5 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
      <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">Base Operativa</p>
      <p class="mt-2 text-sm leading-6 text-slate-300">
        Acceso rapido al flujo comercial y de produccion con una navegacion limpia y persistente.
      </p>
    </div>
  </div>
</aside>
