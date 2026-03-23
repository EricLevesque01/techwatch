"""Unit tests for the adapter base class infrastructure."""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from techwatch.adapters.base import (
    ALLOWED_DOMAINS,
    RateLimiter,
    ResponseCache,
    RetryPolicy,
    check_domain_allowlist,
)


class TestRateLimiter:
    def test_initial_tokens_available(self):
        limiter = RateLimiter(max_qps=10.0, burst=5)
        # Should not block when tokens are available
        start = time.monotonic()
        limiter.acquire()
        elapsed = time.monotonic() - start
        assert elapsed < 0.1

    def test_burst_allows_multiple_fast_calls(self):
        limiter = RateLimiter(max_qps=1.0, burst=3)
        start = time.monotonic()
        for _ in range(3):
            limiter.acquire()
        elapsed = time.monotonic() - start
        assert elapsed < 0.5  # Should be fast due to burst


class TestRetryPolicy:
    def test_exponential_backoff(self):
        policy = RetryPolicy(base_delay=1.0, jitter=0.0)
        assert policy.get_delay(0) == 1.0
        assert policy.get_delay(1) == 2.0
        assert policy.get_delay(2) == 4.0

    def test_max_delay_cap(self):
        policy = RetryPolicy(base_delay=1.0, max_delay=10.0, jitter=0.0)
        assert policy.get_delay(10) == 10.0

    def test_jitter_adds_randomness(self):
        policy = RetryPolicy(base_delay=1.0, jitter=0.5)
        delays = [policy.get_delay(0) for _ in range(10)]
        # With jitter, not all delays should be identical
        assert len(set(round(d, 2) for d in delays)) > 1


class TestResponseCache:
    def test_put_and_get(self, tmp_path):
        cache = ResponseCache(cache_dir=tmp_path / "cache", ttl=300)
        cache.put("https://example.com", {"q": "test"}, {"result": "data"})

        result = cache.get("https://example.com", {"q": "test"})
        assert result == {"result": "data"}

    def test_miss_returns_none(self, tmp_path):
        cache = ResponseCache(cache_dir=tmp_path / "cache", ttl=300)
        assert cache.get("https://nonexistent.com") is None

    def test_different_params_different_keys(self, tmp_path):
        cache = ResponseCache(cache_dir=tmp_path / "cache", ttl=300)
        cache.put("https://example.com", {"q": "a"}, {"result": "a"})
        cache.put("https://example.com", {"q": "b"}, {"result": "b"})

        assert cache.get("https://example.com", {"q": "a"}) == {"result": "a"}
        assert cache.get("https://example.com", {"q": "b"}) == {"result": "b"}

    def test_expired_entry_returns_none(self, tmp_path):
        cache = ResponseCache(cache_dir=tmp_path / "cache", ttl=0)
        cache.put("https://example.com", None, {"result": "old"})

        # TTL=0 means immediately expired
        import time
        time.sleep(0.01)
        assert cache.get("https://example.com") is None


class TestDomainAllowlist:
    def test_allowed_domains(self):
        assert check_domain_allowlist("https://api.bestbuy.com/v1/products")
        assert check_domain_allowlist("https://api.ebay.com/buy/browse/v1")
        assert check_domain_allowlist("https://www.ecb.europa.eu/stats")

    def test_rejected_domains(self):
        assert not check_domain_allowlist("https://evil.com/data")
        assert not check_domain_allowlist("https://amazon.com/product")
        assert not check_domain_allowlist("https://google.com")

    def test_all_allowed_domains_enumerated(self):
        """Verify the allowlist is not accidentally empty."""
        assert len(ALLOWED_DOMAINS) >= 5
        assert "api.bestbuy.com" in ALLOWED_DOMAINS
        assert "api.ebay.com" in ALLOWED_DOMAINS
