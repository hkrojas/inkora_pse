<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/utils/api';
  import { 
    Building2, 
    Users, 
    FileText, 
    CreditCard,
    TrendingUp,
    AlertTriangle,
    CheckCircle,
    Clock,
    Activity,
    Zap
  } from 'lucide-svelte';

  let stats = {
    totalTenants: 0,
    activeTenants: 0,
    totalInvoices: 0,
    activeSubscriptions: 0,
    expiringSoon: 0,
    sunatConfigured: 0
  };
  let recentActivity = [];
  let loading = true;

  onMount(async () => {
    await Promise.all([loadStats(), loadRecentActivity()]);
  });

  async function loadStats() {
    try {
      const tenants = await api.get('/superadmin/tenants?limit=1000');
      
      stats.totalTenants = tenants.length;
      stats.activeTenants = tenants.filter(t => t.is_active).length;
      stats.totalInvoices = tenants.reduce((acc, t) => acc + (t.invoices_used || 0), 0);
      stats.activeSubscriptions = tenants.filter(t => t.plan_type !== 'Free').length;
      
      const thirtyDaysFromNow = new Date();
      thirtyDaysFromNow.setDate(thirtyDaysFromNow.getDate() + 30);
      stats.expiringSoon = tenants.filter(t => {
        if (!t.plan_end_date) return false;
        return new Date(t.plan_end_date) <= thirtyDaysFromNow && new Date(t.plan_end_date) > new Date();
      }).length;
      
      stats.sunatConfigured = tenants.filter(t => t.sunat_usuario_sol && t.sunat_cert_url).length;
    } catch (e) {
      console.error('Error loading stats:', e);
    }
  }

  async function loadRecentActivity() {
    try {
      recentActivity = [
        { type: 'tenant', message: 'Nueva empresa registrada', time: 'Hace 2 horas', icon: Building2 },
        { type: 'invoice', message: 'Factura #001-00500 emitida', time: 'Hace 4 horas', icon: FileText },
        { type: 'subscription', message: 'Plan Pro activado', time: 'Hace 1 día', icon: CreditCard },
        { type: 'user', message: 'Nuevo usuario registrado', time: 'Hace 1 día', icon: Users },
      ];
    } catch (e) {
      console.error('Error loading activity:', e);
    } finally {
      loading = false;
    }
  }

  function formatNumber(num) {
    return new Intl.NumberFormat('es-PE').format(num || 0);
  }
</script>

<div class="space-y-8">
  <!-- Header -->
  <div class="flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-bold text-white">Dashboard</h1>
      <p class="text-slate-500 text-sm">Resumen global del sistema</p>
    </div>
    <div class="flex items-center gap-2 text-xs text-emerald-400 bg-emerald-500/10 px-3 py-1.5 rounded-full">
      <Activity size={14} />
      Sistema activo
    </div>
  </div>

  <!-- Stats Grid -->
  <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
    <!-- Total Empresas -->
    <div class="bg-slate-900 rounded-2xl border border-slate-800 p-6 hover:border-emerald-500/30 transition-all">
      <div class="flex items-start justify-between">
        <div>
          <p class="text-slate-500 text-xs font-medium uppercase tracking-wider">Total Empresas</p>
          <p class="text-3xl font-black text-white mt-2">{formatNumber(stats.totalTenants)}</p>
          <p class="text-emerald-400 text-xs mt-1 flex items-center gap-1">
            <TrendingUp size={12} />
            {stats.activeTenants} activas
          </p>
        </div>
        <div class="p-3 rounded-xl bg-blue-500/10">
          <Building2 class="text-blue-400" size={24} />
        </div>
      </div>
    </div>

    <!-- Facturas del Mes -->
    <div class="bg-slate-900 rounded-2xl border border-slate-800 p-6 hover:border-emerald-500/30 transition-all">
      <div class="flex items-start justify-between">
        <div>
          <p class="text-slate-500 text-xs font-medium uppercase tracking-wider">Facturas Emitidas</p>
          <p class="text-3xl font-black text-white mt-2">{formatNumber(stats.totalInvoices)}</p>
          <p class="text-slate-400 text-xs mt-1">este mes</p>
        </div>
        <div class="p-3 rounded-xl bg-purple-500/10">
          <FileText class="text-purple-400" size={24} />
        </div>
      </div>
    </div>

    <!-- Suscripciones Activas -->
    <div class="bg-slate-900 rounded-2xl border border-slate-800 p-6 hover:border-emerald-500/30 transition-all">
      <div class="flex items-start justify-between">
        <div>
          <p class="text-slate-500 text-xs font-medium uppercase tracking-wider">Suscripciones</p>
          <p class="text-3xl font-black text-white mt-2">{stats.activeSubscriptions}</p>
          <p class="text-emerald-400 text-xs mt-1 flex items-center gap-1">
            <Zap size={12} />
            Plan Pro/Premium
          </p>
        </div>
        <div class="p-3 rounded-xl bg-emerald-500/10">
          <CreditCard class="text-emerald-400" size={24} />
        </div>
      </div>
    </div>

    <!-- SUNAT Configurado -->
    <div class="bg-slate-900 rounded-2xl border border-slate-800 p-6 hover:border-emerald-500/30 transition-all">
      <div class="flex items-start justify-between">
        <div>
          <p class="text-slate-500 text-xs font-medium uppercase tracking-wider">SUNAT</p>
          <p class="text-3xl font-black text-white mt-2">{stats.sunatConfigured}</p>
          <p class="text-amber-400 text-xs mt-1 flex items-center gap-1">
            <AlertTriangle size={12} />
            {stats.totalTenants - stats.sunatConfigured} pendientes
          </p>
        </div>
        <div class="p-3 rounded-xl bg-amber-500/10">
          <CheckCircle class="text-amber-400" size={24} />
        </div>
      </div>
    </div>
  </div>

  <!-- Segunda fila -->
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
    <!-- Alertas -->
    {#if stats.expiringSoon > 0}
      <div class="bg-slate-900 rounded-2xl border border-amber-500/30 p-6">
        <div class="flex items-center gap-3 mb-4">
          <div class="p-2 rounded-lg bg-amber-500/10">
            <Clock class="text-amber-400" size={20} />
          </div>
          <h3 class="text-white font-semibold">Planes por Vencer</h3>
        </div>
        <p class="text-amber-400 text-3xl font-black">{stats.expiringSoon}</p>
        <p class="text-slate-500 text-sm mt-1">empresas en los próximos 30 días</p>
        <a href="/admin/tenants?filter=expiring" class="inline-block mt-4 text-xs text-amber-400 hover:text-amber-300">
          Ver empresas →
        </a>
      </div>
    {/if}

    <!-- Actividad Reciente -->
    <div class="bg-slate-900 rounded-2xl border border-slate-800 p-6 lg:col-span-2">
      <h3 class="text-white font-semibold mb-4">Actividad Reciente</h3>
      <div class="space-y-4">
        {#each recentActivity as activity}
          <div class="flex items-center gap-4 p-3 rounded-xl bg-slate-800/50">
            <div class="p-2 rounded-lg bg-slate-700">
              <svelte:component this={activity.icon} class="text-slate-400" size={16} />
            </div>
            <div class="flex-1">
              <p class="text-white text-sm">{activity.message}</p>
              <p class="text-slate-500 text-xs">{activity.time}</p>
            </div>
          </div>
        {/each}
      </div>
    </div>
  </div>

  <!-- Accesos Rápidos -->
  <div class="bg-slate-900 rounded-2xl border border-slate-800 p-6">
    <h3 class="text-white font-semibold mb-4">Accesos Rápidos</h3>
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <a href="/admin/tenants" class="p-4 rounded-xl bg-slate-800/50 hover:bg-slate-800 border border-slate-700 hover:border-emerald-500/30 transition-all text-center group">
        <Building2 class="text-slate-400 group-hover:text-emerald-400 mx-auto mb-2" size={24} />
        <p class="text-white text-sm font-medium">Gestionar Empresas</p>
      </a>
      <a href="/admin/usuarios" class="p-4 rounded-xl bg-slate-800/50 hover:bg-slate-800 border border-slate-700 hover:border-emerald-500/30 transition-all text-center group">
        <Users class="text-slate-400 group-hover:text-emerald-400 mx-auto mb-2" size={24} />
        <p class="text-white text-sm font-medium">Usuarios</p>
      </a>
      <a href="/admin/config" class="p-4 rounded-xl bg-slate-800/50 hover:bg-slate-800 border border-slate-700 hover:border-emerald-500/30 transition-all text-center group">
        <CreditCard class="text-slate-400 group-hover:text-emerald-400 mx-auto mb-2" size={24} />
        <p class="text-white text-sm font-medium">Planes y Precios</p>
      </a>
      <a href="/admin/audit" class="p-4 rounded-xl bg-slate-800/50 hover:bg-slate-800 border border-slate-700 hover:border-emerald-500/30 transition-all text-center group">
        <Activity class="text-slate-400 group-hover:text-emerald-400 mx-auto mb-2" size={24} />
        <p class="text-white text-sm font-medium">Auditoría</p>
      </a>
    </div>
  </div>
</div>
