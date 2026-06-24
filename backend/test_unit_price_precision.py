"""Unit-price precision tests.

Prices with more than two decimals must be preserved until line totals are
calculated. The bug case is 0.365 x 1000 = 365.00, not 370.00.
"""
from decimal import Decimal

from services.calculations import calcular_item, sumarizar_cotizacion


def test_three_decimal_unit_price_is_not_rounded_before_multiplication():
    result = calcular_item(
        cantidad=Decimal("1000"),
        precio_con_igv=Decimal("0.365"),
        tipo_afectacion_igv="10",
    )

    assert result["precio_unitario"] == Decimal("0.3650")
    assert result["total_item"] == Decimal("365.00")
    assert result["total_base_igv"] == Decimal("309.32")
    assert result["total_igv"] == Decimal("55.68")


def test_four_decimal_unit_price_is_preserved_for_line_total():
    result = calcular_item(
        cantidad=Decimal("10000"),
        precio_con_igv=Decimal("0.1234"),
        tipo_afectacion_igv="10",
    )

    assert result["precio_unitario"] == Decimal("0.1234")
    assert result["total_item"] == Decimal("1234.00")


def test_decimal_quantity_is_preserved_until_line_total():
    result = calcular_item(
        cantidad=Decimal("2.555"),
        precio_con_igv=Decimal("10.00"),
        tipo_afectacion_igv="10",
    )

    assert result["total_item"] == Decimal("25.55")


def test_extended_value_unit_keeps_ten_decimals():
    result = calcular_item(
        cantidad=Decimal("1"),
        precio_con_igv=Decimal("0.365"),
        tipo_afectacion_igv="10",
    )

    assert result["valor_unitario"] == Decimal("0.3093220339")


def test_quote_summary_uses_rounded_line_totals_only():
    items = [
        calcular_item(Decimal("1000"), Decimal("0.365"), "10"),
        calcular_item(Decimal("500"), Decimal("0.455"), "10"),
    ]

    totals = sumarizar_cotizacion(items)

    assert totals["total_venta"] == Decimal("592.50")
