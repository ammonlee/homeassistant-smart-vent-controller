"""Script implementations for Zone Controller."""

from typing import Any
from datetime import datetime, time as dt_time
import logging

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.service import async_call_from_config

from .const import DOMAIN
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

_LOGGER = logging.getLogger(__name__)


class VentControlScript:
    """Script to control vents for multiple rooms."""
    
    def __init__(self, hass: HomeAssistant, entry):
        """Initialize the script."""
        self.hass = hass
        self.entry = entry
        self.error_recovery = ErrorRecovery(hass, entry)
    
    async def async_run(self, rooms_csv: str = None):
        """Run the vent control script."""
        try:
            # Check if vent control is enabled
            auto_vent_control = self.entry.options.get("auto_vent_control", True)
            if not auto_vent_control:
                _LOGGER.info("Vent control disabled. Skipping vent adjustments.")
                return
            
            # Check error recovery
            if self.error_recovery.should_disable_component("vent_control"):
                _LOGGER.error(
                    "Vent control disabled due to repeated errors. "
                    "Check logs and fix issues, then restart Home Assistant."
                )
                return
            
            debug_mode = self.entry.options.get("debug_mode", False)
            
            # Get configuration with validation
            min_other = safe_int(self.entry.options.get("min_other_room_open_pct", 20), 20, 0, 100)
            close_thr = safe_int(self.entry.options.get("closed_threshold_pct", 10), 10, 0, 100)
            relief_pct = safe_int(self.entry.options.get("relief_open_pct", 60), 60, 0, 100)
            max_relief = safe_int(self.entry.options.get("max_relief_rooms", 3), 3, 1, 10)
            
            main_thermostat = self.entry.data.get("main_thermostat")
            if not validate_entity_state(self.hass, main_thermostat, "climate"):
                _LOGGER.error(f"Thermostat {main_thermostat} not found or unavailable")
                self.error_recovery.record_error("vent_control", EntityUnavailableError(f"Thermostat {main_thermostat} unavailable"))
                return
            
            thermostat_state = self.hass.states.get(main_thermostat)
            mode = thermostat_state.state if thermostat_state else "off"
            action = get_safe_attribute(self.hass, main_thermostat, "hvac_action", "idle")
        
            # Parse selected rooms
            selected_list = self._parse_rooms_csv(rooms_csv or "")
            
            if debug_mode:
                _LOGGER.info(
                    f"Zone Controller: Starting vent adjustment. "
                    f"Mode={mode}, Action={action}, Selected={','.join(selected_list)}"
                )
            
            # Get room data
            rooms_data = await self._get_rooms_data(selected_list)
            
            # Get all vent entities
            all_vent_entities = await self._get_all_vent_entities()
            
            if not all_vent_entities:
                _LOGGER.warning("No vent entities found. Check room configuration.")
                return
            
            if debug_mode:
                _LOGGER.info(f"Total Vents: {len(all_vent_entities)}")
            
            # Step 1: Set all vents to minimum
            await self._set_vents_to_minimum(all_vent_entities, min_other, debug_mode)
            
            # Step 2: Open selected rooms to 100%
            await self._open_selected_rooms(rooms_data, selected_list, debug_mode)
            
            # Step 3: Close rooms that don't need conditioning
            await self._close_unneeded_rooms(rooms_data, selected_list, mode, action, min_other, debug_mode)
            
            # Step 4: Enforce ≤ 1/3 closed with relief
            await self._enforce_relief_rule(
                all_vent_entities, rooms_data, selected_list, 
                mode, action, close_thr, relief_pct, max_relief, debug_mode
            )
            
            # Reset error count on success
            self.error_recovery.reset_errors("vent_control")
            
        except Exception as e:
            _LOGGER.error(f"Error in vent control script: {e}", exc_info=True)
            self.error_recovery.record_error("vent_control", e)
            raise
    
    def _parse_rooms_csv(self, rooms_csv: str) -> list[str]:
        """Parse comma-separated room list."""
        if not rooms_csv or rooms_csv.strip() in ["", "none"]:
            return []
        
        # Get valid room keys from config
        rooms = self.entry.data.get("rooms", [])
        valid_keys = [
            room.get("name", "").lower().replace(" ", "_")
            for room in rooms
        ]
        
        # Parse CSV
        parts = [p.strip() for p in rooms_csv.split(",") if p.strip()]
        filtered = [p for p in parts if p in valid_keys]
        
        return filtered
    
    async def _get_rooms_data(self, selected_list: list[str]) -> list[dict]:
        """Get data for all rooms with caching."""
        rooms_config = self.entry.data.get("rooms", [])
        rooms_data = []
        
        # Get coordinator for cache access
        coordinator = self.hass.data.get("zone_controller", {}).get(self.entry.entry_id)
        use_cache = coordinator is not None
        
        for room_config in rooms_config:
            room_key = room_config.get("name", "").lower().replace(" ", "_")
            
            # Try cache first
            cached_data = None
            if use_cache:
                cached_data = coordinator.room_cache.get_room_data(room_key)
            
            if cached_data:
                rooms_data.append(cached_data)
                continue
            
            # Fetch fresh data if not cached
            climate_entity = room_config.get("climate_entity")
            temp_sensor = room_config.get("temp_sensor", "")
            occ_sensor = room_config.get("occupancy_sensor", "")
            vent_entities = room_config.get("vent_entities", [])
            priority = room_config.get("priority", 5)
            
            # Get current temperature with validation
            current_temp = None
            temp_valid = False
            
            if temp_sensor and validate_entity_state(self.hass, temp_sensor, "sensor"):
                temp_value = get_safe_state(self.hass, temp_sensor)
                if temp_value:
                    current_temp = safe_float(temp_value, min_val=40.0, max_val=100.0)
                    temp_valid = validate_temperature(current_temp)
            
            if not temp_valid and climate_entity and validate_entity_state(self.hass, climate_entity, "climate"):
                temp = get_safe_attribute(self.hass, climate_entity, "current_temperature")
                if temp is not None:
                    current_temp = safe_float(temp, min_val=40.0, max_val=100.0)
                    temp_valid = validate_temperature(current_temp)
            
            # Get target temperature with validation
            target_temp = None
            if climate_entity and validate_entity_state(self.hass, climate_entity, "climate"):
                temp = get_safe_attribute(self.hass, climate_entity, "temperature")
                if temp is not None:
                    target_temp = safe_float(temp, min_val=40.0, max_val=100.0)
                else:
                    lo = get_safe_attribute(self.hass, climate_entity, "target_temp_low")
                    hi = get_safe_attribute(self.hass, climate_entity, "target_temp_high")
                    if lo is not None and hi is not None:
                        lo_float = safe_float(lo, min_val=40.0, max_val=100.0)
                        hi_float = safe_float(hi, min_val=40.0, max_val=100.0)
                        target_temp = (lo_float + hi_float) / 2
            
            # Calculate delta
            delta = (target_temp - current_temp) if (target_temp is not None and current_temp is not None) else 0
            
            # Get occupancy with validation
            occupied = False
            if occ_sensor and validate_entity_state(self.hass, occ_sensor, "binary_sensor"):
                occ_state_value = get_safe_state(self.hass, occ_sensor)
                occupied = occ_state_value == "on"
            
            room_data = {
                "key": room_key,
                "name": room_config.get("name", ""),
                "climate_entity": climate_entity,
                "temp_sensor": temp_sensor,
                "occ_sensor": occ_sensor,
                "vent_entities": vent_entities,
                "priority": priority,
                "current_temp": current_temp,
                "target_temp": target_temp,
                "delta": delta,
                "occupied": occupied,
                "temp_valid": temp_valid,
            }
            
            # Cache room data
            if use_cache:
                coordinator.room_cache.set_room_data(room_key, room_data)
            
            rooms_data.append(room_data)
        
        return rooms_data
    
    async def _get_all_vent_entities(self) -> list[str]:
        """Get all vent entities from room configurations."""
        vent_entities = []
        rooms_config = self.entry.data.get("rooms", [])
        
        for room_config in rooms_config:
            vent_entities.extend(room_config.get("vent_entities", []))
        
        # Remove duplicates
        return list(set(vent_entities))
    
    async def _set_vents_to_minimum(self, vent_entities: list[str], min_other: int, debug_mode: bool):
        """Set all vents to minimum."""
        # Use batcher for multiple calls
        async with ServiceCallBatcher(self.hass, batch_size=10) as batcher:
            for vent_entity in vent_entities:
                if not validate_entity_state(self.hass, vent_entity, "cover"):
                    if debug_mode:
                        _LOGGER.debug(f"Skipping unavailable vent {vent_entity}")
                    continue
                
                # Validate position
                if not validate_vent_position(min_other):
                    _LOGGER.warning(f"Invalid vent position {min_other} for {vent_entity}, skipping")
                    continue
                
                # Add to batch
                await batcher.add_call(
                    "cover",
                    "set_cover_position",
                    {"entity_id": vent_entity, "position": min_other}
                )
        
        # Batch will flush automatically on exit
    
    async def _open_selected_rooms(self, rooms_data: list[dict], selected_list: list[str], debug_mode: bool):
        """Open selected rooms to 100%."""
        # Use batcher for multiple calls
        async with ServiceCallBatcher(self.hass, batch_size=10) as batcher:
            for room in rooms_data:
                if room["key"] in selected_list:
                    if debug_mode:
                        _LOGGER.info(f"Opening {room['name']} vents to 100%")
                    
                    for vent_entity in room.get("vent_entities", []):
                        if not validate_entity_state(self.hass, vent_entity, "cover"):
                            if debug_mode:
                                _LOGGER.debug(f"Skipping unavailable vent {vent_entity}")
                            continue
                        
                        # Add to batch
                        await batcher.add_call(
                            "cover",
                            "set_cover_position",
                            {"entity_id": vent_entity, "position": 100}
                        )
        
        # Batch will flush automatically on exit
    
    async def _close_unneeded_rooms(
        self, rooms_data: list[dict], selected_list: list[str], 
        mode: str, action: str, min_other: int, debug_mode: bool
    ):
        """Close rooms that don't need conditioning."""
        for room in rooms_data:
            if room["key"] in selected_list:
                continue
            
            should_close = False
            if mode == "heat" or action == "heating":
                should_close = room["delta"] < 0  # Above target
            elif mode == "cool" or action == "cooling":
                should_close = room["delta"] > 0  # Below target
            
            if should_close:
                if debug_mode:
                    _LOGGER.info(f"Closing {room['name']} vents to minimum (above/below target)")
                
                for vent_entity in room["vent_entities"]:
                    if self.hass.states.get(vent_entity) and self.hass.states.get(vent_entity).state != "unavailable":
                        try:
                            await self.hass.services.async_call(
                                "cover",
                                "set_cover_position",
                                {"entity_id": vent_entity, "position": min_other}
                            )
                        except Exception as e:
                            if debug_mode:
                                _LOGGER.warning(f"Error closing vent {vent_entity}: {e}")
    
    async def _enforce_relief_rule(
        self, all_vent_entities: list[str], rooms_data: list[dict], 
        selected_list: list[str], mode: str, action: str,
        close_thr: int, relief_pct: int, max_relief: int, debug_mode: bool
    ):
        """Enforce ≤ 1/3 closed rule with relief."""
        # Count closed vents
        closed_count = 0
        total_vents = len(all_vent_entities)
        
        for vent_entity in all_vent_entities:
            if validate_entity_state(self.hass, vent_entity, "cover"):
                position = get_safe_attribute(self.hass, vent_entity, "current_position", 100)
                position_int = safe_int(position, 100, 0, 100)
                if position_int <= close_thr:
                    closed_count += 1
        
        max_closed = total_vents // 3
        
        if debug_mode:
            _LOGGER.info(
                f"Relief check - Closed={closed_count}, Max={max_closed}, "
                f"Relief candidates={len([r for r in rooms_data if r['key'] not in selected_list])}"
            )
        
        if closed_count <= max_closed or total_vents == 0:
            return
        
        # Get relief candidates
        relief_candidates = []
        for room in rooms_data:
            if room["key"] in selected_list:
                continue
            
            # Filter by mode
            if mode == "heat" or action == "heating":
                if room["delta"] >= 0:  # At or below target
                    relief_candidates.append(room)
            elif mode == "cool" or action == "cooling":
                if room["delta"] <= 0:  # At or above target
                    relief_candidates.append(room)
            else:
                relief_candidates.append(room)
        
        if not relief_candidates:
            return
        
        # Score and sort relief candidates
        scored = []
        for room in relief_candidates:
            occ_rank = 1 if room["occupied"] else 0
            priority_rank = room["priority"]
            
            if mode == "heat" or action == "heating":
                temp_rank = -room["delta"]  # Prefer rooms furthest below target
            elif mode == "cool" or action == "cooling":
                temp_rank = room["delta"]  # Prefer rooms furthest above target
            else:
                temp_rank = abs(room["delta"])
            
            score = (occ_rank * 10000) + (priority_rank * 100) + temp_rank
            scored.append({"room": room, "score": score})
        
        # Sort by score (highest first) and limit
        scored.sort(key=lambda x: x["score"], reverse=True)
        relief_rooms = [s["room"] for s in scored[:max_relief]]
        
        if debug_mode:
            _LOGGER.info(
                f"Opening relief vents. Need {closed_count - max_closed} more open. "
                f"Relief rooms: {','.join([r['name'] for r in relief_rooms])}"
            )
        
        # Open relief vents with batching
        async with ServiceCallBatcher(self.hass, batch_size=5) as batcher:
            for relief_room in relief_rooms:
                if debug_mode:
                    _LOGGER.info(f"Opening relief vents for {relief_room['name']} to {relief_pct}%")
                
                for vent_entity in relief_room.get("vent_entities", []):
                    if not validate_entity_state(self.hass, vent_entity, "cover"):
                        if debug_mode:
                            _LOGGER.debug(f"Skipping unavailable relief vent {vent_entity}")
                        continue
                    
                    if not validate_vent_position(relief_pct):
                        _LOGGER.warning(f"Invalid relief position {relief_pct} for {vent_entity}, skipping")
                        continue
                    
                    # Add to batch
                    await batcher.add_call(
                        "cover",
                        "set_cover_position",
                        {"entity_id": vent_entity, "position": relief_pct}
                    )
            
            # Flush batch before checking state
            await batcher.flush()
            
            # Wait for state update
            await self.hass.async_block_till_done()
            import asyncio
            await asyncio.sleep(0.5)
            
            # Recheck closed count
            closed_now = 0
            for vent_entity in all_vent_entities:
                if validate_entity_state(self.hass, vent_entity, "cover"):
                    position = get_safe_attribute(self.hass, vent_entity, "current_position", 100)
                    position_int = safe_int(position, 100, 0, 100)
                    if position_int <= close_thr:
                        closed_now += 1
            
            if debug_mode:
                _LOGGER.info(f"After relief - Closed={closed_now}, Max={max_closed}")
            
            if closed_now <= max_closed:
                if debug_mode:
                    _LOGGER.info("Relief complete. Closed count satisfied.")
                return


class ThermostatControlScript:
    """Script to control thermostat for multiple rooms."""
    
    def __init__(self, hass: HomeAssistant, entry):
        """Initialize the script."""
        self.hass = hass
        self.entry = entry
        self.error_recovery = ErrorRecovery(hass, entry)
    
    async def async_run(self, rooms_csv: str = None):
        """Run the thermostat control script."""
        try:
            # Check if thermostat control is enabled
            auto_control = self.entry.options.get("auto_thermostat_control", True)
            if not auto_control:
                if self.entry.options.get("debug_mode", False):
                    _LOGGER.info("Auto thermostat control disabled")
                return
            
            # Check error recovery
            if self.error_recovery.should_disable_component("thermostat_control"):
                _LOGGER.error(
                    "Thermostat control disabled due to repeated errors. "
                    "Check logs and fix issues, then restart Home Assistant."
                )
                return
            
            # Check manual override
            manual_override = await self._check_manual_override()
            if manual_override:
                if self.entry.options.get("debug_mode", False):
                    _LOGGER.info("Manual override detected. Skipping thermostat control.")
                return
            
            # Check cycle protection
            min_runtime = safe_int(self.entry.options.get("hvac_min_runtime_min", 10), 10, 0, 30)
            min_off_time = safe_int(self.entry.options.get("hvac_min_off_time_min", 5), 5, 0, 30)
            cycle_protection_enabled = min_runtime > 0 or min_off_time > 0
            
            if cycle_protection_enabled:
                can_change = await self._check_cycle_protection()
                if not can_change:
                    if self.entry.options.get("debug_mode", False):
                        _LOGGER.info("BLOCKED by cycle protection")
                    return
            
            # Parse selected rooms
            selected_list = self._parse_rooms_csv(rooms_csv or "")
            
            main_thermostat = self.entry.data.get("main_thermostat")
            if not validate_entity_state(self.hass, main_thermostat, "climate"):
                _LOGGER.error(f"Thermostat {main_thermostat} not found or unavailable")
                self.error_recovery.record_error("thermostat_control", EntityUnavailableError(f"Thermostat {main_thermostat} unavailable"))
                return
            
            thermostat_state = self.hass.states.get(main_thermostat)
            mode = thermostat_state.state if thermostat_state else "off"
            action = get_safe_attribute(self.hass, main_thermostat, "hvac_action", "idle")
            debug_mode = self.entry.options.get("debug_mode", False)
            
            if debug_mode:
                _LOGGER.info(
                    f"Thermostat Control: Mode={mode}, Action={action}, "
                    f"Selected={','.join(selected_list)}"
                )
            
            # Handle empty selected list
            if not selected_list:
                default_temp = safe_int(self.entry.options.get("default_thermostat_temp", 72), 72, 65, 80)
                if debug_mode:
                    _LOGGER.info(f"No rooms need conditioning. Resetting to default {default_temp}°F")
                
                success = await safe_service_call(
                    self.hass,
                    "climate",
                    "set_temperature",
                    {"entity_id": main_thermostat, "temperature": default_temp},
                    max_retries=2
                )
                
                if success:
                    # Update last setpoint
                    await safe_service_call(
                        self.hass,
                        "input_number",
                        "set_value",
                        {
                            "entity_id": "input_number.last_thermostat_setpoint",
                            "value": default_temp
                        },
                        max_retries=1
                    )
                else:
                    _LOGGER.error(f"Failed to set thermostat to default {default_temp}°F")
                    self.error_recovery.record_error("thermostat_control", ServiceCallError("Failed to set default temperature"))
                
                return
            
            # Get room targets
            rooms_config = self.entry.data.get("rooms", [])
            room_targets = []
            
            for room_config in rooms_config:
                room_key = room_config.get("name", "").lower().replace(" ", "_")
                if room_key not in selected_list:
                    continue
                
                climate_entity = room_config.get("climate_entity")
                if climate_entity and validate_entity_state(self.hass, climate_entity, "climate"):
                    temp = get_safe_attribute(self.hass, climate_entity, "temperature")
                    if temp is not None:
                        temp_float = safe_float(temp, min_val=40.0, max_val=100.0)
                        if temp_float > 0:
                            room_targets.append(temp_float)
                    else:
                        lo = get_safe_attribute(self.hass, climate_entity, "target_temp_low")
                        hi = get_safe_attribute(self.hass, climate_entity, "target_temp_high")
                        if lo is not None and hi is not None:
                            lo_float = safe_float(lo, min_val=40.0, max_val=100.0)
                            hi_float = safe_float(hi, min_val=40.0, max_val=100.0)
                            if lo_float > 0 and hi_float > 0:
                                room_targets.append((lo_float + hi_float) / 2)
        
            if not room_targets:
                _LOGGER.warning("No valid room targets found. Cannot set thermostat.")
                return
            
            # Calculate setpoints based on mode
            if mode == "heat" or action == "heating":
                heat_target = max(room_targets)
                boost_enabled = self.entry.options.get("heat_boost_enabled", True)
                boost = safe_float(self.entry.options.get("heat_boost_f", 0.0), 0.0, 0.0, 3.0) if boost_enabled else 0.0
                new_setpoint = safe_float(heat_target + boost, min_val=40.0, max_val=100.0)
                
                if debug_mode:
                    _LOGGER.info(
                        f"Setting HEAT to {new_setpoint}°F "
                        f"(target={heat_target}°F, boost={boost}°F)"
                    )
                
                success = await safe_service_call(
                    self.hass,
                    "climate",
                    "set_temperature",
                    {"entity_id": main_thermostat, "temperature": new_setpoint},
                    max_retries=2
                )
                
                if success:
                    await safe_service_call(
                        self.hass,
                        "input_number",
                        "set_value",
                        {
                            "entity_id": "input_number.last_thermostat_setpoint",
                            "value": new_setpoint
                        },
                        max_retries=1
                    )
                else:
                    _LOGGER.error(f"Failed to set thermostat to {new_setpoint}°F")
                    self.error_recovery.record_error("thermostat_control", ServiceCallError("Failed to set heat temperature"))
        
            elif mode == "cool" or action == "cooling":
                cool_target = safe_float(min(room_targets), min_val=40.0, max_val=100.0)
                
                if debug_mode:
                    _LOGGER.info(f"Setting COOL to {cool_target}°F")
                
                success = await safe_service_call(
                    self.hass,
                    "climate",
                    "set_temperature",
                    {"entity_id": main_thermostat, "temperature": cool_target},
                    max_retries=2
                )
                
                if success:
                    await safe_service_call(
                        self.hass,
                        "input_number",
                        "set_value",
                        {
                            "entity_id": "input_number.last_thermostat_setpoint",
                            "value": cool_target
                        },
                        max_retries=1
                    )
                else:
                    _LOGGER.error(f"Failed to set thermostat to {cool_target}°F")
                    self.error_recovery.record_error("thermostat_control", ServiceCallError("Failed to set cool temperature"))
            
            elif mode in ["auto", "heat_cool"]:
                heat_target = max(room_targets)
                cool_target = min(room_targets)
                boost_enabled = self.entry.options.get("heat_boost_enabled", True)
                boost = safe_float(self.entry.options.get("heat_boost_f", 0.0), 0.0, 0.0, 3.0) if boost_enabled else 0.0
                lo = safe_float(heat_target + boost, min_val=40.0, max_val=100.0)
                hi = safe_float(cool_target, min_val=40.0, max_val=100.0)
                
                if debug_mode:
                    _LOGGER.info(
                        f"Setting AUTO/HEAT_COOL to {lo}°F-{hi}°F "
                        f"(heat={heat_target}°F, cool={cool_target}°F, boost={boost}°F)"
                    )
                
                success = await safe_service_call(
                    self.hass,
                    "climate",
                    "set_temperature",
                    {
                        "entity_id": main_thermostat,
                        "target_temp_low": lo,
                        "target_temp_high": hi
                    },
                    max_retries=2
                )
                
                if success:
                    await safe_service_call(
                        self.hass,
                        "input_number",
                        "set_value",
                        {
                            "entity_id": "input_number.last_thermostat_setpoint",
                            "value": (lo + hi) / 2
                        },
                        max_retries=1
                    )
                else:
                    _LOGGER.error(f"Failed to set thermostat to {lo}°F-{hi}°F")
                    self.error_recovery.record_error("thermostat_control", ServiceCallError("Failed to set auto temperature"))
            
            # Reset error count on success
            self.error_recovery.reset_errors("thermostat_control")
            
        except Exception as e:
            _LOGGER.error(f"Error in thermostat control script: {e}", exc_info=True)
            self.error_recovery.record_error("thermostat_control", e)
            raise
    
    def _parse_rooms_csv(self, rooms_csv: str) -> list[str]:
        """Parse comma-separated room list."""
        if not rooms_csv or rooms_csv.strip() in ["", "none"]:
            return []
        
        rooms = self.entry.data.get("rooms", [])
        valid_keys = [
            room.get("name", "").lower().replace(" ", "_")
            for room in rooms
        ]
        
        parts = [p.strip() for p in rooms_csv.split(",") if p.strip()]
        filtered = [p for p in parts if p in valid_keys]
        
        return filtered
    
    async def _check_manual_override(self) -> bool:
        """Check if manual override is active."""
        main_thermostat = self.entry.data.get("main_thermostat")
        thermostat = self.hass.states.get(main_thermostat)
        if not thermostat:
            return False
        
        current_temp = thermostat.attributes.get("temperature")
        if current_temp is None:
            return False
        
        last_setpoint_state = self.hass.states.get("input_number.last_thermostat_setpoint")
        if not last_setpoint_state or last_setpoint_state.state in ["unknown", "unavailable"]:
            # Try coordinator storage as fallback
            last = self.hass.data.get(DOMAIN, {}).get("last_thermostat_setpoint")
            if last is None:
                return False
        else:
            try:
                last = float(last_setpoint_state.state)
            except (ValueError, TypeError):
                return False
        
        try:
            current = float(current_temp)
            diff = abs(current - last)
            return diff > 0.5  # Tolerance
        except (ValueError, TypeError):
            return False
    
    async def _check_cycle_protection(self) -> bool:
        """Check if cycle protection allows setpoint changes."""
        main_thermostat = self.entry.data.get("main_thermostat")
        thermostat = self.hass.states.get(main_thermostat)
        if not thermostat:
            return True
        
        action = thermostat.attributes.get("hvac_action", "idle")
        min_runtime = self.entry.options.get("hvac_min_runtime_min", 10) * 60
        min_off_time = self.entry.options.get("hvac_min_off_time_min", 5) * 60
        
        if action in ["heating", "cooling"]:
            start_ts_state = self.hass.states.get("input_number.hvac_cycle_start_timestamp")
            if start_ts_state and start_ts_state.state not in ["unknown", "unavailable"]:
                try:
                    start_time = float(start_ts_state.state)
                    if start_time > 0:
                        runtime = (datetime.now().timestamp() - start_time)
                        return runtime >= min_runtime
                except (ValueError, TypeError):
                    pass
        elif action == "idle":
            end_ts_state = self.hass.states.get("input_number.hvac_cycle_end_timestamp")
            if end_ts_state and end_ts_state.state not in ["unknown", "unavailable"]:
                try:
                    end_time = float(end_ts_state.state)
                    if end_time > 0:
                        off_time = (datetime.now().timestamp() - end_time)
                        return off_time >= min_off_time
                except (ValueError, TypeError):
                    pass
        
        return True

