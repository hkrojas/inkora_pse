<script>
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
  import {
    CircleAlert,
    CircleCheckBig,
    Download,
    FileText,
    LoaderCircle,
    Plus,
    Truck
  } from 'lucide-svelte';
  import { onMount } from 'svelte';

  const conductorOptions = [
    { id: 'cond-1', label: 'Carlos Mejia', nombres: 'Carlos', apellidos: 'Mejia Soto', nro_doc: '45678912', licencia: 'Q12345678' },
    { id: 'cond-2', label: 'Lucia Paredes', nombres: 'Lucia', apellidos: 'Paredes Leon', nro_doc: '40781234', licencia: 'Q22345679' },
    { id: 'cond-3', label: 'Miguel Ramos', nombres: 'Miguel', apellidos: 'Ramos Diaz', nro_doc: '47890123', licencia: 'Q32345670' }
  ];

  const vehicleOptions = [
    { id: 'veh-1', label: 'Sprinter - F1A221', placa: 'F1A221' },
    { id: 'veh-2', label: 'Kia K2500 - B7R912', placa: 'B7R912' },
    { id: 'veh-3', label: 'Hyundai H100 - C3T447', placa: 'C3T447' }
  ];

  let isLoading = true;
  let quoteLoading = false;
  let saving = false;
  let emitting = false;

  let loadError = '';
  let formError = '';
  let emitError = '';
  let successMessage = '';

  let cotizaciones = [];
  let guias = [];
  let selectedQuote = null;
  let activeGuideId = null;
  let lastEmissionLinks = { xml: null, pdf: null, cdr: null };

  let form = getInitialForm();
  const fieldClass = `h-12 w-full rounded-2xl px-4 text-sm text-slate-700 ${premiumInputClass}`;
  const textareaClass = `w-full rounded-2xl px-4 py-3 text-sm text-slate-700 ${premiumInputClass}`;
  const softPanelClass = `rounded-[28px] p-5 ${mutedGlassPanelClass}`;
  const dangerButtonClass =
    'bg-gradient-to-b from-red-600 to-red-700 text-white shadow-[inset_0px_1px_0px_rgba(255,255,255,0.12),0px_1px_2px_rgba(127,29,29,0.35)] hover:from-red-500 hover:to-red-600 transition-all duration-300 hover:-translate-y-[1px]';

  function getInitialForm() {
    return {
      cotizacion_id: '',
      fecha_traslado: getDefaultDateTime(),
      peso_bruto_total: '',
      numero_bultos: '',
      motivo_traslado: '01',
      descripcion_motivo: 'Venta',
      selectedConductorId: conductorOptions[0].id,
      conductor_nombres: conductorOptions[0].nombres,
      conductor_apellidos: conductorOptions[0].apellidos,
      conductor_nro_doc: conductorOptions[0].nro_doc,
      conductor_licencia: conductorOptions[0].licencia,
      selectedVehicleId: vehicleOptions[0].id,
      vehiculo_placa: vehicleOptions[0].placa,
      partida_ubigeo: '150101',
      partida_direccion: 'Av. Industrial 456, Lima',
      llegada_ubigeo: '150101',
      llegada_direccion: ''
    };
  }

  function getDefaultDateTime() {
    const current = new Date();
    current.setMinutes(0, 0, 0);
    const offset = current.getTimezoneOffset() * 60000;
    return new Date(current.getTime() - offset).toISOString().slice(0, 16);
  }

  function formatCurrency(amount) {
    return new Intl.NumberFormat('es-PE', {
      style: 'currency',
      currency: 'PEN'
    }).format(Number(amount || 0));
  }

  function formatDate(dateString, withTime = false) {
    if (!dateString) return 'Sin fecha';

    return new Date(dateString).toLocaleDateString('es-PE', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      ...(withTime ? { hour: '2-digit', minute: '2-digit' } : {})
    });
  }

  function getGuideStatusBadge(status) {
    const normalized = `${status || ''}`.trim().toLowerCase();

    if (['emitida', 'aceptada', 'enviada'].includes(normalized)) {
      return 'bg-emerald-50 text-emerald-700 border border-emerald-200';
    }

    if (['anulada', 'rechazada', 'error'].includes(normalized)) {
      return 'bg-red-50 text-red-700 border border-red-200';
    }

    return 'bg-amber-50 text-amber-700 border border-amber-200';
  }

  function getQuoteLabel(cotizacion) {
    return `${cotizacion.serie}-${String(cotizacion.correlativo).padStart(6, '0')} · ${cotizacion.cliente?.razon_social || 'Cliente'}`;
  }

  function getQuoteMeta(cotizacionId) {
    return cotizaciones.find((cotizacion) => cotizacion.id === cotizacionId) || null;
  }

  function mapGuideItems(cotizacion) {
    return (cotizacion?.items || []).map((item) => ({
      descripcion: item.descripcion,
      cantidad: Number(item.cantidad || 0),
      unidad_medida: 'NIU',
      codigo_producto: item.producto_id ? String(item.producto_id) : null,
      peso_item: null
    }));
  }

  function hydrateConductor(conductorId) {
    const conductor = conductorOptions.find((option) => option.id === conductorId);
    if (!conductor) return;

    form = {
      ...form,
      selectedConductorId: conductor.id,
      conductor_nombres: conductor.nombres,
      conductor_apellidos: conductor.apellidos,
      conductor_nro_doc: conductor.nro_doc,
      conductor_licencia: conductor.licencia
    };
  }

  function hydrateVehicle(vehicleId) {
    const vehicle = vehicleOptions.find((option) => option.id === vehicleId);
    if (!vehicle) return;

    form = {
      ...form,
      selectedVehicleId: vehicle.id,
      vehiculo_placa: vehicle.placa
    };
  }

  async function loadSelectedQuote(cotizacionId) {
    if (!cotizacionId) {
      selectedQuote = null;
      return;
    }

    quoteLoading = true;

    try {
      const quote = await api.get(`/cotizaciones/${cotizacionId}`);
      selectedQuote = quote;
      form = {
        ...form,
        cotizacion_id: cotizacionId,
        llegada_ubigeo: quote.cliente?.ubigeo || form.llegada_ubigeo || '150101',
        llegada_direccion: quote.cliente?.direccion || form.llegada_direccion
      };
    } catch (error) {
      formError = error?.message || 'No se pudo cargar la cotizacion seleccionada.';
      selectedQuote = null;
    } finally {
      quoteLoading = false;
    }
  }

  async function loadPageData(options = {}) {
    if (!options.silent) {
      isLoading = true;
      loadError = '';
    }

    try {
      const [quotesResponse, guiasResponse] = await Promise.all([
        api.get('/cotizaciones/'),
        api.get('/guias-remision/')
      ]);

      cotizaciones = quotesResponse.filter((cotizacion) => {
        const status = `${cotizacion.estado || ''}`.toLowerCase();
        return !['cancelada', 'cancelado', 'rechazada', 'rechazado', 'anulada', 'anulado'].includes(status);
      });
      guias = guiasResponse;

      if (options.preserveActiveGuideId) {
        activeGuideId = options.preserveActiveGuideId;
      } else if (!activeGuideId && guiasResponse.length > 0) {
        activeGuideId = guiasResponse[0].id;
      }

      if (!form.cotizacion_id && cotizaciones.length > 0) {
        const firstQuoteId = cotizaciones[0].id;
        form = { ...form, cotizacion_id: firstQuoteId };
        await loadSelectedQuote(firstQuoteId);
      } else if (form.cotizacion_id && (!selectedQuote || selectedQuote.id !== Number(form.cotizacion_id))) {
        await loadSelectedQuote(Number(form.cotizacion_id));
      }
    } catch (error) {
      loadError = error?.message || 'No se pudieron cargar los despachos.';
    } finally {
      isLoading = false;
    }
  }

  async function handleQuoteChange(event) {
    const quoteId = Number(event.currentTarget.value || 0);
    form = { ...form, cotizacion_id: quoteId || '' };
    formError = '';
    successMessage = '';
    await loadSelectedQuote(quoteId);
  }

  function handleConductorChange(event) {
    hydrateConductor(event.currentTarget.value);
  }

  function handleVehicleChange(event) {
    hydrateVehicle(event.currentTarget.value);
  }

  async function handleCreateGuide() {
    formError = '';
    successMessage = '';
    emitError = '';

    if (!selectedQuote) {
      formError = 'Selecciona una cotizacion para generar la guia.';
      return;
    }

    const items = mapGuideItems(selectedQuote);
    if (items.length === 0) {
      formError = 'La cotizacion seleccionada no tiene items para despachar.';
      return;
    }

    saving = true;

    try {
      const payload = {
        cotizacion_id: Number(form.cotizacion_id),
        fecha_traslado: new Date(form.fecha_traslado).toISOString(),
        motivo_traslado: form.motivo_traslado,
        descripcion_motivo: form.descripcion_motivo || 'Venta',
        peso_bruto_total: Number(form.peso_bruto_total),
        unidad_medida_peso: 'KGM',
        numero_bultos: form.numero_bultos ? Number(form.numero_bultos) : null,
        modalidad_traslado: '02',
        conductor_tipo_doc: '1',
        conductor_nro_doc: form.conductor_nro_doc,
        conductor_nombres: form.conductor_nombres,
        conductor_apellidos: form.conductor_apellidos,
        conductor_licencia: form.conductor_licencia,
        vehiculo_placa: form.vehiculo_placa,
        partida_ubigeo: form.partida_ubigeo || '150101',
        partida_direccion: form.partida_direccion,
        llegada_ubigeo: form.llegada_ubigeo || '150101',
        llegada_direccion: form.llegada_direccion,
        items
      };

      const createdGuide = await api.post('/guias-remision/', payload);
      activeGuideId = createdGuide.id;
      lastEmissionLinks = { xml: null, pdf: null, cdr: null };
      successMessage = 'Guia creada en borrador. Ya puedes enviarla a SUNAT.';
      await loadPageData({ silent: true, preserveActiveGuideId: createdGuide.id });
    } catch (error) {
      formError = error?.message || 'No se pudo crear la guia de remision.';
    } finally {
      saving = false;
    }
  }

  async function handleEmitGuide() {
    if (!activeGuideId) return;

    emitting = true;
    emitError = '';
    successMessage = '';

    try {
      const response = await api.post(`/guias-remision/${activeGuideId}/emitir`, {});
      const links = response?.links || response?.sunat_response?.links || {};

      lastEmissionLinks = {
        xml: links?.xml || null,
        pdf: links?.pdf || null,
        cdr: links?.cdr || null
      };

      successMessage = 'Guia emitida a SUNAT. Ya puedes descargar XML, PDF y CDR.';
      await loadPageData({ silent: true, preserveActiveGuideId: activeGuideId });
    } catch (error) {
      emitError = error?.message || 'No se pudo emitir la guia a SUNAT.';
    } finally {
      emitting = false;
    }
  }

  function openDownload(url) {
    if (!url) return;
    window.open(url, '_blank', 'noopener,noreferrer');
  }

  onMount(loadPageData);

  $: activeGuide = guias.find((guia) => guia.id === activeGuideId) || null;
  $: activeQuoteMeta = activeGuide ? getQuoteMeta(activeGuide.cotizacion_id) : null;
  $: activeGuideDownloads = {
    xml: activeGuide?.sunat_xml_url || lastEmissionLinks.xml,
    pdf: activeGuide?.sunat_pdf_url || lastEmissionLinks.pdf,
    cdr: activeGuide?.sunat_cdr_url || lastEmissionLinks.cdr
  };
</script>

<div class="space-y-6">
  <section class="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
    <div class="space-y-2">
      <p class={pageEyebrowClass}>Logistica fiscal</p>
      <div class="space-y-1">
        <h1 class={pageTitleClass}>Despachos</h1>
        <p class={`max-w-3xl ${pageSubtitleClass}`}>
          Genera guias de remision desde cotizaciones vigentes y controla la emision final hacia SUNAT.
        </p>
      </div>
    </div>

    <div class={`rounded-2xl px-4 py-3 ${glassPanelClass}`}>
      <p class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Estado operativo</p>
      <p class="mt-1 text-sm font-semibold text-slate-900">{guias.length} guia{guias.length === 1 ? '' : 's'} registradas</p>
    </div>
  </section>

  {#if isLoading}
    <div class={`flex min-h-[420px] items-center justify-center rounded-[30px] ${glassPanelStrongClass}`}>
      <div class={`flex items-center gap-3 rounded-2xl px-5 py-4 text-sm text-slate-600 ${mutedGlassPanelClass}`}>
        <LoaderCircle class="h-5 w-5 animate-spin text-emerald-600" strokeWidth={1.9} />
        <span>Cargando centro de despachos...</span>
      </div>
    </div>
  {:else if loadError}
    <div class="rounded-3xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
      {loadError}
    </div>
  {:else}
    <div class="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
      <section class={`rounded-[30px] ${glassPanelStrongClass}`}>
        <div class="border-b border-white/60 px-6 py-5">
          <div class="flex items-start gap-4">
            <div class="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600">
              <Truck class="h-5 w-5" strokeWidth={1.9} />
            </div>
            <div class="min-w-0 flex-1">
              <p class="text-sm font-semibold text-slate-900">Nueva guia de remision</p>
              <p class="mt-1 text-sm leading-6 text-slate-500">
                Selecciona la cotizacion de origen, define conductor, vehiculo y peso, y deja listo el documento para SUNAT.
              </p>
            </div>
          </div>
        </div>

        <div class="space-y-6 px-6 py-6">
          <div class="grid gap-4 md:grid-cols-2">
            <div class="space-y-2 md:col-span-2">
              <label for="quote-select" class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Cotizacion origen</label>
              <select
                id="quote-select"
                bind:value={form.cotizacion_id}
                on:change={handleQuoteChange}
                class={fieldClass}
              >
                <option value="">Selecciona una cotizacion</option>
                {#each cotizaciones as cotizacion}
                  <option value={cotizacion.id}>{getQuoteLabel(cotizacion)}</option>
                {/each}
              </select>
            </div>

            <div class="space-y-2">
              <label for="transfer-date" class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Fecha de traslado</label>
              <input
                id="transfer-date"
                type="datetime-local"
                bind:value={form.fecha_traslado}
                class={fieldClass}
              />
            </div>

            <div class="space-y-2">
              <label for="transport-weight" class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Peso bruto total (kg)</label>
              <input
                id="transport-weight"
                type="number"
                min="0.001"
                step="0.001"
                bind:value={form.peso_bruto_total}
                placeholder="Ej. 125.500"
                class={fieldClass}
              />
            </div>

            <div class="space-y-2">
              <label for="packages-count" class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Numero de bultos</label>
              <input
                id="packages-count"
                type="number"
                min="1"
                step="1"
                bind:value={form.numero_bultos}
                placeholder="Opcional"
                class={fieldClass}
              />
            </div>

            <div class="space-y-2">
              <label for="transfer-note" class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Motivo descriptivo</label>
              <input
                id="transfer-note"
                type="text"
                bind:value={form.descripcion_motivo}
                placeholder="Venta, traslado interno, reposicion..."
                class={fieldClass}
              />
            </div>
          </div>

          <div class="grid gap-6 lg:grid-cols-2">
            <div class={softPanelClass}>
              <div class="flex items-center justify-between gap-3">
                <div>
                  <p class="text-sm font-semibold text-slate-900">Conductor</p>
                  <p class="text-sm text-slate-500">Asignacion de traslado privado</p>
                </div>
                <span class="rounded-full bg-white px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                  Modalidad 02
                </span>
              </div>

              <div class="mt-4 grid gap-4">
                <div class="space-y-2">
                  <label for="driver-select" class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Seleccionar conductor</label>
                  <select
                    id="driver-select"
                    bind:value={form.selectedConductorId}
                    on:change={handleConductorChange}
                    class={fieldClass}
                  >
                    {#each conductorOptions as conductor}
                      <option value={conductor.id}>{conductor.label}</option>
                    {/each}
                  </select>
                </div>

                <div class="grid gap-4 sm:grid-cols-2">
                  <div class="space-y-2">
                    <label for="driver-doc" class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Nro. documento</label>
                    <input
                      id="driver-doc"
                      type="text"
                      bind:value={form.conductor_nro_doc}
                      class={fieldClass}
                    />
                  </div>

                  <div class="space-y-2">
                    <label for="driver-license" class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Licencia</label>
                    <input
                      id="driver-license"
                      type="text"
                      bind:value={form.conductor_licencia}
                      class={fieldClass}
                    />
                  </div>
                </div>
              </div>
            </div>

            <div class={softPanelClass}>
              <div>
                <p class="text-sm font-semibold text-slate-900">Vehiculo</p>
                <p class="text-sm text-slate-500">Unidad operativa asignada al despacho</p>
              </div>

              <div class="mt-4 grid gap-4">
                <div class="space-y-2">
                  <label for="vehicle-select" class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Seleccionar vehiculo</label>
                  <select
                    id="vehicle-select"
                    bind:value={form.selectedVehicleId}
                    on:change={handleVehicleChange}
                    class={fieldClass}
                  >
                    {#each vehicleOptions as vehicle}
                      <option value={vehicle.id}>{vehicle.label}</option>
                    {/each}
                  </select>
                </div>

                <div class="space-y-2">
                  <label for="vehicle-plate" class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Placa</label>
                  <input
                    id="vehicle-plate"
                    type="text"
                    bind:value={form.vehiculo_placa}
                    class={fieldClass}
                  />
                </div>
              </div>
            </div>
          </div>

          <div class="grid gap-6 lg:grid-cols-2">
            <div class={softPanelClass}>
              <div>
                <p class="text-sm font-semibold text-slate-900">Punto de partida</p>
                <p class="text-sm text-slate-500">Direccion fiscal o almacen de salida</p>
              </div>

              <div class="grid gap-4">
                <div class="space-y-2">
                  <label for="origin-ubigeo" class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Ubigeo</label>
                  <input
                    id="origin-ubigeo"
                    type="text"
                    bind:value={form.partida_ubigeo}
                    class={fieldClass}
                  />
                </div>

                <div class="space-y-2">
                  <label for="origin-address" class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Direccion</label>
                  <textarea
                    id="origin-address"
                    rows="3"
                    bind:value={form.partida_direccion}
                    class={textareaClass}
                  ></textarea>
                </div>
              </div>
            </div>

            <div class={softPanelClass}>
              <div>
                <p class="text-sm font-semibold text-slate-900">Punto de llegada</p>
                <p class="text-sm text-slate-500">Destino del cliente o punto de entrega</p>
              </div>

              <div class="grid gap-4">
                <div class="space-y-2">
                  <label for="destination-ubigeo" class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Ubigeo</label>
                  <input
                    id="destination-ubigeo"
                    type="text"
                    bind:value={form.llegada_ubigeo}
                    class={fieldClass}
                  />
                </div>

                <div class="space-y-2">
                  <label for="destination-address" class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Direccion</label>
                  <textarea
                    id="destination-address"
                    rows="3"
                    bind:value={form.llegada_direccion}
                    class={textareaClass}
                  ></textarea>
                </div>
              </div>
            </div>
          </div>

          <div class={softPanelClass}>
            <div class="flex items-center justify-between gap-3">
              <div>
                <p class="text-sm font-semibold text-slate-900">Items a despachar</p>
                <p class="text-sm text-slate-500">Preview heredado desde la cotizacion seleccionada</p>
              </div>

              {#if selectedQuote}
                <div class="rounded-full bg-white px-3 py-1 text-xs font-semibold text-slate-600">
                  Total {formatCurrency(selectedQuote.total_venta)}
                </div>
              {/if}
            </div>

            <div class="mt-4">
              {#if quoteLoading}
                <div class={`flex items-center gap-3 rounded-2xl px-4 py-4 text-sm text-slate-600 ${glassPanelClass}`}>
                  <LoaderCircle class="h-4 w-4 animate-spin text-emerald-600" strokeWidth={1.9} />
                  <span>Sincronizando cotizacion...</span>
                </div>
              {:else if selectedQuote}
                <div class="space-y-3">
                  <div class={`rounded-2xl px-4 py-3 ${glassPanelClass}`}>
                    <p class="text-sm font-semibold text-slate-900">{selectedQuote.cliente?.razon_social || 'Cliente sin nombre'}</p>
                    <p class="mt-1 text-sm text-slate-500">{selectedQuote.cliente?.direccion || 'Sin direccion registrada'}</p>
                  </div>

                  <div class="space-y-2">
                    {#each selectedQuote.items as item}
                      <div class={`flex items-start justify-between gap-4 rounded-2xl px-4 py-3 ${glassPanelClass}`}>
                        <div>
                          <p class="text-sm font-semibold text-slate-900">{item.descripcion}</p>
                          <p class="mt-1 text-sm text-slate-500">Cantidad {item.cantidad}</p>
                        </div>
                        <p class="text-sm font-semibold text-slate-900">{formatCurrency(item.total_item)}</p>
                      </div>
                    {/each}
                  </div>
                </div>
              {:else}
                <div class={`rounded-2xl border border-dashed border-slate-300 px-4 py-6 text-center text-sm text-slate-500 ${mutedGlassPanelClass}`}>
                  Selecciona una cotizacion para previsualizar los items de la guia.
                </div>
              {/if}
            </div>
          </div>

          {#if formError}
            <div class="flex items-start gap-3 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              <CircleAlert class="mt-0.5 h-4 w-4 shrink-0" strokeWidth={1.9} />
              <span>{formError}</span>
            </div>
          {/if}

          <div class="flex flex-wrap items-center justify-between gap-3 border-t border-white/60 pt-5">
            <p class="text-sm text-slate-500">El borrador se guarda primero y luego se emite a SUNAT desde el panel lateral.</p>

            <button
              type="button"
              class={`inline-flex items-center gap-2 rounded-xl px-5 py-3 text-sm font-semibold ${premiumPrimaryButtonClass} disabled:cursor-not-allowed disabled:opacity-60`}
              on:click={handleCreateGuide}
              disabled={saving}
            >
              {#if saving}
                <LoaderCircle class="h-4 w-4 animate-spin" strokeWidth={1.9} />
                <span>Guardando...</span>
              {:else}
                <Plus class="h-4 w-4" strokeWidth={2} />
                <span>Crear borrador GRE</span>
              {/if}
            </button>
          </div>
        </div>
      </section>

      <div class="space-y-6">
        <section class={`rounded-[30px] ${glassPanelStrongClass}`}>
          <div class="border-b border-white/60 px-6 py-5">
            <p class="text-sm font-semibold text-slate-900">Panel SUNAT</p>
            <p class="mt-1 text-sm text-slate-500">Emision final y descarga de artefactos fiscales.</p>
          </div>

          <div class="space-y-5 px-6 py-6">
            {#if activeGuide}
              <div class={softPanelClass}>
                <div class="flex flex-wrap items-start justify-between gap-3">
                  <div class="space-y-2">
                    <div class="flex flex-wrap items-center gap-3">
                      <p class="text-lg font-semibold tracking-tight text-slate-900">
                        {activeGuide.serie}-{String(activeGuide.correlativo).padStart(6, '0')}
                      </p>
                      <span class="inline-flex rounded-full px-3 py-1 text-xs font-semibold {getGuideStatusBadge(activeGuide.estado)}">
                        {activeGuide.estado}
                      </span>
                    </div>
                    <p class="text-sm text-slate-500">
                      {activeQuoteMeta ? getQuoteLabel(activeQuoteMeta) : `Cotizacion #${activeGuide.cotizacion_id || 'sin origen'}`}
                    </p>
                  </div>

                  <div class={`rounded-2xl px-4 py-3 ${glassPanelClass}`}>
                    <p class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Traslado</p>
                    <p class="mt-2 text-sm font-semibold text-slate-900">{formatDate(activeGuide.fecha_traslado, true)}</p>
                  </div>
                </div>

                <div class="mt-5 grid gap-3 sm:grid-cols-2">
                  <div class={`rounded-2xl p-4 ${glassPanelClass}`}>
                    <p class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Conductor</p>
                    <p class="mt-2 text-sm font-semibold text-slate-900">
                      {activeGuide.conductor_nombres || ''} {activeGuide.conductor_apellidos || ''}
                    </p>
                    <p class="mt-1 text-sm text-slate-500">{activeGuide.conductor_nro_doc || 'Sin documento'}</p>
                  </div>

                  <div class={`rounded-2xl p-4 ${glassPanelClass}`}>
                    <p class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Vehiculo / peso</p>
                    <p class="mt-2 text-sm font-semibold text-slate-900">{activeGuide.vehiculo_placa || 'Sin placa'}</p>
                    <p class="mt-1 text-sm text-slate-500">{activeGuide.peso_bruto_total} {activeGuide.unidad_medida_peso}</p>
                  </div>
                </div>

                <div class="mt-5 flex flex-wrap gap-3">
                  <button
                    type="button"
                    class={`inline-flex items-center gap-2 rounded-xl px-5 py-3 text-sm font-semibold ${dangerButtonClass} disabled:cursor-not-allowed disabled:opacity-60`}
                    on:click={handleEmitGuide}
                    disabled={emitting || activeGuide.estado === 'emitida'}
                  >
                    {#if emitting}
                      <LoaderCircle class="h-4 w-4 animate-spin" strokeWidth={1.9} />
                      <span>Enviando a SUNAT...</span>
                    {:else}
                      <Truck class="h-4 w-4" strokeWidth={1.9} />
                      <span>{activeGuide.estado === 'emitida' ? 'Ya emitida' : 'Emitir a SUNAT'}</span>
                    {/if}
                  </button>

                  <button
                    type="button"
                    class={`inline-flex items-center gap-2 rounded-xl px-4 py-3 text-sm font-semibold ${premiumSecondaryButtonClass} disabled:cursor-not-allowed disabled:opacity-50`}
                    on:click={() => openDownload(activeGuideDownloads.xml)}
                    disabled={!activeGuideDownloads.xml}
                  >
                    <Download class="h-4 w-4" strokeWidth={1.9} />
                    <span>XML</span>
                  </button>

                  <button
                    type="button"
                    class={`inline-flex items-center gap-2 rounded-xl px-4 py-3 text-sm font-semibold ${premiumSecondaryButtonClass} disabled:cursor-not-allowed disabled:opacity-50`}
                    on:click={() => openDownload(activeGuideDownloads.pdf)}
                    disabled={!activeGuideDownloads.pdf}
                  >
                    <Download class="h-4 w-4" strokeWidth={1.9} />
                    <span>PDF</span>
                  </button>

                  <button
                    type="button"
                    class={`inline-flex items-center gap-2 rounded-xl px-4 py-3 text-sm font-semibold ${premiumSecondaryButtonClass} disabled:cursor-not-allowed disabled:opacity-50`}
                    on:click={() => openDownload(activeGuideDownloads.cdr)}
                    disabled={!activeGuideDownloads.cdr}
                  >
                    <Download class="h-4 w-4" strokeWidth={1.9} />
                    <span>CDR</span>
                  </button>
                </div>

                {#if emitError}
                  <div class="mt-4 flex items-start gap-3 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                    <CircleAlert class="mt-0.5 h-4 w-4 shrink-0" strokeWidth={1.9} />
                    <span>{emitError}</span>
                  </div>
                {/if}

                {#if successMessage}
                  <div class="mt-4 flex items-start gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                    <CircleCheckBig class="mt-0.5 h-4 w-4 shrink-0" strokeWidth={1.9} />
                    <span>{successMessage}</span>
                  </div>
                {/if}
              </div>
            {:else}
              <div class={`rounded-3xl border border-dashed border-slate-300 px-5 py-10 text-center ${mutedGlassPanelClass}`}>
                <p class="text-sm font-semibold text-slate-900">Sin guia seleccionada</p>
                <p class="mt-1 text-sm text-slate-500">Crea un borrador para activar la emision y las descargas SUNAT.</p>
              </div>
            {/if}
          </div>
        </section>

        <section class={`rounded-[30px] ${glassPanelStrongClass}`}>
          <div class="border-b border-white/60 px-6 py-5">
            <p class="text-sm font-semibold text-slate-900">Guias recientes</p>
            <p class="mt-1 text-sm text-slate-500">Selecciona un borrador o una guia emitida para revisar sus descargas.</p>
          </div>

          <div class="space-y-3 px-4 py-4">
            {#if guias.length > 0}
              {#each guias as guia}
                <button
                  type="button"
                  class={`w-full rounded-2xl border px-4 py-4 text-left ${
                    activeGuideId === guia.id
                      ? 'border-slate-900/10 bg-white/95 shadow-[0_12px_30px_rgba(15,23,42,0.06)]'
                      : 'border-white/60 bg-white/70'
                  } ${premiumRowHoverClass}`}
                  on:click={() => {
                    activeGuideId = guia.id;
                    emitError = '';
                    successMessage = '';
                  }}
                >
                  <div class="flex items-start justify-between gap-3">
                    <div class="min-w-0">
                      <div class="flex flex-wrap items-center gap-2">
                        <p class="text-sm font-semibold text-slate-900">
                          {guia.serie}-{String(guia.correlativo).padStart(6, '0')}
                        </p>
                        <span class="inline-flex rounded-full px-2.5 py-1 text-[11px] font-semibold {getGuideStatusBadge(guia.estado)}">
                          {guia.estado}
                        </span>
                      </div>
                      <p class="mt-1 text-sm text-slate-500">
                        {getQuoteMeta(guia.cotizacion_id)?.cliente?.razon_social || 'Sin cliente asociado'}
                      </p>
                    </div>

                    <div class="rounded-full border border-white/70 bg-white/80 px-3 py-1 text-[11px] font-semibold text-slate-500 shadow-[0_8px_24px_rgba(15,23,42,0.04)]">
                      {formatDate(guia.fecha_emision)}
                    </div>
                  </div>
                </button>
              {/each}
            {:else}
              <div class="flex flex-col items-center justify-center gap-3 px-5 py-10 text-center">
                <div class="flex h-12 w-12 items-center justify-center rounded-2xl border border-slate-200 bg-slate-50 text-slate-500">
                  <FileText class="h-5 w-5" strokeWidth={1.9} />
                </div>
                <div class="space-y-1">
                  <p class="text-sm font-semibold text-slate-900">No hay guias registradas</p>
                  <p class="text-sm text-slate-500">El primer borrador creado aparecera aqui para su seguimiento.</p>
                </div>
              </div>
            {/if}
          </div>
        </section>
      </div>
    </div>
  {/if}
</div>
