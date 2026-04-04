<script>
  import { goto } from '$app/navigation';
  import { api } from '$lib/utils/api';
  import {
    glassPanelClass,
    glassPanelStrongClass,
    mutedGlassPanelClass,
    pageEyebrowClass,
    pageSubtitleClass,
    pageTitleClass,
    premiumInputClass,
    premiumPrimaryButtonClass,
    premiumRowHoverClass,
    premiumSecondaryButtonClass
  } from '$lib/utils/uiClasses';
  import { AlertTriangle, Boxes, Pencil, Plus, Search, Trash2, Upload } from 'lucide-svelte';
  import { onMount } from 'svelte';

  const typeFilters = [
    { id: 'todos', label: 'Todos' },
    { id: 'pliegos', label: 'Pliegos' },
    { id: 'tintas', label: 'Tintas' },
    { id: 'acabados', label: 'Acabados' }
  ];

  let isLoading = true;
  let saving = false;
  let deletingId = null;
  let error = '';
  let formError = '';
  let search = '';
  let activeFilter = 'todos';
  let insumos = [];
  let editingId = null;
  let form = createInitialForm();

  function createInitialForm() {
    return {
      nombre: '',
      unidad_compra: 'Resma',
      unidad_consumo: 'Pliego',
      factor_conversion: '1',
      costo_promedio: '0',
      stock_actual: '0',
      umbral_minimo: '50'
    };
  }

  function normalizeText(value) {
    return `${value || ''}`
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .trim();
  }

  function classifyInsumo(nombre) {
    const value = normalizeText(nombre);

    if (['papel', 'pliego', 'resma', 'couche', 'bond', 'kraft', 'cartulina'].some((keyword) => value.includes(keyword))) {
      return 'pliegos';
    }

    if (['tinta', 'toner', 'cyan', 'magenta', 'amarillo', 'black', 'negro'].some((keyword) => value.includes(keyword))) {
      return 'tintas';
    }

    if (['laminado', 'barniz', 'troquel', 'foil', 'hot', 'acabado', 'anillado'].some((keyword) => value.includes(keyword))) {
      return 'acabados';
    }

    return 'otros';
  }

  function formatDecimal(value, digits = 2) {
    return new Intl.NumberFormat('es-PE', {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits
    }).format(Number(value || 0));
  }

  function getStockVariant(insumo) {
    const stock = Number(insumo?.stock_actual || 0);
    const minimum = Number(insumo?.umbral_minimo || 0);

    if (stock <= minimum) {
      return {
        label: 'Crítico',
        classes: 'bg-red-100 text-red-700 border border-red-200'
      };
    }

    if (stock <= minimum * 1.5) {
      return {
        label: 'Bajo',
        classes: 'bg-amber-100 text-amber-700 border border-amber-200'
      };
    }

    return {
      label: 'Estable',
      classes: 'bg-emerald-100 text-emerald-700 border border-emerald-200'
    };
  }

  function getTypeBadge(type) {
    if (type === 'pliegos') return 'bg-sky-100 text-sky-700 border border-sky-200';
    if (type === 'tintas') return 'bg-violet-100 text-violet-700 border border-violet-200';
    if (type === 'acabados') return 'bg-amber-100 text-amber-700 border border-amber-200';
    return 'bg-slate-100 text-slate-700 border border-slate-200';
  }

  function resetForm() {
    editingId = null;
    formError = '';
    form = createInitialForm();
  }

  function startEdit(insumo) {
    editingId = insumo.id;
    formError = '';
    form = {
      nombre: insumo.nombre || '',
      unidad_compra: insumo.unidad_compra || '',
      unidad_consumo: insumo.unidad_consumo || '',
      factor_conversion: `${insumo.factor_conversion ?? 1}`,
      costo_promedio: `${insumo.costo_promedio ?? 0}`,
      stock_actual: `${insumo.stock_actual ?? 0}`,
      umbral_minimo: `${insumo.umbral_minimo ?? 50}`
    };
  }

  async function loadInsumos() {
    isLoading = true;
    error = '';

    try {
      insumos = await api.get('/insumos/');
    } catch (loadError) {
      error = loadError?.message || 'No se pudo cargar el inventario.';
    } finally {
      isLoading = false;
    }
  }

  async function handleSubmit() {
    if (!form.nombre.trim()) {
      formError = 'El nombre del insumo es obligatorio.';
      return;
    }

    saving = true;
    formError = '';

    const payload = {
      nombre: form.nombre.trim(),
      unidad_compra: form.unidad_compra.trim(),
      unidad_consumo: form.unidad_consumo.trim(),
      factor_conversion: Number(form.factor_conversion || 0),
      costo_promedio: Number(form.costo_promedio || 0),
      stock_actual: Number(form.stock_actual || 0),
      umbral_minimo: Number(form.umbral_minimo || 0)
    };

    try {
      if (editingId) {
        await api.put(`/insumos/${editingId}`, payload);
      } else {
        await api.post('/insumos/', payload);
      }

      await loadInsumos();
      resetForm();
    } catch (submitError) {
      formError = submitError?.message || 'No se pudo guardar el insumo.';
    } finally {
      saving = false;
    }
  }

  async function handleDelete(insumo) {
    if (!confirm(`Eliminar "${insumo.nombre}" del catálogo de inventario?`)) {
      return;
    }

    deletingId = insumo.id;
    formError = '';

    try {
      await api.delete(`/insumos/${insumo.id}`);
      await loadInsumos();

      if (editingId === insumo.id) {
        resetForm();
      }
    } catch (deleteError) {
      formError = deleteError?.message || 'No se pudo eliminar el insumo.';
    } finally {
      deletingId = null;
    }
  }

  function getFilterCount(filterId) {
    return insumos.filter((insumo) => filterId === 'todos' || classifyInsumo(insumo.nombre) === filterId).length;
  }

  onMount(loadInsumos);

  $: filteredInsumos = insumos.filter((insumo) => {
    const matchesType = activeFilter === 'todos' || classifyInsumo(insumo.nombre) === activeFilter;
    const term = normalizeText(search);

    if (!term) return matchesType;

    const haystack = [insumo.nombre, insumo.unidad_compra, insumo.unidad_consumo]
      .filter(Boolean)
      .map(normalizeText);

    return matchesType && haystack.some((value) => value.includes(term));
  });

  $: criticalCount = insumos.filter((insumo) => Number(insumo.stock_actual || 0) <= Number(insumo.umbral_minimo || 0)).length;
  $: averageCost = insumos.length > 0
    ? insumos.reduce((sum, insumo) => sum + Number(insumo.costo_promedio || 0), 0) / insumos.length
    : 0;
</script>

<div class="space-y-6">
  <section class="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
    <div class="space-y-2">
      <p class={pageEyebrowClass}>Gestión de inventario</p>
      <div class="space-y-1">
        <h1 class={pageTitleClass}>Almacén</h1>
        <p class={`max-w-3xl ${pageSubtitleClass}`}>
          Controla materias primas, detecta quiebres de stock y mantén listo el catálogo operativo para producción y compras.
        </p>
      </div>
    </div>

    <div class="flex flex-col gap-3 sm:flex-row">
      <button
        type="button"
        on:click={() => goto('/almacen/compras')}
        class={`inline-flex items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-medium ${premiumSecondaryButtonClass}`}
      >
        <Upload class="h-4 w-4" strokeWidth={2} />
        <span>OCR de compras</span>
      </button>

      <button
        type="button"
        on:click={resetForm}
        class={`inline-flex items-center justify-center gap-2 rounded-xl px-5 py-3 text-sm font-semibold ${premiumPrimaryButtonClass}`}
      >
        <Plus class="h-4 w-4" strokeWidth={2.2} />
        <span>Nuevo insumo</span>
      </button>
    </div>
  </section>

  <section class="grid gap-4 md:grid-cols-3">
    <article class={`rounded-[30px] p-5 ${glassPanelClass}`}>
      <p class="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">SKU operativos</p>
      <p class="mt-3 text-3xl font-bold tracking-tight text-slate-900">{insumos.length}</p>
      <p class="mt-2 text-sm text-slate-500">Insumos activos disponibles para planificación y consumo.</p>
    </article>

    <article class="rounded-[30px] border border-red-100/70 bg-white/85 p-5 shadow-[0_18px_40px_rgba(239,68,68,0.08)] backdrop-blur-xl">
      <p class="text-xs font-semibold uppercase tracking-[0.22em] text-red-600">Stock crítico</p>
      <p class="mt-3 text-3xl font-bold tracking-tight text-red-700">{criticalCount}</p>
      <p class="mt-2 text-sm text-red-700/80">Items por debajo del mínimo que requieren reposición inmediata.</p>
    </article>

    <article class={`rounded-[30px] p-5 ${glassPanelClass}`}>
      <p class="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Costo promedio</p>
      <p class="mt-3 text-3xl font-bold tracking-tight text-slate-900">S/ {formatDecimal(averageCost)}</p>
      <p class="mt-2 text-sm text-slate-500">Lectura rápida del ticket medio de materia prima en catálogo.</p>
    </article>
  </section>

  <section class="grid gap-6 xl:grid-cols-[minmax(0,1.35fr)_22rem]">
    <div class="space-y-4">
      <div class={`flex flex-col gap-3 rounded-[30px] p-5 lg:flex-row lg:items-center lg:justify-between ${glassPanelStrongClass}`}>
        <div class="relative max-w-xl flex-1">
          <Search class="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" strokeWidth={1.9} />
          <input
            bind:value={search}
            type="text"
            placeholder="Buscar por insumo o unidad..."
            class={`h-11 w-full rounded-2xl pl-11 pr-4 text-sm text-slate-700 ${premiumInputClass}`}
          />
        </div>

        <div class="flex flex-wrap gap-2">
          {#each typeFilters as filter}
            <button
              type="button"
              on:click={() => activeFilter = filter.id}
              class="inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-medium transition-all duration-200
                {activeFilter === filter.id
                  ? 'border-emerald-200 bg-emerald-50 text-emerald-700 shadow-sm'
                  : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-100 hover:text-slate-900'}"
            >
              <span>{filter.label}</span>
              <span class="rounded-full px-2 py-0.5 text-[11px] font-semibold {activeFilter === filter.id ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500'}">
                {getFilterCount(filter.id)}
              </span>
            </button>
          {/each}
        </div>
      </div>

      <section class={`overflow-hidden rounded-[30px] ${glassPanelStrongClass}`}>
        {#if isLoading}
          <div class="overflow-x-auto" aria-hidden="true">
            <table class="min-w-full border-separate border-spacing-0">
              <thead>
                <tr class="bg-slate-50/60">
                  <th class="px-6 pb-3 pt-5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Insumo</th>
                  <th class="px-6 pb-3 pt-5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Unidades</th>
                  <th class="px-6 pb-3 pt-5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Stock</th>
                  <th class="px-6 pb-3 pt-5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Costo</th>
                  <th class="px-6 pb-3 pt-5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Estado</th>
                  <th class="px-6 pb-3 pt-5 text-right text-xs font-semibold uppercase tracking-wider text-slate-500">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {#each Array.from({ length: 6 }, (_, index) => index) as _, index}
                  <tr class="animate-pulse">
                    <td class="px-6 py-4 {index === 5 ? 'border-b-0' : 'border-b border-slate-200/70'}"><div class="h-4 w-40 rounded-full bg-slate-200"></div></td>
                    <td class="px-6 py-4 {index === 5 ? 'border-b-0' : 'border-b border-slate-200/70'}"><div class="h-4 w-28 rounded-full bg-slate-200"></div></td>
                    <td class="px-6 py-4 {index === 5 ? 'border-b-0' : 'border-b border-slate-200/70'}"><div class="h-4 w-24 rounded-full bg-slate-200"></div></td>
                    <td class="px-6 py-4 {index === 5 ? 'border-b-0' : 'border-b border-slate-200/70'}"><div class="h-4 w-20 rounded-full bg-slate-200"></div></td>
                    <td class="px-6 py-4 {index === 5 ? 'border-b-0' : 'border-b border-slate-200/70'}"><div class="h-7 w-24 rounded-full bg-slate-100"></div></td>
                    <td class="px-6 py-4 text-right {index === 5 ? 'border-b-0' : 'border-b border-slate-200/70'}"><div class="ml-auto h-4 w-16 rounded-full bg-slate-200"></div></td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {:else if error}
          <div class="flex min-h-[280px] flex-col items-center justify-center gap-4 px-6 py-10 text-center">
            <div class="flex h-14 w-14 items-center justify-center rounded-2xl border border-red-200 bg-red-50 text-red-600">
              <AlertTriangle class="h-6 w-6" strokeWidth={1.9} />
            </div>
            <div class="space-y-2">
              <p class="text-lg font-semibold tracking-tight text-slate-900">No se pudo cargar el almacén</p>
              <p class="max-w-md text-sm leading-6 text-slate-500">{error}</p>
            </div>
          </div>
        {:else if filteredInsumos.length === 0}
          <div class="flex min-h-[280px] flex-col items-center justify-center gap-4 px-6 py-10 text-center">
            <div class={`flex h-14 w-14 items-center justify-center rounded-2xl text-slate-400 ${mutedGlassPanelClass}`}>
              <Boxes class="h-6 w-6" strokeWidth={1.9} />
            </div>
            <div class="space-y-2">
              <p class="text-lg font-semibold tracking-tight text-slate-900">No hay insumos para este filtro</p>
              <p class="max-w-md text-sm leading-6 text-slate-500">Prueba con otra búsqueda o registra un nuevo item para poblar el inventario.</p>
            </div>
          </div>
        {:else}
          <div class="overflow-x-auto">
            <table class="min-w-full border-separate border-spacing-0">
              <thead>
                <tr class="bg-slate-50/60">
                  <th class="px-6 pb-3 pt-5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Insumo</th>
                  <th class="px-6 pb-3 pt-5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Unidades</th>
                  <th class="px-6 pb-3 pt-5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Stock</th>
                  <th class="px-6 pb-3 pt-5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Costo</th>
                  <th class="px-6 pb-3 pt-5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Estado</th>
                  <th class="px-6 pb-3 pt-5 text-right text-xs font-semibold uppercase tracking-wider text-slate-500">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {#each filteredInsumos as insumo, index}
                  <tr class={premiumRowHoverClass}>
                    <td class="px-6 py-4 {index === filteredInsumos.length - 1 ? 'border-b-0' : 'border-b border-slate-200/70'}">
                      <div class="space-y-2">
                        <div class="flex flex-wrap items-center gap-2">
                          <p class="text-sm font-semibold text-slate-900">{insumo.nombre}</p>
                          <span class="inline-flex rounded-full px-2.5 py-1 text-[11px] font-semibold {getTypeBadge(classifyInsumo(insumo.nombre))}">
                            {classifyInsumo(insumo.nombre)}
                          </span>
                        </div>
                        <p class="text-xs text-slate-500">Conversión: 1 {insumo.unidad_compra} = {formatDecimal(insumo.factor_conversion, 4)} {insumo.unidad_consumo}</p>
                      </div>
                    </td>

                    <td class="px-6 py-4 text-sm text-slate-600 {index === filteredInsumos.length - 1 ? 'border-b-0' : 'border-b border-slate-200/70'}">
                      <div class="space-y-1">
                        <p>{insumo.unidad_compra}</p>
                        <p class="text-xs text-slate-500">{insumo.unidad_consumo}</p>
                      </div>
                    </td>

                    <td class="px-6 py-4 {index === filteredInsumos.length - 1 ? 'border-b-0' : 'border-b border-slate-200/70'}">
                      <div class="space-y-1">
                        <p class="text-sm font-semibold text-slate-900">{formatDecimal(insumo.stock_actual)} {insumo.unidad_consumo}</p>
                        <p class="text-xs text-slate-500">Mínimo {formatDecimal(insumo.umbral_minimo)}</p>
                      </div>
                    </td>

                    <td class="px-6 py-4 text-sm font-semibold text-slate-900 {index === filteredInsumos.length - 1 ? 'border-b-0' : 'border-b border-slate-200/70'}">
                      S/ {formatDecimal(insumo.costo_promedio)}
                    </td>

                    <td class="px-6 py-4 {index === filteredInsumos.length - 1 ? 'border-b-0' : 'border-b border-slate-200/70'}">
                      <span class="inline-flex rounded-full px-3 py-1 text-xs font-semibold {getStockVariant(insumo).classes}">
                        {getStockVariant(insumo).label}
                      </span>
                    </td>

                    <td class="px-6 py-4 text-right {index === filteredInsumos.length - 1 ? 'border-b-0' : 'border-b border-slate-200/70'}">
                      <div class="flex justify-end gap-2">
                        <button
                          type="button"
                          on:click={() => startEdit(insumo)}
                          class="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-500 transition-colors hover:border-emerald-200 hover:text-emerald-600"
                          aria-label="Editar insumo"
                        >
                          <Pencil class="h-4 w-4" strokeWidth={1.9} />
                        </button>

                        <button
                          type="button"
                          on:click={() => handleDelete(insumo)}
                          disabled={deletingId === insumo.id}
                          class="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-500 transition-colors hover:border-red-200 hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-60"
                          aria-label="Eliminar insumo"
                        >
                          <Trash2 class="h-4 w-4" strokeWidth={1.9} />
                        </button>
                      </div>
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {/if}
      </section>
    </div>

    <aside class={`rounded-[30px] p-5 ${glassPanelStrongClass}`}>
      <div class="space-y-5">
        <div class="space-y-1">
          <p class="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">{editingId ? 'Editar insumo' : 'Alta rápida'}</p>
          <h2 class="text-lg font-semibold tracking-tight text-slate-900">{editingId ? 'Actualizar catálogo' : 'Nuevo insumo'}</h2>
        </div>

        <div class="space-y-4">
          <div class="space-y-2">
            <label class="block text-xs font-semibold uppercase tracking-[0.22em] text-slate-500" for="nombre-insumo">Nombre</label>
            <input id="nombre-insumo" bind:value={form.nombre} type="text" placeholder="Ej. Pliego couché 250g" class={`h-11 w-full rounded-2xl px-4 text-sm text-slate-700 ${premiumInputClass}`} />
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div class="space-y-2">
              <label class="block text-xs font-semibold uppercase tracking-[0.22em] text-slate-500" for="unidad-compra">Unidad compra</label>
              <input id="unidad-compra" bind:value={form.unidad_compra} type="text" class={`h-11 w-full rounded-2xl px-4 text-sm text-slate-700 ${premiumInputClass}`} />
            </div>

            <div class="space-y-2">
              <label class="block text-xs font-semibold uppercase tracking-[0.22em] text-slate-500" for="unidad-consumo">Unidad consumo</label>
              <input id="unidad-consumo" bind:value={form.unidad_consumo} type="text" class={`h-11 w-full rounded-2xl px-4 text-sm text-slate-700 ${premiumInputClass}`} />
            </div>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div class="space-y-2">
              <label class="block text-xs font-semibold uppercase tracking-[0.22em] text-slate-500" for="factor-conversion">Factor conversión</label>
              <input id="factor-conversion" bind:value={form.factor_conversion} type="number" min="0.0001" step="0.0001" class={`h-11 w-full rounded-2xl px-4 text-sm text-slate-700 ${premiumInputClass}`} />
            </div>

            <div class="space-y-2">
              <label class="block text-xs font-semibold uppercase tracking-[0.22em] text-slate-500" for="costo-promedio">Costo promedio</label>
              <input id="costo-promedio" bind:value={form.costo_promedio} type="number" min="0" step="0.01" class={`h-11 w-full rounded-2xl px-4 text-sm text-slate-700 ${premiumInputClass}`} />
            </div>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div class="space-y-2">
              <label class="block text-xs font-semibold uppercase tracking-[0.22em] text-slate-500" for="stock-actual">Stock actual</label>
              <input id="stock-actual" bind:value={form.stock_actual} type="number" min="0" step="0.01" class={`h-11 w-full rounded-2xl px-4 text-sm text-slate-700 ${premiumInputClass}`} />
            </div>

            <div class="space-y-2">
              <label class="block text-xs font-semibold uppercase tracking-[0.22em] text-slate-500" for="umbral-minimo">Stock mínimo</label>
              <input id="umbral-minimo" bind:value={form.umbral_minimo} type="number" min="0" step="0.01" class={`h-11 w-full rounded-2xl px-4 text-sm text-slate-700 ${premiumInputClass}`} />
            </div>
          </div>
        </div>

        {#if formError}
          <div class="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {formError}
          </div>
        {/if}

        <div class="flex flex-col gap-3">
          <button
            type="button"
            on:click={handleSubmit}
            disabled={saving}
            class={`inline-flex items-center justify-center rounded-xl px-4 py-3 text-sm font-semibold ${premiumPrimaryButtonClass} disabled:cursor-not-allowed disabled:opacity-70`}
          >
            {saving ? 'Guardando...' : editingId ? 'Actualizar insumo' : 'Crear insumo'}
          </button>

          {#if editingId}
            <button
              type="button"
              on:click={resetForm}
              class={`inline-flex items-center justify-center rounded-xl px-4 py-3 text-sm font-medium ${premiumSecondaryButtonClass}`}
            >
              Cancelar edición
            </button>
          {/if}
        </div>
      </div>
    </aside>
  </section>
</div>
