<script>
  import { auth } from '$lib/stores/auth';
  import { createEventDispatcher } from 'svelte';

  const dispatch = createEventDispatcher();
  $: user = $auth.user;

  let searchExpanded = false;
</script>

<header class="h-16 flex items-center justify-between px-4 md:px-8 bg-slate-50/80 backdrop-blur-md sticky top-0 z-40 shadow-sm border-b border-outline-variant/10 gap-3">
  
  <!-- Mobile: Hamburger -->
  <button 
    class="md:hidden p-2.5 rounded-xl bg-surface-container-low text-on-surface-variant hover:text-primary transition-all shrink-0"
    on:click={() => dispatch('toggleMobile')}
  >
    <span class="material-symbols-outlined">menu</span>
  </button>

  <!-- Search bar -->
  <div class="flex items-center gap-6 flex-1 max-w-md {searchExpanded ? '' : 'hidden md:flex'}">
    <div class="relative w-full">
      <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline text-lg">search</span>
      <input 
        type="text" 
        placeholder="Buscar facturas, clientes o insumos..." 
        class="w-full pl-10 pr-4 py-2 bg-surface-container-low border-none rounded-full text-sm focus:ring-2 focus:ring-primary/20 transition-all placeholder:text-outline/60"
      />
    </div>
  </div>

  <!-- Mobile: Search toggle -->
  <button 
    class="md:hidden p-2.5 rounded-xl bg-surface-container-low text-on-surface-variant hover:text-primary transition-all {searchExpanded ? 'hidden' : ''}"
    on:click={() => searchExpanded = !searchExpanded}
  >
    <span class="material-symbols-outlined">search</span>
  </button>

  <div class="flex items-center gap-4 {searchExpanded ? 'hidden' : ''}">
    <!-- Exchange Rate Badge -->
    <div class="hidden lg:flex items-center gap-2 bg-surface-container-low px-3 py-1.5 rounded-full border border-outline-variant/20">
      <span class="material-symbols-outlined filled text-sm text-secondary">account_balance_wallet</span>
      <span class="text-xs font-bold text-on-surface">TC: 3.742</span>
    </div>

    <!-- SuperAdmin Badge -->
    {#if user?.is_superadmin}
      <a 
        href="/superadmin" 
        class="hidden sm:flex items-center gap-2 px-3 py-2 rounded-xl bg-primary/10 text-primary hover:bg-primary hover:text-white transition-all text-xs font-bold"
      >
        <span class="material-symbols-outlined text-base">admin_panel_settings</span>
        <span class="hidden lg:inline">PANEL SAAS</span>
      </a>
    {/if}

    <!-- Notification buttons -->
    <div class="flex items-center gap-1.5">
      <button class="p-2 text-slate-500 hover:bg-slate-200/50 rounded-full transition-colors relative">
        <span class="material-symbols-outlined">notifications</span>
        <span class="absolute top-1.5 right-1.5 w-2 h-2 bg-error rounded-full"></span>
      </button>
      <button class="hidden sm:flex p-2 text-slate-500 hover:bg-slate-200/50 rounded-full transition-colors">
        <span class="material-symbols-outlined">settings</span>
      </button>
    </div>
    
    <div class="hidden md:block h-8 w-px bg-outline-variant/30 mx-1"></div>
    
    <!-- User profile -->
    <div class="flex items-center gap-3">
      <div class="text-right hidden xl:flex flex-col">
        <p class="text-xs font-bold text-on-surface">{user?.nombre_completo || 'Cargando...'}</p>
        <p class="text-[10px] text-outline font-medium uppercase tracking-wider">{user?.is_superadmin ? 'Super Admin' : 'Plan Pro'}</p>
      </div>
      <div class="w-10 h-10 rounded-full bg-gradient-to-br from-primary to-primary-container flex items-center justify-center text-white font-bold ring-2 ring-primary/10 text-sm shadow-sm">
        {user?.nombre_completo ? user.nombre_completo.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2) : '??'}
      </div>
      <button 
        on:click={() => auth.logout()}
        class="p-2 text-slate-500 hover:text-error rounded-full transition-colors"
        title="Cerrar Sesión"
      >
        <span class="material-symbols-outlined text-xl">logout</span>
      </button>
    </div>
  </div>
</header>
