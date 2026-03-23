"""Unit tests for condition normalization.

Tests the deterministic mapping from marketplace-specific conditions
to the canonical 3-axis model (condition, functional_state, cosmetic_grade).
"""

from __future__ import annotations

import pytest

from techwatch.models.enums import CanonicalCondition, CosmeticGrade, FunctionalState
from techwatch.normalization.condition import (
    normalize_backmarket_condition,
    normalize_bestbuy_condition,
    normalize_ebay_condition,
    normalize_swappa_condition,
)


# ── Best Buy Open Box ───────────────────────────────────────────────


class TestBestBuyCondition:
    """Best Buy Open Box condition normalization tests."""

    def test_excellent_maps_correctly(self):
        c = normalize_bestbuy_condition("Excellent")
        assert c.canonical == CanonicalCondition.OPEN_BOX
        assert c.functional_state == FunctionalState.FULLY_FUNCTIONAL
        assert c.cosmetic_grade == CosmeticGrade.EXCELLENT
        assert c.source_label == "Excellent"

    def test_certified_maps_to_certified_refurbished(self):
        c = normalize_bestbuy_condition("Certified")
        assert c.canonical == CanonicalCondition.CERTIFIED_REFURBISHED
        assert c.functional_state == FunctionalState.FULLY_FUNCTIONAL
        assert c.cosmetic_grade == CosmeticGrade.PRISTINE

    def test_satisfactory_maps_to_fair(self):
        c = normalize_bestbuy_condition("Satisfactory")
        assert c.canonical == CanonicalCondition.OPEN_BOX
        assert c.cosmetic_grade == CosmeticGrade.FAIR

    def test_new_item(self):
        c = normalize_bestbuy_condition("New")
        assert c.canonical == CanonicalCondition.NEW

    def test_case_insensitive(self):
        c = normalize_bestbuy_condition("EXCELLENT")
        assert c.canonical == CanonicalCondition.OPEN_BOX

    def test_unknown_condition(self):
        c = normalize_bestbuy_condition("SomeNewLabel")
        assert c.canonical == CanonicalCondition.UNKNOWN
        assert c.source_label == "SomeNewLabel"


# ── eBay ────────────────────────────────────────────────────────────


class TestEbayCondition:
    """eBay condition ID normalization tests."""

    @pytest.mark.parametrize(
        "condition_id,expected_canonical",
        [
            (1000, CanonicalCondition.NEW),
            (1500, CanonicalCondition.OPEN_BOX),
            (2000, CanonicalCondition.CERTIFIED_REFURBISHED),
            (2010, CanonicalCondition.CERTIFIED_REFURBISHED),
            (2020, CanonicalCondition.REFURBISHED),
            (2030, CanonicalCondition.REFURBISHED),
            (2500, CanonicalCondition.REFURBISHED),
            (3000, CanonicalCondition.USED_LIKE_NEW),
            (4000, CanonicalCondition.USED_GOOD),
            (5000, CanonicalCondition.USED_GOOD),
            (6000, CanonicalCondition.USED_FAIR),
            (7000, CanonicalCondition.FOR_PARTS),
        ],
    )
    def test_known_condition_ids(self, condition_id: int, expected_canonical: CanonicalCondition):
        c = normalize_ebay_condition(condition_id)
        assert c.canonical == expected_canonical

    def test_certified_refurbished_is_fully_functional(self):
        c = normalize_ebay_condition(2000)
        assert c.functional_state == FunctionalState.FULLY_FUNCTIONAL
        assert c.cosmetic_grade == CosmeticGrade.EXCELLENT

    def test_for_parts_condition(self):
        c = normalize_ebay_condition(7000)
        assert c.functional_state == FunctionalState.FOR_PARTS
        assert c.cosmetic_grade == CosmeticGrade.POOR

    def test_custom_text_overrides_source_label(self):
        c = normalize_ebay_condition(3000, "Pre-owned - Like New")
        assert c.source_label == "Pre-owned - Like New"
        assert c.canonical == CanonicalCondition.USED_LIKE_NEW

    def test_unknown_condition_id(self):
        c = normalize_ebay_condition(9999)
        assert c.canonical == CanonicalCondition.UNKNOWN


# ── Back Market ─────────────────────────────────────────────────────


class TestBackMarketCondition:
    """Back Market condition normalization tests."""

    @pytest.mark.parametrize(
        "grade,expected_cosmetic",
        [
            ("Fair", CosmeticGrade.FAIR),
            ("Good", CosmeticGrade.GOOD),
            ("Excellent", CosmeticGrade.EXCELLENT),
            ("Premium", CosmeticGrade.PREMIUM),
        ],
    )
    def test_grade_mapping(self, grade: str, expected_cosmetic: CosmeticGrade):
        c = normalize_backmarket_condition(grade)
        assert c.cosmetic_grade == expected_cosmetic

    def test_all_grades_are_fully_functional(self):
        """Back Market guarantees 100% functionality regardless of appearance."""
        for grade in ("Fair", "Good", "Excellent", "Premium"):
            c = normalize_backmarket_condition(grade)
            assert c.functional_state == FunctionalState.FULLY_FUNCTIONAL

    def test_unknown_grade(self):
        c = normalize_backmarket_condition("SomeNewGrade")
        assert c.canonical == CanonicalCondition.UNKNOWN
        assert c.cosmetic_grade == CosmeticGrade.UNKNOWN
        assert c.functional_state == FunctionalState.FULLY_FUNCTIONAL


# ── Swappa ──────────────────────────────────────────────────────────


class TestSwappaCondition:
    """Swappa condition normalization tests."""

    def test_mint_condition(self):
        c = normalize_swappa_condition("Mint")
        assert c.canonical == CanonicalCondition.USED_LIKE_NEW
        assert c.cosmetic_grade == CosmeticGrade.PRISTINE

    def test_good_condition(self):
        c = normalize_swappa_condition("Good")
        assert c.canonical == CanonicalCondition.USED_GOOD
        assert c.cosmetic_grade == CosmeticGrade.GOOD

    def test_fair_condition(self):
        c = normalize_swappa_condition("Fair")
        assert c.canonical == CanonicalCondition.USED_FAIR
        assert c.cosmetic_grade == CosmeticGrade.FAIR

    def test_all_swappa_items_fully_functional(self):
        """Swappa requires all items to be fully functional."""
        for grade in ("Mint", "Good", "Fair"):
            c = normalize_swappa_condition(grade)
            assert c.functional_state == FunctionalState.FULLY_FUNCTIONAL
