<script>
  import '../app.css';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import Header from '$lib/components/Header.svelte';
  import Sidebar from '$lib/components/Sidebar.svelte';
  import { auth, checkAuth } from '$lib/stores/auth';
  import Toast from '$lib/components/Toast.svelte';
  import { onMount } from 'svelte';

  let mobileOpen = false;

  onMount(() => {
    void checkAuth();
  });

  $: pathname = $page.url.pathname;
  $: isLoginPage = pathname === '/login';
  $: isAdminLoginPage = pathname === '/admin/login';
  $: isShelllessPage = isLoginPage || isAdminLoginPage;

  $: if (!$auth.loading && !$auth.isAuthenticated && !isShelllessPage) {
    if (typeof window !== 'undefined') {
      goto('/login');
    }
  }

  $: if (!$auth.loading && $auth.isAuthenticated && isLoginPage) {
    if (typeof window !== 'undefined') {
      goto('/dashboard');
    }
  }

  function toggleMobileSidebar() {
    mobileOpen = !mobileOpen;
  }
</script>

{#if $auth.loading}
  <div class="flex min-h-screen items-center justify-center bg-slate-50">
    <div class="flex flex-col items-center gap-5 text-center">
      <div class="flex h-14 w-14 items-center justify-center rounded-2xl border border-emerald-100 bg-white shadow-sm">
        <div class="h-8 w-8 animate-spin rounded-full border-[3px] border-slate-200 border-t-emerald-500"></div>
      </div>
      <div class="space-y-2">
        <p class="text-xs font-semibold uppercase tracking-[0.32em] text-slate-500">PrintFlow</p>
        <p class="text-sm text-slate-600">Cargando entorno operativo...</p>
      </div>
    </div>
  </div>
{:else if isShelllessPage}
  <slot />
{:else if $auth.isAuthenticated}
  <div class="min-h-screen bg-slate-950 md:grid md:grid-cols-[17.5rem_minmax(0,1fr)]">
    <Sidebar bind:mobileOpen />

    <div class="flex h-screen min-w-0 flex-col bg-slate-50 selection:bg-emerald-100 selection:text-emerald-900">
      <Header on:toggleMobile={toggleMobileSidebar} />

      <main class="min-h-0 flex-1 overflow-y-auto">
        <div class="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:px-10 lg:py-8">
          <slot />
        </div>
      </main>
    </div>
  </div>
{:else}
  <div class="min-h-screen bg-slate-50"></div>
{/if}

<Toast />
