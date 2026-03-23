"""Unit tests for currency conversion and FX handling."""

from __future__ import annotations

import pytest

from techwatch.adapters.fx.ecb import CurrencyConverter


@pytest.fixture
def converter():
    """Create a converter with known test rates."""
    rates = {
        "EUR": 1.0,
        "USD": 1.08,
        "GBP": 0.86,
        "JPY": 163.5,
        "CHF": 0.97,
    }
    return CurrencyConverter(rates=rates)


class TestCurrencyConverter:
    def test_same_currency_returns_same_amount(self, converter):
        assert converter.convert(100.0, "USD", "USD") == 100.0

    def test_eur_to_usd(self, converter):
        result = converter.convert(100.0, "EUR", "USD")
        assert result is not None
        assert result == pytest.approx(108.0, rel=0.01)

    def test_usd_to_eur(self, converter):
        result = converter.convert(108.0, "USD", "EUR")
        assert result is not None
        assert result == pytest.approx(100.0, rel=0.01)

    def test_cross_rate_usd_to_gbp(self, converter):
        result = converter.convert(108.0, "USD", "GBP")
        assert result is not None
        assert result == pytest.approx(86.0, rel=0.01)

    def test_unsupported_currency_returns_none(self, converter):
        """Never fabricate precision — return None for missing rates."""
        result = converter.convert(100.0, "USD", "RUB")
        assert result is None

    def test_unsupported_from_currency_returns_none(self, converter):
        result = converter.convert(100.0, "BTC", "USD")
        assert result is None

    def test_empty_converter_returns_none(self):
        empty = CurrencyConverter()
        result = empty.convert(100.0, "USD", "EUR")
        assert result is None

    def test_is_loaded(self, converter):
        assert converter.is_loaded is True
        assert CurrencyConverter().is_loaded is False

    def test_supported_currencies(self, converter):
        currencies = converter.get_supported_currencies()
        assert "USD" in currencies
        assert "EUR" in currencies
        assert len(currencies) == 5
