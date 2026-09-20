from __future__ import annotations

import argparse
from datetime import datetime, timezone

import models
from database import SessionLocal
from services.document_flow_service import DOCUMENT_STATUS_ISSUED, DOCUMENT_STATUS_PENDING


DEFAULT_ERROR = "Smart PSE remote verification missing; document not considered emitted"


def _document_number(document) -> str:
    serie = document.serie or ""
    correlativo = str(document.correlativo or "").zfill(6)
    return f"{serie}-{correlativo}" if serie else correlativo


def _query_candidates(db, ruc: str | None):
    query = (
        db.query(models.Cotizacion)
        .join(models.Tenant, models.Cotizacion.tenant_id == models.Tenant.id)
        .filter(
            models.Cotizacion.estado == DOCUMENT_STATUS_ISSUED,
            models.Cotizacion.document_kind.in_(["fiscal_document", "credit_note", "debit_note"]),
            models.Cotizacion.provider_endpoint.like("/api/cpe/%"),
            (
                models.Cotizacion.provider_verification_status.is_(None)
                | (models.Cotizacion.provider_verification_status != "verified")
            ),
        )
        .order_by(models.Cotizacion.id.asc())
    )
    if ruc:
        query = query.filter(models.Tenant.business_ruc == ruc)
    return query.all()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit Smart PSE fiscal documents marked as issued without remote verification."
    )
    parser.add_argument("--ruc", default="20606751509", help="Tenant RUC to audit. Use empty value for all tenants.")
    parser.add_argument("--apply", action="store_true", help="Mark inconsistent documents as pending.")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        ruc = (args.ruc or "").strip() or None
        candidates = _query_candidates(db, ruc)
        print(f"smartpse_audit candidates={len(candidates)} ruc={ruc or 'ALL'} apply={args.apply}")
        for document in candidates:
            print(
                "document "
                f"id={document.id} tenant_id={document.tenant_id} number={_document_number(document)} "
                f"status={document.estado} verification={document.provider_verification_status or 'missing'} "
                f"provider_document_name={document.provider_document_name or 'missing'}"
            )
            if args.apply:
                document.estado = DOCUMENT_STATUS_PENDING
                document.sunat_error = DEFAULT_ERROR
                document.provider_verification_status = document.provider_verification_status or "failed"
                document.provider_verification_error = DEFAULT_ERROR
                document.provider_verified_at = None
        if args.apply:
            db.commit()
            print(f"smartpse_audit applied_at={datetime.now(timezone.utc).isoformat(timespec='seconds')}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
