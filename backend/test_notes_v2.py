from decimal import Decimal

import crud
import models
from conftest import make_cliente, make_quote_via_crud, make_tenant, make_user
from schemas.notes import FiscalNoteDraftCreate, NoteAdjustmentLine
from services import note_adjustment_service
from services.document_flow_service import DOCUMENT_STATUS_ISSUED


def _accepted_document(db, suffix="81", *, tipo="01", price="118.00"):
    tenant = make_tenant(db, suffix)
    user = make_user(db, tenant, email=f"notes-{suffix}@inkora.test")
    client = make_cliente(db, tenant, suffix)
    quote = make_quote_via_crud(db, tenant, user, client, precio=price)
    document = crud.create_fiscal_document_from_quote(db, quote, user.id, tipo)
    document.estado = DOCUMENT_STATUS_ISSUED
    db.commit()
    db.refresh(document)
    return tenant, user, document


def _payload(document, **overrides):
    data = {
        "comprobante_afectado_id": document.id,
        "tipo_nota": "credito",
        "cod_motivo": "04",
        "descripcion_motivo": "Descuento comercial pactado",
        "adjustment_mode": "global",
        "input_type": "amount",
        "input_value": Decimal("20.00"),
    }
    data.update(overrides)
    return FiscalNoteDraftCreate(**data)


def test_global_percentage_is_explicit_and_proportional(db_session):
    tenant, _, document = _accepted_document(db_session, "81", price="236.00")
    payload = _payload(document, input_type="percentage", input_value=Decimal("25"))

    _, lines, totals = note_adjustment_service.calculate_adjustment(
        db_session, tenant.id, payload,
    )

    assert totals["total_venta"] == Decimal("59.00")
    assert totals["total_igv"] == Decimal("9.00")
    assert all(line.inventory_source_item_id for line in lines)


def test_boleta_hides_and_rejects_global_discount(db_session):
    tenant, _, document = _accepted_document(db_session, "82", tipo="03")
    context = note_adjustment_service.get_note_context(db_session, tenant.id, document.id)
    assert "04" not in context["allowed_motives"]["credito"]

    try:
        note_adjustment_service.calculate_adjustment(
            db_session, tenant.id, _payload(document),
        )
    except ValueError as exc:
        assert "no aplica" in str(exc)
    else:
        raise AssertionError("La boleta no debe aceptar NC 04")


def test_line_return_cannot_exceed_original_quantity(db_session):
    tenant, _, document = _accepted_document(db_session, "83")
    source = document.items[0]
    payload = _payload(
        document,
        cod_motivo="07",
        adjustment_mode="lines",
        input_type=None,
        input_value=None,
        inventory_impact="undelivered",
        lines=[NoteAdjustmentLine(source_item_id=source.id, quantity=Decimal("2"))],
    )
    try:
        note_adjustment_service.calculate_adjustment(db_session, tenant.id, payload)
    except ValueError as exc:
        assert "maximo devolvible" in str(exc)
    else:
        raise AssertionError("No debe permitir devolver mas de lo facturado")


def test_draft_is_idempotent_and_does_not_consume_correlative(db_session):
    tenant, user, document = _accepted_document(db_session, "84")
    payload = _payload(document)
    first, created = note_adjustment_service.create_draft(
        db_session, tenant.id, user.id, payload, "notes-v2-idempotency",
    )
    second, created_again = note_adjustment_service.create_draft(
        db_session, tenant.id, user.id, payload, "notes-v2-idempotency",
    )

    assert created is True
    assert created_again is False
    assert first.id == second.id
    assert first.estado == "borrador"
    assert first.serie is None
    assert first.correlativo is None


def test_v2_note_never_accepts_success_without_verified_cdr(db_session):
    tenant, user, document = _accepted_document(db_session, "85")
    note, _ = note_adjustment_service.create_draft(
        db_session, tenant.id, user.id, _payload(document), "notes-v2-no-cdr",
    )
    note, _ = note_adjustment_service.assign_number_for_emission(
        db_session, tenant.id, note.id,
    )

    updated = crud.guardar_respuesta_sunat(
        db_session,
        note.id,
        {"success": True, "provider_verification_status": "verified"},
        tenant_id=tenant.id,
    )

    assert updated.estado == "pendiente"
    assert "sin CDR" in updated.sunat_error


def test_debit_penalty_is_inaffecta(db_session):
    tenant, _, document = _accepted_document(db_session, "86")
    payload = _payload(
        document,
        tipo_nota="debito",
        cod_motivo="13",
        descripcion_motivo="Penalidad contractual",
        adjustment_mode="charge",
        input_value=Decimal("25.00"),
    )
    _, lines, totals = note_adjustment_service.calculate_adjustment(db_session, tenant.id, payload)
    assert lines[0].tipo_afectacion_igv == "30"
    assert totals["total_inafecta"] == Decimal("25.00")
    assert totals["total_igv"] == Decimal("0.00")
