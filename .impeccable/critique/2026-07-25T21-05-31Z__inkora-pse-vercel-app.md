---
target: web pública de Inkora
total_score: 24
max_score: 36
na_heuristics: 7
p0_count: 0
p1_count: 3
timestamp: 2026-07-25T21-05-31Z
slug: inkora-pse-vercel-app
---
# Revisión de diseño — web pública de Inkora

## Design Health Score

| # | Heurística | Puntaje | Hallazgo principal |
|---|---|---:|---|
| 1 | Visibilidad del estado del sistema | 3 | La función futura está marcada como “Próximamente”, pero no se pudo validar feedback de interacciones dinámicas. |
| 2 | Correspondencia con el mundo real | 3 | El lenguaje SUNAT, RUC, comprobantes y cobranza encaja con Perú; “tenant” se filtra al login y rompe esa naturalidad. |
| 3 | Control y libertad | 3 | Hay rutas claras a acceso, login y recorrido; falta una salida comercial más directa como contacto o demo. |
| 4 | Consistencia y estándares | 3 | La identidad pública es coherente, pero el despliegue no coincide plenamente con el frontend local y el tono del login baja de calidad. |
| 5 | Prevención de errores | 2 | El alta estructura bien los datos, pero no muestra requisitos de contraseña antes de escribir y no se validaron estados de error. |
| 6 | Reconocimiento antes que recuerdo | 3 | El recorrido comercial se explica visualmente y los CTA son previsibles; el destino de “Solicitar acceso” necesita más contexto previo. |
| 7 | Flexibilidad y eficiencia | n/a | No es una heurística determinante para una landing de persuasión. |
| 8 | Diseño estético y minimalista | 3 | La dirección visual es sólida, aunque la página se alarga y repite demostraciones del producto. |
| 9 | Reconocer, diagnosticar y recuperarse de errores | 2 | La implementación local muestra mensajes del backend de forma directa y no se verificó una recuperación guiada en producción. |
| 10 | Ayuda y documentación | 2 | Existe FAQ, pero faltan ayuda humana, proceso de alta, tiempos, plan y compromisos operativos visibles. |
| **Total** | | **24/36** | **Aceptable; base fuerte con mejoras importantes de conversión y confianza.** |

## Veredicto de especificidad

Inkora sí se siente diseñado para un producto concreto. La combinación carbón, verde lima, datos en soles, estados SUNAT y el hilo cotización → comprobante → inventario → cobranza evitan el aspecto de plantilla SaaS genérica. El hero “Vender es difícil. Ordenarlo no debería serlo.” tiene voz propia y la demostración del dashboard transmite una operación conectada.

La debilidad no es falta de personalidad visual, sino falta de prueba comercial. La web dice con claridad qué hace Inkora, pero demuestra poco por qué una pyme debería confiarle su facturación, sus credenciales y sus cobros. Además, amplía el público a comercios, distribuidoras y servicios, mientras el producto se define internamente como SaaS vertical para imprentas y pequeños negocios. Esa tensión reduce especialización percibida.

El detector local registró 14 hallazgos: 13 de estilo y 1 de calidad, concentrados en `frontend/src/styles/globals.css` (12), `tokens.css` (1) y `app.css` (1). Seis son falsos positivos contextuales: cuatro bordes de estado pertenecen a toasts, la transición de ancho anima un subrayado y la supuesta cuadrícula es una textura de vista previa. Los hallazgos útiles son el uso reiterado de easing tipo bounce y la dependencia de tipografías muy comunes en partes del frontend local. No se atribuyen automáticamente a la landing desplegada porque sus bundles y fuentes difieren del árbol local.

## Impresión general

La primera pantalla es convincente, legible y memorable. El mayor salto no vendrá de hacerla más llamativa: vendrá de convertir su promesa en una decisión segura. Inkora necesita mostrar con la misma precisión visual qué incluye, cómo se activa, cuánto acompañamiento recibe el cliente y qué evidencia respalda su confiabilidad fiscal.

## Lo que funciona

1. **Hero con postura.** La jerarquía tipográfica, el contraste carbón/lima y la frase principal capturan el problema operativo sin sonar como un ERP tradicional.
2. **Producto explicado como recorrido.** Mostrar una venta conectada desde cotización hasta cobranza comunica mejor el valor que una cuadrícula de funciones aisladas.
3. **Lenguaje y datos locales.** Soles, RUC, SUNAT, facturas, boletas, CDR y XML sitúan el producto en Perú y generan reconocimiento inmediato.

## Problemas prioritarios

### [P1] La promesa comercial excede o difumina el posicionamiento real

**Por qué importa:** La landing habla a cualquier comercio, distribuidora o empresa de servicios. Inkora, en cambio, tiene una ventaja vertical clara en imprentas y pequeños negocios peruanos. Cuanto más amplia es la promesa, más parece un ERP genérico y más difícil es creer que resuelve detalles operativos específicos.

**Cambio:** Elegir una jerarquía explícita: “hecho para imprentas; adaptable a pymes con ventas por pedido” o, si la expansión horizontal es deliberada, respaldarla con casos reales por sector. Ajustar también cualquier capacidad mostrada que aún no tenga madurez de lanzamiento.

**Comando sugerido:** `$impeccable clarify`

### [P1] El CTA pide datos antes de resolver dudas de compra

**Por qué importa:** “Solicitar acceso” aparece repetidamente, pero antes de entregar RUC, teléfono, administrador y contraseña el visitante no sabe precio, modalidad del único plan, tiempo de aprobación, soporte, migración ni qué sucederá después. Es fricción especialmente alta para un producto fiscal.

**Cambio:** Añadir antes del CTA una sección compacta “Qué ocurre después” con 3 pasos, plazo de respuesta, alcance del plan y canal de soporte. Si el precio aún no es público, explicar claramente que la solicitud no genera cobro ni activa emisión fiscal.

**Comando sugerido:** `$impeccable clarify`

### [P1] Falta evidencia concreta de confianza fiscal y empresarial

**Por qué importa:** La página afirma separación por empresa, trazabilidad y estados reales, pero no ofrece política de privacidad, términos, responsable comercial, soporte visible, documentación de seguridad, casos reales ni testimonios. En facturación electrónica, esas ausencias pesan más que en un SaaS de baja criticidad.

**Cambio:** Crear un bloque de confianza verificable: razón social/contacto, privacidad y términos, disponibilidad/soporte, tratamiento de credenciales fiscales, respaldo documental y uno o dos casos de clientes autorizados. Evitar claims absolutos que no estén documentados.

**Comando sugerido:** `$impeccable harden`

### [P2] La página repite demostraciones y da demasiado espacio a una función futura

**Por qué importa:** Dashboard, flujo, cuatro módulos, recorrido de cinco pasos y múltiples tarjetas cuentan parcialmente la misma historia. La consulta de comprobantes “Próximamente” ocupa una sección completa y desvía atención hacia algo que todavía no convierte ni resuelve una tarea.

**Cambio:** Comprimir la narrativa en tres momentos: captar/ordenar la venta, emitir con claridad fiscal y cobrar/controlar. Mover la función futura a una nota breve o eliminarla hasta que exista. Usar el espacio recuperado para prueba social y proceso de alta.

**Comando sugerido:** `$impeccable distill`

### [P2] La transición landing → login/alta pierde refinamiento y habla en jerga interna

**Por qué importa:** En el login aparecen “Gestion”, “operacion” y “Sesion” sin tilde, además de “datos por tenant”. Ese es precisamente el punto donde el usuario evalúa seguridad y profesionalismo. El término “tenant” pertenece a la arquitectura, no al lenguaje de una pyme.

**Cambio:** Corregir ortografía y reemplazarlo por “datos separados por empresa”. Añadir requisitos de contraseña antes de escribir, explicar que el alta queda pendiente y ofrecer un canal de ayuda visible.

**Comando sugerido:** `$impeccable polish`

### [P2] El frontend público carga una hoja de estilos desproporcionada

**Por qué importa:** El bundle desplegado expone aproximadamente 600 KB de CSS y 314 KB de JavaScript sin comprimir. La landing parece compartir una gran superficie de estilos con la aplicación, lo que aumenta costo de mantenimiento y puede afectar conexiones móviles.

**Cambio:** Separar estilos críticos de marketing y aplicación, eliminar CSS no usado del entry público, revisar code splitting por ruta y medir LCP/INP/CLS en producción antes de fijar objetivos.

**Comando sugerido:** `$impeccable optimize`

## Carga cognitiva

Carga moderada: fallan principalmente **enfoque único**, por la cantidad de bloques que compiten después del hero, y **divulgación progresiva**, porque se muestran módulos, recorrido, sectores, función futura, confianza y FAQ en una sola página extensa. La agrupación, jerarquía y reconocimiento están bien resueltos. No hay una pared de opciones en el encabezado: cuatro anclas más dos acciones se mantienen razonables.

## Viaje emocional

El inicio genera energía y alivio: “ordenarlo no debería serlo”. La demostración del dashboard crea el pico de aspiración. Luego la página entra en una meseta por repetición. La sección de confianza debería ser el punto de tranquilidad antes de solicitar acceso, pero hoy presenta principios más que pruebas. El cierre vuelve al CTA sin terminar de resolver el riesgo percibido.

## Alertas por persona

**Jordan, primer usuario:** entiende rápido que Inkora conecta ventas, SUNAT y cobranza, pero no puede anticipar qué sucederá después de enviar el formulario, cuánto cuesta ni quién lo acompañará. “Tenant” en el login introduce una palabra técnica innecesaria.

**Riley, usuario que prueba límites:** verá una consulta de documentos no funcional, promesas de seguridad sin documentos enlazados y una diferencia entre el despliegue público y el frontend local. Preguntará si inventario/Kardex y todos los sectores anunciados están realmente listos para lanzamiento.

**Casey, usuario móvil distraído:** la página es larga y exige atravesar varios bloques similares antes de la prueba de confianza. La gran cantidad de media queries indica intención responsive, pero la inspección móvil visual completa no pudo concluirse; deben verificarse menú, recortes de mockups, tamaños de toque y el formulario de alta a 390 px y 200% de zoom.

## Observaciones menores

- “Próximamente” está etiquetado con honestidad; conservar esa transparencia aunque se reduzca la sección.
- El hero utiliza un mockup suficientemente específico, pero el texto diminuto dentro del dashboard no debe considerarse contenido legible en móvil.
- La FAQ es una buena base; debería responder también plan, soporte, aprobación y custodia de credenciales.
- El detector marca seis usos de easing elástico en el frontend local; conviene reemplazarlos por movimiento más sobrio en un producto fiscal.
- La implementación local muestra buena intención accesible: skip link, `lang="es"`, foco visible, `prefers-reduced-motion`, labels y textos alternativos. Falta validación real con teclado y contraste.

## Preguntas para decidir la siguiente fase

1. ¿Inkora quiere liderar con especialización en imprentas o presentarse desde ahora como producto horizontal para cualquier pyme?
2. ¿El único plan comercial y su precio pueden mostrarse públicamente, o debe explicarse como cotización asistida?
3. ¿La consulta pública de comprobantes es una promesa cercana que ayuda a vender o distrae del alcance listo hoy?
