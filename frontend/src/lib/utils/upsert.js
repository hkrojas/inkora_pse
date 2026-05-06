/**
 * Orchestrates client and product upserts before saving a quote or invoice.
 * All functions throw on failure so callers can abort the chain.
 */

import { clientes as clientesSvc } from '../../services/clientes';
import { productos as productosSvc } from '../../services/productos';
import { normalizePeruMobileInput } from './peruPhoneValidation';
import {
  getFiscalClientErrorMessage,
  normalizeFiscalDocumentNumber,
  normalizeFiscalUbigeo,
} from './fiscalClientValidation';
import {
  normalizeInternalProductCode,
  normalizeSunatUnitCode,
} from './sunatCatalogs';

/**
 * Create or update a client.
 * @param {{ id: string|null, isNew: boolean, isDirty: boolean, form: object }} clientState
 * @returns {Promise<number>} resolved cliente_id
 */
export async function upsertCliente({ id, isNew, isDirty, form }) {
  if (!isNew && !isDirty) {
    if (!id) throw new Error('No hay cliente seleccionado');
    return Number(id);
  }

  const normalizedForm = {
    ...form,
    numero_documento: normalizeFiscalDocumentNumber(form.tipo_documento, form.numero_documento),
    ubigeo: normalizeFiscalUbigeo(form.ubigeo || ''),
    telefono: normalizePeruMobileInput(form.telefono || ''),
  };
  const clientError = getFiscalClientErrorMessage(normalizedForm);
  if (clientError) {
    throw new Error(clientError);
  }

  const payload = {
    tipo_documento: normalizedForm.tipo_documento,
    numero_documento: String(normalizedForm.numero_documento || '').trim(),
    razon_social: String(normalizedForm.razon_social || '').trim(),
    nombre_comercial: String(normalizedForm.nombre_comercial || '').trim(),
    direccion: String(normalizedForm.direccion || '').trim(),
    ubigeo: String(normalizedForm.ubigeo || '').trim(),
    email: String(normalizedForm.email || '').trim(),
    telefono: normalizedForm.telefono,
    whatsapp: normalizedForm.telefono,
    contacto: '',
  };

  if (isNew) {
    const created = await clientesSvc.create(payload);
    return created.id;
  }

  const updated = await clientesSvc.update(Number(id), payload);
  return updated.id;
}

/**
 * For each line item marked _isNew, create the product in the catalog.
 * Returns a new items array with resolved producto_id values.
 * @param {Array} items
 * @returns {Promise<Array>}
 */
export async function upsertProductos(items) {
  return Promise.all(
    items.map(async (item) => {
      if (!item._isNew) return item;

      const nombre = String(item.descripcion || '').trim();
      if (!nombre) return item;

      const created = await productosSvc.create({
        nombre,
        codigo_interno: normalizeInternalProductCode(item.codigo) || undefined,
        precio_unitario: Number(item.precio_unitario) || 1,
        precio_incluye_igv: true,
        unidad_medida: normalizeSunatUnitCode(item.unidad_medida),
        tipo_afectacion_igv: item.tipo_afectacion_igv || '10',
        descripcion: nombre,
      });

      return { ...item, producto_id: String(created.id), _isNew: false };
    }),
  );
}
