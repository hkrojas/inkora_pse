import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeftRight, Building2, Eye, Plus, RefreshCw } from "lucide-react";
import EmptyState from "../components/ui/EmptyState";
import Pagination from "../components/ui/Pagination";
import Spinner from "../components/ui/Spinner";
import { PageError } from "../components/ui/PageState";
import { internalTransfers } from "../services/internalTransfers";

const PAGE_SIZE = 15;
const STATUS = {
  draft: "Borrador",
  pending: "Pendiente",
  in_transit: "En tránsito",
  partially_received: "Recepción parcial",
  completed: "Completado",
  cancelled: "Cancelado",
};

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
      <header className="page-header internal-transfer-hero">
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
          <Link className="btn" to="/inventario/establecimientos">
            <Building2 size={15} />
            Establecimientos
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
        <PageError message={error} onRetry={load} />
      ) : (
        <section className="internal-transfer-card">
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
            <div className="ink-table-wrap">
              <table className="ink-table">
                <thead>
                  <tr>
                    <th>Traslado</th>
                    <th>Ruta</th>
                    <th>Bienes</th>
                    <th>Estado</th>
                    <th className="text-right">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((item) => (
                    <tr key={item.id}>
                      <td>
                        <strong>TI-{item.id}</strong>
                        <small>
                          {new Date(item.created_at).toLocaleDateString(
                            "es-PE",
                          )}
                        </small>
                      </td>
                      <td>
                        <strong>{item.source_establishment.name}</strong>
                        <small>
                          hacia {item.destination_establishment.name}
                        </small>
                      </td>
                      <td>
                        {item.lines.length}
                        <small>
                          {item.dispatches.length} despacho
                          {item.dispatches.length === 1 ? "" : "s"}
                        </small>
                      </td>
                      <td>
                        <span
                          className={`internal-transfer-status is-${item.status}`}
                        >
                          {STATUS[item.status] || item.status}
                        </span>
                      </td>
                      <td className="text-right">
                        <Link
                          className="btn btn-sm"
                          to={`/traslados-internos/${item.id}`}
                        >
                          <Eye size={14} />
                          Abrir
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
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
