"""Unit tests for the normalization engine — Best Buy, eBay, and JSON-LD mappers."""

from __future__ import annotations

import pytest

from techwatch.models.enums import CanonicalCondition, SellerType, Source
from techwatch.normalization.engine import (
    normalize_bestbuy_product,
    normalize_ebay_item,
    normalize_jsonld_product,
)


class TestBestBuyNormalization:
    """Tests for normalize_bestbuy_product."""

    def test_minimal_product(self):
        raw = {
            "sku": 12345,
            "name": "Test Laptop",
            "brandName": "TestBrand",
            "salePrice": 899.99,
            "regularPrice": 999.99,
            "categoryPath": [{"name": "Computers"}, {"name": "Laptops"}],
            "freeShipping": True,
            "condition": "New",
            "inStoreAvailability": True,
        }
        product, offer = normalize_bestbuy_product(raw)

        assert product.canonical_product_id == "bestbuy:bestbuy:12345"
        assert product.title == "Test Laptop"
        assert product.brand == "TestBrand"
        assert product.canonical_category == "laptop"
        assert offer.source == Source.BESTBUY
        assert offer.pricing.sale_amount == 899.99
        assert offer.pricing.shipping_amount == 0.0
        assert offer.delivery.pickup_available is True
        assert offer.merchant.seller_type == SellerType.RETAILER

    def test_spec_extraction(self):
        raw = {
            "sku": 99999,
            "name": "ThinkPad X1",
            "categoryPath": [{"name": "Laptops"}],
            "salePrice": 1200,
            "regularPrice": 1200,
            "freeShipping": True,
            "condition": "New",
            "details": [
                {"name": "Processor Model", "value": "Intel Core i7"},
                {"name": "System Memory RAM", "value": "16 GB"},
                {"name": "Total Storage Capacity", "value": "512GB"},
            ],
        }
        product, _ = normalize_bestbuy_product(raw)
        assert product.specs.cpu == "Intel Core i7"
        assert product.specs.ram_gb == 16
        assert product.specs.storage_gb == 512

    def test_condition_mapping(self):
        raw = {
            "sku": 1,
            "name": "Test",
            "categoryPath": [],
            "salePrice": 100,
            "freeShipping": True,
            "condition": "Excellent",
        }
        _, offer = normalize_bestbuy_product(raw)
        assert offer.condition.canonical == CanonicalCondition.OPEN_BOX


class TestEbayNormalization:
    """Tests for normalize_ebay_item."""

    def test_minimal_ebay_item(self):
        raw = {
            "itemId": "v1|123456|0",
            "title": "ThinkPad X1 Carbon Gen 11",
            "price": {"value": "649.99", "currency": "USD"},
            "conditionId": "3000",
            "condition": "Used",
            "seller": {
                "username": "tech_deals",
                "feedbackPercentage": "99.5",
                "feedbackScore": "1500",
            },
            "itemWebUrl": "https://www.ebay.com/itm/123456",
        }
        product, offer = normalize_ebay_item(raw)

        assert product.canonical_product_id == "ebay:ebay:v1|123456|0"
        assert product.title == "ThinkPad X1 Carbon Gen 11"
        assert offer.source == Source.EBAY
        assert offer.pricing.sale_amount == 649.99
        assert offer.condition.canonical == CanonicalCondition.USED_LIKE_NEW
        assert offer.merchant.seller_name == "tech_deals"
        assert offer.merchant.seller_feedback_pct == 99.5

    def test_missing_condition_id(self):
        raw = {
            "itemId": "v1|999|0",
            "title": "Unknown Item",
            "price": {"value": "100", "currency": "USD"},
        }
        _, offer = normalize_ebay_item(raw)
        assert offer.condition.canonical == CanonicalCondition.UNKNOWN

    def test_shipping_cost_parsed(self):
        raw = {
            "itemId": "v1|111|0",
            "title": "Test",
            "price": {"value": "50", "currency": "USD"},
            "conditionId": "1000",
            "shippingOptions": [{"shippingCost": {"value": "9.99", "currency": "USD"}}],
        }
        _, offer = normalize_ebay_item(raw)
        assert offer.pricing.shipping_amount == 9.99
        assert offer.pricing.total_landed_cost == pytest.approx(59.99)


class TestJsonLdNormalization:
    """Tests for normalize_jsonld_product."""

    def test_single_offer(self):
        raw = {
            "name": "Sony WH-1000XM5",
            "brand": "Sony",
            "model": "WH-1000XM5",
            "sku": "wh1000xm5",
            "category": "Headphones",
            "url": "https://example.com/product",
            "offers": [
                {
                    "price": 299.99,
                    "currency": "USD",
                    "seller": {"name": "Amazon", "type": "Organization"},
                    "url": "https://example.com/buy",
                },
            ],
        }
        results = normalize_jsonld_product(raw)
        assert len(results) == 1
        product, offer = results[0]
        assert product.title == "Sony WH-1000XM5"
        assert product.canonical_category == "headphones"
        assert offer.pricing.sale_amount == 299.99
        assert offer.merchant.seller_type == SellerType.RETAILER

    def test_multiple_offers(self):
        raw = {
            "name": "Test Product",
            "sku": "test-123",
            "offers": [
                {"price": 100, "currency": "USD"},
                {"price": 95, "currency": "USD"},
            ],
        }
        results = normalize_jsonld_product(raw)
        assert len(results) == 2

    def test_no_offers(self):
        raw = {"name": "Orphan Product", "sku": "none"}
        results = normalize_jsonld_product(raw)
        assert len(results) == 0
