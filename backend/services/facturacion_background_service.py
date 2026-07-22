import crud
from services import facturacion_service
import models
from config import settings
from database import SessionLocal, apply_tenant_context, reset_tenant_context
from logging_utils import get_logger
from services import fiscal_provider_service, sunat_service
from services.fiscal_clock import fiscal_datetime_in_peru

logger = get_logger(__name__)


def process_direct_sunat_emission_bg(
    cotizacion_id: int,
    tenant_id: int,
    *,
    raise_on_error: bool = False,
) -> dict | None:
    """
    Pipeline completo de emision directa a SUNAT en segundo plano.
    Se mantiene fuera de los routers para que el HTTP layer quede fino.
    """
    db = SessionLocal()
    tenant_token = None
    try:
        tenant_token = apply_tenant_context(db, tenant_id)

        cotizacion = (
            db.query(models.Cotizacion)
            .filter(models.Cotizacion.id == cotizacion_id)
            .first()
        )
        tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()

        if settings.is_fiscal_beta:
            detail = "La emision SUNAT directa esta deshabilitada en FISCAL_ENV=beta."
            if cotizacion:
                crud.guardar_error_sunat(db, cotizacion_id, detail, tenant_id=tenant_id)
            logger.error(
                "sunat_direct_beta_blocked",
                extra={
                    "event": "sunat_direct_beta_blocked",
                    "tenant_id": tenant_id,
                    "cotizacion_id": cotizacion_id,
                },
            )
            if raise_on_error:
                raise RuntimeError(detail)
            return {"success": False, "message": detail}

        if not cotizacion or not tenant or not fiscal_provider_service.has_complete_direct_sunat_credentials(tenant):
            detail = "Faltan credenciales SUNAT directas del tenant."
            if cotizacion:
                crud.guardar_error_sunat(db, cotizacion_id, detail, tenant_id=tenant_id)
            logger.error(
                "sunat_credentials_missing",
                extra={
                    "event": "sunat_credentials_missing",
                    "tenant_id": tenant_id,
                    "cotizacion_id": cotizacion_id,
                },
            )
            if raise_on_error:
                raise RuntimeError(detail)
            return {"success": False, "message": detail}

        emisor_data = {
            "ruc": tenant.business_ruc or "12345678901",
            "nombre": tenant.business_name or "Empresa Test",
            "direccion": tenant.business_address or "Calle Real 123",
            "ubigeo": getattr(tenant, "ubigeo", None) or "150101",
        }
        cliente = cotizacion.cliente
        cliente_data = {
            "numero_documento": cliente.numero_documento,
            "tipo_documento": facturacion_service.obtener_tipo_documento_codigo(
                cliente.tipo_documento
            ),
            "nombre": cliente.razon_social or "-",
        }

        items_data = []
        for item in cotizacion.items:
            calc = facturacion_service.calculations.calcular_item(
                item.cantidad,
                item.precio_unitario,
                tipo_afectacion_igv=getattr(item, "tipo_afectacion_igv", "10"),
            )
            items_data.append(
                {
                    "descripcion": item.descripcion,
                    "cantidad": item.cantidad,
                    "valor_unitario": calc["valor_unitario"],
                    "precio_unitario": item.precio_unitario,
                    "valor_venta": calc["total_base_igv"],
                    "igv": calc["total_igv"],
                }
            )

        ubl_payload = {
            "serie": cotizacion.serie
            or ("F001" if cotizacion.tipo_comprobante == "01" else "B001"),
            "correlativo": str(cotizacion.correlativo or cotizacion.id).zfill(6),
            "fecha_emision": fiscal_datetime_in_peru(cotizacion.fecha_emision).date().isoformat(),
            "tipo_comprobante": cotizacion.tipo_comprobante or "01",
            "monto_letras": facturacion_service.numero_a_letras(cotizacion.total_venta),
            "emisor": emisor_data,
            "cliente": cliente_data,
            "items": items_data,
            "total_gravada": cotizacion.total_gravada,
            "total_igv": cotizacion.total_igv,
            "total_venta": cotizacion.total_venta,
        }

        cert_data = sunat_service.SUNATService.get_cert_from_storage(
            tenant.sunat_cert_url
        )
        sunat = sunat_service.SUNATService(
            ruc=tenant.business_ruc,
            usuario_sol=tenant.sunat_usuario_sol,
            clave_sol=tenant.sunat_clave_sol,
            cert_data=cert_data,
            cert_password=tenant.sunat_cert_password,
        )

        xml_raw = sunat.generate_invoice_ubl(ubl_payload)
        xml_signed = sunat.sign_xml(xml_raw)
        resultado = sunat.send_bill(
            f"{ubl_payload['serie']}-{ubl_payload['correlativo']}",
            xml_signed,
        )

        if resultado["success"]:
            response_payload = {
                "success": True,
                "sunat_response": {
                    "success": True,
                    "cdrResponse": {
                        "description": "Aceptado por SUNAT (Procesamiento Directo)"
                    },
                    "links": {"cdr": "stored_locally"},
                },
            }
            crud.guardar_respuesta_sunat(
                db,
                cotizacion_id,
                response_payload,
                tenant_id=tenant_id,
            )
            logger.info(
                "sunat_emission_completed",
                extra={
                    "event": "sunat_emission_completed",
                    "tenant_id": tenant_id,
                    "cotizacion_id": cotizacion_id,
                },
            )
            return response_payload
        else:
            detail = resultado.get("message") or "SUNAT directo rechazó la emisión."
            crud.guardar_error_sunat(db, cotizacion_id, detail, tenant_id=tenant_id)
            logger.error(
                "sunat_emission_failed",
                extra={
                    "event": "sunat_emission_failed",
                    "tenant_id": tenant_id,
                    "cotizacion_id": cotizacion_id,
                },
            )
            if raise_on_error:
                raise RuntimeError(detail)
            return {"success": False, "message": detail}
    except Exception as exc:
        detail = str(exc) or "Fallo el procesamiento directo contra SUNAT."
        crud.guardar_error_sunat(
            db,
            cotizacion_id,
            detail,
            tenant_id=tenant_id,
        )
        logger.exception(
            "sunat_emission_background_failed",
            extra={
                "event": "sunat_emission_background_failed",
                "tenant_id": tenant_id,
                "cotizacion_id": cotizacion_id,
            },
        )
        if raise_on_error:
            raise
        return {"success": False, "message": detail}
    finally:
        if tenant_token is not None:
            reset_tenant_context(tenant_token)
        db.close()
