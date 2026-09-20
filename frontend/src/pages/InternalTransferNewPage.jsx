import { useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  ArrowRightLeft,
  Boxes,
  PackagePlus,
  Plus,
  Search,
  Trash2,
} from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import CustomSelect from "../components/ui/CustomSelect";
import Spinner from "../components/ui/Spinner";
import { useToast } from "../components/ui/Toast";
import { internalTransfers } from "../services/internalTransfers";
import { inventory } from "../services/inventory";
import { productos } from "../services/productos";

const newManualLine = () => ({
  key: crypto.randomUUID(),
  product_id: null,
  description: "",
  product_code: "",
  unit_code: "NIU",
  quantity: "1",
  manual_goods_confirmed: true,
});

export default function InternalTransferNewPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [establishments, setEstablishments] = useState([]);
  const [warehouses, setWarehouses] = useState([]);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [form, setForm] = useState({
    source_establishment_id: "",
    destination_establishment_id: "",
    source_warehouse_id: "",
    destination_warehouse_id: "",
    reason: "",
  });
  const [lines, setLines] = useState([]);

  useEffect(() => {
    Promise.all([internalTransfers.establishments(), inventory.warehouses()])
      .then(([establishmentRows, warehouseRows]) => {
        setEstablishments(establishmentRows);
        setWarehouses(warehouseRows);
      })
      .catch((err) =>
        toast(err.message || "No se pudo preparar el formulario.", "error"),
      )
      .finally(() => setLoading(false));
  }, [toast]);

  useEffect(() => {
    const term = query.trim();
    if (term.length < 2) {
      setResults([]);
      return undefined;
    }
    let active = true;
    const controller = new AbortController();
    setSearching(true);
    const timer = window.setTimeout(
      () =>
        productos
          .search(term, 12, { signal: controller.signal })
          .then((rows) => {
            if (active) setResults(rows);
          })
          .catch(() => {
            if (active) setResults([]);
          })
          .finally(() => {
            if (active) setSearching(false);
          }),
      250,
    );
    return () => {
      active = false;
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [query]);

  const verified = establishments.filter(
    (row) => row.is_active && row.verified_at,
  );
  const sourceWarehouses = useMemo(
    () =>
      warehouses.filter(
        (row) =>
          String(row.establishment_id) === String(form.source_establishment_id),
      ),
    [form.source_establishment_id, warehouses],
  );
  const destinationWarehouses = useMemo(
    () =>
      warehouses.filter(
        (row) =>
          String(row.establishment_id) ===
          String(form.destination_establishment_id),
      ),
    [form.destination_establishment_id, warehouses],
  );
  const canSubmit = Boolean(
    form.source_establishment_id &&
      form.destination_establishment_id &&
      form.reason.trim().length >= 3 &&
      lines.length &&
      lines.every(
        (line) =>
          Number(line.quantity) > 0 &&
          String(line.unit_code || "").trim() &&
          (line.product_id || String(line.description || "").trim()),
      ),
  );
  const addProduct = (product) => {
    if (lines.some((line) => Number(line.product_id) === Number(product.id))) {
      toast("Ese producto ya está incluido.", "warning");
      return;
    }
    setLines((current) => [
      ...current,
      {
        key: crypto.randomUUID(),
        product_id: product.id,
        description: product.nombre,
        product_code: product.codigo_interno || "",
        unit_code: product.unidad_medida || "NIU",
        quantity: "1",
        manual_goods_confirmed: false,
      },
    ]);
    setQuery("");
    setResults([]);
  };
  const updateLine = (key, patch) =>
    setLines((current) =>
      current.map((line) => (line.key === key ? { ...line, ...patch } : line)),
    );
  const submit = async (event) => {
    event.preventDefault();
    if (!lines.length) {
      toast("Agrega al menos un bien.", "error");
      return;
    }
    setSaving(true);
    try {
      const data = await internalTransfers.create({
        ...form,
        source_establishment_id: Number(form.source_establishment_id),
        destination_establishment_id: Number(form.destination_establishment_id),
        source_warehouse_id: form.source_warehouse_id
          ? Number(form.source_warehouse_id)
          : null,
        destination_warehouse_id: form.destination_warehouse_id
          ? Number(form.destination_warehouse_id)
          : null,
        idempotency_key: crypto.randomUUID(),
        lines: lines.map(({ key: _key, ...line }) => ({
          ...line,
          quantity: Number(line.quantity),
        })),
      });
      toast(
        "Traslado creado. Ahora puedes preparar el primer despacho.",
        "success",
      );
      navigate(`/traslados-internos/${data.id}`);
    } catch (err) {
      toast(err.message || "No se pudo crear el traslado.", "error");
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
  return (
    <div className="page-shell internal-transfer-page max-w-6xl">
      <header className="page-header internal-transfer-hero">
        <div className="page-header-copy">
          <Link className="internal-transfer-back" to="/traslados-internos">
            <ArrowLeft size={15} />
            Traslados
          </Link>
          <h1 className="page-title">Nuevo traslado interno</h1>
          <p className="page-subtitle">
            Define la solicitud completa. Las existencias se reservarán recién
            al crear cada despacho.
          </p>
        </div>
      </header>
      {verified.length < 1 ? (
        <section className="internal-transfer-card internal-transfer-blocker">
          <Boxes size={22} />
          <div>
            <h2>Completa la configuración fiscal</h2>
            <p>Necesitas al menos un establecimiento activo y verificado.</p>
          </div>
          <Link className="btn-primary" to="/inventario/establecimientos">
            Configurar establecimientos
          </Link>
        </section>
      ) : (
        <form className="internal-transfer-workflow" onSubmit={submit}>
          <section className="internal-transfer-card">
            <div className="internal-transfer-section-title">
              <span>01</span>
              <div>
                <h2>Ruta del traslado</h2>
                <p>
                  Elige establecimientos verificados y, si controlas stock, sus
                  almacenes.
                </p>
              </div>
            </div>
            <div className="internal-transfer-route-grid">
              <div>
                <label>Establecimiento de partida</label>
                <CustomSelect
                  required
                  ariaLabel="Establecimiento de partida"
                  value={form.source_establishment_id}
                  onChange={(value) =>
                    setForm({
                      ...form,
                      source_establishment_id: value,
                      source_warehouse_id: "",
                    })
                  }
                  options={verified.map((row) => ({
                    value: row.id,
                    label: `${row.sunat_code} · ${row.name}`,
                  }))}
                />
              </div>
              <ArrowRight className="internal-transfer-route-arrow" />
              <div>
                <label>Establecimiento de llegada</label>
                <CustomSelect
                  required
                  ariaLabel="Establecimiento de llegada"
                  value={form.destination_establishment_id}
                  onChange={(value) =>
                    setForm({
                      ...form,
                      destination_establishment_id: value,
                      destination_warehouse_id: "",
                    })
                  }
                  options={verified.map((row) => ({
                    value: row.id,
                    label: `${row.sunat_code} · ${row.name}`,
                  }))}
                />
              </div>
            </div>
            <div className="internal-transfer-form-grid">
              <div>
                <label>
                  Almacén de origen <small>(si controla stock)</small>
                </label>
                <CustomSelect
                  ariaLabel="Almacén de origen"
                  value={form.source_warehouse_id}
                  onChange={(value) =>
                    setForm({ ...form, source_warehouse_id: value })
                  }
                  placeholder="Sin almacén"
                  options={sourceWarehouses.map((row) => ({
                    value: row.id,
                    label: row.name,
                  }))}
                />
              </div>
              <div>
                <label>
                  Almacén de destino <small>(si controla stock)</small>
                </label>
                <CustomSelect
                  ariaLabel="Almacén de destino"
                  value={form.destination_warehouse_id}
                  onChange={(value) =>
                    setForm({ ...form, destination_warehouse_id: value })
                  }
                  placeholder="Sin almacén"
                  options={destinationWarehouses.map((row) => ({
                    value: row.id,
                    label: row.name,
                  }))}
                />
              </div>
            </div>
            <label>
              Motivo operativo
              <textarea
                className="input mt-1 min-h-24"
                required
                minLength={3}
                value={form.reason}
                onChange={(e) => setForm({ ...form, reason: e.target.value })}
                placeholder="Ej. Reposición de existencias en tienda secundaria"
              />
            </label>
            {form.source_establishment_id &&
              form.source_establishment_id ===
                form.destination_establishment_id && (
                <p className="internal-transfer-note">
                  El origen y destino pertenecen al mismo establecimiento.
                  Inkora registrará el movimiento interno sin GRE si la
                  dirección también coincide.
                </p>
              )}
          </section>
          <section className="internal-transfer-card">
            <div className="internal-transfer-section-title">
              <span>02</span>
              <div>
                <h2>Bienes solicitados</h2>
                <p>
                  Puedes agregar productos del catálogo o bienes manuales sin
                  control de existencias.
                </p>
              </div>
            </div>
            <div className="internal-transfer-product-search">
              <Search size={16} />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Buscar producto por nombre o código"
              />
              {searching && <span>Buscando…</span>}
            </div>
            {results.length > 0 && (
              <div className="internal-transfer-search-results">
                {results.map((product) => (
                  <button
                    type="button"
                    key={product.id}
                    onClick={() => addProduct(product)}
                  >
                    <PackagePlus size={15} />
                    <span>
                      <strong>{product.nombre}</strong>
                      <small>{product.codigo_interno || "Sin código"}</small>
                    </span>
                    <Plus size={15} />
                  </button>
                ))}
              </div>
            )}
            <div className="ink-table-scroll">
              <table className="ink-table">
                <thead>
                  <tr>
                    <th>Bien</th>
                    <th>Código</th>
                    <th>Unidad</th>
                    <th>Cantidad</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {lines.map((line) => (
                    <tr key={line.key}>
                      <td>
                        {line.product_id ? (
                          <>
                            <strong>{line.description}</strong>
                            <div className="ink-table-cell__meta">
                              Producto del catálogo
                            </div>
                          </>
                        ) : (
                          <input
                            className="input"
                            required
                            value={line.description}
                            onChange={(e) =>
                              updateLine(line.key, {
                                description: e.target.value,
                              })
                            }
                            placeholder="Descripción del bien"
                          />
                        )}
                      </td>
                      <td>
                        <input
                          className="input"
                          value={line.product_code}
                          onChange={(e) =>
                            updateLine(line.key, {
                              product_code: e.target.value,
                            })
                          }
                          disabled={Boolean(line.product_id)}
                        />
                      </td>
                      <td>
                        <input
                          className="input internal-transfer-unit"
                          maxLength={3}
                          required
                          value={line.unit_code}
                          onChange={(e) =>
                            updateLine(line.key, {
                              unit_code: e.target.value.toUpperCase(),
                            })
                          }
                        />
                      </td>
                      <td>
                        <input
                          className="input internal-transfer-quantity"
                          required
                          type="number"
                          min="0.0001"
                          step="0.0001"
                          value={line.quantity}
                          onChange={(e) =>
                            updateLine(line.key, { quantity: e.target.value })
                          }
                        />
                      </td>
                      <td>
                        <button
                          type="button"
                          className="ink-row-btn"
                          onClick={() =>
                            setLines((current) =>
                              current.filter((item) => item.key !== line.key),
                            )
                          }
                          aria-label="Quitar bien"
                        >
                          <Trash2 size={15} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {lines.length === 0 && (
              <div className="internal-transfer-inline-empty">
                <Boxes size={20} />
                <span>Busca un producto o agrega un bien manual.</span>
              </div>
            )}
            <button
              className="btn"
              type="button"
              onClick={() =>
                setLines((current) => [...current, newManualLine()])
              }
            >
              <Plus size={15} />
              Agregar bien manual
            </button>
          </section>
          <div className="internal-transfer-submit">
            <Link className="btn" to="/traslados-internos">
              Cancelar
            </Link>
            <button
              className="btn-primary"
              type="submit"
              disabled={saving || !canSubmit}
            >
              {saving ? (
                "Creando…"
              ) : (
                <>
                  <ArrowRightLeft size={16} />
                  Crear traslado
                </>
              )}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
