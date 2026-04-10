"""Data coordinator for Smart Vent Controller.

Manages polling, efficiency learning, cycle tracking, and persistent state.
All runtime state that was previously spread across input_number entities
now lives here and is persisted via SmartVentStore.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    DEFAULT_POLL_INTERVAL_ACTIVE_SEC,
    DEFAULT_POLL_INTERVAL_IDLE_SEC,
    DEFAULT_INITIAL_EFFICIENCY,
)
from .cache import RoomDataCache, EntityStateCache
from .store import SmartVentStore
from .algorithm import compute_efficiency_sample

_LOGGER = logging.getLogger(__name__)


class SmartVentControllerCoordinator(DataUpdateCoordinator):
    """Coordinator that owns all runtime state for one config entry."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._active_interval = timedelta(
            seconds=entry.options.get(
                "poll_interval_active_sec", DEFAULT_POLL_INTERVAL_ACTIVE_SEC
            )
        )
        self._idle_interval = timedelta(
            seconds=entry.options.get(
                "poll_interval_idle_sec", DEFAULT_POLL_INTERVAL_IDLE_SEC
            )
        )
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=self._idle_interval,
        )
        self.config_entry = entry
        self.rooms = entry.data.get("rooms", [])

        self.room_cache = RoomDataCache(ttl_seconds=5)
        self.entity_cache = EntityStateCache(ttl_seconds=2)

        self.store = SmartVentStore(hass, entry.entry_id)

        self.automations: list[Any] = []

        self._is_hvac_active = False

    async def async_initialize(self) -> None:
        """Load persisted state from disk. Call once during entry setup."""
        await self.store.async_load()

    # -- polling interval management ----------------------------------------

    def _update_polling_interval(self, active: bool) -> None:
        new_interval = self._active_interval if active else self._idle_interval
        if self.update_interval != new_interval:
            self.update_interval = new_interval
            _LOGGER.debug("Polling interval changed to %s", new_interval)

    # -- main update --------------------------------------------------------

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            data: dict[str, Any] = {}
            main_thermostat = self.config_entry.data.get("main_thermostat")

            hvac_active = False
            if main_thermostat:
                thermo = self.hass.states.get(main_thermostat)
                if thermo:
                    action = thermo.attributes.get("hvac_action", "idle")
                    hvac_active = action in ("heating", "cooling")
                    data["hvac_action"] = action
                    data["hvac_mode"] = thermo.state

            was_active = self._is_hvac_active
            self._is_hvac_active = hvac_active
            self._update_polling_interval(hvac_active)

            if hvac_active and not was_active:
                await self._handle_cycle_start(data.get("hvac_action", "idle"))
            elif not hvac_active and was_active:
                await self._handle_cycle_end()

            for room in self.rooms:
                room_name = room.get("name", "").lower().replace(" ", "_")
                temp_sensor = room.get("temp_sensor")
                climate_entity = room.get("climate_entity")

                current_temp = None
                if temp_sensor:
                    state = self.hass.states.get(temp_sensor)
                    if state and state.state not in (
                        "unknown", "unavailable", "None", "none"
                    ):
                        try:
                            current_temp = float(state.state)
                        except (ValueError, TypeError):
                            pass

                if current_temp is None and climate_entity:
                    climate = self.hass.states.get(climate_entity)
                    if climate:
                        temp = climate.attributes.get("current_temperature")
                        if temp is not None:
                            try:
                                current_temp = float(temp)
                            except (ValueError, TypeError):
                                pass

                data[f"{room_name}_temp"] = current_temp

                vent_entities = room.get("vent_entities", [])
                positions = []
                for vent in vent_entities:
                    vent_state = self.hass.states.get(vent)
                    if vent_state:
                        pos = vent_state.attributes.get("current_position", 0)
                        try:
                            positions.append(float(pos))
                        except (ValueError, TypeError):
                            pass
                data[f"{room_name}_vent_avg"] = (
                    sum(positions) / len(positions) if positions else 0
                )

                occ_sensor = room.get("occupancy_sensor")
                if occ_sensor:
                    occ_state = self.hass.states.get(occ_sensor)
                    data[f"{room_name}_occupied"] = (
                        occ_state.state == "on" if occ_state else False
                    )

            return data

        except Exception as err:
            raise UpdateFailed(
                f"Error updating Smart Vent Controller: {err}"
            ) from err

    # -- HVAC cycle tracking ------------------------------------------------

    async def _handle_cycle_start(self, action: str) -> None:
        now = datetime.now().timestamp()
        self.store.cycle_start_ts = now
        self.store.hvac_last_action = action

        for room in self.rooms:
            room_key = room.get("name", "").lower().replace(" ", "_")
            temp_sensor = room.get("temp_sensor")
            climate_entity = room.get("climate_entity")

            temp = None
            if temp_sensor:
                state = self.hass.states.get(temp_sensor)
                if state and state.state not in ("unknown", "unavailable"):
                    try:
                        temp = float(state.state)
                    except (ValueError, TypeError):
                        pass
            if temp is None and climate_entity:
                climate = self.hass.states.get(climate_entity)
                if climate:
                    ct = climate.attributes.get("current_temperature")
                    if ct is not None:
                        try:
                            temp = float(ct)
                        except (ValueError, TypeError):
                            pass
            if temp is not None:
                self.store.set_cycle_start_temp(room_key, temp)

        await self.store.async_save()
        _LOGGER.debug("HVAC cycle started: %s at %.0f", action, now)

    async def _handle_cycle_end(self) -> None:
        now = datetime.now().timestamp()
        self.store.cycle_end_ts = now

        start_ts = self.store.cycle_start_ts
        if start_ts > 0:
            minutes = (now - start_ts) / 60.0
            if minutes > self.store.max_running_minutes:
                self.store.max_running_minutes = minutes

            hvac_mode = self.store.hvac_last_action
            await self._learn_efficiency(minutes, hvac_mode)

        self.store.clear_cycle_start_temps()
        self.store.clear_cycle_avg_apertures()
        await self.store.async_save()
        _LOGGER.debug("HVAC cycle ended at %.0f", now)

    # -- efficiency learning ------------------------------------------------

    async def _learn_efficiency(self, minutes: float, hvac_mode: str) -> None:
        """Compute and store per-room efficiency from the cycle that just ended."""
        for room in self.rooms:
            room_key = room.get("name", "").lower().replace(" ", "_")

            start_temp = self.store.get_cycle_start_temp(room_key)
            if start_temp is None:
                continue

            current_temp = self._get_room_temp(room)
            if current_temp is None:
                continue

            avg_aperture = self.store.get_cycle_avg_aperture(room_key)
            if avg_aperture <= 0:
                vent_entities = room.get("vent_entities", [])
                positions = []
                for vent in vent_entities:
                    vs = self.hass.states.get(vent)
                    if vs:
                        try:
                            positions.append(
                                float(vs.attributes.get("current_position", 0))
                            )
                        except (ValueError, TypeError):
                            pass
                avg_aperture = sum(positions) / len(positions) if positions else 0

            rate = compute_efficiency_sample(
                start_temp, current_temp, minutes, avg_aperture, hvac_mode
            )
            if rate is None:
                continue

            old_rate = self.store.get_effective_rate(room_key, hvac_mode)
            if old_rate > 0:
                blended = old_rate * 0.7 + rate * 0.3
            else:
                blended = rate

            if hvac_mode in ("cool", "cooling"):
                self.store.set_cooling_rate(room_key, blended)
            else:
                self.store.set_heating_rate(room_key, blended)

            _LOGGER.info(
                "Learned %s rate for %s: %.4f (was %.4f)",
                hvac_mode, room_key, blended, old_rate,
            )

    # -- helpers ------------------------------------------------------------

    def _get_room_temp(self, room_config: dict) -> float | None:
        temp_sensor = room_config.get("temp_sensor")
        climate_entity = room_config.get("climate_entity")

        if temp_sensor:
            state = self.hass.states.get(temp_sensor)
            if state and state.state not in ("unknown", "unavailable"):
                try:
                    return float(state.state)
                except (ValueError, TypeError):
                    pass
        if climate_entity:
            climate = self.hass.states.get(climate_entity)
            if climate:
                ct = climate.attributes.get("current_temperature")
                if ct is not None:
                    try:
                        return float(ct)
                    except (ValueError, TypeError):
                        pass
        return None

    def get_rooms_to_condition_value(self) -> str:
        """Compute rooms-to-condition CSV without relying on a sensor entity ID.

        This is the canonical source; the RoomsToConditionSensor reads from here.
        """
        rooms = self.config_entry.data.get("rooms", [])
        main_thermostat = self.config_entry.data.get("main_thermostat")
        hysteresis = self.config_entry.options.get("room_hysteresis_f", 1.0)
        require_occupancy = self.config_entry.options.get("require_occupancy", True)

        if not main_thermostat:
            return "none"

        thermostat = self.hass.states.get(main_thermostat)
        if not thermostat or thermostat.state not in (
            "heat", "cool", "auto", "heat_cool"
        ):
            return "none"

        mode = thermostat.state
        result: list[str] = []

        for room in rooms:
            room_key = room.get("name", "").lower().replace(" ", "_")
            current_temp = self._get_room_temp(room)
            if current_temp is None or current_temp < 40 or current_temp > 100:
                continue

            target_temp = self._get_room_target(room)
            if target_temp is None:
                continue

            delta = target_temp - current_temp

            if require_occupancy:
                occ_sensor = room.get("occupancy_sensor", "")
                if occ_sensor:
                    occ_state = self.hass.states.get(occ_sensor)
                    if not occ_state or occ_state.state != "on":
                        continue

            if mode in ("heat", "auto", "heat_cool") and delta > hysteresis:
                result.append(room_key)
            elif mode in ("cool", "auto", "heat_cool") and delta < -hysteresis:
                result.append(room_key)

        return ",".join(result) if result else "none"

    def _get_room_target(self, room_config: dict) -> float | None:
        climate_entity = room_config.get("climate_entity")
        if not climate_entity:
            return None
        climate = self.hass.states.get(climate_entity)
        if not climate:
            return None
        temp = climate.attributes.get("temperature")
        if temp is not None:
            try:
                return float(temp)
            except (ValueError, TypeError):
                pass
        lo = climate.attributes.get("target_temp_low")
        hi = climate.attributes.get("target_temp_high")
        if lo is not None and hi is not None:
            try:
                return (float(lo) + float(hi)) / 2
            except (ValueError, TypeError):
                pass
        return None

    # -- override room support ----------------------------------------------

    def set_room_override(
        self, room_key: str, enabled: bool, duration_min: int = 60
    ) -> None:
        """Override (or clear) a room's conditioning for *duration_min* minutes."""
        overrides: dict = self.store._data.setdefault("room_overrides", {})
        if enabled:
            overrides[room_key] = {
                "until": datetime.now().timestamp() + duration_min * 60,
            }
        else:
            overrides.pop(room_key, None)

    def is_room_overridden(self, room_key: str) -> bool:
        overrides: dict = self.store._data.get("room_overrides", {})
        info = overrides.get(room_key)
        if not info:
            return False
        if datetime.now().timestamp() > info.get("until", 0):
            overrides.pop(room_key, None)
            return False
        return True
