import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  FilePlus2,
  PackageCheck,
  Pencil,
  Send,
  Truck,
  Warehouse,
  XCircle,
} from "lucide-react";
import { Link, useParams } from "react-router-dom";
import CustomSelect from "../components/ui/CustomSelect";
import Drawer from "../components/ui/Drawer";
import Spinner from "../components/ui/Spinner";
import { PageError } from "../components/ui/PageState";
import { useToast } from "../components/ui/Toast";
import { internalTransfers } from "../services/internalTransfers";

const qty = (value) =>
  Number(value || 0).toLocaleString("es-PE", { maximumFractionDigits: 4 });
const localDateTime = () => {
  const date = new Date(Date.now() + 24 * 60 * 60 * 1000);
  date.setMinutes(date.getMinutes() - date.getTimezoneOffset());
  return date.toISOString().slice(0, 16);
};
const guideDefaults = {
  fecha_traslado: localDateTime(),
  peso_bruto_total: "1",
  unidad_medida_peso: "KGM",
  numero_bultos: "",
  modalidad_traslado: "02",
  fecha_entrega_transportista: "",
  indicador_m1_l: false,
  registrar_vehiculo_transportista: false,
  transportista_acuerdo_confirmado: false,
  observaciones: "",
  transportista_ruc: "",
  transportista_razon_social: "",
  transportista_nro_mtc: "",
  conductor_tipo_doc: "1",
  conductor_nro_doc: "",
  conductor_nombres: "",
  conductor_apellidos: "",
  conductor_licencia: "",
  vehiculo_placa: "",
  vehiculo_nro_circulacion: "",
};

export default function InternalTransferDetailPage() {
  const { id } = useParams();
  const toast = useToast();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [drawer, setDrawer] = useState(null);
  const [saving, setSaving] = useState(false);
  const [selectedDispatch, setSelectedDispatch] = useState(null);
  const [dispatchQty, setDispatchQty] = useState({});
  const [receiptQty, setReceiptQty] = useState({});
  const [receiptNote, setReceiptNote] = useState("");
  const [guide, setGuide] = useState(guideDefaults);
  const [editReason, setEditReason] = useState("");
  const [editQty, setEditQty] = useState({});
  const load = useCallback(() => {
    setLoading(true);
    setError("");
    internalTransfers
      .get(id)
      .then(setData)
      .catch((err) => setError(err.message || "No se pudo cargar el traslado."))
      .finally(() => setLoading(false));
  }, [id]);
  useEffect(() => {
    load();
  }, [load]);

  const progress = useMemo(() => {
    if (!data) return { requested: 0, assigned: 0, departed: 0, received: 0 };
    return data.lines.reduce(
      (sum, row) => ({
        requested: sum.requested + Number(row.quantity),
        assigned: sum.assigned + Number(row.assigned),
        departed: sum.departed + Number(row.departed),
        received: sum.received + Number(row.received),
      }),
      { requested: 0, assigned: 0, departed: 0, received: 0 },
    );
  }, [data]);
  const openDispatch = () => {
    setDispatchQty(
      Object.fromEntries(
        data.lines
          .filter((line) => Number(line.pending_assignment) > 0)
          .map((line) => [line.id, String(line.pending_assignment)]),
      ),
    );
    setDrawer("dispatch");
  };
  const createDispatch = async (event) => {
    event.preventDefault();
    setSaving(true);
    try {
      const lines = data.lines
        .map((line) => ({
          transfer_line_id: line.id,
          quantity: Number(dispatchQty[line.id] || 0),
        }))
        .filter((line) => line.quantity > 0);
      if (!lines.length) throw new Error("Indica al menos una cantidad.");
      await internalTransfers.createDispatch(data.id, {
        idempotency_key: crypto.randomUUID(),
        lines,
      });
      toast("Despacho preparado y cantidades reservadas.", "success");
      setDrawer(null);
      await load();
    } catch (err) {
      toast(err.message || "No se pudo crear el despacho.", "error");
    } finally {
      setSaving(false);
    }
  };
  const openGuide = (dispatch) => {
    setSelectedDispatch(dispatch);
    setGuide({ ...guideDefaults, fecha_traslado: localDateTime() });
    setDrawer("guide");
  };
  const createGuide = async (event) => {
    event.preventDefault();
    setSaving(true);
    try {
      const payload = {
        ...guide,
        dispatch_id: selectedDispatch.id,
        idempotency_key: crypto.randomUUID(),
        fecha_traslado: new Date(guide.fecha_traslado).toISOString(),
        fecha_entrega_transportista: guide.fecha_entrega_transportista
          ? new Date(guide.fecha_entrega_transportista).toISOString()
          : null,
        peso_bruto_total: Number(guide.peso_bruto_total),
        numero_bultos: guide.numero_bultos ? Number(guide.numero_bultos) : null,
        partida_ubigeo: data.source_establishment.ubigeo,
        partida_direccion: data.source_establishment.address,
        llegada_ubigeo: data.destination_establishment.ubigeo,
        llegada_direccion: data.destination_establishment.address,
      };
      Object.keys(payload).forEach((key) => {
        if (payload[key] === "") payload[key] = null;
      });
      const created = await internalTransfers.createGuide(payload);
      toast("Borrador GRE creado.", "success");
      setDrawer(null);
      await load();
      window.location.assign(`/guias/${created.id}`);
    } catch (err) {
      toast(err.message || "No se pudo crear la GRE.", "error");
    } finally {
      setSaving(false);
    }
  };
  const confirmDeparture = async (dispatch) => {
    setSaving(true);
    try {
      await internalTransfers.confirmDeparture(
        dispatch.id,
        crypto.randomUUID(),
      );
      toast("Salida confirmada. Los bienes están en tránsito.", "success");
      await load();
    } catch (err) {
      toast(err.message || "No se pudo confirmar la salida.", "error");
    } finally {
      setSaving(false);
    }
  };
  const openReceipt = (dispatch) => {
    setSelectedDispatch(dispatch);
    setReceiptQty(
      Object.fromEntries(
        dispatch.lines.map((line) => [
          line.id,
          String(
            Math.max(
              0,
              Number(line.departed_quantity) - Number(line.received_quantity),
            ),
          ),
        ]),
      ),
    );
    setReceiptNote("");
    setDrawer("receipt");
  };
  const receive = async (event) => {
    event.preventDefault();
    setSaving(true);
    try {
      const lines = selectedDispatch.lines
        .map((line) => ({
          dispatch_line_id: line.id,
          quantity: Number(receiptQty[line.id] || 0),
        }))
        .filter((line) => line.quantity > 0);
      if (!lines.length)
        throw new Error("Indica al menos una cantidad recibida.");
      await internalTransfers.receive(selectedDispatch.id, {
        idempotency_key: crypto.randomUUID(),
        note: receiptNote || null,
        lines,
      });
      toast("Recepción registrada.", "success");
      setDrawer(null);
      await load();
    } catch (err) {
      toast(err.message || "No se pudo registrar la recepción.", "error");
    } finally {
      setSaving(false);
    }
  };
  const openEdit = () => {
    setEditReason(data.reason);
    setEditQty(
      Object.fromEntries(
        data.lines.map((line) => [line.id, String(line.quantity)]),
      ),
    );
    setDrawer("edit");
  };
  const editTransfer = async (event) => {
    event.preventDefault();
    setSaving(true);
    try {
      await internalTransfers.update(data.id, {
        version: data.version,
        reason: editReason,
        source_establishment_id: data.source_establishment.id,
        destination_establishment_id: data.destination_establishment.id,
        source_warehouse_id: data.source_warehouse?.id || null,
        destination_warehouse_id: data.destination_warehouse?.id || null,
        lines: data.lines.map((line) => ({
          product_id: line.product_id,
          description: line.description,
          product_code: line.product_code,
          unit_code: line.unit_code,
          quantity: Number(editQty[line.id]),
          manual_goods_confirmed: !line.product_id,
        })),
      });
      toast("Traslado actualizado.", "success");
      setDrawer(null);
      await load();
    } catch (err) {
      toast(err.message || "No se pudo actualizar el traslado.", "error");
    } finally {
      setSaving(false);
    }
  };
  const cancelTransfer = async () => {
    if (
      !window.confirm(
        "Se cancelará el saldo liberable y sus reservas. La evidencia fiscal existente se conservará. ¿Continuar?",
      )
    )
      return;
    setSaving(true);
    try {
      await internalTransfers.cancel(data.id);
      toast("Traslado cancelado.", "success");
      await load();
    } catch (err) {
      toast(err.message || "No se pudo cancelar el traslado.", "error");
    } finally {
      setSaving(false);
    }
  };

  if (loading)
    return (
      <div className="page-shell">
        <Spinner />
      </div>
    );
  if (error)
    return (
      <div className="page-shell">
        <PageError message={error} onRetry={load} />
      </div>
    );
  return (
    <div className="page-shell internal-transfer-page max-w-6xl">
      <header className="page-header internal-transfer-hero">
        <div className="page-header-copy">
          <Link className="internal-transfer-back" to="/traslados-internos">
            <ArrowLeft size={15} />
            Traslados
          </Link>
          <h1 className="page-title">Traslado TI-{data.id}</h1>
          <p className="page-subtitle">{data.reason}</p>
        </div>
        <div className="page-actions">
          {data.status !== "cancelled" && data.dispatches.length === 0 && (
            <button className="btn" type="button" onClick={openEdit}>
              <Pencil size={15} />
              Editar
            </button>
          )}
          {data.status !== "cancelled" && (
            <button
              className="btn"
              type="button"
              onClick={cancelTransfer}
              disabled={saving}
            >
              <XCircle size={15} />
              Cancelar
            </button>
          )}
          {data.status !== "cancelled" &&
            data.lines.some((line) => Number(line.pending_assignment) > 0) && (
              <button
                className="btn-primary"
                type="button"
                onClick={openDispatch}
              >
                <Send size={15} />
                Preparar despacho
              </button>
            )}
        </div>
      </header>
      <section className="internal-transfer-route-card">
        <div>
          <span className="internal-transfer-route-icon">
            <Warehouse size={18} />
          </span>
          <small>Partida · {data.source_establishment.sunat_code}</small>
          <strong>{data.source_establishment.name}</strong>
          <p>{data.source_establishment.address}</p>
        </div>
        <ArrowRight />
        <div>
          <span className="internal-transfer-route-icon">
            <Warehouse size={18} />
          </span>
          <small>Llegada · {data.destination_establishment.sunat_code}</small>
          <strong>{data.destination_establishment.name}</strong>
          <p>{data.destination_establishment.address}</p>
        </div>
      </section>
      <section className="internal-transfer-progress">
        <article>
          <small>Solicitado</small>
          <strong>{qty(progress.requested)}</strong>
        </article>
        <article>
          <small>Asignado</small>
          <strong>{qty(progress.assigned)}</strong>
        </article>
        <article>
          <small>Enviado</small>
          <strong>{qty(progress.departed)}</strong>
        </article>
        <article>
          <small>Recibido</small>
          <strong>{qty(progress.received)}</strong>
        </article>
      </section>
      <section className="ink-table-card">
        <div className="ink-table-header">
          <div className="ink-table-title">
            <h2>Bienes del traslado</h2>
            <p>
              Las cantidades se controlan por línea y hasta cuatro decimales.
            </p>
          </div>
        </div>
        <div className="ink-table-scroll">
          <table className="ink-table">
            <thead>
              <tr>
                <th>Bien</th>
                <th>Solicitado</th>
                <th>Cancelado</th>
                <th>Asignado</th>
                <th>En tránsito</th>
                <th>Recibido</th>
                <th>Pendiente</th>
              </tr>
            </thead>
            <tbody>
              {data.lines.map((line) => (
                <tr key={line.id}>
                  <td>
                    <div className="ink-table-cell__primary">
                      {line.description}
                    </div>
                    <div className="ink-table-cell__meta">
                      {line.product_code || "Sin código"} · {line.unit_code}
                      {line.inventory_controlled
                        ? " · Controla stock"
                        : " · Documental"}
                    </div>
                  </td>
                  <td>{qty(line.quantity)}</td>
                  <td>{qty(line.cancelled)}</td>
                  <td>{qty(line.assigned)}</td>
                  <td>{qty(line.in_transit)}</td>
                  <td>{qty(line.received)}</td>
                  <td>
                    <strong>{qty(line.pending_assignment)}</strong>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <section className="internal-transfer-dispatches">
        <div className="internal-transfer-section-title">
          <span>03</span>
          <div>
            <h2>Viajes y guías</h2>
            <p>
              Cada despacho representa un viaje y, si corresponde, su propia
              GRE.
            </p>
          </div>
        </div>
        {data.dispatches.length === 0 ? (
          <div className="internal-transfer-inline-empty">
            <Truck size={20} />
            <span>Aún no se ha preparado ningún despacho.</span>
          </div>
        ) : (
          data.dispatches.map((dispatch, index) => {
            const canDepart =
              !dispatch.departure_confirmed_at &&
              (!data.requires_gre ||
                ["emitida", "aceptada"].includes(dispatch.guide?.status));
            const canReceive =
              Boolean(dispatch.departure_confirmed_at) &&
              dispatch.lines.some(
                (line) =>
                  Number(line.received_quantity) <
                  Number(line.departed_quantity),
              );
            return (
              <article
                className="internal-transfer-dispatch-card"
                key={dispatch.id}
              >
                <div>
                  <span className="internal-transfer-dispatch-number">
                    Viaje {index + 1}
                  </span>
                  <strong>
                    {dispatch.guide
                      ? dispatch.guide.number
                      : data.requires_gre
                        ? "GRE pendiente"
                        : "Sin GRE requerida"}
                  </strong>
                  <small>
                    {dispatch.lines.length} línea
                    {dispatch.lines.length === 1 ? "" : "s"} · {dispatch.status}
                  </small>
                </div>
                <div className="internal-transfer-dispatch-actions">
                  {dispatch.guide ? (
                    <Link
                      className="btn btn-sm"
                      to={`/guias/${dispatch.guide.id}`}
                    >
                      <FilePlus2 size={14} />
                      Abrir GRE
                    </Link>
                  ) : (
                    data.requires_gre && (
                      <button
                        className="btn btn-sm"
                        type="button"
                        onClick={() => openGuide(dispatch)}
                      >
                        <FilePlus2 size={14} />
                        Crear GRE
                      </button>
                    )
                  )}
                  <button
                    className="btn btn-sm"
                    type="button"
                    disabled={!canDepart || saving}
                    onClick={() => confirmDeparture(dispatch)}
                  >
                    <Send size={14} />
                    Confirmar salida
                  </button>
                  <button
                    className="btn-primary btn-sm"
                    type="button"
                    disabled={!canReceive || saving}
                    onClick={() => openReceipt(dispatch)}
                  >
                    <PackageCheck size={14} />
                    Registrar recepción
                  </button>
                </div>
              </article>
            );
          })
        )}
      </section>

      <Drawer
        open={drawer === "edit"}
        onClose={() => setDrawer(null)}
        title="Editar traslado"
        subtitle="Solo es posible antes de preparar el primer despacho."
        icon={<Pencil size={20} />}
        footer={
          <>
            <button
              className="btn-ghost"
              type="button"
              onClick={() => setDrawer(null)}
            >
              Cancelar
            </button>
            <button
              className="btn-primary"
              type="submit"
              form="edit-transfer-form"
              disabled={saving}
            >
              {saving ? "Guardando…" : "Guardar cambios"}
            </button>
          </>
        }
      >
        <form
          id="edit-transfer-form"
          className="internal-transfer-form"
          onSubmit={editTransfer}
        >
          <label>
            Motivo operativo
            <textarea
              className="input mt-1 min-h-24"
              required
              minLength={3}
              value={editReason}
              onChange={(e) => setEditReason(e.target.value)}
            />
          </label>
          {data.lines.map((line) => (
            <label className="internal-transfer-quantity-row" key={line.id}>
              <span>
                <strong>{line.description}</strong>
                <small>{line.unit_code}</small>
              </span>
              <input
                className="input"
                type="number"
                min="0.0001"
                step="0.0001"
                required
                value={editQty[line.id] || ""}
                onChange={(e) =>
                  setEditQty({ ...editQty, [line.id]: e.target.value })
                }
              />
            </label>
          ))}
        </form>
      </Drawer>

      <Drawer
        open={drawer === "dispatch"}
        onClose={() => setDrawer(null)}
        title="Preparar despacho"
        subtitle="Las cantidades seleccionadas quedarán reservadas."
        icon={<Send size={20} />}
        footer={
          <>
            <button
              className="btn-ghost"
              type="button"
              onClick={() => setDrawer(null)}
            >
              Cancelar
            </button>
            <button
              className="btn-primary"
              type="submit"
              form="dispatch-form"
              disabled={saving}
            >
              {saving ? "Reservando…" : "Crear despacho"}
            </button>
          </>
        }
      >
        <form
          id="dispatch-form"
          className="internal-transfer-form"
          onSubmit={createDispatch}
        >
          {data.lines
            .filter((line) => Number(line.pending_assignment) > 0)
            .map((line) => (
              <label className="internal-transfer-quantity-row" key={line.id}>
                <span>
                  <strong>{line.description}</strong>
                  <small>
                    Disponible para asignar: {qty(line.pending_assignment)}{" "}
                    {line.unit_code}
                    {line.available_stock != null
                      ? ` · Stock libre: ${qty(line.available_stock)}`
                      : ""}
                  </small>
                </span>
                <input
                  className="input"
                  type="number"
                  min="0"
                  max={line.pending_assignment}
                  step="0.0001"
                  value={dispatchQty[line.id] || ""}
                  onChange={(e) =>
                    setDispatchQty({
                      ...dispatchQty,
                      [line.id]: e.target.value,
                    })
                  }
                />
              </label>
            ))}
        </form>
      </Drawer>

      <Drawer
        open={drawer === "guide"}
        onClose={() => setDrawer(null)}
        title="Datos de la GRE"
        subtitle={`Viaje del traslado TI-${data.id}`}
        icon={<Truck size={20} />}
        footer={
          <>
            <button
              className="btn-ghost"
              type="button"
              onClick={() => setDrawer(null)}
            >
              Cancelar
            </button>
            <button
              className="btn-primary"
              type="submit"
              form="guide-form"
              disabled={saving}
            >
              {saving ? "Creando…" : "Crear borrador GRE"}
            </button>
          </>
        }
      >
        <form
          id="guide-form"
          className="internal-transfer-form"
          onSubmit={createGuide}
        >
          <div className="internal-transfer-form-grid">
            <label>
              Inicio del traslado
              <input
                className="input mt-1"
                required
                type="datetime-local"
                value={guide.fecha_traslado}
                onChange={(e) =>
                  setGuide({ ...guide, fecha_traslado: e.target.value })
                }
              />
            </label>
            <label>
              Peso bruto
              <input
                className="input mt-1"
                required
                type="number"
                min="0.001"
                step="0.001"
                value={guide.peso_bruto_total}
                onChange={(e) =>
                  setGuide({ ...guide, peso_bruto_total: e.target.value })
                }
              />
            </label>
          </div>
          <div className="internal-transfer-form-grid">
            <label>
              Unidad de peso
              <CustomSelect
                value={guide.unidad_medida_peso}
                onChange={(value) =>
                  setGuide({ ...guide, unidad_medida_peso: value })
                }
                options={[
                  { value: "KGM", label: "Kilogramos" },
                  { value: "TNE", label: "Toneladas" },
                ]}
              />
            </label>
            <label>
              Número de bultos
              <input
                className="input mt-1"
                type="number"
                min="1"
                value={guide.numero_bultos}
                onChange={(e) =>
                  setGuide({ ...guide, numero_bultos: e.target.value })
                }
              />
            </label>
          </div>
          <label>
            Modalidad
            <CustomSelect
              value={guide.modalidad_traslado}
              onChange={(value) =>
                setGuide({
                  ...guide,
                  modalidad_traslado: value,
                  indicador_m1_l: false,
                  registrar_vehiculo_transportista: false,
                })
              }
              options={[
                { value: "02", label: "Transporte privado" },
                { value: "01", label: "Transporte público" },
              ]}
            />
          </label>
          <label className="internal-transfer-check">
            <input
              type="checkbox"
              checked={guide.indicador_m1_l}
              onChange={(e) =>
                setGuide({
                  ...guide,
                  indicador_m1_l: e.target.checked,
                  registrar_vehiculo_transportista: false,
                })
              }
            />
            <span>
              <strong>Vehículo M1 o L</strong>
              <small>No exige conductor dentro del supuesto habilitado.</small>
            </span>
          </label>
          {guide.modalidad_traslado === "01" && (
            <>
              <label>
                Entrega al transportista
                <input
                  className="input mt-1"
                  required
                  type="datetime-local"
                  value={guide.fecha_entrega_transportista}
                  onChange={(e) =>
                    setGuide({
                      ...guide,
                      fecha_entrega_transportista: e.target.value,
                    })
                  }
                />
              </label>
              <div className="internal-transfer-form-grid">
                <label>
                  RUC del transportista
                  <input
                    className="input mt-1"
                    required
                    pattern="[0-9]{11}"
                    value={guide.transportista_ruc}
                    onChange={(e) =>
                      setGuide({
                        ...guide,
                        transportista_ruc: e.target.value.replace(/\D/g, ""),
                      })
                    }
                  />
                </label>
                <label>
                  Registro MTC
                  <input
                    className="input mt-1"
                    required
                    value={guide.transportista_nro_mtc}
                    onChange={(e) =>
                      setGuide({
                        ...guide,
                        transportista_nro_mtc: e.target.value,
                      })
                    }
                  />
                </label>
              </div>
              <label>
                Razón social
                <input
                  className="input mt-1"
                  required
                  value={guide.transportista_razon_social}
                  onChange={(e) =>
                    setGuide({
                      ...guide,
                      transportista_razon_social: e.target.value,
                    })
                  }
                />
              </label>
              {!guide.indicador_m1_l && (
                <label className="internal-transfer-check">
                  <input
                    type="checkbox"
                    checked={guide.registrar_vehiculo_transportista}
                    onChange={(e) =>
                      setGuide({
                        ...guide,
                        registrar_vehiculo_transportista: e.target.checked,
                      })
                    }
                  />
                  <span>
                    <strong>
                      Registrar vehículo y conductor del transportista
                    </strong>
                    <small>
                      Requiere confirmar el acuerdo y completar los datos de
                      circulación.
                    </small>
                  </span>
                </label>
              )}
            </>
          )}
          {!guide.indicador_m1_l &&
            (guide.modalidad_traslado === "02" ||
              guide.registrar_vehiculo_transportista) && (
              <>
                <div className="internal-transfer-form-grid">
                  <label>
                    DNI/documento del conductor
                    <input
                      className="input mt-1"
                      required
                      value={guide.conductor_nro_doc}
                      onChange={(e) =>
                        setGuide({
                          ...guide,
                          conductor_nro_doc: e.target.value,
                        })
                      }
                    />
                  </label>
                  <label>
                    Licencia
                    <input
                      className="input mt-1"
                      required
                      value={guide.conductor_licencia}
                      onChange={(e) =>
                        setGuide({
                          ...guide,
                          conductor_licencia: e.target.value.toUpperCase(),
                        })
                      }
                    />
                  </label>
                </div>
                <div className="internal-transfer-form-grid">
                  <label>
                    Nombres
                    <input
                      className="input mt-1"
                      required
                      value={guide.conductor_nombres}
                      onChange={(e) =>
                        setGuide({
                          ...guide,
                          conductor_nombres: e.target.value,
                        })
                      }
                    />
                  </label>
                  <label>
                    Apellidos
                    <input
                      className="input mt-1"
                      required
                      value={guide.conductor_apellidos}
                      onChange={(e) =>
                        setGuide({
                          ...guide,
                          conductor_apellidos: e.target.value,
                        })
                      }
                    />
                  </label>
                </div>
                {guide.registrar_vehiculo_transportista && (
                  <>
                    <label>
                      Número de circulación
                      <input
                        className="input mt-1"
                        required
                        value={guide.vehiculo_nro_circulacion}
                        onChange={(e) =>
                          setGuide({
                            ...guide,
                            vehiculo_nro_circulacion: e.target.value,
                          })
                        }
                      />
                    </label>
                    <label className="internal-transfer-check">
                      <input
                        type="checkbox"
                        checked={guide.transportista_acuerdo_confirmado}
                        onChange={(e) =>
                          setGuide({
                            ...guide,
                            transportista_acuerdo_confirmado: e.target.checked,
                          })
                        }
                      />
                      <span>
                        <strong>
                          Confirmo el acuerdo con el transportista
                        </strong>
                        <small>
                          La confirmación quedará auditada con usuario y fecha.
                        </small>
                      </span>
                    </label>
                  </>
                )}
              </>
            )}
          {(guide.modalidad_traslado === "02" ||
            guide.indicador_m1_l ||
            guide.registrar_vehiculo_transportista) && (
            <label>
              Placa
              <input
                className="input mt-1 uppercase"
                required
                value={guide.vehiculo_placa}
                onChange={(e) =>
                  setGuide({
                    ...guide,
                    vehiculo_placa: e.target.value.toUpperCase(),
                  })
                }
              />
            </label>
          )}
          <label>
            Observaciones
            <textarea
              className="input mt-1 min-h-24"
              value={guide.observaciones}
              onChange={(e) =>
                setGuide({ ...guide, observaciones: e.target.value })
              }
            />
          </label>
          <p className="internal-transfer-note">
            <AlertTriangle size={15} />
            La serie y el correlativo se asignan en backend según la
            configuración de la empresa.
          </p>
        </form>
      </Drawer>

      <Drawer
        open={drawer === "receipt"}
        onClose={() => setDrawer(null)}
        title="Registrar recepción"
        subtitle="Ingresa solo las cantidades físicamente recibidas."
        icon={<PackageCheck size={20} />}
        footer={
          <>
            <button
              className="btn-ghost"
              type="button"
              onClick={() => setDrawer(null)}
            >
              Cancelar
            </button>
            <button
              className="btn-primary"
              type="submit"
              form="receipt-form"
              disabled={saving}
            >
              {saving ? "Registrando…" : "Confirmar recepción"}
            </button>
          </>
        }
      >
        <form
          id="receipt-form"
          className="internal-transfer-form"
          onSubmit={receive}
        >
          {selectedDispatch?.lines.map((line) => {
            const transferLine = data.lines.find(
              (item) => item.id === line.transfer_line_id,
            );
            const remaining = Math.max(
              0,
              Number(line.departed_quantity) - Number(line.received_quantity),
            );
            return (
              <label className="internal-transfer-quantity-row" key={line.id}>
                <span>
                  <strong>
                    {transferLine?.description || `Línea ${line.id}`}
                  </strong>
                  <small>Pendiente por recibir: {qty(remaining)}</small>
                </span>
                <input
                  className="input"
                  type="number"
                  min="0"
                  max={remaining}
                  step="0.0001"
                  value={receiptQty[line.id] || ""}
                  onChange={(e) =>
                    setReceiptQty({ ...receiptQty, [line.id]: e.target.value })
                  }
                />
              </label>
            );
          })}
          <label>
            Observación <small>(opcional)</small>
            <textarea
              className="input mt-1 min-h-24"
              value={receiptNote}
              onChange={(e) => setReceiptNote(e.target.value)}
              placeholder="Ej. Recepción parcial, embalaje pendiente de revisión"
            />
          </label>
          <p className="internal-transfer-note">
            <CheckCircle2 size={15} />
            El stock ingresará al destino solo por las cantidades confirmadas.
          </p>
        </form>
      </Drawer>
    </div>
  );
}
