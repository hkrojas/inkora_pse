import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Building2,
  CheckCircle2,
  Link2,
  MapPin,
  Pencil,
  Plus,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";
import CustomSelect from "../components/ui/CustomSelect";
import Drawer from "../components/ui/Drawer";
import EmptyState from "../components/ui/EmptyState";
import Spinner from "../components/ui/Spinner";
import { PageError } from "../components/ui/PageState";
import { useToast } from "../components/ui/Toast";
import { internalTransfers } from "../services/internalTransfers";
import { inventory } from "../services/inventory";

const blank = {
  sunat_code: "",
  name: "",
  ubigeo: "",
  address: "",
  is_main: false,
  is_active: true,
};

export default function EstablishmentsPage() {
  const toast = useToast();
  const [rows, setRows] = useState([]);
  const [warehouses, setWarehouses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [drawer, setDrawer] = useState(null);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(blank);
  const [verifyNote, setVerifyNote] = useState("");
  const [warehouseId, setWarehouseId] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [establishments, warehouseRows] = await Promise.all([
        internalTransfers.establishments(true),
        inventory.warehouses(),
      ]);
      setRows(establishments);
      setWarehouses(warehouseRows);
    } catch (err) {
      setError(err.message || "No se pudieron cargar los establecimientos.");
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => {
    load();
  }, [load]);

  const warehouseByEstablishment = useMemo(
    () =>
      warehouses.reduce((map, row) => {
        if (row.establishment_id) (map[row.establishment_id] ||= []).push(row);
        return map;
      }, {}),
    [warehouses],
  );

  const openCreate = () => {
    setEditing(null);
    setForm(blank);
    setDrawer("edit");
  };
  const openEdit = (row) => {
    setEditing(row);
    setForm({ ...row });
    setDrawer("edit");
  };
  const submit = async (event) => {
    event.preventDefault();
    setSaving(true);
    try {
      if (editing)
        await internalTransfers.updateEstablishment(editing.id, form);
      else await internalTransfers.createEstablishment(form);
      toast(
        editing ? "Establecimiento actualizado." : "Establecimiento creado.",
        "success",
      );
      setDrawer(null);
      await load();
    } catch (err) {
      toast(err.message || "No se pudo guardar el establecimiento.", "error");
    } finally {
      setSaving(false);
    }
  };
  const verify = async (event) => {
    event.preventDefault();
    setSaving(true);
    try {
      await internalTransfers.verifyEstablishment(editing.id, verifyNote);
      toast("Datos fiscales verificados.", "success");
      setDrawer(null);
      await load();
    } catch (err) {
      toast(err.message || "No se pudo verificar el establecimiento.", "error");
    } finally {
      setSaving(false);
    }
  };
  const linkWarehouse = async (event) => {
    event.preventDefault();
    setSaving(true);
    try {
      const warehouse = warehouses.find(
        (row) => String(row.id) === String(warehouseId),
      );
      await inventory.updateWarehouse(warehouse.id, {
        name: warehouse.name,
        location: warehouse.location || "",
        is_default: warehouse.is_default,
        establishment_id: editing.id,
      });
      toast("Almacén vinculado al establecimiento.", "success");
      setDrawer(null);
      await load();
    } catch (err) {
      toast(err.message || "No se pudo vincular el almacén.", "error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="page-shell internal-transfer-page">
      <header className="page-header internal-transfer-hero">
        <div className="page-header-copy">
          <span className="internal-transfer-kicker">
            <Building2 size={15} /> Configuración fiscal
          </span>
          <h1 className="page-title">Establecimientos</h1>
          <p className="page-subtitle">
            Registra los locales declarados a SUNAT y vincula los almacenes que
            operan en cada uno.
          </p>
        </div>
        <div className="page-actions">
          <button className="btn" type="button" onClick={load}>
            <RefreshCw size={15} />
            Actualizar
          </button>
          <button className="btn-primary" type="button" onClick={openCreate}>
            <Plus size={15} />
            Nuevo establecimiento
          </button>
        </div>
      </header>
      {loading ? (
        <Spinner />
      ) : error ? (
        <PageError message={error} onRetry={load} />
      ) : rows.length === 0 ? (
        <EmptyState
          icon={<Building2 size={24} />}
          title="Configura tu primer establecimiento"
          description="Necesitas partida y llegada verificadas antes de emitir una GRE por traslado interno."
          actionLabel="Crear establecimiento"
          onAction={openCreate}
        />
      ) : (
        <div className="establishment-grid">
          {rows.map((row) => (
            <article
              className={`establishment-card ${row.verified_at ? "is-verified" : ""}`}
              key={row.id}
            >
              <div className="establishment-card__head">
                <span className="establishment-code">{row.sunat_code}</span>
                <span
                  className={`internal-transfer-status ${row.verified_at ? "is-completed" : "is-pending"}`}
                >
                  {row.verified_at ? "Verificado" : "Pendiente"}
                </span>
              </div>
              <h2>{row.name}</h2>
              <p>
                <MapPin size={14} />
                {row.address}
              </p>
              <small>
                Ubigeo {row.ubigeo}
                {row.is_main ? " · Principal" : ""}
              </small>
              <div className="establishment-card__warehouses">
                <strong>Almacenes vinculados</strong>
                <span>
                  {(warehouseByEstablishment[row.id] || [])
                    .map((item) => item.name)
                    .join(", ") || "Ninguno"}
                </span>
              </div>
              <div className="establishment-card__actions">
                <button
                  className="btn btn-sm"
                  type="button"
                  onClick={() => openEdit(row)}
                >
                  <Pencil size={14} />
                  Editar
                </button>
                <button
                  className="btn btn-sm"
                  type="button"
                  onClick={() => {
                    setEditing(row);
                    setVerifyNote(
                      "Datos contrastados con la ficha RUC y establecimientos anexos de SUNAT.",
                    );
                    setDrawer("verify");
                  }}
                >
                  <ShieldCheck size={14} />
                  Verificar
                </button>
                <button
                  className="btn btn-sm"
                  type="button"
                  onClick={() => {
                    setEditing(row);
                    setWarehouseId("");
                    setDrawer("link");
                  }}
                >
                  <Link2 size={14} />
                  Vincular almacén
                </button>
              </div>
            </article>
          ))}
        </div>
      )}

      <Drawer
        open={drawer === "edit"}
        onClose={() => setDrawer(null)}
        title={editing ? "Editar establecimiento" : "Nuevo establecimiento"}
        subtitle="Los datos deben coincidir con la información declarada a SUNAT."
        icon={<Building2 size={20} />}
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
              form="establishment-form"
              disabled={saving}
            >
              {saving ? "Guardando…" : "Guardar"}
            </button>
          </>
        }
      >
        <form
          id="establishment-form"
          className="internal-transfer-form"
          onSubmit={submit}
        >
          <div className="internal-transfer-form-grid">
            <label>
              Código SUNAT
              <input
                className="input mt-1"
                required
                pattern="[0-9]{4}"
                maxLength={4}
                value={form.sunat_code}
                onChange={(e) =>
                  setForm({
                    ...form,
                    sunat_code: e.target.value.replace(/\D/g, ""),
                  })
                }
                placeholder="0000"
              />
            </label>
            <label>
              Nombre
              <input
                className="input mt-1"
                required
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            </label>
          </div>
          <label>
            Ubigeo
            <input
              className="input mt-1"
              required
              pattern="[0-9]{6}"
              maxLength={6}
              value={form.ubigeo}
              onChange={(e) =>
                setForm({ ...form, ubigeo: e.target.value.replace(/\D/g, "") })
              }
            />
          </label>
          <label>
            Dirección completa
            <textarea
              className="input mt-1 min-h-24"
              required
              value={form.address}
              onChange={(e) => setForm({ ...form, address: e.target.value })}
            />
          </label>
          <label className="internal-transfer-check">
            <input
              type="checkbox"
              checked={form.is_main}
              onChange={(e) => setForm({ ...form, is_main: e.target.checked })}
            />
            <span>
              <strong>Establecimiento principal</strong>
              <small>Usa el código 0000 solo si corresponde en SUNAT.</small>
            </span>
          </label>
          {editing && (
            <label className="internal-transfer-check">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(e) =>
                  setForm({ ...form, is_active: e.target.checked })
                }
              />
              <span>
                <strong>Disponible para nuevos traslados</strong>
              </span>
            </label>
          )}
        </form>
      </Drawer>
      <Drawer
        open={drawer === "verify"}
        onClose={() => setDrawer(null)}
        title="Verificar datos fiscales"
        subtitle={editing?.name || ""}
        icon={<CheckCircle2 size={20} />}
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
              form="verify-establishment"
              disabled={saving}
            >
              Confirmar verificación
            </button>
          </>
        }
      >
        <form
          id="verify-establishment"
          className="internal-transfer-form"
          onSubmit={verify}
        >
          <p className="internal-transfer-note">
            Esta acción deja constancia del usuario y la fecha. No modifica los
            registros de SUNAT.
          </p>
          <label>
            Evidencia o criterio de verificación
            <textarea
              className="input mt-1 min-h-28"
              required
              minLength={10}
              value={verifyNote}
              onChange={(e) => setVerifyNote(e.target.value)}
            />
          </label>
        </form>
      </Drawer>
      <Drawer
        open={drawer === "link"}
        onClose={() => setDrawer(null)}
        title="Vincular almacén"
        subtitle={editing?.name || ""}
        icon={<Link2 size={20} />}
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
              form="link-warehouse"
              disabled={saving || !warehouseId}
            >
              Vincular
            </button>
          </>
        }
      >
        <form
          id="link-warehouse"
          className="internal-transfer-form"
          onSubmit={linkWarehouse}
        >
          <label>
            Almacén
            <CustomSelect
              required
              value={warehouseId}
              onChange={setWarehouseId}
              ariaLabel="Almacén"
              placeholder="Selecciona un almacén"
              options={warehouses.map((row) => ({
                value: row.id,
                label: `${row.name} · ${row.code}`,
              }))}
            />
          </label>
          <p className="internal-transfer-note">
            Varias ubicaciones internas pueden pertenecer al mismo
            establecimiento.
          </p>
        </form>
      </Drawer>
    </div>
  );
}
