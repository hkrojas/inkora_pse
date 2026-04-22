Estructura JSON para Guía de Remisión Electrónica (GRE) - ApisPeru

Este documento detalla la estructura JSON correcta y validada para emitir una Guía de Remisión Electrónica (GRE) para un Traslado General (Venta a Terceros) en el entorno de Producción de SUNAT a través de ApisPeru.

Esta estructura cumple con las reglas estrictas de la Nueva GRE, asegurando que el punto de partida esté correctamente vinculado al local del emisor, mientras que el punto de llegada se adapta dinámicamente a la dirección de cualquier cliente.

JSON Completo Validado (Caso General: Venta)

{
  "version": 2022,
  "tipoDoc": "09",
  "serie": "T001",
  "correlativo": "000008",
  "fechaEmision": "2026-04-11T22:38:52-05:00",
  "observacion": "GUIA DE REMISION - VENTA",
  "company": {
    "ruc": 20606751509,
    "razonSocial": "PAPELERIA GRAFICA Y PUBLICITARIA SAC.",
    "nombreComercial": "PAPELERIA GRAFICA Y PUBLICITARIA SAC.",
    "address": {
      "direccion": "AV. ALFONSO  UGARTE NRO. 252 INT. 1023 BAR. MONSERRATE LIMA LIMA LIMA",
      "provincia": "LIMA",
      "departamento": "LIMA",
      "distrito": "LIMA",
      "ubigueo": "150101",
      "codLocal": "0000"
    }
  },
  "destinatario": {
    "tipoDoc": "6",
    "numDoc": 20191308868,
    "rznSocial": "ARCOR DE PERU S A"
  },
  "envio": {
    "codTraslado": "01",
    "desTraslado": "VENTA",
    "modTraslado": "02",
    "fecTraslado": "2026-04-11T22:38:52-05:00",
    "pesoTotal": 15.5,
    "undPesoTotal": "KGM",
    "numBultos": 2,
    "llegada": {
      "ubigueo": "150117",
      "direccion": "AV. INDUSTRIAL 123, PUEBLO LIBRE",
      "ruc": "20191308868"
    },
    "partida": {
      "ubigueo": "150101",
      "direccion": "AV. ALFONSO  UGARTE NRO. 252 INT. 1023 BAR. MONSERRATE LIMA LIMA LIMA",
      "codLocal": "0000",
      "ruc": "20606751509"
    },
    "vehiculo": {
      "placa": "A3N877"
    },
    "choferes": [
      {
        "tipo": "Principal",
        "tipoDoc": "1",
        "nroDoc": "72758912",
        "nombres": "Hildebrando Kennedy",
        "apellidos": "Rojas Alvarez",
        "licencia": "Q40215873"
      }
    ]
  },
  "details": [
    {
      "cantidad": 50.0,
      "unidad": "NIU",
      "descripcion": "CAJAS DE PAPEL BOND A4",
      "codigo": "PROD-001"
    }
  ]
}


Reglas Críticas de Negocio (Nueva GRE API REST)

Punto de Partida Estricto (codLocal y ruc):

En la partida (envio.partida), es obligatorio declarar de qué local oficial del emisor sale la mercadería.

Se debe enviar el codLocal (usualmente "0000" para la dirección principal) y el ruc del emisor.

Evita el Error 3365 y 3410 de SUNAT.

Punto de Llegada General (Terceros):

Cuando el traslado es una Venta (codTraslado: "01"), la mercadería va al cliente.

En la llegada (envio.llegada), NO es necesario enviar el codLocal (ya que no conoces los códigos de sucursales internas de tus clientes).

Solo debes incluir el ubigueo, la direccion de entrega, y opcionalmente el ruc del destinatario.

Peso Bruto (pesoTotal):

El peso total debe ser obligatoriamente mayor a cero (ej. 15.5).

Valores en 0 o nulos provocan rechazo inmediato en la validación de SUNAT.

Modalidades de Traslado (modTraslado):

Privado ("02"): Usas tus propios vehículos. La placa debe enviarse sin guiones (ej. A3N877). Se requiere el array choferes con un conductor de tipo "Principal".

Público ("01"): Contratas a una empresa de transportes. En este caso se elimina el nodo vehiculo y choferes, y en su lugar se envía el nodo transportista con los datos de la agencia (RUC, Razón Social, MTC, etc.).