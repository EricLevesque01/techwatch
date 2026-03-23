"""Unit tests for deal detection trigger evaluation."""

from __future__ import annotations

import pytest

from techwatch.agents.deal_analyst import evaluate_trigger, evaluate_watch_triggers
from techwatch.models import (
    Analysis,
    Offer,
    Pricing,
    Product,
    ScoreComponents,
    SearchResult,
    Watch,
    WatchTrigger,
)
from techwatch.models.enums import (
    CanonicalCondition,
    SellerType,
    Source,
    TriggerMetric,
    TriggerOperator,
)
from techwatch.models.offer import Condition, Merchant


def _make_result(
    price: float = 500.0, rank: int = 1, offer_id: str = "test-1"
) -> SearchResult:
    product = Product(
        canonical_product_id="test:test:1",
        title="Test Product",
        canonical_category="laptop",
    )
    offer = Offer(
        offer_id=offer_id,
        source=Source.BESTBUY,
        pricing=Pricing(sale_amount=price, currency="USD"),
        merchant=Merchant(marketplace="Test", seller_type=SellerType.RETAILER),
    )
    analysis = Analysis(overall_score=0.75)
    return SearchResult(product=product, offer=offer, analysis=analysis, rank=rank)


class TestTriggerEvaluation:
    def test_price_drop_pct_fires(self):
        trigger = WatchTrigger(
            metric=TriggerMetric.PRICE_DROP_PCT,
            operator=TriggerOperator.GTE,
            threshold=8.0,
        )
        result = _make_result(price=460.0)
        stats = {"median": 500.0, "min": 480.0, "max": 520.0, "count": 10}

        reason = evaluate_trigger(trigger, result, stats)
        assert reason is not None
        assert "8" in reason or "dropped" in reason.lower()

    def test_price_drop_pct_does_not_fire_below_threshold(self):
        trigger = WatchTrigger(
            metric=TriggerMetric.PRICE_DROP_PCT,
            operator=TriggerOperator.GTE,
            threshold=10.0,
        )
        result = _make_result(price=470.0)
        stats = {"median": 500.0, "min": 480.0, "max": 520.0, "count": 10}

        reason = evaluate_trigger(trigger, result, stats)
        assert reason is None  # 6% drop < 10% threshold

    def test_price_drop_no_history(self):
        """No false positives when there's no price history."""
        trigger = WatchTrigger(
            metric=TriggerMetric.PRICE_DROP_PCT,
            operator=TriggerOperator.GTE,
            threshold=5.0,
        )
        result = _make_result(price=400.0)
        stats = {"median": None, "min": None, "max": None, "count": 0}

        reason = evaluate_trigger(trigger, result, stats)
        assert reason is None

    def test_new_offer_rank_fires(self):
        trigger = WatchTrigger(
            metric=TriggerMetric.NEW_OFFER_RANK,
            operator=TriggerOperator.LTE,
            threshold=3.0,
        )
        result = _make_result(rank=2)
        stats = {}

        reason = evaluate_trigger(trigger, result, stats)
        assert reason is not None
        assert "#2" in reason

    def test_new_offer_rank_does_not_fire(self):
        trigger = WatchTrigger(
            metric=TriggerMetric.NEW_OFFER_RANK,
            operator=TriggerOperator.LTE,
            threshold=3.0,
        )
        result = _make_result(rank=5)
        stats = {}

        reason = evaluate_trigger(trigger, result, stats)
        assert reason is None

    def test_price_below_fires(self):
        trigger = WatchTrigger(
            metric=TriggerMetric.PRICE_BELOW,
            operator=TriggerOperator.LTE,
            threshold=500.0,
        )
        result = _make_result(price=450.0)
        stats = {}

        reason = evaluate_trigger(trigger, result, stats)
        assert reason is not None
        assert "below" in reason.lower()
