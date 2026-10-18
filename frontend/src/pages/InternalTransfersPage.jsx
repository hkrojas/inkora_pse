import { useCallback, useEffect, useId, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeftRight, CircleHelp, Eye, Plus, RefreshCw, Warehouse } from "lucide-react";
import EmptyState from "../components/ui/EmptyState";
import Pagination from "../components/ui/Pagination";
import Spinner from "../components/ui/Spinner";
import { PageError } from "../components/ui/PageState";
import { internalTransfers } from "../services/internalTransfers";
import "../styles/internalTransfersList.css";

const PAGE_SIZE = 15;
const STATUS = {
  draft: { label: "Borrador", help: "La solicitud está creada y tiene bienes pendientes de asignar a un viaje." },
  pending: { label: "Pendiente", help: "Hay bienes asignados a viajes. La salida aún no está confirmada." },
  in_transit: { label: "En tránsito", help: "Hay bienes enviados que todavía están pendientes de recepción." },
  partially_received: { label: "Recepción parcial", help: "Se recibió una parte de los bienes solicitados. El traslado todavía no está completo." },
  completed: { label: "Completado", help: "Se completó la recepción de los bienes del traslado." },
  cancelled: { label: "Cancelado", help: "El traslado fue cancelado y no permite preparar nuevos viajes." },
};

function TransferStatus({ status }) {
  const [open, setOpen] = useState(false);
  const helpId = useId();
  const meta = STATUS[status] || { label: "Sin información", help: "Revisa el detalle del traslado para consultar su situación." };

  return (
    <div className="transfer-status-help">
      <button
        type="button"
        className={`internal-transfer-status is-${status}`}
        aria-label={`${meta.label}: ayuda del estado`}
        aria-expanded={open}
        aria-controls={helpId}
        onClick={() => setOpen((value) => !value)}
        onKeyDown={(event) => { if (event.key === "Escape") setOpen(false); }}
      >
        {meta.label}<CircleHelp size={13} aria-hidden="true" />
      </button>
      <p id={helpId} className="transfer-status-help__text" hidden={!open}>{meta.help}</p>
    </div>
  );
}

function TransferDate({ value }) {
  return <time dateTime={value}>{new Date(value).toLocaleDateString("es-PE")}</time>;
}

export default function InternalTransfersPage() {
  const [page, setPage] = useState(1);
  const [data, setData] = useState({ items: [], total: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    setLoading(true);
    setError("");
    internalTransfers
      .list({ skip: (page - 1) * PAGE_SIZE, limit: PAGE_SIZE })
      .then(setData)
      .catch((err) =>
        setError(
          err.message || "No se pudieron cargar los traslados internos.",
        ),
      )
      .finally(() => setLoading(false));
  }, [page]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="page-shell internal-transfer-page">
      <header className="page-header internal-transfer-hero ink-enter-1">
        <div className="page-header-copy">
          <span className="internal-transfer-kicker">
            <ArrowLeftRight size={15} /> Logística nacional
          </span>
          <h1 className="page-title">Traslados internos</h1>
          <p className="page-subtitle">
            Organiza viajes entre establecimientos, controla cantidades en
            tránsito y registra la recepción.
          </p>
        </div>
        <div className="page-actions">
          <button type="button" className="btn" onClick={load}>
            <RefreshCw size={15} />
            Actualizar
          </button>
          <Link className="btn" to="/inventario?tab=warehouses">
            <Warehouse size={15} />
            Almacenes
          </Link>
          <Link className="btn-primary" to="/traslados-internos/nuevo">
            <Plus size={15} />
            Nuevo traslado
          </Link>
        </div>
      </header>

      {loading ? (
        <Spinner />
      ) : error ? (
        <PageError description={error} onRetry={load} />
      ) : (
        <section className="internal-transfer-card transfer-list ink-enter-2" aria-label="Bandeja de traslados internos">
          {data.items.length === 0 ? (
            <EmptyState
              icon={<ArrowLeftRight size={24} />}
              title="Aún no hay traslados internos"
              description="Crea una solicitud para preparar uno o varios despachos entre establecimientos."
              action={
                <Link className="btn-primary" to="/traslados-internos/nuevo">
                  <Plus size={15} />
                  Crear traslado
                </Link>
              }
            />
          ) : (
            <>
            <p className="transfer-list__intro">Cada traslado puede incluir varios bienes y realizarse en uno o más viajes.</p>
            <div className="ink-table-wrap transfer-list__desktop">
              <table className="ink-table" aria-label="Traslados internos">
                <thead>
                  <tr>
                    <th>Traslado</th>
                    <th>Origen → Destino</th>
                    <th className="transfer-list__number">Ítems</th>
                    <th className="transfer-list__number">Viajes</th>
                    <th>Estado</th>
                    <th className="text-right">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((item) => (
                    <tr key={item.id}>
                      <td data-label="Traslado">
                        <div className="min-w-0">
                          <div className="ink-table-cell__primary">TI-{item.id}</div>
                          <div className="ink-table-cell__meta"><TransferDate value={item.created_at} /></div>
                        </div>
                      </td>
                      <td>
                        <div className="min-w-0">
                          <div className="ink-table-cell__primary">{item.source_establishment.name}</div>
                          <div className="ink-table-cell__meta">
                            → {item.destination_establishment.name}
                          </div>
                        </div>
                      </td>
                      <td className="transfer-list__number">{item.lines.length}</td>
                      <td className="transfer-list__number">{item.dispatches.length}</td>
                      <td><TransferStatus status={item.status} /></td>
                      <td data-label="Acciones" className="text-right">
                        <Link
                          className="btn-secondary btn-sm"
                          to={`/traslados-internos/${item.id}`}
                        >
                          <Eye size={14} aria-hidden="true" />
                          Ver detalle
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="transfer-list__mobile" aria-label="Traslados internos">
              {data.items.map((item) => (
                <article key={item.id} className="transfer-list-card" aria-label={`Traslado TI-${item.id}`}>
                  <header className="transfer-list-card__head">
                    <div><h2>TI-{item.id}</h2><TransferDate value={item.created_at} /></div>
                    <TransferStatus status={item.status} />
                  </header>
                  <dl className="transfer-list-card__route">
                    <div><dt>Origen</dt><dd>{item.source_establishment.name}</dd></div>
                    <div><dt>Destino</dt><dd>{item.destination_establishment.name}</dd></div>
                  </dl>
                  <footer className="transfer-list-card__foot">
                    <dl className="transfer-list-card__counts">
                      <div><dt>Ítems</dt><dd>{item.lines.length}</dd></div>
                      <div><dt>Viajes</dt><dd>{item.dispatches.length}</dd></div>
                    </dl>
                    <Link className="btn-secondary btn-sm" to={`/traslados-internos/${item.id}`}><Eye size={14} aria-hidden="true" />Ver detalle</Link>
                  </footer>
                </article>
              ))}
            </div>
            </>
          )}
          <Pagination
            page={page}
            totalPages={Math.max(
              1,
              Math.ceil(Number(data.total || 0) / PAGE_SIZE),
            )}
            onPageChange={setPage}
          />
        </section>
      )}
    </div>
  );
}
