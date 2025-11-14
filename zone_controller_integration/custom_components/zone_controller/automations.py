"""Automation implementations for Smart Vent Controller."""

from typing import Any
from datetime import datetime
import logging

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change, async_track_time_interval
from homeassistant.const import EVENT_STATE_CHANGED

from .const import DOMAIN
from .scripts import VentControlScript, ThermostatControlScript

_LOGGER = logging.getLogger(__name__)


class SmartVentConditionerAutomation:
    """Main zone conditioner automation."""
    
    def __init__(self, hass: HomeAssistant, entry):
        """Initialize the automation."""
        self.hass = hass
        self.entry = entry
        self.vent_script = VentControlScript(hass, entry)
        self.thermostat_script = ThermostatControlScript(hass, entry)
        self._last_trigger_time = None
        self._unsubscribers = []
    
    async def async_setup(self):
        """Set up the automation."""
        # Get entities to track
        rooms = self.entry.data.get("rooms", [])
        main_thermostat = self.entry.data.get("main_thermostat")
        
        # Track climate entities
        climate_entities = []
        for room in rooms:
            climate_entity = room.get("climate_entity")
            if climate_entity:
                climate_entities.append(climate_entity)
        
        # Track occupancy sensors
        occ_sensors = []
        for room in rooms:
            occ_sensor = room.get("occupancy_sensor")
            if occ_sensor:
                occ_sensors.append(occ_sensor)
        
        # Track delta sensors (created by sensor platform)
        delta_sensors = []
        for room in rooms:
            room_key = room.get("name", "").lower().replace(" ", "_")
            delta_sensors.append(f"sensor.{room_key}_delta_degf")
        
        # Track thermostat
        all_entities = climate_entities + occ_sensors + delta_sensors
        if main_thermostat:
            all_entities.append(main_thermostat)
        
        # Set up state change listeners
        if all_entities:
            self._unsubscribers.append(
                async_track_state_change(
                    self.hass,
                    all_entities,
                    self._handle_state_change,
                    to_state=None,  # Track all changes
                )
            )
        
        # Set up periodic trigger (every 5 minutes)
        self._unsubscribers.append(
            async_track_time_interval(
                self.hass,
                self._handle_periodic,
                seconds=300  # 5 minutes
            )
        )
        
        _LOGGER.info("Smart Vent Controller automation set up and running")
    
    async def async_unload(self):
        """Unload the automation."""
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()
    
    @callback
    def _handle_state_change(self, entity_id, old_state, new_state):
        """Handle state change with debouncing."""
        if new_state is None:
            return
        
        # Check cooldown
        cooldown_sec = self.entry.options.get("automation_cooldown_sec", 30)
        if self._last_trigger_time:
            elapsed = (datetime.now() - self._last_trigger_time).total_seconds()
            if elapsed < cooldown_sec:
                return
        
        # Debounce: Cancel previous pending task if exists
        if hasattr(self, '_pending_task') and self._pending_task:
            self._pending_task.cancel()
        
        # Schedule with small delay to batch rapid changes
        import asyncio
        self._pending_task = self.hass.async_create_task(
            self._debounced_run_automation()
        )
    
    async def _debounced_run_automation(self):
        """Debounced automation run."""
        # Small delay to batch rapid state changes
        await asyncio.sleep(0.5)
        await self._run_automation()
    
    @callback
    def _handle_periodic(self, now):
        """Handle periodic trigger."""
        self.hass.async_create_task(self._run_automation())
    
    async def _run_automation(self):
        """Run the automation logic."""
        self._last_trigger_time = datetime.now()
        
        # Get rooms to condition
        rooms_to_condition = self.hass.states.get("sensor.rooms_to_condition")
        if not rooms_to_condition:
            return
        
        rooms_csv = rooms_to_condition.state
        if rooms_csv in ["", "none", "unknown", "unavailable"]:
            rooms_csv = ""
        
        # Run vent control
        auto_vent_control = self.entry.options.get("auto_vent_control", True)
        if auto_vent_control:
            try:
                await self.vent_script.async_run(rooms_csv)
            except Exception as e:
                _LOGGER.error(f"Error in vent control script: {e}", exc_info=True)
        
        # Run thermostat control
        auto_thermostat_control = self.entry.options.get("auto_thermostat_control", True)
        if auto_thermostat_control and rooms_csv:
            try:
                await self.thermostat_script.async_run(rooms_csv)
            except Exception as e:
                _LOGGER.error(f"Error in thermostat control script: {e}", exc_info=True)


class HVACCycleTrackingAutomation:
    """Automation to track HVAC cycle timing."""
    
    def __init__(self, hass: HomeAssistant, entry):
        """Initialize the automation."""
        self.hass = hass
        self.entry = entry
        self._unsubscribers = []
    
    async def async_setup(self):
        """Set up the automation."""
        main_thermostat = self.entry.data.get("main_thermostat")
        if not main_thermostat:
            return
        
        # Track thermostat hvac_action attribute changes
        self._unsubscribers.append(
            async_track_state_change(
                self.hass,
                main_thermostat,
                self._handle_hvac_action_change,
                to_state=None,
            )
        )
        
        _LOGGER.info("HVAC cycle tracking automation set up")
    
    async def async_unload(self):
        """Unload the automation."""
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()
    
    @callback
    def _handle_hvac_action_change(self, entity_id, old_state, new_state):
        """Handle HVAC action change."""
        if new_state is None:
            return
        
        old_action = old_state.attributes.get("hvac_action", "idle") if old_state else "idle"
        new_action = new_state.attributes.get("hvac_action", "idle")
        
        if old_action == new_action:
            return
        
        # Handle cycle start
        if old_action == "idle" and new_action in ["heating", "cooling"]:
            self.hass.async_create_task(self._handle_cycle_start(new_action))
        
        # Handle cycle end
        elif old_action in ["heating", "cooling"] and new_action == "idle":
            self.hass.async_create_task(self._handle_cycle_end())
    
    async def _handle_cycle_start(self, action: str):
        """Handle cycle start."""
        timestamp = datetime.now().timestamp()
        
        await self.hass.services.async_call(
            "input_number",
            "set_value",
            {
                "entity_id": "input_number.hvac_cycle_start_timestamp",
                "value": timestamp
            }
        )
        
        # Store in coordinator
        coordinator = self.hass.data.get(DOMAIN, {})
        if isinstance(coordinator, dict):
            coordinator["hvac_last_action"] = action
        elif hasattr(coordinator, "hvac_last_action"):
            coordinator.hvac_last_action = action
        
        _LOGGER.debug(f"HVAC cycle started: {action} at {timestamp}")
    
    async def _handle_cycle_end(self):
        """Handle cycle end."""
        timestamp = datetime.now().timestamp()
        
        await self.hass.services.async_call(
            "input_number",
            "set_value",
            {
                "entity_id": "input_number.hvac_cycle_end_timestamp",
                "value": timestamp
            }
        )
        
        _LOGGER.debug(f"HVAC cycle ended at {timestamp}")


class ClearManualOverrideAutomation:
    """Automation to clear manual override when cycle completes."""
    
    def __init__(self, hass: HomeAssistant, entry):
        """Initialize the automation."""
        self.hass = hass
        self.entry = entry
        self._unsubscribers = []
    
    async def async_setup(self):
        """Set up the automation."""
        main_thermostat = self.entry.data.get("main_thermostat")
        if not main_thermostat:
            return
        
        # Track when HVAC action returns to idle
        self._unsubscribers.append(
            async_track_state_change(
                self.hass,
                main_thermostat,
                self._handle_idle_transition,
                to_state=None,
            )
        )
        
        _LOGGER.info("Clear manual override automation set up")
    
    async def async_unload(self):
        """Unload the automation."""
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()
    
    @callback
    def _handle_idle_transition(self, entity_id, old_state, new_state):
        """Handle transition to idle."""
        if new_state is None:
            return
        
        old_action = old_state.attributes.get("hvac_action", "idle") if old_state else "idle"
        new_action = new_state.attributes.get("hvac_action", "idle")
        
        # Only clear if transitioning from heating/cooling to idle
        if old_action in ["heating", "cooling"] and new_action == "idle":
            self.hass.async_create_task(self._clear_override())
    
    async def _clear_override(self):
        """Clear manual override."""
        main_thermostat = self.entry.data.get("main_thermostat")
        thermostat = self.hass.states.get(main_thermostat)
        if not thermostat:
            return
        
        current_temp = thermostat.attributes.get("temperature")
        if current_temp is None:
            return
        
        # Update last setpoint to current
        await self.hass.services.async_call(
            "input_number",
            "set_value",
            {
                "entity_id": "input_number.last_thermostat_setpoint",
                "value": float(current_temp)
            }
        )
        
        _LOGGER.info("Manual override cleared after cycle completion. Resuming auto control.")

