<script>
  import '../app.css';
  import Sidebar from '$lib/components/Sidebar.svelte';
  import Header from '$lib/components/Header.svelte';
  import Toast from '$lib/components/Toast.svelte';
  import { auth } from '$lib/stores/auth';
  import { page } from '$app/stores';
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { fade, fly } from 'svelte/transition';
  
  let sidebarOpen = true;
  let mobileOpen = false;

  onMount(async () => {
    await auth.checkAuth();
  });

  $: isLoginPage = $page.url.pathname === '/login';
  
  $: if (!$auth.loading && !$auth.isAuthenticated && !isLoginPage) {
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

  $: pageKey = $page.url.pathname;
</script>

{#if $auth.loading}
  <div class="flex items-center justify-center min-h-screen bg-surface" in:fade={{ duration: 200 }}>
    <div class="flex flex-col items-center gap-6">
      <div class="relative">
        <div class="w-14 h-14 border-4 border-primary/10 border-t-primary rounded-full animate-spin"></div>
      </div>
      <div class="text-center">
        <p class="font-manrope text-on-surface font-bold tracking-[0.3em] text-xs uppercase mb-2">PrintFlow</p>
        <p class="text-outline text-[10px] font-medium">Sincronizando sesión segura...</p>
      </div>
    </div>
  </div>
{:else if isLoginPage}
  <div in:fade={{ duration: 300 }}>
    <slot />
  </div>
{:else if $auth.isAuthenticated}
  <div class="flex min-h-screen bg-surface font-body selection:bg-primary/10 selection:text-primary">
    <Sidebar bind:isOpen={sidebarOpen} bind:mobileOpen={mobileOpen} />
    
    <div class="flex-1 flex flex-col transition-all duration-500 ease-in-out {sidebarOpen ? 'md:ml-64' : 'md:ml-20'}">
      <Header on:toggleMobile={toggleMobileSidebar} />
      {#key pageKey}
        <main 
          class="p-4 sm:p-6 md:p-10 container mx-auto max-w-[1600px]"
          in:fly={{ y: 12, duration: 400, delay: 50 }}
        >
          <slot />
        </main>
      {/key}
    </div>
  </div>
{:else}
  <div class="min-h-screen bg-surface"></div>
{/if}

<Toast />

<style>
  :global(body) {
    overflow-x: hidden;
  }
  
  :global(.animate-in) {
    animation-fill-mode: forwards;
  }
</style>
