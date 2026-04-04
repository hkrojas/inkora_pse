<script>
  import '../app.css';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import Header from '$lib/components/Header.svelte';
  import Sidebar from '$lib/components/Sidebar.svelte';
  import { auth, checkAuth } from '$lib/stores/auth';
  import { appShellBackgroundClass, glassPanelClass } from '$lib/utils/uiClasses';
  import Toast from '$lib/components/Toast.svelte';
  import { onMount } from 'svelte';
  import { fade, fly } from 'svelte/transition';

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
  <div class={`relative min-h-screen overflow-hidden ${appShellBackgroundClass} selection:bg-blue-100 selection:text-blue-900 md:grid md:grid-cols-[18rem_minmax(0,1fr)]`}>
    <div class="pointer-events-none absolute inset-0 overflow-hidden">
      <div class="absolute left-[-8rem] top-[-6rem] h-72 w-72 rounded-full bg-white/80 blur-3xl"></div>
      <div class="absolute right-[-7rem] top-16 h-80 w-80 rounded-full bg-blue-200/25 blur-3xl"></div>
      <div class="absolute bottom-[-9rem] left-[28%] h-96 w-96 rounded-full bg-slate-300/20 blur-3xl"></div>
    </div>

    <div class="relative z-10">
      <Sidebar bind:mobileOpen />
    </div>

    <div class="relative z-10 flex h-screen min-w-0 flex-col">
      <Header on:toggleMobile={toggleMobileSidebar} />

      <main class="min-h-0 flex-1 overflow-y-auto px-2 pb-3 pt-2 sm:px-3 lg:px-4">
        <div class={`mx-auto w-full max-w-[96rem] rounded-[32px] ${glassPanelClass} min-h-full px-4 py-5 sm:px-6 lg:px-8 lg:py-8`}>
          {#key $page.url.pathname}
            <div in:fly={{ y: 20, duration: 300 }} out:fade>
              <slot />
            </div>
          {/key}
        </div>
      </main>
    </div>
  </div>
{:else}
  <div class="min-h-screen bg-slate-50"></div>
{/if}

<Toast />
