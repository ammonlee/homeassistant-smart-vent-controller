"""Migration utilities for importing from YAML configuration."""

import logging
from typing import Any
from pathlib import Path
import yaml

from homeassistant.core import HomeAssistant
from homeassistant.config import load_yaml_config_file
from homeassistant.exceptions import HomeAssistantError

_LOGGER = logging.getLogger(__name__)


class MigrationError(HomeAssistantError):
    """Error during migration."""
    pass


async def detect_yaml_config(hass: HomeAssistant) -> dict[str, Any] | None:
    """Detect and parse YAML configuration.
    
    Args:
        hass: Home Assistant instance
    
    Returns:
        Parsed configuration dict or None if not found
    """
    config_dir = Path(hass.config.config_dir)
    
    # Common YAML locations
    yaml_paths = [
        config_dir / "packages" / "vent_zone_controller.yaml",
        config_dir / "vent_zone_controller.yaml",
        config_dir / "packages" / "vent_zone_controller_updated.yaml",
    ]
    
    for yaml_path in yaml_paths:
        if yaml_path.exists():
            try:
                config = await hass.async_add_executor_job(
                    load_yaml_config_file, str(yaml_path)
                )
                if config and "input_number" in config:
                    # Likely our YAML config
                    return await parse_yaml_config(hass, config)
            except Exception as e:
                _LOGGER.warning(f"Error reading YAML config at {yaml_path}: {e}")
                continue
    
    return None


async def parse_yaml_config(hass: HomeAssistant, yaml_config: dict[str, Any]) -> dict[str, Any]:
    """Parse YAML configuration into integration format.
    
    Args:
        hass: Home Assistant instance
        yaml_config: Parsed YAML configuration
    
    Returns:
        Configuration dict for integration
    """
    result = {
        "main_thermostat": None,
        "rooms": [],
        "options": {},
    }
    
    # Extract main thermostat from scripts/automations
    # Look for climate.set_temperature calls
    scripts = yaml_config.get("script", {})
    automations = yaml_config.get("automation", [])
    
    # Check scripts first
    for script_name, script_config in scripts.items():
        if isinstance(script_config, dict):
            sequence = script_config.get("sequence", [])
            for action in sequence:
                if isinstance(action, dict):
                    service = action.get("service", "")
                    if "climate.set_temperature" in service:
                        service_data = action.get("service_data", {})
                        entity_id = service_data.get("entity_id")
                        if entity_id and "climate" in entity_id and "thermostat" in entity_id.lower():
                            result["main_thermostat"] = entity_id
                            break
            if result["main_thermostat"]:
                break
    
    # Check automations if not found
    if not result["main_thermostat"]:
        for automation in automations:
            if isinstance(automation, dict):
                actions = automation.get("action", [])
                for action in actions:
                    if isinstance(action, dict):
                        service = action.get("service", "")
                        if "climate.set_temperature" in service:
                            service_data = action.get("service_data", {})
                            entity_id = service_data.get("entity_id")
                            if entity_id and "climate" in entity_id:
                                result["main_thermostat"] = entity_id
                                break
                if result["main_thermostat"]:
                    break
    
    # Extract rooms from template sensors
    # Look for room temperature/target/delta sensors
    sensors = yaml_config.get("sensor", [])
    room_patterns = {}
    
    # Common room names to look for
    room_names = [
        "master", "blue", "gold", "green", "grey", "guest", "kitchen",
        "family", "piano", "basement", "office", "bedroom", "living"
    ]
    
    for sensor in sensors:
        if isinstance(sensor, dict):
            platform = sensor.get("platform", "")
            if platform == "template":
                # Look for room temperature sensors
                for room_name in room_names:
                    sensor_id = sensor.get("unique_id", "") or sensor.get("friendly_name", "")
                    if room_name in sensor_id.lower() and "temp" in sensor_id.lower():
                        if room_name not in room_patterns:
                            room_patterns[room_name] = {
                                "name": room_name.title().replace("_", " "),
                                "climate_entity": None,
                                "temp_sensor": None,
                                "occupancy_sensor": None,
                                "vent_entities": [],
                            }
    
    # Extract room configurations from template sensors
    # Look for climate entities in templates
    for sensor in sensors:
        if isinstance(sensor, dict) and sensor.get("platform") == "template":
            template = sensor.get("value_template", "")
            if isinstance(template, str):
                # Look for climate entities
                import re
                climate_matches = re.findall(r"climate\.(\w+_room)", template)
                for match in climate_matches:
                    room_key = match.replace("_room", "").lower()
                    if room_key in room_patterns:
                        room_patterns[room_key]["climate_entity"] = f"climate.{match}"
    
    # Extract vent entities from groups or direct references
    groups = yaml_config.get("group", {})
    for group_name, group_config in groups.items():
        if isinstance(group_config, dict):
            entities = group_config.get("entities", [])
            for entity in entities:
                if isinstance(entity, str) and "cover" in entity and "vent" in entity.lower():
                    # Try to match to room
                    for room_key in room_patterns:
                        if room_key in entity.lower():
                            if entity not in room_patterns[room_key]["vent_entities"]:
                                room_patterns[room_key]["vent_entities"].append(entity)
    
    # Convert to rooms list
    for room_key, room_data in room_patterns.items():
        if room_data["climate_entity"] or room_data["vent_entities"]:
            result["rooms"].append({
                "name": room_data["name"],
                "climate_entity": room_data["climate_entity"] or f"climate.{room_key}_room_room",
                "temp_sensor": room_data["temp_sensor"] or "",
                "occupancy_sensor": room_data["occupancy_sensor"] or "",
                "vent_entities": room_data["vent_entities"],
                "priority": 5,  # Default priority
            })
    
    # Extract settings from input_number and input_boolean
    input_numbers = yaml_config.get("input_number", {})
    input_booleans = yaml_config.get("input_boolean", {})
    
    # Map common settings
    if "min_other_room_open_pct" in input_numbers:
        result["options"]["min_other_room_open_pct"] = input_numbers["min_other_room_open_pct"].get("initial", 20)
    
    if "closed_threshold_pct" in input_numbers:
        result["options"]["closed_threshold_pct"] = input_numbers["closed_threshold_pct"].get("initial", 10)
    
    if "relief_open_pct" in input_numbers:
        result["options"]["relief_open_pct"] = input_numbers["relief_open_pct"].get("initial", 60)
    
    if "max_relief_rooms" in input_numbers:
        result["options"]["max_relief_rooms"] = input_numbers["max_relief_rooms"].get("initial", 3)
    
    if "room_hysteresis_f" in input_numbers:
        result["options"]["room_hysteresis_f"] = input_numbers["room_hysteresis_f"].get("initial", 1.0)
    
    if "occupancy_linger_min" in input_numbers:
        result["options"]["occupancy_linger_min"] = input_numbers["occupancy_linger_min"].get("initial", 30)
    
    if "occupancy_linger_night_min" in input_numbers:
        result["options"]["occupancy_linger_night_min"] = input_numbers["occupancy_linger_night_min"].get("initial", 60)
    
    if "heat_boost_f" in input_numbers:
        result["options"]["heat_boost_f"] = input_numbers["heat_boost_f"].get("initial", 1.0)
    
    if "hvac_min_runtime_min" in input_numbers:
        result["options"]["hvac_min_runtime_min"] = input_numbers["hvac_min_runtime_min"].get("initial", 10)
    
    if "hvac_min_off_time_min" in input_numbers:
        result["options"]["hvac_min_off_time_min"] = input_numbers["hvac_min_off_time_min"].get("initial", 5)
    
    if "default_thermostat_temp" in input_numbers:
        result["options"]["default_thermostat_temp"] = input_numbers["default_thermostat_temp"].get("initial", 72)
    
    if "automation_cooldown_sec" in input_numbers:
        result["options"]["automation_cooldown_sec"] = input_numbers["automation_cooldown_sec"].get("initial", 30)
    
    if "require_occupancy" in input_booleans:
        result["options"]["require_occupancy"] = input_booleans["require_occupancy"].get("initial", True)
    
    if "heat_boost_enabled" in input_booleans:
        result["options"]["heat_boost_enabled"] = input_booleans["heat_boost_enabled"].get("initial", True)
    
    if "auto_thermostat_control" in input_booleans:
        result["options"]["auto_thermostat_control"] = input_booleans["auto_thermostat_control"].get("initial", True)
    
    if "auto_vent_control" in input_booleans:
        result["options"]["auto_vent_control"] = input_booleans["auto_vent_control"].get("initial", True)
    
    if "debug_mode" in input_booleans:
        result["options"]["debug_mode"] = input_booleans["debug_mode"].get("initial", False)
    
    return result


async def validate_migration_config(hass: HomeAssistant, config: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate migration configuration.
    
    Args:
        hass: Home Assistant instance
        config: Configuration to validate
    
    Returns:
        Tuple of (is_valid, list of warnings)
    """
    warnings = []
    
    # Validate main thermostat
    main_thermostat = config.get("main_thermostat")
    if not main_thermostat:
        warnings.append("No main thermostat found in YAML configuration")
    elif main_thermostat not in hass.states.async_entity_ids("climate"):
        warnings.append(f"Main thermostat {main_thermostat} not found or unavailable")
    
    # Validate rooms
    rooms = config.get("rooms", [])
    if not rooms:
        warnings.append("No rooms found in YAML configuration")
    
    for room in rooms:
        climate_entity = room.get("climate_entity")
        if climate_entity and climate_entity not in hass.states.async_entity_ids("climate"):
            warnings.append(f"Room {room.get('name')} climate entity {climate_entity} not found")
        
        vent_entities = room.get("vent_entities", [])
        for vent_entity in vent_entities:
            if vent_entity not in hass.states.async_entity_ids("cover"):
                warnings.append(f"Vent entity {vent_entity} not found")
    
    is_valid = len(warnings) == 0 or all("not found" not in w for w in warnings)
    
    return is_valid, warnings

