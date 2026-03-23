"""Unit tests for the source selector."""

from __future__ import annotations

import pytest

from techwatch.agents.source_selector import AdapterSelection, select_sources
from techwatch.models import SearchPlan
from techwatch.models.enums import CanonicalCondition, Source


class TestSourceSelector:
    def test_us_new_selects_bestbuy_and_ebay(self):
        plan = SearchPlan(
            canonical_category="laptop",
            keywords=["thinkpad"],
            conditions=[CanonicalCondition.NEW],
            country="US",
        )
        selections = select_sources(plan)
        adapters = [s.adapter_name for s in selections]
        assert "bestbuy_products" in adapters
        assert "ebay_browse" in adapters

    def test_us_openbox_selects_bestbuy_openbox(self):
        plan = SearchPlan(
            canonical_category="monitor",
            keywords=["oled"],
            conditions=[CanonicalCondition.OPEN_BOX],
            country="US",
        )
        selections = select_sources(plan)
        adapters = [s.adapter_name for s in selections]
        assert "bestbuy_openbox" in adapters

    def test_non_us_skips_bestbuy(self):
        plan = SearchPlan(
            canonical_category="laptop",
            keywords=["thinkpad"],
            conditions=[CanonicalCondition.NEW],
            country="UK",
        )
        selections = select_sources(plan)
        adapters = [s.adapter_name for s in selections]
        assert "bestbuy_products" not in adapters
        assert "ebay_browse" in adapters

    def test_used_conditions_always_include_ebay(self):
        plan = SearchPlan(
            canonical_category="phone",
            keywords=["iphone"],
            conditions=[CanonicalCondition.USED_GOOD, CanonicalCondition.USED_FAIR],
            country="US",
        )
        selections = select_sources(plan)
        adapters = [s.adapter_name for s in selections]
        assert "ebay_browse" in adapters
        assert "bestbuy_products" not in adapters

    def test_preferred_source_gets_priority(self):
        plan = SearchPlan(
            canonical_category="laptop",
            keywords=["laptop"],
            conditions=[CanonicalCondition.NEW],
            preferred_sources=[Source.EBAY],
            country="US",
        )
        selections = select_sources(plan)
        # eBay should be first when preferred
        assert selections[0].adapter_name == "ebay_browse"

    def test_returns_adapter_selections(self):
        plan = SearchPlan(
            canonical_category="laptop",
            conditions=[CanonicalCondition.NEW],
            country="US",
        )
        selections = select_sources(plan)
        assert all(isinstance(s, AdapterSelection) for s in selections)
        assert all(s.source in Source for s in selections)

    def test_all_conditions_selects_everything(self):
        plan = SearchPlan(
            canonical_category="laptop",
            conditions=list(CanonicalCondition),
            country="US",
        )
        selections = select_sources(plan)
        adapters = [s.adapter_name for s in selections]
        assert "bestbuy_products" in adapters
        assert "bestbuy_openbox" in adapters
        assert "ebay_browse" in adapters
