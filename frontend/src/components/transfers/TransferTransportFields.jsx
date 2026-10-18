import CustomSelect from "../ui/CustomSelect";

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
  const set = (patch) => onChange({ ...value, ...patch });
  const publicTransport = value.modalidad_traslado === "01";
  const driverRequired =
    !value.indicador_m1_l &&
    (!publicTransport || value.registrar_vehiculo_transportista);
  const field = (key, label, props = {}) => (
    <label className="transfer-wizard__field" key={key}>
      <span>{label}</span>
      <input
        className="input"
        required
        value={value[key]}
        onChange={(event) => set({ [key]: event.target.value })}
        {...props}
      />
    </label>
  );
  return (
    <div className="transfer-wizard__transport">
      <div className="transfer-wizard__grid">
        {field("fecha_traslado", "Fecha y hora de salida", {
          type: "datetime-local",
        })}
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
          {field(
            "fecha_entrega_transportista",
            "Fecha y hora de entrega al transportista",
            { type: "datetime-local" },
          )}
          {!value.indicador_m1_l && (
            <>
              <div className="transfer-wizard__grid">
                {field("transportista_ruc", "RUC del transportista", {
                  inputMode: "numeric",
                  pattern: "[0-9]{11}",
                  maxLength: 11,
                })}
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
            )}
            {field("conductor_nombres", "Nombres del conductor")}
            {field("conductor_apellidos", "Apellidos del conductor")}
            {field("conductor_licencia", "Licencia de conducir")}
          </div>
        </>
      )}
      {(!publicTransport ||
        value.indicador_m1_l ||
        value.registrar_vehiculo_transportista) &&
        field("vehiculo_placa", "Placa del vehículo", { maxLength: 10 })}
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
