"""Audit Smart PSE fiscal evidence without deleting test documents.

Default mode is dry-run. Use --apply only after reviewing the printed report.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime

import models
from database import SessionLocal
from services import smartpse_client
from services.document_flow_service import FISCAL_DOCUMENT_KINDS, DOCUMENT_STATUS_ISSUED


MISSING_REMOTE_MESSAGE = (
    "Smart PSE remote verification missing; document not considered emitted"
)


def _document_number(document: models.Cotizacion) -> str:
    return f"{document.serie}-{str(document.correlativo).zfill(6)}"


def _remote_status(tenant: models.Tenant, document: models.Cotizacion, *, verify_remote: bool) -> str:
    if document.provider_verification_status == "verified":
        return "verified"
    if not verify_remote:
        return document.provider_verification_status or "not_checked"
    if not document.provider_document_name:
        return "missing_provider_document_name"
    try:
        smartpse_client.get_default_client().consult_ticket(tenant, document.provider_document_name)
    except Exception:
        return "remote_missing"
    return "remote_found"


def _audit_document(tenant: models.Tenant, document: models.Cotizacion, *, verify_remote: bool) -> dict:
    remote_status = _remote_status(tenant, document, verify_remote=verify_remote)
    local_accepted = (
        document.estado == DOCUMENT_STATUS_ISSUED
        and bool(document.sunat_cdr_content or document.sunat_cdr_url)
        and not document.sunat_error
    )
    evidence_ok = remote_status in {"verified", "remote_found"}
    return {
        "id": document.id,
        "number": _document_number(document),
        "tipo_comprobante": document.tipo_comprobante,
        "estado": document.estado,
        "local_accepted": local_accepted,
        "remote_status": remote_status,
        "provider_document_name": document.provider_document_name,
        "has_xml": bool(document.sunat_xml_content or document.sunat_xml_url),
        "has_cdr": bool(document.sunat_cdr_content or document.sunat_cdr_url),
        "has_pdf": bool(document.sunat_pdf_url),
        "needs_repair": bool(local_accepted and not evidence_ok),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ruc", default="20606751509")
    parser.add_argument("--verify-remote", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        tenant = db.query(models.Tenant).filter(models.Tenant.business_ruc == args.ruc).first()
        if not tenant:
            print(json.dumps({"ok": False, "error": "tenant_not_found", "ruc": args.ruc}, indent=2))
            return 1

        documents = (
            db.query(models.Cotizacion)
            .filter(
                models.Cotizacion.tenant_id == tenant.id,
                models.Cotizacion.document_kind.in_(FISCAL_DOCUMENT_KINDS),
            )
            .order_by(models.Cotizacion.id.asc())
            .all()
        )
        report = [
            _audit_document(tenant, document, verify_remote=args.verify_remote)
            for document in documents
        ]

        if args.apply:
            repaired_ids = {entry["id"] for entry in report if entry["needs_repair"]}
            for document in documents:
                if document.id not in repaired_ids:
                    continue
                document.provider_verification_status = "failed"
                document.provider_verified_at = None
                document.sunat_error = MISSING_REMOTE_MESSAGE
                document.cdr_artifact_status = document.cdr_artifact_status or "failed"
                document.pdf_artifact_status = document.pdf_artifact_status or "failed"
            db.commit()

        print(json.dumps({
            "ok": True,
            "mode": "apply" if args.apply else "dry-run",
            "ruc": args.ruc,
            "tenant_id": tenant.id,
            "generated_at": datetime.now().isoformat(),
            "total": len(report),
            "needs_repair": sum(1 for entry in report if entry["needs_repair"]),
            "items": report,
        }, indent=2, ensure_ascii=False))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
