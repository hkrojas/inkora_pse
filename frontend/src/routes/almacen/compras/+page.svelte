<script>
  import { api } from '$lib/utils/api';
  import { CircleAlert, FileText, Package, Upload } from 'lucide-svelte';

  let fileInput;
  let dragActive = false;
  let uploading = false;
  let error = '';
  let successMessage = '';
  let selectedFile = null;
  let previewItems = [];

  function getReadableSize(bytes) {
    if (!bytes) return '0 KB';
    const kilobytes = bytes / 1024;
    return kilobytes >= 1024 ? `${(kilobytes / 1024).toFixed(2)} MB` : `${Math.max(kilobytes, 0.1).toFixed(1)} KB`;
  }

  function isSupportedFile(file) {
    if (!file) return false;

    const mimeType = `${file.type || ''}`.toLowerCase();
    const fileName = `${file.name || ''}`.toLowerCase();

    return mimeType === 'application/pdf'
      || mimeType.startsWith('image/')
      || fileName.endsWith('.pdf')
      || fileName.endsWith('.png')
      || fileName.endsWith('.jpg')
      || fileName.endsWith('.jpeg')
      || fileName.endsWith('.webp');
  }

  function openFilePicker() {
    fileInput?.click();
  }

  function handleZoneKeydown(event) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      openFilePicker();
    }
  }

  function handleFileChange(event) {
    const file = event.currentTarget.files?.[0];
    if (file) {
      void processFile(file);
    }
  }

  function handleDragEnter(event) {
    event.preventDefault();
    dragActive = true;
  }

  function handleDragOver(event) {
    event.preventDefault();
    dragActive = true;
  }

  function handleDragLeave(event) {
    event.preventDefault();
    dragActive = false;
  }

  function handleDrop(event) {
    event.preventDefault();
    dragActive = false;

    const file = event.dataTransfer?.files?.[0];
    if (file) {
      void processFile(file);
    }
  }

  async function processFile(file) {
    if (!isSupportedFile(file)) {
      error = 'Solo se admiten PDF o imágenes legibles del proveedor.';
      successMessage = '';
      previewItems = [];
      selectedFile = null;
      return;
    }

    uploading = true;
    error = '';
    successMessage = '';
    previewItems = [];
    selectedFile = file;

    try {
      const formData = new FormData();
      formData.append('file', file);

      const result = await api.postForm('/ai/leer-factura-proveedor', formData);
      previewItems = Array.isArray(result?.insumos) ? result.insumos : [];
      successMessage = previewItems.length > 0
        ? 'Documento procesado. Revisa los insumos detectados antes de registrarlos.'
        : 'El documento se procesó, pero no se detectaron insumos claros.';
    } catch (uploadError) {
      error = uploadError?.message || 'No se pudo procesar el documento con IA.';
    } finally {
      uploading = false;

      if (fileInput) {
        fileInput.value = '';
      }
    }
  }
</script>

<div class="space-y-6">
  <section class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
    <div class="space-y-2">
      <p class="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Almacén inteligente</p>
      <div class="space-y-1">
        <h1 class="text-2xl font-bold tracking-tight text-slate-900">Compras</h1>
        <p class="max-w-3xl text-sm leading-6 text-slate-500">
          Carga facturas de proveedor en PDF o imagen y deja que la IA prepare una lectura preliminar de los insumos comprados.
        </p>
      </div>
    </div>
  </section>

  <section class="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
    <div
      class="rounded-3xl border border-dashed p-6 transition-all duration-200
        {dragActive ? 'border-emerald-400 bg-emerald-50 shadow-sm shadow-emerald-900/5' : 'border-slate-300 bg-white shadow-sm'}"
      on:dragenter={handleDragEnter}
      on:dragover={handleDragOver}
      on:dragleave={handleDragLeave}
      on:drop={handleDrop}
      on:click={openFilePicker}
      on:keydown={handleZoneKeydown}
      role="button"
      tabindex="0"
      aria-label="Zona para cargar factura de proveedor"
    >
      <div class="flex min-h-[260px] flex-col items-center justify-center gap-5 text-center">
        <div class="flex h-16 w-16 items-center justify-center rounded-2xl border border-emerald-100 bg-emerald-50 text-emerald-600">
          <Upload class="h-8 w-8" strokeWidth={1.9} />
        </div>

        <div class="space-y-2">
          <h2 class="text-lg font-semibold tracking-tight text-slate-900">Arrastra una factura aquí</h2>
          <p class="max-w-md text-sm leading-6 text-slate-500">
            También puedes hacer clic para seleccionar un PDF, JPG, PNG o WEBP y enviarlo al OCR inteligente.
          </p>
        </div>

        <button
          type="button"
          class="inline-flex items-center justify-center rounded-xl bg-emerald-600 px-5 py-3 text-sm font-semibold text-white shadow-sm shadow-emerald-900/10 ring-1 ring-inset ring-emerald-500/70 transition-all duration-200 hover:bg-emerald-500"
        >
          Seleccionar archivo
        </button>

        <p class="text-xs font-medium uppercase tracking-[0.24em] text-slate-400">
          Formatos admitidos: PDF, JPG, PNG, WEBP
        </p>
      </div>

      <input
        bind:this={fileInput}
        type="file"
        accept=".pdf,image/*"
        class="hidden"
        on:change={handleFileChange}
      />
    </div>

    <aside class="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <div class="space-y-5">
        <div class="space-y-1">
          <p class="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Estado de carga</p>
          <h2 class="text-lg font-semibold tracking-tight text-slate-900">Lectura preliminar del documento</h2>
        </div>

        <div class="rounded-2xl border border-slate-200 bg-slate-50 p-4">
          <p class="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Archivo actual</p>

          {#if selectedFile}
            <div class="mt-3 space-y-2">
              <p class="text-sm font-semibold text-slate-900">{selectedFile.name}</p>
              <div class="flex flex-wrap gap-2 text-xs text-slate-500">
                <span class="rounded-full bg-white px-3 py-1">{selectedFile.type || 'Tipo no detectado'}</span>
                <span class="rounded-full bg-white px-3 py-1">{getReadableSize(selectedFile.size)}</span>
              </div>
            </div>
          {:else}
            <p class="mt-3 text-sm text-slate-500">Todavía no has cargado una factura.</p>
          {/if}
        </div>

        <div class="rounded-2xl border border-slate-200 bg-slate-50 p-4">
          <p class="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Checklist</p>
          <div class="mt-3 space-y-3 text-sm text-slate-600">
            <div class="flex items-start gap-3">
              <div class="mt-0.5 flex h-7 w-7 items-center justify-center rounded-full bg-white shadow-sm">
                <FileText class="h-4 w-4 text-slate-500" strokeWidth={1.9} />
              </div>
              <p>Sube un documento legible con el detalle de productos o insumos comprados.</p>
            </div>
            <div class="flex items-start gap-3">
              <div class="mt-0.5 flex h-7 w-7 items-center justify-center rounded-full bg-white shadow-sm">
                <Package class="h-4 w-4 text-slate-500" strokeWidth={1.9} />
              </div>
              <p>La tabla mostrará una lectura preliminar para que revises nombre y cantidad antes de registrar stock.</p>
            </div>
          </div>
        </div>

        {#if error}
          <div class="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        {:else if successMessage}
          <div class="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
            {successMessage}
          </div>
        {/if}
      </div>
    </aside>
  </section>

  <section class="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">
    <div class="border-b border-slate-200 px-6 py-5">
      <div class="space-y-1">
        <p class="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Previsualización OCR</p>
        <h2 class="text-lg font-semibold tracking-tight text-slate-900">Ítems extraídos</h2>
      </div>
    </div>

    {#if uploading}
      <div class="overflow-x-auto" aria-hidden="true">
        <table class="min-w-full border-separate border-spacing-0">
          <thead>
            <tr class="bg-slate-50/60">
              <th class="px-6 pb-3 pt-5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Insumo</th>
              <th class="px-6 pb-3 pt-5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Cantidad</th>
            </tr>
          </thead>
          <tbody>
            {#each Array.from({ length: 5 }, (_, index) => index) as _, index}
              <tr class="animate-pulse">
                <td class="px-6 py-4 {index === 4 ? 'border-b-0' : 'border-b border-slate-200/70'}">
                  <div class="h-4 w-52 rounded-full bg-slate-200"></div>
                </td>
                <td class="px-6 py-4 {index === 4 ? 'border-b-0' : 'border-b border-slate-200/70'}">
                  <div class="h-4 w-20 rounded-full bg-slate-200"></div>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {:else if previewItems.length > 0}
      <div class="overflow-x-auto">
        <table class="min-w-full border-separate border-spacing-0">
          <thead>
            <tr class="bg-slate-50/60">
              <th class="px-6 pb-3 pt-5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Insumo</th>
              <th class="px-6 pb-3 pt-5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Cantidad</th>
            </tr>
          </thead>
          <tbody>
            {#each previewItems as item, index}
              <tr class="transition-colors hover:bg-slate-50">
                <td class="px-6 py-4 text-sm font-medium text-slate-900 {index === previewItems.length - 1 ? 'border-b-0' : 'border-b border-slate-200/70'}">
                  {item.nombre}
                </td>
                <td class="px-6 py-4 text-sm text-slate-600 {index === previewItems.length - 1 ? 'border-b-0' : 'border-b border-slate-200/70'}">
                  {item.cantidad}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {:else}
      <div class="flex min-h-[260px] flex-col items-center justify-center gap-4 px-6 py-10 text-center">
        <div class="flex h-14 w-14 items-center justify-center rounded-2xl border border-slate-200 bg-slate-50 text-slate-400">
          <CircleAlert class="h-7 w-7" strokeWidth={1.9} />
        </div>
        <div class="space-y-2">
          <h3 class="text-lg font-semibold tracking-tight text-slate-900">Aún no hay lectura disponible</h3>
          <p class="max-w-md text-sm leading-6 text-slate-500">
            Carga una factura de proveedor para generar una tabla preliminar con los insumos detectados por el OCR.
          </p>
        </div>
      </div>
    {/if}
  </section>
</div>
