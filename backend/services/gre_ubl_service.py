"""SUNAT Nueva GRE UBL 2.1 (09/31), including the June 2026 amendments."""
from __future__ import annotations

from xml.etree import ElementTree as ET

from services.smartpse_ubl_service import (
    NS,
    _add,
    _add_signature,
    _add_ubl_extensions,
    _date_time,
    _document_id,
    _q,
    _quantity,
)


CATALOG = "urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo"


def _party(parent, tag: str, data: dict, *, wrapped=False):
    node = _add(parent, "cac", tag)
    party = _add(node, "cac", "Party") if wrapped else node
    identification = _add(party, "cac", "PartyIdentification")
    _add(
        identification,
        "cbc",
        "ID",
        data.get("numDoc"),
        schemeID=data.get("tipoDoc") or "6",
        schemeName="Documento de Identidad",
        schemeAgencyName="PE:SUNAT",
        schemeURI=CATALOG + "06",
    )
    legal = _add(party, "cac", "PartyLegalEntity")
    _add(legal, "cbc", "RegistrationName", data.get("rznSocial"))
    if data.get("nroMtc"):
        _add(legal, "cbc", "CompanyID", data["nroMtc"])
    return node


def _address(parent, tag: str, data: dict):
    node = _add(parent, "cac", tag)
    _add(
        node,
        "cbc",
        "ID",
        data.get("ubigeo") or data.get("ubigueo"),
        schemeAgencyName="PE:INEI",
        schemeName="Ubigeos",
    )
    if data.get("codLocal"):
        _add(
            node,
            "cbc",
            "AddressTypeCode",
            data["codLocal"],
            listID=data.get("ruc"),
            listAgencyName="PE:SUNAT",
            listName="Establecimientos anexos",
        )
    line = _add(node, "cac", "AddressLine")
    _add(line, "cbc", "Line", data.get("direccion"))
    return node


def _document_reference(root, reference: dict):
    node = _add(root, "cac", "AdditionalDocumentReference")
    number = str(reference.get("numero") or "").lstrip("0") or "0"
    _add(node, "cbc", "ID", f"{reference['serie']}-{number}")
    document_type = reference["tipo_documento"]
    _add(
        node,
        "cbc",
        "DocumentTypeCode",
        document_type,
        listAgencyName="PE:SUNAT",
        listName="Documento relacionado al transporte",
        listURI=CATALOG + "61",
    )
    labels = {
        "01": "FACTURA",
        "03": "BOLETA DE VENTA",
        "09": "GUIA DE REMISION REMITENTE",
    }
    _add(node, "cbc", "DocumentType", labels.get(document_type, "DOCUMENTO RELACIONADO"))
    issuer = _add(node, "cac", "IssuerParty")
    identification = _add(issuer, "cac", "PartyIdentification")
    _add(identification, "cbc", "ID", reference["ruc_emisor"], schemeID="6")


def _transport_equipment(shipment, vehicle: dict):
    handling = _add(shipment, "cac", "TransportHandlingUnit")
    equipment = _add(handling, "cac", "TransportEquipment")
    _add(equipment, "cbc", "ID", vehicle.get("placa"))
    if vehicle.get("nroCirculacion"):
        means = _add(equipment, "cac", "ApplicableTransportMeans")
        _add(means, "cbc", "RegistrationNationalityID", vehicle["nroCirculacion"])
    if vehicle.get("nroAutorizacion"):
        reference = _add(equipment, "cac", "ShipmentDocumentReference")
        _add(
            reference,
            "cbc",
            "ID",
            vehicle["nroAutorizacion"],
            schemeID=vehicle.get("codEmisor"),
            schemeName="Entidad Autorizadora",
            schemeAgencyName="PE:SUNAT",
        )


def build_despatch_xml(payload: dict) -> str:
    tipo = str(payload.get("tipoDoc") or "09")
    if tipo not in {"09", "31"}:
        raise ValueError("Tipo de guía no soportado")
    root = ET.Element(_q("despatch", "DespatchAdvice"), {"xmlns": NS["despatch"]})
    _add_ubl_extensions(root)
    _add(root, "cbc", "UBLVersionID", "2.1")
    _add(root, "cbc", "CustomizationID", "2.0")
    _add(root, "cbc", "ID", _document_id(payload))
    issue_date, issue_time = _date_time(payload.get("fechaEmision"))
    _add(root, "cbc", "IssueDate", issue_date)
    _add(root, "cbc", "IssueTime", issue_time)
    _add(
        root,
        "cbc",
        "DespatchAdviceTypeCode",
        tipo,
        listAgencyName="PE:SUNAT",
        listName="Tipo de Documento",
        listURI=CATALOG + "01",
    )
    if payload.get("observacion"):
        _add(root, "cbc", "Note", payload["observacion"])
    for reference in payload.get("documentosRelacionados") or []:
        _document_reference(root, reference)

    company = payload["company"]
    _add_signature(root, company)
    _party(
        root,
        "DespatchSupplierParty",
        {"tipoDoc": "6", "numDoc": company["ruc"], "rznSocial": company["razonSocial"]},
        wrapped=True,
    )
    _party(root, "DeliveryCustomerParty", payload["destinatario"], wrapped=True)
    if tipo == "31" and payload.get("pagador"):
        _party(root, "OriginatorCustomerParty", payload["pagador"], wrapped=True)

    envio = payload["envio"]
    shipment = _add(root, "cac", "Shipment")
    _add(shipment, "cbc", "ID", "SUNAT_Envio")
    if tipo == "09":
        _add(
            shipment,
            "cbc",
            "HandlingCode",
            envio["codTraslado"],
            listAgencyName="PE:SUNAT",
            listName="Motivo de traslado",
            listURI=CATALOG + "20",
        )
        if envio.get("desTraslado"):
            _add(shipment, "cbc", "HandlingInstructions", envio["desTraslado"])
    _add(
        shipment,
        "cbc",
        "GrossWeightMeasure",
        _quantity(envio["pesoTotal"]),
        unitCode=envio.get("undPesoTotal") or "KGM",
    )
    if envio.get("numBultos") is not None:
        _add(shipment, "cbc", "TotalTransportHandlingUnitQuantity", envio["numBultos"])
    flags = (
        ("indicadorM1L", "SUNAT_Envio_IndicadorTrasladoVehiculoM1L"),
        ("registrarVehiculoTransportista", "SUNAT_Envio_IndicadorVehiculoConductoresTransp"),
        ("indTransbordo", "SUNAT_Envio_IndicadorTransbordoProgramado"),
    )
    for key, value in flags:
        if envio.get(key):
            _add(shipment, "cbc", "SpecialInstructions", value)
    if tipo == "31":
        payer = envio.get("pagadorFlete") or "Remitente"
        _add(shipment, "cbc", "SpecialInstructions", f"SUNAT_Envio_IndicadorPagadorFlete_{payer}")

    stage = _add(shipment, "cac", "ShipmentStage")
    if tipo == "09":
        _add(
            stage,
            "cbc",
            "TransportModeCode",
            envio["modTraslado"],
            listAgencyName="PE:SUNAT",
            listName="Modalidad de traslado",
            listURI=CATALOG + "18",
        )
    if tipo == "31" or envio.get("modTraslado") == "02" or envio.get("registrarVehiculoTransportista"):
        transit = _add(stage, "cac", "TransitPeriod")
        _add(transit, "cbc", "StartDate", _date_time(envio["fecTraslado"])[0])
    if envio.get("transportista"):
        _party(stage, "CarrierParty", envio["transportista"])
    if tipo == "09" and envio.get("modTraslado") == "01":
        loading = _add(stage, "cac", "LoadingTransportEvent")
        _add(loading, "cbc", "OccurrenceDate", _date_time(envio["fecEntrega"])[0])
    for person in envio.get("choferes") or []:
        driver = _add(stage, "cac", "DriverPerson")
        _add(
            driver,
            "cbc",
            "ID",
            person["nroDoc"],
            schemeID=person.get("tipoDoc") or "1",
            schemeName="Documento de Identidad",
            schemeAgencyName="PE:SUNAT",
            schemeURI=CATALOG + "06",
        )
        _add(driver, "cbc", "FirstName", person["nombres"])
        _add(driver, "cbc", "FamilyName", person["apellidos"])
        _add(driver, "cbc", "JobTitle", person.get("tipo") or "Principal")
        identity = _add(driver, "cac", "IdentityDocumentReference")
        _add(identity, "cbc", "ID", person["licencia"])

    delivery = _add(shipment, "cac", "Delivery")
    _address(delivery, "DeliveryAddress", envio["llegada"])
    despatch = _add(delivery, "cac", "Despatch")
    _address(despatch, "DespatchAddress", envio["partida"])
    if tipo == "31":
        _party(despatch, "DespatchParty", payload["remitente"])
    if envio.get("vehiculo"):
        _transport_equipment(shipment, envio["vehiculo"])

    for index, item in enumerate(payload.get("details") or [], start=1):
        line = _add(root, "cac", "DespatchLine")
        _add(line, "cbc", "ID", index)
        _add(
            line,
            "cbc",
            "DeliveredQuantity",
            _quantity(item["cantidad"]),
            unitCode=item["unidad"],
            unitCodeListID="UN/ECE rec 20",
            unitCodeListAgencyName="United Nations Economic Commission for Europe",
        )
        order = _add(line, "cac", "OrderLineReference")
        _add(order, "cbc", "LineID", index)
        product = _add(line, "cac", "Item")
        _add(product, "cbc", "Description", item["descripcion"])
        if item.get("codigo"):
            seller = _add(product, "cac", "SellersItemIdentification")
            _add(seller, "cbc", "ID", item["codigo"])
    return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")
