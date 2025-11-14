"""Helper entities initialization for Smart Vent Controller."""

import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.storage import Store

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Storage key for helper entities config
STORAGE_KEY = f"{DOMAIN}.helpers"
STORAGE_VERSION = 1


async def async_setup_helpers(hass: HomeAssistant, entry: ConfigEntry):
    """Set up helper entities automatically."""
    _LOGGER.info("Setting up Smart Vent Controller helper entities...")
    
    # Create helper entities via YAML config injection
    # This is the most reliable method
    await _create_helpers_via_yaml(hass, entry)
    
    _LOGGER.info("Smart Vent Controller helper entities setup complete")


async def _create_helpers_via_yaml(hass: HomeAssistant, entry: ConfigEntry):
    """Create helpers by injecting YAML configuration."""
    # Get the input_number, input_boolean, and input_text storage collections
    # and create items directly
    
    # Define all helper entities
    number_configs = _get_number_configs(entry)
    boolean_configs = _get_boolean_configs()
    text_configs = _get_text_configs()
    
    # Create input_number entities
    await _ensure_input_numbers(hass, number_configs)
    
    # Create input_boolean entities
    await _ensure_input_booleans(hass, boolean_configs)
    
    # Create input_text entities
    await _ensure_input_texts(hass, text_configs)


def _get_number_configs(entry: ConfigEntry) -> dict:
    """Get input_number configurations."""
    configs = {
        "min_other_room_open_pct": {
            "name": "Minimum Other Room Open %",
            "min": 0,
            "max": 100,
            "step": 1,
            "initial": 20,
            "unit_of_measurement": "%",
            "icon": "mdi:weather-windy",
        },
        "occupancy_linger_min": {
            "name": "Occupancy Linger (day, min)",
            "min": 0,
            "max": 300,
            "step": 1,
            "initial": 30,
            "unit_of_measurement": "min",
            "icon": "mdi:timer-sand",
        },
        "occupancy_linger_night_min": {
            "name": "Occupancy Linger (night, min)",
            "min": 0,
            "max": 300,
            "step": 1,
            "initial": 60,
            "unit_of_measurement": "min",
            "icon": "mdi:weather-night",
        },
        "room_hysteresis_f": {
            "name": "Room Hysteresis (°F)",
            "min": 0,
            "max": 5,
            "step": 0.1,
            "initial": 1.0,
            "unit_of_measurement": "°F",
            "icon": "mdi:tune",
        },
        "closed_threshold_pct": {
            "name": "Closed Threshold %",
            "min": 0,
            "max": 100,
            "step": 1,
            "initial": 10,
            "unit_of_measurement": "%",
            "icon": "mdi:percent",
        },
        "relief_open_pct": {
            "name": "Relief Open %",
            "min": 0,
            "max": 100,
            "step": 1,
            "initial": 60,
            "unit_of_measurement": "%",
            "icon": "mdi:fan",
        },
        "heat_boost_f": {
            "name": "Heat Boost (°F)",
            "min": 0,
            "max": 3,
            "step": 0.5,
            "initial": 1.0,
            "unit_of_measurement": "°F",
            "icon": "mdi:thermometer-plus",
        },
        "automation_cooldown_sec": {
            "name": "Automation Cooldown (sec)",
            "min": 0,
            "max": 300,
            "step": 5,
            "initial": 30,
            "unit_of_measurement": "s",
            "icon": "mdi:timer-outline",
        },
        "max_relief_rooms": {
            "name": "Max Relief Rooms",
            "min": 1,
            "max": 10,
            "step": 1,
            "initial": 3,
            "unit_of_measurement": "rooms",
            "icon": "mdi:fan-alert",
        },
        "default_thermostat_temp": {
            "name": "Default Thermostat Temp (°F)",
            "min": 65,
            "max": 80,
            "step": 1,
            "initial": 72,
            "unit_of_measurement": "°F",
            "icon": "mdi:thermometer",
        },
        "hvac_min_runtime_min": {
            "name": "HVAC Minimum Runtime (min)",
            "min": 0,
            "max": 30,
            "step": 1,
            "initial": 10,
            "unit_of_measurement": "min",
            "icon": "mdi:timer-play-outline",
        },
        "hvac_min_off_time_min": {
            "name": "HVAC Minimum Off Time (min)",
            "min": 0,
            "max": 30,
            "step": 1,
            "initial": 5,
            "unit_of_measurement": "min",
            "icon": "mdi:timer-off-outline",
        },
        "hvac_cycle_start_timestamp": {
            "name": "HVAC Cycle Start Timestamp (Internal)",
            "min": 0,
            "max": 9999999999,
            "step": 1,
            "initial": 0,
            "icon": "mdi:clock-start",
            "mode": "box",
        },
        "hvac_cycle_end_timestamp": {
            "name": "HVAC Cycle End Timestamp (Internal)",
            "min": 0,
            "max": 9999999999,
            "step": 1,
            "initial": 0,
            "icon": "mdi:clock-end",
            "mode": "box",
        },
        "last_thermostat_setpoint": {
            "name": "Last Thermostat Setpoint (Internal)",
            "min": 40,
            "max": 100,
            "step": 0.5,
            "initial": 72,
            "unit_of_measurement": "°F",
            "icon": "mdi:thermostat",
        },
    }
    
    # Add room priorities
    rooms = entry.data.get("rooms", [])
    for room in rooms:
        room_key = room.get("name", "").lower().replace(" ", "_")
        priority_key = f"{room_key}_priority"
        configs[priority_key] = {
            "name": f"{room.get('name', room_key.title())} Priority",
            "min": 0,
            "max": 10,
            "step": 1,
            "initial": room.get("priority", 5),
            "icon": "mdi:star",
        }
    
    return configs


def _get_boolean_configs() -> dict:
    """Get input_boolean configurations."""
    return {
        "require_occupancy": {
            "name": "Condition Only When Occupied",
            "initial": True,
            "icon": "mdi:account-eye",
        },
        "heat_boost_enabled": {
            "name": "Heat Boost Enabled",
            "initial": True,
            "icon": "mdi:fire",
        },
        "auto_thermostat_control": {
            "name": "Auto Thermostat Control",
            "initial": True,
            "icon": "mdi:thermostat-auto",
        },
        "auto_vent_control": {
            "name": "Auto Vent Control",
            "initial": True,
            "icon": "mdi:air-conditioner",
        },
        "debug_mode": {
            "name": "Debug Mode (Enhanced Logging)",
            "initial": False,
            "icon": "mdi:bug",
        },
    }


def _get_text_configs() -> dict:
    """Get input_text configurations."""
    return {
        "hvac_last_action": {
            "name": "HVAC Last Action (Internal)",
            "initial": "idle",
            "min": 0,
            "max": 20,
        },
    }


async def _ensure_input_numbers(hass: HomeAssistant, configs: dict):
    """Ensure input_number entities exist."""
    from homeassistant.components.input_number import DOMAIN as INPUT_NUMBER_DOMAIN
    
    # Try to access the storage collection
    try:
        # Get the storage collection manager
        if INPUT_NUMBER_DOMAIN in hass.data:
            collection = hass.data[INPUT_NUMBER_DOMAIN]
            if hasattr(collection, "async_create_item"):
                for entity_id, config in configs.items():
                    full_id = f"{INPUT_NUMBER_DOMAIN}.{entity_id}"
                    
                    # Check if exists
                    if hass.states.get(full_id) is not None:
                        _LOGGER.debug(f"Input number {full_id} already exists")
                        continue
                    
                    # Create item
                    try:
                        item_config = {
                            "id": entity_id,
                            "name": config["name"],
                            "min": config["min"],
                            "max": config["max"],
                            "step": config["step"],
                            "initial": config.get("initial", 0),
                        }
                        if "unit_of_measurement" in config:
                            item_config["unit_of_measurement"] = config["unit_of_measurement"]
                        if "icon" in config:
                            item_config["icon"] = config["icon"]
                        if "mode" in config:
                            item_config["mode"] = config["mode"]
                        
                        await collection.async_create_item(item_config)
                        _LOGGER.info(f"Created input_number.{entity_id}")
                    except Exception as e:
                        _LOGGER.warning(f"Could not create input_number.{entity_id}: {e}")
    except Exception as e:
        _LOGGER.debug(f"Could not access input_number storage: {e}")
        # Fallback: log instructions
        _LOGGER.info(
            "Could not auto-create input_number entities. "
            "Please create them manually via YAML or UI. "
            "See HELPER_ENTITIES.md for configuration."
        )


async def _ensure_input_booleans(hass: HomeAssistant, configs: dict):
    """Ensure input_boolean entities exist."""
    from homeassistant.components.input_boolean import DOMAIN as INPUT_BOOLEAN_DOMAIN
    
    try:
        if INPUT_BOOLEAN_DOMAIN in hass.data:
            collection = hass.data[INPUT_BOOLEAN_DOMAIN]
            if hasattr(collection, "async_create_item"):
                for entity_id, config in configs.items():
                    full_id = f"{INPUT_BOOLEAN_DOMAIN}.{entity_id}"
                    
                    if hass.states.get(full_id) is not None:
                        _LOGGER.debug(f"Input boolean {full_id} already exists")
                        continue
                    
                    try:
                        await collection.async_create_item({
                            "id": entity_id,
                            "name": config["name"],
                            "initial": config.get("initial", False),
                            "icon": config.get("icon"),
                        })
                        _LOGGER.info(f"Created input_boolean.{entity_id}")
                    except Exception as e:
                        _LOGGER.warning(f"Could not create input_boolean.{entity_id}: {e}")
    except Exception as e:
        _LOGGER.debug(f"Could not access input_boolean storage: {e}")
        _LOGGER.info(
            "Could not auto-create input_boolean entities. "
            "Please create them manually via YAML or UI."
        )


async def _ensure_input_texts(hass: HomeAssistant, configs: dict):
    """Ensure input_text entities exist."""
    from homeassistant.components.input_text import DOMAIN as INPUT_TEXT_DOMAIN
    
    try:
        if INPUT_TEXT_DOMAIN in hass.data:
            collection = hass.data[INPUT_TEXT_DOMAIN]
            if hasattr(collection, "async_create_item"):
                for entity_id, config in configs.items():
                    full_id = f"{INPUT_TEXT_DOMAIN}.{entity_id}"
                    
                    if hass.states.get(full_id) is not None:
                        _LOGGER.debug(f"Input text {full_id} already exists")
                        continue
                    
                    try:
                        await collection.async_create_item({
                            "id": entity_id,
                            "name": config["name"],
                            "initial": config.get("initial", ""),
                            "min": config.get("min", 0),
                            "max": config.get("max", 255),
                        })
                        _LOGGER.info(f"Created input_text.{entity_id}")
                    except Exception as e:
                        _LOGGER.warning(f"Could not create input_text.{entity_id}: {e}")
    except Exception as e:
        _LOGGER.debug(f"Could not access input_text storage: {e}")
        _LOGGER.info(
            "Could not auto-create input_text entities. "
            "Please create them manually via YAML or UI."
        )
