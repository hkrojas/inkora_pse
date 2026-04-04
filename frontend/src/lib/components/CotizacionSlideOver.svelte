<script>
  import { api } from '$lib/utils/api';
  import {
    glassPanelClass,
    glassPanelStrongClass,
    mutedGlassPanelClass,
    premiumInputClass,
    premiumPrimaryButtonClass,
    premiumSecondaryButtonClass,
    premiumRowHoverClass
  } from '$lib/utils/uiClasses';
  import {
    Calculator,
    Check,
    ChevronLeft,
    ChevronRight,
    Layers3,
    Package,
    Percent,
    Ruler,
    Search,
    Truck,
    UserRound,
    X
  } from 'lucide-svelte';
  import { createEventDispatcher, onMount } from 'svelte';
  import { cubicOut } from 'svelte/easing';
  import { fade, fly } from 'svelte/transition';

  export let show = false;

  const dispatch = createEventDispatcher();

  const steps = [
    { id: 1, title: 'Cliente', subtitle: 'Cuenta y contacto' },
    { id: 2, title: 'Especificaciones', subtitle: 'Formato y producción' },
    { id: 3, title: 'Costos', subtitle: 'Acabados y total' }
  ];

  const paperOptions = [
    { label: 'Couché 150g', multiplier: 1 },
    { label: 'Couché 250g', multiplier: 1.12 },
    { label: 'Bond 90g', multiplier: 0.92 },
    { label: 'Kraft 200g', multiplier: 1.18 }
  ];

  const finishOptions = [
    { id: 'laminado_mate', label: 'Laminado Mate', cost: 42 },
    { id: 'barniz_uv', label: 'Barniz UV', cost: 65 },
    { id: 'troquelado', label: 'Troquelado', cost: 88 },
    { id: 'hot_stamping', label: 'Hot Stamping', cost: 120 }
  ];

  let loadingCatalogs = true;
  let saving = false;
  let aiBusy = false;
  let currentStep = 1;
  let stepError = '';
  let aiError = '';
  let aiDraftText = '';
  let aiSuggestedClient = '';
  let aiSuggestions = [];
  let clientes = [];
  let productos = [];
  let clientSearch = '';
  let clientName = '';
  let clientDocument = '';
  let clientContact = '';
  let clientAddress = '';

  let formData = createInitialState();

  function createInitialState() {
    return {
      cliente_id: '',
      moneda: 'PEN',
      producto_id: '',
      descripcion: '',
      ancho: '',
      alto: '',
      papel: 'Couché 150g',
      cantidad: 1000,
      acabados: [],
      flete: 0,
      margen: 20
    };
  }

  const panelClass = `rounded-[28px] p-5 ${glassPanelClass}`;
  const softPanelClass = `rounded-[28px] p-5 ${mutedGlassPanelClass}`;
  const fieldClass = `h-12 w-full rounded-2xl px-4 text-sm text-slate-700 ${premiumInputClass}`;
  const fieldWithIconClass = `h-12 w-full rounded-2xl pl-11 pr-4 text-sm text-slate-700 ${premiumInputClass}`;
  const textAreaClass = `w-full rounded-2xl px-4 py-3 text-sm text-slate-700 ${premiumInputClass}`;

  onMount(loadCatalogs);

  async function loadCatalogs() {
    loadingCatalogs = true;

    try {
      const [clientesResponse, productosResponse] = await Promise.all([
        api.get('/clientes/'),
        api.get('/productos/')
      ]);

      clientes = clientesResponse;
      productos = productosResponse;
    } catch (error) {
      console.error('Error cargando catálogos del slide-over:', error);
      stepError = 'No se pudieron cargar clientes y productos.';
    } finally {
      loadingCatalogs = false;
    }
  }

  function normalizeSearchValue(value) {
    return `${value || ''}`
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .trim();
  }

  function findMatchingClient(query) {
    const normalizedQuery = normalizeSearchValue(query);
    if (!normalizedQuery) return null;

    return (
      clientes.find((cliente) =>
        [cliente.razon_social, cliente.numero_documento, cliente.email]
          .filter(Boolean)
          .some((value) => {
            const normalizedValue = normalizeSearchValue(value);
            return normalizedValue.includes(normalizedQuery) || normalizedQuery.includes(normalizedValue);
          })
      ) || null
    );
  }

  function findMatchingProduct(item) {
    const normalizedDescription = normalizeSearchValue(item?.descripcion);
    if (!normalizedDescription) return null;

    return (
      productos.find((producto) =>
        [producto.nombre, producto.descripcion]
          .filter(Boolean)
          .some((value) => normalizedDescription.includes(normalizeSearchValue(value)))
      ) || null
    );
  }

  function findMatchingPaper(material) {
    const normalizedMaterial = normalizeSearchValue(material);
    if (!normalizedMaterial) return null;

    return paperOptions.find((paper) => {
      const normalizedPaper = normalizeSearchValue(paper.label);
      return normalizedPaper.includes(normalizedMaterial) || normalizedMaterial.includes(normalizedPaper);
    });
  }

  function toNumber(value) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function selectClient(cliente) {
    formData.cliente_id = `${cliente.id}`;
    clientSearch = cliente.razon_social || cliente.numero_documento || '';
    stepError = '';
  }

  function applyProductDefaults() {
    if (!selectedProduct) return;

    if (!formData.descripcion.trim()) {
      formData.descripcion = selectedProduct.descripcion || selectedProduct.nombre;
    }
  }

  function toggleFinish(id) {
    if (formData.acabados.includes(id)) {
      formData.acabados = formData.acabados.filter((finishId) => finishId !== id);
    } else {
      formData.acabados = [...formData.acabados, id];
    }
  }

  function buildLineDescription() {
    const parts = [];

    if (selectedProduct?.nombre) parts.push(selectedProduct.nombre);

    const cleanDescription = formData.descripcion.trim();
    if (cleanDescription && cleanDescription !== selectedProduct?.nombre && cleanDescription !== selectedProduct?.descripcion) {
      parts.push(cleanDescription);
    }

    if (toNumber(formData.ancho) > 0 && toNumber(formData.alto) > 0) {
      parts.push(`${toNumber(formData.ancho)} x ${toNumber(formData.alto)} cm`);
    }

    if (formData.papel) parts.push(formData.papel);

    if (activeFinishes.length) {
      parts.push(`Acabados: ${activeFinishes.map((finish) => finish.label).join(', ')}`);
    }

    return parts.join(' · ') || 'Servicio de impresión personalizado';
  }

  function validateStep(step = currentStep) {
    if (step === 1 && !formData.cliente_id) {
      stepError = 'Selecciona un cliente antes de continuar.';
      return false;
    }

    if (step === 2) {
      if (!formData.producto_id) {
        stepError = 'Selecciona un servicio base para calcular la cotización.';
        return false;
      }

      if (!formData.descripcion.trim()) {
        stepError = 'Añade una descripción breve del trabajo a cotizar.';
        return false;
      }

      if (toNumber(formData.cantidad) <= 0) {
        stepError = 'La cantidad debe ser mayor a cero.';
        return false;
      }
    }

    if (step === 3 && estimatedUnitPrice <= 0) {
      stepError = 'El total calculado debe ser mayor a cero antes de finalizar.';
      return false;
    }

    stepError = '';
    return true;
  }

  function goToNextStep() {
    if (!validateStep()) return;
    currentStep = Math.min(currentStep + 1, 3);
  }

  function goToPreviousStep() {
    currentStep = Math.max(currentStep - 1, 1);
    stepError = '';
  }

  function resetForm() {
    currentStep = 1;
    stepError = '';
    aiError = '';
    aiDraftText = '';
    aiSuggestedClient = '';
    aiSuggestions = [];
    clientSearch = '';
    clientName = '';
    clientDocument = '';
    clientContact = '';
    clientAddress = '';
    formData = createInitialState();
  }

  function applyAiResult(result) {
    const parsedItems = Array.isArray(result?.items) ? result.items : [];
    const primaryItem = parsedItems[0];
    const matchedClient = findMatchingClient(result?.cliente_sugerido);
    const matchedProduct = primaryItem ? findMatchingProduct(primaryItem) : null;
    const matchedPaper = primaryItem ? findMatchingPaper(primaryItem.material) : null;

    aiSuggestions = parsedItems;
    aiSuggestedClient = result?.cliente_sugerido || '';
    aiError = '';
    stepError = '';

    if (aiSuggestedClient) {
      clientSearch = aiSuggestedClient;
    }

    if (matchedClient) {
      selectClient(matchedClient);
    } else {
      formData.cliente_id = '';
    }

    if (primaryItem) {
      formData.descripcion = primaryItem.descripcion || formData.descripcion;
      formData.cantidad = Math.max(Number(primaryItem.cantidad || 1), 1);

      if (matchedProduct) {
        formData.producto_id = `${matchedProduct.id}`;
      }

      if (matchedPaper) {
        formData.papel = matchedPaper.label;
      }
    }

    if (matchedClient && currentStep === 1) {
      currentStep = 2;
    }
  }

  async function handleAiQuoteDraft() {
    if (!aiDraftText.trim()) {
      aiError = 'Pega el correo o mensaje del cliente antes de analizarlo.';
      return;
    }

    aiBusy = true;
    aiError = '';
    stepError = '';

    try {
      const result = await api.post('/ai/cotizar-texto', { texto: aiDraftText.trim() });
      applyAiResult(result);
    } catch (error) {
      aiError = error?.message || 'No se pudo interpretar el texto del cliente con IA.';
    } finally {
      aiBusy = false;
    }
  }

  function close() {
    show = false;
    dispatch('close');
    resetForm();
  }

  function handleKeydown(event) {
    if (show && event.key === 'Escape') {
      close();
    }
  }

  async function handlePrimaryAction() {
    if (currentStep < 3) {
      goToNextStep();
      return;
    }

    if (!validateStep(3)) return;

    saving = true;

    try {
      const payload = {
        cliente_id: Number(formData.cliente_id),
        moneda: formData.moneda,
        items: [
          {
            producto_id: formData.producto_id ? Number(formData.producto_id) : null,
            descripcion: buildLineDescription(),
            cantidad: Number(formData.cantidad),
            precio_unitario: Number(estimatedUnitPrice.toFixed(2))
          }
        ]
      };

      await api.post('/cotizaciones/', payload);
      dispatch('success');
      close();
    } catch (error) {
      stepError = error?.message || 'No se pudo registrar la cotización.';
    } finally {
      saving = false;
    }
  }

  $: selectedClient = clientes.find((cliente) => `${cliente.id}` === `${formData.cliente_id}`) || null;
  $: selectedProduct = productos.find((producto) => `${producto.id}` === `${formData.producto_id}`) || null;

  $: if (selectedClient) {
    clientName = selectedClient.razon_social || '';
    clientDocument = selectedClient.numero_documento || '';
    clientContact = [selectedClient.email, selectedClient.telefono].filter(Boolean).join(' · ') || 'Sin datos de contacto';
    clientAddress = selectedClient.direccion || 'Dirección no registrada';
  } else if (!formData.cliente_id) {
    clientName = aiSuggestedClient || '';
    clientDocument = aiSuggestedClient ? 'Cliente por confirmar' : '';
    clientContact = aiSuggestedClient ? 'Selecciona una coincidencia en el padrón interno' : '';
    clientAddress = aiSuggestedClient ? 'Sin vínculo automático con la base de clientes' : '';
  }

  $: filteredClients = clientes
    .filter((cliente) => {
      const searchTerm = clientSearch.trim().toLowerCase();
      if (!searchTerm) return true;

      return [cliente.razon_social, cliente.numero_documento, cliente.email, cliente.telefono]
        .filter(Boolean)
        .some((value) => `${value}`.toLowerCase().includes(searchTerm));
    })
    .slice(0, 6);

  $: activeFinishes = finishOptions.filter((finish) => formData.acabados.includes(finish.id));
  $: paperConfig = paperOptions.find((paper) => paper.label === formData.papel) || paperOptions[0];
  $: quantity = Math.max(toNumber(formData.cantidad), 0);
  $: width = Math.max(toNumber(formData.ancho), 0);
  $: height = Math.max(toNumber(formData.alto), 0);
  $: baseUnitPrice = Math.max(toNumber(selectedProduct?.precio_unitario), 0);
  $: dimensionFactor = width > 0 && height > 0 ? Math.max((width * height) / 600, 1) : 1;
  $: productionSubtotal = baseUnitPrice * paperConfig.multiplier * dimensionFactor * quantity;
  $: finishesTotal = activeFinishes.reduce((sum, finish) => sum + finish.cost, 0);
  $: shippingTotal = Math.max(toNumber(formData.flete), 0);
  $: marginPercent = Math.max(toNumber(formData.margen), 0);
  $: marginAmount = productionSubtotal * (marginPercent / 100);
  $: grandTotal = productionSubtotal + finishesTotal + shippingTotal + marginAmount;
  $: estimatedUnitPrice = quantity > 0 ? grandTotal / quantity : 0;
  $: primaryButtonLabel = currentStep === 3 ? 'Finalizar Cotización' : 'Siguiente';
  $: lineDescriptionPreview = buildLineDescription();
</script>

<svelte:window on:keydown={handleKeydown} />

{#if show}
  <div
    class="fixed inset-0 z-40 bg-slate-900/20 backdrop-blur-sm"
    on:click={close}
    on:keydown={(event) => event.key === 'Escape' && close()}
    role="button"
    tabindex="-1"
    transition:fade={{ duration: 180 }}
  ></div>

  <div
    class={`fixed inset-y-0 right-0 z-50 flex h-full w-full max-w-2xl flex-col ${glassPanelStrongClass} shadow-2xl shadow-slate-900/10`}
    transition:fly={{ x: 500, opacity: 1, duration: 320, easing: cubicOut }}
    aria-modal="true"
    role="dialog"
    aria-label="Crear cotización"
  >
    <div class="border-b border-white/60 px-6 py-6 sm:px-8">
      <div class="flex items-start justify-between gap-4">
        <div class="space-y-2">
          <p class="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Asistente comercial</p>
          <div class="space-y-1">
            <h2 class="text-2xl font-bold tracking-tight text-slate-900">Nueva Cotización</h2>
            <p class="max-w-xl text-sm leading-6 text-slate-500">
              Construye el documento paso a paso con cliente, especificaciones y costos consolidados.
            </p>
          </div>
        </div>

        <button
          on:click={close}
          class={`inline-flex h-11 w-11 items-center justify-center rounded-2xl ${premiumSecondaryButtonClass} text-slate-500 hover:text-slate-900`}
          aria-label="Cerrar asistente"
        >
          <X class="h-5 w-5" strokeWidth={1.9} />
        </button>
      </div>

      <div class="mt-6 grid grid-cols-3 gap-3">
        {#each steps as step}
          <div
            class={`rounded-2xl border px-4 py-3 transition-all duration-300 ${
              currentStep === step.id
                ? 'border-slate-900/10 bg-gradient-to-b from-zinc-800 to-zinc-950 shadow-[inset_0px_1px_0px_rgba(255,255,255,0.1),0px_1px_2px_rgba(0,0,0,0.4)]'
                : currentStep > step.id
                  ? 'border-white/70 bg-white/80 shadow-[0_8px_24px_rgba(15,23,42,0.04)]'
                  : 'border-white/70 bg-white/60 shadow-[0_8px_24px_rgba(15,23,42,0.03)]'
            }`}
          >
            <div class="flex items-center gap-3">
              <div
                class={`flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold ${
                  currentStep === step.id
                    ? 'bg-white/10 text-white'
                    : currentStep > step.id
                      ? 'bg-slate-900 text-white'
                      : 'bg-slate-200 text-slate-500'
                }`}
              >
                {#if currentStep > step.id}
                  <Check class="h-4 w-4" strokeWidth={2.4} />
                {:else}
                  {step.id}
                {/if}
              </div>

              <div class="min-w-0">
                <p
                  class={`truncate text-sm font-semibold tracking-tight ${
                    currentStep === step.id ? 'text-white' : currentStep > step.id ? 'text-slate-900' : 'text-slate-500'
                  }`}
                >
                  {step.title}
                </p>
                <p
                  class={`truncate text-xs ${
                    currentStep === step.id ? 'text-white/65' : currentStep >= step.id ? 'text-slate-500' : 'text-slate-400'
                  }`}
                >
                  {step.subtitle}
                </p>
              </div>
            </div>
          </div>
        {/each}
      </div>
    </div>

    <div class="flex-1 overflow-y-auto px-6 py-6 sm:px-8 sm:py-7">
      {#if loadingCatalogs}
        <div class="flex min-h-full flex-col items-center justify-center gap-5 text-center">
          <div class="flex h-14 w-14 items-center justify-center rounded-2xl border border-blue-100 bg-blue-50">
            <div class="h-8 w-8 animate-spin rounded-full border-[3px] border-slate-200 border-t-blue-500"></div>
          </div>
          <div class="space-y-2">
            <p class="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">Preparando asistente</p>
            <p class="text-sm text-slate-500">Cargando clientes y productos...</p>
          </div>
        </div>
      {:else}
        <div class="space-y-6">
          <section class={`rounded-[30px] p-5 ${mutedGlassPanelClass}`}>
            <div class="space-y-4">
              <div class="space-y-1">
                <p class="text-xs font-semibold uppercase tracking-[0.24em] text-emerald-700">Asistente IA</p>
                <h3 class="text-base font-semibold tracking-tight text-slate-900">Cotización desde texto libre</h3>
                <p class="text-sm leading-6 text-slate-600">
                  Pega aquí el correo del cliente y usaremos el backend de IA para sugerir cliente, descripción, cantidad y material.
                </p>
              </div>

              <div class="space-y-3">
                <label class="block text-xs font-semibold uppercase tracking-[0.22em] text-slate-500" for="ai-draft-text">
                  Pega aquí el correo del cliente
                </label>
                <textarea
                  id="ai-draft-text"
                  bind:value={aiDraftText}
                  rows="5"
                  placeholder="Hola PrintFlow, necesitamos 2,500 folders corporativos en couché 250g con laminado mate para la campaña de abril..."
                  class={textAreaClass}
                ></textarea>
              </div>

              <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                <p class="text-xs leading-5 text-slate-500">
                  Si el cliente existe en tu base, intentaremos vincularlo automáticamente y adelantar el stepper.
                </p>

                <button
                  type="button"
                  on:click={handleAiQuoteDraft}
                  disabled={aiBusy}
                  class={`inline-flex items-center justify-center rounded-xl px-4 py-3 text-sm font-semibold ${premiumPrimaryButtonClass} disabled:cursor-not-allowed disabled:opacity-70`}
                >
                  {aiBusy ? 'Analizando texto...' : 'Autocompletar con IA'}
                </button>
              </div>

              {#if aiError}
                <div class="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  {aiError}
                </div>
              {/if}

              {#if aiSuggestedClient || aiSuggestions.length > 0}
                <div class={`rounded-2xl p-4 ${glassPanelClass}`}>
                  <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                    <div class="space-y-1">
                      <p class="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Cliente sugerido</p>
                      <p class="text-sm font-semibold text-slate-900">{aiSuggestedClient || 'Sin sugerencia de cliente'}</p>
                      <p class="text-xs text-slate-500">
                        {selectedClient ? 'Cliente enlazado automáticamente con tu base interna.' : 'Revisa la sugerencia y confirma la coincidencia manualmente si es necesario.'}
                      </p>
                    </div>

                    <div class="rounded-full border border-white/70 bg-white/80 px-3 py-1 text-xs font-semibold text-slate-700 shadow-[0_8px_24px_rgba(15,23,42,0.04)]">
                      {aiSuggestions.length} ítem{aiSuggestions.length === 1 ? '' : 's'} detectado{aiSuggestions.length === 1 ? '' : 's'}
                    </div>
                  </div>

                  {#if aiSuggestions.length > 0}
                    <div class="mt-4 space-y-2">
                      {#each aiSuggestions as item, index}
                      <div class={`flex items-start justify-between gap-4 rounded-2xl px-4 py-3 ${mutedGlassPanelClass}`}>
                          <div class="min-w-0">
                            <p class="text-sm font-medium text-slate-900">{item.descripcion}</p>
                            <p class="text-xs text-slate-500">{item.material || 'Material no especificado'}</p>
                          </div>

                          <div class="shrink-0 rounded-full bg-white px-3 py-1 text-xs font-semibold text-slate-700">
                            {index === 0 ? `${item.cantidad} u. aplicadas` : `${item.cantidad} u.`}
                          </div>
                        </div>
                      {/each}
                    </div>
                  {/if}
                </div>
              {/if}
            </div>
          </section>

          {#if currentStep === 1}
            <section class="space-y-6">
              <div class="space-y-2">
                <h3 class="text-lg font-semibold tracking-tight text-slate-900">Paso 1. Selección del cliente</h3>
                <p class="text-sm leading-6 text-slate-500">
                  Busca la cuenta comercial adecuada y verifica sus datos antes de pasar a producción.
                </p>
              </div>

              <div class="space-y-3">
                <label class="block text-xs font-semibold uppercase tracking-[0.22em] text-slate-500" for="client-search">
                  Buscar cliente
                </label>

                <div class="relative">
                  <Search class="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" strokeWidth={1.9} />
                  <input
                    id="client-search"
                    type="text"
                    bind:value={clientSearch}
                    placeholder="RUC, razón social o correo..."
                    class={fieldWithIconClass}
                  />
                </div>

                <div class={`rounded-2xl p-2 ${mutedGlassPanelClass}`}>
                  {#if filteredClients.length > 0}
                    <div class="space-y-1">
                      {#each filteredClients as cliente}
                        <button
                          on:click={() => selectClient(cliente)}
                        class={`flex w-full items-start justify-between rounded-xl px-4 py-3 text-left ${premiumRowHoverClass} ${`${cliente.id}` === `${formData.cliente_id}` ? 'bg-white/90 shadow-[0_10px_28px_rgba(15,23,42,0.05)]' : ''}`}
                        >
                          <div class="min-w-0 space-y-1">
                            <p class="truncate text-sm font-semibold text-slate-900">{cliente.razon_social}</p>
                            <p class="text-xs text-slate-500">{cliente.numero_documento} {cliente.email ? `· ${cliente.email}` : ''}</p>
                          </div>

                          <ChevronRight class="mt-0.5 h-4 w-4 shrink-0 text-slate-400" strokeWidth={2} />
                        </button>
                      {/each}
                    </div>
                  {:else}
                    <div class="flex items-center justify-center px-4 py-10 text-center text-sm text-slate-500">
                      No encontramos coincidencias con esa búsqueda.
                    </div>
                  {/if}
                </div>
              </div>

              <div class="grid gap-4 md:grid-cols-2">
                <div class="space-y-2">
                  <label class="block text-xs font-semibold uppercase tracking-[0.22em] text-slate-500" for="client-name">
                    Nombre / Razón social
                  </label>
                  <div class="relative">
                    <UserRound class="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" strokeWidth={1.9} />
                    <input
                      id="client-name"
                      type="text"
                      value={clientName}
                      readonly
                      placeholder="Selecciona un cliente"
                      class={fieldWithIconClass}
                    />
                  </div>
                </div>

                <div class="space-y-2">
                  <label class="block text-xs font-semibold uppercase tracking-[0.22em] text-slate-500" for="client-contact">
                    Contacto
                  </label>
                  <input
                    id="client-contact"
                    type="text"
                    value={clientContact}
                    readonly
                    placeholder="Correo o teléfono"
                    class={fieldClass}
                  />
                </div>

                <div class="space-y-2">
                  <label class="block text-xs font-semibold uppercase tracking-[0.22em] text-slate-500" for="client-document">
                    Documento
                  </label>
                  <input
                    id="client-document"
                    type="text"
                    value={clientDocument}
                    readonly
                    placeholder="RUC / DNI"
                    class={fieldClass}
                  />
                </div>

                <div class="space-y-2">
                  <label class="block text-xs font-semibold uppercase tracking-[0.22em] text-slate-500" for="client-address">
                    Dirección
                  </label>
                  <input
                    id="client-address"
                    type="text"
                    value={clientAddress}
                    readonly
                    placeholder="Dirección fiscal"
                    class={fieldClass}
                  />
                </div>
              </div>
            </section>
          {/if}

          {#if currentStep === 2}
            <section class="space-y-6">
              <div class="space-y-2">
                <h3 class="text-lg font-semibold tracking-tight text-slate-900">Paso 2. Especificaciones técnicas</h3>
                <p class="text-sm leading-6 text-slate-500">
                  Define el servicio base, el formato de impresión y los acabados para estructurar el trabajo.
                </p>
              </div>

              <div class="space-y-4">
                <div class={panelClass}>
                  <div class="mb-4 flex items-center gap-3">
                    <div class="flex h-10 w-10 items-center justify-center rounded-2xl bg-slate-50 text-slate-600">
                      <Package class="h-5 w-5" strokeWidth={1.9} />
                    </div>
                    <div>
                      <h4 class="text-sm font-semibold text-slate-900">Trabajo base</h4>
                      <p class="text-xs text-slate-500">Selecciona el producto que sirve como referencia comercial.</p>
                    </div>
                  </div>

                  <div class="grid gap-4">
                    <div class="space-y-2">
                      <label class="block text-xs font-semibold uppercase tracking-[0.22em] text-slate-500" for="product-select">
                        Servicio base
                      </label>
                      <select
                        id="product-select"
                        bind:value={formData.producto_id}
                        on:change={applyProductDefaults}
                        class={fieldClass}
                      >
                        <option value="">Selecciona un producto...</option>
                        {#each productos as producto}
                          <option value={producto.id}>{producto.nombre} · S/ {producto.precio_unitario}</option>
                        {/each}
                      </select>
                    </div>

                    <div class="space-y-2">
                      <label class="block text-xs font-semibold uppercase tracking-[0.22em] text-slate-500" for="job-description">
                        Descripción del trabajo
                      </label>
                      <textarea
                        id="job-description"
                        bind:value={formData.descripcion}
                        rows="3"
                        placeholder="Ej. Impresión de brochures corporativos para campaña trimestral"
                        class={textAreaClass}
                      ></textarea>
                    </div>
                  </div>
                </div>

                <div class="grid gap-4 lg:grid-cols-2">
                  <div class={panelClass}>
                    <div class="mb-4 flex items-center gap-3">
                      <div class="flex h-10 w-10 items-center justify-center rounded-2xl bg-slate-50 text-slate-600">
                        <Ruler class="h-5 w-5" strokeWidth={1.9} />
                      </div>
                      <div>
                        <h4 class="text-sm font-semibold text-slate-900">Dimensiones</h4>
                        <p class="text-xs text-slate-500">Usa centímetros para estimar formato y complejidad.</p>
                      </div>
                    </div>

                    <div class="grid grid-cols-2 gap-4">
                      <div class="space-y-2">
                        <label class="block text-xs font-semibold uppercase tracking-[0.22em] text-slate-500" for="width-input">
                          Ancho
                        </label>
                        <input
                          id="width-input"
                          type="number"
                          min="0"
                          bind:value={formData.ancho}
                          class={fieldClass}
                        />
                      </div>

                      <div class="space-y-2">
                        <label class="block text-xs font-semibold uppercase tracking-[0.22em] text-slate-500" for="height-input">
                          Alto
                        </label>
                        <input
                          id="height-input"
                          type="number"
                          min="0"
                          bind:value={formData.alto}
                          class={fieldClass}
                        />
                      </div>
                    </div>
                  </div>

                  <div class={panelClass}>
                    <div class="mb-4 flex items-center gap-3">
                      <div class="flex h-10 w-10 items-center justify-center rounded-2xl bg-slate-50 text-slate-600">
                        <Layers3 class="h-5 w-5" strokeWidth={1.9} />
                      </div>
                      <div>
                        <h4 class="text-sm font-semibold text-slate-900">Material y tiraje</h4>
                        <p class="text-xs text-slate-500">Escoge papel y cantidad para construir el costo base.</p>
                      </div>
                    </div>

                    <div class="grid gap-4">
                      <div class="space-y-2">
                        <label class="block text-xs font-semibold uppercase tracking-[0.22em] text-slate-500" for="paper-select">
                          Tipo de papel
                        </label>
                        <select
                          id="paper-select"
                          bind:value={formData.papel}
                          class={fieldClass}
                        >
                          {#each paperOptions as paper}
                            <option value={paper.label}>{paper.label}</option>
                          {/each}
                        </select>
                      </div>

                      <div class="space-y-2">
                        <label class="block text-xs font-semibold uppercase tracking-[0.22em] text-slate-500" for="quantity-input">
                          Cantidad
                        </label>
                        <input
                          id="quantity-input"
                          type="number"
                          min="1"
                          bind:value={formData.cantidad}
                          class={fieldClass}
                        />
                      </div>
                    </div>
                  </div>
                </div>

                <div class={panelClass}>
                  <div class="mb-4 space-y-1">
                    <h4 class="text-sm font-semibold text-slate-900">Acabados</h4>
                    <p class="text-xs text-slate-500">Selecciona los complementos que aumentan el costo del trabajo.</p>
                  </div>

                  <div class="grid gap-3 sm:grid-cols-2">
                    {#each finishOptions as finish}
                      <button
                        type="button"
                        on:click={() => toggleFinish(finish.id)}
                        class={`flex items-center justify-between rounded-2xl border px-4 py-3 text-left transition-all duration-300 ${
                          formData.acabados.includes(finish.id)
                            ? 'border-slate-900/10 bg-white/95 shadow-[0_12px_30px_rgba(15,23,42,0.06)]'
                            : 'border-white/60 bg-white/65 hover:bg-white/90'
                        }`}
                      >
                        <div class="space-y-1">
                          <p class="text-sm font-medium text-slate-900">{finish.label}</p>
                          <p class="text-xs text-slate-500">S/ {finish.cost.toFixed(2)} por trabajo</p>
                        </div>

                        <div class={`flex h-6 w-6 items-center justify-center rounded-full ${formData.acabados.includes(finish.id) ? 'bg-slate-900 text-white' : 'bg-slate-200 text-slate-500'}`}>
                          <Check class="h-3.5 w-3.5" strokeWidth={2.4} />
                        </div>
                      </button>
                    {/each}
                  </div>
                </div>
              </div>
            </section>
          {/if}

          {#if currentStep === 3}
            <section class="space-y-6">
              <div class="space-y-2">
                <h3 class="text-lg font-semibold tracking-tight text-slate-900">Paso 3. Costos y acabados</h3>
                <p class="text-sm leading-6 text-slate-500">
                  Ajusta el cierre comercial con flete, margen de ganancia y una lectura clara del total estimado.
                </p>
              </div>

              <div class="grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
                <div class="space-y-4">
                  <div class={panelClass}>
                    <div class="mb-4 flex items-center gap-3">
                      <div class="flex h-10 w-10 items-center justify-center rounded-2xl bg-slate-50 text-slate-600">
                        <Truck class="h-5 w-5" strokeWidth={1.9} />
                      </div>
                      <div>
                        <h4 class="text-sm font-semibold text-slate-900">Cargos logísticos</h4>
                        <p class="text-xs text-slate-500">Usa cargos complementarios para entrega y coordinación.</p>
                      </div>
                    </div>

                    <div class="space-y-2">
                      <label class="block text-xs font-semibold uppercase tracking-[0.22em] text-slate-500" for="shipping-input">
                        Flete
                      </label>
                      <input
                        id="shipping-input"
                        type="number"
                        min="0"
                        step="0.01"
                        bind:value={formData.flete}
                        class={fieldClass}
                      />
                    </div>
                  </div>

                  <div class={panelClass}>
                    <div class="mb-4 flex items-center gap-3">
                      <div class="flex h-10 w-10 items-center justify-center rounded-2xl bg-slate-50 text-slate-600">
                        <Percent class="h-5 w-5" strokeWidth={1.9} />
                      </div>
                      <div>
                        <h4 class="text-sm font-semibold text-slate-900">Margen de ganancia</h4>
                        <p class="text-xs text-slate-500">Aplica un margen porcentual sobre el costo de producción.</p>
                      </div>
                    </div>

                    <div class="grid gap-4 sm:grid-cols-2">
                      <div class="space-y-2">
                        <label class="block text-xs font-semibold uppercase tracking-[0.22em] text-slate-500" for="margin-input">
                          Margen %
                        </label>
                        <input
                          id="margin-input"
                          type="number"
                          min="0"
                          step="0.01"
                          bind:value={formData.margen}
                          class={fieldClass}
                        />
                      </div>

                      <div class="space-y-2">
                        <label class="block text-xs font-semibold uppercase tracking-[0.22em] text-slate-500" for="currency-select">
                          Moneda
                        </label>
                        <select
                          id="currency-select"
                          bind:value={formData.moneda}
                          class={fieldClass}
                        >
                          <option value="PEN">Soles (PEN)</option>
                          <option value="USD">Dólares (USD)</option>
                        </select>
                      </div>
                    </div>
                  </div>
                </div>

                <aside class={`rounded-[30px] p-5 ${mutedGlassPanelClass}`}>
                  <div class="mb-5 flex items-center gap-3">
                    <div class="flex h-10 w-10 items-center justify-center rounded-2xl bg-white text-slate-600 shadow-sm">
                      <Calculator class="h-5 w-5" strokeWidth={1.9} />
                    </div>
                    <div>
                      <h4 class="text-sm font-semibold text-slate-900">Resumen calculado</h4>
                      <p class="text-xs text-slate-500">Estimación comercial del trabajo listo para enviar.</p>
                    </div>
                  </div>

                  <div class={`rounded-2xl p-4 ${glassPanelClass}`}>
                    <p class="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Concepto final</p>
                    <p class="mt-2 text-sm leading-6 text-slate-700">{lineDescriptionPreview}</p>
                  </div>

                  <div class="mt-4 space-y-3 text-sm">
                    <div class="flex items-center justify-between text-slate-600">
                      <span>Costo producción</span>
                      <strong class="font-semibold text-slate-900">S/ {productionSubtotal.toFixed(2)}</strong>
                    </div>

                    <div class="flex items-center justify-between text-slate-600">
                      <span>Acabados</span>
                      <strong class="font-semibold text-slate-900">S/ {finishesTotal.toFixed(2)}</strong>
                    </div>

                    <div class="flex items-center justify-between text-slate-600">
                      <span>Flete</span>
                      <strong class="font-semibold text-slate-900">S/ {shippingTotal.toFixed(2)}</strong>
                    </div>

                    <div class="flex items-center justify-between text-slate-600">
                      <span>Margen ({marginPercent.toFixed(0)}%)</span>
                      <strong class="font-semibold text-slate-900">S/ {marginAmount.toFixed(2)}</strong>
                    </div>
                  </div>

                  <div class="mt-5 rounded-2xl bg-slate-900 px-5 py-4 text-white">
                    <div class="flex items-center justify-between gap-4">
                      <div>
                        <p class="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">Total estimado</p>
                        <p class="mt-2 text-3xl font-bold tracking-tight">S/ {grandTotal.toFixed(2)}</p>
                      </div>

                      <div class="text-right">
                        <p class="text-xs uppercase tracking-[0.22em] text-slate-400">Unitario</p>
                        <p class="mt-2 text-lg font-semibold">S/ {estimatedUnitPrice.toFixed(2)}</p>
                      </div>
                    </div>
                  </div>
                </aside>
              </div>
            </section>
          {/if}
        </div>
      {/if}
    </div>

    <div class="sticky bottom-0 border-t border-white/60 bg-white/70 p-4 backdrop-blur-xl sm:px-8 sm:py-5">
      <div class="space-y-4">
        {#if stepError}
          <div class="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {stepError}
          </div>
        {/if}

        <div class="flex flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-between">
          <button
            on:click={close}
            class={`inline-flex items-center justify-center rounded-xl px-4 py-3 text-sm font-medium ${premiumSecondaryButtonClass}`}
          >
            Cancelar
          </button>

          <div class="flex flex-col gap-3 sm:flex-row">
            {#if currentStep > 1}
              <button
                on:click={goToPreviousStep}
                class={`inline-flex items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-medium ${premiumSecondaryButtonClass}`}
              >
                <ChevronLeft class="h-4 w-4" strokeWidth={2.2} />
                <span>Anterior</span>
              </button>
            {/if}

            <button
              on:click={handlePrimaryAction}
              disabled={saving}
              class={`inline-flex min-w-[220px] items-center justify-center gap-2 rounded-xl px-5 py-3 text-sm font-semibold ${premiumPrimaryButtonClass} disabled:cursor-not-allowed disabled:opacity-70`}
            >
              <span>{saving ? 'Guardando...' : primaryButtonLabel}</span>
              {#if currentStep < 3}
                <ChevronRight class="h-4 w-4" strokeWidth={2.2} />
              {/if}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
{/if}
