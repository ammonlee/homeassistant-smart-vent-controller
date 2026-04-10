"""Script implementations for Smart Vent Controller.

Vent targeting now uses the algorithm module for continuous percentage
calculations with configurable granularity and adjustment throttling.
Thermostat control reads/writes cycle state via the coordinator's store.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    DEFAULT_INITIAL_EFFICIENCY,
    DEFAULT_VENT_GRANULARITY,
    DEFAULT_MIN_ADJUSTMENT_PCT,
    DEFAULT_MIN_ADJUSTMENT_INTERVAL_MIN,
    DEFAULT_TEMP_ERROR_OVERRIDE_F,
    DEFAULT_CONVENTIONAL_VENT_COUNT,
    DEFAULT_CONTROL_STRATEGY,
)
from .error_handling import (
    safe_float,
    safe_int,
    validate_entity_state,
    get_safe_state,
    get_safe_attribute,
    safe_service_call,
    validate_temperature,
    validate_vent_position,
    ErrorRecovery,
    EntityUnavailableError,
    ServiceCallError,
)
from .cache import ServiceCallBatcher
from .algorithm import (
    AlgorithmSettings,
    round_to_granularity,
    calculate_all_vent_targets,
    calculate_longest_time_to_target,
    adjust_for_minimum_airflow,
    compute_simple_targets,
    should_pre_adjust,
)

if TYPE_CHECKING:
    from .coordinator import SmartVentControllerCoordinator

_LOGGER = logging.getLogger(__name__)


class VentControlScript:
    """Controls vent positions using learned efficiency or simple targeting."""

    def __init__(self, hass: HomeAssistant, entry) -> None:
        self.hass = hass
        self.entry = entry
        self.error_recovery = ErrorRecovery(hass, entry)

    async def async_run(self, rooms_csv: str = "") -> None:
        try:
            if not self.entry.options.get("auto_vent_control", True):
                return
            if self.error_recovery.should_disable_component("vent_control"):
                _LOGGER.error(
                    "Vent control disabled due to repeated errors. "
                    "Fix issues and restart Home Assistant."
                )
                return

            debug = self.entry.options.get("debug_mode", False)
            coordinator: SmartVentControllerCoordinator = self.hass.data.get(
                DOMAIN, {}
            ).get(self.entry.entry_id)

            main_thermostat = self.entry.data.get("main_thermostat")
            if not validate_entity_state(self.hass, main_thermostat, "climate"):
                _LOGGER.error("Thermostat %s unavailable", main_thermostat)
                self.error_recovery.record_error(
                    "vent_control",
                    EntityUnavailableError(f"Thermostat {main_thermostat}"),
                )
                return

            thermo_state = self.hass.states.get(main_thermostat)
            mode = thermo_state.state if thermo_state else "off"
            action = get_safe_attribute(self.hass, main_thermostat, "hvac_action", "idle")

            selected_list = self._parse_rooms_csv(rooms_csv)
            rooms_data = self._collect_rooms_data(coordinator)
            all_vents = self._collect_all_vents()

            if not all_vents:
                _LOGGER.warning("No vent entities configured.")
                return

            strategy = self.entry.options.get("control_strategy", DEFAULT_CONTROL_STRATEGY)
            granularity = safe_int(
                self.entry.options.get("vent_granularity", DEFAULT_VENT_GRANULARITY),
                DEFAULT_VENT_GRANULARITY, 1, 100,
            )
            min_adj_pct = safe_int(
                self.entry.options.get("min_adjustment_pct", DEFAULT_MIN_ADJUSTMENT_PCT),
                DEFAULT_MIN_ADJUSTMENT_PCT, 0, 100,
            )
            min_adj_interval = safe_int(
                self.entry.options.get(
                    "min_adjustment_interval_min", DEFAULT_MIN_ADJUSTMENT_INTERVAL_MIN
                ),
                DEFAULT_MIN_ADJUSTMENT_INTERVAL_MIN, 0, 120,
            )
            temp_error_override = safe_float(
                self.entry.options.get(
                    "temp_error_override_f", DEFAULT_TEMP_ERROR_OVERRIDE_F
                ),
                DEFAULT_TEMP_ERROR_OVERRIDE_F, 0.0, 10.0,
            )
            conv_vents = safe_int(
                self.entry.options.get(
                    "conventional_vent_count", DEFAULT_CONVENTIONAL_VENT_COUNT
                ),
                DEFAULT_CONVENTIONAL_VENT_COUNT, 0, 30,
            )
            min_open = safe_int(
                self.entry.options.get("min_other_room_open_pct", 20), 20, 0, 100
            )
            initial_eff = safe_float(
                self.entry.options.get("initial_efficiency", DEFAULT_INITIAL_EFFICIENCY),
                DEFAULT_INITIAL_EFFICIENCY, 1, 100,
            )

            if debug:
                _LOGGER.info(
                    "Vent control: mode=%s action=%s strategy=%s selected=%s",
                    mode, action, strategy, ",".join(selected_list),
                )

            # Build per-room algorithm inputs
            hvac_mode = action if action in ("heating", "cooling") else mode
            setpoint = self._resolve_setpoint(main_thermostat, hvac_mode)

            use_learned = strategy in ("learned", "hybrid") and coordinator is not None
            algo_rooms: list[dict] = []
            for rd in rooms_data:
                rate = 0.0
                if use_learned and coordinator:
                    rate = coordinator.store.get_effective_rate(rd["key"], hvac_mode)
                if rate <= 0:
                    rate = initial_eff / 100.0 * 0.05

                algo_rooms.append({
                    "key": rd["key"],
                    "temp": rd.get("current_temp"),
                    "rate": rate,
                    "active": True,
                    "delta": rd.get("delta", 0),
                    "occupied": rd.get("occupied", False),
                    "priority": rd.get("priority", 5),
                })

            # Compute targets
            if strategy == "simple" or setpoint is None:
                targets = compute_simple_targets(
                    rooms_data, selected_list, mode, action, min_open
                )
                for key in selected_list:
                    targets[key] = 100.0
            else:
                longest_time = calculate_longest_time_to_target(
                    algo_rooms, hvac_mode, setpoint,
                    max_running_minutes=coordinator.store.max_running_minutes if coordinator else 60.0,
                )
                if longest_time <= 0:
                    longest_time = 30.0

                targets = calculate_all_vent_targets(
                    algo_rooms, hvac_mode, setpoint, longest_time,
                    strategy=strategy,
                )
                for key in selected_list:
                    targets[key] = max(targets.get(key, 0), 80.0)

            # Enforce minimum open for non-selected rooms
            for rd in rooms_data:
                key = rd["key"]
                if key not in selected_list:
                    targets[key] = max(targets.get(key, 0), float(min_open))

            # Minimum airflow adjustment
            targets = adjust_for_minimum_airflow(
                targets, algo_rooms, hvac_mode, conv_vents
            )

            # Round to granularity
            final_targets: dict[str, int] = {}
            for key, pct in targets.items():
                final_targets[key] = round_to_granularity(pct, granularity)

            # Apply to vents with throttling
            now_ts = datetime.now().timestamp()
            async with ServiceCallBatcher(self.hass, batch_size=10) as batcher:
                for rd in rooms_data:
                    key = rd["key"]
                    target_pos = final_targets.get(key, min_open)
                    for vent_entity in rd.get("vent_entities", []):
                        if not validate_entity_state(self.hass, vent_entity, "cover"):
                            continue
                        if not validate_vent_position(target_pos):
                            continue

                        current_pos = safe_int(
                            get_safe_attribute(
                                self.hass, vent_entity, "current_position", target_pos
                            ),
                            target_pos, 0, 100,
                        )
                        move = abs(current_pos - target_pos)

                        temp_error = abs(rd.get("delta", 0))
                        force = temp_error >= temp_error_override

                        if not force and move < min_adj_pct:
                            continue

                        if not force and coordinator:
                            last_adj = coordinator.store.get_vent_last_adjusted(vent_entity)
                            if last_adj > 0:
                                elapsed_min = (now_ts - last_adj) / 60.0
                                if elapsed_min < min_adj_interval:
                                    continue

                        await batcher.add_call(
                            "cover",
                            "set_cover_position",
                            {"entity_id": vent_entity, "position": target_pos},
                        )
                        if coordinator:
                            coordinator.store.set_vent_last_adjusted(vent_entity, now_ts)

                        if debug:
                            _LOGGER.info(
                                "Vent %s: %d%% -> %d%%", vent_entity, current_pos, target_pos
                            )

            self.error_recovery.reset_errors("vent_control")

        except Exception as exc:
            _LOGGER.error("Error in vent control: %s", exc, exc_info=True)
            self.error_recovery.record_error("vent_control", exc)
            raise

    # -- helpers ------------------------------------------------------------

    def _parse_rooms_csv(self, csv: str) -> list[str]:
        if not csv or csv.strip() in ("", "none"):
            return []
        rooms = self.entry.data.get("rooms", [])
        valid = {r.get("name", "").lower().replace(" ", "_") for r in rooms}
        return [p.strip() for p in csv.split(",") if p.strip() in valid]

    def _collect_rooms_data(self, coordinator) -> list[dict]:
        rooms_config = self.entry.data.get("rooms", [])
        result: list[dict] = []
        for rc in rooms_config:
            key = rc.get("name", "").lower().replace(" ", "_")
            climate = rc.get("climate_entity")
            temp_sensor = rc.get("temp_sensor", "")
            occ_sensor = rc.get("occupancy_sensor", "")
            vents = rc.get("vent_entities", [])
            priority = rc.get("priority", 5)

            current = None
            if temp_sensor and validate_entity_state(self.hass, temp_sensor, "sensor"):
                v = get_safe_state(self.hass, temp_sensor)
                if v:
                    current = safe_float(v, min_val=40.0, max_val=100.0) or None
            if current is None and climate and validate_entity_state(self.hass, climate, "climate"):
                t = get_safe_attribute(self.hass, climate, "current_temperature")
                if t is not None:
                    current = safe_float(t, min_val=40.0, max_val=100.0) or None

            target = None
            if climate and validate_entity_state(self.hass, climate, "climate"):
                t = get_safe_attribute(self.hass, climate, "temperature")
                if t is not None:
                    target = safe_float(t, min_val=40.0, max_val=100.0) or None
                else:
                    lo = get_safe_attribute(self.hass, climate, "target_temp_low")
                    hi = get_safe_attribute(self.hass, climate, "target_temp_high")
                    if lo is not None and hi is not None:
                        lo_f = safe_float(lo, min_val=40.0, max_val=100.0)
                        hi_f = safe_float(hi, min_val=40.0, max_val=100.0)
                        if lo_f and hi_f:
                            target = (lo_f + hi_f) / 2

            delta = (target - current) if target and current else 0.0
            occupied = False
            if occ_sensor and validate_entity_state(self.hass, occ_sensor, "binary_sensor"):
                occupied = get_safe_state(self.hass, occ_sensor) == "on"

            result.append({
                "key": key,
                "name": rc.get("name", ""),
                "climate_entity": climate,
                "temp_sensor": temp_sensor,
                "occ_sensor": occ_sensor,
                "vent_entities": vents,
                "priority": priority,
                "current_temp": current,
                "target_temp": target,
                "delta": delta,
                "occupied": occupied,
            })
        return result

    def _collect_all_vents(self) -> list[str]:
        vents: set[str] = set()
        for rc in self.entry.data.get("rooms", []):
            vents.update(rc.get("vent_entities", []))
        return list(vents)

    def _resolve_setpoint(self, thermostat_id: str, hvac_mode: str) -> float | None:
        state = self.hass.states.get(thermostat_id)
        if not state:
            return None
        if hvac_mode in ("cool", "cooling"):
            hi = state.attributes.get("target_temp_high")
            if hi is not None:
                try:
                    return float(hi)
                except (ValueError, TypeError):
                    pass
        elif hvac_mode in ("heat", "heating"):
            lo = state.attributes.get("target_temp_low")
            if lo is not None:
                try:
                    return float(lo)
                except (ValueError, TypeError):
                    pass
        temp = state.attributes.get("temperature")
        if temp is not None:
            try:
                return float(temp)
            except (ValueError, TypeError):
                pass
        return None


class ThermostatControlScript:
    """Controls the main thermostat setpoint based on selected room targets.

    Uses the coordinator store instead of input_number entities.
    """

    def __init__(self, hass: HomeAssistant, entry) -> None:
        self.hass = hass
        self.entry = entry
        self.error_recovery = ErrorRecovery(hass, entry)

    async def async_run(self, rooms_csv: str = "") -> None:
        try:
            if not self.entry.options.get("auto_thermostat_control", True):
                return
            if self.error_recovery.should_disable_component("thermostat_control"):
                _LOGGER.error("Thermostat control disabled due to repeated errors.")
                return

            coordinator: SmartVentControllerCoordinator | None = self.hass.data.get(
                DOMAIN, {}
            ).get(self.entry.entry_id)

            if await self._check_manual_override(coordinator):
                if self.entry.options.get("debug_mode", False):
                    _LOGGER.info("Manual override detected. Skipping.")
                return

            if self._check_cycle_protection(coordinator):
                if self.entry.options.get("debug_mode", False):
                    _LOGGER.info("BLOCKED by cycle protection")
                return

            selected_list = self._parse_rooms_csv(rooms_csv)
            main_thermostat = self.entry.data.get("main_thermostat")
            if not validate_entity_state(self.hass, main_thermostat, "climate"):
                _LOGGER.error("Thermostat %s unavailable", main_thermostat)
                self.error_recovery.record_error(
                    "thermostat_control",
                    EntityUnavailableError(f"Thermostat {main_thermostat}"),
                )
                return

            thermo = self.hass.states.get(main_thermostat)
            mode = thermo.state if thermo else "off"
            action = get_safe_attribute(self.hass, main_thermostat, "hvac_action", "idle")
            debug = self.entry.options.get("debug_mode", False)

            if not selected_list:
                default_temp = safe_int(
                    self.entry.options.get("default_thermostat_temp", 72), 72, 65, 80
                )
                if debug:
                    _LOGGER.info("No rooms selected. Setting default %d°F", default_temp)
                ok = await safe_service_call(
                    self.hass, "climate", "set_temperature",
                    {"entity_id": main_thermostat, "temperature": default_temp},
                    max_retries=2,
                )
                if ok and coordinator:
                    coordinator.store.last_thermostat_setpoint = float(default_temp)
                    await coordinator.store.async_save()
                elif not ok:
                    self.error_recovery.record_error(
                        "thermostat_control", ServiceCallError("set default temp")
                    )
                return

            room_targets = self._gather_room_targets(selected_list)
            if not room_targets:
                _LOGGER.warning("No valid room targets found.")
                return

            new_setpoint = None

            if mode == "heat" or action == "heating":
                heat_target = max(room_targets)
                boost_on = self.entry.options.get("heat_boost_enabled", True)
                boost = (
                    safe_float(self.entry.options.get("heat_boost_f", 0.0), 0.0, 0.0, 3.0)
                    if boost_on else 0.0
                )
                new_setpoint = safe_float(heat_target + boost, min_val=40.0, max_val=100.0)
                ok = await safe_service_call(
                    self.hass, "climate", "set_temperature",
                    {"entity_id": main_thermostat, "temperature": new_setpoint},
                    max_retries=2,
                )
            elif mode == "cool" or action == "cooling":
                new_setpoint = safe_float(min(room_targets), min_val=40.0, max_val=100.0)
                ok = await safe_service_call(
                    self.hass, "climate", "set_temperature",
                    {"entity_id": main_thermostat, "temperature": new_setpoint},
                    max_retries=2,
                )
            elif mode in ("auto", "heat_cool"):
                heat_target = max(room_targets)
                cool_target = min(room_targets)
                boost_on = self.entry.options.get("heat_boost_enabled", True)
                boost = (
                    safe_float(self.entry.options.get("heat_boost_f", 0.0), 0.0, 0.0, 3.0)
                    if boost_on else 0.0
                )
                lo = safe_float(heat_target + boost, min_val=40.0, max_val=100.0)
                hi = safe_float(cool_target, min_val=40.0, max_val=100.0)
                new_setpoint = (lo + hi) / 2.0
                ok = await safe_service_call(
                    self.hass, "climate", "set_temperature",
                    {
                        "entity_id": main_thermostat,
                        "target_temp_low": lo,
                        "target_temp_high": hi,
                    },
                    max_retries=2,
                )
            else:
                ok = True

            if ok and new_setpoint is not None and coordinator:
                coordinator.store.last_thermostat_setpoint = new_setpoint
                await coordinator.store.async_save()
            elif not ok:
                self.error_recovery.record_error(
                    "thermostat_control", ServiceCallError("set temperature failed")
                )

            self.error_recovery.reset_errors("thermostat_control")

        except Exception as exc:
            _LOGGER.error("Error in thermostat control: %s", exc, exc_info=True)
            self.error_recovery.record_error("thermostat_control", exc)
            raise

    # -- helpers ------------------------------------------------------------

    def _parse_rooms_csv(self, csv: str) -> list[str]:
        if not csv or csv.strip() in ("", "none"):
            return []
        rooms = self.entry.data.get("rooms", [])
        valid = {r.get("name", "").lower().replace(" ", "_") for r in rooms}
        return [p.strip() for p in csv.split(",") if p.strip() in valid]

    async def _check_manual_override(self, coordinator) -> bool:
        main = self.entry.data.get("main_thermostat")
        thermo = self.hass.states.get(main)
        if not thermo:
            return False
        current = thermo.attributes.get("temperature")
        if current is None:
            return False
        last = coordinator.store.last_thermostat_setpoint if coordinator else 0
        if last <= 0:
            return False
        try:
            return abs(float(current) - last) > 0.5
        except (ValueError, TypeError):
            return False

    def _check_cycle_protection(self, coordinator) -> bool:
        main = self.entry.data.get("main_thermostat")
        thermo = self.hass.states.get(main)
        if not thermo:
            return False
        action = thermo.attributes.get("hvac_action", "idle")
        min_runtime = self.entry.options.get("hvac_min_runtime_min", 10) * 60
        min_off = self.entry.options.get("hvac_min_off_time_min", 5) * 60

        if coordinator is None:
            return False
        now = datetime.now().timestamp()

        if action in ("heating", "cooling"):
            start = coordinator.store.cycle_start_ts
            if start > 0 and (now - start) < min_runtime:
                return True
        elif action == "idle":
            end = coordinator.store.cycle_end_ts
            if end > 0 and (now - end) < min_off:
                return True
        return False

    def _gather_room_targets(self, selected_keys: list[str]) -> list[float]:
        targets: list[float] = []
        for rc in self.entry.data.get("rooms", []):
            key = rc.get("name", "").lower().replace(" ", "_")
            if key not in selected_keys:
                continue
            climate = rc.get("climate_entity")
            if not climate or not validate_entity_state(self.hass, climate, "climate"):
                continue
            t = get_safe_attribute(self.hass, climate, "temperature")
            if t is not None:
                v = safe_float(t, min_val=40.0, max_val=100.0)
                if v:
                    targets.append(v)
            else:
                lo = get_safe_attribute(self.hass, climate, "target_temp_low")
                hi = get_safe_attribute(self.hass, climate, "target_temp_high")
                if lo is not None and hi is not None:
                    lf = safe_float(lo, min_val=40.0, max_val=100.0)
                    hf = safe_float(hi, min_val=40.0, max_val=100.0)
                    if lf and hf:
                        targets.append((lf + hf) / 2)
        return targets
