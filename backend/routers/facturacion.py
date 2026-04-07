from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from sqlalchemy.orm import Session

import crud
from services import facturacion_service
import models
import schemas
from api_dependencies import (
    get_current_user,
    get_db_tenant,
    require_document_emitter,
)
from api_utils import raise_internal_server_error
from services import pdf_storage_service
from services.facturacion_background_service import process_direct_sunat_emission_bg

router = APIRouter(tags=["facturacion"])


def _validar_pre_emision(quote, tipo_comprobante: str):
    """
    Valida los pre-requisitos antes de enviar a SUNAT.
    Lanza HTTPException 400 con mensaje claro si algo no está listo.
    """
    cliente = quote.cliente

    # 1. Cliente asignado
    if not cliente:
        raise HTTPException(400, "Pre-validacion fallida: La cotizacion no tiene cliente asignado.")

    # 2. Documento de identidad del cliente
    if not cliente.numero_documento or len(cliente.numero_documento.strip()) < 8:
        raise HTTPException(
            400,
            "Pre-validacion fallida: El cliente no tiene numero de documento valido (minimo 8 digitos).",
        )

    # 3. Para facturas (tipo 01): el cliente debe tener RUC (11 digitos, tipo 6)
    if tipo_comprobante == "01":
        if cliente.tipo_documento != "6" or len(cliente.numero_documento.strip()) != 11:
            raise HTTPException(
                400,
                (
                    "Pre-validacion fallida: Las Facturas (tipo 01) requieren que el cliente "
                    "tenga RUC (11 digitos, tipo_documento='6'). "
                    f"Documento actual: {cliente.numero_documento} (tipo {cliente.tipo_documento})."
                ),
            )

    # 4. tipo_comprobante debe ser valido
    TIPOS_VALIDOS = {"01", "03", "07", "08"}
    if tipo_comprobante not in TIPOS_VALIDOS:
        raise HTTPException(
            400,
            f"Pre-validacion fallida: tipo_comprobante '{tipo_comprobante}' no valido. "
            f"Valores permitidos: {', '.join(sorted(TIPOS_VALIDOS))}.",
        )

    # 5. Monto de venta debe ser > 0
    if not quote.total_venta or quote.total_venta <= 0:
        raise HTTPException(
            400,
            "Pre-validacion fallida: La cotizacion tiene total_venta igual a cero. No se puede facturar.",
        )

    # 6. Debe tener al menos un item
    if not quote.items:
        raise HTTPException(
            400,
            "Pre-validacion fallida: La cotizacion no tiene items. Agregue al menos un producto o servicio.",
        )

    # 7. Cotización no debe estar anulada
    if quote.estado == "anulada":
        raise HTTPException(
            400,
            "Pre-validacion fallida: No se puede facturar una cotizacion anulada.",
        )


@router.post("/cotizaciones/{cotizacion_id}/facturar")
def emitir_comprobante(
    cotizacion_id: int,
    payload: schemas.FacturarPayload,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(require_document_emitter),
):
    quote = crud.get_cotizacion(db, cotizacion_id, current_user)
    if not quote:
        raise HTTPException(404, "Documento no encontrado")

    if quote.document_kind != "quotation":
        raise HTTPException(
            400,
            "La ruta de facturacion solo acepta cotizaciones comerciales.",
        )

    # Pre-validación estructural antes de crear registro o contactar SUNAT
    _validar_pre_emision(quote, payload.tipo_comprobante)

    linked_fiscal_document = crud.get_latest_fiscal_document_for_quote(
        db,
        quote.id,
        current_user.tenant_id,
    )
    if linked_fiscal_document and linked_fiscal_document.estado != "anulada":
        raise HTTPException(
            400,
            (
                f"Operacion bloqueada: La cotizacion {quote.serie}-{quote.correlativo} "
                f"ya tiene un documento fiscal asociado ({linked_fiscal_document.serie}-"
                f"{str(linked_fiscal_document.correlativo).zfill(6)}). "
                "Anule el documento existente antes de emitir uno nuevo."
            ),
        )

    # Fase 9: verificar límite de documentos antes de crear el fiscal
    try:
        crud.check_document_limit(db, current_user.tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=402, detail=str(exc))

    try:
        fiscal_document = crud.create_fiscal_document_from_quote(
            db,
            quote,
            current_user.id,
            payload.tipo_comprobante,
        )
        tenant = (
            db.query(models.Tenant)
            .filter(models.Tenant.id == current_user.tenant_id)
            .first()
        )

        if tenant and tenant.sunat_usuario_sol and tenant.sunat_cert_url:
            background_tasks.add_task(
                process_direct_sunat_emission_bg,
                fiscal_document.id,
                current_user.tenant_id,
            )
            background_tasks.add_task(
                pdf_storage_service.process_pdf_background,
                fiscal_document.id,
                current_user.tenant_id,
            )

            return {
                "success": True,
                "source_quote_id": quote.id,
                "document_id": fiscal_document.id,
                "internal_order_number": fiscal_document.internal_order_number,
                "message": (
                    "Emision directa iniciada. El comprobante se procesara en segundo plano."
                ),
                "sunat_response": {
                    "success": True,
                    "cdrResponse": {"description": "En cola para envio directo"},
                },
            }

        resultado = facturacion_service.emitir_factura(
            fiscal_document,
            db,
            current_user,
            tipo_doc_override=payload.tipo_comprobante,
        )
        crud.guardar_respuesta_sunat(
            db,
            fiscal_document.id,
            resultado,
            tenant_id=current_user.tenant_id,
        )

        background_tasks.add_task(
            pdf_storage_service.process_pdf_background,
            fiscal_document.id,
            current_user.tenant_id,
        )
        resultado["source_quote_id"] = quote.id
        resultado["document_id"] = fiscal_document.id
        resultado["internal_order_number"] = fiscal_document.internal_order_number
        return resultado

    except facturacion_service.FacturacionException as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:
        raise_internal_server_error(
            "emitir_comprobante",
            "Error en el servicio de facturacion.",
            exc,
        )


@router.post("/notas/emitir")
def emitir_nota(
    nota_data: schemas.NotaCreate,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(require_document_emitter),
):
    doc_afectado = crud.resolve_fiscal_document_reference(
        db,
        nota_data.comprobante_afectado_id,
        current_user.tenant_id,
    )
    if not doc_afectado:
        raise HTTPException(404, "Comprobante afectado no encontrado")

    if doc_afectado.estado not in ("facturada",):
        raise HTTPException(
            400,
            (
                "Operacion bloqueada: Solo se pueden emitir Notas de Credito/Debito "
                "contra comprobantes en estado 'facturada'. "
                f"Estado actual del documento {doc_afectado.serie}-{doc_afectado.correlativo}: "
                f"'{doc_afectado.estado}'."
            ),
        )

    try:
        db_nota = crud.crear_nota_credito_debito(
            db=db,
            doc_afectado=doc_afectado,
            usuario_id=current_user.id,
            tipo_nota=nota_data.tipo_nota,
            cod_motivo=nota_data.cod_motivo,
            descripcion_motivo=nota_data.descripcion_motivo,
        )
        resultado = facturacion_service.emitir_nota(
            nota=db_nota,
            doc_afectado=doc_afectado,
            user=current_user,
            cod_motivo=nota_data.cod_motivo,
            descripcion=nota_data.descripcion_motivo,
            tipo_nota=nota_data.tipo_nota,
        )
        crud.guardar_respuesta_sunat(
            db,
            db_nota.id,
            resultado,
            tenant_id=current_user.tenant_id,
        )
        return resultado
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except facturacion_service.FacturacionException as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:
        raise_internal_server_error(
            "emitir_nota",
            "Error en el servicio de notas electronicas.",
            exc,
        )


@router.post("/bajas/anular")
def anular_documento(
    data: schemas.AnulacionCreate,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(require_document_emitter),
):
    comprobante = crud.resolve_fiscal_document_reference(
        db,
        data.comprobante_id,
        current_user.tenant_id,
    )
    if not comprobante:
        raise HTTPException(404)

    if comprobante.estado != "facturada":
        estado_msg = {
            "pendiente": "El documento aun no ha sido emitido ante SUNAT. No requiere anulacion.",
            "anulada": "El documento ya fue anulado previamente. No se puede procesar dos veces.",
        }
        raise HTTPException(
            400,
            (
                "Operacion bloqueada: "
                f"{estado_msg.get(comprobante.estado, f'Estado invalido: {comprobante.estado}')}"
            ),
        )

    try:
        resultado = facturacion_service.anular_comprobante(
            comprobante,
            data.motivo,
            current_user,
        )
        crud.anular_cotizacion(
            db,
            comprobante.id,
            tenant_id=current_user.tenant_id,
        )
        return resultado
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except facturacion_service.FacturacionException as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:
        raise_internal_server_error(
            "anular_documento",
            "Error al anular el documento.",
            exc,
        )


@router.post("/facturacion/{tipo_archivo}")
def recuperar_archivo_api(
    tipo_archivo: str,
    payload: schemas.DescargaArchivoPayload,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    if tipo_archivo not in ["xml", "pdf", "cdr"]:
        raise HTTPException(400, "Tipo invalido")

    comprobante = crud.resolve_fiscal_document_reference(
        db,
        payload.comprobante_id,
        current_user.tenant_id,
    )
    if not comprobante:
        raise HTTPException(404)

    try:
        contenido = facturacion_service.descargar_archivo(
            tipo_archivo,
            comprobante,
            current_user,
        )
        media_type = "application/pdf" if tipo_archivo == "pdf" else "application/xml"
        if tipo_archivo == "cdr":
            media_type = "application/zip"
        ext = tipo_archivo if tipo_archivo != "cdr" else "zip"
        filename = f"{comprobante.serie}-{comprobante.correlativo}.{ext}"
        return Response(
            content=contenido,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except facturacion_service.FacturacionException as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:
        raise_internal_server_error(
            "recuperar_archivo_api",
            "No se pudo recuperar el archivo solicitado.",
            exc,
        )
