import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, MapPin, Package, Truck } from 'lucide-react';
import { guias as svc } from '../services/guias';
import Spinner from '../components/ui/Spinner';
import Badge, { statusBadge } from '../components/ui/Badge';
import { useToast } from '../components/ui/Toast';

const MOTIVO_LABEL = {
  '01': 'Venta',
  '02': 'Compra',
  '04': 'Traslado entre establecimientos',
  '13': 'Otros',
};

const MODALIDAD_LABEL = {
  '01': 'Transporte publico',
  '02': 'Transporte privado',
};

export default function GuiaDetalle() {
  const { id } = useParams();
  const toast = useToast();
  const [guia, setGuia] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    svc.get(id)
      .then(setGuia)
      .catch(() => toast('No se pudo cargar la guía. Revisa tu conexión e inténtalo nuevamente.', 'error'))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!guia) {
    return (
      <div className="page-shell">
        <Link to="/guias" className="inline-flex items-center gap-2 text-sm text-[var(--text-secondary)]">
          <ArrowLeft className="h-4 w-4" />
          Volver a guias
        </Link>
        <p className="text-sm text-[var(--text-secondary)]">Guia no encontrada.</p>
      </div>
    );
  }

  const numero =
    guia.serie && guia.correlativo != null
      ? `${guia.serie}-${String(guia.correlativo).padStart(6, '0')}`
      : `#${guia.id}`;

  const fmt = (value) => (value ? new Date(value).toLocaleDateString('es-PE') : '--');

  return (
    <div className="page-shell max-w-5xl">
      <div className="page-header">
        <div className="page-header-copy">
          <Link to="/guias" className="mb-4 inline-flex items-center gap-2 text-sm text-[var(--text-secondary)]">
            <ArrowLeft className="h-4 w-4" />
            Volver a guias
          </Link>
          <p className="page-kicker">Seguimiento de despacho</p>
          <h2 className="page-title">Guia {numero}</h2>
          <p className="page-subtitle">
            Emitida: {fmt(guia.fecha_emision)} · Traslado: {fmt(guia.fecha_traslado)}
          </p>
        </div>

        <div className="page-actions">
          <Badge variant={statusBadge(guia.estado)}>{guia.estado || 'pendiente'}</Badge>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="ink-card p-5">
          <h3 className="ink-card-title flex items-center gap-2">
            <Truck className="h-4 w-4 text-[var(--text-brand)]" />
            Traslado
          </h3>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <div>
              <p className="label">Motivo</p>
              <p className="text-sm text-[var(--text-primary)]">
                {MOTIVO_LABEL[guia.motivo_traslado] || guia.motivo_traslado}{' '}
                {guia.descripcion_motivo ? `· ${guia.descripcion_motivo}` : ''}
              </p>
            </div>
            <div>
              <p className="label">Modalidad</p>
              <p className="text-sm text-[var(--text-primary)]">
                {MODALIDAD_LABEL[guia.modalidad_traslado] || guia.modalidad_traslado}
              </p>
            </div>
            <div>
              <p className="label">Peso bruto</p>
              <p className="text-sm text-[var(--text-primary)]">
                {guia.peso_bruto_total} {guia.unidad_medida_peso}
              </p>
            </div>
            {guia.internal_order_number && (
              <div>
                <p className="label">Orden</p>
                <Link to={`/cotizaciones/${guia.cotizacion_id}`} className="text-sm text-[var(--text-brand)] underline">
                  {guia.internal_order_number}
                </Link>
              </div>
            )}
          </div>
        </div>

        <div className="ink-card p-5">
          <h3 className="ink-card-title flex items-center gap-2">
            <MapPin className="h-4 w-4 text-[var(--text-brand)]" />
            Ruta
          </h3>
          <div className="mt-4 grid gap-6 md:grid-cols-2">
            <div>
              <p className="label">Origen</p>
              <p className="text-sm text-[var(--text-primary)]">{guia.partida_direccion || '--'}</p>
              {guia.partida_ubigeo && (
                <p className="mt-1 text-xs text-[var(--text-secondary)]">Ubigeo: {guia.partida_ubigeo}</p>
              )}
            </div>
            <div>
              <p className="label">Destino</p>
              <p className="text-sm text-[var(--text-primary)]">{guia.llegada_direccion || '--'}</p>
              {guia.llegada_ubigeo && (
                <p className="mt-1 text-xs text-[var(--text-secondary)]">Ubigeo: {guia.llegada_ubigeo}</p>
              )}
            </div>
          </div>
        </div>
      </div>

      {(guia.transportista_ruc || guia.conductor_nro_doc || guia.vehiculo_placa) && (
        <div className="ink-card p-5">
          <h3 className="ink-card-title">Transportista</h3>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            {guia.transportista_ruc && (
              <div>
                <p className="label">RUC transportista</p>
                <p className="text-sm text-[var(--text-primary)]">
                  {guia.transportista_ruc}
                  {guia.transportista_razon_social ? ` · ${guia.transportista_razon_social}` : ''}
                </p>
              </div>
            )}
            {guia.conductor_nro_doc && (
              <div>
                <p className="label">Conductor</p>
                <p className="text-sm text-[var(--text-primary)]">
                  {[guia.conductor_nombres, guia.conductor_apellidos].filter(Boolean).join(' ') ||
                    guia.conductor_nro_doc}
                </p>
                {guia.conductor_licencia && (
                  <p className="mt-1 text-xs text-[var(--text-secondary)]">
                    Licencia: {guia.conductor_licencia}
                  </p>
                )}
              </div>
            )}
            {guia.vehiculo_placa && (
              <div>
                <p className="label">Vehiculo</p>
                <p className="font-mono-label text-sm text-[var(--text-primary)]">
                  {guia.vehiculo_placa}
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {guia.items && guia.items.length > 0 && (
        <div className="ink-table-card">
          <div className="ink-card-header">
            <div>
              <h3 className="ink-card-title flex items-center gap-2">
                <Package className="h-4 w-4 text-[var(--text-brand)]" />
                Bienes a trasladar
              </h3>
              <p className="ink-card-subtitle">{guia.items.length} item(s) incluidos en la guia</p>
            </div>
          </div>

          <table className="ink-table">
            <thead>
              <tr>
                <th>Descripcion</th>
                <th className="text-right">Cantidad</th>
                <th>Unidad</th>
              </tr>
            </thead>
            <tbody>
              {guia.items.map((item) => (
                <tr key={item.id}>
                  <td data-label="Descripcion">{item.descripcion}</td>
                  <td data-label="Cantidad" className="text-right font-mono-label">{Number(item.cantidad)}</td>
                  <td data-label="Unidad" className="text-[var(--text-secondary)]">{item.unidad_medida}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {(guia.sunat_pdf_url || guia.sunat_error) && (
        <div className="ink-card p-5">
          <h3 className="ink-card-title">SUNAT</h3>
          {guia.sunat_pdf_url && (
            <a href={guia.sunat_pdf_url} target="_blank" rel="noreferrer" className="mt-4 inline-flex text-sm text-[var(--text-brand)] underline">
              Descargar PDF SUNAT
            </a>
          )}
          {guia.sunat_error && (
            <p className="mt-3 text-sm text-[var(--color-error)]">{guia.sunat_error}</p>
          )}
        </div>
      )}
    </div>
  );
}
