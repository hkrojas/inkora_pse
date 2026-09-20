import { useMemo, useState } from 'react';
import { AlertTriangle, Hash } from 'lucide-react';
import Drawer from '../ui/Drawer';
import { useToast } from '../ui/Toast';
import { superadmin as svc } from '../../services/superadmin';

const DOCUMENTS = [
  {
    key: 'invoice',
    title: 'Facturas',
    description: 'Comprobantes de venta tipo 01.',
    seriesField: 'fiscal_invoice_series',
    floorField: 'fiscal_invoice_series_floor',
    prefix: 'F',
    placeholder: 'FA01',
  },
  {
    key: 'receipt',
    title: 'Boletas de venta',
    description: 'Comprobantes de venta tipo 03.',
    seriesField: 'fiscal_boleta_series',
    floorField: 'fiscal_boleta_series_floor',
    prefix: 'B',
    placeholder: 'BA01',
  },
  {
    key: 'gre-sender',
    title: 'Guías del remitente',
    description: 'Guías de remisión tipo 09.',
    seriesField: 'fiscal_gre_remitente_series',
    floorField: 'fiscal_gre_remitente_series_floor',
    prefix: 'T',
    placeholder: 'TI01',
  },
  {
    key: 'gre-carrier',
    title: 'Guías del transportista',
    description: 'Guías de remisión tipo 31.',
    seriesField: 'fiscal_gre_transportista_series',
    floorField: 'fiscal_gre_transportista_series_floor',
    prefix: 'V',
    placeholder: 'VI01',
  },
];

function initialForm(tenant) {
  return DOCUMENTS.reduce((form, document) => ({
    ...form,
    [document.seriesField]: tenant?.[document.seriesField]
      || (document.key.startsWith('gre-') ? document.placeholder : ''),
    [document.floorField]: String(tenant?.[document.floorField] ?? 0),
  }), { confirmed: false });
}

function validate(form) {
  for (const document of DOCUMENTS) {
    const series = form[document.seriesField];
    const floor = Number(form[document.floorField]);
    if (!new RegExp(`^${document.prefix}[A-Z0-9]{3}$`).test(series)) {
      return `${document.title}: la serie debe tener cuatro caracteres y comenzar con ${document.prefix}.`;
    }
    if (!Number.isInteger(floor) || floor < 0 || floor > 99999999) {
      return `${document.title}: indica un último número válido.`;
    }
  }
  if (!form.confirmed) return 'Confirma que revisaste las series y los últimos números utilizados.';
  return null;
}

export default function TenantFiscalSeriesDrawer({ tenant, onClose, onSaved }) {
  const toast = useToast();
  const [form, setForm] = useState(() => initialForm(tenant));
  const [saving, setSaving] = useState(false);
  const error = useMemo(() => validate(form), [form]);

  const setField = (field, value) => {
    setForm((current) => ({
      ...current,
      [field]: field.includes('series')
        ? value.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 4)
        : value,
    }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (error) {
      toast(error, 'error');
      return;
    }
    setSaving(true);
    try {
      const payload = DOCUMENTS.reduce((values, document) => ({
        ...values,
        [document.seriesField]: form[document.seriesField],
        [document.floorField]: Number(form[document.floorField]),
      }), { confirmed: true });
      const updated = await svc.updateFiscalSeries(tenant.id, payload);
      onSaved(updated);
      toast('Series y numeración actualizadas.');
      onClose();
    } catch (requestError) {
      toast(requestError.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Drawer
      open={Boolean(tenant)}
      onClose={onClose}
      title="Series y numeración"
      subtitle={tenant.business_name}
      eyebrow="Configuración fiscal"
      icon={<Hash size={18} />}
      size="wide"
      initialFocus="[data-series-first]"
      footerClassName="fiscal-series-footer"
      footer={(
        <>
          <button type="button" className="btn-secondary" onClick={onClose} disabled={saving}>
            Cancelar
          </button>
          <button type="submit" form="tenant-fiscal-series-form" className="btn" disabled={saving || Boolean(error)}>
            {saving ? 'Guardando…' : 'Guardar cambios'}
          </button>
        </>
      )}
    >
      <form id="tenant-fiscal-series-form" className="fiscal-series-form" onSubmit={handleSubmit}>
        <div className="drawer-editor-callout drawer-editor-callout--warning">
          <AlertTriangle size={18} aria-hidden="true" />
          <div>
            <strong>Revisa estos datos antes de guardar</strong>
            <small>
              El último número es el correlativo más reciente ya utilizado. Inkora comenzará con el siguiente
              y nunca cambiará documentos emitidos anteriormente.
            </small>
          </div>
        </div>

        <div className="fiscal-series-grid">
          {DOCUMENTS.map((document, index) => {
            const floor = Number(form[document.floorField]);
            const next = Number.isInteger(floor) && floor >= 0 ? floor + 1 : 1;
            return (
              <section key={document.key} className="fiscal-series-card">
                <div className="fiscal-series-card__head">
                  <div>
                    <h4>{document.title}</h4>
                    <p>{document.description}</p>
                  </div>
                  <span className="fiscal-series-preview">
                    {form[document.seriesField] || document.placeholder}-{String(next).padStart(8, '0')}
                  </span>
                </div>
                <div className="fiscal-series-fields">
                  <label>
                    <span>Serie</span>
                    <input
                      data-series-first={index === 0 ? 'true' : undefined}
                      value={form[document.seriesField]}
                      onChange={(event) => setField(document.seriesField, event.target.value)}
                      placeholder={document.placeholder}
                      maxLength={4}
                      autoComplete="off"
                      aria-describedby={`${document.key}-series-help`}
                    />
                    <small id={`${document.key}-series-help`}>Cuatro caracteres; debe comenzar con {document.prefix}.</small>
                  </label>
                  <label>
                    <span>Último número utilizado</span>
                    <input
                      type="number"
                      min="0"
                      max="99999999"
                      step="1"
                      inputMode="numeric"
                      value={form[document.floorField]}
                      onChange={(event) => setField(document.floorField, event.target.value)}
                    />
                    <small>Usa 0 si la serie todavía no tiene documentos.</small>
                  </label>
                </div>
              </section>
            );
          })}
        </div>

        <div className="fiscal-series-demo-note">
          <strong>En modo demo</strong>
          <span>Las guías usan T999 y V999. Estas series productivas no se consumen durante las pruebas.</span>
        </div>

        <label className="fiscal-series-confirmation">
          <input
            type="checkbox"
            checked={form.confirmed}
            onChange={(event) => setForm((current) => ({ ...current, confirmed: event.target.checked }))}
          />
          <span>Confirmo que revisé estas series y números en SUNAT o Smart PSE.</span>
        </label>
        {error ? <p className="fiscal-series-error" role="status">{error}</p> : null}
      </form>
    </Drawer>
  );
}
