<script>
  import { page } from '$app/stores';
  import { fade } from 'svelte/transition';
  export let isOpen = true;
  export let mobileOpen = false;

  const menuItems = [
    { name: 'Dashboard', icon: 'dashboard', href: '/dashboard' },
    { name: 'Cotizaciones', icon: 'receipt_long', href: '/cotizaciones' },
    { name: 'Producción', icon: 'print', href: '/produccion' },
    { name: 'Configuración', icon: 'settings', href: '/configuracion' }
  ];

  function closeMobile() {
    mobileOpen = false;
  }

  $: currentPath = $page.url.pathname;
</script>

<!-- Mobile Backdrop -->
{#if mobileOpen}
  <div 
    class="fixed inset-0 z-40 bg-scrim/50 backdrop-blur-sm md:hidden"
    on:click={closeMobile}
    on:keydown={(e) => e.key === 'Escape' && closeMobile()}
    role="button"
    tabindex="-1"
    transition:fade={{ duration: 200 }}
  ></div>
{/if}

<!-- Sidebar -->
<aside 
  class="fixed inset-y-0 left-0 z-50 transition-all duration-500 ease-in-out flex flex-col bg-slate-100 border-r border-outline-variant/10
    {isOpen ? 'w-64' : 'w-20'}
    max-md:-translate-x-full max-md:w-64 max-md:shadow-2xl
    {mobileOpen ? 'max-md:translate-x-0' : ''}"
>
  <!-- Logo -->
  <div class="py-8 px-4 mb-2">
    <div class="px-2 flex items-center gap-3">
      <div class="w-10 h-10 bg-primary rounded-lg flex items-center justify-center text-white shadow-lg shrink-0">
        <span class="material-symbols-outlined filled">print</span>
      </div>
      {#if isOpen || mobileOpen}
        <div>
          <h1 class="font-manrope text-lg font-bold text-primary">PrintFlow</h1>
          <p class="text-xs text-slate-500 font-medium">Editorial Precision</p>
        </div>
      {/if}
    </div>
  </div>

  <!-- Close button mobile -->
  {#if mobileOpen}
    <button 
      class="absolute top-4 right-4 md:hidden p-2 rounded-lg text-on-surface-variant hover:text-error hover:bg-error/10 transition-all"
      on:click={closeMobile}
    >
      <span class="material-symbols-outlined">close</span>
    </button>
  {/if}

  <!-- Navigation -->
  <nav class="flex-1 space-y-1 px-2">
    {#each menuItems as item}
      <a 
        href={item.href} 
        on:click={closeMobile}
        class="flex items-center gap-3 px-4 py-3 transition-all duration-300 ease-in-out
          {currentPath === item.href || (item.href !== '/dashboard' && currentPath.startsWith(item.href))
            ? 'text-primary font-bold border-r-4 border-primary bg-slate-200/50' 
            : 'text-slate-500 font-medium hover:text-primary hover:bg-slate-200/50'}"
      >
        <span class="material-symbols-outlined">{item.icon}</span>
        {#if isOpen || mobileOpen}
          <span class="font-manrope text-base tracking-tight">{item.name}</span>
        {/if}
      </a>
    {/each}
  </nav>

  <!-- Bottom Section -->
  <div class="mt-auto px-4 pb-8 space-y-4">
    <!-- CTA Button -->
    {#if isOpen || mobileOpen}
      <a 
        href="/cotizaciones"
        class="w-full py-3 px-4 bg-gradient-to-br from-primary to-primary-container text-white rounded-xl font-bold flex items-center justify-center gap-2 shadow-xl shadow-primary/10 active:scale-95 transition-transform text-sm"
      >
        <span class="material-symbols-outlined text-sm">add_circle</span>
        <span>Nueva Cotización</span>
      </a>
    {/if}

    <div class="space-y-1">
      <a class="flex items-center gap-3 px-4 py-2 text-slate-500 font-medium hover:text-primary transition-colors" href="/configuracion">
        <span class="material-symbols-outlined text-xl">help_outline</span>
        {#if isOpen || mobileOpen}
          <span class="text-sm">Soporte</span>
        {/if}
      </a>
    </div>

    <!-- Collapse toggle (desktop) -->
    <button 
      on:click={() => isOpen = !isOpen}
      class="hidden md:flex w-full p-3 rounded-xl bg-white/70 text-on-surface-variant hover:bg-primary hover:text-white transition-all duration-300 items-center justify-center border border-outline-variant/10"
    >
      <span class="material-symbols-outlined text-lg">{isOpen ? 'chevron_left' : 'chevron_right'}</span>
    </button>
  </div>
</aside>
