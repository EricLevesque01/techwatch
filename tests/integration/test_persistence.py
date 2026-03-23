"""Integration tests for the persistence layer."""

from __future__ import annotations

import os
from datetime import datetime

import pytest

from techwatch.models import (
    Analysis,
    Offer,
    Pricing,
    Product,
    ScoreComponents,
    Watch,
    WatchTrigger,
)
from techwatch.models.enums import (
    CanonicalCondition,
    SellerType,
    Source,
    TriggerMetric,
    TriggerOperator,
    WatchStatus,
)
from techwatch.models.offer import Condition, Merchant
from techwatch.persistence.database import get_session, init_db, reset_engine
from techwatch.persistence.repos import OfferRepo, WatchRepo
from techwatch.config import reset_settings


@pytest.fixture(autouse=True)
def _clean_db(tmp_path):
    os.environ["DATABASE_URL"] = f"sqlite:///{tmp_path}/persist_test.db"
    reset_settings()
    reset_engine()
    init_db()
    yield
    reset_settings()
    reset_engine()


def _make_product(pid: str = "test:test:1") -> Product:
    return Product(
        canonical_product_id=pid,
        title="Test Product",
        canonical_category="laptop",
    )


def _make_offer(oid: str = "offer-1", price: float = 500.0) -> Offer:
    return Offer(
        offer_id=oid,
        source=Source.BESTBUY,
        condition=Condition(canonical=CanonicalCondition.NEW),
        pricing=Pricing(sale_amount=price, currency="USD"),
        merchant=Merchant(marketplace="Test", seller_type=SellerType.RETAILER),
    )


def _make_analysis(score: float = 0.75) -> Analysis:
    return Analysis(overall_score=score)


class TestOfferRepo:
    def test_upsert_creates_new_offer(self):
        with get_session() as session:
            repo = OfferRepo(session)
            row = repo.upsert(_make_product(), _make_offer(), _make_analysis())
            assert row.id is not None
            assert row.offer_id == "offer-1"

    def test_upsert_updates_existing(self):
        with get_session() as session:
            repo = OfferRepo(session)
            repo.upsert(_make_product(), _make_offer(price=500.0), _make_analysis(0.7))
            repo.upsert(_make_product(), _make_offer(price=450.0), _make_analysis(0.8))

            row = repo.get_by_offer_id("offer-1")
            assert row is not None
            assert row.sale_amount == 450.0
            assert row.overall_score == 0.8

    def test_price_history_grows(self):
        with get_session() as session:
            repo = OfferRepo(session)
            repo.upsert(_make_product(), _make_offer(price=500.0), _make_analysis())
            repo.upsert(_make_product(), _make_offer(price=480.0), _make_analysis())
            repo.upsert(_make_product(), _make_offer(price=460.0), _make_analysis())

            history = repo.get_price_history("offer-1", days=30)
            assert len(history) == 3

    def test_price_stats(self):
        with get_session() as session:
            repo = OfferRepo(session)
            for price in [500.0, 480.0, 460.0, 440.0, 420.0]:
                repo.upsert(_make_product(), _make_offer(price=price), _make_analysis())

            stats = repo.get_price_stats("offer-1", days=30)
            assert stats["count"] == 5
            assert stats["min"] == 420.0
            assert stats["max"] == 500.0
            assert stats["median"] is not None

    def test_get_nonexistent(self):
        with get_session() as session:
            repo = OfferRepo(session)
            assert repo.get_by_offer_id("nonexistent") is None


class TestWatchRepo:
    def test_create_and_get(self):
        watch = Watch(raw_query="test laptop", budget=900.0)
        with get_session() as session:
            repo = WatchRepo(session)
            row = repo.create(watch)
            assert row.watch_id == watch.watch_id

            retrieved = repo.get(watch.watch_id)
            assert retrieved is not None
            assert retrieved.raw_query == "test laptop"

    def test_list_active(self):
        with get_session() as session:
            repo = WatchRepo(session)
            repo.create(Watch(raw_query="active watch"))
            repo.create(Watch(raw_query="another active"))

            active = repo.list_active()
            assert len(active) == 2

    def test_pause_and_resume(self):
        watch = Watch(raw_query="pausable watch")
        with get_session() as session:
            repo = WatchRepo(session)
            repo.create(watch)

            repo.update_status(watch.watch_id, WatchStatus.PAUSED)
            row = repo.get(watch.watch_id)
            assert row.status == WatchStatus.PAUSED.value

            repo.update_status(watch.watch_id, WatchStatus.ACTIVE)
            row = repo.get(watch.watch_id)
            assert row.status == WatchStatus.ACTIVE.value

    def test_soft_delete(self):
        watch = Watch(raw_query="deletable")
        with get_session() as session:
            repo = WatchRepo(session)
            repo.create(watch)
            repo.update_status(watch.watch_id, WatchStatus.DELETED)

            all_watches = repo.list_all()
            assert len(all_watches) == 0  # Deleted are filtered

            active = repo.list_active()
            assert len(active) == 0

    def test_log_run(self):
        watch = Watch(raw_query="logged watch")
        with get_session() as session:
            repo = WatchRepo(session)
            repo.create(watch)

            now = datetime.utcnow()
            run = repo.log_run(
                watch.watch_id,
                started_at=now,
                finished_at=now,
                results_count=5,
                alerts_fired=True,
            )
            assert run.results_count == 5
            assert run.alerts_fired is True

    def test_update_last_run(self):
        watch = Watch(raw_query="timed watch")
        with get_session() as session:
            repo = WatchRepo(session)
            repo.create(watch)

            now = datetime.utcnow()
            repo.update_last_run(watch.watch_id, now)
            row = repo.get(watch.watch_id)
            assert row.last_run_at is not None

    def test_triggers_roundtrip(self):
        watch = Watch(
            raw_query="trigger watch",
            triggers=[
                WatchTrigger(
                    metric=TriggerMetric.PRICE_DROP_PCT,
                    operator=TriggerOperator.GTE,
                    threshold=8.0,
                ),
            ],
        )
        with get_session() as session:
            repo = WatchRepo(session)
            repo.create(watch)

            row = repo.get(watch.watch_id)
            triggers = row.get_triggers()
            assert len(triggers) == 1
            assert triggers[0]["threshold"] == 8.0
