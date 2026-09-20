---
timestamp: 2026-07-26T02-33-00Z
slug: frontend-src-pages-login-jsx
---
⚠️ DEGRADED: revisión principal realizada desde código fuente; los agentes de Assessment A no completaron y el navegador integrado no estuvo disponible. Assessment B sí fue independiente y completó el detector.

# Auditoría de Login y Solicitar acceso

## Veredicto

La base funcional es sólida y transmite control operativo, especialmente en los estados de solicitud y la consulta de RUC. Sin embargo, la experiencia visual quedó desacoplada de la nueva landing Ruta Operativa: conserva el verde y la estructura general, pero vuelve a gradientes, transparencias, radios grandes y una tarjeta de seguridad genérica. La transición desde la web pública se siente como entrar a otro producto.

Puntuación heurística: 23/40 — aceptable, con mejoras importantes antes de considerarlo pulido.

1. Visibilidad del estado: 3/4. Hay carga, envío, consulta de RUC y estados pending/approved/rejected.
2. Correspondencia con el mundo real: 2/4. El campo dice Correo / Usuario pero usa type=email; dashboard y tenant son términos internos.
3. Control y libertad: 3/4. Recuperación, volver, mostrar contraseña y reinicio de solicitud están presentes.
4. Consistencia: 2/4. Login y alta son coherentes entre sí, pero no con la identidad actual de la landing.
5. Prevención de errores: 2/4. Hay required y validación básica, pero las reglas y coincidencia de contraseña aparecen demasiado tarde.
6. Reconocimiento sobre memoria: 3/4. Etiquetas y ayudas son claras; faltan requisitos visibles de contraseña.
7. Flexibilidad y eficiencia: 2/4. La consulta RUC reduce trabajo; el formulario largo no preserva borrador.
8. Estética y minimalismo: 2/4. Login es razonablemente compacto; la solicitud acumula panel, tarjeta y ocho campos.
9. Recuperación de errores: 2/4. Los errores son globales y pueden exponer mensajes técnicos, sin vinculación al campo ni recuperación de foco.
10. Ayuda y documentación: 2/4. La aprobación está bien explicada; faltan reglas de contraseña y una explicación más humana de seguridad.

## Fortalezas

- La solicitud explica con honestidad que el alta requiere aprobación y representa claramente los estados posteriores.
- La consulta de RUC autocompleta razón social y dirección, una mejora real de velocidad y reducción de errores.
- El login incluye recordar dispositivo, recuperación y mostrar/ocultar contraseña.
- Los estados de espera, éxito, rechazo y error tienen mensajes y acciones diferenciadas.
- El detector mecánico no encontró anti-patrones en los tres componentes revisados.

## Problemas prioritarios

### P1 — Ruptura visual y de confianza con la landing

La landing usa papel frío, tinta verde, lima #A3E635, trazos documentales y radios contenidos. Las pantallas de acceso conservan el sistema visual anterior: #8dc63f, gradientes, superficies translúcidas, radios de 18–24 px, sombra blanda y animación elástica. El cambio se percibe justo cuando el usuario entrega credenciales o datos empresariales.

Recomendación: rediseñar ambas como una extensión de Ruta Operativa, con una hoja de acceso clara, el hilo verde como guía de progreso, bordes documentales y superficies opacas. Mantener intacta la lógica.

### P1 — Contrato contradictorio en Correo / Usuario

El login promete aceptar correo o usuario, pero el control es type=email. Un nombre de usuario válido sin arroba queda bloqueado por el navegador antes de llegar a la autenticación.

Recomendación: confirmar el contrato real. Si solo se admite correo, cambiar la etiqueta a Correo electrónico. Si se admite usuario, usar un campo de texto con validación adecuada.

### P1 — Validación tardía y genérica en Solicitar acceso

La contraseña no muestra sus requisitos antes del error y la confirmación solo se valida al enviar. Los fallos se presentan en una alerta general; no se asocian al campo ni llevan el foco al punto que debe corregirse.

Recomendación: mostrar requisitos persistentes, coincidencia en vivo después de la interacción, mensajes por campo con aria-describedby y foco en el primer error. Traducir errores del backend a mensajes seguros y accionables.

### P2 — Carga de captura alta en móvil

El formulario pide ocho datos en una sola columna y coloca la acción principal al final. La consulta RUC ayuda, pero una interrupción puede hacer perder todo el avance.

Recomendación: dividir visualmente Empresa → Administrador → Revisión, preferiblemente en dos pasos cortos; preservar temporalmente el borrador no sensible y mantener visible el contexto de aprobación.

### P2 — Accesibilidad y jerarquía móvil

Al ocultarse el panel de marca, la primera cabecera visible sigue siendo un h2, no un h1. El botón de mostrar contraseña mide aproximadamente 30 px, por debajo de un objetivo táctil cómodo. Los textos blancos secundarios con opacidades cercanas a .48–.58 tienen riesgo de contraste insuficiente y deben medirse en navegador.

Recomendación: usar h1 en cada ruta, ampliar controles táctiles a 44×44 px y verificar contraste AA en texto secundario y estados. Mantener foco visible y reduced motion.

## Carga cognitiva

El login tiene carga baja: dos campos, dos decisiones secundarias y una acción clara. Solicitar acceso tiene carga media-alta por volumen de captura, no por exceso de opciones. La mejor reducción no es eliminar datos necesarios, sino secuenciarlos, anticipar reglas y autocompletar cuanto sea verificable.

## Recorrido emocional

- Entrada: la landing establece una identidad diferenciada y operativa.
- Login: la identidad visual retrocede a una plantilla SaaS más genérica; baja la continuidad percibida.
- Solicitud: la explicación de aprobación recupera confianza y establece expectativas honestas.
- Captura: las reglas ocultas de contraseña y errores globales pueden crear una caída innecesaria.
- Final: los estados pending/approved/rejected cierran bien el ciclo y dan una próxima acción.

## Personas

- Jordan, usuario nuevo: puede interpretar Correo / Usuario literalmente y quedar bloqueado; tampoco sabe las reglas de contraseña antes de fallar.
- Sam, teclado/lector de pantalla: recibe labels y algunos anuncios en vivo, pero pierde una jerarquía h1 en móvil y los errores no están ligados al campo.
- Casey, móvil e interrupciones: se beneficia de la consulta RUC, pero el alta larga y sin borrador aumenta abandono.
- Dueño de pyme: entiende la aprobación, pero frases como tenant o acceso fiscal protegido son menos claras que empresa, comprobantes y permisos.

## Observaciones menores

- Corregir tildes visibles: Gestión, operación y Sesión.
- Convertir el nombre/símbolo de Inkora en enlace a la página pública para ofrecer una salida clara.
- Sustituir Acceder al dashboard por Iniciar sesión, salvo que siempre represente el destino real; superadmin ya redirige a otro espacio.
- Reescribir la tarjeta de seguridad con evidencia comprensible del producto y sin jerga interna.

## Orden recomendado

1. Resolver el contrato correo/usuario y los errores por campo.
2. Unificar tokens, tipografía, bordes, movimiento y color con Ruta Operativa.
3. Reorganizar Solicitar acceso en grupos o pasos, conservando el flujo y API actuales.
4. Corregir jerarquía, objetivos táctiles, contraste y reduced motion.
5. Añadir pruebas de teclado, errores, responsive y estados de solicitud.

## Preguntas de diseño

- ¿El login debe sentirse como el último tramo de la web comercial o como la primera pantalla del espacio operativo? Hoy queda a mitad de ambos.
- ¿Inkora realmente admite nombres de usuario, o el texto está prometiendo una capacidad que el formulario no soporta?
- ¿La aprobación necesita una sola página larga o ganaría confianza con Empresa → Responsable → Confirmación?

## Run Notes

- Objetivos: frontend-src-pages-login-jsx y frontend-src-pages-accessrequestpage-jsx.
- Lista de exclusiones: no se encontró una lista aplicable.
- Assessment A: dos intentos independientes no completaron; se realizó revisión principal del código fuente.
- Assessment B: agente independiente, sin acceso a Assessment A; detector ejecutado exactamente una vez.
- Detector: salida limpia, 0 hallazgos.
- Navegador/overlay: no disponible; error literal Browser is not available: iab. No se usó navegador sustituto.
- Servidor local: no iniciado.
- Inyección visual: no intentada.
- Archivos temporales: este archivo se elimina después de persistir el snapshot.
- Cambios al producto: ninguno.
