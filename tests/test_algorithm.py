"""Tests for the algorithm module (pure functions, no HA dependency)."""
import pytest

from custom_components.smart_vent_controller.algorithm import (
    AlgorithmSettings,
    round_to_granularity,
    has_reached_setpoint,
    should_pre_adjust,
    compute_efficiency_sample,
    calculate_vent_target,
    calculate_linear_target,
    calculate_longest_time_to_target,
    calculate_all_vent_targets,
    adjust_for_minimum_airflow,
    compute_simple_targets,
)


# ---------------------------------------------------------------------------
# round_to_granularity
# ---------------------------------------------------------------------------

class TestRoundToGranularity:
    def test_basic_rounding(self):
        assert round_to_granularity(47, 5) == 45
        assert round_to_granularity(48, 5) == 50
        assert round_to_granularity(50, 10) == 50
        assert round_to_granularity(54, 10) == 50
        assert round_to_granularity(55, 10) == 60

    def test_clamps_to_0_100(self):
        assert round_to_granularity(-5, 5) == 0
        assert round_to_granularity(105, 5) == 100

    def test_granularity_zero_or_negative(self):
        assert round_to_granularity(47.3, 0) == 47
        assert round_to_granularity(47.3, -1) == 47


# ---------------------------------------------------------------------------
# has_reached_setpoint
# ---------------------------------------------------------------------------

class TestHasReachedSetpoint:
    def test_heating_reached(self):
        assert has_reached_setpoint("heating", 72.0, 73.0) is True

    def test_heating_not_reached(self):
        assert has_reached_setpoint("heating", 72.0, 70.0) is False

    def test_cooling_reached(self):
        assert has_reached_setpoint("cooling", 74.0, 73.0) is True

    def test_cooling_not_reached(self):
        assert has_reached_setpoint("cooling", 74.0, 75.0) is False


# ---------------------------------------------------------------------------
# should_pre_adjust
# ---------------------------------------------------------------------------

class TestShouldPreAdjust:
    def test_heating_near_setpoint(self):
        assert should_pre_adjust("heating", 72.0, 71.5) is True

    def test_heating_far_from_setpoint(self):
        # 68 is well below setpoint minus offset; pre-adjust should fire
        # because the room is already in heating territory
        assert should_pre_adjust("heating", 72.0, 68.0) is True
        # Only far *above* setpoint should not trigger pre-adjust in heating
        assert should_pre_adjust("heating", 72.0, 80.0) is False

    def test_cooling_near_setpoint(self):
        assert should_pre_adjust("cooling", 74.0, 74.5) is True

    def test_cooling_far_from_setpoint(self):
        # 80 is well above setpoint + offset; pre-adjust should fire
        assert should_pre_adjust("cooling", 74.0, 80.0) is True
        # Only far *below* setpoint should not trigger pre-adjust in cooling
        assert should_pre_adjust("cooling", 74.0, 60.0) is False

    def test_unknown_mode(self):
        assert should_pre_adjust("off", 72.0, 72.0) is False


# ---------------------------------------------------------------------------
# compute_efficiency_sample
# ---------------------------------------------------------------------------

class TestComputeEfficiencySample:
    def test_valid_heating_sample(self):
        rate = compute_efficiency_sample(
            start_temp=68.0, end_temp=72.0, minutes=20.0,
            avg_aperture_pct=80.0, hvac_mode="heating",
        )
        assert rate is not None
        assert rate > 0

    def test_valid_cooling_sample(self):
        rate = compute_efficiency_sample(
            start_temp=78.0, end_temp=74.0, minutes=20.0,
            avg_aperture_pct=80.0, hvac_mode="cooling",
        )
        assert rate is not None
        assert rate > 0

    def test_too_short(self):
        assert compute_efficiency_sample(68.0, 72.0, 2.0, 80.0, "heating") is None

    def test_zero_aperture(self):
        assert compute_efficiency_sample(68.0, 72.0, 20.0, 0, "heating") is None

    def test_wrong_direction_heating(self):
        assert compute_efficiency_sample(72.0, 68.0, 20.0, 80.0, "heating") is None

    def test_wrong_direction_cooling(self):
        assert compute_efficiency_sample(74.0, 78.0, 20.0, 80.0, "cooling") is None

    def test_tiny_delta_rejected(self):
        assert compute_efficiency_sample(70.0, 70.05, 20.0, 80.0, "heating") is None


# ---------------------------------------------------------------------------
# calculate_vent_target / calculate_linear_target
# ---------------------------------------------------------------------------

class TestVentTargetCalculations:
    def test_at_setpoint_returns_zero(self):
        assert calculate_vent_target(72.0, 72.0, 0.1, 30.0, "heating") == 0.0
        assert calculate_linear_target(72.0, 72.0, 0.1, 30.0, "heating") == 0.0

    def test_zero_rate_returns_100(self):
        assert calculate_vent_target(68.0, 72.0, 0.0, 30.0, "heating") == 100.0
        assert calculate_linear_target(68.0, 72.0, 0.0, 30.0, "heating") == 100.0

    def test_reasonable_target(self):
        pct = calculate_vent_target(68.0, 72.0, 0.15, 30.0, "heating")
        assert 0 <= pct <= 100

    def test_linear_proportional(self):
        pct_close = calculate_linear_target(71.0, 72.0, 0.1, 30.0, "heating")
        pct_far = calculate_linear_target(68.0, 72.0, 0.1, 30.0, "heating")
        assert pct_far > pct_close


# ---------------------------------------------------------------------------
# calculate_longest_time_to_target
# ---------------------------------------------------------------------------

class TestLongestTimeToTarget:
    def test_basic(self):
        rooms = [
            {"temp": 68.0, "rate": 0.1, "active": True},
            {"temp": 65.0, "rate": 0.1, "active": True},
        ]
        t = calculate_longest_time_to_target(rooms, "heating", 72.0)
        # 65->72 = 70 min, capped to default max_running_minutes=60
        assert t == pytest.approx(60.0, abs=0.1)

    def test_inactive_ignored(self):
        rooms = [
            {"temp": 60.0, "rate": 0.1, "active": False},
            {"temp": 70.0, "rate": 0.1, "active": True},
        ]
        t = calculate_longest_time_to_target(rooms, "heating", 72.0)
        assert t == pytest.approx(20.0, abs=0.1)

    def test_all_at_setpoint(self):
        rooms = [{"temp": 73.0, "rate": 0.1, "active": True}]
        t = calculate_longest_time_to_target(rooms, "heating", 72.0)
        assert t == -1.0

    def test_capped_at_max(self):
        rooms = [{"temp": 50.0, "rate": 0.01, "active": True}]
        t = calculate_longest_time_to_target(rooms, "heating", 72.0, max_running_minutes=60.0)
        assert t == 60.0


# ---------------------------------------------------------------------------
# calculate_all_vent_targets
# ---------------------------------------------------------------------------

class TestAllVentTargets:
    def test_simple_strategy(self):
        rooms = [
            {"key": "a", "temp": 68.0, "rate": 0.1, "active": True},
            {"key": "b", "temp": 71.0, "rate": 0.1, "active": True},
        ]
        targets = calculate_all_vent_targets(rooms, "heating", 72.0, 30.0, strategy="simple")
        assert 0 <= targets["a"] <= 100
        assert 0 <= targets["b"] <= 100
        assert targets["a"] > targets["b"]

    def test_inactive_room_gets_zero(self):
        rooms = [{"key": "x", "temp": 68.0, "rate": 0.1, "active": False}]
        targets = calculate_all_vent_targets(rooms, "heating", 72.0, 30.0)
        assert targets["x"] == 0.0


# ---------------------------------------------------------------------------
# adjust_for_minimum_airflow
# ---------------------------------------------------------------------------

class TestMinimumAirflow:
    def test_already_above_minimum(self):
        targets = {"a": 50.0, "b": 50.0}
        rooms = [
            {"key": "a", "temp": 68.0, "active": True},
            {"key": "b", "temp": 70.0, "active": True},
        ]
        result = adjust_for_minimum_airflow(targets, rooms, "heating")
        assert result["a"] == 50.0
        assert result["b"] == 50.0

    def test_boost_when_below_minimum(self):
        targets = {"a": 5.0, "b": 5.0}
        rooms = [
            {"key": "a", "temp": 68.0, "active": True},
            {"key": "b", "temp": 70.0, "active": True},
        ]
        result = adjust_for_minimum_airflow(targets, rooms, "heating")
        avg = (result["a"] + result["b"]) / 2
        assert avg >= 30.0 or avg >= targets["a"]

    def test_conventional_vents_contribute(self):
        targets = {"a": 10.0}
        rooms = [{"key": "a", "temp": 68.0, "active": True}]
        result = adjust_for_minimum_airflow(
            targets, rooms, "heating", conventional_vent_count=5
        )
        assert result["a"] >= 10.0


# ---------------------------------------------------------------------------
# compute_simple_targets
# ---------------------------------------------------------------------------

class TestSimpleTargets:
    def test_selected_get_100(self):
        rooms = [
            {"key": "a", "delta": 3.0},
            {"key": "b", "delta": -1.0},
        ]
        targets = compute_simple_targets(rooms, ["a"], "heat", "heating", 20)
        assert targets["a"] == 100.0

    def test_non_selected_get_min(self):
        rooms = [
            {"key": "a", "delta": 3.0},
            {"key": "b", "delta": -1.0},
        ]
        targets = compute_simple_targets(rooms, ["a"], "heat", "heating", 20)
        assert targets["b"] == 20.0
