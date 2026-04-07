"""
routers/reportes.py — Launch Scope: Cobranza y Reportes

Endpoints de cobranza y reportes contables del tenant.
Extraídos de routers/pagos.py en la limpieza de P2 del refactor (2026-04-07).

Rutas:
  GET /cobranza/resumen      — posición de cobranza del tenant
  GET /cobranza/vencidas     — documentos vencidos con saldo pendiente
  GET /reporte/mensual       — Excel mensual para el contador
"""

import calendar
import io
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

import crud
import models
import schemas
from api_dependencies import get_current_user, get_db_tenant

router = APIRouter(tags=["reportes"])


@router.get(
    "/cobranza/resumen",
    response_model=schemas.CobranzaResumenResponse,
    summary="Resumen de cobranza del tenant",
)
def cobranza_resumen(
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    """
    Devuelve un resumen de la posición de cobranza:
    - total por cobrar
    - total vencido
    - total cobrado en el mes
    - contadores de documentos por estado
    """
    data = crud.get_cobranza_resumen(db, current_user.tenant_id)
    return schemas.CobranzaResumenResponse(**data)


@router.get(
    "/cobranza/vencidas",
    summary="Lista de documentos vencidos con saldo pendiente",
)
def cobranza_vencidas(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    """
    Lista cotizaciones cuya fecha_vencimiento ya pasó y aún tienen saldo pendiente.
    Ordena de la más antigua (mayor riesgo) a la más reciente.
    """
    ahora = datetime.now()
    cotizaciones = crud.get_cobranza_vencida(
        db, current_user.tenant_id, skip=skip, limit=limit
    )

    result = []
    for cot in cotizaciones:
        cliente = cot.cliente
        dias_vencido = 0
        if cot.fecha_vencimiento:
            delta = ahora - cot.fecha_vencimiento
            dias_vencido = max(0, delta.days)

        result.append({
            "cotizacion_id": cot.id,
            "document_number": cot.document_number,
            "internal_order_number": cot.internal_order_number,
            "cliente_nombre": cliente.razon_social if cliente else "",
            "cliente_documento": cliente.numero_documento if cliente else "",
            "fecha_vencimiento": cot.fecha_vencimiento,
            "total_venta": cot.total_venta or Decimal("0"),
            "monto_pagado": cot.monto_pagado or Decimal("0"),
            "saldo_pendiente": cot.saldo_pendiente or Decimal("0"),
            "dias_vencido": dias_vencido,
        })

    return result


@router.get(
    "/reporte/mensual",
    summary="Reporte mensual de documentos fiscales (Excel para contador)",
)
def reporte_mensual_excel(
    anio: int = Query(..., ge=2020, le=2100, description="Año del reporte"),
    mes: int = Query(..., ge=1, le=12, description="Mes del reporte (1-12)"),
    db: Session = Depends(get_db_tenant),
    current_user: models.User = Depends(get_current_user),
):
    """
    Genera un archivo Excel con todos los comprobantes fiscales emitidos en el mes.
    Diseñado para ser entregado directamente al contador.
    Incluye: número de comprobante, fecha, cliente, RUC, base imponible, IGV, total,
    estado de pago, monto pagado, saldo pendiente y condición de pago.
    """
    try:
        import openpyxl
        from openpyxl.styles import Alignment, Font, PatternFill
        from openpyxl.utils import get_column_letter
    except ImportError:
        raise HTTPException(500, "openpyxl no está instalado en el servidor.")

    docs = crud.get_reporte_mensual(db, current_user.tenant_id, anio, mes)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Reporte {mes:02d}-{anio}"

    # ── Cabecera empresa ──────────────────────────────────────────────────────
    tenant = (
        db.query(models.Tenant)
        .filter(models.Tenant.id == current_user.tenant_id)
        .first()
    )
    empresa = tenant.business_name if tenant else "Empresa"
    ruc_empresa = tenant.business_ruc if tenant else ""

    ws.merge_cells("A1:N1")
    ws["A1"] = f"REPORTE MENSUAL DE COMPROBANTES — {empresa} (RUC {ruc_empresa})"
    ws["A1"].font = Font(bold=True, size=13)
    ws["A1"].alignment = Alignment(horizontal="center")

    ws.merge_cells("A2:N2")
    nombre_mes = calendar.month_name[mes].upper()
    ws["A2"] = f"PERIODO: {nombre_mes} {anio}"
    ws["A2"].alignment = Alignment(horizontal="center")

    ws.append([])  # fila vacía

    # ── Encabezados de tabla ──────────────────────────────────────────────────
    HEADERS = [
        "Tipo",
        "Serie",
        "Correlativo",
        "Fecha Emisión",
        "Cliente",
        "RUC / DNI",
        "Tipo Doc.",
        "Base Imponible",
        "IGV (18%)",
        "Total",
        "Moneda",
        "Estado Pago",
        "Monto Pagado",
        "Saldo Pendiente",
        "Condición Pago",
        "Observaciones",
    ]
    header_row = 4
    ws.append(HEADERS)

    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    for col_idx, _ in enumerate(HEADERS, start=1):
        cell = ws.cell(row=header_row, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")

    # ── Filas de datos ────────────────────────────────────────────────────────
    TIPO_LABEL = {"01": "Factura", "03": "Boleta", "07": "Nota Crédito", "08": "Nota Débito"}
    _D = Decimal

    totales_base = _D("0")
    totales_igv = _D("0")
    totales_total = _D("0")
    totales_pagado = _D("0")
    totales_saldo = _D("0")

    alt_fill = PatternFill(start_color="DDEEFF", end_color="DDEEFF", fill_type="solid")

    for row_num, doc in enumerate(docs, start=1):
        cliente = doc.cliente
        total_venta = doc.total_venta or _D("0")
        igv = (total_venta * _D("18") / _D("118")).quantize(_D("0.01"))
        base = (total_venta - igv).quantize(_D("0.01"))
        monto_pagado = doc.monto_pagado or _D("0")
        saldo = doc.saldo_pendiente or _D("0")

        tipo_label = TIPO_LABEL.get(doc.tipo_comprobante or "", doc.tipo_comprobante or "")
        fecha_str = doc.fecha_emision.strftime("%d/%m/%Y") if doc.fecha_emision else ""
        payment_status = doc.payment_status if hasattr(doc, "payment_status") else ""

        row_data = [
            tipo_label,
            doc.serie or "",
            str(doc.correlativo or "").zfill(6),
            fecha_str,
            cliente.razon_social if cliente else "",
            cliente.numero_documento if cliente else "",
            cliente.tipo_documento if cliente else "",
            float(base),
            float(igv),
            float(total_venta),
            doc.moneda or "PEN",
            payment_status,
            float(monto_pagado),
            float(saldo),
            doc.condicion_pago or "",
            doc.observaciones or "",
        ]

        ws.append(row_data)
        data_row = header_row + row_num

        # Filas alternadas
        if row_num % 2 == 0:
            for col_idx in range(1, len(HEADERS) + 1):
                ws.cell(row=data_row, column=col_idx).fill = alt_fill

        # Formato numérico para columnas monetarias (8,9,10,13,14)
        for col_idx in [8, 9, 10, 13, 14]:
            ws.cell(row=data_row, column=col_idx).number_format = '#,##0.00'

        totales_base += base
        totales_igv += igv
        totales_total += total_venta
        totales_pagado += monto_pagado
        totales_saldo += saldo

    # ── Fila de totales ───────────────────────────────────────────────────────
    total_row = header_row + len(docs) + 1
    ws.cell(row=total_row, column=1, value="TOTALES")
    ws.cell(row=total_row, column=1).font = Font(bold=True)
    totales = {8: float(totales_base), 9: float(totales_igv), 10: float(totales_total),
               13: float(totales_pagado), 14: float(totales_saldo)}
    for col_idx, val in totales.items():
        cell = ws.cell(row=total_row, column=col_idx, value=val)
        cell.number_format = '#,##0.00'
        cell.font = Font(bold=True)

    # ── Ancho de columnas ─────────────────────────────────────────────────────
    col_widths = [12, 8, 12, 14, 35, 14, 10, 16, 12, 14, 8, 14, 14, 16, 16, 30]
    for i, width in enumerate(col_widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = width

    # ── Resumen final ─────────────────────────────────────────────────────────
    summary_start = total_row + 3
    ws.cell(row=summary_start, column=1, value="RESUMEN DEL PERIODO").font = Font(bold=True, size=11)
    ws.cell(row=summary_start + 1, column=1, value="Total documentos emitidos:")
    ws.cell(row=summary_start + 1, column=2, value=len(docs))
    ws.cell(row=summary_start + 2, column=1, value="Total facturado:")
    ws.cell(row=summary_start + 2, column=2, value=float(totales_total)).number_format = '#,##0.00'
    ws.cell(row=summary_start + 2, column=2).number_format = '#,##0.00'
    ws.cell(row=summary_start + 3, column=1, value="Total cobrado:")
    ws.cell(row=summary_start + 3, column=2, value=float(totales_pagado))
    ws.cell(row=summary_start + 3, column=2).number_format = '#,##0.00'
    ws.cell(row=summary_start + 4, column=1, value="Saldo pendiente:")
    ws.cell(row=summary_start + 4, column=2, value=float(totales_saldo))
    ws.cell(row=summary_start + 4, column=2).number_format = '#,##0.00'

    # ── Serializar y devolver ─────────────────────────────────────────────────
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    filename = f"reporte_{anio}_{mes:02d}_{current_user.tenant_id}.xlsx"
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
