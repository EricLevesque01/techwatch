"""Unit tests for domain model validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from techwatch.models import (
    Analysis,
    Condition,
    Delivery,
    Merchant,
    Offer,
    Pricing,
    Product,
    ScoreComponents,
    SearchPlan,
    Specs,
    Watch,
    WatchTrigger,
)
from techwatch.models.enums import (
    CanonicalCondition,
    CosmeticGrade,
    FunctionalState,
    SellerType,
    Source,
    TriggerMetric,
    TriggerOperator,
)


class TestProduct:
    def test_minimal_product(self):
        p = Product(
            canonical_product_id="bestbuy:bestbuy:12345",
            title="MacBook Air M3",
            canonical_category="laptop",
        )
        assert p.title == "MacBook Air M3"
        assert p.specs.cpu is None

    def test_product_with_specs(self):
        p = Product(
            canonical_product_id="ebay:ebay:999",
            title="ThinkPad X1 Carbon",
            canonical_category="laptop",
            specs=Specs(cpu="Intel i7", ram_gb=16, storage_gb=512),
        )
        assert p.specs.ram_gb == 16

    def test_product_roundtrip_json(self):
        p = Product(
            canonical_product_id="test:test:1",
            title="Test",
            canonical_category="laptop",
            specs=Specs(cpu="M3"),
        )
        data = p.model_dump_json()
        p2 = Product.model_validate_json(data)
        assert p2.canonical_product_id == p.canonical_product_id


class TestOffer:
    def test_total_landed_cost(self):
        o = Offer(
            offer_id="o1",
            source=Source.BESTBUY,
            pricing=Pricing(sale_amount=899.99, shipping_amount=5.99, currency="USD"),
            merchant=Merchant(marketplace="Best Buy"),
        )
        assert o.pricing.total_landed_cost == pytest.approx(905.98, rel=1e-2)

    def test_effective_price_prefers_sale(self):
        p = Pricing(list_amount=999.99, sale_amount=799.99, currency="USD")
        assert p.effective_price == 799.99

    def test_effective_price_falls_back_to_list(self):
        p = Pricing(list_amount=999.99, currency="USD")
        assert p.effective_price == 999.99


class TestCondition:
    def test_three_axis_condition(self):
        c = Condition(
            canonical=CanonicalCondition.OPEN_BOX,
            source_label="Excellent",
            functional_state=FunctionalState.FULLY_FUNCTIONAL,
            cosmetic_grade=CosmeticGrade.EXCELLENT,
        )
        assert c.canonical == CanonicalCondition.OPEN_BOX
        assert c.functional_state == FunctionalState.FULLY_FUNCTIONAL
        assert c.cosmetic_grade == CosmeticGrade.EXCELLENT


class TestScoreComponents:
    def test_values_must_be_0_to_1(self):
        with pytest.raises(ValidationError):
            ScoreComponents(spec_fit=1.5)

    def test_valid_scores(self):
        s = ScoreComponents(spec_fit=0.8, value=0.7, delivery=0.6, condition=0.9, trust=0.85)
        assert s.spec_fit == 0.8


class TestWatch:
    def test_watch_creation_with_triggers(self):
        w = Watch(
            raw_query="gaming laptop",
            budget=1500.0,
            triggers=[
                WatchTrigger(
                    metric=TriggerMetric.PRICE_DROP_PCT,
                    operator=TriggerOperator.GTE,
                    threshold=8.0,
                ),
            ],
        )
        assert len(w.triggers) == 1
        assert w.triggers[0].threshold == 8.0

    def test_watch_id_auto_generated(self):
        w1 = Watch(raw_query="test1")
        w2 = Watch(raw_query="test2")
        assert w1.watch_id != w2.watch_id
        assert len(w1.watch_id) == 12
