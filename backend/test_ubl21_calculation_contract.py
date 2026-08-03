import json
from decimal import Decimal
from pathlib import Path

from services.calculations import calcular_item, sumarizar_cotizacion


CONTRACT_PATH = Path(__file__).resolve().parents[1] / "contracts" / "ubl21_calculation_cases.json"
LINE_KEYS = ("cantidad", "precio_unitario", "valor_unitario", "total_base_igv", "total_igv", "total_item")


def test_ubl21_calculation_contract():
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    for case in contract["cases"]:
        lines = [
            calcular_item(
                Decimal(item["cantidad"]),
                Decimal(item["precio_unitario"]),
                item["tipo_afectacion_igv"],
            )
            for item in case["items"]
        ]

        for actual, expected in zip(lines, case["expected"]["lines"], strict=True):
            for key in LINE_KEYS:
                assert actual[key] == Decimal(expected[key]), f"{case['name']}: {key}"

        totals = sumarizar_cotizacion(lines)
        for key, expected in case["expected"]["totals"].items():
            assert totals[key] == Decimal(expected), f"{case['name']}: {key}"
