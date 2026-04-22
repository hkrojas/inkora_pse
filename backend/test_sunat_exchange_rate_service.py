from unittest.mock import patch

import pytest

from services import sunat_exchange_rate_service as service


class _FakeResponse:
    def __init__(self, text: str, status_code: int = 200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("http error")


def setup_function():
    service._CACHE_VALUE = None
    service._CACHE_EXPIRES_AT = None


def test_parse_exchange_rate_payload_ok():
    payload = service._parse_exchange_rate_payload("16/04/2026|3.425|3.436|")

    assert payload["date"] == "2026-04-16"
    assert payload["buy"] == "3.425"
    assert payload["sell"] == "3.436"
    assert payload["stale"] is False


def test_get_exchange_rate_uses_cache_after_first_hit():
    with patch.object(
        service.requests,
        "get",
        return_value=_FakeResponse("16/04/2026|3.425|3.436|"),
    ) as get_mock:
        first = service.get_exchange_rate()
        second = service.get_exchange_rate()

    assert first["buy"] == "3.425"
    assert second["sell"] == "3.436"
    assert get_mock.call_count == 1


def test_get_exchange_rate_falls_back_to_stale_cache_on_error():
    with patch.object(
        service.requests,
        "get",
        return_value=_FakeResponse("16/04/2026|3.425|3.436|"),
    ):
        fresh = service.get_exchange_rate()

    assert fresh["stale"] is False

    with patch.object(
        service.requests,
        "get",
        side_effect=service.requests.RequestException("down"),
    ):
        stale = service.get_exchange_rate(force_refresh=True)

    assert stale["status"] == "stale"
    assert stale["stale"] is True
    assert stale["buy"] == "3.425"


def test_parse_exchange_rate_payload_rejects_invalid_payload():
    with pytest.raises(service.SunatExchangeRateError):
        service._parse_exchange_rate_payload("invalido")
