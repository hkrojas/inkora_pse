<script>
  import { api } from '$lib/utils/api';
  import {
    glassPanelClass,
    glassPanelStrongClass,
    mutedGlassPanelClass,
    premiumInputClass,
    premiumPrimaryButtonClass,
    premiumSecondaryButtonClass
  } from '$lib/utils/uiClasses';
  import {
    CalendarDays,
    CircleAlert,
    CircleCheckBig,
    FileText,
    LoaderCircle,
    Wallet,
    X
  } from 'lucide-svelte';
  import { cubicOut } from 'svelte/easing';
  import { createEventDispatcher } from 'svelte';
  import { fade, fly } from 'svelte/transition';

  export let show = false;
  export let cotizacionId = null;

  const dispatch = createEventDispatcher();

  let detail = null;
  let pagos = [];
  let isLoading = false;
  let loadError = '';
  let lastLoadedId = null;

  let showPaymentModal = false;
  let paymentSaving = false;
  let paymentError = '';
  let paymentForm = getInitialPaymentForm();

  function getInitialPaymentForm() {
    return {
      monto_pagado: '',
      metodo_pago: 'Transferencia',
      referencia_operacion: '',
      tipo: 'adelanto'
    };
  }

  function closeDetail() {
    show = false;
    showPaymentModal = false;
    paymentError = '';
  }

  function openPaymentModal() {
    if (!detail) return;

    paymentForm = {
      monto_pagado: detail.saldo_pendiente ? Number(detail.saldo_pendiente).toFixed(2) : '',
      metodo_pago: 'Transferencia',
      referencia_operacion: '',
      tipo: 'adelanto'
    };
    paymentError = '';
    showPaymentModal = true;
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

  function getProgressPercent() {
    const total = Number(detail?.total_venta || 0);
    const paid = Number(detail?.monto_pagado || 0);

    if (total <= 0) return 0;
    return Math.max(0, Math.min(100, Math.round((paid / total) * 100)));
  }

  function getStatusBadge(status) {
    const normalized = `${status || ''}`.trim().toLowerCase();

    if (['aprobada', 'aprobado', 'facturada', 'emitida', 'cerrada'].includes(normalized)) {
      return 'bg-emerald-50 text-emerald-700 border border-emerald-200';
    }

    if (['cancelada', 'cancelado', 'rechazada', 'rechazado', 'anulada', 'anulado'].includes(normalized)) {
      return 'bg-red-50 text-red-700 border border-red-200';
    }

    return 'bg-amber-50 text-amber-700 border border-amber-200';
  }

  async function loadDetail(force = false) {
    if (!show || !cotizacionId) return;
    if (!force && lastLoadedId === cotizacionId) return;

    isLoading = true;
    loadError = '';

    try {
      const [cotizacionResponse, pagosResponse] = await Promise.all([
        api.get(`/cotizaciones/${cotizacionId}`),
        api.get(`/cotizaciones/${cotizacionId}/pagos`)
      ]);

      detail = {
        ...cotizacionResponse,
        pagos: pagosResponse
      };
      pagos = pagosResponse;
      lastLoadedId = cotizacionId;
    } catch (error) {
      loadError = error?.message || 'No se pudo cargar el detalle de la cotizacion.';
    } finally {
      isLoading = false;
    }
  }

  async function submitPayment() {
    paymentSaving = true;
    paymentError = '';

    try {
      await api.post(`/cotizaciones/${cotizacionId}/pagos`, {
        monto_pagado: Number(paymentForm.monto_pagado),
        metodo_pago: paymentForm.metodo_pago,
        referencia_operacion: paymentForm.referencia_operacion || null,
        tipo: paymentForm.tipo
      });

      showPaymentModal = false;
      paymentForm = getInitialPaymentForm();
      await loadDetail(true);
      dispatch('updated');
    } catch (error) {
      paymentError = error?.message || 'No se pudo registrar el pago.';
    } finally {
      paymentSaving = false;
    }
  }

  $: if (show && cotizacionId && lastLoadedId !== cotizacionId) {
    void loadDetail();
  }

  $: if (!show) {
    detail = null;
    pagos = [];
    loadError = '';
    lastLoadedId = null;
    showPaymentModal = false;
    paymentError = '';
    paymentForm = getInitialPaymentForm();
  }

  $: progressPercent = getProgressPercent();
  $: canRegisterPayment = Number(detail?.saldo_pendiente || 0) > 0;
</script>

<svelte:window
  on:keydown={(event) => {
    if (event.key !== 'Escape') return;
    if (showPaymentModal) {
      showPaymentModal = false;
      return;
    }
    if (show) {
      closeDetail();
    }
  }}
/>

{#if show}
  <div class="fixed inset-0 z-40 bg-slate-950/45 backdrop-blur-sm" transition:fade={{ duration: 180 }}></div>

  <div class="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6">
    <div
      class={`flex max-h-[92vh] w-full max-w-5xl flex-col overflow-hidden rounded-[32px] ${glassPanelStrongClass} shadow-2xl shadow-slate-900/10`}
      transition:fly={{ y: 24, opacity: 0.6, duration: 240, easing: cubicOut }}
    >
      <div class="flex items-start justify-between gap-4 border-b border-white/60 px-6 py-5 sm:px-8">
        <div class="space-y-2">
          <p class="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Detalle comercial</p>
          <div class="flex flex-wrap items-center gap-3">
            <h2 class="text-2xl font-bold tracking-tight text-slate-900">
              {#if detail}
                {detail.serie}-{String(detail.correlativo).padStart(6, '0')}
              {:else}
                Cotizacion
              {/if}
            </h2>

            {#if detail}
              <span class="inline-flex rounded-full px-3 py-1 text-xs font-semibold {getStatusBadge(detail.estado)}">
                {detail.estado}
              </span>
            {/if}
          </div>
        </div>

        <button
          type="button"
          class={`inline-flex h-11 w-11 items-center justify-center rounded-2xl ${premiumSecondaryButtonClass} text-slate-500 hover:text-slate-900`}
          aria-label="Cerrar detalle"
          on:click={closeDetail}
        >
          <X class="h-5 w-5" strokeWidth={1.9} />
        </button>
      </div>

      <div class="min-h-0 flex-1 overflow-y-auto px-6 py-6 sm:px-8">
        {#if isLoading}
          <div class="flex min-h-[420px] items-center justify-center">
            <div class={`flex items-center gap-3 rounded-2xl px-5 py-4 text-sm text-slate-600 ${mutedGlassPanelClass}`}>
              <LoaderCircle class="h-5 w-5 animate-spin text-emerald-600" strokeWidth={1.9} />
              <span>Cargando detalle y pagos...</span>
            </div>
          </div>
        {:else if loadError}
          <div class="rounded-3xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
            {loadError}
          </div>
        {:else if detail}
          <div class="space-y-6">
            <section class="grid gap-4 xl:grid-cols-[1.4fr_1fr]">
              <div class={`rounded-[30px] p-5 ${mutedGlassPanelClass}`}>
                <div class="flex flex-wrap items-start justify-between gap-4">
                  <div class="space-y-2">
                    <p class="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Cliente</p>
                    <div class="space-y-1">
                      <p class="text-lg font-semibold tracking-tight text-slate-900">
                        {detail.cliente?.razon_social || 'Cliente sin nombre'}
                      </p>
                      <p class="text-sm text-slate-500">
                        {detail.cliente?.numero_documento || 'Sin documento'} · {detail.cliente?.email || 'Sin correo'}
                      </p>
                      <p class="text-sm text-slate-500">{detail.cliente?.direccion || 'Sin direccion registrada'}</p>
                    </div>
                  </div>

                  <div class={`rounded-2xl px-4 py-3 ${glassPanelClass}`}>
                    <div class="flex items-center gap-2 text-sm text-slate-600">
                      <CalendarDays class="h-4 w-4 text-slate-400" strokeWidth={1.9} />
                      <span>Emitida: {formatDate(detail.fecha_emision)}</span>
                    </div>
                    <p class="mt-2 text-sm text-slate-500">
                      Vence: {detail.fecha_vencimiento ? formatDate(detail.fecha_vencimiento) : 'Sin vencimiento'}
                    </p>
                  </div>
                </div>

                <div class="mt-5 grid gap-3 md:grid-cols-3">
                  <div class={`rounded-2xl p-4 ${glassPanelClass}`}>
                    <p class="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Total</p>
                    <p class="mt-2 text-2xl font-bold tracking-tight text-slate-900">{formatCurrency(detail.total_venta)}</p>
                  </div>

                  <div class={`rounded-2xl p-4 ${glassPanelClass}`}>
                    <p class="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Abonado</p>
                    <p class="mt-2 text-2xl font-bold tracking-tight text-emerald-700">
                      {formatCurrency(detail.monto_pagado)}
                    </p>
                  </div>

                  <div class={`rounded-2xl p-4 ${glassPanelClass}`}>
                    <p class="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Saldo</p>
                    <p class="mt-2 text-2xl font-bold tracking-tight text-slate-900">
                      {formatCurrency(detail.saldo_pendiente)}
                    </p>
                  </div>
                </div>

                <div class={`mt-5 rounded-2xl p-4 ${glassPanelClass}`}>
                  <div class="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p class="text-sm font-semibold text-slate-900">Progreso de cobranza</p>
                      <p class="text-sm text-slate-500">
                        {progressPercent}% abonado · saldo pendiente {formatCurrency(detail.saldo_pendiente)}
                      </p>
                    </div>

                    <button
                      type="button"
                      class={`inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold transition-all ${
                        canRegisterPayment
                          ? premiumPrimaryButtonClass
                          : 'cursor-not-allowed border border-white/60 bg-white/60 text-slate-400'
                      }`}
                      on:click={openPaymentModal}
                      disabled={!canRegisterPayment}
                    >
                      <Wallet class="h-4 w-4" strokeWidth={1.9} />
                      <span>{canRegisterPayment ? 'Registrar pago / adelanto' : 'Documento cubierto'}</span>
                    </button>
                  </div>

                  <div class="mt-4 h-3 overflow-hidden rounded-full bg-slate-100">
                    <div
                      class="h-full rounded-full bg-gradient-to-r from-emerald-500 to-emerald-600 transition-all duration-300"
                      style={`width: ${progressPercent}%`}
                    ></div>
                  </div>
                </div>
              </div>

              <div class={`rounded-[30px] p-5 ${glassPanelClass}`}>
                <div class="flex items-start gap-3">
                  <div class="flex h-11 w-11 items-center justify-center rounded-2xl bg-slate-100 text-slate-700">
                    <Wallet class="h-5 w-5" strokeWidth={1.9} />
                  </div>

                  <div class="min-w-0 flex-1 space-y-2">
                    <p class="text-sm font-semibold text-slate-900">Historial de pagos</p>
                    <p class="text-sm leading-6 text-slate-500">
                      Registra adelantos y monitorea el saldo pendiente del documento.
                    </p>
                  </div>
                </div>

                <div class="mt-5 space-y-3">
                  {#if pagos.length > 0}
                    {#each pagos as pago}
                      <div class={`rounded-2xl p-4 ${mutedGlassPanelClass}`}>
                        <div class="flex items-start justify-between gap-3">
                          <div>
                            <p class="text-sm font-semibold text-slate-900">{formatCurrency(pago.monto_pagado)}</p>
                            <p class="mt-1 text-xs uppercase tracking-[0.18em] text-slate-500">
                              {pago.tipo} · {pago.metodo_pago}
                            </p>
                          </div>
                          <p class="text-xs text-slate-500">{formatDate(pago.fecha_pago, true)}</p>
                        </div>

                        {#if pago.referencia_operacion}
                          <p class="mt-3 text-sm text-slate-600">Ref: {pago.referencia_operacion}</p>
                        {/if}
                      </div>
                    {/each}
                  {:else}
                    <div class="rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-4 py-6 text-center">
                      <p class="text-sm font-semibold text-slate-900">Sin pagos registrados</p>
                      <p class="mt-1 text-sm text-slate-500">Aun no se ha abonado ningun importe a esta cotizacion.</p>
                    </div>
                  {/if}
                </div>
              </div>
            </section>

            <section class={`rounded-[30px] ${glassPanelClass}`}>
              <div class="flex items-center justify-between gap-4 border-b border-white/60 px-5 py-4">
                <div class="flex items-center gap-3">
                  <div class="flex h-10 w-10 items-center justify-center rounded-2xl bg-slate-100 text-slate-700">
                    <FileText class="h-5 w-5" strokeWidth={1.9} />
                  </div>
                  <div>
                    <p class="text-sm font-semibold text-slate-900">Items de la cotizacion</p>
                    <p class="text-sm text-slate-500">{detail.items.length} linea{detail.items.length === 1 ? '' : 's'} comerciales</p>
                  </div>
                </div>

                <div class="rounded-full border border-white/70 bg-white/80 px-3 py-1 text-xs font-semibold text-slate-600 shadow-[0_8px_24px_rgba(15,23,42,0.04)]">
                  {formatCurrency(detail.total_venta)}
                </div>
              </div>

              <div class="overflow-x-auto">
                <table class="min-w-full border-separate border-spacing-0">
                  <thead>
                    <tr class="bg-slate-50/70">
                      <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Descripcion</th>
                      <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Cantidad</th>
                      <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">P. unitario</th>
                      <th class="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wider text-slate-500">Total</th>
                    </tr>
                  </thead>

                  <tbody>
                    {#each detail.items as item, index (item.id)}
                      <tr>
                        <td class="px-5 py-4 text-sm text-slate-700 {index === detail.items.length - 1 ? '' : 'border-b border-slate-200/70'}">
                          {item.descripcion}
                        </td>
                        <td class="px-5 py-4 text-sm text-slate-600 {index === detail.items.length - 1 ? '' : 'border-b border-slate-200/70'}">
                          {item.cantidad}
                        </td>
                        <td class="px-5 py-4 text-sm text-slate-600 {index === detail.items.length - 1 ? '' : 'border-b border-slate-200/70'}">
                          {formatCurrency(item.precio_unitario)}
                        </td>
                        <td class="px-5 py-4 text-right text-sm font-semibold text-slate-900 {index === detail.items.length - 1 ? '' : 'border-b border-slate-200/70'}">
                          {formatCurrency(item.total_item)}
                        </td>
                      </tr>
                    {/each}
                  </tbody>
                </table>
              </div>
            </section>
          </div>
        {/if}
      </div>
    </div>
  </div>

  {#if showPaymentModal}
    <div class="fixed inset-0 z-[60] bg-slate-950/50 backdrop-blur-sm" transition:fade={{ duration: 160 }}></div>

    <div class="fixed inset-0 z-[70] flex items-center justify-center p-4">
      <div
        class={`w-full max-w-lg rounded-[30px] ${glassPanelStrongClass} shadow-2xl shadow-slate-900/10`}
        transition:fly={{ y: 16, opacity: 0.6, duration: 220, easing: cubicOut }}
      >
        <div class="flex items-start justify-between gap-4 border-b border-white/60 px-6 py-5">
          <div class="space-y-2">
            <p class="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Caja comercial</p>
            <h3 class="text-xl font-bold tracking-tight text-slate-900">Registrar pago / adelanto</h3>
          </div>

          <button
            type="button"
            class={`inline-flex h-10 w-10 items-center justify-center rounded-2xl ${premiumSecondaryButtonClass} text-slate-500 hover:text-slate-900`}
            aria-label="Cerrar formulario de pago"
            on:click={() => (showPaymentModal = false)}
          >
            <X class="h-4 w-4" strokeWidth={1.9} />
          </button>
        </div>

        <div class="space-y-4 px-6 py-5">
          <div class={`rounded-2xl px-4 py-3 text-sm text-slate-700 ${mutedGlassPanelClass}`}>
            Saldo disponible para registrar: <span class="font-semibold">{formatCurrency(detail?.saldo_pendiente)}</span>
          </div>

          <div class="grid gap-4 sm:grid-cols-2">
            <div class="space-y-2">
              <label for="payment-amount" class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Monto</label>
              <input
                id="payment-amount"
                type="number"
                min="0.01"
                step="0.01"
                bind:value={paymentForm.monto_pagado}
                class={`h-12 w-full rounded-2xl px-4 text-sm text-slate-700 ${premiumInputClass}`}
              />
            </div>

            <div class="space-y-2">
              <label for="payment-type" class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Tipo</label>
              <select
                id="payment-type"
                bind:value={paymentForm.tipo}
                class={`h-12 w-full rounded-2xl px-4 text-sm text-slate-700 ${premiumInputClass}`}
              >
                <option value="adelanto">Adelanto</option>
                <option value="pago">Pago</option>
              </select>
            </div>

            <div class="space-y-2">
              <label for="payment-method" class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Metodo</label>
              <select
                id="payment-method"
                bind:value={paymentForm.metodo_pago}
                class={`h-12 w-full rounded-2xl px-4 text-sm text-slate-700 ${premiumInputClass}`}
              >
                <option value="Transferencia">Transferencia</option>
                <option value="Yape">Yape</option>
                <option value="Efectivo">Efectivo</option>
              </select>
            </div>

            <div class="space-y-2">
              <label for="payment-reference" class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Referencia</label>
              <input
                id="payment-reference"
                type="text"
                bind:value={paymentForm.referencia_operacion}
                placeholder="Operacion, voucher o nota"
                class={`h-12 w-full rounded-2xl px-4 text-sm text-slate-700 ${premiumInputClass}`}
              />
            </div>
          </div>

          {#if paymentError}
            <div class="flex items-start gap-3 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              <CircleAlert class="mt-0.5 h-4 w-4 shrink-0" strokeWidth={1.9} />
              <span>{paymentError}</span>
            </div>
          {/if}
        </div>

        <div class="flex items-center justify-between gap-3 border-t border-white/60 px-6 py-4">
          <button
            type="button"
            class="rounded-xl px-4 py-2 text-sm font-semibold text-slate-500 transition-colors hover:bg-white/80 hover:text-slate-900"
            on:click={() => (showPaymentModal = false)}
          >
            Cancelar
          </button>

          <button
            type="button"
            class={`inline-flex items-center gap-2 rounded-xl px-5 py-3 text-sm font-semibold ${premiumPrimaryButtonClass} disabled:cursor-not-allowed disabled:opacity-60`}
            on:click={submitPayment}
            disabled={paymentSaving}
          >
            {#if paymentSaving}
              <LoaderCircle class="h-4 w-4 animate-spin" strokeWidth={1.9} />
              <span>Registrando...</span>
            {:else}
              <CircleCheckBig class="h-4 w-4" strokeWidth={1.9} />
              <span>Guardar pago</span>
            {/if}
          </button>
        </div>
      </div>
    </div>
  {/if}
{/if}
