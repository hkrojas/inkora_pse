"""Tests for unit-price precision — verifies that prices with more than 2
decimals are preserved through the calculation pipeline and produce correct
line totals.

Covers the bug: 0.365 × 1000 must equal 365.00, not 370.00.
"""
from decimal import Decimal

import pytest

from services.calculations import calcular_item, sumarizar_cotizacion, to_decimal


class TestPrecisionPreserved:
    """Prices with 3-4 decimals must not be rounded before multiplication."""

    def test_basic_3_decimal_price(self):
        """0.365 × 1000 = 365.00 (not 370.00)."""
        result = calcular_item(
            cantidad=Decimal("1000"),
            precio_con_igv=Decimal("0.365"),
            tipo_afectacion_igv="10",
        )
        assert result["total_item"] == Decimal("365.00")

    def test_4_decimal_price(self):
        """0.1234 × 10000 = 1234.00."""
        result = calcular_item(
            cantidad=Decimal("10000"),
            precio_con_igv=Decimal("0.1234"),
            tipo_afectacion_igv="10",
        )
        assert result["total_item"] == Decimal("1234.00")

    def test_precio_unitario_preserved(self):
        """The precio_unitario in the result must match the input exactly."""
        result = calcular_item(
            cantidad=Decimal("1"),
            precio_con_igv=Decimal("0.365"),
            tipo_afectacion_igv="10",
        )
        assert result["precio_unitario"] == Decimal("0.365")

    def test_valor_unitario_extended_precision(self):
        """valor_unitario (sin IGV) should have 10-decimal precision."""
        result = calcular_item(
            cantidad=Decimal("1"),
            precio_con_igv=Decimal("0.365"),
            tipo_afectacion_igv="10",
        )
        vu = result["valor_unitario"]
        # 0.365 / 1.18 = 0.3093220339...
        assert vu == Decimal("0.3093220339")

    def test_igv_derived_correctly(self):
        """IGV = total_item - total_base_igv (subtraction method)."""
        result = calcular_item(
            cantidad=Decimal("1000"),
            precio_con_igv=Decimal("0.365"),
            tipo_afectacion_igv="10",
        )
        assert result["total_igv"] == result["total_item"] - result["total_base_igv"]

    def test_exonerada_3_decimal_price(self):
        """Exonerada items: 0.125 × 2000 = 250.00."""
        result = calcular_item(
            cantidad=Decimal("2000"),
            precio_con_igv=Decimal("0.125"),
            tipo_afectacion_igv="20",  # exonerada
        )
        assert result["total_item"] == Decimal("250.00")
        assert result["total_igv"] == Decimal("0.00")

    def test_sumarizar_with_precision_items(self):
        """Header totals from multiple precision items must be correct."""
        items = [
            calcular_item(Decimal("1000"), Decimal("0.365"), "10"),
            calcular_item(Decimal("500"), Decimal("0.455"), "10"),
        ]
        totals = sumarizar_cotizacion(items)
        # 365.00 + 227.50 = 592.50
        assert totals["total_venta"] == Decimal("592.50")


class TestStandard2DecimalPrices:
    """Existing 2-decimal prices must still work correctly."""

    def test_standard_price(self):
        """10.00 × 5 = 50.00."""
        result = calcular_item(
            cantidad=Decimal("5"),
            precio_con_igv=Decimal("10.00"),
            tipo_afectacion_igv="10",
        )
        assert result["total_item"] == Decimal("50.00")

    def test_single_item(self):
        """118.00 × 1 = 118.00."""
        result = calcular_item(
            cantidad=Decimal("1"),
            precio_con_igv=Decimal("118.00"),
            tipo_afectacion_igv="10",
        )
        assert result["total_item"] == Decimal("118.00")
        assert result["total_base_igv"] == Decimal("100.00")
        assert result["total_igv"] == Decimal("18.00")
