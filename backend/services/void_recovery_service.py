"""Durable, single-submission cancellation and read-only reconciliation.

The emission job owns the frozen batch and its evidence. A ticket, HTTP success,
timeout or interrupted execution never authorizes an inventory reversal.
"""
from datetime import timedelta, timezone
from xml.etree import ElementTree as ET

from fastapi.encoders import jsonable_encoder

import fiscal_time
import models
from services import emission_leases, smartpse_client, smartpse_response, smartpse_ubl_service


def is_summary(document):
    return document.tipo_comprobante == "03" or (
        document.tipo_comprobante in {"07", "08"} and (document.serie or "").startswith("B")
    )


def validate_document(document, user):
    if document.tenant_id != user.tenant_id:
        raise ValueError("El comprobante no pertenece a la empresa autenticada.")
    if document.tipo_comprobante not in {"01", "03", "07", "08"} or not document.serie or document.correlativo is None:
        raise ValueError("Identidad fiscal incompleta para solicitar la baja.")
    if document.estado != "facturada" or not document.sunat_accepted:
        raise ValueError("La baja requiere un comprobante vigente con CDR aceptado.")
    cdr = document.sunat_cdr_content or smartpse_response.extract_cdr_xml(document.provider_response)
    if not cdr:
        raise ValueError("Recupere el CDR original antes de solicitar la baja.")
    try:
        smartpse_response.validate_sale_cdr(cdr, {
            "serie": document.serie, "correlativo": document.correlativo,
            "company": {"ruc": user.tenant.business_ruc},
        })
    except smartpse_client.SmartPSEException as exc:
        raise ValueError("El CDR original no confirma la identidad del comprobante; requiere conciliación.") from exc
    if document.tipo_comprobante == "07" and document.inventory_impact not in {None, "none"}:
        raise ValueError("La nota tiene un movimiento de inventario asociado; requiere conciliación antes de una baja.")
    if not document.fecha_emision:
        raise ValueError("Falta la fecha de emisión original; concilie el comprobante antes de darlo de baja.")
    issued = fiscal_time.as_lima(document.fecha_emision).date()
    # The saved reception time is authoritative when available. Legacy documents
    # without a reception timestamp require review rather than an invented window.
    accepted = document.provider_verified_at
    if not accepted:
        raise ValueError("Falta la fecha de recepción del CDR; concilie el comprobante antes de darlo de baja.")
    # Provider verification timestamps originate in UTC, unlike issue dates.
    accepted_day = fiscal_time.as_lima(accepted if accepted.tzinfo else accepted.replace(tzinfo=timezone.utc)).date()
    today = fiscal_time.today_lima()
    if issued > today or accepted_day > today or today > accepted_day + timedelta(days=7):
        raise ValueError("El comprobante está fuera del plazo de baja; revise si corresponde una nota de crédito.")


def ensure_note_source_available(db, document, *, jobs=None):
    """Caller locks the source row before creating/numbering/emitting a note."""
    if jobs is None:
        jobs = db.query(models.DocumentEmissionJob).filter(
            models.DocumentEmissionJob.tenant_id == document.tenant_id,
            models.DocumentEmissionJob.resource_type == models.EMISSION_JOB_RESOURCE_COTIZACION,
            models.DocumentEmissionJob.resource_id == document.id,
            models.DocumentEmissionJob.action == models.EMISSION_JOB_ACTION_VOID_FISCAL,
        ).all()
    for job in jobs:
        if job.action != models.EMISSION_JOB_ACTION_VOID_FISCAL:
            continue
        if job.status == models.EMISSION_JOB_STATUS_FAILED:
            snapshot = job.payload_snapshot or {}
            if snapshot.get("void_protocol_version") == 1 and snapshot.get("void_send_started") is False:
                continue
            from services.facturacion_service import FacturacionRejectedException
            try:
                cdr_result(snapshot.get("void_result") or {}, snapshot.get("void_payload") or {})
            except FacturacionRejectedException:
                continue  # A matching definitive rejection did not cancel the source.
            except (KeyError, TypeError):
                pass  # Incomplete historical evidence also requires reconciliation.
        raise ValueError("El comprobante tiene una baja pendiente de conciliación; no se puede emitir una nota.")


def ensure_no_active_notes(db, document):
    note = db.query(models.Cotizacion.id).filter(
        models.Cotizacion.tenant_id == document.tenant_id,
        models.Cotizacion.nota_referencia_id == document.id,
        models.Cotizacion.tipo_comprobante.in_(("07", "08")),
        models.Cotizacion.estado.in_(("pendiente", "facturada")),
    ).first()
    if note:
        raise ValueError("Resuelva primero las notas pendientes o vigentes vinculadas al comprobante antes de solicitar la baja.")


def _reserve_counter(db, tenant_id, prefix, day):
    # Caller holds the tenant row lock through job creation. Include existing
    # manually registered batches so a new automatic batch cannot reuse them.
    used = set()
    batches = db.query(models.DocumentEmissionJob.payload_snapshot["void_payload"]["correlativo"].as_string()).filter(
        models.DocumentEmissionJob.tenant_id == tenant_id,
        models.DocumentEmissionJob.action == models.EMISSION_JOB_ACTION_VOID_FISCAL,
        models.DocumentEmissionJob.payload_snapshot["void_payload"]["tipoDoc"].as_string() == prefix,
        models.DocumentEmissionJob.payload_snapshot["void_payload"]["correlativo"].as_string().like(day + "-%"),
    ).all()
    if prefix == "RC":
        batches += db.query(models.ResumenDiario.correlativo).filter(
            models.ResumenDiario.tenant_id == tenant_id,
            models.ResumenDiario.correlativo.like(day + "-%")).all()
    for (value,) in batches:
        number = str(value or "").split("-")[-1]
        if number.isdigit():
            used.add(int(number))
    for number in range(1, 100000):
        if number not in used:
            return f"{day}-{number:05d}"
    raise ValueError("Se agotaron los correlativos de lotes de baja del día.")


def prepare_snapshot(db, document, user, reason):
    from services import facturacion_service

    validate_document(document, user)
    now = fiscal_time.now_lima()
    prefix = "RC" if is_summary(document) else "RA"
    if prefix == "RC":
        payload = facturacion_service._build_summary_payload(document, reason, user)
        payload["fecResumen"] = fiscal_time.iso_lima_wall_time(document.fecha_emision)
        if document.tipo_comprobante in {"07", "08"}:
            reference = document.nota_referencia
            if not reference or reference.tenant_id != document.tenant_id or reference.tipo_comprobante != "03":
                raise ValueError("La nota requiere una boleta de referencia de la misma empresa.")
            payload["details"][0]["docReferencia"] = {
                "tipoDoc": "03", "nroDoc": facturacion_service._document_number(reference)}
        payload["fecGeneracion"] = fiscal_time.iso_lima(now)
    else:
        payload = {
            "company": facturacion_service._build_company_payload(user),
            "fecGeneracion": fiscal_time.iso_lima_wall_time(document.fecha_emision),
            "fecComunicacion": fiscal_time.iso_lima(now),
            "details": [{"tipoDoc": document.tipo_comprobante, "serie": document.serie,
                         "correlativo": str(document.correlativo), "desMotivoBaja": reason}],
        }
    payload["tipoDoc"] = prefix
    payload["correlativo"] = _reserve_counter(db, document.tenant_id, prefix, now.strftime("%Y%m%d"))
    endpoint = "/summary/send" if prefix == "RC" else "/voided/send"
    payload = jsonable_encoder(payload)
    return {
        "motivo": reason, "confirmed_not_delivered": True,
        "void_protocol_version": 1, "void_send_started": False,
        "void_payload": payload, "void_endpoint": endpoint,
        "void_filename": smartpse_ubl_service.build_smartpse_filename(payload),
        "void_xml": facturacion_service._build_smartpse_xml(payload, endpoint),
        "document_number": facturacion_service._document_number(document),
        "requested_at": fiscal_time.iso_lima(now), "requested_by": user.id,
    }


def ensure_manual_batch_available(db, tenant_id, payload):
    """Manual and automatic RC batches share the same serialized namespace."""
    db.query(models.Tenant).filter(models.Tenant.id == tenant_id).with_for_update(key_share=True).one()
    correlativo = payload["correlativo"]
    reserved = db.query(models.DocumentEmissionJob.id).filter(
        models.DocumentEmissionJob.tenant_id == tenant_id,
        models.DocumentEmissionJob.action == models.EMISSION_JOB_ACTION_VOID_FISCAL,
        models.DocumentEmissionJob.payload_snapshot["void_payload"]["tipoDoc"].as_string() == "RC",
        models.DocumentEmissionJob.payload_snapshot["void_payload"]["correlativo"].as_string() == correlativo,
    ).first()
    previous = db.query(models.ResumenDiario.id).filter(
        models.ResumenDiario.tenant_id == tenant_id,
        models.ResumenDiario.correlativo == correlativo,
    ).first()
    if reserved or previous:
        raise ValueError("Este lote de resumen ya está registrado o reservado para una baja. Consulte su resultado; no lo reenvíe.")


def cdr_result(result, payload):
    from services import facturacion_service

    cdr = result.get("cdr_xml") or smartpse_response.extract_cdr_xml(result)
    if not cdr:
        return dict(result, pending=True)
    try:
        root = ET.fromstring(cdr)
        if root.tag.rsplit("}", 1)[-1] != "ApplicationResponse":
            raise smartpse_client.SmartPSEException("El CDR de baja no es una constancia válida.")
        if len(root.findall("cac:DocumentResponse", smartpse_response.NS)) != 1:
            raise smartpse_client.SmartPSEException("El CDR no identifica un único lote de baja.")
        smartpse_response.validate_sale_cdr(cdr, {
            "serie": payload["tipoDoc"], "correlativo": payload["correlativo"], "company": payload["company"]})
    except smartpse_client.SmartPSEDefinitiveRejection as exc:
        raise facturacion_service.FacturacionRejectedException(str(exc), {"cdr": cdr}) from exc
    except (smartpse_client.SmartPSEException, ET.ParseError):
        return dict(result, pending=True, confirmation_error="CDR de baja inválido o de otra identidad; requiere conciliación.")
    return dict(result, success=True, pending=False, cdr_xml=cdr)


def process(db, job, document, user):
    from services import facturacion_service

    snapshot = dict(job.payload_snapshot or {})
    if type(snapshot.get("void_protocol_version")) is not int or snapshot.get("void_protocol_version") != 1:
        raise ValueError("Baja histórica sin lote congelado; requiere revisión, no se reenviará automáticamente.")
    if snapshot.get("confirmed_not_delivered") is not True or type(snapshot.get("void_send_started")) is not bool:
        raise ValueError("La baja no tiene confirmación o evidencia de envío reconocida; requiere revisión.")
    payload = snapshot["void_payload"]
    if (snapshot["document_number"] != facturacion_service._document_number(document)
            or payload["company"]["ruc"] != facturacion_service._build_company_payload(user)["ruc"]
            or snapshot["void_filename"] != smartpse_ubl_service.build_smartpse_filename(payload)):
        raise ValueError("La identidad fiscal cambió; el lote de baja requiere revisión.")
    previous = snapshot.get("void_result") or {}
    if previous.get("cdr_xml"):
        checked = cdr_result(previous, payload)
        if not checked["pending"]:
            return checked
    started = snapshot.get("void_send_started") is True
    if not started:
        validate_document(document, user)
        snapshot["void_send_started"] = True
        job.payload_snapshot = snapshot
        emission_leases.check(db)
        db.commit()  # durable uncertainty fence BEFORE the provider call
    emission_leases.before_provider(db)
    try:
        if started:
            # Demo summary tickets require an explicit environment in the GET
            # body; otherwise the provider returns 404 for the existing batch.
            consult_kwargs = {"extra_payload": {"environment": "demo"}} if facturacion_service._smartpse_demo_mode(user) else {}
            data = smartpse_client.get_default_client().consult_ticket(user.tenant, snapshot["void_filename"], **consult_kwargs)
            result = {
                "success": True, "provider_response": data,
                "cdr_xml": smartpse_response.extract_cdr_xml(data),
                "ticket": data.get("ticket") or job.provider_ticket,
                "provider_endpoint": f"/api/cpe/consultar/{snapshot['void_filename']}",
                "provider_status_code": 200,
            }
        else:
            result = facturacion_service._enviar_a_api(payload, user, snapshot["void_endpoint"],
                poll_async=False, xml_content_override=snapshot["void_xml"])
    except (facturacion_service.FacturacionException, smartpse_client.SmartPSEException) as exc:
        data = getattr(exc, "provider_response", None) or getattr(exc, "response_data", None) or {}
        result = {"success": False, "pending": True, "provider_response": data,
                  "cdr_xml": smartpse_response.extract_cdr_xml(data),
                  "confirmation_error": str(exc), "ticket": data.get("ticket") or job.provider_ticket}
    except Exception as exc:
        # An unexpected transport/parser failure after the durable fence is
        # still uncertainty, never permission to submit the batch again.
        result = {"success": False, "pending": True,
                  "confirmation_error": f"Resultado de baja incierto ({type(exc).__name__}); se consultará sin reenviar."}
    emission_leases.check(db, result)
    snapshot["void_result"] = jsonable_encoder(result)
    job.payload_snapshot = snapshot
    job.provider_ticket = result.get("ticket") or job.provider_ticket
    db.commit()  # retain evidence even when the matching CDR is a rejection
    return cdr_result(result, payload)
