<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/utils/api';
  import { 
    Search, 
    Plus, 
    Edit, 
    Trash2, 
    MoreVertical,
    CheckCircle,
    XCircle,
    AlertTriangle,
    Clock,
    Building2,
    X,
    Loader2,
    Eye,
    EyeOff,
    RefreshCw
  } from 'lucide-svelte';

  let tenants = [];
  let loading = true;
  let searchQuery = '';
  let filterPlan = 'all';
  let filterStatus = 'all';

  let showModal = false;
  let showDeleteConfirm = false;
  let selectedTenant = null;
  let saving = false;
  let deleting = false;

  let editForm = {
    business_name: '',
    business_ruc: '',
    business_address: '',
    business_phone: '',
    is_active: true,
    plan_type: 'Free',
    invoice_limit: 50,
    plan_end_date: '',
    sunat_usuario_sol: '',
    sunat_clave_sol: '',
    sunat_cert_password: '',
    sunat_cert_url: ''
  };

  onMount(async () => {
    await loadTenants();
  });

  async function loadTenants() {
    loading = true;
    try {
      tenants = await api.get('/superadmin/tenants?limit=1000');
    } catch (e) {
      console.error('Error loading tenants:', e);
    } finally {
      loading = false;
    }
  }

  $: filteredTenants = tenants.filter(t => {
    const matchesSearch = !searchQuery || 
      t.business_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.business_ruc?.includes(searchQuery);
    
    const matchesPlan = filterPlan === 'all' || t.plan_type === filterPlan;
    const matchesStatus = filterStatus === 'all' || 
      (filterStatus === 'active' && t.is_active) ||
      (filterStatus === 'inactive' && !t.is_active);
    
    return matchesSearch && matchesPlan && matchesStatus;
  });

  function openCreate() {
    selectedTenant = null;
    editForm = {
      business_name: '',
      business_ruc: '',
      business_address: '',
      business_phone: '',
      is_active: true,
      plan_type: 'Free',
      invoice_limit: 50,
      plan_end_date: '',
      sunat_usuario_sol: '',
      sunat_clave_sol: '',
      sunat_cert_password: '',
      sunat_cert_url: ''
    };
    showModal = true;
  }

  function openEdit(tenant) {
    selectedTenant = tenant;
    editForm = {
      business_name: tenant.business_name || '',
      business_ruc: tenant.business_ruc || '',
      business_address: tenant.business_address || '',
      business_phone: tenant.business_phone || '',
      is_active: tenant.is_active ?? true,
      plan_type: tenant.plan_type || 'Free',
      invoice_limit: tenant.invoice_limit || 50,
      plan_end_date: tenant.plan_end_date ? tenant.plan_end_date.split('T')[0] : '',
      sunat_usuario_sol: tenant.sunat_usuario_sol || '',
      sunat_clave_sol: '',
      sunat_cert_password: '',
      sunat_cert_url: tenant.sunat_cert_url || ''
    };
    showModal = true;
  }

  function openDelete(tenant) {
    selectedTenant = tenant;
    showDeleteConfirm = true;
  }

  async function saveTenant() {
    saving = true;
    try {
      const data = { ...editForm };
      if (!data.sunat_clave_sol) delete data.sunat_clave_sol;
      if (!data.sunat_cert_password) delete data.sunat_cert_password;
      if (!data.plan_end_date) delete data.plan_end_date;

      if (selectedTenant) {
        await api.patch(`/superadmin/tenants/${selectedTenant.id}`, data);
      } else {
        await api.post('/tenants/', data);
      }
      
      await loadTenants();
      showModal = false;
    } catch (e) {
      alert('Error al guardar: ' + e.message);
    } finally {
      saving = false;
    }
  }

  async function deleteTenant() {
    deleting = true;
    try {
      await api.delete(`/superadmin/tenants/${selectedTenant.id}`);
      await loadTenants();
      showDeleteConfirm = false;
      selectedTenant = null;
    } catch (e) {
      alert('Error al eliminar: ' + e.message);
    } finally {
      deleting = false;
    }
  }

  function getPlanColor(plan) {
    switch(plan?.toLowerCase()) {
      case 'premium': return 'bg-purple-500/10 text-purple-400 border-purple-500/20';
      case 'pro': return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
      default: return 'bg-slate-700/50 text-slate-400 border-slate-600';
    }
  }

  function isExpired(date) {
    if (!date) return false;
    return new Date(date) < new Date();
  }

  function isExpiringSoon(date) {
    if (!date) return false;
    const thirtyDays = new Date();
    thirtyDays.setDate(thirtyDays.getDate() + 30);
    return new Date(date) <= thirtyDays && new Date(date) > new Date();
  }
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
    <div>
      <h1 class="text-2xl font-bold text-white">Empresas</h1>
      <p class="text-slate-500 text-sm">Gestiona todas las imprentas del sistema</p>
    </div>
    <button 
      on:click={openCreate}
      class="inline-flex items-center gap-2 px-4 py-2.5 bg-emerald-500 hover:bg-emerald-400 text-slate-900 font-semibold rounded-xl transition-all"
    >
      <Plus size={18} />
      Nueva Empresa
    </button>
  </div>

  <!-- Filtros -->
  <div class="flex flex-col md:flex-row gap-4">
    <div class="relative flex-1">
      <Search class="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
      <input
        type="text"
        bind:value={searchQuery}
        placeholder="Buscar por nombre o RUC..."
        class="w-full h-12 pl-12 pr-4 bg-slate-900 border border-slate-800 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
      />
    </div>
    <select 
      bind:value={filterPlan}
      class="h-12 px-4 bg-slate-900 border border-slate-800 rounded-xl text-white focus:outline-none focus:border-emerald-500"
    >
      <option value="all">Todos los planes</option>
      <option value="Free">Free</option>
      <option value="Pro">Pro</option>
      <option value="Premium">Premium</option>
    </select>
    <select 
      bind:value={filterStatus}
      class="h-12 px-4 bg-slate-900 border border-slate-800 rounded-xl text-white focus:outline-none focus:border-emerald-500"
    >
      <option value="all">Todos los estados</option>
      <option value="active">Activas</option>
      <option value="inactive">Inactivas</option>
    </select>
  </div>

  <!-- Tabla -->
  <div class="bg-slate-900 rounded-2xl border border-slate-800 overflow-hidden">
    {#if loading}
      <div class="p-12 flex items-center justify-center">
        <Loader2 class="text-emerald-500 animate-spin" size={32} />
      </div>
    {:else if filteredTenants.length === 0}
      <div class="p-12 text-center">
        <Building2 class="text-slate-600 mx-auto mb-4" size={48} />
        <p class="text-slate-400">No se encontraron empresas</p>
      </div>
    {:else}
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead class="bg-slate-800/50">
            <tr>
              <th class="px-6 py-4 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">Empresa</th>
              <th class="px-6 py-4 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">Plan</th>
              <th class="px-6 py-4 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">Facturas</th>
              <th class="px-6 py-4 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">SUNAT</th>
              <th class="px-6 py-4 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">Estado</th>
              <th class="px-6 py-4 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">Vencimiento</th>
              <th class="px-6 py-4 text-right text-xs font-semibold text-slate-400 uppercase tracking-wider">Acciones</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-800">
            {#each filteredTenants as tenant}
              <tr class="hover:bg-slate-800/30 transition-colors">
                <td class="px-6 py-4">
                  <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-xl bg-slate-700 flex items-center justify-center text-white font-bold">
                      {tenant.business_name?.[0] || 'E'}
                    </div>
                    <div>
                      <p class="text-white font-medium">{tenant.business_name}</p>
                      <p class="text-slate-500 text-xs">RUC: {tenant.business_ruc}</p>
                    </div>
                  </div>
                </td>
                <td class="px-6 py-4">
                  <span class={`px-3 py-1 rounded-lg text-xs font-semibold border ${getPlanColor(tenant.plan_type)}`}>
                    {tenant.plan_type || 'Free'}
                  </span>
                </td>
                <td class="px-6 py-4">
                  <div class="w-24">
                    <div class="flex justify-between text-xs mb-1">
                      <span class="text-slate-400">{tenant.invoices_used || 0}</span>
                      <span class="text-slate-500">/ {tenant.invoice_limit || 50}</span>
                    </div>
                    <div class="h-1.5 bg-slate-700 rounded-full overflow-hidden">
                      <div 
                        class="h-full bg-emerald-500 rounded-full"
                        style="width: {Math.min(((tenant.invoices_used || 0) / (tenant.invoice_limit || 50)) * 100, 100)}%"
                      ></div>
                    </div>
                  </div>
                </td>
                <td class="px-6 py-4">
                  {#if tenant.sunat_usuario_sol && tenant.sunat_cert_url}
                    <span class="inline-flex items-center gap-1 text-emerald-400 text-xs font-medium">
                      <CheckCircle size={14} /> Configurado
                    </span>
                  {:else}
                    <span class="inline-flex items-center gap-1 text-amber-400 text-xs font-medium">
                      <AlertTriangle size={14} /> Pendiente
                    </span>
                  {/if}
                </td>
                <td class="px-6 py-4">
                  {#if tenant.is_active}
                    <span class="inline-flex items-center gap-1 text-emerald-400 text-xs font-medium">
                      <CheckCircle size={14} /> Activo
                    </span>
                  {:else}
                    <span class="inline-flex items-center gap-1 text-red-400 text-xs font-medium">
                      <XCircle size={14} /> Inactivo
                    </span>
                  {/if}
                </td>
                <td class="px-6 py-4">
                  {#if tenant.plan_end_date}
                    {#if isExpired(tenant.plan_end_date)}
                      <span class="text-red-400 text-xs font-medium flex items-center gap-1">
                        <AlertTriangle size={14} /> Vencido
                      </span>
                    {:else if isExpiringSoon(tenant.plan_end_date)}
                      <span class="text-amber-400 text-xs font-medium flex items-center gap-1">
                        <Clock size={14} /> {new Date(tenant.plan_end_date).toLocaleDateString()}
                      </span>
                    {:else}
                      <span class="text-slate-400 text-xs">
                        {new Date(tenant.plan_end_date).toLocaleDateString()}
                      </span>
                    {/if}
                  {:else}
                    <span class="text-slate-600 text-xs">-</span>
                  {/if}
                </td>
                <td class="px-6 py-4">
                  <div class="flex items-center justify-end gap-2">
                    <button 
                      on:click={() => openEdit(tenant)}
                      class="p-2 rounded-lg bg-slate-800 text-slate-400 hover:text-emerald-400 hover:bg-slate-700 transition-colors"
                      title="Editar"
                    >
                      <Edit size={16} />
                    </button>
                    <button 
                      on:click={() => openDelete(tenant)}
                      class="p-2 rounded-lg bg-slate-800 text-slate-400 hover:text-red-400 hover:bg-slate-700 transition-colors"
                      title="Eliminar"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </div>
</div>

<!-- Modal Create/Edit -->
{#if showModal}
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
    <div class="bg-slate-900 rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden border border-slate-800">
      <div class="p-6 border-b border-slate-800 flex items-center justify-between">
        <h2 class="text-xl font-bold text-white">
          {selectedTenant ? 'Editar Empresa' : 'Nueva Empresa'}
        </h2>
        <button 
          on:click={() => showModal = false}
          class="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
        >
          <X size={20} />
        </button>
      </div>

      <div class="p-6 space-y-6 overflow-y-auto max-h-[60vh]">
        <!-- Datos básicos -->
        <div class="space-y-4">
          <h3 class="text-sm font-semibold text-slate-400 uppercase tracking-wider">Datos de la Empresa</h3>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="space-y-2">
              <label class="text-xs text-slate-400">Razón Social</label>
              <input 
                type="text" 
                bind:value={editForm.business_name}
                class="w-full h-11 px-4 bg-slate-800 border border-slate-700 rounded-xl text-white focus:outline-none focus:border-emerald-500"
              />
            </div>
            <div class="space-y-2">
              <label class="text-xs text-slate-400">RUC</label>
              <input 
                type="text" 
                bind:value={editForm.business_ruc}
                class="w-full h-11 px-4 bg-slate-800 border border-slate-700 rounded-xl text-white focus:outline-none focus:border-emerald-500"
              />
            </div>
            <div class="space-y-2">
              <label class="text-xs text-slate-400">Dirección</label>
              <input 
                type="text" 
                bind:value={editForm.business_address}
                class="w-full h-11 px-4 bg-slate-800 border border-slate-700 rounded-xl text-white focus:outline-none focus:border-emerald-500"
              />
            </div>
            <div class="space-y-2">
              <label class="text-xs text-slate-400">Teléfono</label>
              <input 
                type="text" 
                bind:value={editForm.business_phone}
                class="w-full h-11 px-4 bg-slate-800 border border-slate-700 rounded-xl text-white focus:outline-none focus:border-emerald-500"
              />
            </div>
          </div>
        </div>

        <!-- Suscripción -->
        <div class="space-y-4">
          <h3 class="text-sm font-semibold text-slate-400 uppercase tracking-wider">Suscripción</h3>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div class="space-y-2">
              <label class="text-xs text-slate-400">Plan</label>
              <select 
                bind:value={editForm.plan_type}
                class="w-full h-11 px-4 bg-slate-800 border border-slate-700 rounded-xl text-white focus:outline-none focus:border-emerald-500"
              >
                <option value="Free">Free</option>
                <option value="Pro">Pro</option>
                <option value="Premium">Premium</option>
              </select>
            </div>
            <div class="space-y-2">
              <label class="text-xs text-slate-400">Límite Facturas</label>
              <input 
                type="number" 
                bind:value={editForm.invoice_limit}
                class="w-full h-11 px-4 bg-slate-800 border border-slate-700 rounded-xl text-white focus:outline-none focus:border-emerald-500"
              />
            </div>
            <div class="space-y-2">
              <label class="text-xs text-slate-400">Vencimiento</label>
              <input 
                type="date" 
                bind:value={editForm.plan_end_date}
                class="w-full h-11 px-4 bg-slate-800 border border-slate-700 rounded-xl text-white focus:outline-none focus:border-emerald-500"
              />
            </div>
          </div>
          <div class="flex items-center gap-3">
            <input 
              type="checkbox" 
              id="is_active"
              bind:checked={editForm.is_active}
              class="w-4 h-4 rounded bg-slate-800 border-slate-700 text-emerald-500 focus:ring-emerald-500/20"
            />
            <label for="is_active" class="text-sm text-white">Empresa activa</label>
          </div>
        </div>

        <!-- SUNAT -->
        <div class="space-y-4">
          <h3 class="text-sm font-semibold text-slate-400 uppercase tracking-wider">Configuración SUNAT</h3>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="space-y-2">
              <label class="text-xs text-slate-400">Usuario SOL</label>
              <input 
                type="text" 
                bind:value={editForm.sunat_usuario_sol}
                placeholder="MODDATOS"
                class="w-full h-11 px-4 bg-slate-800 border border-slate-700 rounded-xl text-white placeholder-slate-600 focus:outline-none focus:border-emerald-500"
              />
            </div>
            <div class="space-y-2">
              <label class="text-xs text-slate-400">Clave SOL</label>
              <input 
                type="password" 
                bind:value={editForm.sunat_clave_sol}
                placeholder="••••••••"
                class="w-full h-11 px-4 bg-slate-800 border border-slate-700 rounded-xl text-white placeholder-slate-600 focus:outline-none focus:border-emerald-500"
              />
            </div>
            <div class="space-y-2">
              <label class="text-xs text-slate-400">Password Certificado</label>
              <input 
                type="password" 
                bind:value={editForm.sunat_cert_password}
                placeholder="Pin del .p12"
                class="w-full h-11 px-4 bg-slate-800 border border-slate-700 rounded-xl text-white placeholder-slate-600 focus:outline-none focus:border-emerald-500"
              />
            </div>
            <div class="space-y-2">
              <label class="text-xs text-slate-400">URL Certificado (.p12)</label>
              <input 
                type="text" 
                bind:value={editForm.sunat_cert_url}
                placeholder="https://..."
                class="w-full h-11 px-4 bg-slate-800 border border-slate-700 rounded-xl text-white placeholder-slate-600 focus:outline-none focus:border-emerald-500"
              />
            </div>
          </div>
        </div>
      </div>

      <div class="p-6 border-t border-slate-800 flex justify-end gap-3">
        <button 
          on:click={() => showModal = false}
          class="px-6 h-12 rounded-xl bg-slate-800 text-white font-medium hover:bg-slate-700 transition-colors"
        >
          Cancelar
        </button>
        <button 
          on:click={saveTenant}
          disabled={saving}
          class="px-6 h-12 rounded-xl bg-emerald-500 text-slate-900 font-semibold hover:bg-emerald-400 transition-colors flex items-center gap-2 disabled:opacity-50"
        >
          {#if saving}
            <Loader2 class="animate-spin" size={18} />
          {/if}
          Guardar
        </button>
      </div>
    </div>
  </div>
{/if}

<!-- Confirm Delete -->
{#if showDeleteConfirm}
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
    <div class="bg-slate-900 rounded-2xl w-full max-w-md border border-slate-800 p-6">
      <div class="text-center">
        <div class="w-16 h-16 rounded-full bg-red-500/10 flex items-center justify-center mx-auto mb-4">
          <AlertTriangle class="text-red-500" size={32} />
        </div>
        <h3 class="text-xl font-bold text-white mb-2">¿Eliminar Empresa?</h3>
        <p class="text-slate-400 mb-6">
          ¿Estás seguro de eliminar <strong class="text-white">{selectedTenant?.business_name}</strong>? 
          Esta acción no se puede deshacer y eliminará todos los datos asociados.
        </p>
        <div class="flex gap-3">
          <button 
            on:click={() => showDeleteConfirm = false}
            class="flex-1 h-12 rounded-xl bg-slate-800 text-white font-medium hover:bg-slate-700 transition-colors"
          >
            Cancelar
          </button>
          <button 
            on:click={deleteTenant}
            disabled={deleting}
            class="flex-1 h-12 rounded-xl bg-red-500 text-white font-semibold hover:bg-red-400 transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {#if deleting}
              <Loader2 class="animate-spin" size={18} />
            {/if}
            Eliminar
          </button>
        </div>
      </div>
    </div>
  </div>
{/if}
