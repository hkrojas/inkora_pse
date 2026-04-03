<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/utils/api';
  import { 
    Search,
    Filter,
    Clock,
    User,
    Building2,
    Settings,
    Trash2,
    Edit,
    Plus,
    LogIn,
    Download,
    Loader2,
    AlertCircle,
    CheckCircle,
    XCircle
  } from 'lucide-svelte';

  let logs = [];
  let loading = true;
  let searchQuery = '';
  let filterAction = 'all';

  const actionTypes = [
    { value: 'all', label: 'Todas las acciones' },
    { value: 'create', label: 'Crear' },
    { value: 'update', label: 'Actualizar' },
    { value: 'delete', label: 'Eliminar' },
    { value: 'login', label: 'Inicio de sesión' },
    { value: 'config_change', label: 'Cambio de configuración' },
  ];

  onMount(async () => {
    await loadLogs();
  });

  async function loadLogs() {
    loading = true;
    try {
      logs = await api.get('/superadmin/audit-logs?limit=200');
    } catch (e) {
      console.error('Error loading logs:', e);
      logs = [];
    } finally {
      loading = false;
    }
  }

  $: filteredLogs = logs.filter(l => {
    const matchesSearch = !searchQuery || 
      l.details?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      l.entity_type?.toLowerCase().includes(searchQuery.toLowerCase());
    
    const matchesAction = filterAction === 'all' || l.action === filterAction;
    
    return matchesSearch && matchesAction;
  });

  function getActionIcon(action) {
    switch(action) {
      case 'create': return Plus;
      case 'update': return Edit;
      case 'delete': return Trash2;
      case 'login': return LogIn;
      case 'config_change': return Settings;
      default: return Activity;
    }
  }

  function getActionColor(action) {
    switch(action) {
      case 'create': return 'bg-emerald-500/10 text-emerald-400';
      case 'update': return 'bg-blue-500/10 text-blue-400';
      case 'delete': return 'bg-red-500/10 text-red-400';
      case 'login': return 'bg-purple-500/10 text-purple-400';
      case 'config_change': return 'bg-amber-500/10 text-amber-400';
      default: return 'bg-slate-500/10 text-slate-400';
    }
  }

  function formatDate(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleString('es-PE', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  function getEntityIcon(entityType) {
    switch(entityType) {
      case 'tenant': return Building2;
      case 'user': return User;
      case 'config': return Settings;
      default: return AlertCircle;
    }
  }
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
    <div>
      <h1 class="text-2xl font-bold text-white">Auditoría</h1>
      <p class="text-slate-500 text-sm">Registro de todas las acciones administrativas</p>
    </div>
    <button 
      on:click={loadLogs}
      class="inline-flex items-center gap-2 px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-white font-medium rounded-xl transition-all"
    >
      <Download size={18} />
      Exportar
    </button>
  </div>

  <!-- Filtros -->
  <div class="flex flex-col md:flex-row gap-4">
    <div class="relative flex-1">
      <Search class="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
      <input
        type="text"
        bind:value={searchQuery}
        placeholder="Buscar en detalles..."
        class="w-full h-12 pl-12 pr-4 bg-slate-900 border border-slate-800 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
      />
    </div>
    <select 
      bind:value={filterAction}
      class="h-12 px-4 bg-slate-900 border border-slate-800 rounded-xl text-white focus:outline-none focus:border-emerald-500"
    >
      {#each actionTypes as type}
        <option value={type.value}>{type.label}</option>
      {/each}
    </select>
  </div>

  <!-- Timeline -->
  <div class="bg-slate-900 rounded-2xl border border-slate-800 overflow-hidden">
    {#if loading}
      <div class="p-12 flex items-center justify-center">
        <Loader2 class="text-emerald-500 animate-spin" size={32} />
      </div>
    {:else if filteredLogs.length === 0}
      <div class="p-12 text-center">
        <AlertCircle class="text-slate-600 mx-auto mb-4" size={48} />
        <p class="text-slate-400">No se encontraron registros</p>
      </div>
    {:else}
      <div class="divide-y divide-slate-800">
        {#each filteredLogs as log}
          <div class="p-4 hover:bg-slate-800/30 transition-colors">
            <div class="flex items-start gap-4">
              <!-- Icono de acción -->
              <div class={`p-2.5 rounded-xl ${getActionColor(log.action)}`}>
                <svelte:component this={getActionIcon(log.action)} size={18} />
              </div>

              <!-- Contenido -->
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 mb-1">
                  <span class="text-white font-medium capitalize">{log.action}</span>
                  {#if log.entity_type}
                    <span class="text-slate-500 text-sm">en</span>
                    <span class="text-emerald-400 font-medium capitalize">{log.entity_type}</span>
                    {#if log.entity_id}
                      <span class="text-slate-600 text-sm">#{log.entity_id}</span>
                    {/if}
                  {/if}
                </div>
                
                {#if log.details}
                  <p class="text-slate-400 text-sm mb-2">{log.details}</p>
                {/if}

                <div class="flex items-center gap-4 text-xs text-slate-500">
                  <span class="flex items-center gap-1">
                    <Clock size={12} />
                    {formatDate(log.timestamp)}
                  </span>
                  {#if log.ip_address}
                    <span>IP: {log.ip_address}</span>
                  {/if}
                </div>
              </div>
            </div>
          </div>
        {/each}
      </div>
    {/if}
  </div>

  <!-- Info -->
  <div class="bg-slate-900/50 rounded-xl p-4 border border-slate-800">
    <p class="text-slate-500 text-xs">
      <strong class="text-slate-400">Nota:</strong> Los logs de auditoría se almacenan durante 90 días. 
      Esta información es útil para cumplimiento legal y resolución de problemas.
    </p>
  </div>
</div>
