"""Contract tests — verify that Pydantic schemas used for LLM structured outputs
remain valid and serialize/deserialize correctly.

These tests catch schema drift between our models and what OpenAI expects.
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from techwatch.models import (
    AlertDecision,
    OfferNarrative,
    SearchPlan,
)
from techwatch.models.enums import CanonicalCondition, Source


class TestSearchPlanContract:
    """SearchPlan is used as the response_model for the Planner agent."""

    def test_minimal_valid_plan(self):
        plan = SearchPlan(
            canonical_category="laptop",
            keywords=["thinkpad"],
            conditions=[CanonicalCondition.NEW],
            country="US",
        )
        assert plan.canonical_category == "laptop"

    def test_full_plan(self):
        plan = SearchPlan(
            canonical_category="monitor",
            keywords=["oled", "27 inch", "240hz"],
            required_specs={"screen_in": 27.0, "refresh_hz": 240},
            excluded_specs={"panel_type": "VA"},
            budget_max=800.0,
            budget_currency="USD",
            conditions=[CanonicalCondition.NEW, CanonicalCondition.OPEN_BOX],
            preferred_sources=[Source.BESTBUY, Source.EBAY],
            country="US",
            postal_code="10001",
            reasoning="User wants a high refresh OLED for gaming",
        )
        assert plan.budget_max == 800.0
        assert Source.BESTBUY in plan.preferred_sources

    def test_json_roundtrip(self):
        plan = SearchPlan(
            canonical_category="laptop",
            keywords=["macbook", "air"],
            required_specs={"ram_gb": 16},
            budget_max=1200.0,
            conditions=[CanonicalCondition.NEW, CanonicalCondition.CERTIFIED_REFURBISHED],
            country="US",
            reasoning="Looking for a MacBook Air with 16GB RAM",
        )
        json_str = plan.model_dump_json()
        restored = SearchPlan.model_validate_json(json_str)
        assert restored.canonical_category == "laptop"
        assert restored.required_specs["ram_gb"] == 16
        assert len(restored.conditions) == 2

    def test_json_schema_is_valid(self):
        schema = SearchPlan.model_json_schema()
        assert "properties" in schema
        assert "canonical_category" in schema["properties"]
        assert "keywords" in schema["properties"]
        assert "conditions" in schema["properties"]

    def test_strict_mode_rejects_type_coercion(self):
        """SearchPlan has strict=True, so type coercion must be rejected."""
        with pytest.raises(ValidationError):
            SearchPlan(
                canonical_category=123,  # type: ignore — should be str
                keywords=["test"],
                country="US",
                conditions=[CanonicalCondition.NEW],
            )

    def test_empty_keywords_allowed(self):
        plan = SearchPlan(
            canonical_category="laptop",
            country="US",
        )
        assert plan.keywords == []

    def test_conditions_default(self):
        plan = SearchPlan(canonical_category="laptop", country="US")
        assert CanonicalCondition.NEW in plan.conditions


class TestOfferNarrativeContract:
    """OfferNarrative is used as the response_model for the Explainer agent."""

    def test_minimal_narrative(self):
        n = OfferNarrative(
            headline="Good deal on a refurbished ThinkPad",
        )
        assert n.headline
        assert n.value_insight is None

    def test_full_narrative(self):
        n = OfferNarrative(
            headline="Excellent open-box deal",
            value_insight="22% below typical pricing",
            condition_insight="Excellent condition with full warranty",
            delivery_insight="Available for pickup today",
            recommendation="Strong buy for budget-conscious buyers",
            caveats="Open-box items have a shorter return window",
        )
        assert all([
            n.headline, n.value_insight, n.condition_insight,
            n.delivery_insight, n.recommendation, n.caveats,
        ])

    def test_json_roundtrip(self):
        n = OfferNarrative(
            headline="Test headline",
            value_insight="Test value",
        )
        restored = OfferNarrative.model_validate_json(n.model_dump_json())
        assert restored.headline == n.headline

    def test_json_schema_is_valid(self):
        schema = OfferNarrative.model_json_schema()
        assert "headline" in schema["properties"]


class TestAlertDecisionContract:
    """AlertDecision is used by the deal analyst (deterministic, not LLM)."""

    def test_no_alert(self):
        d = AlertDecision(should_alert=False)
        assert not d.should_alert
        assert d.triggered_rules == []

    def test_with_alert(self):
        d = AlertDecision(
            should_alert=True,
            triggered_rules=["Price dropped 12% vs median"],
            headline="Deal alert for ThinkPad X1",
            summary="Price dropped significantly",
            top_offer_ids=["bb-12345"],
        )
        assert d.should_alert
        assert len(d.triggered_rules) == 1

    def test_json_roundtrip(self):
        d = AlertDecision(
            should_alert=True,
            triggered_rules=["Test rule"],
            headline="Test",
            summary="Test summary",
            top_offer_ids=["id-1", "id-2"],
        )
        restored = AlertDecision.model_validate_json(d.model_dump_json())
        assert restored.top_offer_ids == ["id-1", "id-2"]
