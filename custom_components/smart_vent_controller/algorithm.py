"""Pure algorithm functions for vent position targeting and airflow balancing.

Adapted from the HVAC Vent Optimizer's DAB module. All functions are stateless
and operate on plain data structures for testability.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class AlgorithmSettings:
    """Tuning knobs for vent targeting calculations (Fahrenheit-based)."""

    setpoint_offset: float = 1.0
    pre_adjust_threshold: float = 0.3
    max_minutes_to_setpoint: float = 60.0
    min_runtime_for_rate: float = 5.0
    min_detectable_temp_change: float = 0.2
    min_combined_vent_flow: float = 30.0
    increment_pct: float = 1.5
    max_iterations: int = 500
    standard_vent_default_open: float = 50.0
    thermostat_hysteresis: float = 1.0
    base_const: float = 0.0991
    exp_const: float = 2.3
    max_temp_change_rate: float = 2.5
    min_temp_change_rate: float = 0.001


DEFAULT_SETTINGS = AlgorithmSettings()


def round_to_granularity(value: float, granularity: int) -> int:
    """Round a vent position to the nearest allowed increment."""
    if granularity <= 0:
        return max(0, min(100, int(round(value))))
    rounded = int(round(value / granularity) * granularity)
    return max(0, min(100, rounded))


def has_reached_setpoint(hvac_mode: str, setpoint: float, current_temp: float) -> bool:
    """Check whether a room has reached its setpoint for the given HVAC mode."""
    if hvac_mode in ("cool", "cooling"):
        return current_temp <= setpoint
    return current_temp >= setpoint


def should_pre_adjust(
    hvac_mode: str,
    setpoint: float,
    current_temp: float,
    settings: AlgorithmSettings = DEFAULT_SETTINGS,
) -> bool:
    """Return True when temp is close enough to setpoint that vents should pre-position."""
    if hvac_mode in ("cool", "cooling"):
        return current_temp + settings.setpoint_offset - settings.pre_adjust_threshold >= setpoint
    if hvac_mode in ("heat", "heating"):
        return current_temp - settings.setpoint_offset + settings.pre_adjust_threshold <= setpoint
    return False


def compute_efficiency_sample(
    start_temp: float,
    end_temp: float,
    minutes: float,
    avg_aperture_pct: float,
    hvac_mode: str,
    settings: AlgorithmSettings = DEFAULT_SETTINGS,
) -> float | None:
    """Derive an efficiency rate from a single HVAC cycle observation.

    Returns a positive rate (deg-F per minute at 100% open) or None if the
    sample should be rejected.
    """
    if minutes < settings.min_runtime_for_rate:
        return None
    if avg_aperture_pct <= 0:
        return None

    delta = abs(end_temp - start_temp)
    if delta < settings.min_detectable_temp_change:
        return None

    if hvac_mode in ("heat", "heating") and end_temp < start_temp:
        return None
    if hvac_mode in ("cool", "cooling") and end_temp > start_temp:
        return None

    raw_rate = delta / minutes
    normalised = raw_rate / (avg_aperture_pct / 100.0)

    if normalised > settings.max_temp_change_rate:
        return None
    return max(normalised, settings.min_temp_change_rate)


def calculate_vent_target(
    current_temp: float,
    setpoint: float,
    efficiency_rate: float,
    longest_time: float,
    hvac_mode: str,
    settings: AlgorithmSettings = DEFAULT_SETTINGS,
) -> float:
    """Calculate an ideal vent open percentage for one room (exponential model).

    Returns a float 0..100.
    """
    if has_reached_setpoint(hvac_mode, setpoint, current_temp):
        return 0.0
    if efficiency_rate <= 0 or longest_time <= 0:
        return 100.0

    target_rate = abs(setpoint - current_temp) / longest_time
    pct = settings.base_const * math.exp((target_rate / efficiency_rate) * settings.exp_const)
    return max(0.0, min(100.0, pct * 100.0))


def calculate_linear_target(
    current_temp: float,
    setpoint: float,
    efficiency_rate: float,
    longest_time: float,
    hvac_mode: str,
) -> float:
    """Simple linear vent target: (needed_rate / room_rate) * 100."""
    if has_reached_setpoint(hvac_mode, setpoint, current_temp):
        return 0.0
    if efficiency_rate <= 0 or longest_time <= 0:
        return 100.0

    needed_rate = abs(setpoint - current_temp) / longest_time
    pct = (needed_rate / efficiency_rate) * 100.0
    return max(0.0, min(100.0, pct))


def calculate_longest_time_to_target(
    rooms: list[dict],
    hvac_mode: str,
    setpoint: float,
    max_running_minutes: float = 60.0,
) -> float:
    """Find the longest estimated minutes-to-setpoint across active rooms.

    Each room dict must contain keys: ``temp`` (float), ``rate`` (float),
    ``active`` (bool, optional, default True).
    """
    longest = -1.0
    for room in rooms:
        if not room.get("active", True):
            continue
        temp = room.get("temp")
        rate = room.get("rate", 0.0)
        if temp is None or rate <= 0:
            continue
        if has_reached_setpoint(hvac_mode, setpoint, temp):
            continue
        minutes = abs(setpoint - temp) / rate
        minutes = min(minutes, max_running_minutes)
        longest = max(longest, minutes)
    return longest


def calculate_all_vent_targets(
    rooms: list[dict],
    hvac_mode: str,
    setpoint: float,
    longest_time: float,
    strategy: str = "simple",
    settings: AlgorithmSettings = DEFAULT_SETTINGS,
) -> dict[str, float]:
    """Compute target vent % for every room.

    Each room dict must have: ``key`` (str), ``temp`` (float),
    ``rate`` (float), ``active`` (bool, default True).

    Returns ``{room_key: target_pct}``.
    """
    targets: dict[str, float] = {}
    for room in rooms:
        key = room["key"]
        temp = room.get("temp")
        rate = room.get("rate", 0.0)
        active = room.get("active", True)

        if not active:
            targets[key] = 0.0
            continue
        if temp is None:
            targets[key] = 100.0
            continue

        if strategy == "learned":
            targets[key] = calculate_vent_target(
                temp, setpoint, rate, longest_time, hvac_mode, settings
            )
        elif strategy == "hybrid":
            exp_target = calculate_vent_target(
                temp, setpoint, rate, longest_time, hvac_mode, settings
            )
            lin_target = calculate_linear_target(
                temp, setpoint, rate, longest_time, hvac_mode
            )
            targets[key] = (exp_target + lin_target) / 2.0
        else:
            targets[key] = calculate_linear_target(
                temp, setpoint, rate, longest_time, hvac_mode
            )
    return targets


def adjust_for_minimum_airflow(
    targets: dict[str, float],
    rooms: list[dict],
    hvac_mode: str,
    conventional_vent_count: int = 0,
    settings: AlgorithmSettings = DEFAULT_SETTINGS,
) -> dict[str, float]:
    """Boost vent targets until average flow meets the configured minimum.

    Modifies and returns *targets* in-place.  Rooms that need more conditioning
    (colder in heating, warmer in cooling) get proportionally more boost.
    """
    total_devices = conventional_vent_count
    flow_sum = conventional_vent_count * settings.standard_vent_default_open

    active_keys: list[str] = []
    for room in rooms:
        if not room.get("active", True):
            continue
        key = room["key"]
        active_keys.append(key)
        total_devices += 1
        flow_sum += targets.get(key, 0.0)

    if total_devices <= 0:
        return targets

    avg_flow = flow_sum / total_devices
    if avg_flow >= settings.min_combined_vent_flow:
        return targets

    needed = settings.min_combined_vent_flow * total_devices - flow_sum
    temps = [r.get("temp", 70.0) for r in rooms if r["key"] in active_keys]
    if not temps:
        return targets
    min_temp = min(temps) - 0.1
    max_temp = max(temps) + 0.1
    temp_range = max_temp - min_temp if max_temp != min_temp else 1.0

    iterations = 0
    while needed > 0 and iterations < settings.max_iterations:
        iterations += 1
        for room in rooms:
            key = room["key"]
            if key not in active_keys:
                continue
            current = targets.get(key, 0.0)
            if current >= 100:
                continue
            temp = room.get("temp", 70.0)

            if hvac_mode in ("cool", "cooling"):
                proportion = (temp - min_temp) / temp_range
            else:
                proportion = (max_temp - temp) / temp_range

            bump = settings.increment_pct * max(proportion, 0.1)
            targets[key] = min(100.0, current + bump)
            needed -= bump
            if needed <= 0:
                break

    return targets


def compute_simple_targets(
    rooms_data: list[dict],
    selected_keys: list[str],
    hvac_mode: str,
    hvac_action: str,
    min_open_pct: int,
) -> dict[str, float]:
    """Original simple targeting: selected rooms get 100%, others get min or 0.

    Preserved as the ``simple`` strategy fallback when no learned rates exist.
    """
    targets: dict[str, float] = {}
    for room in rooms_data:
        key = room["key"]
        if key in selected_keys:
            targets[key] = 100.0
        else:
            delta = room.get("delta", 0)
            should_close = False
            if hvac_mode in ("heat",) or hvac_action == "heating":
                should_close = delta < 0
            elif hvac_mode in ("cool",) or hvac_action == "cooling":
                should_close = delta > 0
            targets[key] = float(min_open_pct) if should_close else float(min_open_pct)
    return targets
