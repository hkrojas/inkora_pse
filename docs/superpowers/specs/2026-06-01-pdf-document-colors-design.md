# PDF Document Colors Design

## Goal

Expose PDF color customization to tenant users from Configuracion, using the existing PDF designer and the tenant color fields already supported by the backend.

## Scope

- Add a visible section in `Configuracion > Apariencia` for document PDF colors.
- Reuse `/diseno-pdf` as the full editor for quote, invoice, boleta and related document styling.
- Show the current PDF primary color and note color in Configuracion.
- Keep the beta-safe data model: `primary_color` and `pdf_note_1_color`.
- Do not add database migrations or new fiscal behavior.
- Do not emit real fiscal documents.

## Architecture

The existing `PdfDesignerPage` remains the source of truth for editing PDF visual settings. `ConfiguracionPage` becomes the operational entry point, so users can discover the PDF customization area without knowing the direct route.

`tenant.primary_color` drives the main table, header boxes, lines and totals in PDF rendering. `tenant.pdf_note_1_color` drives the highlighted commercial note color. Any fixed blue accent still used by the modern PDF builder should be replaced with the tenant primary color where it represents the document accent.

## UX

`Configuracion > Apariencia` will contain:

- Existing app theme controls.
- A new "Colores de documentos PDF" card.
- A compact live sample showing a header strip, a table header and a total pill using the saved color.
- A button that opens `/diseno-pdf`.

The full editor stays on `/diseno-pdf` and keeps its live preview.

## Validation

No secret-bearing fields are added. The feature only reads and writes tenant visual fields already exposed by `/tenant/`.

Backend schema validation should reject invalid hex colors for `primary_color` and `pdf_note_1_color`, preventing broken ReportLab rendering.

## Tests

- Frontend lint/build.
- Backend schema test for valid and invalid PDF colors.
- Targeted static/UI test where available to ensure Configuracion exposes the PDF color entry point.
- `git diff --check`.

## Rollout

This is a beta-safe UI/validation change. Existing tenants keep their current colors. Tenants without custom colors continue using the default blue.
