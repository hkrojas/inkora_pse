import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, MapPin, Truck, Package } from 'lucide-react';
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
  '01': 'Transporte público',
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
      .catch(() => toast('Error al cargar la guía', 'error'))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="flex h-64 items-center justify-center"><Spinner size="lg" /></div>;
  if (!guia) return (
    <div className="p-6">
      <Link to="/guias" className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4">
        <ArrowLeft className="h-4 w-4" /> Volver a guías
      </Link>
      <p className="text-sm text-gray-500">Guía no encontrada.</p>
    </div>
  );

  const numero = guia.serie && guia.correlativo != null
    ? `${guia.serie}-${String(guia.correlativo).padStart(6, '0')}`
    : `#${guia.id}`;

  const fmt = (d) => d ? new Date(d).toLocaleDateString('es-PE') : '—';

  return (
    <div className="p-6 max-w-3xl space-y-6">
      {/* Encabezado */}
      <div>
        <Link to="/guias" className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-3">
          <ArrowLeft className="h-4 w-4" /> Volver a guías
        </Link>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-lg font-semibold text-gray-900">Guía {numero}</h1>
            <p className="text-sm text-gray-500">
              Emitida: {fmt(guia.fecha_emision)} · Traslado: {fmt(guia.fecha_traslado)}
            </p>
          </div>
          <Badge variant={statusBadge(guia.estado)}>{guia.estado || 'pendiente'}</Badge>
        </div>
      </div>

      {/* Traslado */}
      <div className="rounded-xl border border-gray-200 bg-white shadow-sm p-5 space-y-4">
        <h2 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
          <Truck className="h-4 w-4 text-gray-400" /> Traslado
        </h2>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-xs text-gray-500 mb-0.5">Motivo</p>
            <p className="text-gray-900">{MOTIVO_LABEL[guia.motivo_traslado] || guia.motivo_traslado} {guia.descripcion_motivo ? `· ${guia.descripcion_motivo}` : ''}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500 mb-0.5">Modalidad</p>
            <p className="text-gray-900">{MODALIDAD_LABEL[guia.modalidad_traslado] || guia.modalidad_traslado}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500 mb-0.5">Peso bruto</p>
            <p className="text-gray-900">{guia.peso_bruto_total} {guia.unidad_medida_peso}</p>
          </div>
          {guia.internal_order_number && (
            <div>
              <p className="text-xs text-gray-500 mb-0.5">Orden</p>
              <Link to={`/cotizaciones/${guia.cotizacion_id}`} className="text-blue-600 hover:underline text-sm">
                {guia.internal_order_number}
              </Link>
            </div>
          )}
        </div>
      </div>

      {/* Origen → Destino */}
      <div className="rounded-xl border border-gray-200 bg-white shadow-sm p-5">
        <h2 className="text-sm font-semibold text-gray-900 flex items-center gap-2 mb-4">
          <MapPin className="h-4 w-4 text-gray-400" /> Ruta
        </h2>
        <div className="grid grid-cols-2 gap-6 text-sm">
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Origen</p>
            <p className="text-gray-900">{guia.partida_direccion || '—'}</p>
            {guia.partida_ubigeo && <p className="text-xs text-gray-400 mt-0.5">Ubigeo: {guia.partida_ubigeo}</p>}
          </div>
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Destino</p>
            <p className="text-gray-900">{guia.llegada_direccion || '—'}</p>
            {guia.llegada_ubigeo && <p className="text-xs text-gray-400 mt-0.5">Ubigeo: {guia.llegada_ubigeo}</p>}
          </div>
        </div>
      </div>

      {/* Transportista / Conductor */}
      {(guia.transportista_ruc || guia.conductor_nro_doc || guia.vehiculo_placa) && (
        <div className="rounded-xl border border-gray-200 bg-white shadow-sm p-5">
          <h2 className="text-sm font-semibold text-gray-900 mb-4">Transportista</h2>
          <div className="grid grid-cols-2 gap-4 text-sm">
            {guia.transportista_ruc && (
              <div>
                <p className="text-xs text-gray-500 mb-0.5">RUC transportista</p>
                <p className="text-gray-900">{guia.transportista_ruc} {guia.transportista_razon_social ? `· ${guia.transportista_razon_social}` : ''}</p>
              </div>
            )}
            {guia.conductor_nro_doc && (
              <div>
                <p className="text-xs text-gray-500 mb-0.5">Conductor</p>
                <p className="text-gray-900">{[guia.conductor_nombres, guia.conductor_apellidos].filter(Boolean).join(' ') || guia.conductor_nro_doc}</p>
                {guia.conductor_licencia && <p className="text-xs text-gray-400 mt-0.5">Licencia: {guia.conductor_licencia}</p>}
              </div>
            )}
            {guia.vehiculo_placa && (
              <div>
                <p className="text-xs text-gray-500 mb-0.5">Vehículo</p>
                <p className="text-gray-900 font-mono">{guia.vehiculo_placa}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Bienes */}
      {guia.items && guia.items.length > 0 && (
        <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
          <div className="flex items-center gap-2 border-b border-gray-100 px-5 py-3.5">
            <Package className="h-4 w-4 text-gray-400" />
            <h2 className="text-sm font-semibold text-gray-900">Bienes a trasladar</h2>
            <span className="ml-auto text-xs text-gray-400">{guia.items.length} ítem(s)</span>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                <th className="px-5 py-3">Descripción</th>
                <th className="px-5 py-3 text-right">Cantidad</th>
                <th className="px-5 py-3">Unidad</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {guia.items.map((item) => (
                <tr key={item.id} className="hover:bg-gray-50">
                  <td className="px-5 py-3 text-gray-900">{item.descripcion}</td>
                  <td className="px-5 py-3 text-right text-gray-700">{Number(item.cantidad)}</td>
                  <td className="px-5 py-3 text-gray-500">{item.unidad_medida}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* SUNAT */}
      {(guia.sunat_pdf_url || guia.sunat_error) && (
        <div className="rounded-xl border border-gray-200 bg-white shadow-sm p-5">
          <h2 className="text-sm font-semibold text-gray-900 mb-3">SUNAT</h2>
          {guia.sunat_pdf_url && (
            <a href={guia.sunat_pdf_url} target="_blank" rel="noreferrer" className="text-sm text-blue-600 hover:underline">
              Descargar PDF SUNAT
            </a>
          )}
          {guia.sunat_error && (
            <p className="text-xs text-red-600 mt-1">{guia.sunat_error}</p>
          )}
        </div>
      )}
    </div>
  );
}
