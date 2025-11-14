"""Zone Controller integration for Home Assistant."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform

from .const import DOMAIN
from .coordinator import ZoneControllerCoordinator
from . import script, automation
from .helpers import async_setup_helpers
from .device import async_create_room_devices, async_remove_room_devices

_LOGGER = logging.getLogger(__name__)

# Register diagnostics
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
    """Set up Zone Controller from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    # Create coordinator
    coordinator = ZoneControllerCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    
    hass.data[DOMAIN][entry.entry_id] = coordinator
    
    # Set up helper entities automatically (if possible)
    # Note: This attempts to create helpers but may fall back to manual creation
    try:
        await async_setup_helpers(hass, entry)
    except Exception as e:
        _LOGGER.warning(
            f"Could not auto-create helper entities: {e}. "
            "Please create them manually. See HELPER_ENTITIES.md"
        )
    
    # Create device registry entries for rooms
    try:
        await async_create_room_devices(hass, entry)
    except Exception as e:
        _LOGGER.warning(f"Could not create room devices: {e}")
    
    # Forward entry setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Set up scripts and automations
    await script.async_setup_entry(hass, entry)
    await automation.async_setup_entry(hass, entry)
    
    # Register services
    await _async_register_services(hass, entry)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Zone Controller entry."""
    # Remove room devices
    try:
        await async_remove_room_devices(hass, entry)
    except Exception as e:
        _LOGGER.warning(f"Could not remove room devices: {e}")
    
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    # Unload scripts and automations
    await automation.async_unload_entry(hass, entry)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok


async def _async_register_services(hass: HomeAssistant, entry: ConfigEntry):
    """Register custom services."""
    
    async def set_room_priority(call):
        """Handle set_room_priority service call."""
        room = call.data.get("room")
        priority = call.data.get("priority")
        
        # Update room priority in config entry
        rooms = list(entry.data.get("rooms", []))
        for i, room_config in enumerate(rooms):
            room_key = room_config.get("name", "").lower().replace(" ", "_")
            if room_key == room.lower().replace(" ", "_"):
                rooms[i] = {**room_config, "priority": priority}
                break
        
        data = dict(entry.data)
        data["rooms"] = rooms
        
        hass.config_entries.async_update_entry(entry, data=data)
    
    async def override_room(call):
        """Handle override_room service call."""
        # TODO: Implement room override logic
        pass
    
    async def reset_to_defaults(call):
        """Handle reset_to_defaults service call."""
        # Reset all options to defaults
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
        }
        
        hass.config_entries.async_update_entry(entry, options=options)
        _LOGGER.info("Zone Controller options reset to defaults")
    
    # Register services
    hass.services.async_register(DOMAIN, "set_room_priority", set_room_priority)
    hass.services.async_register(DOMAIN, "override_room", override_room)
    hass.services.async_register(DOMAIN, "reset_to_defaults", reset_to_defaults)
