<script>
  import { page } from '$app/stores';
  import { FileText, LayoutDashboard, Printer, Settings2 } from 'lucide-svelte';
  import { fade } from 'svelte/transition';

  export let mobileOpen = false;

  const menuItems = [
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { name: 'Cotizaciones', href: '/cotizaciones', icon: FileText },
    { name: 'Producción', href: '/produccion', icon: Printer },
    { name: 'Configuración', href: '/configuracion', icon: Settings2 }
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
  class="fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-slate-800 bg-slate-900 transition-transform duration-300 md:static md:z-auto
    {mobileOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}"
>
  <div class="border-b border-slate-800 px-6 py-7">
    <a href="/dashboard" class="flex items-center gap-4" on:click={closeMobile}>
      <div class="flex h-11 w-11 items-center justify-center rounded-2xl border border-emerald-500/30 bg-emerald-500/10">
        <Printer class="h-5 w-5 text-emerald-400" strokeWidth={1.9} />
      </div>

      <div class="min-w-0">
        <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-emerald-400/80">Midnight Forest</p>
        <h1 class="truncate text-lg font-semibold tracking-tight text-white">PrintFlow</h1>
      </div>
    </a>
  </div>

  <nav class="flex-1 px-4 py-6">
    <p class="px-4 text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-500">Navegación</p>

    <div class="mt-4 space-y-1.5">
      {#each menuItems as item}
        <a
          href={item.href}
          on:click={closeMobile}
          class="group flex items-center gap-3 rounded-r-xl border-l-2 px-4 py-3 text-sm font-medium tracking-tight transition-all duration-200
            {isActive(item.href, currentPath)
              ? 'border-emerald-500 bg-slate-800/50 text-white'
              : 'border-transparent text-slate-300 hover:bg-slate-800/40 hover:text-white'}"
        >
          <svelte:component
            this={item.icon}
            class="h-5 w-5 shrink-0 {isActive(item.href, currentPath) ? 'text-emerald-400' : 'text-slate-400 group-hover:text-slate-200'}"
            strokeWidth={1.9}
          />
          <span>{item.name}</span>
        </a>
      {/each}
    </div>
  </nav>

  <div class="border-t border-slate-800 px-6 py-6">
    <div class="rounded-2xl border border-slate-800 bg-slate-800/40 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.03)]">
      <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">Base Operativa</p>
      <p class="mt-2 text-sm leading-6 text-slate-300">
        Acceso rápido al flujo comercial y de producción con una navegación limpia y persistente.
      </p>
    </div>
  </div>
</aside>
