<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/utils/api';
  import { 
    Settings,
    CreditCard,
    Zap,
    Shield,
    Save,
    Loader2,
    Plus,
    X
  } from 'lucide-svelte';

  let saving = false;
  let plans = [
    { 
      name: 'Free', 
      price: 0, 
      invoice_limit: 50, 
      features: ['50 facturas/mes', '1 usuario', 'Soporte email']
    },
    { 
      name: 'Pro', 
      price: 99, 
      invoice_limit: 500, 
      features: ['500 facturas/mes', '5 usuarios', 'Soporte prioritario', 'API Access']
    },
    { 
      name: 'Premium', 
      price: 299, 
      invoice_limit: 999999, 
      features: ['Facturas ilimitadas', 'Usuarios ilimitados', 'Soporte 24/7', 'API Access', 'Integraciones']
    }
  ];

  let config = {
    global_dniruc_token: '',
    gemini_api_key: '',
    default_plan: 'Free',
    allow_signup: true,
    maintenance_mode: false
  };

  onMount(async () => {
    await loadConfig();
  });

  async function loadConfig() {
    try {
      // Cargar configuración global
      const tenants = await api.get('/superadmin/tenants?limit=1');
      // Por ahora usamos valores por defecto
    } catch (e) {
      console.error('Error loading config:', e);
    }
  }

  async function saveConfig() {
    saving = true;
    try {
      // Simulación de guardado - en producción would call an API
      await new Promise(r => setTimeout(r, 1000));
      alert('Configuración guardada correctamente');
    } catch (e) {
      alert('Error al guardar configuración');
    } finally {
      saving = false;
    }
  }
</script>

<div class="space-y-8">
  <!-- Header -->
  <div>
    <h1 class="text-2xl font-bold text-white">Configuración</h1>
    <p class="text-slate-500 text-sm">Configuración global del sistema SaaS</p>
  </div>

  <!-- Planes -->
  <div class="space-y-4">
    <h2 class="text-lg font-semibold text-white flex items-center gap-2">
      <CreditCard size={20} />
      Planes de Suscripción
    </h2>
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      {#each plans as plan}
        <div class="bg-slate-900 rounded-2xl border border-slate-800 p-6 hover:border-emerald-500/30 transition-all">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-lg font-bold text-white">{plan.name}</h3>
            {#if plan.name === 'Pro'}
              <span class="px-2 py-1 rounded-lg bg-emerald-500/10 text-emerald-400 text-xs font-medium">Popular</span>
            {/if}
          </div>
          <p class="text-3xl font-black text-white mb-4">
            S/ {plan.price}
            <span class="text-sm font-normal text-slate-500">/mes</span>
          </p>
          <ul class="space-y-2 mb-6">
            {#each plan.features as feature}
              <li class="flex items-center gap-2 text-slate-400 text-sm">
                <Zap size={14} class="text-emerald-400" />
                {feature}
              </li>
            {/each}
          </ul>
          <div class="pt-4 border-t border-slate-800">
            <p class="text-xs text-slate-500">Límite: {plan.invoice_limit === 999999 ? 'Ilimitado' : plan.invoice_limit} facturas/mes</p>
          </div>
        </div>
      {/each}
    </div>
  </div>

  <!-- Configuración Global -->
  <div class="space-y-4">
    <h2 class="text-lg font-semibold text-white flex items-center gap-2">
      <Settings size={20} />
      Configuración General
    </h2>
    <div class="bg-slate-900 rounded-2xl border border-slate-800 p-6 space-y-6">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div class="space-y-2">
          <label class="text-xs text-slate-400">Token DNIRUC API (Global)</label>
          <input 
            type="text" 
            bind:value={config.global_dniruc_token}
            placeholder="Token de APIsPeru"
            class="w-full h-11 px-4 bg-slate-800 border border-slate-700 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
          />
          <p class="text-[10px] text-slate-500">Token compartido para todas las empresas sin token propio</p>
        </div>

        <div class="space-y-2">
          <label class="text-xs text-slate-400">Gemini API Key</label>
          <input 
            type="password" 
            bind:value={config.gemini_api_key}
            placeholder="AIza..."
            class="w-full h-11 px-4 bg-slate-800 border border-slate-700 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
          />
          <p class="text-[10px] text-slate-500">API key para funcionalidades de IA</p>
        </div>

        <div class="space-y-2">
          <label class="text-xs text-slate-400">Plan por Defecto</label>
          <select 
            bind:value={config.default_plan}
            class="w-full h-11 px-4 bg-slate-800 border border-slate-700 rounded-xl text-white focus:outline-none focus:border-emerald-500"
          >
            <option value="Free">Free</option>
            <option value="Pro">Pro</option>
            <option value="Premium">Premium</option>
          </select>
        </div>
      </div>

      <div class="flex flex-col gap-4 pt-4 border-t border-slate-800">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-white font-medium">Permitir registros</p>
            <p class="text-slate-500 text-xs">Nuevas empresas pueden registrarse</p>
          </div>
          <label class="relative inline-flex items-center cursor-pointer">
            <input type="checkbox" bind:checked={config.allow_signup} class="sr-only peer" />
            <div class="w-11 h-6 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-500"></div>
          </label>
        </div>

        <div class="flex items-center justify-between">
          <div>
            <p class="text-white font-medium">Modo mantenimiento</p>
            <p class="text-slate-500 text-xs">Bloquea el acceso a todas las empresas</p>
          </div>
          <label class="relative inline-flex items-center cursor-pointer">
            <input type="checkbox" bind:checked={config.maintenance_mode} class="sr-only peer" />
            <div class="w-11 h-6 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-amber-500"></div>
          </label>
        </div>
      </div>

      <div class="flex justify-end pt-4">
        <button 
          on:click={saveConfig}
          disabled={saving}
          class="px-6 h-12 rounded-xl bg-emerald-500 text-slate-900 font-semibold hover:bg-emerald-400 transition-colors flex items-center gap-2 disabled:opacity-50"
        >
          {#if saving}
            <Loader2 class="animate-spin" size={18} />
          {:else}
            <Save size={18} />
          {/if}
          Guardar Configuración
        </button>
      </div>
    </div>
  </div>
</div>
