"""Smart Vent Controller integration for Home Assistant."""

import json
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform

from .const import DOMAIN
from .coordinator import SmartVentControllerCoordinator
from . import script, automation
from .device import async_create_room_devices, async_remove_room_devices

_LOGGER = logging.getLogger(__name__)

async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry
):
    """Return diagnostics for a config entry."""
    from .diagnostics import async_get_config_entry_diagnostics as get_diagnostics
    return await get_diagnostics(hass, config_entry)

PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Smart Vent Controller from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    coordinator = SmartVentControllerCoordinator(hass, entry)
    await coordinator.async_initialize()
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    try:
        await async_create_room_devices(hass, entry)
    except Exception as exc:
        _LOGGER.warning("Could not create room devices: %s", exc)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await script.async_setup_entry(hass, entry)
    await automation.async_setup_entry(hass, entry)
    await _async_register_services(hass, entry)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Smart Vent Controller entry."""
    try:
        await async_remove_room_devices(hass, entry)
    except Exception as exc:
        _LOGGER.warning("Could not remove room devices: %s", exc)

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    await automation.async_unload_entry(hass, entry)

    if unload_ok:
        coordinator = hass.data[DOMAIN].pop(entry.entry_id, None)
        if coordinator:
            await coordinator.store.async_save()

    return unload_ok


async def _async_register_services(hass: HomeAssistant, entry: ConfigEntry):
    """Register custom services."""

    async def set_room_priority(call):
        room = call.data.get("room")
        priority = call.data.get("priority")
        rooms = list(entry.data.get("rooms", []))
        for i, rc in enumerate(rooms):
            key = rc.get("name", "").lower().replace(" ", "_")
            if key == room.lower().replace(" ", "_"):
                rooms[i] = {**rc, "priority": priority}
                break
        data = dict(entry.data)
        data["rooms"] = rooms
        hass.config_entries.async_update_entry(entry, data=data)

    async def override_room(call):
        room = call.data.get("room", "")
        enabled = call.data.get("enabled", True)
        duration = call.data.get("duration_min", 60)
        coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
        if coordinator is None:
            _LOGGER.error("Coordinator not found for override_room")
            return
        room_key = room.lower().replace(" ", "_")
        coordinator.set_room_override(room_key, enabled, duration)
        await coordinator.store.async_save()
        _LOGGER.info(
            "Room override %s for %s (%d min)",
            "enabled" if enabled else "disabled", room_key, duration,
        )

    async def reset_to_defaults(call):
        from .const import (
            DEFAULT_MIN_OTHER_ROOM_OPEN_PCT,
            DEFAULT_CLOSED_THRESHOLD_PCT,
            DEFAULT_RELIEF_OPEN_PCT,
            DEFAULT_MAX_RELIEF_ROOMS,
            DEFAULT_ROOM_HYSTERESIS_F,
            DEFAULT_OCCUPANCY_LINGER_MIN,
            DEFAULT_OCCUPANCY_LINGER_NIGHT_MIN,
            DEFAULT_HEAT_BOOST_F,
            DEFAULT_HVAC_MIN_RUNTIME_MIN,
            DEFAULT_HVAC_MIN_OFF_TIME_MIN,
            DEFAULT_DEFAULT_THERMOSTAT_TEMP,
            DEFAULT_VENT_GRANULARITY,
            DEFAULT_MIN_ADJUSTMENT_PCT,
            DEFAULT_MIN_ADJUSTMENT_INTERVAL_MIN,
            DEFAULT_TEMP_ERROR_OVERRIDE_F,
            DEFAULT_CONVENTIONAL_VENT_COUNT,
            DEFAULT_CONTROL_STRATEGY,
            DEFAULT_POLL_INTERVAL_ACTIVE_SEC,
            DEFAULT_POLL_INTERVAL_IDLE_SEC,
        )
        options = {
            "min_other_room_open_pct": DEFAULT_MIN_OTHER_ROOM_OPEN_PCT,
            "closed_threshold_pct": DEFAULT_CLOSED_THRESHOLD_PCT,
            "relief_open_pct": DEFAULT_RELIEF_OPEN_PCT,
            "max_relief_rooms": DEFAULT_MAX_RELIEF_ROOMS,
            "room_hysteresis_f": DEFAULT_ROOM_HYSTERESIS_F,
            "occupancy_linger_min": DEFAULT_OCCUPANCY_LINGER_MIN,
            "occupancy_linger_night_min": DEFAULT_OCCUPANCY_LINGER_NIGHT_MIN,
            "heat_boost_f": DEFAULT_HEAT_BOOST_F,
            "hvac_min_runtime_min": DEFAULT_HVAC_MIN_RUNTIME_MIN,
            "hvac_min_off_time_min": DEFAULT_HVAC_MIN_OFF_TIME_MIN,
            "default_thermostat_temp": DEFAULT_DEFAULT_THERMOSTAT_TEMP,
            "automation_cooldown_sec": 30,
            "require_occupancy": True,
            "heat_boost_enabled": True,
            "auto_thermostat_control": True,
            "auto_vent_control": True,
            "debug_mode": False,
            "vent_granularity": DEFAULT_VENT_GRANULARITY,
            "min_adjustment_pct": DEFAULT_MIN_ADJUSTMENT_PCT,
            "min_adjustment_interval_min": DEFAULT_MIN_ADJUSTMENT_INTERVAL_MIN,
            "temp_error_override_f": DEFAULT_TEMP_ERROR_OVERRIDE_F,
            "conventional_vent_count": DEFAULT_CONVENTIONAL_VENT_COUNT,
            "control_strategy": DEFAULT_CONTROL_STRATEGY,
            "poll_interval_active_sec": DEFAULT_POLL_INTERVAL_ACTIVE_SEC,
            "poll_interval_idle_sec": DEFAULT_POLL_INTERVAL_IDLE_SEC,
        }
        hass.config_entries.async_update_entry(entry, options=options)
        _LOGGER.info("Smart Vent Controller options reset to defaults")

    async def export_efficiency(call):
        coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
        if coordinator is None:
            return
        data = coordinator.store.export_efficiency()
        path = call.data.get("path", "")
        if path:
            config_dir = hass.config.path()
            full = f"{config_dir}/{path}"
            with open(full, "w") as f:
                json.dump(data, f, indent=2)
            _LOGGER.info("Efficiency data exported to %s", full)
        else:
            _LOGGER.info("Efficiency data: %s", json.dumps(data))

    async def import_efficiency(call):
        coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
        if coordinator is None:
            return
        payload = call.data.get("payload")
        path = call.data.get("path", "")
        if path:
            config_dir = hass.config.path()
            full = f"{config_dir}/{path}"
            with open(full) as f:
                payload = json.load(f)
        if payload:
            coordinator.store.import_efficiency(payload)
            await coordinator.store.async_save()
            _LOGGER.info("Efficiency data imported")

    hass.services.async_register(DOMAIN, "set_room_priority", set_room_priority)
    hass.services.async_register(DOMAIN, "override_room", override_room)
    hass.services.async_register(DOMAIN, "reset_to_defaults", reset_to_defaults)
    hass.services.async_register(DOMAIN, "export_efficiency", export_efficiency)
    hass.services.async_register(DOMAIN, "import_efficiency", import_efficiency)
