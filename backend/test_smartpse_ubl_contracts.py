from xml.etree import ElementTree as ET

from services.smartpse_ubl_service import (
    build_despatch_document_xml,
    build_sale_document_xml,
    build_smartpse_filename,
    build_summary_document_xml,
    build_voided_document_xml,
)


NS = {
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
}


def _sale_payload(tipo_doc="01"):
    return {
        "ublVersion": "2.1",
        "tipoDoc": tipo_doc,
        "serie": "F001" if tipo_doc != "03" else "B001",
        "correlativo": "00000001",
        "fechaEmision": "2026-05-05T10:30:00-05:00",
        "tipoMoneda": "PEN",
        "company": {
            "ruc": "20123456789",
            "razonSocial": "INKORA TEST SAC",
            "address": {"direccion": "Av. Lima 100", "ubigueo": "150101"},
        },
        "client": {
            "tipoDoc": "6",
            "numDoc": "20191308868",
            "rznSocial": "CLIENTE SAC",
        },
        "mtoOperGravadas": 100,
        "mtoIGV": 18,
        "valorVenta": 100,
        "totalImpuestos": 18,
        "mtoImpVenta": 118,
        "details": [
            {
                "codProducto": "SKU-001",
                "unidad": "NIU",
                "descripcion": "Impresion de prueba",
                "cantidad": 1,
                "mtoValorUnitario": 100,
                "mtoValorVenta": 100,
                "mtoBaseIgv": 100,
                "porcentajeIgv": 18,
                "igv": 18,
                "tipAfeIgv": "10",
                "totalImpuestos": 18,
                "mtoPrecioUnitario": 118,
            }
        ],
        "legends": [{"code": "1000", "value": "CIENTO DIECIOCHO CON 00/100 SOLES"}],
    }


def test_invoice_xml_and_filename_follow_sunat_contract():
    payload = _sale_payload("01")
    xml = build_sale_document_xml(payload)
    root = ET.fromstring(xml)

    assert root.tag.endswith("Invoice")
    assert root.find("./cbc:UBLVersionID", NS).text == "2.1"
    profile = root.find("./cbc:ProfileID", NS)
    assert profile.text == "0101"
    assert profile.attrib["schemeAgencyName"] == "PE:SUNAT"
    assert profile.attrib["schemeURI"].endswith("catalogo17")
    assert root.find("./cbc:ID", NS).text == "F001-00000001"
    invoice_type = root.find("./cbc:InvoiceTypeCode", NS)
    assert invoice_type.text == "01"
    assert invoice_type.attrib["listID"] == "0101"
    assert invoice_type.attrib["listAgencyName"] == "PE:SUNAT"
    assert invoice_type.attrib["name"] == "Tipo de Operacion"
    assert invoice_type.attrib["listSchemeURI"].endswith("catalogo51")
    assert root.find("./cac:Signature/cbc:ID", NS).text == "SIGN-20123456789"
    assert root.find(
        "./cac:Signature/cac:DigitalSignatureAttachment/cac:ExternalReference/cbc:URI",
        NS,
    ).text == "#SIGN-20123456789"
    assert root.find(
        "./cac:AccountingSupplierParty/cac:Party/cac:PartyLegalEntity/cac:RegistrationAddress/cbc:AddressTypeCode",
        NS,
    ).text == "0000"
    assert root.find("./cac:PaymentTerms/cbc:ID", NS).text == "FormaPago"
    assert root.find("./cac:PaymentTerms/cbc:PaymentMeansID", NS).text == "Contado"
    assert root.find("./cac:InvoiceLine/cac:Item/cbc:Description", NS).text == "Impresion de prueba"
    assert build_smartpse_filename(payload) == "20123456789-01-F001-00000001"


def test_credit_and_debit_notes_use_note_roots_and_affected_document_reference():
    credit = _sale_payload("07")
    credit.update(
        {
            "serie": "FF01",
            "tipDocAfectado": "01",
            "numDocfectado": "F001-00000001",
            "codMotivo": "01",
            "desMotivo": "Anulacion",
        }
    )
    debit = dict(credit)
    debit["tipoDoc"] = "08"
    debit["codMotivo"] = "02"

    credit_root = ET.fromstring(build_sale_document_xml(credit))
    debit_root = ET.fromstring(build_sale_document_xml(debit))

    assert credit_root.tag.endswith("CreditNote")
    assert credit_root.find("./cbc:Note", NS).text == "CIENTO DIECIOCHO CON 00/100 SOLES"
    assert credit_root.find("./cac:DiscrepancyResponse/cbc:ReferenceID", NS).text == "F001-00000001"
    assert credit_root.find("./cac:LegalMonetaryTotal/cbc:PayableAmount", NS).text == "118.00"
    assert credit_root.find("./cac:PaymentTerms", NS) is None
    assert debit_root.tag.endswith("DebitNote")
    assert debit_root.find("./cbc:DebitNoteTypeCode", NS) is None
    assert debit_root.find("./cac:DiscrepancyResponse/cbc:ResponseCode", NS).text == "02"
    assert debit_root.find("./cac:RequestedMonetaryTotal/cbc:PayableAmount", NS).text == "118.00"


def test_despatch_xml_and_filename_follow_gre_contract():
    payload = {
        "tipoDoc": "09",
        "serie": "T001",
        "correlativo": "00000001",
        "fechaEmision": "2026-05-05T10:30:00-05:00",
        "company": {"ruc": "20123456789", "razonSocial": "INKORA TEST SAC"},
        "destinatario": {"tipoDoc": "6", "numDoc": "20191308868", "rznSocial": "CLIENTE SAC"},
        "envio": {
            "codTraslado": "01",
            "desTraslado": "VENTA",
            "modTraslado": "02",
            "fecTraslado": "2026-05-06",
            "pesoTotal": 5,
            "undPesoTotal": "KGM",
            "numBultos": 1,
            "llegada": {"ubigueo": "150101", "direccion": "Av. Destino 200"},
            "partida": {"ubigueo": "150101", "direccion": "Av. Origen 100"},
            "vehiculo": {"placa": "ABC123"},
            "choferes": [
                {
                    "tipoDoc": "1",
                    "nroDoc": "72758912",
                    "nombres": "KENNEDY",
                    "apellidos": "ROJAS",
                    "licencia": "Q12345678",
                }
            ],
        },
        "details": [{"descripcion": "Paquete", "cantidad": 2, "unidad": "NIU", "codigo": "PK-001"}],
    }

    root = ET.fromstring(build_despatch_document_xml(payload))

    assert root.tag.endswith("DespatchAdvice")
    assert root.find("./cbc:ID", NS).text == "T001-00000001"
    assert root.find("./cac:Shipment/cbc:HandlingCode", NS).text == "01"
    assert root.find("./cac:Shipment/cbc:Information", NS).text == "VENTA"
    assert root.find("./cac:Shipment/cbc:TotalTransportHandlingUnitQuantity", NS).text == "1"
    assert root.find("./cac:Shipment/cac:ShipmentStage/cac:TransitPeriod/cbc:StartDate", NS).text == "2026-05-06"
    assert root.find(
        "./cac:Shipment/cac:ShipmentStage/cac:TransportMeans/cac:RoadTransport/cbc:LicensePlateID",
        NS,
    ).text == "ABC123"
    assert root.find("./cac:Shipment/cac:ShipmentStage/cac:DriverPerson/cbc:ID", NS).text == "72758912"
    assert root.find("./cac:DespatchLine/cac:Item/cbc:Description", NS).text == "Paquete"
    assert build_smartpse_filename(payload) == "20123456789-09-T001-00000001"


def test_summary_voided_and_reversion_xml_use_batch_filename_prefixes():
    company = {"ruc": "20123456789", "razonSocial": "INKORA TEST SAC"}
    summary = {
        "tipoDoc": "RC",
        "correlativo": "20260505-001",
        "fecGeneracion": "2026-05-05T00:00:00-05:00",
        "fecResumen": "2026-05-05T00:00:00-05:00",
        "company": company,
        "details": [
            {
                "tipoDoc": "03",
                "serieNro": "B001-00000001",
                "estado": "1",
                "total": 118,
                "mtoOperGravadas": 100,
                "mtoIGV": 18,
            }
        ],
    }
    voided = {
        "tipoDoc": "RA",
        "correlativo": "20260505-001",
        "fecGeneracion": "2026-05-05T00:00:00-05:00",
        "fecComunicacion": "2026-05-05T00:00:00-05:00",
        "company": company,
        "details": [{"tipoDoc": "01", "serie": "F001", "correlativo": "00000001", "desMotivoBaja": "ERROR"}],
    }
    reversion = dict(voided)
    reversion["tipoDoc"] = "RR"

    assert ET.fromstring(build_summary_document_xml(summary)).tag.endswith("SummaryDocuments")
    summary_root = ET.fromstring(build_summary_document_xml(summary))
    assert summary_root.find("./cac:AccountingSupplierParty/cbc:CustomerAssignedAccountID", NS).text == "20123456789"
    summary_ns = {**NS, "sac": "urn:sunat:names:specification:ubl:peru:schema:xsd:SunatAggregateComponents-1"}
    assert summary_root.find("./sac:SummaryDocumentsLine/cac:Status/cbc:ConditionCode", summary_ns).text == "1"
    assert summary_root.find("./sac:SummaryDocumentsLine/sac:BillingPayment/cbc:InstructionID", summary_ns).text == "01"
    assert summary_root.find("./sac:SummaryDocumentsLine/cac:TaxTotal/cbc:TaxAmount", summary_ns).text == "18.00"
    voided_root = ET.fromstring(build_voided_document_xml(voided))
    assert voided_root.tag.endswith("VoidedDocuments")
    assert voided_root.find("./cac:AccountingSupplierParty/cbc:CustomerAssignedAccountID", NS).text == "20123456789"
    assert ET.fromstring(build_voided_document_xml(reversion)).tag.endswith("VoidedDocuments")
    assert build_smartpse_filename(summary) == "20123456789-RC-20260505-001"
    assert build_smartpse_filename(voided) == "20123456789-RA-20260505-001"
    assert build_smartpse_filename(reversion) == "20123456789-RR-20260505-001"
