from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
import traceback
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
os.chdir(BACKEND_DIR)
sys.path.insert(0, str(BACKEND_DIR))

from database import SessionLocal  # noqa: E402
import crud  # noqa: E402
import models  # noqa: E402
import schemas  # noqa: E402
from services import facturacion_service  # noqa: E402
from services import pdf_generator  # noqa: E402


LIMA_TZ = ZoneInfo("America/Lima")
EMISOR_RUC = "20606751509"
PRICE_WITH_IGV = Decimal("118.00")
PDF_TIMEOUT = 90
QR_TIMEOUT = 60

CUSTOMERS = [
    {"name": "Exituno S.A.C.", "ruc": "20153270814"},
    {"name": "EMUSA Perú S.A.C.", "ruc": "20508998201"},
    {"name": "Industria Gráfica Cimagraf S.A.C.", "ruc": "20508998193"},
    {"name": "Quad/Graphics Perú S.R.L.", "ruc": "20508998195"},
    {"name": "Metrocolor S.A.", "ruc": "20100070970"},
    {"name": "Enotria S.A.", "ruc": "20100070971"},
    {"name": "Perú Offset Digital S.A.C.", "ruc": "20508998205"},
    {"name": "Corporación Grafissa S.A.C.", "ruc": "20508998207"},
    {"name": "Amauta Impresiones Comerciales S.A.C.", "ruc": "20508998209"},
    {"name": "Corporación Gráfica Universal S.A.C.", "ruc": "20508998211"},
    {"name": "Dicomsa S.A.", "ruc": "20100070972"},
    {"name": "Lettera Gráfica S.A.C.", "ruc": "20508998213"},
    {"name": "Gráfica Biblos S.A.C.", "ruc": "20508998215"},
    {"name": "Imprenta Yanes S.A.C.", "ruc": "20508998217"},
    {"name": "Gráfica Horizonte S.A.C.", "ruc": "20508998219"},
    {"name": "Impresiones Digitales Prisma S.A.C.", "ruc": "20508998221"},
    {"name": "Gráfica Andina S.A.C.", "ruc": "20508998223"},
    {"name": "Imprenta San Marcos S.A.C.", "ruc": "20508998225"},
    {"name": "Gráfica Continental S.A.C.", "ruc": "20508998227"},
    {"name": "Impresiones Modernas S.A.C.", "ruc": "20508998229"},
]

FAMILIES = [
    "boleta",
    "factura",
    "nota_credito",
    "nota_debito",
    "baja_factura",
    "retencion",
    "percepcion",
    "reversion",
]


def lima_now() -> datetime:
    return datetime.now(LIMA_TZ)


def now_iso() -> str:
    return lima_now().replace(microsecond=0).isoformat()


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def write_bytes(path: Path, data: bytes) -> None:
    path.write_bytes(data)


def decode_b64(data: str | None) -> bytes | None:
    if not data:
        return None
    return base64.b64decode(data)


def get_context():
    db = SessionLocal()
    tenant = (
        db.query(models.Tenant)
        .filter(models.Tenant.business_ruc == EMISOR_RUC)
        .first()
    )
    if not tenant:
        raise RuntimeError(f"No existe tenant emisor con RUC {EMISOR_RUC}")

    user = (
        db.query(models.User)
        .filter(models.User.tenant_id == tenant.id, models.User.is_superadmin.is_(False))
        .order_by(models.User.id.asc())
        .first()
    )
    if not user:
        user = (
            db.query(models.User)
            .filter(models.User.tenant_id == tenant.id)
            .order_by(models.User.id.asc())
            .first()
        )
    if not user:
        raise RuntimeError("No existe usuario asociado al tenant emisor")
    return db, tenant, user


def upsert_customer(db, tenant: models.Tenant, item: dict[str, str]):
    customer = (
        db.query(models.Cliente)
        .filter(
            models.Cliente.tenant_id == tenant.id,
            models.Cliente.numero_documento == item["ruc"],
        )
        .first()
    )
    payload = {
        "tipo_documento": "6",
        "numero_documento": item["ruc"],
        "razon_social": item["name"],
        "nombre_comercial": item["name"],
        "direccion": f"Direccion referencial cliente {item['ruc']}",
        "ubigeo": "150101",
        "email": None,
        "telefono": None,
        "whatsapp": None,
        "contacto": None,
        "condicion_pago": "contado",
        "direccion_entrega": f"Direccion referencial cliente {item['ruc']}",
        "observaciones": "Cliente de pruebas backend beta",
    }
    if customer:
        for key, value in payload.items():
            setattr(customer, key, value)
        db.commit()
        db.refresh(customer)
        return customer

    return crud.create_cliente(db, schemas.ClienteCreate(**payload), tenant.id)


def create_quote(db, tenant: models.Tenant, user: models.User, customer: models.Cliente, description: str):
    payload = schemas.CotizacionCreate(
        cliente_id=customer.id,
        moneda="PEN",
        tipo_comprobante="00",
        observaciones="Prueba backend beta",
        items=[
            schemas.CotizacionItemCreate(
                descripcion=description,
                cantidad=Decimal("1"),
                precio_unitario=PRICE_WITH_IGV,
                unidad_medida="NIU",
                tipo_afectacion_igv="10",
            )
        ],
    )
    return crud.create_cotizacion(db, payload, user.id, tenant.id)


def build_qr_payload(comprobante, customer: models.Cliente) -> dict[str, Any]:
    return {
        "ruc": EMISOR_RUC,
        "tipo": comprobante.tipo_comprobante,
        "serie": comprobante.serie,
        "numero": str(comprobante.correlativo),
        "emision": comprobante.fecha_emision.date().isoformat(),
        "igv": float(comprobante.total_igv or 0),
        "total": float(comprobante.total_venta or 0),
        "clienteTipo": customer.tipo_documento,
        "clienteNumero": customer.numero_documento,
    }


def build_voided_payload(documento, user: models.User, motivo: str, correlativo: str) -> dict[str, Any]:
    now = now_iso()
    later = (lima_now() + timedelta(minutes=1)).replace(microsecond=0).isoformat()
    return {
        "correlativo": correlativo,
        "fecGeneracion": now,
        "fecComunicacion": later,
        "company": facturacion_service._build_company_payload(user),
        "details": [
            {
                "tipoDoc": documento.tipo_comprobante,
                "serie": documento.serie,
                "correlativo": str(documento.correlativo).zfill(6),
                "desMotivoBaja": motivo,
            }
        ],
    }


def build_retencion_payload(
    user: models.User,
    counterparty: dict[str, str],
    invoice_number: str,
    correlativo: str,
) -> dict[str, Any]:
    ts = now_iso()
    return {
        "serie": "R001",
        "correlativo": correlativo,
        "fechaEmision": ts,
        "company": facturacion_service._build_company_payload(user),
        "proveedor": {
            "tipoDoc": "6",
            "numDoc": counterparty["ruc"],
            "rznSocial": counterparty["name"],
            "address": {
                "direccion": f"Direccion referencial proveedor {counterparty['ruc']}",
                "provincia": "LIMA",
                "departamento": "LIMA",
                "distrito": "LIMA",
                "ubigueo": "150101",
            },
        },
        "observacion": "RETENCION DE PRUEBA BACKEND BETA",
        "impRetenido": 3.54,
        "impPagado": 118.0,
        "regimen": "01",
        "tasa": 3,
        "details": [
            {
                "tipoDoc": "01",
                "numDoc": invoice_number,
                "fechaEmision": ts,
                "fechaRetencion": ts,
                "moneda": "PEN",
                "impTotal": 118.0,
                "impPagar": 118.0,
                "impRetenido": 3.54,
                "pagos": [
                    {
                        "moneda": "PEN",
                        "importe": 118.0,
                        "fecha": ts,
                    }
                ],
                "tipoCambio": {
                    "fecha": ts,
                    "factor": 1,
                    "monedaObj": "PEN",
                    "monedaRef": "PEN",
                },
            }
        ],
    }


def build_percepcion_payload(
    user: models.User,
    counterparty: dict[str, str],
    invoice_number: str,
    correlativo: str,
) -> dict[str, Any]:
    ts = now_iso()
    return {
        "serie": "P001",
        "correlativo": correlativo,
        "fechaEmision": ts,
        "observacion": "PERCEPCION DE PRUEBA BACKEND BETA",
        "company": facturacion_service._build_company_payload(user),
        "proveedor": {
            "tipoDoc": "6",
            "numDoc": counterparty["ruc"],
            "rznSocial": counterparty["name"],
            "address": {
                "direccion": f"Direccion referencial proveedor {counterparty['ruc']}",
                "provincia": "LIMA",
                "departamento": "LIMA",
                "distrito": "LIMA",
                "ubigueo": "150101",
            },
        },
        "impPercibido": 2.36,
        "impCobrado": 120.36,
        "regimen": "01",
        "tasa": 2,
        "details": [
            {
                "tipoDoc": "01",
                "numDoc": invoice_number,
                "fechaEmision": ts,
                "fechaPercepcion": ts,
                "moneda": "PEN",
                "impTotal": 118.0,
                "impCobrar": 120.36,
                "impPercibido": 2.36,
                "cobros": [
                    {
                        "moneda": "PEN",
                        "fecha": ts,
                        "importe": 120.36,
                    }
                ],
                "tipoCambio": {
                    "fecha": ts,
                    "factor": 1,
                    "monedaObj": "PEN",
                    "monedaRef": "PEN",
                },
            }
        ],
    }


def build_reversion_payload(
    user: models.User,
    ret_number: str,
    perc_number: str,
    correlativo: str,
) -> dict[str, Any]:
    now = now_iso()
    later = (lima_now() + timedelta(minutes=2)).replace(microsecond=0).isoformat()
    return {
        "correlativo": correlativo,
        "fecGeneracion": now,
        "fecComunicacion": later,
        "company": facturacion_service._build_company_payload(user),
        "details": [
            {
                "tipoDoc": "20",
                "serie": ret_number.split("-")[0],
                "correlativo": ret_number.split("-")[1],
                "desMotivoBaja": "ERROR DE SISTEMA",
            },
            {
                "tipoDoc": "40",
                "serie": perc_number.split("-")[0],
                "correlativo": perc_number.split("-")[1],
                "desMotivoBaja": "ERROR DE SISTEMA",
            },
        ],
    }


def provider_binary_post(user: models.User, endpoint: str, payload: dict[str, Any]):
    import requests

    url = f"{facturacion_service._get_api_base_url(user)}{endpoint}"
    response = requests.post(
        url,
        data=json.dumps(payload, cls=facturacion_service.SUNATDecimalEncoder),
        headers=facturacion_service._provider_request_headers(facturacion_service._get_apisperu_token(user)),
        timeout=PDF_TIMEOUT,
        stream=True,
    )
    return response


def provider_qr_post(user: models.User, payload: dict[str, Any]):
    import requests

    url = f"{facturacion_service._get_api_base_url(user)}/sale/qr"
    response = requests.post(
        url,
        data=json.dumps(payload, cls=facturacion_service.SUNATDecimalEncoder),
        headers=facturacion_service._provider_request_headers(facturacion_service._get_apisperu_token(user)),
        timeout=QR_TIMEOUT,
        stream=True,
    )
    return response


def save_binary_artifact(case_dir: Path, user: models.User, endpoint: str, payload: dict[str, Any], filename: str) -> dict[str, Any]:
    response = provider_binary_post(user, endpoint, payload)
    meta = {
        "status_code": response.status_code,
        "content_type": response.headers.get("Content-Type"),
        "content_length": len(response.content),
    }
    write_json(case_dir / f"{filename}_meta.json", meta)
    if response.status_code < 400 and response.content:
        ext = "pdf" if "pdf" in endpoint else "xml"
        write_bytes(case_dir / f"{filename}.{ext}", response.content)
    else:
        body = response.text if response.text else ""
        write_text(case_dir / f"{filename}_error.txt", body)
    return meta


def save_inkora_pdf(case_dir: Path, document, tenant: models.Tenant) -> dict[str, Any]:
    buffer = pdf_generator.create_comprobante_pdf(document, tenant)
    content = buffer.getvalue()
    write_bytes(case_dir / "pdf_inkora.pdf", content)
    meta = {
        "content_length": len(content),
        "source": "inkora_custom_renderer",
        "uses_official_xml": bool(getattr(document, "sunat_xml_content", None)),
        "uses_official_qr_svg": bool(getattr(document, "sunat_qr_svg", None)),
    }
    write_json(case_dir / "pdf_inkora_meta.json", meta)
    return meta


def save_qr_artifact(case_dir: Path, user: models.User, payload: dict[str, Any]) -> dict[str, Any]:
    response = provider_qr_post(user, payload)
    meta = {
        "status_code": response.status_code,
        "content_type": response.headers.get("Content-Type"),
        "content_length": len(response.content),
    }
    write_json(case_dir / "qr_response_meta.json", meta)
    if response.status_code < 400 and response.content:
        write_json(case_dir / "qr_request.json", payload)
        if "svg" in (response.headers.get("Content-Type") or "").lower():
            write_bytes(case_dir / "qr.svg", response.content)
        else:
            write_bytes(case_dir / "qr.bin", response.content)
    else:
        write_text(case_dir / "qr_error.txt", response.text)
    return meta


def save_common_case_files(case_dir: Path, payload: dict[str, Any], result: dict[str, Any]) -> None:
    write_json(case_dir / "payload.json", payload)
    write_json(case_dir / "emission_result.json", result)
    xml = result.get("xml")
    if xml:
        write_text(case_dir / "xml.xml", xml)
    cdr_zip = decode_b64(result.get("cdr_zip_base64"))
    if cdr_zip:
        write_bytes(case_dir / "cdr.zip", cdr_zip)
    else:
        write_text(case_dir / "cdr_no_aplica.txt", "No se obtuvo CDR en la respuesta normalizada.")


def mark_no_qr(case_dir: Path) -> None:
    write_text(case_dir / "qr_no_aplica.txt", "QR no aplica para esta familia documental.")


def case_name(index: int, item: dict[str, str]) -> str:
    return f"{index:02d}_{item['ruc']}"


def run_boleta_case(db, tenant, user, item, family_dir: Path, index: int) -> dict[str, Any]:
    customer = upsert_customer(db, tenant, item)
    quote = create_quote(db, tenant, user, customer, f"BOLETA PRUEBA {item['ruc']}")
    doc = crud.create_fiscal_document_from_quote(db, quote, user.id, "03")
    result = facturacion_service.emitir_factura(doc, db, user, tipo_doc_override="03")
    crud.guardar_respuesta_sunat(db, doc.id, result, tenant_id=tenant.id)

    payload = facturacion_service._build_download_payload(doc, user)
    case_dir = ensure_dir(family_dir / case_name(index, item))
    save_common_case_files(case_dir, payload, result)
    save_binary_artifact(case_dir, user, "/invoice/pdf", payload, "pdf_apis")
    save_qr_artifact(case_dir, user, build_qr_payload(doc, customer))
    save_inkora_pdf(case_dir, doc, tenant)
    write_json(case_dir / "document_reference.json", {"id": doc.id, "document_number": f"{doc.serie}-{str(doc.correlativo).zfill(6)}"})
    return {"success": True, "document_number": f"{doc.serie}-{str(doc.correlativo).zfill(6)}"}


def run_factura_case(db, tenant, user, item, family_dir: Path, index: int) -> dict[str, Any]:
    customer = upsert_customer(db, tenant, item)
    quote = create_quote(db, tenant, user, customer, f"FACTURA PRUEBA {item['ruc']}")
    doc = crud.create_fiscal_document_from_quote(db, quote, user.id, "01")
    result = facturacion_service.emitir_factura(doc, db, user, tipo_doc_override="01")
    crud.guardar_respuesta_sunat(db, doc.id, result, tenant_id=tenant.id)

    payload = facturacion_service._build_download_payload(doc, user)
    case_dir = ensure_dir(family_dir / case_name(index, item))
    save_common_case_files(case_dir, payload, result)
    save_binary_artifact(case_dir, user, "/invoice/pdf", payload, "pdf_apis")
    save_qr_artifact(case_dir, user, build_qr_payload(doc, customer))
    save_inkora_pdf(case_dir, doc, tenant)
    write_json(case_dir / "document_reference.json", {"id": doc.id, "document_number": f"{doc.serie}-{str(doc.correlativo).zfill(6)}"})
    return {"success": True, "document_number": f"{doc.serie}-{str(doc.correlativo).zfill(6)}"}


def run_nota_credito_case(db, tenant, user, item, family_dir: Path, index: int) -> dict[str, Any]:
    customer = upsert_customer(db, tenant, item)
    quote = create_quote(db, tenant, user, customer, f"BASE NC PRUEBA {item['ruc']}")
    base_doc = crud.create_fiscal_document_from_quote(db, quote, user.id, "03")
    base_result = facturacion_service.emitir_factura(base_doc, db, user, tipo_doc_override="03")
    crud.guardar_respuesta_sunat(db, base_doc.id, base_result, tenant_id=tenant.id)

    note = crud.crear_nota_credito_debito(
        db,
        base_doc,
        user.id,
        "credito",
        "01",
        "ANULACION DE LA OPERACION DE PRUEBA",
    )
    result = facturacion_service.emitir_nota(
        note,
        base_doc,
        user,
        "01",
        "ANULACION DE LA OPERACION DE PRUEBA",
        "credito",
    )
    crud.guardar_respuesta_sunat(db, note.id, result, tenant_id=tenant.id)

    payload = facturacion_service._build_download_payload(note, user)
    case_dir = ensure_dir(family_dir / case_name(index, item))
    save_common_case_files(case_dir, payload, result)
    save_binary_artifact(case_dir, user, "/note/pdf", payload, "pdf_apis")
    save_qr_artifact(case_dir, user, build_qr_payload(note, customer))
    save_inkora_pdf(case_dir, note, tenant)
    write_json(
        case_dir / "base_document_reference.json",
        {"id": base_doc.id, "document_number": f"{base_doc.serie}-{str(base_doc.correlativo).zfill(6)}"},
    )
    return {"success": True, "document_number": f"{note.serie}-{str(note.correlativo).zfill(6)}"}


def run_nota_debito_case(db, tenant, user, item, family_dir: Path, index: int) -> dict[str, Any]:
    customer = upsert_customer(db, tenant, item)
    quote = create_quote(db, tenant, user, customer, f"BASE ND PRUEBA {item['ruc']}")
    base_doc = crud.create_fiscal_document_from_quote(db, quote, user.id, "01")
    base_result = facturacion_service.emitir_factura(base_doc, db, user, tipo_doc_override="01")
    crud.guardar_respuesta_sunat(db, base_doc.id, base_result, tenant_id=tenant.id)

    note = crud.crear_nota_credito_debito(
        db,
        base_doc,
        user.id,
        "debito",
        "02",
        "AUMENTO DE VALOR DE PRUEBA",
    )
    result = facturacion_service.emitir_nota(
        note,
        base_doc,
        user,
        "02",
        "AUMENTO DE VALOR DE PRUEBA",
        "debito",
    )
    crud.guardar_respuesta_sunat(db, note.id, result, tenant_id=tenant.id)

    payload = facturacion_service._build_download_payload(note, user)
    case_dir = ensure_dir(family_dir / case_name(index, item))
    save_common_case_files(case_dir, payload, result)
    save_binary_artifact(case_dir, user, "/note/pdf", payload, "pdf_apis")
    save_qr_artifact(case_dir, user, build_qr_payload(note, customer))
    save_inkora_pdf(case_dir, note, tenant)
    write_json(
        case_dir / "base_document_reference.json",
        {"id": base_doc.id, "document_number": f"{base_doc.serie}-{str(base_doc.correlativo).zfill(6)}"},
    )
    return {"success": True, "document_number": f"{note.serie}-{str(note.correlativo).zfill(6)}"}


def run_baja_factura_case(db, tenant, user, item, family_dir: Path, index: int) -> dict[str, Any]:
    customer = upsert_customer(db, tenant, item)
    quote = create_quote(db, tenant, user, customer, f"BASE BAJA PRUEBA {item['ruc']}")
    base_doc = crud.create_fiscal_document_from_quote(db, quote, user.id, "01")
    base_result = facturacion_service.emitir_factura(base_doc, db, user, tipo_doc_override="01")
    crud.guardar_respuesta_sunat(db, base_doc.id, base_result, tenant_id=tenant.id)

    correlativo = str(90000 + index)
    payload = build_voided_payload(base_doc, user, "ERROR DE SISTEMA DE PRUEBA", correlativo)
    result = facturacion_service.emitir_comunicacion_baja(payload, user)
    crud.anular_cotizacion(db, base_doc.id, tenant_id=tenant.id)

    case_dir = ensure_dir(family_dir / case_name(index, item))
    save_common_case_files(case_dir, payload, result)
    save_binary_artifact(case_dir, user, "/voided/pdf", payload, "pdf")
    mark_no_qr(case_dir)
    write_json(
        case_dir / "base_document_reference.json",
        {"id": base_doc.id, "document_number": f"{base_doc.serie}-{str(base_doc.correlativo).zfill(6)}"},
    )
    return {"success": True, "document_number": f"RA-{correlativo}"}


def emit_support_invoice(db, tenant, user, customer, description: str):
    quote = create_quote(db, tenant, user, customer, description)
    doc = crud.create_fiscal_document_from_quote(db, quote, user.id, "01")
    result = facturacion_service.emitir_factura(doc, db, user, tipo_doc_override="01")
    crud.guardar_respuesta_sunat(db, doc.id, result, tenant_id=tenant.id)
    return doc, result


def run_retencion_case(db, tenant, user, item, family_dir: Path, index: int) -> dict[str, Any]:
    customer = upsert_customer(db, tenant, item)
    base_doc, _ = emit_support_invoice(db, tenant, user, customer, f"BASE RET PRUEBA {item['ruc']}")
    correlativo = str(91000 + index)
    payload = build_retencion_payload(
        user,
        item,
        f"{base_doc.serie}-{str(base_doc.correlativo).zfill(6)}",
        correlativo,
    )
    result = facturacion_service.emitir_retencion(payload, user)

    case_dir = ensure_dir(family_dir / case_name(index, item))
    save_common_case_files(case_dir, payload, result)
    save_binary_artifact(case_dir, user, "/retention/pdf", payload, "pdf")
    mark_no_qr(case_dir)
    write_json(
        case_dir / "base_document_reference.json",
        {"id": base_doc.id, "document_number": f"{base_doc.serie}-{str(base_doc.correlativo).zfill(6)}"},
    )
    return {"success": True, "document_number": f"R001-{correlativo}"}


def run_percepcion_case(db, tenant, user, item, family_dir: Path, index: int) -> dict[str, Any]:
    customer = upsert_customer(db, tenant, item)
    base_doc, _ = emit_support_invoice(db, tenant, user, customer, f"BASE PERC PRUEBA {item['ruc']}")
    correlativo = str(92000 + index)
    payload = build_percepcion_payload(
        user,
        item,
        f"{base_doc.serie}-{str(base_doc.correlativo).zfill(6)}",
        correlativo,
    )
    result = facturacion_service.emitir_percepcion(payload, user)

    case_dir = ensure_dir(family_dir / case_name(index, item))
    save_common_case_files(case_dir, payload, result)
    save_binary_artifact(case_dir, user, "/perception/pdf", payload, "pdf")
    mark_no_qr(case_dir)
    write_json(
        case_dir / "base_document_reference.json",
        {"id": base_doc.id, "document_number": f"{base_doc.serie}-{str(base_doc.correlativo).zfill(6)}"},
    )
    return {"success": True, "document_number": f"P001-{correlativo}"}


def run_reversion_case(db, tenant, user, item, family_dir: Path, index: int) -> dict[str, Any]:
    customer = upsert_customer(db, tenant, item)
    base_ret_doc, _ = emit_support_invoice(db, tenant, user, customer, f"BASE REV RET PRUEBA {item['ruc']}")
    ret_payload = build_retencion_payload(
        user,
        item,
        f"{base_ret_doc.serie}-{str(base_ret_doc.correlativo).zfill(6)}",
        str(93000 + index),
    )
    ret_result = facturacion_service.emitir_retencion(ret_payload, user)

    base_perc_doc, _ = emit_support_invoice(db, tenant, user, customer, f"BASE REV PERC PRUEBA {item['ruc']}")
    perc_payload = build_percepcion_payload(
        user,
        item,
        f"{base_perc_doc.serie}-{str(base_perc_doc.correlativo).zfill(6)}",
        str(94000 + index),
    )
    perc_result = facturacion_service.emitir_percepcion(perc_payload, user)

    payload = build_reversion_payload(
        user,
        f"R001-{str(93000 + index)}",
        f"P001-{str(94000 + index)}",
        str(95000 + index),
    )
    result = facturacion_service.emitir_reversion(payload, user)

    case_dir = ensure_dir(family_dir / case_name(index, item))
    save_common_case_files(case_dir, payload, result)
    save_binary_artifact(case_dir, user, "/reversion/pdf", payload, "pdf")
    mark_no_qr(case_dir)
    write_json(
        case_dir / "base_documents_reference.json",
        {
            "retention_document": f"R001-{str(93000 + index)}",
            "perception_document": f"P001-{str(94000 + index)}",
            "retention_result": ret_result,
            "perception_result": perc_result,
            "retention_base_invoice": f"{base_ret_doc.serie}-{str(base_ret_doc.correlativo).zfill(6)}",
            "perception_base_invoice": f"{base_perc_doc.serie}-{str(base_perc_doc.correlativo).zfill(6)}",
        },
    )
    return {"success": True, "document_number": f"RR-{str(95000 + index)}"}


RUNNERS = {
    "boleta": run_boleta_case,
    "factura": run_factura_case,
    "nota_credito": run_nota_credito_case,
    "nota_debito": run_nota_debito_case,
    "baja_factura": run_baja_factura_case,
    "retencion": run_retencion_case,
    "percepcion": run_percepcion_case,
    "reversion": run_reversion_case,
}


def build_observation_text() -> str:
    today = lima_now().strftime("%Y-%m-%d")
    return (
        f"Observaciones de la bateria backend beta ejecutada el {today}\n\n"
        "- Se excluyo guia de remision porque /despatch/send sigue fallando en Beta Sunat por problema del proveedor.\n"
        "- Se excluyo resumen diario porque /summary/send sigue generando XML invalido en Beta Sunat "
        "(sin <cbc:Percent> para IGV) aun cuando /summary/pdf si responde.\n"
        "- Esta bateria cubre solo documentos que hoy si pueden emitirse desde el backend en Beta Sunat.\n"
    )


def main():
    parser = argparse.ArgumentParser(description="Bateria real backend -> ApisPeru Beta")
    parser.add_argument("--limit", type=int, default=20, help="Numero de casos por familia")
    parser.add_argument("--start-index", type=int, default=1, help="Indice inicial 1-based sobre la lista de RUCs")
    parser.add_argument(
        "--families",
        nargs="*",
        choices=FAMILIES,
        default=FAMILIES,
        help="Familias a ejecutar",
    )
    args = parser.parse_args()

    started = lima_now()
    output_root = ensure_dir(ROOT_DIR / "pruebas" / f"backend_beta_suite_{started:%Y%m%d_%H%M%S}")
    write_text(output_root / "OBSERVACIONES_BETA.txt", build_observation_text())

    manifest: dict[str, Any] = {
        "started_at": started.isoformat(),
        "emisor_ruc": EMISOR_RUC,
        "families": {},
        "skipped_in_beta": ["guia_remision", "summary_send"],
        "limit_per_family": args.limit,
    }

    selected_customers = CUSTOMERS[args.start_index - 1 : args.start_index - 1 + args.limit]

    for family in args.families:
        family_dir = ensure_dir(output_root / family)
        results = []
        ok = 0
        fail = 0
        for offset, item in enumerate(selected_customers, start=args.start_index):
            case_dir = ensure_dir(family_dir / case_name(offset, item))
            started_case = time.time()
            db = None
            try:
                db, tenant, user = get_context()
                result = RUNNERS[family](db, tenant, user, item, family_dir, offset)
                duration = round(time.time() - started_case, 2)
                results.append(
                    {
                        "case": case_name(offset, item),
                        "ruc": item["ruc"],
                        "name": item["name"],
                        "success": True,
                        "duration_seconds": duration,
                        **result,
                    }
                )
                ok += 1
            except Exception as exc:
                duration = round(time.time() - started_case, 2)
                fail += 1
                error_payload = {
                    "case": case_name(offset, item),
                    "ruc": item["ruc"],
                    "name": item["name"],
                    "success": False,
                    "duration_seconds": duration,
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                }
                write_json(case_dir / "error.json", error_payload)
                results.append(error_payload)
                if db is not None:
                    db.rollback()
            finally:
                if db is not None:
                    db.close()

        family_summary = {
            "ok": ok,
            "fail": fail,
            "cases": results,
        }
        manifest["families"][family] = family_summary
        write_json(family_dir / "summary.json", family_summary)

    finished = lima_now()
    manifest["finished_at"] = finished.isoformat()
    manifest["duration_seconds"] = round((finished - started).total_seconds(), 2)
    write_json(output_root / "manifest.json", manifest)
    print(json.dumps({"output_root": str(output_root), "duration_seconds": manifest["duration_seconds"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
