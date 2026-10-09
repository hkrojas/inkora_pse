import { AlertTriangle, CheckCircle2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import Modal from '../ui/Modal';
import { formatCurrency } from '../../lib/utils/documents';
import { getTypeConfig } from './DocumentType';

export default function ConfirmEmitDialog({
  open,
  onClose,
  onConfirm,
  loading = false,
  mode = 'emit',
  tipo,
  serie,
  cliente,
  total,
  moneda = 'PEN',
  extraLines = [],
}) {
  const [notDelivered, setNotDelivered] = useState(false);
  useEffect(() => { setNotDelivered(false); }, [open, serie]);
  if (!open) return null;

  const cfg = getTypeConfig(tipo);
  const isVoid = mode === 'void';
  const Icon = isVoid ? AlertTriangle : CheckCircle2;

  const titles = {
    emit: 'Confirmar emisión del comprobante',
    void: 'Confirmar comunicación de baja',
    note: 'Confirmar emisión de nota',
  };

  const warnings = {
    emit: 'Esta acción enviará el comprobante a SUNAT y consumirá un correlativo. Revisa los datos antes de continuar.',
    void: 'SUNAT será notificada para anular este comprobante. La operación es asíncrona e irreversible.',
    note: 'La nota se enviará a SUNAT y consumirá un correlativo propio. Revisa el motivo y el documento relacionado.',
  };

  const actionLabel = isVoid
    ? 'Confirmar baja'
    : mode === 'note'
      ? 'Emitir nota'
      : 'Emitir comprobante';

  return (
    <Modal open={open} onClose={onClose} title={titles[mode]} size="sm">
      <div className="document-confirm-dialog">
        <div className={`document-confirm-card${isVoid ? ' is-danger' : ''}`}>
          <div className="document-confirm-card__icon">
            <Icon size={18} />
          </div>
          <div className="document-confirm-card__body">
            <p className="document-confirm-card__kicker">
              {cfg.label} · {serie || 'Serie pendiente'}
            </p>
            <p className="document-confirm-card__title">{cliente || 'Cliente pendiente'}</p>
            <p className="document-confirm-card__amount">{formatCurrency(total, moneda)}</p>
            {extraLines.map((line, index) => (
              <p key={index} className="document-confirm-card__meta">{line}</p>
            ))}
          </div>
        </div>

        <div className={`ink-inline-alert ${isVoid ? 'ink-inline-alert-danger' : 'ink-inline-alert-warning'}`}>
          <span>{warnings[mode]}</span>
        </div>
        {isVoid && <label className="flex items-start gap-3 mt-4 relative">
          <input type="checkbox" checked={notDelivered} onChange={(event) => setNotDelivered(event.target.checked)} />
          <span>Confirmo que el comprobante no fue entregado ni puesto a disposición del cliente. Si ya fue entregado, corresponde revisar una nota de crédito.</span>
        </label>}

        <div className="document-confirm-actions">
          <button type="button" className="btn-secondary" onClick={onClose} disabled={loading}>
            Cancelar
          </button>
          <button type="button" className={isVoid ? 'btn-danger' : 'btn-primary'} onClick={() => onConfirm(isVoid ? notDelivered : undefined)} disabled={loading || (isVoid && !notDelivered)}>
            {loading ? 'Procesando...' : actionLabel}
          </button>
        </div>
      </div>
    </Modal>
  );
}
