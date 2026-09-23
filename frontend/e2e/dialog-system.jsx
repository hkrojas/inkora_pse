import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import { ThemeProvider } from '../src/context/ThemeContext';
import { InkoraDialogProvider, useInkoraDialog } from '../src/components/ui/InkoraDialogProvider';
import '../src/app.css';
import '../src/styles/tokens.css';
import '../src/styles/globals.css';

function DialogHarness() {
  const { confirmAction, chooseAction, showCopyLink } = useInkoraDialog();
  const [result, setResult] = useState('sin acción');

  const openDanger = async () => {
    const confirmed = await confirmAction({
      title: 'Eliminar cotización',
      eyebrow: 'Cotizaciones',
      description: 'La cotización dejará de estar disponible en el historial operativo.',
      subjectLabel: 'Cotización',
      subject: 'COT-000277',
      detail: 'Esta acción no se puede deshacer.',
      confirmLabel: 'Eliminar cotización',
      tone: 'danger',
    });
    setResult(`confirmar:${Boolean(confirmed)}`);
  };

  const openDecision = async () => {
    const choice = await chooseAction({
      title: '¿Dónde guardar los cambios?',
      eyebrow: 'Catálogo de productos',
      description: 'Modificaste un producto al preparar este comprobante.',
      detail: 'El comprobante se guardará en ambos casos.',
      dismissValue: 'document',
      options: [
        { value: 'document', label: 'Solo este comprobante', className: 'btn-secondary' },
        { value: 'catalog', label: 'Actualizar catálogo', className: 'btn-primary' },
      ],
    });
    setResult(`decisión:${choice}`);
  };

  const openCopy = async () => {
    const copied = await showCopyLink({
      title: 'Copiar enlace de cotización',
      description: 'Copia este enlace para compartir la cotización con el cliente.',
      value: 'https://inkora.example/cotizaciones/COT-000277',
    });
    setResult(`copiar:${Boolean(copied)}`);
  };

  return (
    <main className="min-h-screen bg-[var(--color-bg)] p-8 text-[var(--color-text)]">
      <section className="mx-auto grid max-w-3xl gap-5 rounded-3xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6">
        <div>
          <p className="text-xs font-extrabold uppercase tracking-wider text-[var(--color-primary)]">Prueba aislada</p>
          <h1 className="mt-1 text-2xl font-black">Diálogos operativos de Inkora</h1>
        </div>
        <div className="flex flex-wrap gap-3">
          <button type="button" className="btn-danger" onClick={openDanger}>Confirmación destructiva</button>
          <button type="button" className="btn-primary" onClick={openDecision}>Decisión explícita</button>
          <button type="button" className="btn-secondary" onClick={openCopy}>Copiar enlace</button>
        </div>
        <output aria-live="polite">Resultado: {result}</output>
      </section>
    </main>
  );
}

localStorage.setItem('inkora-theme', 'light');
createRoot(document.getElementById('root')).render(
  <ThemeProvider>
    <InkoraDialogProvider>
      <DialogHarness />
    </InkoraDialogProvider>
  </ThemeProvider>,
);
