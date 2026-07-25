---
name: Inkora Ruta Operativa
description: Una identidad documental y conectada para la presencia pública de Inkora.
colors:
  route-lime: "#A3E635"
  deep-green: "#365314"
  deep-green-dark: "#243B0B"
  cold-paper: "#F7F9F4"
  paper-white: "#FFFFFF"
  green-ink: "#172019"
  muted-ink: "#536057"
  document-line: "#DCE4D8"
typography:
  display:
    fontFamily: "Mona Sans, Arial, sans-serif"
    fontSize: "clamp(3.375rem, 5.1vw, 4.875rem)"
    fontWeight: 820
    lineHeight: 0.98
    letterSpacing: "-0.04em"
  headline:
    fontFamily: "Mona Sans, Arial, sans-serif"
    fontSize: "clamp(2.6875rem, 5vw, 4.25rem)"
    fontWeight: 810
    lineHeight: 1.02
    letterSpacing: "-0.035em"
  title:
    fontFamily: "Mona Sans, Arial, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 780
    lineHeight: 1.1
    letterSpacing: "-0.02em"
  body:
    fontFamily: "Mona Sans, Arial, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.55
  data:
    fontFamily: "Recursive Mono, monospace"
    fontSize: "0.75rem"
    fontWeight: 400
    lineHeight: 1.4
rounded:
  stamp: "4px"
  control: "7px"
  sheet: "8px"
  section: "10px"
spacing:
  compact: "10px"
  control: "18px"
  content: "24px"
  section-mobile: "84px"
  section-desktop: "124px"
components:
  button-primary:
    backgroundColor: "{colors.route-lime}"
    textColor: "{colors.deep-green-dark}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
    padding: "11px 18px"
    height: "46px"
  button-dark:
    backgroundColor: "{colors.green-ink}"
    textColor: "{colors.paper-white}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
    padding: "11px 18px"
    height: "46px"
  status-stamp:
    backgroundColor: "#E9F9C9"
    textColor: "{colors.deep-green}"
    typography: "{typography.data}"
    rounded: "{rounded.stamp}"
    padding: "7px 9px"
---

# Design System: Inkora Ruta Operativa

## Overview

**Creative North Star: "La hoja operativa desplegable"**

Inkora se presenta como un documento vivo que conserva el hilo de una venta. Pliegues, folios, líneas de expediente y sellos convierten estados abstractos en evidencia legible. La densidad cambia entre manifiesto editorial y registro operativo para que la interfaz tenga carácter sin parecer un dashboard público.

La ruta verde es la firma reutilizable: conecta elementos, marca progreso y convierte el color de marca en infraestructura. El movimiento se concentra en una sola revelación inicial; toda la información permanece disponible sin animación.

**Key Characteristics:**

- Superficies claras con estructura documental.
- Verde visible como ruta, estado y superficie.
- Tipografía editorial acompañada por datos monoespaciados.
- Demostraciones concretas en lugar de afirmaciones decorativas.

## Colors

La paleta combina papel frío, tinta verdosa y un verde lima de alta presencia.

### Primary

- **Verde Ruta:** conecta etapas, identifica acciones principales y ocupa superficies de confianza.

### Secondary

- **Verde Profundo:** aporta contraste a los estados, títulos y secciones operativas.
- **Verde Profundo Oscuro:** sostiene grandes superficies y botones de cierre.

### Neutral

- **Papel Frío:** fondo principal con luminosidad suave.
- **Papel Blanco:** hojas, comprobantes y áreas de lectura intensa.
- **Tinta Verde:** texto principal y estructura.
- **Tinta Atenuada:** explicación secundaria.
- **Línea Documental:** divisores, contornos y relaciones.

**The Infrastructure Green Rule.** El verde debe construir recorridos, superficies o estados; nunca aparece como decoración aislada.

**The Fiscal Signal Rule.** Rojo y ámbar quedan reservados para estados fiscales reales.

## Typography

**Display Font:** Mona Sans (con Arial como respaldo)
**Body Font:** Mona Sans (con Arial como respaldo)
**Label/Mono Font:** Recursive Mono (con monospace como respaldo)

**Character:** Mona Sans permite titulares compactos y lectura operativa limpia. Recursive Mono introduce precisión únicamente cuando el contenido es un folio, importe, hora o estado documental.

### Hierarchy

- **Display** (peso 820, escala fluida hasta 4.875rem, interlínea 0.98): promesa principal.
- **Headline** (peso 810, escala fluida hasta 4.25rem, interlínea 1.02): títulos de sección.
- **Title** (peso 780, 1.5rem, interlínea 1.1): títulos operativos.
- **Body** (peso 400, 1rem, interlínea 1.55): explicación con medida máxima cercana a 70 caracteres.
- **Data** (peso 400, 0.75rem, interlínea 1.4): folios, importes y estados documentales.

**The Data-Only Mono Rule.** Recursive Mono no se usa para párrafos, titulares ni navegación.

## Layout

El contenedor principal alcanza 1180px y conserva 24px de margen lateral, reducido a 16px en móvil. Las secciones usan 124px de aire vertical en escritorio y 84px en móvil. El sistema alterna composición partida, bloques editoriales asimétricos y recorridos lineales.

A 1120px el primer viewport se apila; a 900px cambian navegación y estructuras densas; a 700px la ruta horizontal se vuelve vertical. Las anclas reservan 80px para el encabezado fijo.

**The Density Alternation Rule.** Dos secciones consecutivas no repiten la misma retícula ni la misma densidad.

## Elevation & Depth

La profundidad es estructural: hojas blancas se separan del fondo mediante un desplazamiento suave y un pliegue visible. Las grandes secciones permanecen planas.

### Shadow Vocabulary

- **Hoja operativa** (`0 18px 45px rgba(23, 32, 25, .11)`): demostraciones principales.
- **Desplazamiento de estado** (`4px 6px 0 #E7ECE4`): documentos pequeños conectados a la ruta.
- **Acción táctil** (`0 7px 0 #789F22`): botón primario en reposo.

**The Paper-First Rule.** La elevación solo aparece cuando una superficie representa una hoja o una acción física.

## Shapes

Los radios son contenidos: sellos de 4px, controles de 7px, hojas de 8px y secciones de 10px. Pliegues diagonales, círculos de etapa y líneas rectas construyen el vocabulario. Los bordes de un píxel funcionan como reglas de documento, no como marcos decorativos.

## Components

### Buttons

- **Shape:** control compacto con radio de 7px y altura mínima de 46px.
- **Primary:** verde ruta con texto verde oscuro y desplazamiento sólido inferior.
- **Hover / Focus:** ascenso de 2px, cambio tonal leve y foco exterior de 3px.
- **Dark:** tinta verde con texto blanco para cierres sobre superficies verdes.

### Chips

- **Style:** sello de estado de 4px, tipografía de datos y borde verde.
- **State:** comunica únicamente resultados o fases reales de la demostración.

### Cards / Containers

- **Corner Style:** hojas de 7–8px y secciones de 10px.
- **Background:** blanco para evidencia; papel frío para soporte.
- **Shadow Strategy:** solo las hojas operativas usan elevación.
- **Border:** línea documental de un píxel.
- **Internal Padding:** de 18px en registros compactos a 46px en comprobantes principales.

### Navigation

Navegación ligera sobre papel frío. El estado activo se expresa con una línea verde profunda. En móvil ocupa una superficie completa, bloquea el scroll y conserva acciones separadas.

### Ruta operativa

Un SVG decorativo dibuja la conexión mientras una lista HTML equivalente conserva orden, significado y accesibilidad. En móvil la ruta cambia de eje sin alterar la secuencia.

## Do's and Don'ts

### Do:

- **Do** usar el verde como infraestructura visible de la operación.
- **Do** identificar los datos sintéticos como demostración.
- **Do** conservar la secuencia y toda la información con movimiento reducido.
- **Do** variar escala y densidad entre secciones editoriales.

### Don't:

- **Don't** usar fondos cuadriculados, orbes, vidrio o gradientes decorativos.
- **Don't** estructurar la página como un mosaico bento de tarjetas anidadas.
- **Don't** usar fotografías de stock para sustituir evidencia de producto.
- **Don't** inventar clientes, testimonios, precios, métricas o compromisos comerciales.
