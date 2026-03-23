"""Unit tests for the JSON-LD structured data extractor."""

from __future__ import annotations

import pytest

from techwatch.adapters.structured.jsonld import JsonLdExtractor


class TestJsonLdBlockExtraction:
    """Tests for _extract_jsonld_blocks (HTML -> dicts)."""

    def setup_method(self):
        self.extractor = JsonLdExtractor()

    def test_single_block(self):
        html = """
        <html>
        <head>
        <script type="application/ld+json">
        {"@type": "Product", "name": "Test Product"}
        </script>
        </head>
        <body></body>
        </html>
        """
        blocks = self.extractor._extract_jsonld_blocks(html)
        assert len(blocks) == 1
        assert blocks[0]["@type"] == "Product"

    def test_multiple_blocks(self):
        html = """
        <html><head>
        <script type="application/ld+json">{"@type": "Product", "name": "A"}</script>
        <script type="application/ld+json">{"@type": "Organization", "name": "B"}</script>
        </head><body></body></html>
        """
        blocks = self.extractor._extract_jsonld_blocks(html)
        assert len(blocks) == 2

    def test_array_block(self):
        html = """
        <script type="application/ld+json">
        [{"@type": "Product", "name": "A"}, {"@type": "Product", "name": "B"}]
        </script>
        """
        blocks = self.extractor._extract_jsonld_blocks(html)
        assert len(blocks) == 2

    def test_invalid_json_skipped(self):
        html = """
        <script type="application/ld+json">not valid json</script>
        <script type="application/ld+json">{"@type": "Product", "name": "OK"}</script>
        """
        blocks = self.extractor._extract_jsonld_blocks(html)
        assert len(blocks) == 1

    def test_no_blocks(self):
        html = "<html><body>No JSON-LD here</body></html>"
        blocks = self.extractor._extract_jsonld_blocks(html)
        assert len(blocks) == 0

    def teardown_method(self):
        self.extractor.close()


class TestProductExtraction:
    """Tests for _find_products (filtering Product entities)."""

    def setup_method(self):
        self.extractor = JsonLdExtractor()

    def test_direct_product(self):
        blocks = [{"@type": "Product", "name": "P1"}]
        products = self.extractor._find_products(blocks)
        assert len(products) == 1

    def test_product_in_graph(self):
        blocks = [
            {
                "@graph": [
                    {"@type": "WebPage", "name": "Page"},
                    {"@type": "Product", "name": "P1"},
                    {"@type": "Organization", "name": "Org"},
                ]
            }
        ]
        products = self.extractor._find_products(blocks)
        assert len(products) == 1
        assert products[0]["name"] == "P1"

    def test_no_products(self):
        blocks = [{"@type": "Organization", "name": "Org"}]
        products = self.extractor._find_products(blocks)
        assert len(products) == 0

    def teardown_method(self):
        self.extractor.close()


class TestProductNormalization:
    """Tests for _normalize_product (Schema.org -> flat dict)."""

    def setup_method(self):
        self.extractor = JsonLdExtractor()

    def test_basic_product(self):
        product = {
            "name": "Sony WH-1000XM5",
            "brand": {"name": "Sony"},
            "model": "WH-1000XM5",
            "sku": "sony-wh1000xm5",
            "gtin13": "4548736132450",
            "offers": {
                "@type": "Offer",
                "price": "299.99",
                "priceCurrency": "USD",
            },
        }
        result = self.extractor._normalize_product(product, "https://example.com")
        assert result["name"] == "Sony WH-1000XM5"
        assert result["brand"] == "Sony"
        assert result["gtin"] == "4548736132450"
        assert len(result["offers"]) == 1
        assert result["offers"][0]["price"] == 299.99

    def test_aggregate_offer(self):
        product = {
            "name": "Test",
            "offers": {
                "@type": "AggregateOffer",
                "offers": [
                    {"price": "100", "priceCurrency": "USD"},
                    {"price": "95", "priceCurrency": "USD"},
                ],
            },
        }
        result = self.extractor._normalize_product(product, "https://example.com")
        assert len(result["offers"]) == 2

    def test_no_offers(self):
        product = {"name": "Orphan"}
        result = self.extractor._normalize_product(product, "https://example.com")
        # No offers key means no offers parsed
        assert result["name"] == "Orphan"

    def test_image_extraction_string(self):
        product = {"name": "T", "image": "https://img.com/photo.jpg"}
        result = self.extractor._normalize_product(product, "https://example.com")
        assert result["image"] == "https://img.com/photo.jpg"

    def test_image_extraction_list(self):
        product = {"name": "T", "image": ["https://img.com/1.jpg", "https://img.com/2.jpg"]}
        result = self.extractor._normalize_product(product, "https://example.com")
        assert result["image"] == "https://img.com/1.jpg"

    def test_image_extraction_dict(self):
        product = {"name": "T", "image": {"url": "https://img.com/x.jpg"}}
        result = self.extractor._normalize_product(product, "https://example.com")
        assert result["image"] == "https://img.com/x.jpg"

    def teardown_method(self):
        self.extractor.close()
