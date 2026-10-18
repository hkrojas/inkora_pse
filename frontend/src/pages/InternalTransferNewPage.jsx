import { useEffect, useRef, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  Boxes,
  Check,
  PackagePlus,
  Plus,
  Search,
  Trash2,
} from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import CustomSelect from "../components/ui/CustomSelect";
import Spinner from "../components/ui/Spinner";
import TransferTransportFields, {
  newTransferTransport,
  transferTransportPayload,
} from "../components/transfers/TransferTransportFields";
import { useAuth } from "../context/AuthContext";
import { useFiscalFeatures } from "../hooks/useFiscalFeatures";
import { internalTransfers } from "../services/internalTransfers";
import { inventory } from "../services/inventory";
import { productos } from "../services/productos";
import { SUNAT_UNIT_OPTIONS } from "../lib/utils/sunatCatalogs";
import "../styles/internalTransferWizard.css";

const steps = ["Qué trasladar", "Transporte", "Revisar"];
const units = SUNAT_UNIT_OPTIONS.filter((unit) => unit.value !== "ZZ").map(
  (unit) => ({ ...unit, label: unit.label.replace(/^[A-Z0-9]+\s*-\s*/, "") }),
);
const unitName = (code) =>
  units.find((unit) => unit.value === code)?.label || code;
const qty = (value) =>
  Number(value || 0).toLocaleString("es-PE", { maximumFractionDigits: 4 });
const positiveQuantity = (value) =>
  Number.isFinite(Number(value)) &&
  Number(value) > 0 &&
  Math.abs(Number(value) * 10000 - Math.round(Number(value) * 10000)) <
    0.000001;
const emptyRoute = {
  source_warehouse_id: "",
  destination_warehouse_id: "",
  reason: "",
};
function readProgress(key) {
  try {
    const saved = JSON.parse(sessionStorage.getItem(key));
    return saved?.version === 1 &&
      saved.snapshot &&
      saved.keys &&
      saved.transferPayload
      ? saved
      : null;
  } catch {
    return null;
  }
}

export default function InternalTransferNewPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const features = useFiscalFeatures();
  const progressKey = `inkora-transfer-wizard:${user?.tenant_id}:${user?.id}`;
  const [checkpoint, setCheckpoint] = useState(() => readProgress(progressKey));
  const progressRef = useRef(checkpoint);
  const [form, setForm] = useState(
    () => checkpoint?.snapshot.form || emptyRoute,
  );
  const [lines, setLines] = useState(() => checkpoint?.snapshot.lines || []);
  const [guide, setGuide] = useState(
    () => checkpoint?.snapshot.guide || newTransferTransport(),
  );
  const [split, setSplit] = useState(() => checkpoint?.snapshot.split || false);
  const [step, setStep] = useState(checkpoint ? 2 : 0);
  const [warehouses, setWarehouses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const busyRef = useRef(false);
  const [savingLabel, setSavingLabel] = useState("");
  const headingRef = useRef(null);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [addingProducts, setAddingProducts] = useState(0);
  const [searchError, setSearchError] = useState("");
  const [availability, setAvailability] = useState({});
  const [checkingStock, setCheckingStock] = useState(false);
  const [stockError, setStockError] = useState("");
  const [stockRefresh, setStockRefresh] = useState(0);

  const loadWarehouses = () => {
    setLoading(true);
    setLoadError("");
    inventory
      .warehouses()
      .then(setWarehouses)
      .catch((err) =>
        setLoadError(
          err.message ||
            "No se pudieron cargar los almacenes. Inténtalo nuevamente.",
        ),
      )
      .finally(() => setLoading(false));
  };
  useEffect(loadWarehouses, []);
  useEffect(() => {
    headingRef.current?.focus({ preventScroll: true });
    headingRef.current
      ?.closest(".transfer-wizard")
      ?.scrollIntoView({ block: "start" });
  }, [step, loading, features.loading]);
  useEffect(() => {
    const term = query.trim();
    setSearchError("");
    if (term.length < 2) {
      setResults([]);
      setSearching(false);
      return undefined;
    }
    let active = true;
    const controller = new AbortController();
    setSearching(true);
    const timer = setTimeout(
      () =>
        productos
          .search(term, 12, { signal: controller.signal })
          .then((rows) => {
            if (active) setResults(rows);
          })
          .catch((err) => {
            if (active && !err.isCanceled) {
              setResults([]);
              setSearchError(
                "No pudimos buscar productos. Inténtalo nuevamente.",
              );
            }
          })
          .finally(() => {
            if (active) setSearching(false);
          }),
      250,
    );
    return () => {
      active = false;
      controller.abort();
      clearTimeout(timer);
    };
  }, [query]);
  const productIds = lines
    .filter((line) => line.product_id)
    .map((line) => line.product_id)
    .sort((a, b) => a - b)
    .join(",");
  useEffect(() => {
    setAvailability({});
    setStockError("");
    if (!form.source_warehouse_id || !productIds || checkpoint) {
      setCheckingStock(false);
      return undefined;
    }
    let active = true;
    setCheckingStock(true);
    inventory
      .availability({
        warehouse_id: Number(form.source_warehouse_id),
        items: productIds
          .split(",")
          .map((id) => ({ product_id: Number(id), quantity: 1 })),
      })
      .then((rows) => {
        if (active)
          setAvailability(
            Object.fromEntries(rows.map((row) => [row.product_id, row])),
          );
      })
      .catch(() => {
        if (active)
          setStockError(
            "No se pudo comprobar el stock en origen. Vuelve a consultarlo antes de continuar.",
          );
      })
      .finally(() => {
        if (active) setCheckingStock(false);
      });
    return () => {
      active = false;
    };
  }, [form.source_warehouse_id, productIds, checkpoint, stockRefresh]);

  const verifiedWarehouses = warehouses.filter(
    (row) =>
      row.is_active !== false &&
      row.establishment?.is_active &&
      row.establishment?.verified_at,
  );
  const source =
    verifiedWarehouses.find(
      (row) => String(row.id) === String(form.source_warehouse_id),
    ) || checkpoint?.snapshot.source;
  const destination =
    verifiedWarehouses.find(
      (row) => String(row.id) === String(form.destination_warehouse_id),
    ) || checkpoint?.snapshot.destination;
  const requiresGuide = Boolean(
    source &&
      destination &&
      source.establishment_id !== destination.establishment_id,
  );
  const tripQuantity = (line) =>
    Number(split ? line.trip_quantity : line.quantity);
  const quantityError = (line) => {
    if (!positiveQuantity(line.quantity))
      return "Ingresa una cantidad mayor que 0, con hasta cuatro decimales.";
    const trip = tripQuantity(line);
    if (
      !Number.isFinite(trip) ||
      trip < 0 ||
      (trip > 0 && !positiveQuantity(trip))
    )
      return "Revisa la cantidad de este viaje.";
    if (trip > Number(line.quantity))
      return "Este viaje no puede superar la cantidad total.";
    const stock = availability[line.product_id];
    if (stock && trip > Math.max(0, Number(stock.available)))
      return `Solo hay ${qty(stock.available)} disponibles en origen. Reduce la cantidad de este viaje.`;
    return "";
  };
  const validGoods = Boolean(
    source &&
      destination &&
      source.id !== destination.id &&
      form.reason.trim().length >= 3 &&
      lines.length &&
      lines.every(
        (line) =>
          line.description.trim() && line.unit_code && !quantityError(line),
      ) &&
      lines.some((line) => tripQuantity(line) > 0) &&
      !checkingStock &&
      !stockError &&
      !addingProducts,
  );
  const updateLine = (key, patch) =>
    setLines((current) =>
      current.map((line) => (line.key === key ? { ...line, ...patch } : line)),
    );
  const addProduct = async (product) => {
    if (lines.some((line) => line.product_id === product.id)) {
      setSearchError(
        "Este producto ya está incluido. Cambia su cantidad en la lista.",
      );
      return;
    }
    setQuery("");
    setResults([]);
    setAddingProducts((count) => count + 1);
    try {
      const detail = await productos.get(product.id);
      if (detail.item_type === "service") {
        setSearchError("Los servicios no se trasladan. Selecciona un bien.");
        return;
      }
      setLines((current) =>
        current.some((line) => line.product_id === product.id)
          ? current
          : [
              ...current,
              {
                key: crypto.randomUUID(),
                product_id: product.id,
                description: product.nombre,
                product_code: product.codigo_interno || "",
                unit_code: product.unidad_medida || "NIU",
                quantity: "1",
                trip_quantity: "1",
                manual_goods_confirmed: false,
              },
            ],
      );
    } catch {
      setSearchError(
        "No se pudo agregar el producto. Búscalo e inténtalo nuevamente.",
      );
    } finally {
      setAddingProducts((count) => count - 1);
    }
  };
  const changeStep = (next) => {
    setError("");
    setStep(next);
  };
  const next = (event) => {
    event.preventDefault();
    if (step === 0 && !validGoods) {
      setError(
        "Completa la ruta, el motivo y las cantidades disponibles para este viaje.",
      );
      return;
    }
    if (requiresGuide && !features.isEnabled("guides")) {
      setError("La creación de guías no está habilitada para esta empresa.");
      return;
    }
    if (step === 1 && requiresGuide) {
      const dates = [guide.fecha_traslado];
      if (guide.modalidad_traslado === "01") dates.push(guide.fecha_entrega_transportista);
      if (dates.some((date) => !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(date) || Number.isNaN(new Date(date).getTime()))) {
        setError("Selecciona la fecha y completa la hora de salida y, cuando corresponda, de entrega al transportista.");
        return;
      }
    }
    if (
      step === 1 &&
      requiresGuide &&
      guide.fecha_traslado.slice(0, 10) <
        new Date().toLocaleDateString("en-CA", { timeZone: "America/Lima" })
    ) {
      setError("La fecha de salida no puede ser anterior a hoy.");
      return;
    }
    changeStep(step + 1);
  };
  const persist = (progress) => {
    sessionStorage.setItem(progressKey, JSON.stringify(progress));
    progressRef.current = progress;
    setCheckpoint(progress);
  };
  const finish = async () => {
    if (busyRef.current || (!checkpoint && !validGoods)) return;
    busyRef.current = true;
    setSaving(true);
    setError("");
    try {
      let progress = progressRef.current;
      if (!progress) {
        progress = {
          version: 1,
          snapshot: { form, lines, guide, split, source, destination },
          keys: {
            transfer: crypto.randomUUID(),
            dispatch: crypto.randomUUID(),
            guide: crypto.randomUUID(),
          },
          transferPayload: {
            source_warehouse_id: Number(source.id),
            destination_warehouse_id: Number(destination.id),
            source_establishment_id: source.establishment_id,
            destination_establishment_id: destination.establishment_id,
            reason: form.reason.trim(),
            lines: lines.map((line) => ({
              product_id: line.product_id,
              description: line.description.trim(),
              product_code: line.product_code || null,
              unit_code: line.unit_code,
              quantity: Number(line.quantity),
              manual_goods_confirmed: line.manual_goods_confirmed,
            })),
          },
          tripQuantities: lines.map(tripQuantity),
          transportPayload: requiresGuide
            ? transferTransportPayload(guide)
            : null,
        };
        persist(progress);
      }
      if (!progress.transfer) {
        setSavingLabel("Guardando traslado…");
        const transfer = await internalTransfers.create({
          ...progress.transferPayload,
          idempotency_key: progress.keys.transfer,
        });
        progress = { ...progress, transfer };
        persist(progress);
      }
      if (!progress.dispatchPayload) {
        const savedLines = progress.transfer.lines;
        let manualIndex = 0;
        const manualLines = savedLines.filter((line) => !line.product_id);
        const selections = progress.transferPayload.lines
          .map((line, index) => {
            const saved = line.product_id
              ? savedLines.find((item) => item.product_id === line.product_id)
              : manualLines[manualIndex++];
            if (!saved)
              throw new Error(
                "No se pudieron vincular los bienes guardados. Abre el traslado para revisarlo.",
              );
            return {
              transfer_line_id: saved.id,
              quantity: progress.tripQuantities[index],
            };
          })
          .filter((line) => line.quantity > 0);
        progress = {
          ...progress,
          dispatchPayload: {
            idempotency_key: progress.keys.dispatch,
            lines: selections,
          },
        };
        persist(progress);
      }
      if (!progress.dispatchId) {
        setSavingLabel("Preparando viaje…");
        const result = await internalTransfers.createDispatch(
          progress.transfer.id,
          progress.dispatchPayload,
        );
        progress = { ...progress, dispatchId: result.dispatch_id };
        persist(progress);
      }
      if (progress.transfer.requires_gre && !progress.guideId) {
        setSavingLabel("Creando guía…");
        const savedGuide = await internalTransfers.createGuide({
          ...progress.transportPayload,
          dispatch_id: progress.dispatchId,
          idempotency_key: progress.keys.guide,
          partida_ubigeo: progress.transfer.source_establishment.ubigeo,
          partida_direccion: progress.transfer.source_establishment.address,
          llegada_ubigeo: progress.transfer.destination_establishment.ubigeo,
          llegada_direccion:
            progress.transfer.destination_establishment.address,
        });
        progress = { ...progress, guideId: savedGuide.id };
        persist(progress);
      }
      sessionStorage.removeItem(progressKey);
      navigate(
        progress.guideId
          ? `/guias/${progress.guideId}`
          : `/traslados-internos/${progress.transfer.id}`,
        { replace: true },
      );
    } catch (err) {
      setError(
        err.message ||
          "No se pudo completar el guardado. Reintenta para continuar desde donde quedó.",
      );
    } finally {
      busyRef.current = false;
      setSaving(false);
    }
  };

  if (loading || features.loading)
    return (
      <div className="page-shell">
        <Spinner />
      </div>
    );
  if (!features.isEnabled("internal_transfers"))
    return (
      <div className="page-shell">
        <p className="ink-inline-alert ink-inline-alert-info">
          Los traslados internos no están habilitados para esta empresa.
        </p>
        <Link to="/guias" className="btn">
          Volver a guías
        </Link>
      </div>
    );
  if (loadError && !checkpoint)
    return (
      <div className="page-shell">
        <p role="alert">{loadError}</p>
        <button className="btn" onClick={loadWarehouses}>
          Volver a cargar almacenes
        </button>
      </div>
    );
  return (
    <div className="page-shell internal-transfer-page transfer-wizard max-w-6xl">
      <header className="page-header internal-transfer-hero">
        <div className="page-header-copy">
          <Link className="internal-transfer-back" to="/traslados-internos">
            <ArrowLeft size={15} />
            Traslados
          </Link>
          <h1 className="page-title">Nuevo traslado interno</h1>
          <p className="page-subtitle">
            Prepara tu traslado y su guía en tres pasos.
          </p>
        </div>
      </header>
      {verifiedWarehouses.length < 2 && !checkpoint ? (
        <section className="internal-transfer-card internal-transfer-blocker">
          <Boxes size={22} />
          <div>
            <h2>Prepara tus almacenes</h2>
            <p>
              Necesitas dos almacenes activos con sus datos de dirección
              verificados.
            </p>
          </div>
          <Link className="btn-primary" to="/inventario?tab=warehouses">
            Configurar almacenes
          </Link>
        </section>
      ) : (
        <>
          <nav
            aria-label="Pasos del traslado"
            className="transfer-wizard__steps"
          >
            <ol>
              {steps.map((label, index) => (
                <li key={label}>
                  <button
                    type="button"
                    aria-current={step === index ? "step" : undefined}
                    disabled={saving || Boolean(checkpoint) || index > step}
                    onClick={() => changeStep(index)}
                  >
                    <span className="transfer-wizard__step-number">
                      {index < step ? <Check size={16} /> : index + 1}
                    </span>
                    <span>{label}</span>
                  </button>
                </li>
              ))}
            </ol>
          </nav>
          <form
            onSubmit={
              step < 2
                ? next
                : (event) => {
                    event.preventDefault();
                    finish();
                  }
            }
          >
            <section
              className="internal-transfer-card transfer-wizard__panel"
              key={step}
              aria-labelledby="transfer-step-title"
            >
              <div className="transfer-wizard__section-head">
                <p>Paso {step + 1} de 3</p>
                <h2 id="transfer-step-title" tabIndex={-1} ref={headingRef}>
                  {
                    [
                      "¿Qué vas a trasladar?",
                      "¿Cómo se transportará?",
                      "Revisa antes de crear",
                    ][step]
                  }
                </h2>
              </div>
              {step === 0 && (
                <>
                  <div className="transfer-wizard__grid">
                    <div className="transfer-wizard__field">
                      <span>Almacén de salida</span>
                      <CustomSelect
                        ariaLabel="Almacén de salida"
                        required
                        value={form.source_warehouse_id}
                        onChange={(value) =>
                          setForm({
                            ...form,
                            source_warehouse_id: value,
                            destination_warehouse_id:
                              String(value) ===
                              String(form.destination_warehouse_id)
                                ? ""
                                : form.destination_warehouse_id,
                          })
                        }
                        options={verifiedWarehouses.map((row) => ({
                          value: row.id,
                          label: row.name,
                        }))}
                      />
                      {source && <small>{source.establishment.address}</small>}
                    </div>
                    <div className="transfer-wizard__field">
                      <span>Almacén de llegada</span>
                      <CustomSelect
                        ariaLabel="Almacén de llegada"
                        required
                        value={form.destination_warehouse_id}
                        onChange={(value) =>
                          setForm({ ...form, destination_warehouse_id: value })
                        }
                        options={verifiedWarehouses
                          .filter(
                            (row) =>
                              String(row.id) !==
                              String(form.source_warehouse_id),
                          )
                          .map((row) => ({ value: row.id, label: row.name }))}
                      />
                      {destination && (
                        <small>{destination.establishment.address}</small>
                      )}
                    </div>
                  </div>
                  <label className="transfer-wizard__field">
                    <span>¿Para qué haces el traslado?</span>
                    <input
                      className="input"
                      required
                      minLength={3}
                      maxLength={500}
                      placeholder="Ej. Reponer papel en la tienda"
                      value={form.reason}
                      onChange={(event) =>
                        setForm({ ...form, reason: event.target.value })
                      }
                    />
                  </label>
                  <div className="transfer-wizard__goods-heading">
                    <h3>Bienes que vas a llevar</h3>
                    <button
                      className="btn btn-sm"
                      type="button"
                      onClick={() =>
                        setLines((current) => [
                          ...current,
                          {
                            key: crypto.randomUUID(),
                            product_id: null,
                            description: "",
                            product_code: "",
                            unit_code: "NIU",
                            quantity: "1",
                            trip_quantity: "1",
                            manual_goods_confirmed: true,
                          },
                        ])
                      }
                    >
                      <Plus size={16} />
                      Agregar otro bien
                    </button>
                  </div>
                  <div className="internal-transfer-product-search">
                    <Search size={16} />
                    <input
                      aria-label="Buscar producto"
                      placeholder="Buscar producto por nombre o código"
                      value={query}
                      maxLength={80}
                      onChange={(event) => setQuery(event.target.value)}
                    />
                    {searching && <span role="status">Buscando…</span>}
                  </div>
                  {searchError && (
                    <p className="transfer-wizard__error" role="alert">
                      {searchError}
                    </p>
                  )}
                  {addingProducts > 0 && (
                    <p role="status" className="transfer-wizard__muted">
                      Agregando producto…
                    </p>
                  )}
                  {!searching &&
                    query.trim().length >= 2 &&
                    !results.length &&
                    !searchError && (
                      <p className="transfer-wizard__muted">
                        No encontramos productos. Puedes agregar otro bien sin
                        control de stock.
                      </p>
                    )}
                  {results.length > 0 && (
                    <div className="internal-transfer-search-results">
                      {results.map((product) => (
                        <button
                          type="button"
                          key={product.id}
                          onClick={() => addProduct(product)}
                        >
                          <PackagePlus size={16} />
                          <span>
                            <strong>{product.nombre}</strong>
                            <small>
                              {product.codigo_interno || "Sin código"}
                            </small>
                          </span>
                          <Plus size={16} />
                        </button>
                      ))}
                    </div>
                  )}
                  <label className="transfer-wizard__check">
                    <input
                      type="checkbox"
                      checked={split}
                      onChange={(event) => {
                        setSplit(event.target.checked);
                        setLines((current) =>
                          current.map((line) => ({
                            ...line,
                            trip_quantity: line.quantity,
                          })),
                        );
                      }}
                    />
                    <span>
                      Lo llevaré en varios viajes
                      <small>
                        Indica el total solicitado y cuánto llevarás en este
                        primer viaje.
                      </small>
                    </span>
                  </label>
                  {checkingStock && (
                    <p role="status" className="transfer-wizard__muted">
                      Consultando stock en origen…
                    </p>
                  )}
                  {stockError && (
                    <div
                      className="ink-inline-alert ink-inline-alert-warning"
                      role="alert"
                    >
                      {stockError}
                      <button
                        className="btn btn-sm"
                        type="button"
                        onClick={() => setStockRefresh((value) => value + 1)}
                      >
                        Volver a consultar stock
                      </button>
                    </div>
                  )}
                  {lines.length ? (
                    <table className="ink-table transfer-wizard__items">
                      <thead>
                        <tr>
                          <th>Bien</th>
                          <th>{split ? "Total solicitado" : "Cantidad"}</th>
                          {split && <th>Este viaje</th>}
                          <th>
                            <span className="sr-only">Acciones</span>
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {lines.map((line, index) => (
                          <tr key={line.key}>
                            <td>
                              <div className="transfer-wizard__item-name">
                                {line.product_id ? (
                                  <strong>{line.description}</strong>
                                ) : (
                                  <>
                                    <input
                                      className="input"
                                      aria-label={`Descripción del bien ${index + 1}`}
                                      required
                                      maxLength={500}
                                      placeholder="Describe el bien"
                                      value={line.description}
                                      onChange={(event) =>
                                        updateLine(line.key, {
                                          description: event.target.value,
                                        })
                                      }
                                    />
                                    <small>Sin control de stock</small>
                                  </>
                                )}
                                <div className="transfer-wizard__item-meta">
                                  {line.product_id ? (
                                    <small>
                                      {line.product_code} ·{" "}
                                      {unitName(line.unit_code)}
                                    </small>
                                  ) : (
                                    <>
                                      <CustomSelect
                                        ariaLabel={`Unidad del bien ${index + 1}`}
                                        value={line.unit_code}
                                        onChange={(value) =>
                                          updateLine(line.key, {
                                            unit_code: value,
                                          })
                                        }
                                        options={units}
                                      />
                                      <details>
                                        <summary>Código (opcional)</summary>
                                        <input
                                          className="input"
                                          aria-label={`Código del bien ${index + 1}`}
                                          maxLength={30}
                                          value={line.product_code}
                                          onChange={(event) =>
                                            updateLine(line.key, {
                                              product_code: event.target.value,
                                            })
                                          }
                                        />
                                      </details>
                                    </>
                                  )}
                                  {availability[line.product_id] && (
                                    <small>
                                      Disponible en origen:{" "}
                                      {qty(
                                        availability[line.product_id].available,
                                      )}
                                    </small>
                                  )}
                                </div>
                                {quantityError(line) && (
                                  <p
                                    id={`line-error-${line.key}`}
                                    className="transfer-wizard__error"
                                    role="alert"
                                  >
                                    {quantityError(line)}
                                  </p>
                                )}
                              </div>
                            </td>
                            <td>
                              <label>
                                <span className="transfer-wizard__mobile-label">
                                  {split ? "Total solicitado" : "Cantidad"}
                                </span>
                                <input
                                  className="input"
                                  aria-label={`Cantidad total del bien ${index + 1}`}
                                  type="number"
                                  required
                                  min="0.0001"
                                  step="0.0001"
                                  aria-invalid={Boolean(quantityError(line))}
                                  aria-describedby={
                                    quantityError(line)
                                      ? `line-error-${line.key}`
                                      : undefined
                                  }
                                  value={line.quantity}
                                  onChange={(event) =>
                                    updateLine(line.key, {
                                      quantity: event.target.value,
                                    })
                                  }
                                />
                              </label>
                            </td>
                            {split && (
                              <td>
                                <label>
                                  <span className="transfer-wizard__mobile-label">
                                    Este viaje
                                  </span>
                                  <input
                                    className="input"
                                    aria-label={`Cantidad de este viaje del bien ${index + 1}`}
                                    type="number"
                                    required
                                    min="0"
                                    max={line.quantity}
                                    step="0.0001"
                                    value={line.trip_quantity}
                                    onChange={(event) =>
                                      updateLine(line.key, {
                                        trip_quantity: event.target.value,
                                      })
                                    }
                                  />
                                </label>
                              </td>
                            )}
                            <td>
                              <button
                                type="button"
                                className="ink-row-btn"
                                aria-label={`Quitar bien ${index + 1}`}
                                onClick={() =>
                                  setLines((current) =>
                                    current.filter(
                                      (item) => item.key !== line.key,
                                    ),
                                  )
                                }
                              >
                                <Trash2 size={16} />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : (
                    <div className="internal-transfer-inline-empty">
                      <Boxes size={22} />
                      <span>
                        Busca un producto o agrega un bien que no esté en tu
                        catálogo.
                      </span>
                    </div>
                  )}
                </>
              )}
              {step === 1 &&
                (requiresGuide ? (
                  <TransferTransportFields value={guide} onChange={setGuide} />
                ) : (
                  <p className="ink-inline-alert ink-inline-alert-info">
                    Los dos almacenes pertenecen al mismo establecimiento.
                    Prepararemos el viaje interno sin una guía de remisión.
                  </p>
                ))}
              {step === 2 && (
                <>
                  <div className="transfer-wizard__review-heading">
                    <h3>Ruta y bienes</h3>
                    {!checkpoint && (
                      <button
                        className="btn-ghost"
                        type="button"
                        onClick={() => changeStep(0)}
                      >
                        Editar bienes
                      </button>
                    )}
                  </div>
                  <div className="transfer-wizard__route">
                    <div>
                      <span>Salida</span>
                      <strong>{source?.name}</strong>
                      <small>{source?.establishment.address}</small>
                    </div>
                    <ArrowRight size={22} />
                    <div>
                      <span>Llegada</span>
                      <strong>{destination?.name}</strong>
                      <small>{destination?.establishment.address}</small>
                    </div>
                  </div>
                  <p className="transfer-wizard__reason">{form.reason}</p>
                  <table className="ink-table transfer-wizard__review-items">
                    <thead>
                      <tr>
                        <th>Bien</th>
                        <th>Este viaje</th>
                        {split && <th>Otro viaje</th>}
                      </tr>
                    </thead>
                    <tbody>
                      {lines.map((line) => (
                        <tr key={line.key}>
                          <td>
                            <strong>{line.description}</strong>
                            <small>{unitName(line.unit_code)}</small>
                          </td>
                          <td>{qty(tripQuantity(line))}</td>
                          {split && (
                            <td>
                              {qty(Number(line.quantity) - tripQuantity(line))}
                            </td>
                          )}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {requiresGuide && (
                    <>
                      <div className="transfer-wizard__review-heading">
                        <h3>Transporte</h3>
                        {!checkpoint && (
                          <button
                            className="btn-ghost"
                            type="button"
                            onClick={() => changeStep(1)}
                          >
                            Editar transporte
                          </button>
                        )}
                      </div>
                      <dl className="transfer-wizard__summary">
                        <div>
                          <dt>Salida prevista</dt>
                          <dd>
                            {new Date(guide.fecha_traslado).toLocaleString(
                              "es-PE",
                              { dateStyle: "short", timeStyle: "short" },
                            )}
                          </dd>
                        </div>
                        <div>
                          <dt>Peso total</dt>
                          <dd>
                            {qty(guide.peso_bruto_total)}{" "}
                            {guide.unidad_medida_peso === "KGM"
                              ? "kg"
                              : "toneladas"}
                          </dd>
                        </div>
                        <div>
                          <dt>Quién lo lleva</dt>
                          <dd>
                            {guide.modalidad_traslado === "02"
                              ? "Nosotros"
                              : guide.transportista_razon_social ||
                                "Transportista con vehículo M1 o L"}
                          </dd>
                        </div>
                        <div>
                          <dt>
                            {guide.indicador_m1_l
                              ? "Vehículo M1 o L"
                              : guide.modalidad_traslado === "02" ||
                                  guide.registrar_vehiculo_transportista
                                ? "Conductor y placa"
                                : "RUC del transportista"}
                          </dt>
                          <dd>
                            {guide.indicador_m1_l
                              ? guide.vehiculo_placa
                              : guide.modalidad_traslado === "02" ||
                                  guide.registrar_vehiculo_transportista
                                ? `${guide.conductor_nombres} ${guide.conductor_apellidos} · ${guide.vehiculo_placa}`
                                : guide.transportista_ruc}
                          </dd>
                        </div>
                      </dl>
                      {guide.modalidad_traslado === "01" &&
                        !guide.indicador_m1_l &&
                        !guide.registrar_vehiculo_transportista && (
                          <p className="ink-inline-alert ink-inline-alert-info">
                            El transportista deberá proporcionar su guía (GRE
                            31) antes de registrar la salida física.
                          </p>
                        )}
                    </>
                  )}
                  <p className="transfer-wizard__outcome">
                    {requiresGuide
                      ? "Al crear, prepararemos este viaje y guardaremos la guía como borrador. Luego podrás validarla y emitirla desde su detalle."
                      : "Al crear, quedarán preparadas las cantidades de este viaje."}{" "}
                    La salida física y la recepción se confirman después.
                  </p>
                  {checkpoint && !saving && (
                    <div
                      className="ink-inline-alert ink-inline-alert-info"
                      role="status"
                    >
                      {checkpoint.transfer
                        ? `El traslado TI-${checkpoint.transfer.id} ya está guardado. `
                        : ""}
                      Puedes retomar la creación sin volver a empezar.
                      {checkpoint.transfer && (
                        <Link
                          to={`/traslados-internos/${checkpoint.transfer.id}`}
                          onClick={() => sessionStorage.removeItem(progressKey)}
                        >
                          Continuar desde el traslado
                        </Link>
                      )}
                    </div>
                  )}
                </>
              )}
            </section>
            {error && (
              <p
                className="ink-inline-alert ink-inline-alert-danger"
                role="alert"
              >
                {error}
              </p>
            )}
            <div className="transfer-wizard__actions">
              {step === 0 ? (
                <Link className="btn" to="/traslados-internos">
                  Salir
                </Link>
              ) : (
                <button
                  className="btn"
                  type="button"
                  disabled={saving || Boolean(checkpoint)}
                  onClick={() => changeStep(step - 1)}
                >
                  <ArrowLeft size={16} />
                  Atrás
                </button>
              )}
              <span className="transfer-wizard__action-note" role="status">
                {saving
                  ? savingLabel
                  : step < 2
                    ? "Todavía no se guardará ningún cambio."
                    : "No se registrará la salida física."}
              </span>
              <button
                className="btn-primary"
                type="submit"
                disabled={saving || (step === 0 && !validGoods)}
              >
                {saving ? (
                  savingLabel
                ) : step < 2 ? (
                  <>
                    Continuar <ArrowRight size={16} />
                  </>
                ) : checkpoint ? (
                  "Retomar creación"
                ) : requiresGuide ? (
                  "Crear guía en borrador"
                ) : (
                  "Preparar viaje interno"
                )}
              </button>
            </div>
          </form>
        </>
      )}
    </div>
  );
}
