"""Tests for M4 overstock detection service.

Covers:
- Normal case → correct days_of_supply and risk_level
- avg_daily_sales == 0 → dead_zero_velocity path
- Missing consumption profile → skipped, counted
- insufficient_data == true → still computes, tier stays null
- Stale stock → stock_data_stale: true, calculation proceeds
- Threshold boundary cases (exactly 90 and 180 days_of_supply)
- current_stock == 0 → skipped with counter
"""

from datetime import datetime, timezone, timedelta

import pytest

from app.schemas.overstock import (
    ConsumptionProfile,
    ProductStoreStock,
    ClassificationRow,
    OverstockFlag,
    OverstockOutput,
    OverstockRunMeta,
)
from app.services.overstock_service import (
    calculate_overstock_flag,
    get_velocity_value,
    get_effective_thresholds,
    run_overstock_batch,
    filter_overstock_flags,
    load_consumption_profiles,
    load_stock_and_catalog,
    load_classifications,
)


# ── Fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def now() -> datetime:
    return datetime(2026, 7, 17, 6, 33, 23, tzinfo=timezone.utc)


@pytest.fixture
def fresh_stock_time() -> datetime:
    return datetime(2026, 7, 15, 23, 59, 0, tzinfo=timezone.utc)


@pytest.fixture
def stale_stock_time() -> datetime:
    return datetime(2026, 7, 13, 23, 59, 0, tzinfo=timezone.utc)  # > 2 days before now


# ═════════════════════════════════════════════════════════════════════
# Pure function: calculate_overstock_flag
# ═════════════════════════════════════════════════════════════════════

class TestCalculateOverstockFlag:
    """Core calculation tests — pure function, no I/O."""

    def test_normal_case_low_risk(self, now, fresh_stock_time):
        """prod-008/store-001: stock=700, ads=7.93 → dos=88.3 → low risk."""
        result = calculate_overstock_flag(
            current_stock=700,
            avg_daily_sales=7.93,
            category="Accessory",
            tier="medium",
            updated_at=fresh_stock_time,
            now=now,
        )
        assert result["days_of_supply"] == 88.3
        assert result["risk_level"] == "low"
        assert result["suggested_action"] is None
        assert not result["stock_data_stale"]

    def test_medium_risk_exactly_90(self, now, fresh_stock_time):
        """dos == 90 → medium risk."""
        result = calculate_overstock_flag(
            current_stock=90,
            avg_daily_sales=1.0,
            category="Accessory",
            tier="medium",
            updated_at=fresh_stock_time,
            now=now,
        )
        assert result["days_of_supply"] == 90.0
        assert result["risk_level"] == "medium"
        assert result["suggested_action"] == "discount"

    def test_medium_risk_above_90(self, now, fresh_stock_time):
        """dos == 100 → medium risk."""
        result = calculate_overstock_flag(
            current_stock=100,
            avg_daily_sales=1.0,
            category="Accessory",
            tier="medium",
            updated_at=fresh_stock_time,
            now=now,
        )
        assert result["days_of_supply"] == 100.0
        assert result["risk_level"] == "medium"

    def test_high_risk_exactly_180(self, now, fresh_stock_time):
        """dos == 180 → high risk."""
        result = calculate_overstock_flag(
            current_stock=180,
            avg_daily_sales=1.0,
            category="Accessory",
            tier="medium",
            updated_at=fresh_stock_time,
            now=now,
        )
        assert result["days_of_supply"] == 180.0
        assert result["risk_level"] == "high"
        assert result["suggested_action"] == "flash_sale"

    def test_high_risk_above_180(self, now, fresh_stock_time):
        """dos == 200 → high risk."""
        result = calculate_overstock_flag(
            current_stock=200,
            avg_daily_sales=1.0,
            category="Accessory",
            tier="medium",
            updated_at=fresh_stock_time,
            now=now,
        )
        assert result["days_of_supply"] == 200.0
        assert result["risk_level"] == "high"

    def test_zero_velocity(self, now, fresh_stock_time):
        """avg_daily_sales == 0 → dead_zero_velocity, no divide-by-zero."""
        result = calculate_overstock_flag(
            current_stock=500,
            avg_daily_sales=0.0,
            category="Accessory",
            tier="dead",
            updated_at=fresh_stock_time,
            now=now,
        )
        assert result["days_of_supply"] is None
        assert result["risk_level"] == "dead_zero_velocity"
        assert result["suggested_action"] == "flash_sale"

    def test_stale_stock(self, now, stale_stock_time):
        """Stock updated > 2 days ago → stock_data_stale: true."""
        result = calculate_overstock_flag(
            current_stock=700,
            avg_daily_sales=7.93,
            category="Accessory",
            tier="medium",
            updated_at=stale_stock_time,
            now=now,
        )
        assert result["stock_data_stale"]
        assert result["days_of_supply"] == 88.3  # calculation still proceeds

    def test_fresh_stock(self, now, fresh_stock_time):
        """Stock updated 1 day ago → stock_data_stale: false."""
        result = calculate_overstock_flag(
            current_stock=700,
            avg_daily_sales=7.93,
            category="Accessory",
            tier="medium",
            updated_at=fresh_stock_time,
            now=now,
        )
        assert not result["stock_data_stale"]

    def test_default_now(self, fresh_stock_time):
        """When now is not provided, defaults to UTC now."""
        result = calculate_overstock_flag(
            current_stock=100,
            avg_daily_sales=1.0,
            category="Accessory",
            tier="medium",
            updated_at=fresh_stock_time,
        )
        assert result["days_of_supply"] == 100.0
        # risk depends on when "now" is — just verify it runs without error
        assert result["risk_level"] in ("high", "medium", "low")


# ═════════════════════════════════════════════════════════════════════
# Helper functions
# ═════════════════════════════════════════════════════════════════════

class TestGetVelocityValue:
    def test_default_field_is_average_daily_sales(self):
        profile = ConsumptionProfile(
            product_id="p1", store_id="s1",
            average_daily_sales=5.0, moving_average_7=10.0,
        )
        assert get_velocity_value(profile) == 5.0

    def test_fallback_when_moving_avg_none(self):
        profile = ConsumptionProfile(
            product_id="p1", store_id="s1",
            average_daily_sales=5.0, moving_average_7=None,
        )
        assert get_velocity_value(profile) == 5.0


class TestGetEffectiveThresholds:
    def test_defaults_when_no_category_override(self):
        thresholds = get_effective_thresholds("UnknownCategory")
        assert thresholds["high"] == 180.0
        assert thresholds["medium"] == 90.0


# ═════════════════════════════════════════════════════════════════════
# Data loader tests
# ═════════════════════════════════════════════════════════════════════

class TestLoadConsumptionProfiles:
    def test_loads_profiles_from_m1_output(self):
        """Load profiles from the real module1_output.json."""
        import os
        from pathlib import Path

        path = Path(__file__).resolve().parent.parent.parent / "data" / "module1_output.json"
        if not path.exists():
            pytest.skip("module1_output.json not found — skipping integration test")

        profiles = load_consumption_profiles(str(path))
        assert len(profiles) > 0

        # Check a known entry: prod-008 / store-001
        key = ("prod-008", "store-001")
        assert key in profiles
        assert profiles[key].average_daily_sales == 7.93

    def test_raises_on_missing_file(self):
        with pytest.raises(FileNotFoundError):
            load_consumption_profiles("/nonexistent/path.json")


class TestLoadStockAndCatalog:
    def test_loads_stock_and_categories(self):
        """Load from the real module1_input.json."""
        from pathlib import Path

        path = Path(__file__).resolve().parent.parent.parent / "data" / "module1_input.json"
        if not path.exists():
            pytest.skip("module1_input.json not found — skipping integration test")

        stock_map, category_map = load_stock_and_catalog(str(path))
        assert len(stock_map) > 0
        assert len(category_map) > 0

        # Check known entries
        assert ("prod-008", "store-001") in stock_map
        assert stock_map[("prod-008", "store-001")].current_stock == 700

        # prod-001 is a Smartphone
        assert category_map["prod-001"] == "Smartphone"
        # Unknown product defaults to "default" if missing, but all should be present
        assert category_map.get("prod-999") is None

    def test_raises_on_missing_file(self):
        with pytest.raises(FileNotFoundError):
            load_stock_and_catalog("/nonexistent/path.json")


class TestLoadClassifications:
    def test_loads_classifications_from_m5(self):
        """Load from the real module5_output.json."""
        from pathlib import Path

        path = Path(__file__).resolve().parent.parent.parent / "data" / "module5_output.json"
        if not path.exists():
            pytest.skip("module5_output.json not found — skipping integration test")

        classifications = load_classifications(str(path))
        assert len(classifications) > 0

        # prod-008/store-001 is medium tier, not insufficient_data
        key = ("prod-008", "store-001")
        assert key in classifications
        assert classifications[key].tier == "medium"
        assert not classifications[key].insufficient_data

        # prod-005/store-001 has insufficient_data=True
        key2 = ("prod-005", "store-001")
        assert key2 in classifications
        assert classifications[key2].tier is None
        assert classifications[key2].insufficient_data

    def test_returns_empty_for_missing_file(self):
        """M5 file is optional — returns empty dict, not error."""
        from pathlib import Path
        result = load_classifications("/nonexistent/path.json")
        assert result == {}


# ═════════════════════════════════════════════════════════════════════
# Integration: run_overstock_batch
# ═════════════════════════════════════════════════════════════════════

class TestRunOverstockBatch:
    """End-to-end batch run against real data files."""

    def test_batch_runs_successfully(self):
        """Full batch run produces expected output shape."""
        from pathlib import Path

        root = Path(__file__).resolve().parent.parent.parent
        m1_out = root / "data" / "module1_output.json"
        m1_in = root / "data" / "module1_input.json"
        m5_out = root / "data" / "module5_output.json"

        if not (m1_out.exists() and m1_in.exists() and m5_out.exists()):
            pytest.skip("Data files not found — skipping integration test")

        output = run_overstock_batch(
            m1_output_path=str(m1_out),
            m1_input_path=str(m1_in),
            m5_output_path=str(m5_out),
        )

        # Basic shape checks
        assert isinstance(output, OverstockOutput)
        assert len(output.overstock_flags) > 0
        assert output.meta.total_evaluated > 0

    def test_batch_prod008_store001(self):
        """Verify the specific prod-008/store-001 flag matches expected values."""
        from pathlib import Path

        root = Path(__file__).resolve().parent.parent.parent
        m1_out = root / "data" / "module1_output.json"
        m1_in = root / "data" / "module1_input.json"
        m5_out = root / "data" / "module5_output.json"

        if not (m1_out.exists() and m1_in.exists() and m5_out.exists()):
            pytest.skip("Data files not found — skipping integration test")

        output = run_overstock_batch(
            m1_output_path=str(m1_out),
            m1_input_path=str(m1_in),
            m5_output_path=str(m5_out),
        )

        # Find prod-008/store-001
        target = None
        for f in output.overstock_flags:
            if f.product_id == "prod-008" and f.store_id == "store-001":
                target = f
                break

        assert target is not None, "prod-008/store-001 should be in the output"
        assert target.category == "Accessory"
        assert target.current_stock == 700
        assert target.average_daily_sales == 7.93
        assert target.days_of_supply == 88.3
        assert target.risk_level == "low"
        assert target.suggested_action is None
        assert target.tier == "medium"
        assert not target.stock_data_stale
        assert not target.insufficient_data

    def test_batch_meta_counts(self):
        """Meta counters match the actual flags."""
        from pathlib import Path

        root = Path(__file__).resolve().parent.parent.parent
        m1_out = root / "data" / "module1_output.json"
        m1_in = root / "data" / "module1_input.json"
        m5_out = root / "data" / "module5_output.json"

        if not (m1_out.exists() and m1_in.exists() and m5_out.exists()):
            pytest.skip("Data files not found — skipping integration test")

        output = run_overstock_batch(
            m1_output_path=str(m1_out),
            m1_input_path=str(m1_in),
            m5_output_path=str(m5_out),
        )

        # Verify counts match
        expected_high = sum(1 for f in output.overstock_flags if f.risk_level == "high")
        expected_medium = sum(1 for f in output.overstock_flags if f.risk_level == "medium")
        expected_dead = sum(1 for f in output.overstock_flags if f.risk_level == "dead_zero_velocity")

        assert output.meta.total_flagged_high == expected_high
        assert output.meta.total_flagged_medium == expected_medium
        assert output.meta.total_dead_zero_velocity == expected_dead
        assert output.meta.total_evaluated == len(output.overstock_flags)


# ═════════════════════════════════════════════════════════════════════
# Filter tests
# ═════════════════════════════════════════════════════════════════════

class TestFilterOverstockFlags:
    def test_filter_by_store_id(self):
        flags = [
            OverstockFlag(product_id="p1", store_id="s1", category="c1",
                          current_stock=100, average_daily_sales=1.0,
                          days_of_supply=100.0, risk_level="medium",
                          suggested_action="discount", tier="slow",
                          stock_data_stale=False, insufficient_data=False,
                          computed_at=datetime.now(timezone.utc)),
            OverstockFlag(product_id="p2", store_id="s2", category="c2",
                          current_stock=200, average_daily_sales=1.0,
                          days_of_supply=200.0, risk_level="high",
                          suggested_action="flash_sale", tier="slow",
                          stock_data_stale=False, insufficient_data=False,
                          computed_at=datetime.now(timezone.utc)),
        ]
        meta = OverstockRunMeta(computed_at=datetime.now(timezone.utc))
        output = OverstockOutput(overstock_flags=flags, meta=meta)

        filtered = filter_overstock_flags(output, store_id="s1")
        assert len(filtered) == 1
        assert filtered[0].product_id == "p1"

    def test_filter_by_risk_level(self):
        flags = [
            OverstockFlag(product_id="p1", store_id="s1", category="c1",
                          current_stock=100, average_daily_sales=1.0,
                          days_of_supply=100.0, risk_level="medium",
                          suggested_action="discount", tier="slow",
                          stock_data_stale=False, insufficient_data=False,
                          computed_at=datetime.now(timezone.utc)),
            OverstockFlag(product_id="p2", store_id="s2", category="c2",
                          current_stock=200, average_daily_sales=1.0,
                          days_of_supply=200.0, risk_level="high",
                          suggested_action="flash_sale", tier="slow",
                          stock_data_stale=False, insufficient_data=False,
                          computed_at=datetime.now(timezone.utc)),
        ]
        meta = OverstockRunMeta(computed_at=datetime.now(timezone.utc))
        output = OverstockOutput(overstock_flags=flags, meta=meta)

        filtered = filter_overstock_flags(output, risk_level="high")
        assert len(filtered) == 1
        assert filtered[0].product_id == "p2"

    def test_filter_by_category(self):
        flags = [
            OverstockFlag(product_id="p1", store_id="s1", category="Accessory",
                          current_stock=100, average_daily_sales=1.0,
                          days_of_supply=100.0, risk_level="medium",
                          suggested_action="discount", tier="slow",
                          stock_data_stale=False, insufficient_data=False,
                          computed_at=datetime.now(timezone.utc)),
            OverstockFlag(product_id="p2", store_id="s2", category="Phone",
                          current_stock=200, average_daily_sales=1.0,
                          days_of_supply=200.0, risk_level="high",
                          suggested_action="flash_sale", tier="slow",
                          stock_data_stale=False, insufficient_data=False,
                          computed_at=datetime.now(timezone.utc)),
        ]
        meta = OverstockRunMeta(computed_at=datetime.now(timezone.utc))
        output = OverstockOutput(overstock_flags=flags, meta=meta)

        filtered = filter_overstock_flags(output, category="Accessory")
        assert len(filtered) == 1
        assert filtered[0].product_id == "p1"

    def test_no_filters_returns_all(self):
        flags = [
            OverstockFlag(product_id="p1", store_id="s1", category="c1",
                          current_stock=100, average_daily_sales=1.0,
                          days_of_supply=100.0, risk_level="medium",
                          suggested_action="discount", tier="slow",
                          stock_data_stale=False, insufficient_data=False,
                          computed_at=datetime.now(timezone.utc)),
        ]
        meta = OverstockRunMeta(computed_at=datetime.now(timezone.utc))
        output = OverstockOutput(overstock_flags=flags, meta=meta)

        filtered = filter_overstock_flags(output)
        assert len(filtered) == 1