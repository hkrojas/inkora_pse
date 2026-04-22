/**
 * Orchestrates client and product upserts before saving a quote or invoice.
 * All functions throw on failure so callers can abort the chain.
 */

import { clientes as clientesSvc } from '../../services/clientes';
import { productos as productosSvc } from '../../services/productos';
import { normalizePeruMobileInput } from './peruPhoneValidation';

/**
 * Create or update a client.
 * @param {{ id: string|null, isNew: boolean, isDirty: boolean, form: object }} clientState
 * @returns {Promise<number>} resolved cliente_id
 */
export async function upsertCliente({ id, isNew, isDirty, form }) {
  // Existing client, no edits — nothing to do
  if (!isNew && !isDirty) {
    if (!id) throw new Error('No hay cliente seleccionado');
    return Number(id);
  }

  const payload = {
    tipo_documento:   form.tipo_documento,
    numero_documento: String(form.numero_documento || '').trim(),
    razon_social:     String(form.razon_social || '').trim(),
    direccion:        String(form.direccion || '').trim(),
    email:            String(form.email || '').trim(),
    telefono:         normalizePeruMobileInput(form.telefono || ''),
    whatsapp:         normalizePeruMobileInput(form.telefono || ''),
    contacto:         '',
  };

  if (isNew) {
    const created = await clientesSvc.create(payload);
    return created.id;
  }

  // Update existing client (email/telefono/dirección changed)
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
      if (!nombre) return item; // skip blank lines

      const created = await productosSvc.create({
        nombre,
        codigo_interno:      item.codigo?.trim() || undefined,
        precio_unitario:     Number(item.precio_unitario) || 1,
        precio_incluye_igv:  true,
        unidad_medida:       item.unidad_medida || 'NIU',
        tipo_afectacion_igv: item.tipo_afectacion_igv || '10',
        descripcion:         nombre,
      });

      return { ...item, producto_id: String(created.id), _isNew: false };
    }),
  );
}
