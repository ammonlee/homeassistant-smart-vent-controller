"""Diagnostics support for Zone Controller."""

from typing import Any
from datetime import datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .const import DOMAIN
from .error_handling import validate_entity_state, get_safe_state, get_safe_attribute


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry.
    
    Args:
        hass: Home Assistant instance
        config_entry: Configuration entry
    
    Returns:
        Dictionary containing diagnostic information
    """
    coordinator = hass.data.get(DOMAIN, {}).get(config_entry.entry_id)
    
    # Get basic configuration
    config = {
        "main_thermostat": config_entry.data.get("main_thermostat"),
        "rooms_count": len(config_entry.data.get("rooms", [])),
        "options": config_entry.options or {},
    }
    
    # Get room states
    rooms = []
    for room_config in config_entry.data.get("rooms", []):
        room_name = room_config.get("name", "")
        room_key = room_name.lower().replace(" ", "_")
        climate_entity = room_config.get("climate_entity", "")
        temp_sensor = room_config.get("temp_sensor", "")
        occ_sensor = room_config.get("occupancy_sensor", "")
        vent_entities = room_config.get("vent_entities", [])
        
        # Get room state
        room_state = {
            "name": room_name,
            "key": room_key,
            "climate_entity": climate_entity,
            "climate_available": validate_entity_state(hass, climate_entity, "climate"),
            "temp_sensor": temp_sensor,
            "temp_sensor_available": validate_entity_state(hass, temp_sensor, "sensor") if temp_sensor else False,
            "occupancy_sensor": occ_sensor,
            "occupancy_sensor_available": validate_entity_state(hass, occ_sensor, "binary_sensor") if occ_sensor else False,
            "vent_count": len(vent_entities),
            "vent_entities": vent_entities,
        }
        
        # Get current temperature
        current_temp = None
        if temp_sensor and validate_entity_state(hass, temp_sensor, "sensor"):
            temp_value = get_safe_state(hass, temp_sensor)
            try:
                current_temp = float(temp_value) if temp_value else None
            except (ValueError, TypeError):
                pass
        
        if current_temp is None and climate_entity and validate_entity_state(hass, climate_entity, "climate"):
            temp = get_safe_attribute(hass, climate_entity, "current_temperature")
            if temp is not None:
                try:
                    current_temp = float(temp)
                except (ValueError, TypeError):
                    pass
        
        # Get target temperature
        target_temp = None
        if climate_entity and validate_entity_state(hass, climate_entity, "climate"):
            temp = get_safe_attribute(hass, climate_entity, "temperature")
            if temp is not None:
                try:
                    target_temp = float(temp)
                except (ValueError, TypeError):
                    pass
            else:
                lo = get_safe_attribute(hass, climate_entity, "target_temp_low")
                hi = get_safe_attribute(hass, climate_entity, "target_temp_high")
                if lo is not None and hi is not None:
                    try:
                        target_temp = (float(lo) + float(hi)) / 2
                    except (ValueError, TypeError):
                        pass
        
        # Calculate delta
        delta = None
        if current_temp is not None and target_temp is not None:
            delta = target_temp - current_temp
        
        # Get occupancy
        occupied = False
        if occ_sensor and validate_entity_state(hass, occ_sensor, "binary_sensor"):
            occ_state = get_safe_state(hass, occ_sensor)
            occupied = occ_state == "on"
        
        # Get vent positions
        vent_positions = []
        for vent_entity in vent_entities:
            if validate_entity_state(hass, vent_entity, "cover"):
                position = get_safe_attribute(hass, vent_entity, "current_position", 100)
                vent_positions.append({
                    "entity": vent_entity,
                    "position": position,
                    "available": True,
                })
            else:
                vent_positions.append({
                    "entity": vent_entity,
                    "position": None,
                    "available": False,
                })
        
        room_state.update({
            "current_temperature": current_temp,
            "target_temperature": target_temp,
            "delta": delta,
            "occupied": occupied,
            "vent_positions": vent_positions,
        })
        
        rooms.append(room_state)
    
    # Get main thermostat state
    main_thermostat = config_entry.data.get("main_thermostat")
    thermostat_state = None
    if main_thermostat:
        if validate_entity_state(hass, main_thermostat, "climate"):
            state = hass.states.get(main_thermostat)
            if state:
                thermostat_state = {
                    "entity": main_thermostat,
                    "state": state.state,
                    "available": True,
                    "hvac_action": get_safe_attribute(hass, main_thermostat, "hvac_action"),
                    "temperature": get_safe_attribute(hass, main_thermostat, "temperature"),
                    "current_temperature": get_safe_attribute(hass, main_thermostat, "current_temperature"),
                    "target_temp_low": get_safe_attribute(hass, main_thermostat, "target_temp_low"),
                    "target_temp_high": get_safe_attribute(hass, main_thermostat, "target_temp_high"),
                }
        else:
            thermostat_state = {
                "entity": main_thermostat,
                "available": False,
            }
    
    # Get rooms to condition
    rooms_to_condition = None
    rooms_to_condition_entity = hass.states.get("sensor.rooms_to_condition")
    if rooms_to_condition_entity:
        rooms_to_condition = rooms_to_condition_entity.state
    
    # Get automation status
    automation_status = {
        "auto_vent_control": config_entry.options.get("auto_vent_control", True),
        "auto_thermostat_control": config_entry.options.get("auto_thermostat_control", True),
        "require_occupancy": config_entry.options.get("require_occupancy", True),
        "debug_mode": config_entry.options.get("debug_mode", False),
    }
    
    # Get cycle protection status
    cycle_protection = {
        "enabled": (
            config_entry.options.get("hvac_min_runtime_min", 10) > 0 or
            config_entry.options.get("hvac_min_off_time_min", 5) > 0
        ),
        "min_runtime_min": config_entry.options.get("hvac_min_runtime_min", 10),
        "min_off_time_min": config_entry.options.get("hvac_min_off_time_min", 5),
    }
    
    # Get manual override status
    manual_override = False
    manual_override_entity = hass.states.get("binary_sensor.thermostat_manual_override_detected")
    if manual_override_entity:
        manual_override = manual_override_entity.state == "on"
    
    # Get statistics
    stats_entity = hass.states.get("sensor.zone_controller_stats")
    statistics = None
    if stats_entity:
        statistics = stats_entity.attributes
    
    # Get device registry info
    device_registry = dr.async_get(hass)
    devices = []
    for room_config in config_entry.data.get("rooms", []):
        room_name = room_config.get("name", "")
        room_key = room_name.lower().replace(" ", "_")
        device_id = (DOMAIN, f"{config_entry.entry_id}_{room_key}")
        device = device_registry.async_get_device(identifiers={device_id})
        if device:
            devices.append({
                "name": device.name,
                "identifiers": list(device.identifiers),
                "manufacturer": device.manufacturer,
                "model": device.model,
            })
    
    # Compile diagnostics
    diagnostics = {
        "config": config,
        "main_thermostat": thermostat_state,
        "rooms": rooms,
        "rooms_to_condition": rooms_to_condition,
        "automation_status": automation_status,
        "cycle_protection": cycle_protection,
        "manual_override": manual_override,
        "statistics": statistics,
        "devices": devices,
        "timestamp": datetime.now().isoformat(),
    }
    
    return diagnostics

