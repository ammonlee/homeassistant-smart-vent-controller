"""Climate platform for Smart Vent Controller.

Creates a per-room climate entity with an independent target temperature.
The HVAC mode mirrors the main thermostat; the setpoint is managed by
the integration and persisted in the coordinator store.
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, DEFAULT_DEFAULT_THERMOSTAT_TEMP
from .coordinator import SmartVentControllerCoordinator
from .device import get_room_device_id
from .error_handling import get_safe_attribute

_LOGGER = logging.getLogger(__name__)

_MODE_MAP = {
    "heat": HVACMode.HEAT,
    "cool": HVACMode.COOL,
    "heat_cool": HVACMode.HEAT_COOL,
    "auto": HVACMode.AUTO,
    "off": HVACMode.OFF,
}

_ACTION_MAP = {
    "heating": HVACAction.HEATING,
    "cooling": HVACAction.COOLING,
    "idle": HVACAction.IDLE,
    "off": HVACAction.OFF,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up per-room climate entities."""
    coordinator: SmartVentControllerCoordinator = hass.data[DOMAIN][entry.entry_id]
    rooms = entry.data.get("rooms", [])
    default_temp = entry.options.get("default_thermostat_temp", DEFAULT_DEFAULT_THERMOSTAT_TEMP)

    entities: list[ClimateEntity] = []
    for room in rooms:
        room_name = room.get("name", "")
        room_key = room_name.lower().replace(" ", "_")
        entities.append(
            RoomClimateEntity(
                coordinator,
                entry,
                room_key,
                room_name,
                room.get("climate_entity", ""),
                room.get("temp_sensor", ""),
                default_temp,
            )
        )

    async_add_entities(entities)


class RoomClimateEntity(ClimateEntity):
    """Per-room climate entity with an independent target temperature."""

    _attr_has_entity_name = False
    _attr_temperature_unit = UnitOfTemperature.FAHRENHEIT
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_min_temp = 50
    _attr_max_temp = 90
    _attr_target_temperature_step = 1

    def __init__(
        self,
        coordinator: SmartVentControllerCoordinator,
        entry: ConfigEntry,
        room_key: str,
        room_name: str,
        climate_entity: str,
        temp_sensor: str,
        default_temp: float,
    ) -> None:
        self.coordinator = coordinator
        self._entry = entry
        self._room_key = room_key
        self._room_name = room_name
        self._climate_entity = climate_entity
        self._temp_sensor = temp_sensor
        self._default_temp = default_temp

        self._attr_unique_id = f"{entry.entry_id}_{room_key}_climate"
        self._attr_name = f"{room_name}"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={get_room_device_id(self._entry, self._room_key)},
            name=f"{self._room_name} Zone",
            manufacturer="Smart Vent Controller",
            model="Room Controller",
        )

    # -- HVAC mode (mirrors main thermostat, read-only) --------------------

    @property
    def hvac_modes(self) -> list[HVACMode]:
        return [HVACMode.HEAT, HVACMode.COOL, HVACMode.HEAT_COOL, HVACMode.AUTO, HVACMode.OFF]

    @property
    def hvac_mode(self) -> HVACMode:
        main = self._entry.data.get("main_thermostat", "")
        state = self.coordinator.hass.states.get(main)
        if state:
            return _MODE_MAP.get(state.state, HVACMode.OFF)
        return HVACMode.OFF

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Mode is determined by the main thermostat; ignore per-room changes."""
        pass

    @property
    def hvac_action(self) -> HVACAction | None:
        main = self._entry.data.get("main_thermostat", "")
        action = get_safe_attribute(
            self.coordinator.hass, main, "hvac_action", "idle"
        )
        return _ACTION_MAP.get(action, HVACAction.IDLE)

    # -- Temperature -------------------------------------------------------

    @property
    def current_temperature(self) -> float | None:
        if self._temp_sensor:
            state = self.coordinator.hass.states.get(self._temp_sensor)
            if state and state.state not in ("unknown", "unavailable", "None", "none"):
                try:
                    return float(state.state)
                except (ValueError, TypeError):
                    pass
        if self._climate_entity:
            climate = self.coordinator.hass.states.get(self._climate_entity)
            if climate:
                temp = climate.attributes.get("current_temperature")
                if temp is not None:
                    try:
                        return float(temp)
                    except (ValueError, TypeError):
                        pass
        return None

    @property
    def target_temperature(self) -> float | None:
        stored = self.coordinator.store.get_room_setpoint(self._room_key)
        if stored is not None:
            return stored
        # Fall back to external climate entity setpoint
        if self._climate_entity:
            climate = self.coordinator.hass.states.get(self._climate_entity)
            if climate:
                temp = climate.attributes.get("temperature")
                if temp is not None:
                    try:
                        return float(temp)
                    except (ValueError, TypeError):
                        pass
        return self._default_temp

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is None:
            return
        self.coordinator.store.set_room_setpoint(self._room_key, float(temp))
        await self.coordinator.store.async_save()
        self.async_write_ha_state()

    # -- Coordinator updates -----------------------------------------------

    @property
    def should_poll(self) -> bool:
        return True

    async def async_update(self) -> None:
        """Refresh state from coordinator on poll."""
        pass
