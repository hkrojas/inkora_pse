import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { AlertTriangle, CheckCircle2, CircleHelp, Copy, Info, Link2 } from 'lucide-react';
import Modal from './Modal';

const InkoraDialogContext = createContext(null);

const TONE_META = {
  danger: { icon: AlertTriangle, alertClass: 'ink-inline-alert-danger' },
  warning: { icon: AlertTriangle, alertClass: 'ink-inline-alert-warning' },
  success: { icon: CheckCircle2, alertClass: 'ink-inline-alert-success' },
  info: { icon: Info, alertClass: 'ink-inline-alert-info' },
  default: { icon: CircleHelp, alertClass: 'ink-inline-alert-info' },
};

function DialogContent({ dialog, onResolve }) {
  const tone = TONE_META[dialog.tone] || TONE_META.default;
  const Icon = dialog.icon || tone.icon;

  return (
    <Modal
      open
      onClose={() => onResolve(dialog.dismissValue ?? null)}
      title={dialog.title}
      subtitle={dialog.eyebrow}
      icon={Icon}
      iconTone={dialog.tone || 'primary'}
      size="sm"
      initialFocus="[data-dialog-cancel]"
    >
      <div className="inkora-dialog">
        <p className="inkora-dialog__description">{dialog.description}</p>

        {dialog.subject ? (
          <div className="inkora-dialog__subject">
            <span>{dialog.subjectLabel || 'Elemento seleccionado'}</span>
            <strong>{dialog.subject}</strong>
          </div>
        ) : null}

        {dialog.detail ? (
          <div className={`ink-inline-alert ${tone.alertClass}`} role="note">
            <span>{dialog.detail}</span>
          </div>
        ) : null}

        <div className="inkora-dialog__actions">
          {dialog.kind === 'decision' ? (
            dialog.options.map((option, index) => (
              <button
                key={option.value}
                type="button"
                data-dialog-cancel={index === 0 ? '' : undefined}
                className={option.className || (index === 0 ? 'btn-secondary' : 'btn-primary')}
                onClick={() => onResolve(option.value)}
              >
                {option.label}
              </button>
            ))
          ) : (
            <>
              <button type="button" data-dialog-cancel className="btn-secondary" onClick={() => onResolve(false)}>
                {dialog.cancelLabel || 'Cancelar'}
              </button>
              <button
                type="button"
                className={dialog.tone === 'danger' ? 'btn-danger' : 'btn-primary'}
                onClick={() => onResolve(true)}
              >
                {dialog.confirmLabel || 'Confirmar'}
              </button>
            </>
          )}
        </div>
      </div>
    </Modal>
  );
}

function CopyLinkDialog({ dialog, onResolve }) {
  const inputRef = useRef(null);
  const [copyState, setCopyState] = useState('idle');

  useEffect(() => {
    setCopyState('idle');
  }, [dialog.value]);

  const selectLink = () => {
    inputRef.current?.focus();
    inputRef.current?.select();
  };

  const copyLink = async () => {
    setCopyState('copying');
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(dialog.value);
      } else {
        selectLink();
        const copied = typeof document.execCommand === 'function' && document.execCommand('copy');
        if (!copied) throw new Error('manual-copy-required');
      }
      onResolve(true);
    } catch {
      selectLink();
      setCopyState('manual');
    }
  };

  return (
    <Modal
      open
      onClose={() => onResolve(false)}
      title={dialog.title || 'Copiar enlace'}
      subtitle={dialog.eyebrow || 'Enlace para compartir'}
      icon={Link2}
      iconTone="primary"
      size="sm"
      initialFocus="[data-copy-link-input]"
    >
      <div className="inkora-dialog">
        <p className="inkora-dialog__description">
          {dialog.description || 'Copia este enlace para compartir el documento.'}
        </p>
        <label className="inkora-dialog__copy-field">
          <span>Enlace público</span>
          <input
            ref={inputRef}
            data-copy-link-input
            className="form-input"
            readOnly
            value={dialog.value}
            onFocus={(event) => event.target.select()}
          />
        </label>
        {copyState === 'manual' ? (
          <div className="ink-inline-alert ink-inline-alert-warning" role="status">
            El navegador no permitió copiar automáticamente. El enlace quedó seleccionado para que puedas copiarlo manualmente.
          </div>
        ) : null}
        <div className="inkora-dialog__actions">
          <button type="button" className="btn-secondary" onClick={() => onResolve(false)}>
            Cerrar
          </button>
          {copyState === 'manual' ? (
            <button type="button" className="btn-primary" onClick={() => onResolve(true)}>
              Ya lo copié
            </button>
          ) : (
            <button type="button" className="btn-primary" onClick={copyLink} disabled={copyState === 'copying'}>
              <Copy size={16} />
              {copyState === 'copying' ? 'Copiando…' : 'Copiar enlace'}
            </button>
          )}
        </div>
      </div>
    </Modal>
  );
}

export function InkoraDialogProvider({ children }) {
  const [dialog, setDialog] = useState(null);
  const resolverRef = useRef(null);
  const sequenceRef = useRef(0);

  const openDialog = useCallback((config) => new Promise((resolve) => {
    if (resolverRef.current) resolverRef.current(null);
    resolverRef.current = resolve;
    setDialog({ ...config, key: ++sequenceRef.current });
  }), []);

  const resolveDialog = useCallback((value) => {
    const resolve = resolverRef.current;
    resolverRef.current = null;
    setDialog(null);
    resolve?.(value);
  }, []);

  useEffect(() => () => {
    resolverRef.current?.(null);
    resolverRef.current = null;
  }, []);

  const confirmAction = useCallback((options) => openDialog({
    kind: 'confirm',
    tone: 'default',
    ...options,
  }), [openDialog]);

  const chooseAction = useCallback((options) => openDialog({
    kind: 'decision',
    tone: 'info',
    dismissValue: options.dismissValue ?? null,
    ...options,
  }), [openDialog]);

  const showCopyLink = useCallback((options) => openDialog({
    kind: 'copy-link',
    ...options,
  }), [openDialog]);

  return (
    <InkoraDialogContext.Provider value={{ confirmAction, chooseAction, showCopyLink }}>
      {children}
      {dialog?.kind === 'copy-link' ? (
        <CopyLinkDialog key={dialog.key} dialog={dialog} onResolve={resolveDialog} />
      ) : dialog ? (
        <DialogContent key={dialog.key} dialog={dialog} onResolve={resolveDialog} />
      ) : null}
    </InkoraDialogContext.Provider>
  );
}

export function useInkoraDialog() {
  const context = useContext(InkoraDialogContext);
  if (!context) throw new Error('useInkoraDialog must be used within InkoraDialogProvider');
  return context;
}
