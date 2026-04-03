<script>
  import '../../app.css';
  import { auth } from '$lib/stores/auth';
  import { page } from '$app/stores';
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { 
    LayoutDashboard, 
    Building2, 
    Users, 
    Settings, 
    LogOut,
    Shield,
    Activity
  } from 'lucide-svelte';
  import { api } from '$lib/utils/api';

  let loading = true;
  
  const adminNavItems = [
    { href: '/admin', icon: LayoutDashboard, label: 'Dashboard', exact: true },
    { href: '/admin/tenants', icon: Building2, label: 'Empresas' },
    { href: '/admin/usuarios', icon: Users, label: 'Usuarios' },
    { href: '/admin/config', icon: Settings, label: 'Configuración' },
  ];

  onMount(async () => {
    await auth.checkAuth();
  });

  $: isLoginPage = $page.url.pathname === '/admin/login';
  
  $: if (!$auth.loading && !$auth.isAuthenticated && !isLoginPage) {
    goto('/admin/login');
  }

  $: if (!$auth.loading && $auth.isAuthenticated && !$auth.user?.is_superadmin && !isLoginPage) {
    goto('/dashboard');
  }

  $: if (!$auth.loading && $auth.isAuthenticated && isLoginPage) {
    goto('/admin');
  }

  async function logout() {
    await auth.logout();
    goto('/admin/login');
  }

  $: currentPath = $page.url.pathname;
</script>

{#if $auth.loading || loading}
  <div class="min-h-screen bg-slate-900 flex items-center justify-center">
    <div class="flex flex-col items-center gap-4">
      <div class="w-12 h-12 border-3 border-slate-600 border-t-emerald-500 rounded-full animate-spin"></div>
      <p class="text-slate-400 text-sm font-medium">Verificando acceso administrativo...</p>
    </div>
  </div>
{:else if isLoginPage}
  <slot />
{:else if $auth.isAuthenticated && $auth.user?.is_superadmin}
  <div class="min-h-screen bg-slate-950 flex">
    <!-- Sidebar minimalista -->
    <aside class="w-64 bg-slate-900 border-r border-slate-800 flex flex-col fixed h-screen">
      <!-- Logo -->
      <div class="p-6 border-b border-slate-800">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-emerald-500/10 flex items-center justify-center">
            <Shield class="text-emerald-500" size={24} />
          </div>
          <div>
            <h1 class="text-white font-bold text-sm">ADMIN</h1>
            <p class="text-slate-500 text-[10px] uppercase tracking-wider">Control Tower</p>
          </div>
        </div>
      </div>

      <!-- Navegación -->
      <nav class="flex-1 p-4 space-y-1">
        {#each adminNavItems as item}
          {@const isActive = item.exact ? currentPath === item.href : currentPath.startsWith(item.href)}
          <a 
            href={item.href}
            class="flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all
              {isActive 
                ? 'bg-emerald-500/10 text-emerald-400' 
                : 'text-slate-400 hover:bg-slate-800 hover:text-white'}"
          >
            <svelte:component this={item.icon} size={18} />
            {item.label}
          </a>
        {/each}
      </nav>

      <!-- Usuario actual -->
      <div class="p-4 border-t border-slate-800">
        <div class="flex items-center gap-3 mb-4">
          <div class="w-9 h-9 rounded-full bg-slate-700 flex items-center justify-center">
            <span class="text-white text-xs font-bold">
              {$auth.user?.email?.[0]?.toUpperCase() || 'A'}
            </span>
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-white text-sm font-medium truncate">{$auth.user?.email}</p>
            <p class="text-emerald-400 text-[10px]">Superadmin</p>
          </div>
        </div>
        <button 
          on:click={logout}
          class="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-slate-800 text-slate-400 hover:bg-red-500/10 hover:text-red-400 text-sm font-medium transition-all"
        >
          <LogOut size={16} />
          Cerrar Sesión
        </button>
      </div>
    </aside>

    <!-- Contenido principal -->
    <main class="flex-1 ml-64 p-8">
      <slot />
    </main>
  </div>
{:else}
  <div class="min-h-screen bg-slate-950 flex items-center justify-center">
    <div class="text-center">
      <Shield class="text-red-500 mx-auto mb-4" size={48} />
      <h1 class="text-white text-xl font-bold mb-2">Acceso Denegado</h1>
      <p class="text-slate-400">No tienes permisos de administrador</p>
    </div>
  </div>
{/if}

<style>
  :global(body) {
    background-color: #020617;
  }
</style>
