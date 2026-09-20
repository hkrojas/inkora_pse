# Módulos de producto de Inkora

> Documento vivo de ideas y decisiones de producto. Registrar aquí una idea no autoriza su implementación ni significa que forme parte del lanzamiento.

Última actualización: 21 de agosto de 2026.

## Visión del producto

Inkora busca ser un sistema de facturación y control operativo adaptable a distintos negocios peruanos. El producto no debe crear un flujo diferente para cada rubro; debe ofrecer un núcleo común y permitir que cada empresa utilice los módulos que necesita.

Propuesta de valor preliminar:

> Facturación y control de negocio para empresas que cotizan, venden, entregan mercadería o servicios y necesitan controlar su operación.

La experiencia debe ser sencilla para un negocio pequeño, pero conservar trazabilidad suficiente para empresas con inventario, cotizaciones personalizadas, ventas a crédito y documentos fiscales.

## Principios de diseño del producto

- Mantener un núcleo general reutilizable entre distintos tipos de negocio.
- Conservar los módulos existentes; simplificar su presentación según el rol y contexto del usuario.
- Permitir productos con stock, servicios sin stock y operaciones mixtas.
- No obligar a una empresa de servicios a utilizar almacén o kardex.
- Relacionar cotización, comprobante, guía, salida de inventario y cobranza.
- Ocultar complejidad fiscal durante el uso normal y mostrarla cuando exista una acción o riesgo.
- No confiar en precios calculados por inteligencia artificial: todo precio debe provenir de reglas, fórmulas o listas autorizadas.
- No exigir que el cliente escriba prompts, configure agentes ni defina instrucciones técnicas.
- El asistente debe adaptarse automáticamente al catálogo y reglas vigentes de cada empresa, con aislamiento estricto entre tenants.
- Mantener auditoría de cambios relacionados con precios, descuentos, crédito y pagos.
- No convertir Inkora en un ERP genérico antes de estabilizar el alcance de lanzamiento.

## Estados usados en este documento

- **Actual:** módulo o dominio que ya existe en el proyecto; requiere confirmar su nivel real de terminación antes de ofrecerlo comercialmente.
- **Propuesto:** idea aceptada para evaluación de producto.
- **Futuro:** idea valiosa que no debería competir con la estabilización actual.
- **Congelado:** dominio existente fuera del alcance del lanzamiento; no ampliar sin una decisión explícita.

## Módulos actuales que conforman el núcleo

Estos dominios forman parte del sistema actual o del alcance de lanzamiento conocido:

- Autenticación, empresas, usuarios, roles y permisos.
- Clientes.
- Productos y servicios.
- Cotizaciones y personalización de sus documentos.
- Facturas y boletas.
- Notas de crédito y débito.
- Guías de remisión.
- Etiquetas de despacho.
- Inventario, almacén y kardex.
- Pagos y cobranza.
- Dashboard y resumen operativo.
- Reportes.
- Configuración de la empresa.
- Operaciones fiscales auxiliares: resumen diario, bajas, reversiones, retenciones y percepciones.
- Emisión fiscal, trabajos en cola y SmartPSE.
- Almacenamiento de PDF, XML y CDR.
- Administración interna y superadministración.

### Productos y servicios

Cada ítem comercial debería distinguir al menos entre:

- **Producto con stock:** su venta o despacho puede producir movimientos de inventario y kardex.
- **Servicio sin stock:** puede cotizarse, facturarse y cobrarse sin pedir almacén ni afectar existencias.

Una misma cotización o comprobante puede contener ambos tipos. Por ejemplo, una clínica podría vender una consulta y medicamentos; un taller podría vender mano de obra y repuestos.

## Módulos propuestos

### 1. Asistente de precios y cotización

**Estado:** Propuesto — prioridad de producto alta después de estabilizar el núcleo.

**Problema:** en muchos negocios los precios dependen del dueño o vendedor experimentado. Cuando esa persona se ausenta, otros trabajadores no pueden cotizar con seguridad.

**Objetivo:** capturar el conocimiento comercial del negocio y permitir que un trabajador autorizado calcule y prepare una cotización sin inventar precios ni llamar al dueño.

Ejemplo de solicitud:

> Cotiza 10 talonarios autocopiativos CB, original y copia, tamaño A5, 50 juegos, numerados.

Capacidades propuestas:

- Recibir una solicitud en lenguaje natural.
- Detectar los datos presentes y preguntar únicamente los faltantes.
- Aplicar fórmulas, materiales, cantidades, desperdicio, mano de obra, acabado y margen.
- Mostrar precio unitario, total y un desglose comprensible.
- Convertir el resultado directamente en una cotización editable.
- Consultar productos, servicios, listas de precios e historial autorizado.
- Indicar qué regla o lista produjo el precio.
- Impedir precios inferiores al mínimo configurado.
- Solicitar aprobación cuando el descuento o margen esté fuera de los límites del usuario.
- Mantener registro del cálculo, versión de la regla y persona que lo confirmó.

El chat sería la interfaz de consulta. La fuente real del cálculo debe ser un motor determinista de reglas y fórmulas; el modelo conversacional no puede inventar precios, descuentos ni condiciones.

#### Experiencia sin prompts

El usuario no debe recibir una caja vacía donde tenga que explicar cómo funciona su negocio ni aprender a escribir instrucciones para una IA. Inkora debe proporcionar el asistente listo para usar y limitarlo mediante permisos, herramientas y reglas construidas por el sistema.

Comportamiento esperado:

- Consultar siempre el catálogo vigente de la empresa antes de responder sobre productos, disponibilidad o precios.
- Reconocer nombres, códigos, categorías, unidades, variantes y sinónimos registrados.
- Combinar únicamente productos, materiales, procesos y acabados compatibles según reglas aprobadas.
- Actualizar automáticamente lo que puede consultar cuando se crea, edita, desactiva o elimina un producto.
- No necesitar reentrenamiento manual cada vez que cambia el catálogo.
- No utilizar información perteneciente a otra empresa ni aprender reglas comerciales de un tenant para aplicarlas a otro.
- Respetar el rol del usuario: consultar, cotizar, descontar o aprobar solo dentro de sus permisos.
- Mostrar preguntas guiadas, botones y opciones seleccionables cuando falten datos, en lugar de exigir un prompt preciso.
- Indicar cuando no existe información suficiente y transferir la decisión a una persona autorizada.

La adaptación no debería depender de entrenar un modelo con cada catálogo. El asistente consultará datos vivos mediante herramientas internas controladas: búsqueda de catálogo, consulta de stock, listas de precios, fórmulas, historial autorizado y creación de borradores.

Ejemplo de interacción guiada:

```text
Usuario: Necesito autocopiativos para un cliente.

Inkora: ¿Qué desea preparar?
  [Talonarios] [Formularios continuos] [Otro]

Inkora: Selecciona las características que faltan:
  Tamaño: [A4] [A5] [Personalizado]
  Copias: [Original + 1] [Original + 2]
  Cantidad de juegos: [50] [100] [Otro]
```

El lenguaje natural sirve para acelerar la operación, pero la interfaz guiada permite que una persona sin experiencia complete el mismo cálculo.

#### Cambios y eliminación de productos

- Un producto nuevo debe estar disponible para el asistente una vez guardado y validado.
- Un producto desactivado o eliminado no debe ofrecerse en nuevas cotizaciones.
- Los documentos históricos deben conservar nombre, descripción, unidad, precio y demás datos usados en el momento de su emisión, aunque el catálogo cambie después.
- Si una fórmula depende de un producto desactivado, Inkora debe marcarla como incompleta y evitar un cálculo silenciosamente incorrecto.
- Los cambios de precio o fórmula deben tener vigencia y versión para poder explicar cómo se calculó una cotización anterior.

#### Configuración comercial asistida

Cuando el negocio todavía no tenga reglas suficientes, Inkora debe ofrecer asistentes de configuración basados en formularios y ejemplos del rubro, no prompts técnicos. El dueño seleccionará opciones como margen mínimo, unidades, materiales, acabados y escalas de cantidad. Antes de activar una fórmula, el sistema deberá probarla con ejemplos y pedir una confirmación comprensible.

#### Arquitectura técnica preliminar

No se necesita otra base de datos para la primera versión. PostgreSQL puede mantener tanto el catálogo como las reglas y el contexto autorizado que utilizará el asistente.

Componentes propuestos:

1. **PostgreSQL como fuente de verdad:** productos, servicios, variantes, unidades, aliases, fórmulas, componentes, listas de precios, stock, márgenes, permisos y versiones.
2. **Backend de Inkora como orquestador:** autentica al usuario, deriva la empresa desde su sesión, valida permisos y expone herramientas internas de alcance limitado.
3. **Modelo conversacional:** interpreta la petición, identifica datos faltantes y decide qué herramienta autorizada consultar; no accede directamente a la base de datos ni confirma operaciones por sí mismo.
4. **Motor determinista:** calcula cantidades, costos, precios, márgenes y descuentos sin depender del texto generado por el modelo.
5. **Interfaz guiada:** combina conversación, botones, selectores y un borrador verificable antes de crear la cotización.
6. **Worker opcional:** actualiza índices de búsqueda o representaciones semánticas cuando cambia el catálogo, sin bloquear la operación principal.

Herramientas internas mínimas del asistente:

- `buscar_catalogo`
- `consultar_producto`
- `consultar_stock`
- `obtener_lista_precio`
- `obtener_formula`
- `calcular_precio`
- `validar_margen_descuento`
- `crear_borrador_cotizacion`

Todas deben recibir el contexto empresarial desde el backend autenticado; el modelo no podrá proporcionar ni cambiar `tenant_id`, `company_id` o equivalentes.

La búsqueda inicial debe usar códigos, nombres, aliases y búsqueda textual de PostgreSQL. Si posteriormente el catálogo crece o los usuarios utilizan descripciones muy variables, se puede habilitar `pgvector` dentro del mismo PostgreSQL para búsqueda por significado. No se justifica incorporar una base vectorial separada durante la primera etapa.

Los documentos fiscales y cotizaciones históricas conservarán una copia de los datos comerciales aplicados. El catálogo vivo podrá cambiar sin alterar documentos anteriores.

#### Incorporación de tablas y conocimiento informal

El administrador no debe transcribir manualmente todas las combinaciones ni convertir sus tablas en fórmulas técnicas. Inkora debe aceptar como fuente una fotografía, PDF, Excel o plantilla y producir un **borrador de catálogo calculable** para revisión humana.

Flujo propuesto:

1. El dueño carga o fotografía su tabla de precios actual.
2. Inkora identifica encabezados, filas, unidades, cantidades, materiales y posibles combinaciones.
3. El sistema propone uno o más patrones: búsqueda directa, matriz, tramos, composición, medida, base más recargos, mínimo comercial o costo más margen.
4. Los valores legibles se muestran en una tabla editable; lo ambiguo queda resaltado y sin publicar.
5. El dueño responde preguntas comerciales simples, por ejemplo: “¿este importe es por ciento o por millar?” o “¿incluye IGV?”.
6. Inkora prueba la regla con ejemplos tomados de la fuente y compara el resultado esperado.
7. El administrador aprueba y publica una versión inmutable.

La IA puede transcribir, clasificar y proponer. Nunca podrá publicar ni completar silenciosamente una celda ambigua. Los originales se conservan como evidencia privada y cada precio publicado mantiene su versión.

No es necesario almacenar cada frase posible con la que preguntará un vendedor. Cada producto o familia tendrá nombres, aliases y atributos. La búsqueda combinará coincidencia por código/nombre, texto aproximado y, cuando haga falta, similitud semántica. Si existen varias coincidencias razonables, el asistente presentará opciones antes de calcular.

Las combinaciones numerosas tampoco deben convertirse siempre en una fila por cada resultado posible. Se representarán usando los patrones y operaciones declarativas definidos en [la arquitectura del catálogo calculable](pricing/phase-1-architecture.md). Las muestras y reglas de descubrimiento están documentadas en [la fase de descubrimiento](pricing/phase-0-discovery.md).

#### Onboarding y aprendizaje

Inkora no debe enseñar conceptos de IA ni obligar a completar un recorrido general del sistema. El onboarding debe conducir a un primer resultado real y cambiar según el rol.

Para el administrador:

1. Configurar los datos mínimos de la empresa.
2. Crear un producto o importar una lista real.
3. Revisar las ambigüedades detectadas.
4. Probar un cálculo con un ejemplo conocido.
5. Publicar la primera versión y generar una cotización de prueba.

Para vendedor u operador:

1. Buscar o describir lo que solicita el cliente.
2. Responder preguntas guiadas sobre cantidad, medida, material o acabado.
3. Revisar el precio y crear un borrador de cotización.

El recorrido debe ser opcional, reanudable y de pocos pasos. Las funciones avanzadas se enseñarán en contexto mediante estados vacíos útiles, ayudas breves y videos cortos. El progreso debe guardarse por usuario en backend para respetarlo en distintos dispositivos.

Momentos de valor que se deben medir:

- Administrador: primera lista validada y primer cálculo que coincide con su precio esperado.
- Vendedor: primera cotización correcta sin consultar al dueño.
- Negocio: reducción del tiempo promedio de cotización y de solicitudes de aprobación innecesarias.

#### Referencia preliminar de costos de extracción e IA

Precios públicos consultados el 21 de agosto de 2026; deben verificarse nuevamente antes de contratar o implementar:

| Servicio | Uso posible | Precio público de referencia |
|---|---|---:|
| Google Document AI Enterprise OCR | texto básico | USD 1.50 / 1,000 páginas; la tabla pública muestra un tramo inicial gratuito de hasta 1,000 |
| Google Document AI Form Parser | estructuras y formularios | USD 30 / 1,000 páginas |
| AWS Textract Detect Document Text | texto básico | USD 1.50 / 1,000 páginas en el ejemplo oficial de US West |
| AWS Textract Tables | detección de tablas | USD 15 / 1,000 páginas en el ejemplo oficial de US West |
| Mistral OCR 4 | OCR con estructura documental | USD 4 / 1,000 páginas |
| Mistral Document AI | extracción documentaria enriquecida | USD 5 / 1,000 páginas |
| OpenAI GPT-5.4 mini | interpretación, herramientas y conversación | USD 0.75 / 1M tokens de entrada y USD 4.50 / 1M de salida |
| OpenAI GPT-5.4 nano | clasificación/extracción simple a evaluar | USD 0.20 / 1M tokens de entrada y USD 1.25 / 1M de salida |
| Mistral Small 4 | alternativa económica multimodal | USD 0.15 / 1M tokens de entrada y USD 0.60 / 1M de salida |
| Gemini 2.5 Flash | alternativa multimodal equilibrada | USD 0.30 / 1M tokens de entrada y USD 2.50 / 1M de salida |

Fuentes: [Google Document AI](https://cloud.google.com/products/document-ai/pricing), [AWS Textract](https://aws.amazon.com/textract/pricing/), [Mistral API](https://mistral.ai/pricing/api/), [OpenAI GPT-5.4 mini y nano](https://openai.com/index/introducing-gpt-5-4-mini-and-nano/) y [Gemini API](https://ai.google.dev/gemini-api/docs/pricing).

Recomendación de prototipo: comparar Mistral OCR 4 y Google Document AI sobre el mismo conjunto anonimizado de tablas; utilizar GPT-5.4 mini para la interpretación y el uso de herramientas solo si supera una evaluación de exactitud. Mantener Mistral Small 4 y Gemini Flash como alternativas de costo. La selección final se debe decidir por precisión en listas reales, no solo por precio.

Escenarios económicos orientativos con precios del 21 de agosto de 2026:

- 50 documentos de una página: Mistral OCR cuesta USD 0.20; sumando una interpretación estimada de 2,500 tokens de entrada y 800 de salida por documento con GPT-5.4 mini, el costo técnico base es aproximadamente USD 0.47. Presupuestar USD 0.60–1.00 por reintentos y variación.
- 50 documentos de cinco páginas: con unas 250 páginas y documentos de 8,000 tokens de entrada y 1,500 de salida, el costo técnico base sería aproximadamente USD 1.64. Presupuestar USD 2–4 por variación y revisiones automáticas.
- 200 conversaciones diarias con GPT-5.4 mini, suponiendo 2,000 tokens de entrada y 500 de salida por turno: aproximadamente USD 0.75 al día o USD 22.50 en 30 días por usuario. Un uso ligero puede acercarse a USD 11.25 al mes y uno pesado a USD 39.60.

Estos importes no incluyen impuestos, tipo de cambio, almacenamiento, soporte humano ni el costo de configurar y validar las reglas. El precio comercial debe incluir margen y no trasladar el costo técnico de forma directa.

#### Enrutamiento de modelos para conversación comercial

DeepSeek V4 Flash se incorpora como candidato para el asistente cotidiano. Según su documentación pública del 21 de agosto de 2026, soporta salida JSON, llamadas a herramientas, modos con y sin razonamiento y cuesta USD 0.14 por millón de tokens de entrada sin caché, USD 0.0028 con caché y USD 0.28 por millón de salida. El proveedor lo anuncia como beta pública, por lo que no debe ser la única ruta sin pruebas ni fallback.

Arquitectura candidata:

- DeepSeek V4 Flash sin razonamiento para búsquedas, preguntas guiadas y selección de herramientas rutinarias.
- Motor determinista de Inkora para precios, stock, márgenes y descuentos.
- GPT-5.4 mini como fallback para ambigüedad compleja y como comparador durante la evaluación inicial.
- Revisión o aprobación humana para cambios de reglas y situaciones fuera del catálogo publicado.
- Capa de proveedor intercambiable para evitar que el dominio de precios dependa de una API específica.

Con 2,000 tokens de entrada y 500 de salida por interacción, 200 interacciones diarias durante 30 días cuestan teóricamente cerca de USD 2.52 con DeepSeek V4 Flash frente a USD 22.50 con GPT-5.4 mini. Como una interacción con herramientas normalmente requiere una llamada para seleccionar la herramienta y otra para redactar el resultado, el presupuesto operativo razonable para DeepSeek sería USD 5–8 mensuales por un usuario con ese uso extremo, antes de impuestos. Un enrutamiento híbrido con 90–95 % DeepSeek y 5–10 % GPT se estima en USD 3.50–4.50 con una sola llamada por interacción, y más al incluir las rondas de herramientas.

Antes de seleccionar el proveedor se deben evaluar en español: precisión al escoger herramientas, manejo de nombres coloquiales, preguntas ante ambigüedad, obediencia a esquemas JSON, resistencia a inventar precios, latencia, disponibilidad y condiciones de tratamiento de datos.

Fuente oficial: [DeepSeek V4 Models & Pricing](https://api-docs.deepseek.com/quick_start/pricing/) y [OpenAI GPT-5.4 mini](https://developers.openai.com/api/docs/models/gpt-5.4-mini).

Escenario esperado de uso por usuario, con DeepSeek V4 Flash como modelo principal:

- Hasta 20 importaciones OCR mensuales.
- Hasta 150 mensajes de chat diarios, equivalentes a 4,500 interacciones en 30 días.
- Supuesto conversacional por ronda: 2,000 tokens de entrada y 500 de salida.
- Modo de razonamiento desactivado para consultas rutinarias.

Costos aproximados:

- Veinte documentos de una página: Mistral OCR USD 0.08 más interpretación de DeepSeek cercana a USD 0.01–0.03; total aproximado USD 0.10.
- Veinte documentos de cinco páginas: unas 100 páginas; OCR e interpretación aproximados USD 0.43–0.60.
- Chat con una llamada por mensaje: aproximadamente USD 1.89 mensuales.
- Chat con dos rondas por mensaje para consultar herramientas y redactar: aproximadamente USD 3.78 mensuales.
- Presupuesto total recomendado, incluyendo variación, reintentos y documentos de varias páginas: USD 4–6 mensuales por usuario de uso máximo, antes de impuestos e infraestructura.

### 2. Motor de precios y productos configurables

**Estado:** Propuesto — fundamento necesario para el asistente.

Tipos de precio contemplados:

- Precio fijo.
- Precios escalonados por cantidad.
- Precio calculado por medidas, área, volumen o peso.
- Producto armado con materiales, procesos y acabados.
- Servicio calculado por horas, visitas o unidades.
- Combo o paquete.
- Precio especial por cliente o segmento.

Ejemplos de uso:

- Imprentas: papel, tamaño, copias, juegos, colores, numeración, perforado y acabado.
- Vidrierías: ancho, alto, tipo y espesor de vidrio.
- Confecciones: material, talla, cantidad y estampado.
- Talleres: repuestos y mano de obra.
- Distribuidores: precios escalonados por volumen.
- Servicios: horas, visitas o paquetes.

### 3. Listas de precios, márgenes y descuentos

**Estado:** Propuesto.

- Listas minorista, mayorista y distribuidor.
- Precio especial por cliente.
- Vigencia y moneda de cada lista.
- Historial de cambios.
- Costo de referencia y margen mínimo.
- Descuento máximo según rol.
- Aprobación del dueño desde un dispositivo autorizado.
- Alertas antes de confirmar una operación con pérdida o margen insuficiente.

### 4. Cuenta corriente y crédito de clientes

**Estado:** Propuesto — construir primero para uso interno.

**Objetivo:** reemplazar registros en papel y relacionar cada deuda con la evidencia comercial y fiscal correspondiente.

La ficha de crédito debería incluir:

- Línea de crédito y saldo disponible.
- Condición y plazo de pago.
- Deuda total y deuda vencida.
- Documentos pendientes y fechas de vencimiento.
- Facturas, boletas, cotizaciones y guías relacionadas.
- Pagos registrados, saldo por documento y constancias adjuntas.
- Acuerdos y promesas de pago.
- Observaciones e historial de contacto.
- Estado del cliente: al día, por vencer, vencido o bloqueado para nuevo crédito.

Reglas importantes:

- Un pago no modifica el comprobante fiscal emitido; actualiza la cobranza asociada.
- No se debe borrar el historial de deuda ni de pagos.
- Registrar autor, fecha y motivo de ajustes, descuentos o condonaciones.
- Advertir o bloquear una nueva venta a crédito cuando se excedan las políticas configuradas.

### 5. Ficha comercial ampliada del cliente

**Estado:** Propuesto.

Durante una venta o cotización, mostrar según permisos:

- Productos o servicios comprados recientemente.
- Últimos precios autorizados.
- Cotizaciones anteriores.
- Lista de precios asignada.
- Condición de pago y descuento permitido.
- Deuda y línea de crédito disponible.
- Observaciones comerciales importantes.

### 6. Portal del comprador o cliente final

**Estado:** Futuro — segunda etapa de la cuenta corriente.

El comprador podría utilizar una cuenta o enlace seguro para:

- Consultar cotizaciones, comprobantes, guías y estado de cuenta.
- Descargar PDF, XML y otros documentos autorizados.
- Ver vencimientos y saldos.
- Subir una constancia de pago.
- Confirmar recepción o solicitar revisión.

El comprador no podrá modificar importes, datos fiscales, pagos confirmados ni documentos emitidos. El portal necesitará aislamiento por empresa, acceso de alcance limitado y auditoría completa.

### 7. Caja diaria

**Estado:** Futuro.

- Apertura y cierre de caja.
- Ingresos y egresos operativos.
- Medios de pago.
- Conciliación con ventas y cobranzas.
- Diferencias de caja y responsable del turno.
- Historial no eliminable de correcciones.

### 8. Pedidos, preparación y entregas

**Estado:** Futuro.

- Estados: pendiente, en preparación, listo, despachado y entregado.
- Relación con cotización, comprobante, guía y movimiento de inventario.
- Responsable y fechas de cada transición.
- Evidencia o confirmación de entrega.

Este módulo debe centrarse en trazabilidad comercial y logística; no debe convertirse todavía en un módulo completo de producción.

### 9. Comisiones de vendedores

**Estado:** Futuro.

- Reglas por venta, cobro, producto o margen.
- Diferenciar venta realizada de venta efectivamente cobrada.
- Ajustar comisiones ante notas de crédito o anulaciones.
- Reporte por periodo y vendedor.
- Auditoría de ajustes manuales.

### 10. Recordatorios operativos

**Estado:** Futuro.

- Seguimiento de cotizaciones sin respuesta.
- Avisos de vencimiento y cobranza.
- Recordatorios de pedidos listos o entregas pendientes.
- Alertas internas ante documentos fiscales con problemas.
- Plantillas controladas y registro de comunicaciones.

### 11. Catálogo digital y solicitud de pedido

**Estado:** Propuesto.

- Catálogo público por empresa con productos o servicios seleccionados.
- Enlace compartible por WhatsApp y código QR.
- Precios visibles, “consultar” o “desde”, según configuración.
- Carrito o solicitud que genere un pedido o borrador de cotización, no un comprobante fiscal automático.
- Disponibilidad aproximada sin exponer costos ni información interna.
- Personalización con identidad del negocio.

El cliente final puede iniciar el pedido, pero un usuario tenant debe revisar precio, stock, identidad y condiciones antes de confirmar documentos sensibles.

### 12. Comunicaciones y seguimiento por WhatsApp

**Estado:** Propuesto.

- Compartir cotizaciones, comprobantes, guías y estados de cuenta.
- Plantillas para seguimiento, vencimientos y pedidos listos.
- Registro de qué documento se envió, cuándo y por quién.
- Enlaces seguros con vigencia y ownership validado.
- Consentimiento, preferencias de contacto y exclusión de mensajes automáticos.

La primera versión puede abrir WhatsApp con un mensaje preparado. La automatización mediante API debe evaluarse después por costo, plantillas y cumplimiento.

### 13. Centro de aprobaciones

**Estado:** Propuesto — prioridad alta por su relación con precios y crédito.

- Aprobar descuentos fuera del límite del vendedor.
- Aprobar ventas bajo margen mínimo.
- Aprobar ampliaciones de crédito o ventas a clientes vencidos.
- Aprobar anulaciones, ajustes y operaciones excepcionales según el dominio.
- Solicitud breve con contexto, responsable, decisión, motivo y fecha.
- Acceso móvil para que el dueño responda sin estar físicamente en el negocio.

Una aprobación comercial no reemplaza las validaciones fiscales ni autoriza editar documentos aceptados.

### 14. Devoluciones y cambios

**Estado:** Futuro.

- Registrar devolución total o parcial con motivo.
- Relacionar el movimiento con venta, inventario, pago y documento fiscal.
- Diferenciar cambio comercial, devolución de mercadería, nota de crédito y devolución de dinero.
- Reingresar stock únicamente cuando la mercadería sea recibida y apta.
- Mantener trazabilidad y aprobación para excepciones.

### 15. Conteo y control móvil de inventario

**Estado:** Propuesto.

- Conteos físicos desde celular.
- Lectura de código de barras o QR.
- Conteo parcial por zona, categoría o responsable.
- Comparación entre stock registrado y contado.
- Ajustes solo mediante un flujo autorizado con motivo y auditoría.
- Historial de diferencias recurrentes.

### 16. Agenda para negocios de servicios

**Estado:** Futuro — validar demanda antes de construir.

- Citas o reservas vinculadas al cliente y servicio.
- Responsable, duración, estado y recordatorio.
- Conversión de cita atendida a cotización o comprobante.
- Depósitos o pagos relacionados sin mezclarlos con cobranza SaaS.

Permite atender clínicas, talleres, consultorías y otros servicios, pero debe mantenerse opcional para no complicar a negocios de venta inmediata.

### 17. Sucursales y almacenes múltiples

**Estado:** Futuro — módulo de crecimiento.

- Stock y movimientos por ubicación.
- Series, cajas, vendedores y permisos por sucursal.
- Transferencias entre almacenes con origen, destino y responsable.
- Reportes consolidados y por sede.
- Propiedad tenant obligatoria y restricciones de acceso por usuario.

No activar complejidad multisucursal en empresas que operan desde un único local.

### 18. Espacio Contador multiempresa

**Estado:** Propuesto.

- Rol de contador separado de administrador, vendedor y superadministrador.
- Invitación explícita por cada empresa y revocación inmediata.
- Vista de varias empresas asignadas sin mezclar datos entre tenants.
- Acceso principalmente de lectura, descarga y observación.
- Periodos visibles, estado de revisión y pendientes por empresa.
- Restricción de datos comerciales sensibles que no sean necesarios para la labor contable.

El vínculo multiempresa debe ser una relación explícita contador-tenant. No convierte al contador en superadmin ni permite elegir un `tenant_id` desde el navegador.

### 19. Cierre mensual y conciliación fiscal

**Estado:** Propuesto — prioridad alta para el Espacio Contador.

- Lista de comprobantes emitidos, aceptados, rechazados, anulados y pendientes.
- Conciliación entre documentos registrados, estado SmartPSE/SUNAT, XML y CDR.
- Detección de correlativos faltantes, duplicidades y documentos sin evidencia completa.
- Totales por tipo de comprobante, moneda, impuestos y periodo.
- Checklist de cierre con observaciones, responsable y fecha.
- Bloqueo lógico del periodo revisado; correcciones posteriores quedan registradas y notificadas.

La conciliación informa inconsistencias. No debe cambiar estados fiscales ni completar silenciosamente documentos.

### 20. Exportación y preparación para SIRE

**Estado:** Futuro — sujeto a validación normativa y pruebas con un contador.

- Preparar información del Registro de Ventas e Ingresos Electrónico (RVIE).
- Incorporar posteriormente el Registro de Compras Electrónico (RCE) cuando exista un módulo de compras estabilizado.
- Exportar archivos y anexos en las estructuras vigentes requeridas.
- Validar campos obligatorios, periodos, moneda, documentos y errores antes de descargar.
- Comparar la información de Inkora contra la propuesta obtenida por el contador desde SIRE.
- Conservar versión, hash, fecha y responsable de cada archivo generado.

Inkora no debe presentar automáticamente registros ni declaraciones en la primera etapa, ni almacenar credenciales SOL como parte del flujo ordinario. SUNAT mantiene SIRE para RVIE y RCE y ofrece portal, aplicativo cliente y API; cualquier integración debe verificarse nuevamente contra documentación vigente antes de implementarse.

### 21. Paquete contable mensual

**Estado:** Propuesto.

Descarga por empresa y periodo que puede contener:

- Resumen de ventas.
- Relación de facturas, boletas, notas y guías.
- XML, CDR y PDF disponibles.
- Cobranzas y saldos pendientes, claramente separados de los comprobantes fiscales.
- Retenciones y percepciones registradas.
- Reportes en Excel/CSV y manifiesto de archivos.
- Alertas e inconsistencias no resueltas.

El paquete debe generarse en segundo plano, mantener ownership tenant y evitar URLs públicas permanentes.

### 22. Bandeja de observaciones del contador

**Estado:** Propuesto.

- Solicitar documentos o explicaciones al administrador.
- Asociar una observación a comprobante, pago, periodo o archivo.
- Estados: pendiente, respondida, resuelta y descartada con motivo.
- Adjuntos privados y trazabilidad de respuestas.
- Notificaciones internas sin depender de conversaciones dispersas por WhatsApp.

### 23. Dashboard tributario informativo

**Estado:** Futuro.

- Ventas gravadas, exoneradas o inafectas según la información documentaria disponible.
- IGV de ventas y tendencias por periodo.
- Notas que modifican importes del periodo.
- Retenciones, percepciones y otros conceptos registrados.
- Comparación preliminar con periodos anteriores.

Debe mostrarse como información de apoyo, no como determinación definitiva de impuestos. Sin compras, gastos, crédito fiscal, arrastres y ajustes contables completos, Inkora no puede calcular de forma confiable el IGV o impuesto por pagar.

## Flujo operativo que debe conectar los módulos

```text
Cliente
  -> cálculo o lista de precios
  -> cotización
  -> pedido o venta
  -> comprobante fiscal
  -> guía y salida de inventario, si corresponde
  -> cuenta corriente y cobranza
  -> pago y cierre de saldo
```

La implementación futura debe evitar que estos documentos queden como registros aislados.

## Módulos congelados fuera del lanzamiento

No ampliar sin una instrucción y análisis específico:

- Proveedores.
- Insumos.
- Recetas o BOM.
- Órdenes de producción.
- Alertas de inventario heredadas.
- Inteligencia artificial heredada.

El Asistente de precios propuesto es una idea nueva y acotada. No implica reactivar automáticamente la inteligencia artificial heredada.

## Orden preliminar recomendado

1. Estabilizar el núcleo fiscal, multitenant, permisos, cobranza e inventario actual.
2. Confirmar productos con stock y servicios sin stock.
3. Diseñar el motor determinista de precios y productos configurables.
4. Añadir listas de precios, márgenes, descuentos y aprobaciones.
5. Construir el Asistente de precios sobre ese motor.
6. Completar cuenta corriente de clientes para uso interno.
7. Evaluar portal de compradores.
8. Evaluar caja, pedidos, comisiones y recordatorios con evidencia de clientes beta.
9. Priorizar catálogo digital, centro de aprobaciones y conteo móvil si los clientes beta confirman su uso.
10. Dejar agenda, devoluciones completas y multisucursal para una etapa de crecimiento.
11. Diseñar primero el rol contador, cierre mensual y paquete contable; evaluar SIRE únicamente con datos y formatos vigentes y participación de contadores reales.

## Plantilla para registrar nuevas ideas

Cada nueva propuesta debería añadir:

- **Nombre del módulo.**
- **Estado.**
- **Problema que resuelve.**
- **Usuario principal.**
- **Flujo afectado.**
- **Datos y documentos relacionados.**
- **Permisos y riesgos.**
- **Dependencias.**
- **Criterio para incluirlo en beta o posponerlo.**
