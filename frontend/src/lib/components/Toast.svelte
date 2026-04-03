<script>
  import { writable } from 'svelte/store';
  import { fly, fade } from 'svelte/transition';
  import { CheckCircle, AlertCircle, Info, AlertTriangle, X } from 'lucide-svelte';

  // Toast store
  export const toasts = writable([]);

  let toastList = [];
  toasts.subscribe(v => toastList = v);

  export function addToast(message, type = 'success', duration = 4000) {
    const id = Date.now();
    toasts.update(t => [...t, { id, message, type }]);
    if (duration > 0) {
      setTimeout(() => removeToast(id), duration);
    }
  }

  function removeToast(id) {
    toasts.update(t => t.filter(toast => toast.id !== id));
  }

  const icons = {
    success: CheckCircle,
    error: AlertCircle,
    warning: AlertTriangle,
    info: Info
  };

  const styles = {
    success: 'bg-success/10 border-success/20 text-success',
    error: 'bg-error/10 border-error/20 text-error',
    warning: 'bg-warning/10 border-warning/20 text-warning',
    info: 'bg-info/10 border-info/20 text-info'
  };
</script>

<div class="fixed top-4 right-4 z-[100] flex flex-col gap-3 max-w-sm w-full pointer-events-none">
  {#each toastList as toast (toast.id)}
    <div 
      class="pointer-events-auto flex items-start gap-3 p-4 rounded-2xl border backdrop-blur-xl shadow-lg {styles[toast.type] || styles.info}"
      in:fly={{ x: 100, duration: 300 }}
      out:fade={{ duration: 200 }}
    >
      <svelte:component this={icons[toast.type] || icons.info} size={20} class="shrink-0 mt-0.5" />
      <p class="text-sm font-semibold flex-1">{toast.message}</p>
      <button 
        on:click={() => removeToast(toast.id)}
        class="shrink-0 p-0.5 rounded-lg hover:bg-black/5 transition-colors"
      >
        <X size={14} />
      </button>
    </div>
  {/each}
</div>
