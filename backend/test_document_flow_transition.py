from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import crud
import models
import schemas


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    models.Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        models.Base.metadata.drop_all(bind=engine)


def _create_tenant(db_session, suffix: str):
    tenant = models.Tenant(
        business_name=f"Tenant {suffix}",
        business_ruc=f"209000000{suffix.zfill(2)}",
    )
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    return tenant


def _create_user(db_session, tenant, suffix: str):
    user = models.User(
        email=f"user-{suffix}@test.com",
        hashed_password="hashed",
        nombre_completo=f"User {suffix}",
        rol="admin",
        tenant_id=tenant.id,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return crud.get_user_by_id(db_session, user.id)


def _create_cliente(db_session, tenant, suffix: str):
    cliente = models.Cliente(
        tenant_id=tenant.id,
        tipo_documento="6",
        numero_documento=f"104500000{suffix.zfill(2)}",
        razon_social=f"Cliente {suffix}",
        direccion="Av. Lima 123",
    )
    db_session.add(cliente)
    db_session.commit()
    db_session.refresh(cliente)
    return cliente


def _create_quote(db_session, tenant, user, cliente):
    payload = schemas.CotizacionCreate(
        cliente_id=cliente.id,
        fecha_vencimiento=datetime.now(timezone.utc),
        moneda="PEN",
        tipo_comprobante="00",
        items=[
            schemas.CotizacionItemCreate(
                descripcion="Impresion de volantes",
                cantidad=Decimal("2"),
                precio_unitario=Decimal("59.00"),
            )
        ],
    )
    return crud.create_cotizacion(db_session, payload, user.id, tenant.id)


def test_quote_has_explicit_document_identity(db_session):
    tenant = _create_tenant(db_session, "21")
    user = _create_user(db_session, tenant, "21")
    cliente = _create_cliente(db_session, tenant, "21")

    quote = _create_quote(db_session, tenant, user, cliente)

    assert quote.document_kind == "quotation"
    assert quote.source_quote_id is None
    assert quote.internal_order_number.startswith("ORD-")
    assert quote.linked_fiscal_document_id is None


def test_fiscal_document_is_created_as_separate_record(db_session):
    tenant = _create_tenant(db_session, "22")
    user = _create_user(db_session, tenant, "22")
    cliente = _create_cliente(db_session, tenant, "22")

    quote = _create_quote(db_session, tenant, user, cliente)
    fiscal_document = crud.create_fiscal_document_from_quote(
        db_session,
        quote,
        user.id,
        "01",
    )

    db_session.refresh(quote)

    assert fiscal_document.id != quote.id
    assert fiscal_document.document_kind == "fiscal_document"
    assert fiscal_document.source_quote_id == quote.id
    assert fiscal_document.internal_order_number == quote.internal_order_number
    assert quote.document_kind == "quotation"
    assert quote.source_quote_id is None
    assert quote.linked_fiscal_document_id == fiscal_document.id


def test_credit_note_inherits_traceability_from_fiscal_document(db_session):
    tenant = _create_tenant(db_session, "23")
    user = _create_user(db_session, tenant, "23")
    cliente = _create_cliente(db_session, tenant, "23")

    quote = _create_quote(db_session, tenant, user, cliente)
    fiscal_document = crud.create_fiscal_document_from_quote(
        db_session,
        quote,
        user.id,
        "01",
    )
    fiscal_document.estado = "facturada"
    db_session.commit()
    note = crud.crear_nota_credito_debito(
        db=db_session,
        doc_afectado=fiscal_document,
        usuario_id=user.id,
        tipo_nota="credito",
        cod_motivo="01",
        descripcion_motivo="Anulacion parcial",
    )

    assert note.document_kind == "credit_note"
    assert note.source_quote_id == quote.id
    assert note.internal_order_number == quote.internal_order_number
    assert note.nota_referencia_id == fiscal_document.id


def test_payment_against_fiscal_document_keeps_quote_as_anchor(db_session):
    tenant = _create_tenant(db_session, "24")
    user = _create_user(db_session, tenant, "24")
    cliente = _create_cliente(db_session, tenant, "24")

    quote = _create_quote(db_session, tenant, user, cliente)
    fiscal_document = crud.create_fiscal_document_from_quote(
        db_session,
        quote,
        user.id,
        "01",
    )

    pago = crud.registrar_pago(
        db_session,
        fiscal_document.id,
        schemas.PagoCreate(
            monto_pagado=Decimal("30.00"),
            metodo_pago="Yape",
            referencia_operacion="OP-001",
            tipo="adelanto",
        ),
        tenant.id,
    )

    db_session.refresh(quote)

    assert pago.cotizacion_id == quote.id
    assert pago.source_quote_id == quote.id
    assert pago.fiscal_document_id == fiscal_document.id
    assert pago.internal_order_number == quote.internal_order_number
    assert quote.monto_pagado == Decimal("30.00")


def test_guide_from_fiscal_document_keeps_full_traceability(db_session):
    tenant = _create_tenant(db_session, "25")
    user = _create_user(db_session, tenant, "25")
    cliente = _create_cliente(db_session, tenant, "25")

    quote = _create_quote(db_session, tenant, user, cliente)
    fiscal_document = crud.create_fiscal_document_from_quote(
        db_session,
        quote,
        user.id,
        "01",
    )

    guia = crud.create_guia_remision(
        db_session,
        {
            "cotizacion_id": fiscal_document.id,
            "fecha_traslado": datetime.now(timezone.utc),
            "motivo_traslado": "01",
            "descripcion_motivo": "Despacho",
            "peso_bruto_total": Decimal("10.500"),
            "unidad_medida_peso": "KGM",
            "modalidad_traslado": "01",
            "partida_ubigeo": "150101",
            "partida_direccion": "Av. Origen 123",
            "llegada_ubigeo": "150102",
            "llegada_direccion": "Av. Destino 456",
            "items": [
                {
                    "descripcion": "Impresion de volantes",
                    "cantidad": Decimal("2"),
                    "unidad_medida": "NIU",
                }
            ],
        },
        user.id,
        tenant.id,
    )

    assert guia.cotizacion_id == fiscal_document.id
    assert guia.source_quote_id == quote.id
    assert guia.fiscal_document_id == fiscal_document.id
    assert guia.internal_order_number == quote.internal_order_number
