<script>
  import { onMount } from 'svelte';
  
  onMount(() => {
    // Redirección simple al dashboard
    window.location.href = '/dashboard';
  });
</script>

<div class="flex items-center justify-center min-h-[60vh]">
  <div class="flex flex-col items-center gap-6">
    <div class="w-16 h-16 border-4 border-primary/20 border-t-primary rounded-full animate-spin"></div>
    <div class="text-center space-y-2">
      <p class="text-on-surface font-bold tracking-[0.3em] text-sm uppercase animate-pulse">PrintFlow</p>
      <p class="text-on-surface-variant text-xs font-medium">Iniciando sistema de precisión...</p>
    </div>
  </div>
</div>

