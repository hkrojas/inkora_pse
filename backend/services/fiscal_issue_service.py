"""Validate payment dates against the date of the new fiscal document."""
from datetime import datetime

from services import calculations


def _parse_due_date(value) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def validate_credit_payment_schedule(document, *, issue_datetime: datetime | None = None) -> None:
    condition = str(getattr(document, "condicion_pago", "") or "").strip().lower()
    if not condition or condition == "contado":
        return
    total = calculations.redondear(getattr(document, "total_venta", 0))
    issue_datetime = issue_datetime or getattr(document, "fecha_emision", None)
    installments = []
    for index, installment in enumerate(getattr(document, "cuotas_pago", None) or [], start=1):
        if not isinstance(installment, dict):
            raise ValueError(f"Pre-validacion fallida: La cuota {index} no tiene formato valido.")
        due_date = _parse_due_date(installment.get("fecha_pago") or installment.get("fechaPago"))
        amount = calculations.redondear(installment.get("monto", 0))
        if not due_date:
            raise ValueError(f"Pre-validacion fallida: La cuota {index} no tiene fecha de vencimiento valida.")
        if amount <= 0:
            raise ValueError(f"Pre-validacion fallida: El monto de la cuota {index} debe ser mayor a cero.")
        installments.append((due_date, amount))
    if not installments:
        due_date = _parse_due_date(getattr(document, "fecha_vencimiento", None))
        if not due_date:
            raise ValueError("Pre-validacion fallida: Las facturas al credito requieren al menos una cuota.")
        installments.append((due_date, total))
    if len(installments) > 999:
        raise ValueError("Pre-validacion fallida: SUNAT admite como maximo 999 cuotas.")
    for index, (due_date, _) in enumerate(installments, start=1):
        if issue_datetime and due_date.date() <= issue_datetime.date():
            raise ValueError(
                f"Pre-validacion fallida: La cuota {index} debe vencer despues de la fecha de emision. "
                "Actualice los vencimientos de la cotizacion antes de emitir."
            )
    installment_total = calculations.redondear(
        sum((amount for _, amount in installments), calculations.Decimal("0.00"))
    )
    if installment_total != total:
        raise ValueError(
            f"Pre-validacion fallida: La suma de cuotas ({installment_total}) "
            f"debe coincidir con el total del comprobante ({total})."
        )
