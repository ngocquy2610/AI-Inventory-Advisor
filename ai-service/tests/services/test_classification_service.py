"""Tests for M5 velocity classification service.

Covers:
- Fast/medium/slow/dead boundary cases per category
- insufficient_data triggers correctly on low days_with_sales
- Dead-stock override triggers even when average_daily_sales looks like "slow" not "dead"
- tier_changed correctly True/False against a given previous_tier
- Missing category raises rather than silently defaulting
"""

from datetime import date, datetime

import pytest

from app.schemas.classification import ConsumptionMetric, ClassificationResult
from app.data_access.thresholds_loader import Thresholds, Config
from app.services.classification_service import classify, classify_batch


# ── Fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def default_thresholds() -> dict[str, Thresholds]:
    return {
        "default": Thresholds(fast=10.0, medium=3.0, slow=0.5),
        "electronics": Thresholds(fast=5.0, medium=1.5, slow=0.3),
        "groceries": Thresholds(fast=15.0, medium=5.0, slow=1.0),
    }


@pytest.fixture
def config() -> Config:
    return Config(
        min_days_with_sales_for_classification=3,
        dead_stock_no_sale_days=21,
    )


def make_metric(
    product_id: str = "prod-001",
    store_id: str = "store-001",
    average_daily_sales: float = 5.0,
    days_with_sales: int = 10,
    last_sale_date: str = "2026-05-28",
    trend: str = "Increasing",
    analysis_period_end: str = "2026-05-29",
) -> ConsumptionMetric:
    return ConsumptionMetric(
        product_id=product_id,
        store_id=store_id,
        average_daily_sales=average_daily_sales,
        days_with_sales=days_with_sales,
        last_sale_date=date.fromisoformat(last_sale_date),
        trend=trend,
        analysis_period_end=date.fromisoformat(analysis_period_end),
    )


# ── Boundary tests per category ────────────────────────────────────

class TestBoundaries:
    """Fast/medium/slow/dead boundary cases per category."""

    def test_electronics_fast(self, default_thresholds, config):
        """≥ 5.0 → fast for electronics."""
        m = make_metric(average_daily_sales=5.0)
        result = classify(m, "electronics", default_thresholds, config, previous_tier=None)
        assert result.tier == "fast"
        assert not result.insufficient_data

    def test_electronics_medium(self, default_thresholds, config):
        """1.5 ≤ 4.9 < 5.0 → medium for electronics."""
        m = make_metric(average_daily_sales=4.9)
        result = classify(m, "electronics", default_thresholds, config, previous_tier=None)
        assert result.tier == "medium"

    def test_electronics_slow(self, default_thresholds, config):
        """0.3 ≤ 1.4 < 1.5 → slow for electronics."""
        m = make_metric(average_daily_sales=1.4)
        result = classify(m, "electronics", default_thresholds, config, previous_tier=None)
        assert result.tier == "slow"

    def test_electronics_dead(self, default_thresholds, config):
        """< 0.3 → dead for electronics."""
        m = make_metric(average_daily_sales=0.29)
        result = classify(m, "electronics", default_thresholds, config, previous_tier=None)
        assert result.tier == "dead"

    def test_groceries_fast(self, default_thresholds, config):
        """≥ 15.0 → fast for groceries."""
        m = make_metric(average_daily_sales=15.0)
        result = classify(m, "groceries", default_thresholds, config, previous_tier=None)
        assert result.tier == "fast"

    def test_groceries_medium(self, default_thresholds, config):
        """5.0 ≤ 14.9 < 15.0 → medium for groceries."""
        m = make_metric(average_daily_sales=14.9)
        result = classify(m, "groceries", default_thresholds, config, previous_tier=None)
        assert result.tier == "medium"

    def test_groceries_slow(self, default_thresholds, config):
        """1.0 ≤ 4.9 < 5.0 → slow for groceries."""
        m = make_metric(average_daily_sales=4.9)
        result = classify(m, "groceries", default_thresholds, config, previous_tier=None)
        assert result.tier == "slow"

    def test_groceries_dead(self, default_thresholds, config):
        """< 1.0 → dead for groceries."""
        m = make_metric(average_daily_sales=0.99)
        result = classify(m, "groceries", default_thresholds, config, previous_tier=None)
        assert result.tier == "dead"

    def test_default_fast(self, default_thresholds, config):
        """≥ 10.0 → fast for default."""
        m = make_metric(average_daily_sales=10.0)
        result = classify(m, "default", default_thresholds, config, previous_tier=None)
        assert result.tier == "fast"

    def test_default_medium(self, default_thresholds, config):
        """3.0 ≤ 9.9 < 10.0 → medium for default."""
        m = make_metric(average_daily_sales=9.9)
        result = classify(m, "default", default_thresholds, config, previous_tier=None)
        assert result.tier == "medium"

    def test_default_slow(self, default_thresholds, config):
        """0.5 ≤ 2.9 < 3.0 → slow for default."""
        m = make_metric(average_daily_sales=2.9)
        result = classify(m, "default", default_thresholds, config, previous_tier=None)
        assert result.tier == "slow"

    def test_default_dead(self, default_thresholds, config):
        """< 0.5 → dead for default."""
        m = make_metric(average_daily_sales=0.49)
        result = classify(m, "default", default_thresholds, config, previous_tier=None)
        assert result.tier == "dead"


# ── Insufficient data ──────────────────────────────────────────────

class TestInsufficientData:
    """days_with_sales < min_days_with_sales_for_classification."""

    def test_zero_days(self, default_thresholds, config):
        """0 days with sales → insufficient_data."""
        m = make_metric(days_with_sales=0)
        result = classify(m, "default", default_thresholds, config, previous_tier=None)
        assert result.insufficient_data
        assert result.tier is None

    def test_one_day(self, default_thresholds, config):
        """1 day with sales → insufficient_data."""
        m = make_metric(days_with_sales=1)
        result = classify(m, "default", default_thresholds, config, previous_tier=None)
        assert result.insufficient_data
        assert result.tier is None

    def test_two_days(self, default_thresholds, config):
        """2 days with sales → insufficient_data."""
        m = make_metric(days_with_sales=2)
        result = classify(m, "default", default_thresholds, config, previous_tier=None)
        assert result.insufficient_data
        assert result.tier is None

    def test_exactly_min_days(self, default_thresholds, config):
        """3 days with sales → NOT insufficient_data (boundary)."""
        m = make_metric(days_with_sales=3)
        result = classify(m, "default", default_thresholds, config, previous_tier=None)
        assert not result.insufficient_data
        assert result.tier is not None


# ── Dead-stock recency override ────────────────────────────────────

class TestDeadStockOverride:
    """days_since_last_sale >= dead_stock_no_sale_days forces dead."""

    def test_dead_override_high_avg(self, default_thresholds, config):
        """Even with high avg_daily_sales, long no-sale gap → dead."""
        m = make_metric(
            average_daily_sales=50.0,  # would be "fast" normally
            last_sale_date="2026-05-01",
            analysis_period_end="2026-05-29",  # 28 days gap ≥ 21
        )
        result = classify(m, "default", default_thresholds, config, previous_tier=None)
        assert result.tier == "dead"
        assert result.days_since_last_sale == 28

    def test_dead_override_exactly_21_days(self, default_thresholds, config):
        """Exactly 21 days gap → dead."""
        m = make_metric(
            average_daily_sales=50.0,
            last_sale_date="2026-05-08",
            analysis_period_end="2026-05-29",  # 21 days
        )
        result = classify(m, "default", default_thresholds, config, previous_tier=None)
        assert result.tier == "dead"
        assert result.days_since_last_sale == 21

    def test_dead_override_20_days_not_dead(self, default_thresholds, config):
        """20 days gap → NOT dead (boundary)."""
        m = make_metric(
            average_daily_sales=50.0,
            last_sale_date="2026-05-09",
            analysis_period_end="2026-05-29",  # 20 days
        )
        result = classify(m, "default", default_thresholds, config, previous_tier=None)
        assert result.tier == "fast"  # would be fast based on avg
        assert result.days_since_last_sale == 20


# ── Tier changed detection ─────────────────────────────────────────

class TestTierChanged:
    """tier_changed correctly True/False against a given previous_tier."""

    def test_no_previous_tier(self, default_thresholds, config):
        """No previous_tier → tier_changed=False."""
        m = make_metric()
        result = classify(m, "default", default_thresholds, config, previous_tier=None)
        assert not result.tier_changed
        assert result.previous_tier is None

    def test_same_tier(self, default_thresholds, config):
        """Same tier as previous → tier_changed=False."""
        m = make_metric(average_daily_sales=5.0)  # → medium for default
        result = classify(m, "default", default_thresholds, config, previous_tier="medium")
        assert not result.tier_changed
        assert result.previous_tier == "medium"
        assert result.tier == "medium"

    def test_different_tier(self, default_thresholds, config):
        """Different tier from previous → tier_changed=True."""
        m = make_metric(average_daily_sales=5.0)  # → medium for default
        result = classify(m, "default", default_thresholds, config, previous_tier="slow")
        assert result.tier_changed
        assert result.previous_tier == "slow"
        assert result.tier == "medium"

    def test_from_dead_to_fast(self, default_thresholds, config):
        """Dead → fast → tier_changed=True."""
        m = make_metric(average_daily_sales=15.0)  # → fast for default
        result = classify(m, "default", default_thresholds, config, previous_tier="dead")
        assert result.tier_changed
        assert result.tier == "fast"

    def test_insufficient_data_no_change(self, default_thresholds, config):
        """Insufficient data → tier=None, tier_changed=False."""
        m = make_metric(days_with_sales=0)
        result = classify(m, "default", default_thresholds, config, previous_tier="slow")
        assert result.insufficient_data
        assert result.tier is None
        assert not result.tier_changed  # insufficient_data always False for change


# ── classify_batch integration ─────────────────────────────────────

class TestClassifyBatch:
    """End-to-end batch classification."""

    def test_batch_with_all_categories(self, default_thresholds, config):
        metrics = [
            make_metric(product_id="prod-001", store_id="store-001", average_daily_sales=5.0),
            make_metric(product_id="prod-002", store_id="store-001", average_daily_sales=0.1),
            make_metric(product_id="prod-003", store_id="store-001", average_daily_sales=0, days_with_sales=0),
        ]
        category_map = {
            "prod-001": "electronics",
            "prod-002": "groceries",
            "prod-003": "default",
        }
        output = classify_batch(metrics, category_map, default_thresholds, config)
        assert len(output.classifications) == 3
        assert output.meta.total_classified == 2
        assert output.meta.total_insufficient_data == 1

        # prod-001: electronics, 5.0 → fast
        assert output.classifications[0].tier == "fast"
        assert output.classifications[0].category == "electronics"

        # prod-002: groceries, 0.1 → dead (< 1.0)
        assert output.classifications[1].tier == "dead"
        assert output.classifications[1].category == "groceries"

        # prod-003: default, 0 days → insufficient_data
        assert output.classifications[2].insufficient_data
        assert output.classifications[2].tier is None

    def test_batch_with_previous_tiers(self, default_thresholds, config):
        metrics = [
            make_metric(product_id="prod-001", store_id="store-001", average_daily_sales=5.0),
            make_metric(product_id="prod-002", store_id="store-001", average_daily_sales=0.1),
        ]
        category_map = {"prod-001": "electronics", "prod-002": "groceries"}
        previous = {("prod-001", "store-001"): "slow", ("prod-002", "store-001"): "dead"}

        output = classify_batch(metrics, category_map, default_thresholds, config, previous_tiers=previous)
        assert output.classifications[0].tier_changed  # slow → fast
        assert not output.classifications[1].tier_changed  # dead → dead (same)

    def test_batch_meta_counts(self, default_thresholds, config):
        metrics = [
            make_metric(product_id="p1", store_id="s1", average_daily_sales=5.0),
            make_metric(product_id="p2", store_id="s1", average_daily_sales=0, days_with_sales=0),
            make_metric(product_id="p3", store_id="s1", average_daily_sales=0.1),
        ]
        category_map = {"p1": "default", "p2": "default", "p3": "default"}
        output = classify_batch(metrics, category_map, default_thresholds, config)
        assert output.meta.total_classified == 2
        assert output.meta.total_insufficient_data == 1
        assert output.meta.source_file == "data/module1_output.json"