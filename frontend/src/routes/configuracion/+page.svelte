<script>
  const sections = [
    { id: 'empresa', name: 'Datos de Empresa', icon: 'business' },
    { id: 'pagos', name: 'Pagos e Impuestos', icon: 'credit_card' },
    { id: 'seguridad', name: 'Seguridad y Roles', icon: 'shield' },
    { id: 'notificaciones', name: 'Notificaciones', icon: 'mail' }
  ];

  let activeSection = 'empresa';
  let saving = false;

  function handleSave() {
    saving = true;
    setTimeout(() => { saving = false; }, 1500);
  }
</script>

<div class="space-y-8">
  <!-- Header -->
  <div class="flex flex-col sm:flex-row sm:justify-between sm:items-end gap-4">
    <div>
      <h1 class="font-manrope text-3xl font-extrabold text-primary tracking-tight">Configuración</h1>
      <p class="text-outline font-medium mt-1">Gestiona la identidad visual y los parámetros técnicos de PrintFlow.</p>
    </div>
    <button 
      on:click={handleSave}
      disabled={saving}
      class="btn-primary w-full sm:w-auto flex items-center justify-center gap-2 disabled:opacity-50"
    >
      {#if saving}
        <span class="material-symbols-outlined animate-spin text-lg">progress_activity</span>
        Guardando...
      {:else}
        <span class="material-symbols-outlined text-lg">save</span>
        Guardar Cambios
      {/if}
    </button>
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-4 gap-6 lg:gap-10">
    <!-- Sub-navigation -->
    <aside class="flex lg:flex-col gap-2 overflow-x-auto lg:overflow-x-visible pb-2 lg:pb-0">
      {#each sections as section}
        <button 
          on:click={() => activeSection = section.id}
          class="w-full lg:w-auto flex items-center gap-3 lg:gap-4 p-3 lg:p-4 rounded-xl transition-all font-semibold whitespace-nowrap text-sm
            {activeSection === section.id 
              ? 'bg-primary text-white shadow-lg shadow-primary/20' 
              : 'text-outline hover:bg-surface-container-high hover:text-on-surface'}"
        >
          <span class="material-symbols-outlined text-lg">{section.icon}</span>
          {section.name}
        </button>
      {/each}
    </aside>

    <!-- Content Panel -->
    <div class="lg:col-span-3 bg-surface-container-low p-6 sm:p-8 lg:p-10 rounded-2xl border border-outline-variant/10">
      {#if activeSection === 'empresa'}
        <div class="space-y-8">
          <!-- Logo upload -->
          <div class="flex flex-col sm:flex-row items-start sm:items-center gap-6 sm:gap-8">
            <div class="w-28 h-28 rounded-2xl bg-surface-container-lowest border-2 border-dashed border-outline-variant/20 flex flex-col items-center justify-center relative group overflow-hidden cursor-pointer hover:border-primary/30 transition-colors">
               <span class="material-symbols-outlined text-outline/40 mb-1 group-hover:text-primary transition-colors">upload</span>
               <span class="text-[9px] font-bold text-outline/40 text-center px-2 group-hover:text-primary transition-colors">Subir Logo</span>
               <div class="absolute inset-0 bg-primary/10 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                  <span class="material-symbols-outlined text-primary text-2xl">upload</span>
               </div>
            </div>
            <div>
              <h3 class="font-manrope text-lg font-bold text-on-surface mb-1">Identidad Visual</h3>
              <p class="text-sm text-outline">Este logo aparecerá en todas tus cotizaciones y facturas.</p>
              <p class="text-xs text-outline/60 mt-1">Formatos: PNG, SVG. Máx 2MB.</p>
            </div>
          </div>

          <!-- Form fields -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div class="space-y-2">
              <label class="block font-label text-[10px] font-bold text-outline uppercase tracking-widest pl-1">Razón Social</label>
              <input type="text" value="PrintFlow Solutions S.A.C." class="w-full h-12 px-5 rounded-xl bg-surface-container-lowest border border-outline-variant/10 focus:border-primary/30 focus:ring-2 focus:ring-primary/10 font-medium text-sm transition-all" />
            </div>
            <div class="space-y-2">
              <label class="block font-label text-[10px] font-bold text-outline uppercase tracking-widest pl-1">RUC / Identificación</label>
              <input type="text" value="20123456789" class="w-full h-12 px-5 rounded-xl bg-surface-container-lowest border border-outline-variant/10 focus:border-primary/30 focus:ring-2 focus:ring-primary/10 font-medium text-sm transition-all" />
            </div>
            <div class="space-y-2">
              <label class="block font-label text-[10px] font-bold text-outline uppercase tracking-widest pl-1">Dirección Principal</label>
              <input type="text" value="Av. Industrial 456, Lima" class="w-full h-12 px-5 rounded-xl bg-surface-container-lowest border border-outline-variant/10 focus:border-primary/30 focus:ring-2 focus:ring-primary/10 font-medium text-sm transition-all" />
            </div>
            <div class="space-y-2">
              <label class="block font-label text-[10px] font-bold text-outline uppercase tracking-widest pl-1">Correo de Contacto</label>
              <input type="email" value="contacto@printflow.pe" class="w-full h-12 px-5 rounded-xl bg-surface-container-lowest border border-outline-variant/10 focus:border-primary/30 focus:ring-2 focus:ring-primary/10 font-medium text-sm transition-all" />
            </div>
          </div>
        </div>
      {/if}

      {#if activeSection === 'pagos'}
        <div class="flex flex-col items-center justify-center py-20 text-center space-y-4">
           <div class="p-5 rounded-full bg-tertiary-container/20">
             <span class="material-symbols-outlined text-tertiary text-5xl">credit_card</span>
           </div>
           <p class="font-manrope font-bold text-lg text-on-surface">Módulo de Pagos</p>
           <p class="text-sm text-outline max-w-sm">La configuración de métodos de pago e impuestos estará disponible próximamente.</p>
        </div>
      {/if}

      {#if activeSection === 'seguridad'}
        <div class="flex flex-col items-center justify-center py-20 text-center space-y-4">
           <div class="p-5 rounded-full bg-info-container/20">
             <span class="material-symbols-outlined text-info text-5xl">shield</span>
           </div>
           <p class="font-manrope font-bold text-lg text-on-surface">Seguridad y Roles</p>
           <p class="text-sm text-outline max-w-sm">La gestión de roles y permisos estará disponible próximamente.</p>
        </div>
      {/if}

      {#if activeSection === 'notificaciones'}
        <div class="flex flex-col items-center justify-center py-20 text-center space-y-4">
           <div class="p-5 rounded-full bg-secondary-container/20">
             <span class="material-symbols-outlined text-secondary text-5xl">notifications</span>
           </div>
           <p class="font-manrope font-bold text-lg text-on-surface">Notificaciones</p>
           <p class="text-sm text-outline max-w-sm">La configuración de alertas y notificaciones estará disponible próximamente.</p>
        </div>
      {/if}
    </div>
  </div>
</div>
