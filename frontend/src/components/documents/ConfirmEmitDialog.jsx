import { AlertTriangle, CheckCircle2 } from 'lucide-react';
import Modal from '../ui/Modal';
import { formatCurrency } from '../../lib/utils/documents';
import { getTypeConfig } from './DocumentType';

// Confirmation dialog for irreversible fiscal actions (emit, void, note).
// mode: 'emit' | 'void' | 'note'
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
  if (!open) return null;

  const cfg = getTypeConfig(tipo);
  const isVoid = mode === 'void';

  const titles = {
    emit: 'Confirmar emisión del comprobante',
    void: 'Confirmar comunicación de baja',
    note: 'Confirmar emisión de nota',
  };

  const warnings = {
    emit: 'Esta acción enviará el comprobante a SUNAT y consumirá un número de correlativo. No se puede deshacer.',
    void: 'SUNAT será notificada para anular este comprobante. La operación es asíncrona e irreversible.',
    note: 'La nota se enviará a SUNAT y consumirá un correlativo. Una nota no puede anularse por sí misma.',
  };

  const accentColor = isVoid ? '#DC2626' : cfg.color;
  const accentBg    = isVoid ? '#FEE2E2' : cfg.bg;
  const accentBorder= isVoid ? '#FECACA' : cfg.border;

  return (
    <Modal open={open} onClose={onClose} title={titles[mode]} size="sm">
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>

        {/* Document chip */}
        <div style={{
          display: 'flex',
          alignItems: 'flex-start',
          gap: '14px',
          padding: '14px 16px',
          background: accentBg,
          border: `1.5px solid ${accentBorder}`,
        }}>
          {isVoid
            ? <AlertTriangle size={20} style={{ color: accentColor, flexShrink: 0, marginTop: 1 }} />
            : <CheckCircle2 size={20} style={{ color: accentColor, flexShrink: 0, marginTop: 1 }} />
          }
          <div style={{ minWidth: 0 }}>
            <p style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '11px',
              fontWeight: 700,
              color: accentColor,
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
              marginBottom: '4px',
            }}>
              {cfg.label} · {serie || 'Serie pendiente'}
            </p>
            <p style={{ fontSize: '14px', fontWeight: 700, color: '#0F172A', marginBottom: '2px' }}>
              {cliente || 'Cliente pendiente'}
            </p>
            <p style={{ fontFamily: 'var(--font-mono)', fontSize: '16px', fontWeight: 900, color: accentColor }}>
              {formatCurrency(total, moneda)}
            </p>
            {extraLines.map((line, i) => (
              <p key={i} style={{ fontSize: '12px', color: '#475569', marginTop: '4px' }}>{line}</p>
            ))}
          </div>
        </div>

        {/* Warning */}
        <p style={{
          fontSize: '12px',
          color: '#64748B',
          lineHeight: 1.6,
          padding: '0 2px',
        }}>
          {warnings[mode]}
        </p>

        {/* Actions */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', paddingTop: '4px' }}>
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            style={{
              padding: '8px 18px',
              fontFamily: 'var(--font-body)',
              fontSize: '13px',
              fontWeight: 500,
              color: '#475569',
              background: '#F1F5F9',
              border: '1.5px solid #E2E8F0',
              cursor: 'pointer',
            }}
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={loading}
            style={{
              padding: '8px 20px',
              fontFamily: 'var(--font-mono)',
              fontSize: '11px',
              fontWeight: 700,
              letterSpacing: '0.06em',
              textTransform: 'uppercase',
              color: '#fff',
              background: loading ? '#94A3B8' : (isVoid ? '#DC2626' : accentColor),
              border: 'none',
              cursor: loading ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              transition: 'background 150ms',
            }}
          >
            {loading && (
              <span style={{
                display: 'inline-block',
                width: '12px',
                height: '12px',
                border: '2px solid rgba(255,255,255,0.4)',
                borderTopColor: '#fff',
                borderRadius: '50%',
                animation: 'spin 0.6s linear infinite',
              }} />
            )}
            {isVoid ? 'Confirmar baja' : mode === 'note' ? 'Emitir nota' : 'Emitir comprobante'}
          </button>
        </div>
      </div>
    </Modal>
  );
}
