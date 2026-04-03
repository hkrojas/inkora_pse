<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/utils/api';
  import { 
    Search, 
    Plus, 
    Edit, 
    Trash2,
    Shield,
    User,
    Mail,
    Building2,
    X,
    Loader2,
    AlertTriangle
  } from 'lucide-svelte';

  let users = [];
  let tenants = [];
  let loading = true;
  let searchQuery = '';
  let filterRol = 'all';

  let showModal = false;
  let showDeleteConfirm = false;
  let selectedUser = null;
  let saving = false;
  let deleting = false;

  let editForm = {
    email: '',
    password: '',
    nombre_completo: '',
    rol: 'vendedor',
    tenant_id: null,
    is_superadmin: false
  };

  onMount(async () => {
    await Promise.all([loadUsers(), loadTenants()]);
  });

  async function loadUsers() {
    loading = true;
    try {
      users = await api.get('/superadmin/usuarios?limit=1000');
    } catch (e) {
      console.error('Error loading users:', e);
    } finally {
      loading = false;
    }
  }

  async function loadTenants() {
    try {
      tenants = await api.get('/superadmin/tenants?limit=1000');
    } catch (e) {
      console.error('Error loading tenants:', e);
    }
  }

  $: filteredUsers = users.filter(u => {
    const matchesSearch = !searchQuery || 
      u.email?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      u.nombre_completo?.toLowerCase().includes(searchQuery.toLowerCase());
    
    const matchesRol = filterRol === 'all' || u.rol === filterRol;
    
    return matchesSearch && matchesRol;
  });

  function openCreate() {
    selectedUser = null;
    editForm = {
      email: '',
      password: '',
      nombre_completo: '',
      rol: 'vendedor',
      tenant_id: tenants[0]?.id || null,
      is_superadmin: false
    };
    showModal = true;
  }

  function openEdit(user) {
    selectedUser = user;
    editForm = {
      email: user.email,
      password: '',
      nombre_completo: user.nombre_completo || '',
      rol: user.rol || 'vendedor',
      tenant_id: user.tenant_id,
      is_superadmin: user.is_superadmin || false
    };
    showModal = true;
  }

  function openDelete(user) {
    selectedUser = user;
    showDeleteConfirm = true;
  }

  async function saveUser() {
    saving = true;
    try {
      if (selectedUser) {
        const data = { ...editForm };
        if (!data.password) delete data.password;
        delete data.email;
        await api.patch(`/users/${selectedUser.id}`, data);
      } else {
        await api.post('/register', editForm);
      }
      
      await loadUsers();
      showModal = false;
    } catch (e) {
      alert('Error al guardar: ' + e.message);
    } finally {
      saving = false;
    }
  }

  async function deleteUser() {
    deleting = true;
    try {
      await api.delete(`/users/${selectedUser.id}`);
      await loadUsers();
      showDeleteConfirm = false;
      selectedUser = null;
    } catch (e) {
      alert('Error al eliminar: ' + e.message);
    } finally {
      deleting = false;
    }
  }

  function getTenantName(tenantId) {
    const tenant = tenants.find(t => t.id === tenantId);
    return tenant?.business_name || 'Sin asignar';
  }

  function getRolColor(rol) {
    switch(rol) {
      case 'superadmin': return 'bg-purple-500/10 text-purple-400 border-purple-500/20';
      case 'admin': return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
      default: return 'bg-slate-700/50 text-slate-400 border-slate-600';
    }
  }
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
    <div>
      <h1 class="text-2xl font-bold text-white">Usuarios</h1>
      <p class="text-slate-500 text-sm">Gestiona todos los usuarios del sistema</p>
    </div>
    <button 
      on:click={openCreate}
      class="inline-flex items-center gap-2 px-4 py-2.5 bg-emerald-500 hover:bg-emerald-400 text-slate-900 font-semibold rounded-xl transition-all"
    >
      <Plus size={18} />
      Nuevo Usuario
    </button>
  </div>

  <!-- Filtros -->
  <div class="flex flex-col md:flex-row gap-4">
    <div class="relative flex-1">
      <Search class="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
      <input
        type="text"
        bind:value={searchQuery}
        placeholder="Buscar por email o nombre..."
        class="w-full h-12 pl-12 pr-4 bg-slate-900 border border-slate-800 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
      />
    </div>
    <select 
      bind:value={filterRol}
      class="h-12 px-4 bg-slate-900 border border-slate-800 rounded-xl text-white focus:outline-none focus:border-emerald-500"
    >
      <option value="all">Todos los roles</option>
      <option value="superadmin">Superadmin</option>
      <option value="admin">Admin</option>
      <option value="vendedor">Vendedor</option>
    </select>
  </div>

  <!-- Tabla -->
  <div class="bg-slate-900 rounded-2xl border border-slate-800 overflow-hidden">
    {#if loading}
      <div class="p-12 flex items-center justify-center">
        <Loader2 class="text-emerald-500 animate-spin" size={32} />
      </div>
    {:else if filteredUsers.length === 0}
      <div class="p-12 text-center">
        <User class="text-slate-600 mx-auto mb-4" size={48} />
        <p class="text-slate-400">No se encontraron usuarios</p>
      </div>
    {:else}
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead class="bg-slate-800/50">
            <tr>
              <th class="px-6 py-4 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">Usuario</th>
              <th class="px-6 py-4 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">Empresa</th>
              <th class="px-6 py-4 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">Rol</th>
              <th class="px-6 py-4 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">Estado</th>
              <th class="px-6 py-4 text-right text-xs font-semibold text-slate-400 uppercase tracking-wider">Acciones</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-800">
            {#each filteredUsers as user}
              <tr class="hover:bg-slate-800/30 transition-colors">
                <td class="px-6 py-4">
                  <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-full bg-slate-700 flex items-center justify-center text-white font-bold">
                      {user.email?.[0]?.toUpperCase() || 'U'}
                    </div>
                    <div>
                      <p class="text-white font-medium">{user.nombre_completo || 'Sin nombre'}</p>
                      <p class="text-slate-500 text-xs">{user.email}</p>
                    </div>
                  </div>
                </td>
                <td class="px-6 py-4">
                  <div class="flex items-center gap-2 text-slate-400 text-sm">
                    <Building2 size={14} />
                    {getTenantName(user.tenant_id)}
                  </div>
                </td>
                <td class="px-6 py-4">
                  <span class={`px-3 py-1 rounded-lg text-xs font-semibold border ${getRolColor(user.rol)}`}>
                    {user.rol || 'vendedor'}
                  </span>
                  {#if user.is_superadmin}
                    <span class="ml-2 px-2 py-0.5 rounded text-[10px] bg-purple-500/20 text-purple-400">SUPER</span>
                  {/if}
                </td>
                <td class="px-6 py-4">
                  <span class="inline-flex items-center gap-1 text-emerald-400 text-xs font-medium">
                    <div class="w-2 h-2 rounded-full bg-emerald-400"></div>
                    Activo
                  </span>
                </td>
                <td class="px-6 py-4">
                  <div class="flex items-center justify-end gap-2">
                    <button 
                      on:click={() => openEdit(user)}
                      class="p-2 rounded-lg bg-slate-800 text-slate-400 hover:text-emerald-400 hover:bg-slate-700 transition-colors"
                      title="Editar"
                    >
                      <Edit size={16} />
                    </button>
                    <button 
                      on:click={() => openDelete(user)}
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
    <div class="bg-slate-900 rounded-2xl w-full max-w-lg max-h-[90vh] overflow-hidden border border-slate-800">
      <div class="p-6 border-b border-slate-800 flex items-center justify-between">
        <h2 class="text-xl font-bold text-white">
          {selectedUser ? 'Editar Usuario' : 'Nuevo Usuario'}
        </h2>
        <button 
          on:click={() => showModal = false}
          class="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
        >
          <X size={20} />
        </button>
      </div>

      <div class="p-6 space-y-4 overflow-y-auto max-h-[60vh]">
        <div class="space-y-2">
          <label class="text-xs text-slate-400">Email</label>
          <input 
            type="email" 
            bind:value={editForm.email}
            disabled={selectedUser}
            class="w-full h-11 px-4 bg-slate-800 border border-slate-700 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 disabled:opacity-50"
          />
        </div>

        {#if !selectedUser}
          <div class="space-y-2">
            <label class="text-xs text-slate-400">Contraseña</label>
            <input 
              type="password" 
              bind:value={editForm.password}
              placeholder="••••••••"
              class="w-full h-11 px-4 bg-slate-800 border border-slate-700 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
            />
          </div>
        {/if}

        <div class="space-y-2">
          <label class="text-xs text-slate-400">Nombre Completo</label>
          <input 
            type="text" 
            bind:value={editForm.nombre_completo}
            class="w-full h-11 px-4 bg-slate-800 border border-slate-700 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
          />
        </div>

        <div class="space-y-2">
          <label class="text-xs text-slate-400">Empresa</label>
          <select 
            bind:value={editForm.tenant_id}
            class="w-full h-11 px-4 bg-slate-800 border border-slate-700 rounded-xl text-white focus:outline-none focus:border-emerald-500"
          >
            {#each tenants as tenant}
              <option value={tenant.id}>{tenant.business_name}</option>
            {/each}
          </select>
        </div>

        <div class="space-y-2">
          <label class="text-xs text-slate-400">Rol</label>
          <select 
            bind:value={editForm.rol}
            class="w-full h-11 px-4 bg-slate-800 border border-slate-700 rounded-xl text-white focus:outline-none focus:border-emerald-500"
          >
            <option value="vendedor">Vendedor</option>
            <option value="admin">Admin</option>
            <option value="superadmin">Superadmin</option>
          </select>
        </div>

        <div class="flex items-center gap-3 p-3 rounded-xl bg-slate-800/50 border border-slate-700">
          <input 
            type="checkbox" 
            id="is_superadmin"
            bind:checked={editForm.is_superadmin}
            class="w-4 h-4 rounded bg-slate-800 border-slate-600 text-emerald-500 focus:ring-emerald-500/20"
          />
          <label for="is_superadmin" class="text-sm text-white">
            <span class="font-medium">Superadmin Global</span>
            <span class="text-slate-400 text-xs block">Acceso completo a todas las empresas</span>
          </label>
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
          on:click={saveUser}
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
        <h3 class="text-xl font-bold text-white mb-2">¿Eliminar Usuario?</h3>
        <p class="text-slate-400 mb-6">
          ¿Estás seguro de eliminar a <strong class="text-white">{selectedUser?.email}</strong>? 
          Esta acción no se puede deshacer.
        </p>
        <div class="flex gap-3">
          <button 
            on:click={() => showDeleteConfirm = false}
            class="flex-1 h-12 rounded-xl bg-slate-800 text-white font-medium hover:bg-slate-700 transition-colors"
          >
            Cancelar
          </button>
          <button 
            on:click={deleteUser}
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
