"""Unit tests for the deterministic scoring engine."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from techwatch.models import (
    Analysis,
    Offer,
    Pricing,
    Product,
    ScoreComponents,
    SearchPlan,
    Specs,
)
from techwatch.models.enums import (
    CanonicalCondition,
    CosmeticGrade,
    FunctionalState,
    SellerType,
    Source,
)
from techwatch.models.offer import Condition, Delivery, Merchant
from techwatch.scoring.scorer import (
    DEFAULT_WEIGHTS,
    ScoringWeights,
    score_condition,
    score_delivery,
    score_result,
    score_spec_fit,
    score_trust,
    score_value,
)


# ── Fixtures ────────────────────────────────────────────────────────


def _make_product(**overrides) -> Product:
    defaults = {
        "canonical_product_id": "test:test:123",
        "title": "Test Product",
        "canonical_category": "laptop",
        "specs": Specs(cpu="Apple M3", ram_gb=16, storage_gb=512),
    }
    defaults.update(overrides)
    return Product(**defaults)


def _make_offer(**overrides) -> Offer:
    defaults = {
        "offer_id": "offer-1",
        "source": Source.BESTBUY,
        "pricing": Pricing(list_amount=999.99, sale_amount=899.99, currency="USD"),
        "merchant": Merchant(marketplace="Best Buy", seller_type=SellerType.RETAILER),
    }
    defaults.update(overrides)
    return Offer(**defaults)


def _make_plan(**overrides) -> SearchPlan:
    defaults = {
        "canonical_category": "laptop",
        "keywords": ["ultrabook"],
        "required_specs": {"ram_gb": 16, "storage_gb": 512},
        "budget_max": 1000.0,
        "conditions": [CanonicalCondition.NEW],
        "country": "US",
    }
    defaults.update(overrides)
    return SearchPlan(**defaults)


# ── Spec fit tests ──────────────────────────────────────────────────


class TestSpecFit:
    def test_perfect_match(self):
        product = _make_product(specs=Specs(ram_gb=16, storage_gb=512))
        plan = _make_plan(required_specs={"ram_gb": 16, "storage_gb": 512})
        assert score_spec_fit(product, plan) == 1.0

    def test_partial_match(self):
        product = _make_product(specs=Specs(ram_gb=8, storage_gb=512))
        plan = _make_plan(required_specs={"ram_gb": 16, "storage_gb": 512})
        score = score_spec_fit(product, plan)
        assert 0.5 < score < 1.0  # Partial credit for ram_gb

    def test_no_plan_returns_neutral(self):
        product = _make_product()
        assert score_spec_fit(product, None) == 0.5

    def test_no_required_specs_returns_neutral(self):
        product = _make_product()
        plan = _make_plan(required_specs={})
        assert score_spec_fit(product, plan) == 0.5


# ── Value tests ─────────────────────────────────────────────────────


class TestValue:
    def test_under_budget_scores_high(self):
        offer = _make_offer(pricing=Pricing(sale_amount=500.0, currency="USD"))
        assert score_value(offer, 1000.0) > 0.7

    def test_at_budget_scores_moderate(self):
        offer = _make_offer(pricing=Pricing(sale_amount=1000.0, currency="USD"))
        assert 0.45 <= score_value(offer, 1000.0) <= 0.55

    def test_over_budget_scores_low(self):
        offer = _make_offer(pricing=Pricing(sale_amount=1500.0, currency="USD"))
        assert score_value(offer, 1000.0) < 0.3

    def test_no_budget_still_scores(self):
        offer = _make_offer(pricing=Pricing(sale_amount=500.0, currency="USD"))
        score = score_value(offer, None)
        assert 0.0 <= score <= 1.0


# ── Delivery tests ──────────────────────────────────────────────────


class TestDelivery:
    def test_pickup_available_bonus(self):
        offer_with = _make_offer(delivery=Delivery(pickup_available=True))
        offer_without = _make_offer(delivery=Delivery(pickup_available=False))
        assert score_delivery(offer_with) > score_delivery(offer_without)

    def test_fast_delivery_scores_high(self):
        offer = _make_offer(
            delivery=Delivery(
                earliest_delivery_at=datetime.utcnow() + timedelta(days=1)
            )
        )
        assert score_delivery(offer) > 0.7


# ── Condition tests ─────────────────────────────────────────────────


class TestConditionScoring:
    def test_new_scores_highest(self):
        offer = _make_offer(
            condition=Condition(canonical=CanonicalCondition.NEW)
        )
        assert score_condition(offer) >= 0.95

    def test_for_parts_scores_lowest(self):
        offer = _make_offer(
            condition=Condition(canonical=CanonicalCondition.FOR_PARTS)
        )
        assert score_condition(offer) <= 0.2

    def test_ordering(self):
        """Condition scores should follow a logical ordering."""
        conditions = [
            CanonicalCondition.NEW,
            CanonicalCondition.CERTIFIED_REFURBISHED,
            CanonicalCondition.OPEN_BOX,
            CanonicalCondition.REFURBISHED,
            CanonicalCondition.USED_LIKE_NEW,
            CanonicalCondition.USED_GOOD,
            CanonicalCondition.USED_FAIR,
            CanonicalCondition.FOR_PARTS,
        ]
        scores = [
            score_condition(_make_offer(condition=Condition(canonical=c)))
            for c in conditions
        ]
        # Each score should be >= the next
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1], (
                f"{conditions[i].value} ({scores[i]:.2f}) should score >= "
                f"{conditions[i + 1].value} ({scores[i + 1]:.2f})"
            )


# ── Trust tests ─────────────────────────────────────────────────────


class TestTrust:
    def test_retailer_scores_higher_than_marketplace_seller(self):
        retailer = _make_offer(
            merchant=Merchant(
                marketplace="Best Buy",
                seller_type=SellerType.RETAILER,
            )
        )
        seller = _make_offer(
            source=Source.EBAY,
            merchant=Merchant(
                marketplace="eBay",
                seller_type=SellerType.MARKETPLACE_SELLER,
            ),
        )
        assert score_trust(retailer) > score_trust(seller)


# ── Overall scoring ─────────────────────────────────────────────────


class TestOverallScoring:
    def test_score_is_deterministic(self):
        product = _make_product()
        offer = _make_offer()
        plan = _make_plan()

        r1 = score_result(product, offer, plan, budget=1000.0)
        r2 = score_result(product, offer, plan, budget=1000.0)
        assert r1.overall_score == r2.overall_score

    def test_weights_must_sum_to_one(self):
        with pytest.raises(ValueError, match="sum to 1.0"):
            ScoringWeights(spec_fit=0.5, value=0.5, delivery=0.5, condition=0.0, trust=0.0).validate()

    def test_score_range(self):
        product = _make_product()
        offer = _make_offer()
        result = score_result(product, offer)
        assert 0.0 <= result.overall_score <= 1.0
        assert 0.0 <= result.components.spec_fit <= 1.0
        assert 0.0 <= result.components.value <= 1.0
