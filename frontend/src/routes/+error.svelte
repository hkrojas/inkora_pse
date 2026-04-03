<script>
  import { page } from '$app/stores';
  import { AlertTriangle, Home, RefreshCw, ArrowLeft } from 'lucide-svelte';

  $: statusCode = $page.status;
  $: message = $page.error?.message || 'Ha ocurrido un error inesperado';

  $: title = statusCode === 404 
    ? 'Página no encontrada' 
    : statusCode === 500 
      ? 'Error interno del servidor' 
      : 'Algo salió mal';

  $: subtitle = statusCode === 404
    ? 'La página que buscas no existe o fue movida.'
    : statusCode === 500
      ? 'Nuestro equipo ha sido notificado. Intenta de nuevo en unos minutos.'
      : message;
</script>

<svelte:head>
  <title>Error {statusCode} | PrintFlow</title>
</svelte:head>

<div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-surface-container-lowest via-background to-surface-container-low p-6">
  <div class="max-w-lg w-full text-center space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
    
    <!-- Error Icon -->
    <div class="relative mx-auto w-28 h-28">
      <div class="absolute inset-0 bg-error/10 rounded-full animate-ping opacity-20"></div>
      <div class="relative w-28 h-28 bg-gradient-to-br from-error/20 to-error/5 rounded-full flex items-center justify-center border border-error/10">
        <AlertTriangle size={48} class="text-error" />
      </div>
    </div>

    <!-- Error Code -->
    <div class="space-y-3">
      <p class="text-8xl font-black text-on-surface/10 tracking-tighter leading-none">{statusCode}</p>
      <h1 class="text-2xl sm:text-3xl font-bold text-on-surface tracking-tight">{title}</h1>
      <p class="text-on-surface-variant font-medium max-w-md mx-auto leading-relaxed">{subtitle}</p>
    </div>

    <!-- Actions -->
    <div class="flex flex-col sm:flex-row gap-3 justify-center pt-4">
      <a 
        href="/dashboard" 
        class="inline-flex items-center justify-center gap-2.5 px-8 py-4 rounded-2xl bg-primary text-white font-bold hover:shadow-xl hover:shadow-primary/20 transition-all active:scale-95"
      >
        <Home size={18} />
        Ir al Panel
      </a>
      <button 
        on:click={() => window.location.reload()}
        class="inline-flex items-center justify-center gap-2.5 px-8 py-4 rounded-2xl bg-surface-container-high text-on-surface font-bold hover:bg-surface-container-highest transition-all active:scale-95"
      >
        <RefreshCw size={18} />
        Reintentar
      </button>
    </div>

    <!-- Footer note -->
    <p class="text-xs text-on-surface-variant/60 font-medium pt-8">
      Si el problema persiste, contacta a <a href="mailto:soporte@printflow.com" class="text-primary hover:underline">soporte@printflow.com</a>
    </p>
  </div>
</div>
