"""Unit tests for taxonomy category resolution."""

from __future__ import annotations

import pytest

from techwatch.taxonomy.categories import (
    CANONICAL_CATEGORIES,
    get_all_categories,
    get_category_label,
    resolve_bestbuy_category,
    resolve_ebay_category,
)


class TestBestBuyCategories:
    def test_laptop_category(self):
        assert resolve_bestbuy_category("abcat0502000") == "laptop"

    def test_monitor_category(self):
        assert resolve_bestbuy_category("pcmcat241600050001") == "monitor"

    def test_tv_category(self):
        assert resolve_bestbuy_category("abcat0101000") == "tv"

    def test_unknown_returns_other(self):
        assert resolve_bestbuy_category("nonexistent") == "other"


class TestEbayCategories:
    def test_laptop_category(self):
        assert resolve_ebay_category("175672") == "laptop"

    def test_phone_category(self):
        assert resolve_ebay_category("9355") == "phone"

    def test_gpu_category(self):
        assert resolve_ebay_category("27386") == "gpu"

    def test_unknown_returns_other(self):
        assert resolve_ebay_category("999999") == "other"


class TestCanonicalCategories:
    def test_all_categories_have_labels(self):
        for cat in get_all_categories():
            label = get_category_label(cat)
            assert label
            assert label != cat  # Label should differ from key

    def test_laptop_label(self):
        assert get_category_label("laptop") == "Laptops & Notebooks"

    def test_unknown_category_returns_titlecase(self):
        assert get_category_label("foobar") == "Foobar"

    def test_registry_not_empty(self):
        assert len(CANONICAL_CATEGORIES) >= 10
        assert "other" in CANONICAL_CATEGORIES
