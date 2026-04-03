<script>
    import { onMount } from 'svelte';
    import { auth } from '$lib/stores/auth';
    import { api } from '$lib/utils/api';
    import { goto } from '$app/navigation';
    import { 
        Building2, ShieldCheck, CreditCard, 
        Search, Edit, Settings, FileCheck, 
        AlertCircle, CheckCircle2, XCircle, Clock
    } from 'lucide-svelte';

    let tenants = [];
    let loading = true;
    let selectedTenant = null;
    let showModal = false;
    let saving = false;

    // Formulario de Edición
    let editForm = {
        plan_type: '',
        invoice_limit: 0,
        plan_end_date: '',
        sunat_usuario_sol: '',
        sunat_clave_sol: '',
        sunat_cert_password: '',
        sunat_cert_url: ''
    };

    onMount(async () => {
        // Protección de Ruta
        if ($auth.loading) return;
        if (!$auth.isAuthenticated || !$auth.user?.is_superadmin) {
            goto('/dashboard');
            return;
        }
        await loadTenants();
    });

    async function loadTenants() {
        loading = true;
        try {
            tenants = await api.get('/superadmin/tenants');
        } catch (e) {
            console.error(e);
        } finally {
            loading = false;
        }
    }

    function openEdit(tenant) {
        selectedTenant = tenant;
        editForm = {
            plan_type: tenant.plan_type || 'Free',
            invoice_limit: tenant.invoice_limit || 50,
            plan_end_date: tenant.plan_end_date ? tenant.plan_end_date.split('T')[0] : '',
            sunat_usuario_sol: tenant.sunat_usuario_sol || '',
            sunat_clave_sol: '', // No mostrar por seguridad
            sunat_cert_password: '', // No mostrar
            sunat_cert_url: tenant.sunat_cert_url || ''
        };
        showModal = true;
    }

    async function saveTenant() {
        saving = true;
        try {
            const data = { ...editForm };
            // Solo enviar si no están vacíos (para no sobreescribir con vacío si ya hay algo)
            if (!data.sunat_clave_sol) delete data.sunat_clave_sol;
            if (!data.sunat_cert_password) delete data.sunat_cert_password;

            await api.patch(`/superadmin/tenants/${selectedTenant.id}`, data);
            await loadTenants();
            showModal = false;
        } catch (e) {
            alert('Error al actualizar tenant');
        } finally {
            saving = false;
        }
    }

    function getPlanColor(plan) {
        switch(plan?.toLowerCase()) {
            case 'premium': return 'text-purple-600 bg-purple-50 border-purple-100';
            case 'pro': return 'text-blue-600 bg-blue-50 border-blue-100';
            default: return 'text-gray-600 bg-gray-50 border-gray-100';
        }
    }

    function isExpired(date) {
        if (!date) return false;
        return new Date(date) < new Date();
    }
</script>

<div class="p-8 max-w-7xl mx-auto space-y-8">
    <!-- Header -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
            <h1 class="text-3xl font-bold text-on-surface flex items-center gap-3">
                <ShieldCheck class="text-primary" size={32} />
                Torre de Control SaaS
            </h1>
            <p class="text-on-surface-variant text-sm mt-1">Gestión global de imprentas, planes y cumplimiento SUNAT.</p>
        </div>
        <div class="flex items-center gap-2 text-xs font-medium px-3 py-1.5 rounded-full bg-primary/10 text-primary uppercase tracking-wider">
            Superadmin Mode Active
        </div>
    </div>

    <!-- Stats Overview (Opcional - Simulado) -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div class="p-6 rounded-3xl bg-surface-container-low border border-outline-variant/10">
            <div class="flex items-center gap-4">
                <div class="p-3 rounded-2xl bg-primary/10 text-primary">
                    <Building2 size={24} />
                </div>
                <div>
                    <p class="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Total Imprentas</p>
                    <p class="text-2xl font-black text-on-surface">{tenants.length}</p>
                </div>
            </div>
        </div>
        <div class="p-6 rounded-3xl bg-surface-container-low border border-outline-variant/10">
            <div class="flex items-center gap-4">
                <div class="p-3 rounded-2xl bg-secondary/10 text-secondary">
                    <FileCheck size={24} />
                </div>
                <div>
                    <p class="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Facturas del Mes</p>
                    <p class="text-2xl font-black text-on-surface">
                        {tenants.reduce((acc, t) => acc + (t.invoices_used || 0), 0)}
                    </p>
                </div>
            </div>
        </div>
        <div class="p-6 rounded-3xl bg-surface-container-low border border-outline-variant/10">
            <div class="flex items-center gap-4">
                <div class="p-3 rounded-2xl bg-tertiary/10 text-tertiary">
                    <CreditCard size={24} />
                </div>
                <div>
                    <p class="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Suscripciones Active</p>
                    <p class="text-2xl font-black text-on-surface">
                        {tenants.filter(t => t.plan_type !== 'Free').length}
                    </p>
                </div>
            </div>
        </div>
    </div>

    <!-- Main Table -->
    <div class="bg-surface rounded-[2.5rem] border border-outline-variant/10 overflow-hidden shadow-sm">
        <div class="p-6 border-b border-outline-variant/5 flex items-center justify-between bg-surface-container-lowest/50">
            <h2 class="font-bold text-on-surface tracking-tight">Directorio de Clientes SaaS</h2>
            <div class="relative max-w-xs w-full">
                <Search class="absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant" size={16} />
                <input 
                    type="text" 
                    placeholder="Filtrar por RUC o Nombre..." 
                    class="w-full pl-10 pr-4 py-2 bg-surface-container-low border-none rounded-2xl text-xs focus:ring-2 focus:ring-primary/20"
                />
            </div>
        </div>

        <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse">
                <thead class="bg-surface-container-low/50">
                    <tr>
                        <th class="px-6 py-4 text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Imprenta</th>
                        <th class="px-6 py-4 text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Plan & Vencimiento</th>
                        <th class="px-6 py-4 text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Uso de Facturas</th>
                        <th class="px-6 py-4 text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">SUNAT Config</th>
                        <th class="px-6 py-4 text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Acciones</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-outline-variant/5">
                    {#each tenants as tenant}
                        <tr class="hover:bg-surface-container-lowest transition-colors group">
                            <td class="px-6 py-5">
                                <div class="flex items-center gap-3">
                                    <div class="w-10 h-10 rounded-xl bg-surface-container-high flex items-center justify-center text-primary font-bold">
                                        {tenant.business_name[0]}
                                    </div>
                                    <div class="flex flex-col">
                                        <span class="text-sm font-semibold text-on-surface group-hover:text-primary transition-colors">{tenant.business_name}</span>
                                        <span class="text-[10px] text-on-surface-variant">RUC: {tenant.business_ruc}</span>
                                    </div>
                                </div>
                            </td>
                            <td class="px-6 py-5">
                                <div class="flex flex-col gap-1.5">
                                    <span class={`px-2 py-0.5 rounded-lg text-[10px] font-bold w-fit border ${getPlanColor(tenant.plan_type)}`}>
                                        {tenant.plan_type}
                                    </span>
                                    <span class={`text-[10px] flex items-center gap-1 ${isExpired(tenant.plan_end_date) ? 'text-error' : 'text-on-surface-variant'}`}>
                                        <Clock size={10} />
                                        {tenant.plan_end_date ? new Date(tenant.plan_end_date).toLocaleDateString() : 'Sin fecha'}
                                    </span>
                                </div>
                            </td>
                            <td class="px-6 py-5">
                                <div class="w-full max-w-[120px] space-y-1.5">
                                    <div class="flex justify-between text-[10px] font-medium">
                                        <span class="text-on-surface-variant">{tenant.invoices_used || 0} / {tenant.invoice_limit || 50}</span>
                                        <span class="text-primary">{Math.round((tenant.invoices_used/tenant.invoice_limit)*100) || 0}%</span>
                                    </div>
                                    <div class="h-1.5 w-full bg-surface-container-high rounded-full overflow-hidden">
                                        <div 
                                            class="h-full bg-primary rounded-full" 
                                            style="width: {Math.min((tenant.invoices_used/tenant.invoice_limit)*100, 100)}%"
                                        ></div>
                                    </div>
                                </div>
                            </td>
                            <td class="px-6 py-5">
                                {#if tenant.sunat_usuario_sol && tenant.sunat_cert_url}
                                    <div class="flex items-center gap-1.5 text-success font-bold text-[10px]">
                                        <CheckCircle2 size={12} /> LISTO
                                    </div>
                                {:else}
                                    <div class="flex items-center gap-1.5 text-error font-bold text-[10px]">
                                        <AlertCircle size={12} /> PENDIENTE
                                    </div>
                                {/if}
                            </td>
                            <td class="px-6 py-5">
                                <button 
                                    on:click={() => openEdit(tenant)}
                                    class="p-2 rounded-xl bg-surface-container-low text-on-surface-variant hover:text-primary hover:bg-primary/10 transition-all border border-transparent hover:border-primary/20"
                                >
                                    <Edit size={16} />
                                </button>
                            </td>
                        </tr>
                    {/each}
                </tbody>
            </table>
        </div>
    </div>
</div>

<!-- Modal de Configuración -->
{#if showModal}
    <div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-scrim/40 backdrop-blur-sm">
        <div class="bg-surface rounded-2xl sm:rounded-[2.5rem] w-full max-w-2xl overflow-hidden shadow-2xl border border-outline-variant/10 animate-in fade-in zoom-in duration-200 mx-2">
            <div class="p-8 border-b border-outline-variant/5 bg-surface-container-lowest/50 flex justify-between items-center">
                <div>
                    <h3 class="text-xl font-bold text-on-surface">Configurar Imprenta</h3>
                    <p class="text-on-surface-variant text-xs mt-1">{selectedTenant?.business_name} - {selectedTenant?.business_ruc}</p>
                </div>
                <button on:click={() => showModal = false} class="p-2 rounded-full hover:bg-surface-container-high transition-colors">
                    <XCircle size={24} class="text-on-surface-variant" />
                </button>
            </div>

            <div class="p-4 sm:p-8 space-y-8 overflow-y-auto max-h-[70vh]">
                <!-- Sección Plan -->
                <div class="space-y-4">
                    <h4 class="text-[10px] font-bold text-primary uppercase tracking-[0.2em]">Gestión de Suscripción</h4>
                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div class="space-y-1.5">
                            <label class="text-[10px] font-bold px-1 text-on-surface-variant">PLAN ACTUAL</label>
                            <select bind:value={editForm.plan_type} class="w-full h-11 px-4 rounded-xl bg-surface-container-low border-none focus:ring-2 focus:ring-primary/20 text-sm">
                                <option value="Free">Free</option>
                                <option value="Pro">Pro</option>
                                <option value="Premium">Premium</option>
                            </select>
                        </div>
                        <div class="space-y-1.5">
                            <label class="text-[10px] font-bold px-1 text-on-surface-variant">LÍMITE FACTURAS</label>
                            <input type="number" bind:value={editForm.invoice_limit} class="w-full h-11 px-4 rounded-xl bg-surface-container-low border-none focus:ring-2 focus:ring-primary/20 text-sm" />
                        </div>
                        <div class="space-y-1.5">
                            <label class="text-[10px] font-bold px-1 text-on-surface-variant">VENCIMIENTO</label>
                            <input type="date" bind:value={editForm.plan_end_date} class="w-full h-11 px-4 rounded-xl bg-surface-container-low border-none focus:ring-2 focus:ring-primary/20 text-sm" />
                        </div>
                    </div>
                </div>

                <!-- Sección SUNAT -->
                <div class="space-y-4 pt-4 border-t border-outline-variant/5">
                    <h4 class="text-[10px] font-bold text-tertiary uppercase tracking-[0.2em]">Configuración SUNAT (Producción)</h4>
                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div class="space-y-1.5">
                            <label class="text-[10px] font-bold px-1 text-on-surface-variant">USUARIO SOL</label>
                            <input type="text" bind:value={editForm.sunat_usuario_sol} placeholder="MODDATOS" class="w-full h-11 px-4 rounded-xl bg-surface-container-low border-none focus:ring-2 focus:ring-tertiary/20 text-sm" />
                        </div>
                        <div class="space-y-1.5">
                            <label class="text-[10px] font-bold px-1 text-on-surface-variant">CLAVE SOL</label>
                            <input type="password" bind:value={editForm.sunat_clave_sol} placeholder="********" class="w-full h-11 px-4 rounded-xl bg-surface-container-low border-none focus:ring-2 focus:ring-tertiary/20 text-sm" />
                        </div>
                        <div class="space-y-1.5">
                            <label class="text-[10px] font-bold px-1 text-on-surface-variant">PASSWORD CERTIFICADO</label>
                            <input type="password" bind:value={editForm.sunat_cert_password} placeholder="Pin del .p12" class="w-full h-11 px-4 rounded-xl bg-surface-container-low border-none focus:ring-2 focus:ring-tertiary/20 text-sm" />
                        </div>
                        <div class="space-y-1.5">
                            <label class="text-[10px] font-bold px-1 text-on-surface-variant">CERTIFICADO URL (.PFX / .P12)</label>
                            <input type="text" bind:value={editForm.sunat_cert_url} placeholder="https://..." class="w-full h-11 px-4 rounded-xl bg-surface-container-low border-none focus:ring-2 focus:ring-tertiary/20 text-sm" />
                        </div>
                    </div>
                    <p class="text-[10px] text-on-surface-variant italic">Nota: Para subir un certificado, usa el bucket 'printflow-archivos' y pega aquí la URL pública.</p>
                </div>
            </div>

            <div class="p-4 sm:p-8 bg-surface-container-lowest/50 border-t border-outline-variant/5 flex flex-col sm:flex-row gap-3">
                <button 
                    on:click={() => showModal = false}
                    class="flex-1 h-12 rounded-2xl bg-surface-container-high text-on-surface font-bold hover:bg-surface-container-highest transition-all"
                >
                    Cancelar
                </button>
                <button 
                    on:click={saveTenant}
                    disabled={saving}
                    class="flex-1 h-12 rounded-2xl bg-primary text-white font-bold hover:shadow-lg hover:shadow-primary/20 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
                >
                    {#if saving}
                        <div class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                    {/if}
                    Guardar Cambios
                </button>
            </div>
        </div>
    </div>
{/if}

<style>
    /* Transiciones suaves */
    :global(body) {
        background-color: #F8FAFC;
    }
</style>
