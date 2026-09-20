from datetime import datetime, timedelta
from decimal import Decimal
from xml.etree import ElementTree as ET

import pytest

import models
from conftest import make_producto, make_tenant, make_user
from schemas.guias import GuiaRemisionResponse, SaleDispatchGuideData
from schemas.internal_transfers import (
    EstablishmentCreate,
    EstablishmentVerify,
    InternalTransferCreate,
    InternalTransferDepartureConfirm,
    InternalTransferDispatchCreate,
    InternalTransferDispatchLineCreate,
    InternalTransferGuideCreate,
    InternalTransferLineCreate,
    InternalTransferReceiptCreate,
    InternalTransferReceiptLineCreate,
)
from schemas.inventory import InventoryActivation, ProductInventoryConfig, WarehouseCreate
from services import facturacion_service, gre_ubl_service, internal_transfer_service, inventory_service, sale_dispatch_service


def _enable(db, tenant):
    tenant.smartpse_environment = "demo"
    subscription = models.Subscription(
        tenant_id=tenant.id,
        status="active",
        beta_feature_flags={"guides": True, "internal_transfers": True},
    )
    db.add(subscription)
    db.commit()


def _establishment(db, tenant, user, code, name, ubigeo, address):
    row = internal_transfer_service.create_establishment(
        db,
        tenant.id,
        user.id,
        EstablishmentCreate(
            sunat_code=code,
            name=name,
            ubigeo=ubigeo,
            address=address,
            is_main=code == "0000",
        ),
    )
    return internal_transfer_service.verify_establishment(
        db,
        tenant.id,
        row.id,
        user.id,
        EstablishmentVerify(note="Contrastado con la ficha RUC para pruebas"),
    )


def _warehouse(db, tenant, establishment, code, name, *, default=False):
    return inventory_service.create_warehouse(
        db,
        tenant.id,
        WarehouseCreate(
            code=code,
            name=name,
            establishment_id=establishment.id,
            is_default=default,
        ),
    )


def _inventory_product(db, tenant, user, warehouse, suffix="A", stock="100"):
    product = make_producto(db, tenant, suffix)
    inventory_service.configure_product(
        db,
        tenant.id,
        product.id,
        ProductInventoryConfig(
            item_type="inventory",
            inventory_enabled=True,
            warehouse_id=warehouse.id,
            opening_stock=Decimal(stock),
            minimum_stock=Decimal("0"),
        ),
        user.id,
    )
    return product


def _transfer(db, tenant, user, source, destination, source_wh, destination_wh, product, quantity="100", key="transfer-0001"):
    row, created = internal_transfer_service.create_transfer(
        db,
        tenant.id,
        user.id,
        InternalTransferCreate(
            source_establishment_id=source.id,
            destination_establishment_id=destination.id,
            source_warehouse_id=source_wh.id if source_wh else None,
            destination_warehouse_id=destination_wh.id if destination_wh else None,
            reason="Reposición de establecimiento",
            idempotency_key=key,
            lines=[InternalTransferLineCreate(product_id=product.id, quantity=Decimal(quantity))],
        ),
    )
    assert created is True
    return row


def _dispatch(db, tenant, user, transfer, quantity, key):
    dispatch, created = internal_transfer_service.create_dispatch(
        db,
        tenant.id,
        transfer.id,
        user.id,
        InternalTransferDispatchCreate(
            idempotency_key=key,
            lines=[InternalTransferDispatchLineCreate(
                transfer_line_id=transfer.lines[0].id,
                quantity=Decimal(quantity),
            )],
        ),
    )
    assert created is True
    return dispatch


def _guide_payload(dispatch_id, key="guide-internal-0001"):
    return InternalTransferGuideCreate(
        dispatch_id=dispatch_id,
        idempotency_key=key,
        fecha_traslado=datetime.now() + timedelta(days=1),
        peso_bruto_total=Decimal("25"),
        modalidad_traslado="02",
        partida_ubigeo="150101",
        partida_direccion="Se reemplaza por el establecimiento",
        llegada_ubigeo="150132",
        llegada_direccion="Se reemplaza por el establecimiento",
        vehiculo_placa="ABC123",
        conductor_tipo_doc="1",
        conductor_nro_doc="12345678",
        conductor_nombres="Ana",
        conductor_apellidos="Rojas",
        conductor_licencia="Q123456789",
    )


def test_internal_transfer_gre_moves_stock_only_on_departure_and_receipt(db_session):
    tenant = make_tenant(db_session, "901")
    user = make_user(db_session, tenant, email="transfer901@test.pe")
    _enable(db_session, tenant)
    source = _establishment(db_session, tenant, user, "0000", "Principal", "150101", "Av. Lima 100")
    destination = _establishment(db_session, tenant, user, "0001", "Sucursal", "150132", "Av. Próceres 200")
    source_wh = _warehouse(db_session, tenant, source, "ORIGEN", "Origen", default=True)
    destination_wh = _warehouse(db_session, tenant, destination, "DESTINO", "Destino")
    tenant.inventory_enabled = True
    db_session.commit()
    product = _inventory_product(db_session, tenant, user, source_wh)
    transfer = _transfer(db_session, tenant, user, source, destination, source_wh, destination_wh, product)

    first = _dispatch(db_session, tenant, user, transfer, "40", "dispatch-0040")
    context = internal_transfer_service.transfer_context(db_session, tenant.id, transfer.id)
    assert context["lines"][0]["assigned"] == Decimal("40.0000")
    assert context["lines"][0]["available_stock"] == Decimal("60.0000")
    assert inventory_service._balance(db_session, tenant.id, source_wh.id, product.id).on_hand == Decimal("100.0000")
    assert inventory_service._balance(db_session, tenant.id, destination_wh.id, product.id).on_hand == Decimal("0.0000")

    guide_data = _guide_payload(first.id)
    guide, created = internal_transfer_service.create_guide(db_session, tenant.id, user.id, guide_data)
    assert created is True
    repeated_guide, repeated_created = internal_transfer_service.create_guide(
        db_session,
        tenant.id,
        user.id,
        guide_data,
    )
    assert repeated_guide.id == guide.id
    assert repeated_created is False
    with pytest.raises(internal_transfer_service.InternalTransferError) as exc:
        internal_transfer_service.create_guide(
            db_session,
            tenant.id,
            user.id,
            guide_data.model_copy(update={"peso_bruto_total": Decimal("26")}),
        )
    assert exc.value.code == "IDEMPOTENCY_CONFLICT"
    assert guide.motivo_traslado == "04"
    assert guide.fiscal_document_id is None
    guide.indicador_m1_l = True
    assert GuiaRemisionResponse.model_validate(guide).indicador_m1_l is True
    guide.indicador_m1_l = False
    payload = facturacion_service._base_payload_gre(guide, user)
    assert payload["envio"]["codTraslado"] == "04"
    assert payload["company"]["address"]["codLocal"] == "0000"
    assert payload["envio"]["partida"]["codLocal"] == "0000"
    assert payload["envio"]["llegada"]["codLocal"] == "0001"
    assert payload["envio"]["partida"]["ruc"] == tenant.business_ruc
    assert payload["envio"]["llegada"]["ruc"] == tenant.business_ruc
    assert payload["destinatario"]["numDoc"] == tenant.business_ruc
    assert "documentosRelacionados" not in payload
    xml = gre_ubl_service.build_despatch_xml(payload)
    root = ET.fromstring(xml)
    ns = gre_ubl_service.NS
    assert root.findtext("./cac:Shipment/cbc:HandlingCode", namespaces=ns) == "04"
    assert (
        root.findtext("./cac:Shipment/cbc:HandlingInstructions", namespaces=ns)
        == "TRASLADO ENTRE ESTABLECIMIENTOS DE LA MISMA EMPRESA"
    )
    supplier_ruc = root.findtext(
        "./cac:DespatchSupplierParty/cac:Party/cac:PartyIdentification/cbc:ID",
        namespaces=ns,
    )
    recipient_ruc = root.findtext(
        "./cac:DeliveryCustomerParty/cac:Party/cac:PartyIdentification/cbc:ID",
        namespaces=ns,
    )
    assert supplier_ruc == recipient_ruc == tenant.business_ruc
    source_code = root.find(
        "./cac:Shipment/cac:Delivery/cac:Despatch/cac:DespatchAddress/cbc:AddressTypeCode",
        ns,
    )
    destination_code = root.find(
        "./cac:Shipment/cac:Delivery/cac:DeliveryAddress/cbc:AddressTypeCode",
        ns,
    )
    assert source_code is not None
    assert destination_code is not None
    assert (source_code.text, source_code.get("listID")) == ("0000", tenant.business_ruc)
    assert (destination_code.text, destination_code.get("listID")) == ("0001", tenant.business_ruc)
    assert root.findall("./cac:AdditionalDocumentReference", ns) == []
    validation = sale_dispatch_service.validate_guide_for_emission(db_session, guide)
    assert validation == {"valid": True, "errors": [], "warnings": []}

    guide.estado = "emitida"
    internal_transfer_service.apply_guide_result(db_session, guide, accepted=True)
    db_session.commit()
    internal_transfer_service.confirm_departure(db_session, tenant.id, first.id, user.id, "departure-0040")
    internal_transfer_service.confirm_departure(db_session, tenant.id, first.id, user.id, "departure-0040")
    with pytest.raises(internal_transfer_service.InternalTransferError) as exc:
        internal_transfer_service.confirm_departure(
            db_session,
            tenant.id,
            first.id,
            user.id,
            "departure-other-key",
        )
    assert exc.value.code == "IDEMPOTENCY_CONFLICT"
    db_session.rollback()
    assert (
        db_session.query(models.InventoryMovement)
        .filter(models.InventoryMovement.source_type == "internal_transfer_dispatch")
        .count()
        == 1
    )
    assert inventory_service._balance(db_session, tenant.id, source_wh.id, product.id).on_hand == Decimal("60.0000")
    assert inventory_service._balance(db_session, tenant.id, destination_wh.id, product.id).on_hand == Decimal("0.0000")

    dispatch_line = first.lines[0]
    receipt, created = internal_transfer_service.receive_dispatch(
        db_session,
        tenant.id,
        first.id,
        user.id,
        InternalTransferReceiptCreate(
            idempotency_key="receipt-0025",
            lines=[InternalTransferReceiptLineCreate(dispatch_line_id=dispatch_line.id, quantity=Decimal("25"))],
        ),
    )
    assert created is True
    assert receipt.id
    assert inventory_service._balance(db_session, tenant.id, destination_wh.id, product.id).on_hand == Decimal("25.0000")
    assert internal_transfer_service.transfer_context(db_session, tenant.id, transfer.id)["lines"][0]["in_transit"] == Decimal("15.0000")


def test_partial_dispatches_cannot_overallocate_or_double_reserve(db_session):
    tenant = make_tenant(db_session, "902")
    user = make_user(db_session, tenant, email="transfer902@test.pe")
    _enable(db_session, tenant)
    source = _establishment(db_session, tenant, user, "0000", "Principal", "150101", "Av. Lima 100")
    destination = _establishment(db_session, tenant, user, "0001", "Sucursal", "150132", "Av. Próceres 200")
    source_wh = _warehouse(db_session, tenant, source, "O", "Origen", default=True)
    destination_wh = _warehouse(db_session, tenant, destination, "D", "Destino")
    tenant.inventory_enabled = True
    db_session.commit()
    product = _inventory_product(db_session, tenant, user, source_wh, suffix="B")
    transfer = _transfer(db_session, tenant, user, source, destination, source_wh, destination_wh, product, key="transfer-0002")
    _dispatch(db_session, tenant, user, transfer, "60", "dispatch-0060")

    with pytest.raises(internal_transfer_service.InternalTransferError) as exc:
        _dispatch(db_session, tenant, user, transfer, "60", "dispatch-other-0060")
    db_session.rollback()
    assert exc.value.code == "TRANSFER_QUANTITY_EXCEEDED"
    balance = inventory_service._balance(db_session, tenant.id, source_wh.id, product.id, lock=False)
    assert balance.committed == Decimal("60.0000")


def test_rejected_gre_releases_stock_reservation(db_session):
    tenant = make_tenant(db_session, "903")
    user = make_user(db_session, tenant, email="transfer903@test.pe")
    _enable(db_session, tenant)
    source = _establishment(db_session, tenant, user, "0000", "Principal", "150101", "Av. Lima 100")
    destination = _establishment(db_session, tenant, user, "0001", "Sucursal", "150132", "Av. Próceres 200")
    source_wh = _warehouse(db_session, tenant, source, "O", "Origen", default=True)
    destination_wh = _warehouse(db_session, tenant, destination, "D", "Destino")
    tenant.inventory_enabled = True
    db_session.commit()
    product = _inventory_product(db_session, tenant, user, source_wh, suffix="C")
    transfer = _transfer(db_session, tenant, user, source, destination, source_wh, destination_wh, product, key="transfer-0003")
    dispatch = _dispatch(db_session, tenant, user, transfer, "30", "dispatch-0030")
    guide, _ = internal_transfer_service.create_guide(db_session, tenant.id, user.id, _guide_payload(dispatch.id, "guide-rejected"))

    internal_transfer_service.apply_guide_result(db_session, guide, accepted=False, rejected=True)
    db_session.commit()
    balance = inventory_service._balance(db_session, tenant.id, source_wh.id, product.id, lock=False)
    assert balance.committed == Decimal("0.0000")
    assert balance.on_hand == Decimal("100.0000")
    assert dispatch.lines[0].reservation_status == "released"


def test_manual_goods_work_without_inventory_movements(db_session):
    tenant = make_tenant(db_session, "904")
    user = make_user(db_session, tenant, email="transfer904@test.pe")
    _enable(db_session, tenant)
    source = _establishment(db_session, tenant, user, "0000", "Principal", "150101", "Av. Lima 100")
    destination = _establishment(db_session, tenant, user, "0001", "Sucursal", "150132", "Av. Próceres 200")
    transfer, _ = internal_transfer_service.create_transfer(
        db_session,
        tenant.id,
        user.id,
        InternalTransferCreate(
            source_establishment_id=source.id,
            destination_establishment_id=destination.id,
            reason="Material promocional",
            idempotency_key="manual-transfer",
            lines=[InternalTransferLineCreate(
                description="Muestrarios impresos",
                unit_code="NIU",
                quantity=Decimal("10"),
                manual_goods_confirmed=True,
            )],
        ),
    )
    dispatch = _dispatch(db_session, tenant, user, transfer, "10", "manual-dispatch")
    guide, _ = internal_transfer_service.create_guide(db_session, tenant.id, user.id, _guide_payload(dispatch.id, "manual-guide"))
    guide.estado = "emitida"
    internal_transfer_service.apply_guide_result(db_session, guide, accepted=True)
    db_session.commit()
    internal_transfer_service.confirm_departure(db_session, tenant.id, dispatch.id, user.id, "manual-departure")
    internal_transfer_service.receive_dispatch(
        db_session,
        tenant.id,
        dispatch.id,
        user.id,
        InternalTransferReceiptCreate(
            idempotency_key="manual-receipt",
            lines=[InternalTransferReceiptLineCreate(dispatch_line_id=dispatch.lines[0].id, quantity=Decimal("10"))],
        ),
    )
    assert db_session.query(models.InventoryMovement).count() == 0


def test_catalog_goods_without_tenant_inventory_are_documentary_only(db_session):
    tenant = make_tenant(db_session, "9041")
    user = make_user(db_session, tenant, email="transfer9041@test.pe")
    _enable(db_session, tenant)
    source = _establishment(db_session, tenant, user, "0000", "Principal", "150101", "Av. Lima 100")
    destination = _establishment(db_session, tenant, user, "0001", "Sucursal", "150132", "Av. Próceres 200")
    product = make_producto(db_session, tenant, "DOC")
    transfer = _transfer(
        db_session,
        tenant,
        user,
        source,
        destination,
        None,
        None,
        product,
        quantity="12",
        key="catalog-documentary-transfer",
    )
    dispatch = _dispatch(db_session, tenant, user, transfer, "12", "catalog-documentary-dispatch")
    guide, _ = internal_transfer_service.create_guide(
        db_session,
        tenant.id,
        user.id,
        _guide_payload(dispatch.id, "catalog-documentary-guide"),
    )
    guide.estado = "emitida"
    internal_transfer_service.apply_guide_result(db_session, guide, accepted=True)
    db_session.commit()

    internal_transfer_service.confirm_departure(
        db_session,
        tenant.id,
        dispatch.id,
        user.id,
        "catalog-documentary-departure",
    )
    internal_transfer_service.receive_dispatch(
        db_session,
        tenant.id,
        dispatch.id,
        user.id,
        InternalTransferReceiptCreate(
            idempotency_key="catalog-documentary-receipt",
            lines=[
                InternalTransferReceiptLineCreate(
                    dispatch_line_id=dispatch.lines[0].id,
                    quantity=Decimal("12"),
                )
            ],
        ),
    )

    assert transfer.lines[0].inventory_controlled is False
    assert db_session.query(models.InventoryMovement).count() == 0


def test_transfer_context_isolated_by_tenant(db_session):
    owner = make_tenant(db_session, "9042")
    intruder = make_tenant(db_session, "9043")
    user = make_user(db_session, owner, email="transfer9042@test.pe")
    _enable(db_session, owner)
    source = _establishment(db_session, owner, user, "0000", "Principal", "150101", "Av. Lima 100")
    destination = _establishment(db_session, owner, user, "0001", "Sucursal", "150132", "Av. Próceres 200")
    product = make_producto(db_session, owner, "TENANT")
    transfer = _transfer(
        db_session,
        owner,
        user,
        source,
        destination,
        None,
        None,
        product,
        key="tenant-isolation-transfer",
    )

    with pytest.raises(internal_transfer_service.InternalTransferError) as exc:
        internal_transfer_service.transfer_context(db_session, intruder.id, transfer.id)

    assert exc.value.status_code == 404
    assert exc.value.code == "TRANSFER_NOT_FOUND"


def test_same_establishment_uses_internal_flow_without_gre(db_session):
    tenant = make_tenant(db_session, "905")
    user = make_user(db_session, tenant, email="transfer905@test.pe")
    _enable(db_session, tenant)
    establishment = _establishment(db_session, tenant, user, "0000", "Principal", "150101", "Av. Lima 100")
    source_wh = _warehouse(db_session, tenant, establishment, "A", "Zona A", default=True)
    destination_wh = _warehouse(db_session, tenant, establishment, "B", "Zona B")
    tenant.inventory_enabled = True
    db_session.commit()
    product = _inventory_product(db_session, tenant, user, source_wh, suffix="D")
    transfer = _transfer(db_session, tenant, user, establishment, establishment, source_wh, destination_wh, product, key="same-site-transfer")
    dispatch = _dispatch(db_session, tenant, user, transfer, "10", "same-site-dispatch")
    assert internal_transfer_service.transfer_context(db_session, tenant.id, transfer.id)["requires_gre"] is False
    with pytest.raises(internal_transfer_service.InternalTransferError) as exc:
        internal_transfer_service.create_guide(db_session, tenant.id, user.id, _guide_payload(dispatch.id, "same-site-guide"))
    assert exc.value.code == "GRE_NOT_REQUIRED"


def test_cancel_transfer_releases_only_uncommitted_balance(db_session):
    tenant = make_tenant(db_session, "906")
    user = make_user(db_session, tenant, email="transfer906@test.pe")
    _enable(db_session, tenant)
    source = _establishment(db_session, tenant, user, "0000", "Principal", "150101", "Av. Lima 100")
    destination = _establishment(db_session, tenant, user, "0001", "Sucursal", "150132", "Av. Próceres 200")
    source_wh = _warehouse(db_session, tenant, source, "O", "Origen", default=True)
    destination_wh = _warehouse(db_session, tenant, destination, "D", "Destino")
    tenant.inventory_enabled = True
    db_session.commit()
    product = _inventory_product(db_session, tenant, user, source_wh, suffix="E")
    transfer = _transfer(db_session, tenant, user, source, destination, source_wh, destination_wh, product, key="partial-cancel")
    dispatch = _dispatch(db_session, tenant, user, transfer, "40", "partial-cancel-dispatch")
    guide, _ = internal_transfer_service.create_guide(db_session, tenant.id, user.id, _guide_payload(dispatch.id, "partial-cancel-guide"))
    guide.estado = "emitida"
    internal_transfer_service.apply_guide_result(db_session, guide, accepted=True)
    db_session.commit()

    internal_transfer_service.cancel_transfer(db_session, tenant.id, transfer.id)
    context = internal_transfer_service.transfer_context(db_session, tenant.id, transfer.id)

    assert context["status"] == "pending"
    assert context["lines"][0]["cancelled"] == Decimal("60.0000")
    assert context["lines"][0]["assigned"] == Decimal("40.0000")
    assert context["lines"][0]["pending_assignment"] == Decimal("0.0000")
    assert dispatch.status == "guide_accepted"
    assert inventory_service._balance(db_session, tenant.id, source_wh.id, product.id).committed == Decimal("40.0000")
