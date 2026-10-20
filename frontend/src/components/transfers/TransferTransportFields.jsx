import { cloneElement, useEffect, useId, useRef, useState } from "react";
import CustomSelect from "../ui/CustomSelect";
import DatePicker from "../ui/DatePicker";
import GuideLookup, { GuideQueryControl } from "../guides/GuideLookup";
import { clientes } from "../../services/clientes";

function TransportDateTime({ value, onChange, label, dateLabel, timeLabel }) {
  const [date = "", time = ""] = value.split("T");
  return (
    <fieldset className="transfer-wizard__field min-w-0">
      <legend>{label}</legend>
      <div className="grid grid-cols-[minmax(0,1fr)_116px] gap-3 mt-2">
        <DatePicker value={date} onChange={(next) => onChange(`${next}T${time}`)}
          min={new Date().toLocaleDateString("en-CA", { timeZone: "America/Lima" })}
          required ariaLabel={dateLabel} />
        <input className="input" type="time" required aria-label={timeLabel}
          value={time} onChange={(event) => onChange(`${date}T${event.target.value}`)} />
      </div>
    </fieldset>
  );
}

export const newTransferTransport = () => ({
  fecha_traslado: "",
  peso_bruto_total: "",
  unidad_medida_peso: "KGM",
  numero_bultos: "",
  modalidad_traslado: "02",
  fecha_entrega_transportista: "",
  indicador_m1_l: false,
  registrar_vehiculo_transportista: false,
  transportista_acuerdo_confirmado: false,
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
  observaciones: "",
});

// Send only fields belonging to the chosen transport scenario.
export function transferTransportPayload(guide) {
  const payload = {
    ...guide,
    fecha_traslado: new Date(guide.fecha_traslado).toISOString(),
    peso_bruto_total: Number(guide.peso_bruto_total),
    numero_bultos: guide.numero_bultos ? Number(guide.numero_bultos) : null,
  };
  const publicTransport = guide.modalidad_traslado === "01";
  payload.fecha_entrega_transportista =
    publicTransport && guide.fecha_entrega_transportista
      ? new Date(guide.fecha_entrega_transportista).toISOString()
      : null;
  if (!publicTransport || guide.indicador_m1_l) {
    for (const key of [
      "transportista_ruc",
      "transportista_razon_social",
      "transportista_nro_mtc",
    ])
      payload[key] = null;
  }
  if (
    guide.indicador_m1_l ||
    (publicTransport && !guide.registrar_vehiculo_transportista)
  ) {
    for (const key of [
      "conductor_tipo_doc",
      "conductor_nro_doc",
      "conductor_nombres",
      "conductor_apellidos",
      "conductor_licencia",
    ])
      payload[key] = null;
  }
  if (
    publicTransport &&
    !guide.indicador_m1_l &&
    !guide.registrar_vehiculo_transportista
  )
    payload.vehiculo_placa = null;
  if (!publicTransport || !guide.registrar_vehiculo_transportista) {
    payload.vehiculo_nro_circulacion = null;
    payload.transportista_acuerdo_confirmado = false;
  }
  for (const key of Object.keys(payload))
    if (payload[key] === "") payload[key] = null;
  return payload;
}

export default function TransferTransportFields({ value, onChange }) {
  const latest = useRef(value);
  latest.current = value;
  const lookupSequence = useRef(0);
  const [lookup, setLookup] = useState({ busy: false, message: "", error: false });
  const applyLookup = (update) => onChange(update(latest.current));
  const set = (patch) => onChange({ ...value, ...patch });
  const publicTransport = value.modalidad_traslado === "01";
  const driverRequired =
    !value.indicador_m1_l &&
    (!publicTransport || value.registrar_vehiculo_transportista);
  useEffect(() => {
    setLookup({ busy: false, message: "", error: false });
    return () => { lookupSequence.current += 1; };
  }, [value.conductor_nro_doc, value.conductor_tipo_doc, driverRequired]);
  const lookupDriver = async () => {
    const before = latest.current;
    const number = before.conductor_nro_doc.trim();
    if (lookup.busy || before.conductor_tipo_doc !== "1" || !/^\d{8}$/.test(number)) return;
    const sequence = ++lookupSequence.current;
    setLookup({ busy: true, message: "Consultando DNI…", error: false });
    try {
      const data = await clientes.lookupDocument(number);
      if (sequence !== lookupSequence.current) return;
      const current = latest.current;
      if (current.conductor_nro_doc.trim() !== number || current.conductor_tipo_doc !== "1") return;
      if (current.conductor_nombres !== before.conductor_nombres || current.conductor_apellidos !== before.conductor_apellidos)
        throw new Error("Los nombres cambiaron durante la consulta. Consúltalo otra vez si deseas reemplazarlos.");
      const surnames = [data.apellido_paterno, data.apellido_materno].filter(Boolean).join(" ");
      if (!data.nombres || !surnames || (data.documento && data.documento !== number))
        throw new Error("La consulta no devolvió los nombres completos. Puedes ingresarlos manualmente.");
      onChange({ ...current, conductor_nombres: data.nombres, conductor_apellidos: surnames });
      setLookup({ busy: false, message: "Nombres y apellidos completados. Revisa los datos del conductor.", error: false });
    } catch (error) {
      if (sequence === lookupSequence.current)
        setLookup({ busy: false, message: error.message || "No se pudo consultar el DNI. Puedes ingresar los datos manualmente.", error: true });
    }
  };
  const fieldPrefix = useId();
  const field = (key, label, props = {}, queryControl) => {
    const input = <input
        id={`${fieldPrefix}-${key}`}
        className="input"
        required
        value={value[key]}
        onChange={(event) => set({ [key]: key === "vehiculo_placa" ? event.target.value.toUpperCase().replace(/[-\s]/g, "") : event.target.value })}
        {...props}
      />;
    return <div className="transfer-wizard__field" key={key}>
      <label htmlFor={`${fieldPrefix}-${key}`}>{label}</label>
      {queryControl ? cloneElement(queryControl, { children: input }) : input}
    </div>;
  };
  return (
    <div className="transfer-wizard__transport">
      <div className="transfer-wizard__grid">
        <TransportDateTime value={value.fecha_traslado} onChange={(next) => set({ fecha_traslado: next })}
          label="Fecha y hora de salida" dateLabel="Fecha de salida" timeLabel="Hora de salida" />
        {field(
          "peso_bruto_total",
          `Peso total (${value.unidad_medida_peso === "KGM" ? "kg" : "toneladas"})`,
          { type: "number", min: "0.001", step: "0.001" },
        )}
      </div>
      <fieldset className="transfer-wizard__choices">
        <legend>¿Quién llevará los bienes?</legend>
        {[
          ["02", "Nosotros", "Nos encargamos del vehículo y el conductor."],
          [
            "01",
            "Una empresa de transporte",
            "El transportista realiza el servicio.",
          ],
        ].map(([code, title, description]) => (
          <label
            key={code}
            className={value.modalidad_traslado === code ? "is-selected" : ""}
          >
            <input
              type="radio"
              name="transport-mode"
              value={code}
              checked={value.modalidad_traslado === code}
              onChange={() =>
                set({
                  modalidad_traslado: code,
                  indicador_m1_l: false,
                  registrar_vehiculo_transportista: false,
                  transportista_acuerdo_confirmado: false,
                })
              }
            />
            <span>
              <strong>{title}</strong>
              <small>{description}</small>
            </span>
          </label>
        ))}
      </fieldset>
      <details className="transfer-wizard__options">
        <summary>Opciones del transporte</summary>
        <label className="transfer-wizard__check">
          <input
            type="checkbox"
            checked={value.indicador_m1_l}
            onChange={(event) =>
              set({
                indicador_m1_l: event.target.checked,
                registrar_vehiculo_transportista: false,
                transportista_acuerdo_confirmado: false,
              })
            }
          />
          <span>
            Usar la excepción para vehículo M1 o L
            <small>
              Solo si la categoría de la tarjeta vehicular lo permite. Se pide
              la placa y no los datos del conductor.
            </small>
          </span>
        </label>
        {publicTransport && !value.indicador_m1_l && (
          <label className="transfer-wizard__check">
            <input
              type="checkbox"
              checked={value.registrar_vehiculo_transportista}
              onChange={(event) =>
                set({
                  registrar_vehiculo_transportista: event.target.checked,
                  transportista_acuerdo_confirmado: false,
                })
              }
            />
            <span>
              Registrar también el vehículo y conductor del transportista
              <small>
                Necesitas su número de circulación y confirmar el acuerdo.
              </small>
            </span>
          </label>
        )}
      </details>
      {publicTransport && (
        <>
          <TransportDateTime value={value.fecha_entrega_transportista}
            onChange={(next) => set({ fecha_entrega_transportista: next })}
            label="Fecha y hora de entrega al transportista"
            dateLabel="Fecha de entrega al transportista" timeLabel="Hora de entrega al transportista" />
          {!value.indicador_m1_l && (
            <>
              <div className="transfer-wizard__grid">
                {field("transportista_ruc", "RUC del transportista", {
                  inputMode: "numeric",
                  pattern: "[0-9]{11}",
                  maxLength: 11,
                }, <GuideLookup kind="RUC" form={value} setForm={applyLookup} source="transportista_ruc" targets={{ transportista_razon_social: 'razon_social' }} />)}
                {field(
                  "transportista_nro_mtc",
                  "Registro MTC del transportista",
                )}
              </div>
              {field(
                "transportista_razon_social",
                "Nombre o razón social del transportista",
              )}
              {!value.registrar_vehiculo_transportista && (
                <p className="ink-inline-alert ink-inline-alert-info">
                  Antes de confirmar la salida necesitarás vincular la guía del
                  transportista (GRE 31).
                </p>
              )}
            </>
          )}
        </>
      )}
      {driverRequired && (
        <>
          <h3>Conductor y vehículo</h3>
          <div className="transfer-wizard__grid">
            <div className="transfer-wizard__field">
              <span>Documento del conductor</span>
              <CustomSelect
                ariaLabel="Documento del conductor"
                value={value.conductor_tipo_doc}
                onChange={(code) =>
                  set({ conductor_tipo_doc: code, conductor_nro_doc: "" })
                }
                options={[
                  { value: "1", label: "DNI" },
                  { value: "4", label: "Carné de extranjería" },
                  { value: "7", label: "Pasaporte" },
                  { value: "0", label: "Otro documento" },
                ]}
              />
            </div>
            {field(
              "conductor_nro_doc",
              "Número de documento",
              value.conductor_tipo_doc === "1"
                ? { inputMode: "numeric", pattern: "[0-9]{8}", maxLength: 8 }
                : {},
              value.conductor_tipo_doc === "1" && <GuideQueryControl kind="DNI" busy={lookup.busy}
                disabled={!/^\d{8}$/.test(value.conductor_nro_doc.trim())} onQuery={lookupDriver}
                message={lookup.message} error={lookup.error} alertOnError />,
            )}
            {field("conductor_nombres", "Nombres del conductor")}
            {field("conductor_apellidos", "Apellidos del conductor")}
            {field("conductor_licencia", "Licencia de conducir", {}, value.conductor_tipo_doc === "1" && <GuideLookup kind="licencia" form={value} setForm={applyLookup} source="conductor_nro_doc" identityType={value.conductor_tipo_doc} targets={{ conductor_licencia: 'numero' }} />)}
          </div>
        </>
      )}
      {(!publicTransport ||
        value.indicador_m1_l ||
        value.registrar_vehiculo_transportista) &&
        field("vehiculo_placa", "Placa del vehículo", { maxLength: 10 }, <GuideLookup kind="placa" form={value} setForm={applyLookup} source="vehiculo_placa" />)}
      {publicTransport && value.registrar_vehiculo_transportista && (
        <>
          {field(
            "vehiculo_nro_circulacion",
            "Número de circulación del vehículo",
          )}
          <label className="transfer-wizard__check">
            <input
              type="checkbox"
              required
              checked={value.transportista_acuerdo_confirmado}
              onChange={(event) =>
                set({ transportista_acuerdo_confirmado: event.target.checked })
              }
            />
            <span>
              Confirmo el acuerdo con el transportista para registrar su
              vehículo y conductor.
            </span>
          </label>
        </>
      )}
      <details className="transfer-wizard__options">
        <summary>Bultos, unidad de peso y observaciones (opcional)</summary>
        <div className="transfer-wizard__grid">
          {field("numero_bultos", "Número de bultos", {
            type: "number",
            min: "1",
            step: "1",
            required: false,
          })}
          <div className="transfer-wizard__field">
            <span>Unidad de peso</span>
            <CustomSelect
              ariaLabel="Unidad de peso"
              value={value.unidad_medida_peso}
              onChange={(code) => set({ unidad_medida_peso: code })}
              options={[
                { value: "KGM", label: "Kilogramos" },
                { value: "TNE", label: "Toneladas" },
              ]}
            />
          </div>
        </div>
        <label className="transfer-wizard__field">
          <span>Observaciones</span>
          <textarea
            className="input"
            maxLength={500}
            value={value.observaciones}
            onChange={(event) => set({ observaciones: event.target.value })}
          />
        </label>
      </details>
    </div>
  );
}
