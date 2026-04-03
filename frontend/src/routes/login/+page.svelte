<script>
  import { auth } from '$lib/stores/auth';
  import { fade, fly } from 'svelte/transition';
  
  let email = '';
  let password = '';
  let loading = false;
  let error = '';
  let showPassword = false;

  async function handleLogin() {
    loading = true;
    error = '';
    try {
      await auth.login(email, password);
    } catch (err) {
      error = err instanceof Error ? err.message : 'Credenciales inválidas';
    } finally {
      loading = false;
    }
  }
</script>

<svelte:head>
  <title>Iniciar Sesión | PrintFlow</title>
</svelte:head>

<div class="min-h-screen flex items-center justify-center p-6 relative overflow-hidden bg-surface font-body text-on-surface" in:fade={{ duration: 400 }}>
  <!-- Background Texture -->
  <div class="absolute inset-0 bg-pattern z-0"></div>
  
  <!-- Decorative Gradients -->
  <div class="absolute top-[-10%] right-[-10%] w-96 h-96 bg-primary-fixed opacity-20 blur-[120px] rounded-full"></div>
  <div class="absolute bottom-[-10%] left-[-10%] w-96 h-96 bg-secondary-container opacity-20 blur-[120px] rounded-full"></div>
  
  <!-- Login Container -->
  <main class="relative z-10 w-full max-w-md">
    <div class="bg-surface-container-lowest shadow-[0_12px_32px_rgba(25,28,30,0.04)] rounded-xl p-8 md:p-12 border border-outline-variant/10">
      <!-- Logo & Header -->
      <div class="flex flex-col items-center mb-10">
        <div class="w-14 h-14 bg-primary rounded-xl flex items-center justify-center mb-4 shadow-sm">
          <span class="material-symbols-outlined filled text-white text-3xl">print</span>
        </div>
        <h1 class="font-headline text-3xl font-extrabold tracking-tight text-primary">PrintFlow</h1>
        <p class="text-on-surface-variant text-sm font-medium mt-1">Editorial Precision Management</p>
      </div>
      
      <!-- Error -->
      {#if error}
        <div 
          class="p-4 mb-6 rounded-xl bg-error-container/30 border border-error/20 flex items-center gap-3 text-error"
          in:fly={{ y: -10, duration: 300 }}
        >
          <span class="material-symbols-outlined text-lg">error</span>
          <p class="text-sm font-bold">{error}</p>
        </div>
      {/if}
      
      <!-- Login Form -->
      <form on:submit|preventDefault={handleLogin} class="space-y-6">
        <!-- Email Field -->
        <div class="space-y-2">
          <label class="block font-label text-xs font-semibold text-outline tracking-wider uppercase" for="email">Correo electrónico</label>
          <div class="relative group">
            <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
              <span class="material-symbols-outlined text-outline text-xl group-focus-within:text-primary transition-colors">mail</span>
            </div>
            <input 
              class="block w-full pl-11 pr-4 py-3 bg-surface-container-low border-0 border-b-2 border-transparent focus:border-primary focus:ring-0 transition-all rounded-t-lg font-body text-on-surface placeholder:text-outline/60" 
              id="email" 
              type="email"
              bind:value={email}
              required
              placeholder="nombre@empresa.com"
            />
          </div>
        </div>
        
        <!-- Password Field -->
        <div class="space-y-2">
          <div class="flex justify-between items-center">
            <label class="block font-label text-xs font-semibold text-outline tracking-wider uppercase" for="password">Contraseña</label>
          </div>
          <div class="relative group">
            <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
              <span class="material-symbols-outlined text-outline text-xl group-focus-within:text-primary transition-colors">lock</span>
            </div>
            <input 
              class="block w-full pl-11 pr-12 py-3 bg-surface-container-low border-0 border-b-2 border-transparent focus:border-primary focus:ring-0 transition-all rounded-t-lg font-body text-on-surface placeholder:text-outline/60" 
              id="password" 
              type={showPassword ? 'text' : 'password'}
              bind:value={password}
              required
              placeholder="••••••••"
            />
            <button 
              class="absolute inset-y-0 right-0 pr-4 flex items-center text-outline hover:text-primary transition-colors" 
              type="button"
              on:click={() => showPassword = !showPassword}
              tabindex="-1"
            >
              <span class="material-symbols-outlined text-xl">{showPassword ? 'visibility_off' : 'visibility'}</span>
            </button>
          </div>
        </div>
        
        <!-- Action Links -->
        <div class="flex items-center justify-end">
          <a class="text-xs font-semibold text-primary hover:text-primary-container transition-colors tracking-tight" href="#on:click|preventDefault">
            ¿Olvidaste tu contraseña?
          </a>
        </div>
        
        <!-- Submit Button -->
        <button 
          class="w-full bg-gradient-to-br from-primary to-primary-container text-white font-headline font-bold py-4 rounded-lg shadow-sm hover:shadow-md active:scale-[0.98] transition-all flex items-center justify-center gap-2 group disabled:opacity-50"
          type="submit"
          disabled={loading}
        >
          {#if loading}
            <span class="material-symbols-outlined animate-spin text-lg">progress_activity</span>
            <span>Autenticando...</span>
          {:else}
            <span>Iniciar Sesión</span>
            <span class="material-symbols-outlined text-lg group-hover:translate-x-1 transition-transform">arrow_forward</span>
          {/if}
        </button>
      </form>
      
      <!-- Footer Compliance Note -->
      <div class="mt-12 pt-8 border-t border-outline-variant/20">
        <div class="flex flex-col items-center gap-4">
          <div class="flex items-center gap-2 px-3 py-1 bg-secondary-container/30 rounded-full">
            <span class="material-symbols-outlined filled text-on-secondary-container text-sm">verified_user</span>
            <span class="text-[10px] font-bold text-on-secondary-container uppercase tracking-widest">SUNAT Compliance Secure</span>
          </div>
          <p class="text-[11px] text-outline text-center leading-relaxed max-w-[240px]">
            Al iniciar sesión, aceptas nuestros términos de servicio y políticas de privacidad editorial.
          </p>
        </div>
      </div>
    </div>
    
    <!-- Support Access -->
    <div class="mt-8 flex justify-center items-center gap-6">
      <a class="flex items-center gap-1.5 text-xs font-medium text-outline hover:text-primary transition-colors" href="mailto:soporte@printflow.com">
        <span class="material-symbols-outlined text-base">help_outline</span>
        Soporte
      </a>
      <div class="w-1 h-1 bg-outline-variant rounded-full"></div>
      <p class="text-xs font-medium text-outline">v2.4.0 Editorial</p>
    </div>
  </main>
  
  <!-- Visual Credibility Element: Stats Cards (xl only) -->
  <div class="hidden xl:block absolute left-20 bottom-20 space-y-4">
    <div class="bg-surface-container-lowest/80 backdrop-blur-md p-4 rounded-xl border border-outline-variant/20 shadow-sm w-48">
      <div class="flex items-center gap-3 mb-2">
        <div class="p-2 bg-secondary-container/50 rounded-lg">
          <span class="material-symbols-outlined text-secondary text-sm">trending_up</span>
        </div>
        <span class="text-[10px] font-bold text-outline uppercase tracking-tighter">Eficiencia</span>
      </div>
      <p class="text-xl font-headline font-extrabold text-primary">99.8%</p>
      <p class="text-[10px] text-on-surface-variant font-medium mt-1">Precisión de impresión</p>
    </div>
    <div class="bg-surface-container-lowest/80 backdrop-blur-md p-4 rounded-xl border border-outline-variant/20 shadow-sm w-56 translate-x-12">
      <div class="flex items-center gap-3 mb-2">
        <div class="p-2 bg-primary-fixed/50 rounded-lg">
          <span class="material-symbols-outlined text-primary text-sm">description</span>
        </div>
        <span class="text-[10px] font-bold text-outline uppercase tracking-tighter">Legal</span>
      </div>
      <p class="text-xl font-headline font-extrabold text-primary">SUNAT</p>
      <p class="text-[10px] text-on-surface-variant font-medium mt-1">Sincronización en tiempo real</p>
    </div>
  </div>
</div>
