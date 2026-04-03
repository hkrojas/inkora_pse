import os
import zipfile
import base64
from datetime import datetime
from lxml import etree
from lxml.builder import ElementMaker
import xmltodict
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.backends import default_backend
from signxml import XMLSigner, XMLVerifier, methods
from zeep import Client
from zeep.transports import Transport
import requests

# Namespaces UBL 2.1
NS_MAP = {
    None: "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "ds": "http://www.w3.org/2000/09/xmldsig#",
    "ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
}

E = ElementMaker(nsmap=NS_MAP)
CBC = ElementMaker(namespace=NS_MAP["cbc"])
CAC = ElementMaker(namespace=NS_MAP["cac"])
EXT = ElementMaker(namespace=NS_MAP["ext"])

class SUNATService:
    def __init__(self, ruc: str, usuario_sol: str, clave_sol: str, cert_data: bytes = None, cert_password: str = None):
        self.ruc = ruc
        self.usuario_sol = usuario_sol
        self.clave_sol = clave_sol
        self.cert_data = cert_data
        self.cert_password = cert_password
        
        # Endpoints SUNAT (Beta por defecto)
        self.ws_url = "https://e-beta.sunat.gob.pe/ol-ti-itcpfegem-beta/billService?wsdl"

    def generate_invoice_ubl(self, data: dict) -> str:
        """
        Genera el XML Invoice UBL 2.1.
        'data' debe contener campos como: serie, correlativo, fecha, emisor, cliente, items, totales.
        """
        doc = E.Invoice(
            EXT.UBLExtensions(
                EXT.UBLExtension(
                    EXT.ExtensionContent("") # Aquí irá la firma
                )
            ),
            CBC.UBLVersionID("2.1"),
            CBC.CustomizationID("2.0"),
            CBC.ID(f"{data['serie']}-{data['correlativo']}"),
            CBC.IssueDate(data['fecha_emision']),
            CBC.IssueTime(data.get('hora_emision', '00:00:00')),
            CBC.InvoiceTypeCode(data['tipo_comprobante'], listID="0101"),
            CBC.Note(data.get('monto_letras', ''), languageLocaleID="1000"),
            CBC.DocumentCurrencyCode("PEN"),
            # Emisor
            CAC.Signature(
                CBC.ID(self.ruc),
                CAC.SignatoryParty(
                    CAC.PartyIdentification(CBC.ID(self.ruc)),
                    CAC.PartyName(CBC.Name(data['emisor']['nombre']))
                ),
                CAC.DigitalSignatureAttachment(
                    CAC.ExternalReference(CBC.URI("#SIGN-" + self.ruc))
                )
            ),
            CAC.AccountingSupplierParty(
                CAC.Party(
                    CAC.PartyIdentification(CBC.ID(self.ruc)),
                    CAC.PartyName(CBC.Name(data['emisor']['nombre'])),
                    CAC.PartyLegalEntity(
                        CBC.RegistrationName(data['emisor']['nombre']),
                        CAC.RegistrationAddress(
                            CBC.ID(data['emisor'].get('ubigeo', '150101')),
                            CBC.AddressLine(CBC.Line(data['emisor'].get('direccion', '-')))
                        )
                    )
                )
            ),
            # Cliente
            CAC.AccountingCustomerParty(
                CAC.Party(
                    CAC.PartyIdentification(
                        CBC.ID(data['cliente']['numero_documento'], schemeID=data['cliente']['tipo_documento'])
                    ),
                    CAC.PartyLegalEntity(
                        CBC.RegistrationName(data['cliente']['nombre']),
                    )
                )
            ),
            # Totales
            CAC.TaxTotal(
                CBC.TaxAmount(str(data['total_igv']), currencyID="PEN"),
                CAC.TaxSubtotal(
                    CBC.TaxableAmount(str(data['total_gravada']), currencyID="PEN"),
                    CBC.TaxAmount(str(data['total_igv']), currencyID="PEN"),
                    CAC.TaxCategory(
                        CAC.TaxScheme(
                            CBC.ID("1000"),
                            CBC.Name("IGV"),
                            CBC.TaxTypeCode("VAT")
                        )
                    )
                )
            ),
            CAC.LegalMonetaryTotal(
                CBC.LineExtensionAmount(str(data['total_gravada']), currencyID="PEN"),
                CBC.TaxInclusiveAmount(str(data['total_venta']), currencyID="PEN"),
                CBC.PayableAmount(str(data['total_venta']), currencyID="PEN")
            )
        )
        
        # Items
        for i, item in enumerate(data['items'], 1):
            line = CAC.InvoiceLine(
                CBC.ID(str(i)),
                CBC.InvoicedQuantity(str(item['cantidad']), unitCode="NIU"),
                CBC.LineExtensionAmount(str(item['valor_venta']), currencyID="PEN"),
                CAC.PricingReference(
                    CAC.AlternativeConditionPrice(
                        CBC.PriceAmount(str(item['precio_unitario']), currencyID="PEN"),
                        CBC.PriceTypeCode("01")
                    )
                ),
                CAC.TaxTotal(
                    CBC.TaxAmount(str(item['igv']), currencyID="PEN"),
                    CAC.TaxSubtotal(
                        CBC.TaxableAmount(str(item['valor_venta']), currencyID="PEN"),
                        CBC.TaxAmount(str(item['igv']), currencyID="PEN"),
                        CAC.TaxCategory(
                            CBC.Percent("18.00"),
                            CBC.TaxExemptionReasonCode("10"),
                            CAC.TaxScheme(
                                CBC.ID("1000"),
                                CBC.Name("IGV"),
                                CBC.TaxTypeCode("VAT")
                            )
                        )
                    )
                ),
                CAC.Item(
                    CBC.Description(item['descripcion'])
                ),
                CAC.Price(
                    CBC.PriceAmount(str(item['valor_unitario']), currencyID="PEN")
                )
            )
            doc.append(line)

        return etree.tostring(doc, encoding="utf-8", xml_declaration=True, pretty_print=True).decode()

    def sign_xml(self, xml_str: str) -> str:
        """
        Firma el XML usando el estándar XMLDSIG compatible con SUNAT.
        Inserta la firma en UBLExtension/ExtensionContent.
        """
        if not self.cert_data:
            raise ValueError("Certificado digital no cargado.")
            
        from cryptography.hazmat.primitives.serialization import pkcs12, NoEncryption, Encoding, PrivateFormat
        p12 = pkcs12.load_key_and_certificates(self.cert_data, self.cert_password.encode(), default_backend())
        key = p12[0].private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
        cert = p12[1].public_bytes(Encoding.PEM)
        
        parser = etree.XMLParser(remove_blank_text=True)
        root = etree.fromstring(xml_str.encode(), parser)
        
        # El ID de la firma suele ser SIGN- + RUC
        signer = XMLSigner(
            signature_algorithm="rsa-sha256",
            digest_algorithm="sha256"
        )
        
        # Referenciamos el root
        signed_node = signer.sign(root, key=key, cert=cert)
        
        # En UBL, la firma debe ir dentro de ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent
        # Pero signxml devuelve el root con el nodo Signature al final.
        # Vamos a moverlo.
        signature_node = signed_node.find("{http://www.w3.org/2000/09/xmldsig#}Signature")
        
        # Buscar el contenedor de la extensión
        ext_content = signed_node.find(".//{urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2}ExtensionContent")
        if ext_content is not None:
            ext_content.append(signature_node)
        
        return etree.tostring(signed_node, encoding="utf-8", xml_declaration=True).decode()

    @staticmethod
    def get_cert_from_storage(cert_url: str) -> bytes:
        """Descarga el certificado desde Supabase Storage (URL pública o firmada)."""
        response = requests.get(cert_url)
        response.raise_for_status()
        return response.content

    def send_bill(self, filename: str, content_xml: str) -> dict:
        """
        Empaqueta en ZIP y envía a SUNAT vía SOAP.
        """
        # Crear ZIP en memoria
        from io import BytesIO
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            zip_file.writestr(f"{filename}.xml", content_xml)
        
        zip_base64 = base64.b64encode(zip_buffer.getvalue()).decode()
        
        # Configurar SOAP con headers de autenticación (Token SOL)
        # SUNAT requiere: UsernameToken (RUC + UsuarioSOL, ClaveSOL)
        # Usaremos zeep con WS-Security o manualmente en el header
        
        # Por simplicidad en este prototipo, usamos headers manuales si Zeep se complica
        # Pero intentaremos Zeep:
        from zeep.wsse.username import UsernameToken
        
        client = Client(self.ws_url, wsse=UsernameToken(self.ruc + self.usuario_sol, self.clave_sol))
        
        try:
            # Invocar sendBill(fileName, contentFile)
            # SUNAT responde con un CDR en base64 (zip)
            response_encoded = client.service.sendBill(f"{filename}.zip", zip_base64)
            
            # Decodificar CDR
            cdr_zip = base64.b64decode(response_encoded)
            
            # Extraer respuesta del CDR
            with zipfile.ZipFile(BytesIO(cdr_zip)) as z:
                xml_cdr = z.read(z.namelist()[0])
                # Parsear XML del CDR para ver si fue aceptada
                res_dict = xmltodict.parse(xml_cdr)
                # El estado está en cac:DocumentResponse/cac:Response/cbc:ResponseCode
                
            return {
                "success": True,
                "cdr_zip": cdr_zip,
                "raw_response": res_dict
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
