"""Persistent state storage for Smart Vent Controller.

Replaces the fragile input_number / input_boolean helper approach with a
single JSON file managed via ``homeassistant.helpers.storage.Store``.
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN, STORAGE_VERSION

_LOGGER = logging.getLogger(__name__)


class SmartVentStore:
    """Persistent store for cycle timestamps, learned rates, and runtime data."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store = Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry_id}")
        self._data: dict[str, Any] = {}

    # -- lifecycle ----------------------------------------------------------

    async def async_load(self) -> None:
        stored = await self._store.async_load()
        if stored and isinstance(stored, dict):
            self._data = stored
        else:
            self._data = {}

    async def async_save(self) -> None:
        await self._store.async_save(self._data)

    # -- cycle timestamps ---------------------------------------------------

    @property
    def cycle_start_ts(self) -> float:
        return float(self._data.get("cycle_start_ts", 0))

    @cycle_start_ts.setter
    def cycle_start_ts(self, value: float) -> None:
        self._data["cycle_start_ts"] = value

    @property
    def cycle_end_ts(self) -> float:
        return float(self._data.get("cycle_end_ts", 0))

    @cycle_end_ts.setter
    def cycle_end_ts(self, value: float) -> None:
        self._data["cycle_end_ts"] = value

    @property
    def last_thermostat_setpoint(self) -> float:
        return float(self._data.get("last_thermostat_setpoint", 0))

    @last_thermostat_setpoint.setter
    def last_thermostat_setpoint(self, value: float) -> None:
        self._data["last_thermostat_setpoint"] = value

    @property
    def hvac_last_action(self) -> str:
        return self._data.get("hvac_last_action", "idle")

    @hvac_last_action.setter
    def hvac_last_action(self, value: str) -> None:
        self._data["hvac_last_action"] = value

    # -- per-room learned efficiency rates ----------------------------------

    def get_heating_rate(self, room_key: str) -> float:
        return float(
            self._data.get("heating_rates", {}).get(room_key, 0)
        )

    def set_heating_rate(self, room_key: str, rate: float) -> None:
        self._data.setdefault("heating_rates", {})[room_key] = rate

    def get_cooling_rate(self, room_key: str) -> float:
        return float(
            self._data.get("cooling_rates", {}).get(room_key, 0)
        )

    def set_cooling_rate(self, room_key: str, rate: float) -> None:
        self._data.setdefault("cooling_rates", {})[room_key] = rate

    def get_effective_rate(self, room_key: str, hvac_mode: str) -> float:
        if hvac_mode in ("cool", "cooling"):
            return self.get_cooling_rate(room_key)
        return self.get_heating_rate(room_key)

    # -- per-room cycle start temperatures ----------------------------------

    def get_cycle_start_temp(self, room_key: str) -> float | None:
        return self._data.get("cycle_start_temps", {}).get(room_key)

    def set_cycle_start_temp(self, room_key: str, temp: float) -> None:
        self._data.setdefault("cycle_start_temps", {})[room_key] = temp

    def clear_cycle_start_temps(self) -> None:
        self._data["cycle_start_temps"] = {}

    # -- per-room cycle start apertures -------------------------------------

    def get_cycle_avg_aperture(self, room_key: str) -> float:
        return float(
            self._data.get("cycle_avg_apertures", {}).get(room_key, 0)
        )

    def set_cycle_avg_aperture(self, room_key: str, aperture: float) -> None:
        self._data.setdefault("cycle_avg_apertures", {})[room_key] = aperture

    def clear_cycle_avg_apertures(self) -> None:
        self._data["cycle_avg_apertures"] = {}

    # -- per-vent last adjustment tracking ----------------------------------

    def get_vent_last_adjusted(self, vent_entity: str) -> float:
        return float(
            self._data.get("vent_last_adjusted", {}).get(vent_entity, 0)
        )

    def set_vent_last_adjusted(self, vent_entity: str, timestamp: float) -> None:
        self._data.setdefault("vent_last_adjusted", {})[vent_entity] = timestamp

    # -- max running minutes (rolling) --------------------------------------

    @property
    def max_running_minutes(self) -> float:
        return float(self._data.get("max_running_minutes", 60.0))

    @max_running_minutes.setter
    def max_running_minutes(self, value: float) -> None:
        self._data["max_running_minutes"] = value

    # -- per-room target setpoints ------------------------------------------

    def get_room_setpoint(self, room_key: str) -> float | None:
        val = self._data.get("room_setpoints", {}).get(room_key)
        return float(val) if val is not None else None

    def set_room_setpoint(self, room_key: str, temp: float) -> None:
        self._data.setdefault("room_setpoints", {})[room_key] = temp

    # -- efficiency export / import -----------------------------------------

    def export_efficiency(self) -> dict[str, Any]:
        return {
            "heating_rates": dict(self._data.get("heating_rates", {})),
            "cooling_rates": dict(self._data.get("cooling_rates", {})),
            "max_running_minutes": self.max_running_minutes,
        }

    def import_efficiency(self, payload: dict[str, Any]) -> None:
        if "heating_rates" in payload:
            self._data["heating_rates"] = dict(payload["heating_rates"])
        if "cooling_rates" in payload:
            self._data["cooling_rates"] = dict(payload["cooling_rates"])
        if "max_running_minutes" in payload:
            self._data["max_running_minutes"] = float(payload["max_running_minutes"])
