"""Golden tests for email digest rendering."""

from __future__ import annotations

import pytest

from techwatch.email.renderer import render_digest, render_digest_html
from techwatch.models.narrative import DigestEntry, DigestPayload


@pytest.fixture
def sample_payload():
    return DigestPayload(
        watch_id="abc123def456",
        watch_query="used thinkpad x1 carbon",
        entries=[
            DigestEntry(
                offer_id="bb-12345",
                title="Lenovo ThinkPad X1 Carbon Gen 11",
                headline="Price dropped below 30-day median",
                price_display="USD 749.99",
                condition_display="open_box",
                trigger_reason="Price dropped 12.3% vs 30-day median",
                url="https://www.bestbuy.com/site/12345",
            ),
            DigestEntry(
                offer_id="ebay-67890",
                title="ThinkPad X1 Carbon Gen 10 - Excellent",
                headline="New offer entered top 3",
                price_display="USD 599.00",
                condition_display="used_good",
                trigger_reason="New offer ranked #2",
                url="https://www.ebay.com/itm/67890",
            ),
        ],
        summary="2 alerts: price drop + new top offer",
        generated_at_display="2026-05-05 09:00 UTC",
    )


class TestDigestRendering:
    def test_plaintext_contains_watch_query(self, sample_payload):
        subject, body = render_digest(sample_payload)
        assert "used thinkpad x1 carbon" in body

    def test_plaintext_contains_all_entries(self, sample_payload):
        subject, body = render_digest(sample_payload)
        assert "ThinkPad X1 Carbon Gen 11" in body
        assert "ThinkPad X1 Carbon Gen 10" in body

    def test_plaintext_contains_prices(self, sample_payload):
        _, body = render_digest(sample_payload)
        assert "USD 749.99" in body
        assert "USD 599.00" in body

    def test_plaintext_contains_trigger_reasons(self, sample_payload):
        _, body = render_digest(sample_payload)
        assert "12.3%" in body
        assert "ranked #2" in body

    def test_plaintext_contains_unsubscribe_instructions(self, sample_payload):
        _, body = render_digest(sample_payload)
        assert "techwatch watch pause" in body
        assert sample_payload.watch_id in body

    def test_subject_contains_query(self, sample_payload):
        subject, _ = render_digest(sample_payload)
        assert "used thinkpad x1 carbon" in subject

    def test_html_contains_entries(self, sample_payload):
        html = render_digest_html(sample_payload)
        assert "ThinkPad X1 Carbon Gen 11" in html
        assert "ThinkPad X1 Carbon Gen 10" in html

    def test_html_contains_links(self, sample_payload):
        html = render_digest_html(sample_payload)
        assert "bestbuy.com" in html
        assert "ebay.com" in html

    def test_html_contains_unsubscribe(self, sample_payload):
        html = render_digest_html(sample_payload)
        assert "techwatch watch pause" in html

    def test_single_entry_digest(self):
        payload = DigestPayload(
            watch_id="test123",
            watch_query="monitor",
            entries=[
                DigestEntry(
                    offer_id="x",
                    title="Dell Monitor",
                    headline="Great deal",
                    price_display="USD 299.99",
                    condition_display="new",
                    trigger_reason="Price dropped",
                ),
            ],
            summary="1 alert",
            generated_at_display="2026-05-05 09:00 UTC",
        )
        subject, body = render_digest(payload)
        assert "Dell Monitor" in body
        assert "Great deal" in subject  # Single entry puts headline in subject
