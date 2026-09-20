from datetime import datetime, timedelta, timezone
from decimal import Decimal
from xml.etree import ElementTree as ET
import os

import pytest
import base64

import crud
import models
import schemas
from conftest import make_cliente, make_quote_via_crud, make_tenant, make_user
from services import facturacion_service, gre_ubl_service, sale_dispatch_service, smartpse_response
from services.smartpse_client import SmartPSEDefinitiveRejection, SmartPSEException


def _accepted_invoice(db, suffix="DSP01", quantity=Decimal("100")):
    tenant = make_tenant(db, suffix)
    user = make_user(db, tenant, email=f"{suffix.lower()}@test.com")
    client = make_cliente(db, tenant, suffix)
    quote = make_quote_via_crud(db, tenant, user, client)
    invoice = crud.create_fiscal_document_from_quote(db, quote, user.id, "01")
    invoice.items[0].cantidad = quantity
    invoice.estado = "facturada"
    invoice.sunat_cdr_content = "<ApplicationResponse/>"
    invoice.provider_verification_status = "verified"
    db.commit()
    return tenant, user, invoice


def _payload(invoice, quantity, key):
    return schemas.SaleDispatchFromInvoiceCreate(
        fiscal_document_id=invoice.id,
        idempotency_key=key,
        fecha_traslado=datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc),
        peso_bruto_total=Decimal("12.500"),
        modalidad_traslado="02",
        partida_ubigeo="150101",
        partida_direccion="Av. Origen 100",
        llegada_ubigeo="150103",
        llegada_direccion="Av. Destino 200",
        vehiculo_placa="ABC123",
        conductor_nro_doc="72758912",
        conductor_nombres="Ana",
        conductor_apellidos="Rojas",
        conductor_licencia="Q12345678",
        lines=[schemas.DispatchLineSelection(
            fiscal_document_item_id=invoice.items[0].id,
            quantity=quantity,
            confirmed_as_goods=True,
        )],
    )


def _accepted_receipt(db, suffix="DSPB01", *, direct=True):
    tenant = make_tenant(db, suffix)
    user = make_user(db, tenant, email=f"{suffix.lower()}@test.com")
    client = make_cliente(db, tenant, suffix)
    quote = make_quote_via_crud(db, tenant, user, client)
    receipt = crud.create_fiscal_document_from_quote(db, quote, user.id, "03")
    receipt.estado = "facturada"
    receipt.provider_verification_status = "verified"
    if direct:
        receipt.sunat_cdr_content = "<ApplicationResponse/>"
    else:
        summary = models.ResumenDiario(
            tenant_id=tenant.id,
            usuario_id=user.id,
            correlativo="20260918-1",
            fec_generacion=datetime.now(timezone.utc),
            fec_resumen=datetime.now(timezone.utc),
            details_count=1,
            status=models.RESUMEN_DIARIO_STATUS_SENT,
            success=True,
            payload_snapshot={"details": [{
                "tipoDoc": "03", "serieNro": receipt.document_number, "estado": "1"
            }]},
        )
        db.add(summary)
    db.commit()
    return tenant, user, receipt


def test_receipt_source_is_reserved_and_referenced_as_type_03(db_session):
    tenant, user, receipt = _accepted_receipt(db_session)
    dispatch, created = sale_dispatch_service.create_from_document(
        db_session, tenant.id, user.id,
        schemas.SaleDispatchFromDocumentCreate(**_payload(
            receipt, Decimal("1"), "receipt-dispatch-key-0001"
        ).model_dump()),
    )
    assert created is True
    assert dispatch.source_document_type == "03"
    assert dispatch.lines[0].reservation_status == models.DISPATCH_RESERVATION_ACTIVE
    payload = facturacion_service._base_payload_gre(dispatch.guides[0], user)
    assert payload["documentosRelacionados"][0]["tipo_documento"] == "03"
    xml = gre_ubl_service.build_despatch_xml(payload)
    root = ET.fromstring(xml)
    ns = gre_ubl_service.NS
    assert root.findtext("cac:AdditionalDocumentReference/cbc:DocumentTypeCode", namespaces=ns) == "03"
    assert root.findtext("cac:AdditionalDocumentReference/cbc:DocumentType", namespaces=ns) == "BOLETA DE VENTA"


def test_receipt_accepted_by_daily_summary_persists_summary_evidence(db_session):
    tenant, user, receipt = _accepted_receipt(db_session, "DSPB02", direct=False)
    dispatch, _ = sale_dispatch_service.create_from_document(
        db_session, tenant.id, user.id,
        schemas.SaleDispatchFromDocumentCreate(**_payload(
            receipt, Decimal("1"), "receipt-summary-key-0001"
        ).model_dump()),
    )
    assert dispatch.source_summary_id is not None
    assert dispatch.source_acceptance_evidence["method"] == "daily_summary"


def test_transport_scenarios_do_not_require_fake_driver_and_apply_gre31_rule(db_session):
    tenant, user, invoice = _accepted_invoice(db_session, "DSPTRANS")
    public = _payload(invoice, Decimal("1"), "public-transport-key-0001")
    public.fecha_traslado = datetime.now(timezone.utc) + timedelta(days=1)
    public.modalidad_traslado = "01"
    public.fecha_entrega_transportista = public.fecha_traslado
    public.transportista_ruc = "20123456789"
    public.transportista_razon_social = "TRANSPORTES"
    public.transportista_nro_mtc = "MTC001"
    public.vehiculo_placa = None
    public.conductor_nro_doc = None
    public.conductor_nombres = None
    public.conductor_apellidos = None
    public.conductor_licencia = None
    dispatch, _ = sale_dispatch_service.create_from_document(
        db_session, tenant.id, user.id, schemas.SaleDispatchFromDocumentCreate(**public.model_dump())
    )
    guide = dispatch.guides[0]
    validation = sale_dispatch_service.validate_guide_for_emission(db_session, guide)
    assert validation["valid"] is True
    assert sale_dispatch_service.carrier_guide_required(guide) is True

    guide.registrar_vehiculo_transportista = True
    guide.transportista_acuerdo_confirmado_at = datetime.now(timezone.utc)
    guide.vehiculo_placa = "ABC123"
    guide.vehiculo_nro_circulacion = "CIRC001"
    guide.conductor_tipo_doc = "4"
    guide.conductor_nro_doc = "CE123456"
    guide.conductor_nombres = "ANA"
    guide.conductor_apellidos = "ROJAS"
    guide.conductor_licencia = "Q12345678"
    assert sale_dispatch_service.carrier_guide_required(guide) is False
    assert sale_dispatch_service.validate_guide_for_emission(db_session, guide)["valid"] is True


def test_m1l_keeps_plate_and_date_without_driver_in_payload(db_session):
    tenant, user, invoice = _accepted_invoice(db_session, "DSPM1L")
    data = _payload(invoice, Decimal("1"), "m1l-key-0001")
    data.fecha_traslado = datetime.now(timezone.utc) + timedelta(days=1)
    data.modalidad_traslado = "01"
    data.indicador_m1_l = True
    data.fecha_entrega_transportista = data.fecha_traslado
    data.conductor_nro_doc = None
    data.conductor_nombres = None
    data.conductor_apellidos = None
    data.conductor_licencia = None
    dispatch, _ = sale_dispatch_service.create_from_document(
        db_session, tenant.id, user.id, schemas.SaleDispatchFromDocumentCreate(**data.model_dump())
    )
    guide = dispatch.guides[0]
    assert sale_dispatch_service.validate_guide_for_emission(db_session, guide)["valid"] is True
    payload = facturacion_service._base_payload_gre(guide, user)
    assert payload["envio"]["vehiculo"]["placa"] == "ABC123"
    assert payload["envio"]["fecEntrega"].endswith("-05:00")
    assert "choferes" not in payload["envio"]


def test_partial_dispatches_reserve_exact_invoice_line_and_prevent_excess(db_session):
    tenant, user, invoice = _accepted_invoice(db_session)
    first, created = sale_dispatch_service.create_from_invoice(
        db_session, tenant.id, user.id, _payload(invoice, Decimal("40"), "dispatch-key-0001")
    )
    second, _ = sale_dispatch_service.create_from_invoice(
        db_session, tenant.id, user.id, _payload(invoice, Decimal("60"), "dispatch-key-0002")
    )

    assert created is True
    assert first.lines[0].fiscal_document_item_id == invoice.items[0].id
    assert first.lines[0].inventory_movement_id is None
    assert first.guides[0].items[0].dispatch_line_id == first.lines[0].id
    assert second.lines[0].reservation_status == models.DISPATCH_RESERVATION_ACTIVE
    context = sale_dispatch_service.get_invoice_dispatch_context(db_session, tenant.id, invoice.id)
    assert context["lines"][0]["available"] == Decimal("0.0000")

    with pytest.raises(sale_dispatch_service.DispatchError) as exc:
        sale_dispatch_service.create_from_invoice(
            db_session, tenant.id, user.id, _payload(invoice, Decimal("1"), "dispatch-key-0003")
        )
    assert exc.value.code == "DISPATCH_QUANTITY_EXCEEDED"


def test_demo_and_production_guides_use_separate_series(db_session):
    demo_tenant, demo_user, demo_invoice = _accepted_invoice(db_session, "DSPENV1")
    demo_tenant.smartpse_environment = "demo"
    db_session.commit()
    demo_dispatch, _ = sale_dispatch_service.create_from_invoice(
        db_session,
        demo_tenant.id,
        demo_user.id,
        _payload(demo_invoice, Decimal("1"), "demo-series-key-0001"),
    )
    assert demo_dispatch.guides[0].serie == "T999"
    assert demo_dispatch.guides[0].emission_environment == "demo"

    prod_tenant, prod_user, prod_invoice = _accepted_invoice(db_session, "DSPENV2")
    prod_tenant.smartpse_environment = "produccion"
    prod_tenant.fiscal_gre_remitente_series = "TI01"
    prod_tenant.fiscal_gre_remitente_series_floor = 8
    db_session.commit()
    prod_dispatch, _ = sale_dispatch_service.create_from_invoice(
        db_session,
        prod_tenant.id,
        prod_user.id,
        _payload(prod_invoice, Decimal("1"), "prod-series-key-0001"),
    )
    assert prod_dispatch.guides[0].serie == "TI01"
    assert prod_dispatch.guides[0].correlativo == 9
    assert prod_dispatch.guides[0].emission_environment == "production"


def test_guide_emission_blocks_if_environment_changes_after_draft(db_session):
    tenant, user, invoice = _accepted_invoice(db_session, "DSPENV3")
    tenant.smartpse_environment = "demo"
    db_session.commit()
    dispatch, _ = sale_dispatch_service.create_from_invoice(
        db_session,
        tenant.id,
        user.id,
        _payload(invoice, Decimal("1"), "environment-change-key-0001"),
    )
    tenant.smartpse_environment = "produccion"
    tenant.fiscal_gre_remitente_series = "TI01"
    tenant.fiscal_gre_remitente_series_floor = 0
    db_session.commit()

    validation = sale_dispatch_service.validate_guide_for_emission(
        db_session, dispatch.guides[0]
    )
    assert any(
        error["code"] == "GUIDE_ENVIRONMENT_CHANGED"
        for error in validation["errors"]
    )


def test_production_guide_requires_superadmin_configured_series(db_session):
    tenant, user, invoice = _accepted_invoice(db_session, "DSPENV4")
    tenant.smartpse_environment = "produccion"
    db_session.commit()

    with pytest.raises(sale_dispatch_service.DispatchError) as exc:
        sale_dispatch_service.create_from_invoice(
            db_session,
            tenant.id,
            user.id,
            _payload(invoice, Decimal("1"), "missing-prod-series-key-0001"),
        )

    assert exc.value.code == "GUIDE_PRODUCTION_SERIES_REQUIRED"


def test_dispatch_creation_idempotency_rejects_changed_content(db_session):
    tenant, user, invoice = _accepted_invoice(db_session, "DSP02")
    original, created = sale_dispatch_service.create_from_invoice(
        db_session, tenant.id, user.id, _payload(invoice, Decimal("40"), "same-key-0001")
    )
    repeated, repeated_created = sale_dispatch_service.create_from_invoice(
        db_session, tenant.id, user.id, _payload(invoice, Decimal("40"), "same-key-0001")
    )
    assert created is True and repeated_created is False and repeated.id == original.id

    with pytest.raises(sale_dispatch_service.DispatchError) as exc:
        sale_dispatch_service.create_from_invoice(
            db_session, tenant.id, user.id, _payload(invoice, Decimal("41"), "same-key-0001")
        )
    assert exc.value.code == "IDEMPOTENCY_CONFLICT"


def test_accepted_guide_covers_reservation_without_inventory_movement(db_session):
    tenant, user, invoice = _accepted_invoice(db_session, "DSP03")
    dispatch, _ = sale_dispatch_service.create_from_invoice(
        db_session, tenant.id, user.id, _payload(invoice, Decimal("25"), "cover-key-0001")
    )
    guide = dispatch.guides[0]
    sale_dispatch_service.apply_guide_result(db_session, guide, accepted=True)
    db_session.commit()
    assert dispatch.lines[0].reservation_status == models.DISPATCH_RESERVATION_COVERED
    assert db_session.query(models.InventoryMovement).filter(
        models.InventoryMovement.tenant_id == tenant.id,
        models.InventoryMovement.source_type == "guide",
    ).count() == 0


def test_gre_xml_uses_sunat_specific_nodes_for_private_sale():
    payload = {
        "tipoDoc": "09", "serie": "T001", "correlativo": "000001",
        "fechaEmision": "2026-09-15T10:00:00-05:00", "observacion": "VENTA",
        "company": {"ruc": "20123456789", "razonSocial": "INKORA", "address": {"ubigueo": "150101", "direccion": "Origen"}},
        "destinatario": {"tipoDoc": "6", "numDoc": "20987654321", "rznSocial": "CLIENTE"},
        "documentosRelacionados": [{"tipo_documento": "01", "serie": "F001", "numero": "15", "ruc_emisor": "20123456789"}],
        "envio": {
            "codTraslado": "01", "desTraslado": "VENTA", "modTraslado": "02",
            "fecTraslado": "2026-09-16T00:00:00-05:00", "pesoTotal": "10", "undPesoTotal": "KGM",
            "llegada": {"ubigueo": "150103", "direccion": "Destino"},
            "partida": {"ubigueo": "150101", "direccion": "Origen"},
            "vehiculo": {"placa": "ABC123", "nroCirculacion": "CIRC01"},
            "choferes": [{"tipo": "Principal", "tipoDoc": "1", "nroDoc": "72758912", "nombres": "ANA", "apellidos": "ROJAS", "licencia": "Q12345678"}],
        },
        "details": [{"cantidad": "2", "unidad": "NIU", "descripcion": "CAJA", "codigo": "P1"}],
    }
    xml = gre_ubl_service.build_despatch_xml(payload)
    root = ET.fromstring(xml)
    ns = gre_ubl_service.NS
    assert root.findtext("cac:Shipment/cbc:HandlingCode", namespaces=ns) == "01"
    assert root.findtext("cac:Shipment/cbc:HandlingInstructions", namespaces=ns) == "VENTA"
    assert root.findtext("cac:Shipment/cac:TransportHandlingUnit/cac:TransportEquipment/cbc:ID", namespaces=ns) == "ABC123"
    assert root.findtext("cac:Shipment/cac:TransportHandlingUnit/cac:TransportEquipment/cac:ApplicableTransportMeans/cbc:RegistrationNationalityID", namespaces=ns) == "CIRC01"
    xsd_path = os.getenv("SUNAT_GRE_XSD_PATH")
    if xsd_path:
        from lxml import etree
        schema = etree.XMLSchema(etree.parse(xsd_path))
        xsd_document = etree.fromstring(xml.encode())
        extensions = xsd_document.find(f"{{{gre_ubl_service.NS['ext']}}}UBLExtensions")
        if extensions is not None:
            xsd_document.remove(extensions)  # Smart PSE fills the signature extension.
        schema.assertValid(xsd_document)


def test_gre_31_places_sender_inside_delivery_despatch_party():
    payload = {
        "tipoDoc": "31", "serie": "V001", "correlativo": "000001",
        "fechaEmision": "2026-09-15T10:00:00-05:00",
        "company": {"ruc": "20999999991", "razonSocial": "TRANSPORTES", "address": {"ubigueo": "150101", "direccion": "Base"}},
        "destinatario": {"tipoDoc": "6", "numDoc": "20987654321", "rznSocial": "CLIENTE"},
        "remitente": {"tipoDoc": "6", "numDoc": "20123456789", "rznSocial": "VENDEDOR"},
        "documentosRelacionados": [{"tipo_documento": "09", "serie": "T001", "numero": "1", "ruc_emisor": "20123456789"}],
        "envio": {
            "pagadorFlete": "Remitente", "fecTraslado": "2026-09-16T00:00:00-05:00",
            "pesoTotal": "10", "undPesoTotal": "KGM",
            "llegada": {"ubigueo": "150103", "direccion": "Destino"},
            "partida": {"ubigueo": "150101", "direccion": "Origen"},
            "transportista": {"tipoDoc": "6", "numDoc": "20999999991", "rznSocial": "TRANSPORTES"},
            "vehiculo": {"placa": "ABC123"},
            "choferes": [{"tipo": "Principal", "tipoDoc": "1", "nroDoc": "72758912", "nombres": "ANA", "apellidos": "ROJAS", "licencia": "Q12345678"}],
        },
        "details": [{"cantidad": "2", "unidad": "NIU", "descripcion": "CAJA"}],
    }
    xml = gre_ubl_service.build_despatch_xml(payload)
    root = ET.fromstring(xml)
    ns = gre_ubl_service.NS
    assert root.findtext("cac:Shipment/cac:Delivery/cac:Despatch/cac:DespatchParty/cac:PartyIdentification/cbc:ID", namespaces=ns) == "20123456789"
    xsd_path = os.getenv("SUNAT_GRE_XSD_PATH")
    if xsd_path:
        from lxml import etree
        schema = etree.XMLSchema(etree.parse(xsd_path))
        xsd_document = etree.fromstring(xml.encode())
        extensions = xsd_document.find(f"{{{gre_ubl_service.NS['ext']}}}UBLExtensions")
        if extensions is not None:
            xsd_document.remove(extensions)
        schema.assertValid(xsd_document)


def test_gre_cdr_must_match_document_and_have_acceptance_code_zero():
    def cdr(document, code):
        xml = f'''<ApplicationResponse xmlns:cac="{smartpse_response.NS['cac']}" xmlns:cbc="{smartpse_response.NS['cbc']}"><cac:DocumentResponse><cac:Response><cbc:ResponseCode>{code}</cbc:ResponseCode><cbc:Description>resultado</cbc:Description></cac:Response><cac:DocumentReference><cbc:ID>{document}</cbc:ID></cac:DocumentReference></cac:DocumentResponse></ApplicationResponse>'''
        return base64.b64encode(xml.encode()).decode()
    payload = {"tipoDoc": "09", "serie": "T001", "correlativo": "000001"}
    accepted = smartpse_response.build_smartpse_result(
        payload, {"cdr": cdr("T001-1", "0")}, endpoint="demo", status_code=200, require_cdr=True
    )
    assert accepted["success"] is True and accepted["pending"] is False
    with pytest.raises(SmartPSEDefinitiveRejection):
        smartpse_response.build_smartpse_result(
            payload, {"cdr": cdr("T001-1", "2335")}, endpoint="demo", status_code=200, require_cdr=True
        )
    with pytest.raises(SmartPSEException):
        smartpse_response.build_smartpse_result(
            payload, {"cdr": cdr("T001-2", "0")}, endpoint="demo", status_code=200, require_cdr=True
        )


def test_transport_guide_is_issued_by_carrier_tenant_and_keeps_goods_invoice_separate(db_session):
    tenant = make_tenant(db_session, "00331")
    user = make_user(db_session, tenant, email="carrier@test.com")
    payload = schemas.TransportGuideCreate(
        idempotency_key="carrier-guide-0001",
        gre_remitente=schemas.ExternalDocumentReferenceInput(
            document_type="09", issuer_ruc="20123456789", series="T001", number="45"
        ),
        goods_invoice=schemas.ExternalDocumentReferenceInput(
            document_type="01", issuer_ruc="20123456789", series="F001", number="99"
        ),
        remitente_nro_doc="20123456789", remitente_razon_social="VENDEDOR",
        destinatario_tipo_doc="6", destinatario_nro_doc="20987654321", destinatario_razon_social="CLIENTE",
        fecha_traslado=datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc),
        peso_bruto_total=Decimal("5"), partida_ubigeo="150101", partida_direccion="Origen",
        llegada_ubigeo="150103", llegada_direccion="Destino",
        transportista_nro_mtc="MTC001", vehiculo_placa="ABC123",
        conductor_nro_doc="72758912", conductor_nombres="ANA", conductor_apellidos="ROJAS",
        conductor_licencia="Q12345678",
        lines=[schemas.GuiaRemisionItemCreate(descripcion="CAJA", cantidad=Decimal("2"), unidad_medida="NIU")],
    )
    guide, created = sale_dispatch_service.create_transport_guide(
        db_session, tenant.id, user.id, payload
    )
    assert created is True
    assert guide.tipo_documento == "31"
    assert guide.transportista_ruc == tenant.business_ruc
    assert guide.external_gre_reference.document_type == "09"
    assert guide.goods_invoice_reference.document_type == "01"
    assert guide.dispatch_id is None


def test_transport_guide_requires_verified_external_sender_gre(db_session):
    tenant = make_tenant(db_session, "00332")
    user = make_user(db_session, tenant, email="carrier-verified@test.com")
    payload = schemas.TransportGuideCreate(
        idempotency_key="carrier-guide-verify-0001",
        gre_remitente=schemas.ExternalDocumentReferenceInput(
            document_type="09", issuer_ruc="20123456789", series="T001", number="45"
        ),
        goods_invoice=schemas.ExternalDocumentReferenceInput(
            document_type="01", issuer_ruc="20123456789", series="F001", number="99"
        ),
        remitente_nro_doc="20123456789", remitente_razon_social="VENDEDOR",
        destinatario_tipo_doc="6", destinatario_nro_doc="20987654321", destinatario_razon_social="CLIENTE",
        fecha_traslado=datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc),
        peso_bruto_total=Decimal("5"), partida_ubigeo="150101", partida_direccion="Origen",
        llegada_ubigeo="150103", llegada_direccion="Destino",
        transportista_nro_mtc="MTC001", vehiculo_placa="ABC123",
        conductor_nro_doc="72758912", conductor_nombres="ANA", conductor_apellidos="ROJAS",
        conductor_licencia="Q12345678",
        lines=[schemas.GuiaRemisionItemCreate(descripcion="CAJA", cantidad=Decimal("2"), unidad_medida="NIU")],
    )
    guide, _ = sale_dispatch_service.create_transport_guide(db_session, tenant.id, user.id, payload)
    before = sale_dispatch_service.validate_guide_for_emission(db_session, guide)
    assert any(error["code"] == "GRE_09_NOT_VERIFIED" for error in before["errors"])

    signed_xml = f'''<DespatchAdvice xmlns="urn:oasis:names:specification:ubl:schema:xsd:DespatchAdvice-2" xmlns:cac="{smartpse_response.NS['cac']}" xmlns:cbc="{smartpse_response.NS['cbc']}"><cbc:ID>T001-45</cbc:ID><cbc:DespatchAdviceTypeCode>09</cbc:DespatchAdviceTypeCode><cac:DespatchSupplierParty><cac:Party><cac:PartyIdentification><cbc:ID>20123456789</cbc:ID></cac:PartyIdentification></cac:Party></cac:DespatchSupplierParty></DespatchAdvice>'''
    cdr_xml = f'''<ApplicationResponse xmlns:cac="{smartpse_response.NS['cac']}" xmlns:cbc="{smartpse_response.NS['cbc']}"><cac:DocumentResponse><cac:Response><cbc:ResponseCode>0</cbc:ResponseCode><cbc:Description>Aceptado</cbc:Description></cac:Response><cac:DocumentReference><cbc:ID>T001-45</cbc:ID></cac:DocumentReference></cac:DocumentResponse></ApplicationResponse>'''
    reference = sale_dispatch_service.verify_external_guide_reference(
        db_session, tenant.id, user.id, guide.id,
        schemas.ExternalGuideVerification(
            environment="demo",
            signed_xml=signed_xml,
            cdr=base64.b64encode(cdr_xml.encode()).decode(),
            provider_document_name="20123456789-09-T001-45",
            note="XML firmado y CDR contrastados por soporte.",
        ),
    )
    assert reference.verification_status == "verified"
    assert reference.evidence["signed_xml_sha256"]
    assert db_session.query(models.AuditLog).filter(
        models.AuditLog.entity_type == "guide_external_reference",
        models.AuditLog.entity_id == reference.id,
    ).count() == 1
    after = sale_dispatch_service.validate_guide_for_emission(db_session, guide)
    assert not any(error["code"] == "GRE_09_NOT_VERIFIED" for error in after["errors"])


def test_external_sender_verification_rejects_identity_mismatch(db_session):
    tenant = make_tenant(db_session, "00333")
    user = make_user(db_session, tenant, email="carrier-mismatch@test.com")
    reference = models.GuideExternalReference(
        tenant_id=tenant.id, document_type="09", issuer_ruc="20123456789",
        series="T001", number="45", source="carrier_input",
        verification_status="unverified", created_by_user_id=user.id,
    )
    guide = models.GuiaRemision(
        tipo_documento="31", tenant_id=tenant.id, usuario_id=user.id,
        serie="V001", correlativo=1, fecha_emision=datetime.now(timezone.utc),
        fecha_traslado=datetime.now(timezone.utc), estado="pendiente",
        motivo_traslado="01", peso_bruto_total=Decimal("1"),
        modalidad_traslado="01", partida_ubigeo="150101", partida_direccion="Origen",
        llegada_ubigeo="150103", llegada_direccion="Destino",
        external_gre_reference=reference,
    )
    db_session.add_all([reference, guide])
    db_session.commit()
    signed_xml = f'''<DespatchAdvice xmlns="urn:oasis:names:specification:ubl:schema:xsd:DespatchAdvice-2" xmlns:cac="{smartpse_response.NS['cac']}" xmlns:cbc="{smartpse_response.NS['cbc']}"><cbc:ID>T001-99</cbc:ID><cbc:DespatchAdviceTypeCode>09</cbc:DespatchAdviceTypeCode><cac:DespatchSupplierParty><cac:Party><cac:PartyIdentification><cbc:ID>20123456789</cbc:ID></cac:PartyIdentification></cac:Party></cac:DespatchSupplierParty></DespatchAdvice>'''
    with pytest.raises(sale_dispatch_service.DispatchError) as exc:
        sale_dispatch_service.verify_external_guide_reference(
            db_session, tenant.id, user.id, guide.id,
            schemas.ExternalGuideVerification(
                environment="demo", signed_xml=signed_xml, cdr="x" * 20,
                note="Documento presentado para revisión administrativa.",
            ),
        )
    assert exc.value.code == "EXTERNAL_GRE_IDENTITY_MISMATCH"
    assert reference.verification_status == "unverified"


def test_historical_invoice_stays_blocked_until_admin_confirms_no_prior_dispatch(db_session):
    tenant, user, invoice = _accepted_invoice(db_session, "DSP04")
    invoice.dispatch_reconciliation_status = "required"
    db_session.commit()
    context = sale_dispatch_service.get_invoice_dispatch_context(db_session, tenant.id, invoice.id)
    assert context["eligibility"]["code"] == "HISTORICAL_RECONCILIATION_REQUIRED"

    with pytest.raises(sale_dispatch_service.DispatchError):
        sale_dispatch_service.reconcile_historical_invoice(
            db_session, tenant.id, user.id, invoice.id,
            schemas.HistoricalDispatchReconciliation(
                confirmed_no_prior_dispatch=False,
                note="Se identificaron despachos anteriores.",
            ),
        )
    sale_dispatch_service.reconcile_historical_invoice(
        db_session, tenant.id, user.id, invoice.id,
        schemas.HistoricalDispatchReconciliation(
            confirmed_no_prior_dispatch=True,
            note="Revisión documental confirma que no hubo salida previa.",
        ),
    )
    assert invoice.dispatch_reconciliation_status == "cleared"
