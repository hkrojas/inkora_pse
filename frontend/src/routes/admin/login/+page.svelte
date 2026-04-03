<script>
  import { goto } from '$app/navigation';
  import { auth } from '$lib/stores/auth';
  import { api } from '$lib/utils/api';
  import { Shield, Eye, EyeOff, Loader2, Lock, Mail } from 'lucide-svelte';

  let email = '';
  let password = '';
  let showPassword = false;
  let loading = false;
  let error = '';

  async function handleLogin() {
    if (!email || !password) {
      error = 'Por favor ingresa email y contraseña';
      return;
    }

    loading = true;
    error = '';

    try {
      const response = await fetch('http://localhost:8000/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({ username: email, password })
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Credenciales inválidas');
      }

      const data = await response.json();
      localStorage.setItem('token', data.access_token);
      
      await auth.checkAuth();
      
      if ($auth.user?.is_superadmin) {
        goto('/admin');
      } else {
        error = 'No tienes permisos de administrador';
        localStorage.removeItem('token');
      }
    } catch (e) {
      error = e.message || 'Error al iniciar sesión';
    } finally {
      loading = false;
    }
  }
</script>

<div class="min-h-screen bg-slate-950 flex items-center justify-center p-4">
  <div class="w-full max-w-md">
    <!-- Logo y título -->
    <div class="text-center mb-8">
      <div class="w-16 h-16 rounded-2xl bg-emerald-500/10 flex items-center justify-center mx-auto mb-4">
        <Shield class="text-emerald-500" size={36} />
      </div>
      <h1 class="text-2xl font-bold text-white">Admin Control Tower</h1>
      <p class="text-slate-500 text-sm mt-1">Acceso administrativo reservado</p>
    </div>

    <!-- Formulario -->
    <div class="bg-slate-900 rounded-2xl border border-slate-800 p-8">
      <form on:submit|preventDefault={handleLogin} class="space-y-6">
        {#if error}
          <div class="p-4 rounded-xl bg-red-500/10 border border-red-500/20">
            <p class="text-red-400 text-sm text-center">{error}</p>
          </div>
        {/if}

        <div class="space-y-2">
          <label class="text-slate-400 text-xs font-medium uppercase tracking-wider" for="email">
            Email
          </label>
          <div class="relative">
            <Mail class="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
            <input
              id="email"
              type="email"
              bind:value={email}
              placeholder="admin@ejemplo.com"
              class="w-full h-12 pl-12 pr-4 bg-slate-800 border border-slate-700 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500/20 transition-all"
            />
          </div>
        </div>

        <div class="space-y-2">
          <label class="text-slate-400 text-xs font-medium uppercase tracking-wider" for="password">
            Contraseña
          </label>
          <div class="relative">
            <Lock class="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
            <input
              id="password"
              type={showPassword ? 'text' : 'password'}
              bind:value={password}
              placeholder="••••••••"
              class="w-full h-12 pl-12 pr-12 bg-slate-800 border border-slate-700 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500/20 transition-all"
            />
            <button
              type="button"
              on:click={() => showPassword = !showPassword}
              class="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors"
            >
              {#if showPassword}
                <EyeOff size={18} />
              {:else}
                <Eye size={18} />
              {/if}
            </button>
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          class="w-full h-12 bg-emerald-500 hover:bg-emerald-400 text-slate-900 font-bold rounded-xl transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {#if loading}
            <Loader2 class="animate-spin" size={18} />
            Verificando...
          {:else}
            <Shield size={18} />
            Acceder
          {/if}
        </button>
      </form>
    </div>

    <!-- Footer -->
    <p class="text-center text-slate-600 text-xs mt-6">
      Sistema seguro. Todos los accesos son registrados.
    </p>
    
    <!-- Volver al sistema normal -->
    <div class="text-center mt-4">
      <a href="/login" class="text-slate-500 hover:text-slate-400 text-xs transition-colors">
        ← Volver al sistema de cotizaciones
      </a>
    </div>
  </div>
</div>
