"""Unit tests for price trend analysis."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from techwatch.normalization.trends import (
    MarketSnapshot,
    PriceTrend,
    compute_market_snapshot,
    compute_trend,
)


def _make_history(prices: list[float]):
    """Create mock PriceHistoryRow objects."""
    rows = []
    for i, p in enumerate(prices):
        row = MagicMock()
        row.total_landed_cost = p
        row.recorded_at = datetime.utcnow() - timedelta(days=len(prices) - i)
        rows.append(row)
    return rows


class TestComputeTrend:
    def test_empty_history(self):
        trend = compute_trend("offer-1", [])
        assert trend.data_points == 0
        assert trend.current_price is None

    def test_single_datapoint(self):
        history = _make_history([500.0])
        trend = compute_trend("offer-1", history)
        assert trend.data_points == 1
        assert trend.current_price == 500.0
        assert trend.is_all_time_low is True

    def test_falling_trend(self):
        history = _make_history([600.0, 580.0, 560.0, 540.0, 520.0, 500.0])
        trend = compute_trend("offer-1", history)
        assert trend.trend_direction == "falling"
        assert trend.pct_change_vs_first < 0

    def test_rising_trend(self):
        history = _make_history([400.0, 420.0, 440.0, 460.0, 480.0, 500.0])
        trend = compute_trend("offer-1", history)
        assert trend.trend_direction == "rising"
        assert trend.pct_change_vs_first > 0

    def test_stable_trend(self):
        history = _make_history([500.0, 501.0, 499.0, 500.0, 500.5, 500.0])
        trend = compute_trend("offer-1", history)
        assert trend.trend_direction == "stable"

    def test_all_time_low(self):
        history = _make_history([600.0, 550.0, 520.0, 510.0, 490.0])
        trend = compute_trend("offer-1", history)
        assert trend.is_all_time_low is True
        assert trend.current_price == 490.0

    def test_not_all_time_low(self):
        history = _make_history([400.0, 500.0, 520.0])
        trend = compute_trend("offer-1", history)
        assert trend.is_all_time_low is False

    def test_pct_below_median(self):
        # Median of [600, 550, 520, 500, 450] = 520
        # Current = 450, pct below = (520-450)/520 * 100 = 13.46%
        history = _make_history([600.0, 550.0, 520.0, 500.0, 450.0])
        trend = compute_trend("offer-1", history)
        assert trend.pct_below_median is not None
        assert trend.pct_below_median > 10

    def test_stats_calculated(self):
        history = _make_history([100.0, 200.0, 300.0])
        trend = compute_trend("offer-1", history)
        assert trend.mean_price == 200.0
        assert trend.median_price == 200.0
        assert trend.min_price == 100.0
        assert trend.max_price == 300.0
        assert trend.stdev > 0


class TestMarketSnapshot:
    def test_empty_market(self):
        snapshot = compute_market_snapshot("laptop", [])
        assert snapshot.num_offers == 0
        assert snapshot.median_price == 0.0

    def test_market_with_offers(self):
        trends = [
            PriceTrend(
                offer_id=f"offer-{i}",
                window_days=30,
                data_points=5,
                current_price=price,
                min_price=price - 50,
                max_price=price + 50,
                mean_price=price,
                median_price=price,
                stdev=25.0,
                pct_change_vs_first=-5.0,
                pct_below_median=3.0,
            )
            for i, price in enumerate([500, 600, 700])
        ]
        scores = {"offer-0": 0.85, "offer-1": 0.72, "offer-2": 0.65}

        snapshot = compute_market_snapshot("laptop", trends, scores)
        assert snapshot.num_offers == 3
        assert snapshot.price_range == (500, 700)
        assert snapshot.median_price == 600
        assert snapshot.best_value_offer_id == "offer-0"
        assert snapshot.best_value_score == 0.85
