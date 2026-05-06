# Smart PSE: campos XML obligatorios y optativos validados

Fecha: 2026-05-05

Este documento resume los campos XML UBL que Inkora debe generar para los documentos que Smart PSE logro firmar correctamente en demo.

Alcance validado:

- Factura `01`: firmada y aceptada.
- Boleta `03`: firmada y aceptada.
- Nota de credito `07`: firmada y aceptada.
- Nota de debito `08`: firmada y aceptada.
- Resumen diario `RC`: firmado y aceptado.
- Comunicacion de baja `RA`: firmada y aceptada.
- Guia de remision `09`: firmada por Smart PSE y queda `Pendiente`; no hay CDR final en demo.

Fuera de alcance:

- Reversion `RR`: Smart PSE no la valido como CPE soportado en las pruebas. Mantener bloqueada hasta confirmacion del proveedor.
- Retenciones/percepciones: no estan cubiertas por las pruebas de firma Smart PSE.

## Contrato Smart PSE

Para todos los documentos se envia:

| Campo API | Obligatorio | Descripcion |
| --- | --- | --- |
| `nombre_archivo` | Si | Nombre SUNAT sin extension. Ejemplo: `20606751509-01-F001-000008`. |
| `contenido_archivo` | Si | XML UBL sin firmar, codificado en base64. |

Endpoint:

- Demo: `POST /api/cpe/procesar-demo`
- Produccion: `POST /api/cpe/procesar`

Para `RC` y `RA`, el resultado puede ser asincrono y se consulta con `GET /api/cpe/consultar/{nombre_archivo}`.

Para `GRE`, en las pruebas Smart PSE firma y devuelve ticket, pero el endpoint de consulta documentado aplica a resumenes y no devuelve estado final de guia.

## Convenciones globales XML

Campos comunes obligatorios en los XML firmados:

| Nodo | Obligatorio | Aplica a | Notas |
| --- | --- | --- | --- |
| `ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent` | Si | Todos | Smart PSE inserta la firma digital. |
| `cbc:UBLVersionID` | Si | Todos | `2.1` para factura, boleta, NC, ND y GRE. `2.0` para RC/RA. |
| `cbc:CustomizationID` | Si | Todos | `2.0` para CPE UBL 2.1. `1.1` para RC. `1.0` para RA. |
| `cbc:ID` | Si | Todos | Serie-correlativo o identificador RC/RA. |
| `cbc:IssueDate` | Si | Todos | Fecha de emision/generacion. |
| `cac:Signature` | Si | Todos | ID recomendado: `SIGN-{RUC}`. |
| Emisor | Si | Todos | RUC, razon social, direccion cuando aplique. |

Campos comunes optativos o condicionados:

| Nodo | Condicion |
| --- | --- |
| `cbc:IssueTime` | Usarlo siempre que Inkora tenga hora. Fue usado en los XML firmados. |
| `cbc:Note` | Leyendas, monto en letras, observaciones. |
| `cac:AdditionalDocumentReference` | Documentos relacionados, ordenes, guias, anticipos, percepciones segun caso. |
| `cac:AllowanceCharge` | Descuentos o cargos globales/por linea. |
| Campos de detraccion | Solo si la operacion esta sujeta a detraccion. |
| Campos de cuotas | Solo si la forma de pago es credito. |

## Factura y boleta

Raiz:

- Factura: `Invoice`, `cbc:InvoiceTypeCode = 01`
- Boleta: `Invoice`, `cbc:InvoiceTypeCode = 03`

Nombre de archivo:

- `RUC-01-SERIE-CORRELATIVO`
- `RUC-03-SERIE-CORRELATIVO`

### Obligatorios

| Nodo XML | Fuente Inkora | Nota |
| --- | --- | --- |
| `cbc:UBLVersionID` | constante | `2.1` |
| `cbc:CustomizationID` | constante | `2.0` |
| `cbc:ProfileID` | `tipoOperacion` | Ejemplo `0101`; debe llevar atributos SUNAT del catalogo 17. |
| `cbc:ID` | `serie-correlativo` | Ejemplo `F001-000008`. |
| `cbc:IssueDate` | `fechaEmision` | Fecha del comprobante. |
| `cbc:IssueTime` | `fechaEmision` | Hora del comprobante. |
| `cbc:InvoiceTypeCode` | `tipoDoc` | `01` o `03`; debe llevar atributos SUNAT de tipo de operacion. |
| `cbc:DocumentCurrencyCode` | `tipoMoneda` | Ejemplo `PEN`. |
| `cac:Signature` | empresa | `SIGN-{RUC}`. |
| `cac:AccountingSupplierParty` | empresa | RUC, razon social, nombre comercial, direccion, ubigeo, codigo de local. |
| `cac:AccountingCustomerParty` | cliente | Tipo doc, numero doc, razon social. |
| `cac:PaymentTerms` | forma de pago | `FormaPago` + `Contado` o `Credito`. |
| `cac:TaxTotal` | totales | IGV total y subtotal tributario. |
| `cac:LegalMonetaryTotal` | totales | Valor venta, importe total, monto a pagar. |
| `cac:InvoiceLine` | items | Al menos una linea. |

Campos obligatorios por linea:

| Nodo XML | Fuente Inkora | Nota |
| --- | --- | --- |
| `cbc:ID` | indice | Numero de linea. |
| `cbc:InvoicedQuantity` | cantidad + unidad | `unitCode` SUNAT, por ejemplo `NIU`. |
| `cbc:LineExtensionAmount` | valor venta item | Sin IGV. |
| `cac:PricingReference/cac:AlternativeConditionPrice/cbc:PriceAmount` | precio unitario con IGV | Precio de venta. |
| `cbc:PriceTypeCode` | constante | `01` para precio unitario incluido IGV. |
| `cac:TaxTotal` | impuestos item | Base, IGV, categoria, codigo de afectacion. |
| `cac:Item/cbc:Description` | descripcion | Descripcion del bien/servicio. |
| `cac:SellersItemIdentification/cbc:ID` | codigo producto | Si no hay codigo, generar uno estable. |
| `cac:Price/cbc:PriceAmount` | valor unitario sin IGV | Valor unitario. |

### Optativos o condicionados

| Campo XML | Cuando usarlo |
| --- | --- |
| `cbc:Note languageLocaleID="1000"` | Monto en letras. Recomendado. |
| `cac:PaymentTerms` adicionales `Cuota001`, `Cuota002` | Solo credito. |
| `cac:AllowanceCharge` | Descuentos o cargos. |
| `cac:PrepaidPayment` | Anticipos. |
| `cac:DespatchDocumentReference` | Si la factura esta vinculada a guia. |
| `cac:OrderReference` | Si hay orden de compra. |
| Datos de detraccion | Si la operacion esta sujeta a detraccion. |
| Direccion completa del cliente | Recomendado para factura; condicionado para boleta segun caso. |

## Nota de credito

Raiz:

- `CreditNote`

Nombre de archivo:

- `RUC-07-SERIE-CORRELATIVO`

### Obligatorios

| Nodo XML | Fuente Inkora | Nota |
| --- | --- | --- |
| `cbc:UBLVersionID` | constante | `2.1` |
| `cbc:CustomizationID` | constante | `2.0` |
| `cbc:ProfileID` | `tipoOperacion` | Mantener `0101` salvo operacion especifica. |
| `cbc:ID` | `serie-correlativo` | Serie y numero de la nota. |
| `cbc:IssueDate` / `cbc:IssueTime` | `fechaEmision` | Fecha y hora. |
| `cbc:CreditNoteTypeCode` | `codMotivo` | Motivo SUNAT de NC. |
| `cbc:DocumentCurrencyCode` | `tipoMoneda` | Moneda. |
| `cac:DiscrepancyResponse/cbc:ReferenceID` | doc afectado | Ejemplo `F001-000008`. |
| `cac:DiscrepancyResponse/cbc:ResponseCode` | `codMotivo` | Codigo de motivo. |
| `cac:DiscrepancyResponse/cbc:Description` | `desMotivo` | Motivo textual. |
| `cac:BillingReference/cac:InvoiceDocumentReference/cbc:ID` | doc afectado | Documento que se modifica. |
| `cac:BillingReference/.../cbc:DocumentTypeCode` | tipo doc afectado | `01`, `03`, etc. |
| `cac:Signature` | empresa | Firma. |
| `cac:AccountingSupplierParty` | empresa | Emisor. |
| `cac:AccountingCustomerParty` | cliente | Cliente. |
| `cac:TaxTotal` | totales | Impuestos de la nota. |
| `cac:LegalMonetaryTotal` | totales | Totales de la nota. |
| `cac:CreditNoteLine` | items | Al menos una linea. |

Campos obligatorios por linea:

- `cbc:ID`
- `cbc:CreditedQuantity`
- `cbc:LineExtensionAmount`
- `cac:PricingReference`
- `cac:TaxTotal`
- `cac:Item/cbc:Description`
- `cac:SellersItemIdentification/cbc:ID`
- `cac:Price/cbc:PriceAmount`

### Optativos o condicionados

| Campo XML | Cuando usarlo |
| --- | --- |
| `cbc:Note` | Leyenda o monto en letras. |
| `cac:AdditionalDocumentReference` | Documentos relacionados. |
| `cac:AllowanceCharge` | Descuentos/cargos relacionados a la nota. |
| Referencias adicionales | Cuando la NC afecte anticipos u otros documentos. |

## Nota de debito

Raiz:

- `DebitNote`

Nombre de archivo:

- `RUC-08-SERIE-CORRELATIVO`

### Obligatorios

| Nodo XML | Fuente Inkora | Nota |
| --- | --- | --- |
| `cbc:UBLVersionID` | constante | `2.1` |
| `cbc:CustomizationID` | constante | `2.0` |
| `cbc:ProfileID` | `tipoOperacion` | Mantener `0101` salvo operacion especifica. |
| `cbc:ID` | `serie-correlativo` | Serie y numero de la nota. |
| `cbc:IssueDate` / `cbc:IssueTime` | `fechaEmision` | Fecha y hora. |
| `cbc:DocumentCurrencyCode` | `tipoMoneda` | Moneda. |
| `cac:DiscrepancyResponse/cbc:ReferenceID` | doc afectado | Documento que se modifica. |
| `cac:DiscrepancyResponse/cbc:ResponseCode` | `codMotivo` | Motivo SUNAT de ND. |
| `cac:DiscrepancyResponse/cbc:Description` | `desMotivo` | Motivo textual. |
| `cac:BillingReference/cac:InvoiceDocumentReference/cbc:ID` | doc afectado | Documento afectado. |
| `cac:BillingReference/.../cbc:DocumentTypeCode` | tipo doc afectado | `01`, `03`, etc. |
| `cac:Signature` | empresa | Firma. |
| `cac:AccountingSupplierParty` | empresa | Emisor. |
| `cac:AccountingCustomerParty` | cliente | Cliente. |
| `cac:TaxTotal` | totales | Impuestos de la nota. |
| `cac:RequestedMonetaryTotal` | totales | Total solicitado. |
| `cac:DebitNoteLine` | items | Al menos una linea. |

Campos obligatorios por linea:

- `cbc:ID`
- `cbc:DebitedQuantity`
- `cbc:LineExtensionAmount`
- `cac:PricingReference`
- `cac:TaxTotal`
- `cac:Item/cbc:Description`
- `cac:SellersItemIdentification/cbc:ID`
- `cac:Price/cbc:PriceAmount`

### Regla validada con Smart PSE

En la prueba aceptada, la ND no incluyo `cbc:DebitNoteTypeCode`. El motivo se declaro en `cac:DiscrepancyResponse/cbc:ResponseCode`.

### Optativos o condicionados

| Campo XML | Cuando usarlo |
| --- | --- |
| `cbc:Note` | Leyenda o monto en letras. |
| `cac:AdditionalDocumentReference` | Documentos relacionados. |
| `cac:AllowanceCharge` | Cargos/descuentos de la nota. |

## Resumen diario

Raiz:

- `SummaryDocuments`

Nombre de archivo:

- `RUC-RC-FECHA-CORRELATIVO`
- Ejemplo: `20606751509-RC-20260505-104`

### Obligatorios

| Nodo XML | Fuente Inkora | Nota |
| --- | --- | --- |
| `cbc:UBLVersionID` | constante | `2.0` |
| `cbc:CustomizationID` | constante | `1.1` |
| `cbc:ID` | correlativo RC | Dentro del XML: `RC-{correlativo}`. |
| `cbc:ReferenceDate` | fecha de documentos | Fecha de boletas/notas resumidas. |
| `cbc:IssueDate` | fecha generacion | Fecha de envio del resumen. |
| `cac:Signature` | empresa | Firma. |
| `cac:AccountingSupplierParty/cbc:CustomerAssignedAccountID` | RUC emisor | Estructura legacy UBL 2.0. |
| `cac:AccountingSupplierParty/cbc:AdditionalAccountID` | tipo doc emisor | `6`. |
| `sac:SummaryDocumentsLine` | detalles | Al menos una linea. |

Campos obligatorios por linea:

| Nodo XML | Fuente Inkora | Nota |
| --- | --- | --- |
| `cbc:LineID` | indice | Numero de linea. |
| `cbc:DocumentTypeCode` | tipo doc | Normalmente `03`, `07`, `08`. |
| `cbc:ID` | serie-numero | Documento incluido en el resumen. |
| `cac:AccountingCustomerParty` | cliente | Tipo y numero de documento. |
| `cac:Status/cbc:ConditionCode` | estado | `1` adicionar, `2` modificar, `3` anular, segun SUNAT. |
| `sac:TotalAmount` | total documento | Total por comprobante. |
| `sac:BillingPayment` | importes por tipo operacion | Gravada/exonerada/inafecta/exportacion segun corresponda. |
| `cac:TaxTotal` | impuestos | IGV y otros tributos. |

### Optativos o condicionados

| Campo XML | Cuando usarlo |
| --- | --- |
| Multiples `sac:BillingPayment` | Cuando hay gravadas, exoneradas, inafectas u otros montos. |
| `sac:PerceptionSummaryDocumentReference` | Si aplica percepcion. |
| Lineas de notas | Si se resumen NC/ND de boletas. |

## Comunicacion de baja

Raiz:

- `VoidedDocuments`

Nombre de archivo:

- `RUC-RA-FECHA-CORRELATIVO`
- Ejemplo: `20606751509-RA-20260505-101`

### Obligatorios

| Nodo XML | Fuente Inkora | Nota |
| --- | --- | --- |
| `cbc:UBLVersionID` | constante | `2.0` |
| `cbc:CustomizationID` | constante | `1.0` |
| `cbc:ID` | correlativo RA | Dentro del XML: `RA-{correlativo}`. |
| `cbc:ReferenceDate` | fecha del comprobante | Fecha del documento que se da de baja. |
| `cbc:IssueDate` | fecha generacion | Fecha de la comunicacion. |
| `cac:Signature` | empresa | Firma. |
| `cac:AccountingSupplierParty/cbc:CustomerAssignedAccountID` | RUC emisor | Estructura legacy UBL 2.0. |
| `cac:AccountingSupplierParty/cbc:AdditionalAccountID` | tipo doc emisor | `6`. |
| `sac:VoidedDocumentsLine` | detalles | Al menos una linea. |

Campos obligatorios por linea:

| Nodo XML | Fuente Inkora | Nota |
| --- | --- | --- |
| `cbc:LineID` | indice | Numero de linea. |
| `cbc:DocumentTypeCode` | tipo doc | Tipo del comprobante dado de baja. |
| `sac:DocumentSerialID` | serie | Serie del comprobante. |
| `sac:DocumentNumberID` | correlativo | Numero del comprobante. |
| `sac:VoidReasonDescription` | motivo | Motivo de baja. |

### Optativos o condicionados

| Campo XML | Cuando usarlo |
| --- | --- |
| Multiples lineas | Si se dan de baja varios comprobantes de la misma fecha. |
| Motivo normalizado interno | Recomendado para trazabilidad, aunque SUNAT recibe texto. |

## Guia de remision

Raiz:

- `DespatchAdvice`

Nombre de archivo:

- `RUC-09-SERIE-CORRELATIVO`
- Ejemplo: `20606751509-09-T001-000003`

Estado de prueba:

- Smart PSE firmo el XML y devolvio hash/ticket.
- La guia queda `Pendiente` en panel demo.
- No se obtuvo CDR final por API documentada.

### Campos API adicionales obligatorios para GRE

Smart PSE exige estos campos en el payload de `procesar-demo` para guias:

| Campo | Obligatorio | Nota |
| --- | --- | --- |
| `client_id_sunat` | Si | Credencial API SUNAT. |
| `client_secret_sunat` | Si | Secreto API SUNAT. |
| `sol_user` | Si | En pruebas funciono como `RUC + usuario SOL`, no solo usuario. |
| `sol_password` | Si | Clave SOL. |

### Obligatorios minimos firmados por Smart PSE

| Nodo XML | Fuente Inkora | Nota |
| --- | --- | --- |
| `cbc:UBLVersionID` | constante | `2.1` |
| `cbc:CustomizationID` | constante | `2.0` |
| `cbc:ID` | `serie-correlativo` | Ejemplo `T001-000003`. |
| `cbc:IssueDate` / `cbc:IssueTime` | `fechaEmision` | Fecha y hora de emision. |
| `cbc:DespatchAdviceTypeCode` | constante | `09`. |
| `cac:Signature` | empresa | Firma. |
| Emisor | empresa | RUC, razon social, direccion. |
| `cac:DeliveryCustomerParty` | destinatario | Tipo doc, numero doc, razon social. |
| `cac:Shipment/cbc:ID` | constante | `1`. |
| `cac:Shipment/cac:ShipmentStage/cbc:TransportModeCode` | `envio.modTraslado` | `01` publico, `02` privado. |
| `cac:Shipment/cac:Delivery/cac:DeliveryAddress` | llegada | Ubigeo y direccion. |
| `cac:Shipment/cac:Delivery/cac:DespatchAddress` | partida | Ubigeo y direccion. |
| `cac:Shipment/cbc:GrossWeightMeasure` | peso | Peso total y unidad, por ejemplo `KGM`. |
| `cac:DespatchLine` | items | Al menos una linea. |

Campos obligatorios por linea:

- `cbc:ID`
- `cbc:DeliveredQuantity` con `unitCode`
- `cac:Item/cbc:Description`
- `cac:SellersItemIdentification/cbc:ID`

### Obligatorios SUNAT a completar antes de produccion

Aunque Smart PSE firmo el XML minimo, GRE debe endurecerse antes de produccion porque SUNAT exige datos de traslado que no siempre estan en el XML minimo:

| Campo XML | Fuente Inkora | Condicion |
| --- | --- | --- |
| Motivo de traslado | `envio.codTraslado` / `envio.desTraslado` | Recomendado como obligatorio operativo. |
| Fecha de inicio de traslado | `envio.fecTraslado` | Obligatorio operativo GRE. |
| Numero de bultos | `envio.numBultos` | Condicionado al caso; recomendable capturarlo. |
| Vehiculo / placa | `envio.vehiculo.placa` | Obligatorio en transporte privado. |
| Conductores | `envio.choferes` | Obligatorio en transporte privado. |
| Transportista | `envio.transportista` | Obligatorio en transporte publico. |
| Documento relacionado | factura/boleta | Condicionado si la guia respalda venta u otro comprobante. |
| Codigo de local de partida | `envio.partida.codLocal` | Recomendado para evitar rechazos de locales SUNAT. |
| RUC de partida/llegada | partida/llegada | Condicionado por tipo de traslado. |

### Optativos o condicionados

| Campo XML | Cuando usarlo |
| --- | --- |
| `cbc:Note` | Observaciones de la guia. |
| `cac:AdditionalDocumentReference` | Factura/boleta relacionada u otros documentos. |
| Datos de contenedor | Transporte con contenedores. |
| Subcontratacion de transporte | Si aplica transporte publico/subcontratado. |
| Direcciones extendidas | Cuando se tenga provincia, distrito, departamento. |

## Reglas de implementacion para Inkora

1. El frontend debe seguir enviando JSON Inkora.
2. El backend debe transformar JSON Inkora a un DTO fiscal canonico y luego a XML UBL.
3. No exponer credenciales Smart PSE ni credenciales SUNAT/GRE al tenant.
4. Si falta un campo obligatorio, bloquear antes de enviar a Smart PSE con mensaje claro.
5. Si Smart PSE devuelve `xml_firmado`, guardar XML firmado, hash y respuesta cruda.
6. Si el CDR no existe, no marcar como aceptado.
7. Para GRE demo, guardar estado `pendiente_smartpse` hasta tener confirmacion final.
8. Para RC/RA, consultar solo con el endpoint documentado de resumenes.
9. Para RR, mantener bloqueado hasta confirmacion formal de Smart PSE.

## Fuentes

- Smart PSE, documentacion API: https://smartpse.pe/documentacion
- SUNAT, guia XML factura UBL 2.1: https://cpe.sunat.gob.pe/sites/default/files/inline-files/guia%2Bxml%2Bfactura%2Bversion%202-1%2B1%2B0%20%282%29_0%20%282%29.pdf
- SUNAT, manual del programador CPE: https://cpe.sunat.gob.pe/sites/default/files/inline-files/manual_programador%20%281%29.pdf
- SUNAT, manual servicios GRE: https://cpe.sunat.gob.pe/sites/default/files/inline-files/Manual_Servicios_GRE%20%281%29.pdf
- SUNAT, guia de remision electronica: https://cpe.sunat.gob.pe/tipos_de_comprobantes/guiaderemision
