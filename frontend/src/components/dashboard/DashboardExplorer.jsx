import { useEffect, useId, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { ArrowLeft, ArrowRight, X } from 'lucide-react';
import Spinner from '../ui/Spinner';
import { dashboard } from '../../services/dashboard';

const PAGE_SIZE = 15;
const DOCUMENT_LABELS = { '01': 'Factura', '03': 'Boleta', '07': 'Nota de crédito', '08': 'Nota de débito' };

export default function DashboardExplorer({ context, onClose, onOpenDocument, formatMoney, formatDate }) {
  const panel = useRef(null);
  const titleId = useId();
  const [skip, setSkip] = useState(0);
  const [retry, setRetry] = useState(0);
  const [payload, setPayload] = useState(null);
  const [status, setStatus] = useState('loading');
  const requestKey = JSON.stringify({ ...context.params, skip });
  const closeRef = useRef(onClose);
  closeRef.current = onClose;

  useEffect(() => {
    const previousFocus = document.activeElement;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    panel.current.querySelector('button')?.focus();
    const focusables = () => [...panel.current.querySelectorAll('button:not([disabled]), a[href], [tabindex="0"]')];
    const keyHandler = (event) => {
      if (event.key === 'Escape') { event.preventDefault(); closeRef.current(); }
      if (event.key !== 'Tab') return;
      const elements = focusables();
      const first = elements[0];
      const last = elements.at(-1);
      if (!panel.current.contains(document.activeElement)) { event.preventDefault(); first?.focus(); }
      else if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
    };
    document.addEventListener('keydown', keyHandler);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener('keydown', keyHandler);
      if (previousFocus instanceof HTMLElement && previousFocus.isConnected) previousFocus.focus();
    };
  }, []);

  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    setStatus('loading');
    const timer = window.setTimeout(() => {
      dashboard.records({ ...JSON.parse(requestKey), limit: PAGE_SIZE }, { signal: controller.signal })
        .then((result) => {
          if (!active) return;
          if (!result?.meta || !Array.isArray(result.items) || !Number.isFinite(result.total) || result.total_amount == null) throw new Error('El detalle está incompleto.');
          setPayload(result);
          setStatus('ready');
        })
        .catch((error) => { if (active && !error?.isCanceled) setStatus('error'); });
    }, 0);
    return () => { active = false; window.clearTimeout(timer); controller.abort(); };
  }, [requestKey, retry]);

  const isProduct = context.params.measure === 'product';
  const total = payload?.total || 0;
  return createPortal(
    <div className="business-explorer" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section ref={panel} className="business-explorer__panel" role="dialog" aria-modal="true" aria-labelledby={titleId}>
        <div className="business-explorer__header">
          <div><h2 id={titleId}>{context.title}</h2><p>{context.periodLabel}</p></div>
          <button type="button" onClick={onClose} aria-label="Cerrar detalle"><X size={19} aria-hidden="true" /></button>
        </div>
        <div className="business-explorer__scope" aria-label="Filtros aplicados">
          {context.scope.map((item) => <span key={item}>{item}</span>)}
        </div>
        <div className="business-explorer__content" aria-busy={status === 'loading'}>
          {status === 'loading' && <div className="business-explorer__state"><Spinner size="lg" label="Cargando registros" hint="Consultando las ventas de estas fechas." /></div>}
          {status === 'error' && <div className="business-explorer__state" role="alert"><p>No pudimos cargar los registros.</p><button type="button" className="business-button business-button--primary" onClick={() => setRetry((value) => value + 1)}>Reintentar</button></div>}
          {status === 'ready' && <>
            <div className="business-explorer__total"><span>{isProduct ? 'Venta neta de este producto' : 'Ventas registradas'}</span><strong>{formatMoney(payload.total_amount, payload.meta.currency)}</strong></div>
            <p className="business-explorer__explanation">{isProduct ? 'Incluye solo el importe de este producto dentro de cada comprobante.' : 'Incluye el total de cada venta.'} Descuenta notas de crédito y suma notas de débito. Los importes incluyen IGV.</p>
            {total === 0 ? <p className="business-explorer__state">No hay ventas registradas con estos filtros.</p> : <div className="business-explorer__table-wrap"><table>
              <thead><tr><th>Comprobante</th><th>Cliente</th><th>Fecha</th>{isProduct && <th>Cantidad</th>}<th>Importe</th></tr></thead>
              <tbody>{payload.items.map((row) => <tr key={row.document_id}>
                <td data-label="Comprobante"><button type="button" className="business-record-link" onClick={() => onOpenDocument(row.document_id)}>{row.reference}</button><small>{DOCUMENT_LABELS[row.tipo_comprobante] || 'Comprobante'}{row.state === 'pendiente' ? ' · pendiente de SUNAT' : ''}</small></td>
                <td data-label="Cliente">{row.client_name}</td><td data-label="Fecha">{formatDate(row.issued_at)}</td>
                {isProduct && <td data-label="Cantidad">{row.quantity == null ? '—' : `${Number(row.quantity).toLocaleString('es-PE', { maximumFractionDigits: 4 })} ${row.unit || ''}`}</td>}
                <td data-label="Importe">{formatMoney(row.amount, payload.meta.currency)}</td>
              </tr>)}</tbody>
            </table></div>}
          </>}
        </div>
        {status === 'ready' && total > 0 && <div className="business-explorer__footer">
          <p>Mostrando {skip + 1}–{Math.min(skip + PAGE_SIZE, total)} de {total} registros.<br />Página {Math.floor(skip / PAGE_SIZE) + 1} de {Math.ceil(total / PAGE_SIZE)}.</p>
          <div className="business-explorer__pagination">
            <button type="button" disabled={skip === 0} onClick={() => setSkip((value) => Math.max(0, value - PAGE_SIZE))}><ArrowLeft size={15} aria-hidden="true" />Anterior</button>
            <button type="button" disabled={skip + PAGE_SIZE >= total} onClick={() => setSkip((value) => value + PAGE_SIZE)}>Siguiente<ArrowRight size={15} aria-hidden="true" /></button>
          </div>
        </div>}
      </section>
    </div>, document.body,
  );
}
