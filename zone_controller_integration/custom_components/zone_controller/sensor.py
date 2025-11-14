"""Sensor platform for Smart Vent Controller."""

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.template import Template
from homeassistant.const import UnitOfTemperature

from .const import DOMAIN
from .coordinator import SmartVentControllerCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Smart Vent Controller sensors."""
    coordinator: SmartVentControllerCoordinator = hass.data[DOMAIN][entry.entry_id]
    rooms = entry.data.get("rooms", [])
    
    entities = []
    
    # Create temperature sensors for each room
    for room in rooms:
        room_name = room.get("name", "")
        room_key = room_name.lower().replace(" ", "_")
        climate_entity = room.get("climate_entity")
        temp_sensor = room.get("temp_sensor", "")
        
        # Room temperature sensor
        entities.append(
            RoomTemperatureSensor(coordinator, entry, room_key, room_name, climate_entity, temp_sensor)
        )
        
        # Room target sensor
        entities.append(
            RoomTargetSensor(coordinator, entry, room_key, room_name, climate_entity)
        )
        
        # Room delta sensor
        entities.append(
            RoomDeltaSensor(coordinator, entry, room_key, room_name, climate_entity, temp_sensor)
        )
    
    # Multi-room selection sensor
    entities.append(RoomsToConditionSensor(coordinator, entry))
    
    # HVAC cycle protection sensors
    entities.append(HVACCycleProtectionSensor(coordinator, entry))
    entities.append(HVACCycleStartTimeSensor(coordinator, entry))
    entities.append(HVACCycleEndTimeSensor(coordinator, entry))
    
    # Statistics sensor
    entities.append(ZoneControllerStatsSensor(coordinator, entry))
    
    async_add_entities(entities)


class RoomTemperatureSensor(SensorEntity):
    """Sensor for room current temperature."""
    
    _attr_device_class = "temperature"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.FAHRENHEIT
    
    def __init__(self, coordinator, entry, room_key, room_name, climate_entity, temp_sensor):
        """Initialize the sensor."""
        self.coordinator = coordinator
        self._entry = entry
        self._room_key = room_key
        self._room_name = room_name
        self._climate_entity = climate_entity
        self._temp_sensor = temp_sensor
        self._attr_unique_id = f"{room_key}_temp_degf"
        self._attr_name = f"{room_name} Temp (°F)"
        self._attr_icon = "mdi:thermometer"
    
    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={get_room_device_id(self._entry, self._room_key)},
            name=f"{self._room_name} Zone",
            manufacturer="Smart Vent Controller",
            model="Room Controller",
        )
    
    @property
    def native_value(self):
        """Return the current temperature."""
        # Try temp sensor first
        if self._temp_sensor:
            state = self.coordinator.hass.states.get(self._temp_sensor)
            if state and state.state not in ["unknown", "unavailable", "None", "none"]:
                try:
                    return float(state.state)
                except (ValueError, TypeError):
                    pass
        
        # Fallback to climate entity
        if self._climate_entity:
            climate = self.coordinator.hass.states.get(self._climate_entity)
            if climate:
                temp = climate.attributes.get("current_temperature")
                if temp is not None:
                    return float(temp)
        
        return None


class RoomTargetSensor(SensorEntity):
    """Sensor for room target temperature."""
    
    _attr_device_class = "temperature"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.FAHRENHEIT
    
    def __init__(self, coordinator, entry, room_key, room_name, climate_entity):
        """Initialize the sensor."""
        self.coordinator = coordinator
        self._entry = entry
        self._room_key = room_key
        self._room_name = room_name
        self._climate_entity = climate_entity
        self._attr_unique_id = f"{room_key}_target_degf"
        self._attr_name = f"{room_name} Target (°F)"
        self._attr_icon = "mdi:target"
    
    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={get_room_device_id(self._entry, self._room_key)},
            name=f"{self._room_name} Zone",
            manufacturer="Smart Vent Controller",
            model="Room Controller",
        )
    
    @property
    def native_value(self):
        """Return the target temperature."""
        if self._climate_entity:
            climate = self.coordinator.hass.states.get(self._climate_entity)
            if climate:
                temp = climate.attributes.get("temperature")
                if temp is not None:
                    return float(temp)
                
                # Try target_temp_low/high for AUTO mode
                lo = climate.attributes.get("target_temp_low")
                hi = climate.attributes.get("target_temp_high")
                if lo is not None and hi is not None:
                    return (float(lo) + float(hi)) / 2
        
        return None


class RoomDeltaSensor(SensorEntity):
    """Sensor for room temperature delta (target - current)."""
    
    _attr_device_class = "temperature"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.FAHRENHEIT
    
    def __init__(self, coordinator, entry, room_key, room_name, climate_entity, temp_sensor):
        """Initialize the sensor."""
        self.coordinator = coordinator
        self._entry = entry
        self._room_key = room_key
        self._room_name = room_name
        self._climate_entity = climate_entity
        self._temp_sensor = temp_sensor
        self._attr_unique_id = f"{room_key}_delta_degf"
        self._attr_name = f"{room_name} Delta (°F)"
        self._attr_icon = "mdi:delta"
    
    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={get_room_device_id(self._entry, self._room_key)},
            name=f"{self._room_name} Zone",
            manufacturer="Smart Vent Controller",
            model="Room Controller",
        )
    
    @property
    def native_value(self):
        """Return the temperature delta."""
        # Get target
        target = None
        if self._climate_entity:
            climate = self.coordinator.hass.states.get(self._climate_entity)
            if climate:
                temp = climate.attributes.get("temperature")
                if temp is not None:
                    target = float(temp)
                else:
                    lo = climate.attributes.get("target_temp_low")
                    hi = climate.attributes.get("target_temp_high")
                    if lo is not None and hi is not None:
                        target = (float(lo) + float(hi)) / 2
        
        # Get current
        current = None
        if self._temp_sensor:
            state = self.coordinator.hass.states.get(self._temp_sensor)
            if state and state.state not in ["unknown", "unavailable", "None", "none"]:
                try:
                    current = float(state.state)
                except (ValueError, TypeError):
                    pass
        
        if current is None and self._climate_entity:
            climate = self.coordinator.hass.states.get(self._climate_entity)
            if climate:
                temp = climate.attributes.get("current_temperature")
                if temp is not None:
                    current = float(temp)
        
        if target is not None and current is not None:
            return target - current
        
        return None


class RoomsToConditionSensor(SensorEntity):
    """Sensor that determines which rooms need conditioning."""
    
    _attr_icon = "mdi:home-thermometer-outline"
    
    def __init__(self, coordinator, entry):
        """Initialize the sensor."""
        self.coordinator = coordinator
        self._entry = entry
        self._attr_unique_id = "rooms_to_condition"
        self._attr_name = "Rooms To Condition"
    
    @property
    def native_value(self):
        """Return comma-separated list of rooms needing conditioning."""
        rooms = self._entry.data.get("rooms", [])
        main_thermostat = self._entry.data.get("main_thermostat")
        hysteresis = self._entry.options.get("room_hysteresis_f", 1.0)
        require_occupancy = self._entry.options.get("require_occupancy", True)
        
        if not main_thermostat:
            return "none"
        
        thermostat = self.coordinator.hass.states.get(main_thermostat)
        if not thermostat:
            return "none"
        
        mode = thermostat.state
        if mode not in ["heat", "cool", "auto", "heat_cool"]:
            return "none"
        
        rooms_to_condition = []
        
        for room in rooms:
            room_key = room.get("name", "").lower().replace(" ", "_")
            climate_entity = room.get("climate_entity")
            temp_sensor = room.get("temp_sensor", "")
            occ_sensor = room.get("occupancy_sensor", "")
            
            # Get current temperature
            current_temp = None
            if temp_sensor:
                state = self.coordinator.hass.states.get(temp_sensor)
                if state and state.state not in ["unknown", "unavailable"]:
                    try:
                        current_temp = float(state.state)
                    except (ValueError, TypeError):
                        pass
            
            if current_temp is None and climate_entity:
                climate = self.coordinator.hass.states.get(climate_entity)
                if climate:
                    temp = climate.attributes.get("current_temperature")
                    if temp is not None:
                        current_temp = float(temp)
            
            # Validate temperature
            if current_temp is None or current_temp < 40 or current_temp > 100:
                continue
            
            # Get target
            target_temp = None
            if climate_entity:
                climate = self.coordinator.hass.states.get(climate_entity)
                if climate:
                    temp = climate.attributes.get("temperature")
                    if temp is not None:
                        target_temp = float(temp)
                    else:
                        lo = climate.attributes.get("target_temp_low")
                        hi = climate.attributes.get("target_temp_high")
                        if lo is not None and hi is not None:
                            target_temp = (float(lo) + float(hi)) / 2
            
            if target_temp is None:
                continue
            
            # Calculate delta
            delta = target_temp - current_temp
            
            # Check occupancy if required
            if require_occupancy and occ_sensor:
                occ_state = self.coordinator.hass.states.get(occ_sensor)
                if not occ_state or occ_state.state != "on":
                    continue
            
            # Check if room needs conditioning
            if mode in ["heat", "auto", "heat_cool"] and delta > hysteresis:
                rooms_to_condition.append(room_key)
            elif mode in ["cool", "auto", "heat_cool"] and delta < -hysteresis:
                rooms_to_condition.append(room_key)
        
        return ",".join(rooms_to_condition) if rooms_to_condition else "none"


class HVACCycleProtectionSensor(SensorEntity):
    """Sensor for HVAC cycle protection status."""
    
    _attr_icon = "mdi:shield-check"
    
    def __init__(self, coordinator, entry):
        """Initialize the sensor."""
        self.coordinator = coordinator
        self._entry = entry
        self._attr_unique_id = "hvac_cycle_protection_status"
        self._attr_name = "HVAC Cycle Protection Status"
    
    @property
    def native_value(self):
        """Return protection status."""
        main_thermostat = self._entry.data.get("main_thermostat")
        if not main_thermostat:
            return "allowed"
        
        thermostat = self.coordinator.hass.states.get(main_thermostat)
        if not thermostat:
            return "allowed"
        
        action = thermostat.attributes.get("hvac_action", "idle")
        min_runtime = self._entry.options.get("hvac_min_runtime_min", 10) * 60
        min_off_time = self._entry.options.get("hvac_min_off_time_min", 5) * 60
        
        if action in ["heating", "cooling"]:
            # Check runtime
            start_ts = self.coordinator.hass.states.get("input_number.hvac_cycle_start_timestamp")
            if start_ts:
                try:
                    start_time = float(start_ts.state)
                    if start_time > 0:
                        from datetime import datetime
                        runtime = (datetime.now().timestamp() - start_time)
                        if runtime < min_runtime:
                            return "protected"
                except (ValueError, TypeError):
                    pass
        elif action == "idle":
            # Check off time
            end_ts = self.coordinator.hass.states.get("input_number.hvac_cycle_end_timestamp")
            if end_ts:
                try:
                    end_time = float(end_ts.state)
                    if end_time > 0:
                        from datetime import datetime
                        off_time = (datetime.now().timestamp() - end_time)
                        if off_time < min_off_time:
                            return "protected"
                except (ValueError, TypeError):
                    pass
        
        return "allowed"


class HVACCycleStartTimeSensor(SensorEntity):
    """Sensor for HVAC cycle start timestamp."""
    
    _attr_icon = "mdi:clock-start"
    
    def __init__(self, coordinator, entry):
        """Initialize the sensor."""
        self.coordinator = coordinator
        self._entry = entry
        self._attr_unique_id = "hvac_cycle_start_time"
        self._attr_name = "HVAC Cycle Start Time"
    
    @property
    def native_value(self):
        """Return start timestamp."""
        start_ts = self.coordinator.hass.states.get("input_number.hvac_cycle_start_timestamp")
        if start_ts:
            try:
                return float(start_ts.state)
            except (ValueError, TypeError):
                pass
        return 0


class HVACCycleEndTimeSensor(SensorEntity):
    """Sensor for HVAC cycle end timestamp."""
    
    _attr_icon = "mdi:clock-end"
    
    def __init__(self, coordinator, entry):
        """Initialize the sensor."""
        self.coordinator = coordinator
        self._entry = entry
        self._attr_unique_id = "hvac_cycle_end_time"
        self._attr_name = "HVAC Cycle End Time"
    
    @property
    def native_value(self):
        """Return end timestamp."""
        end_ts = self.coordinator.hass.states.get("input_number.hvac_cycle_end_timestamp")
        if end_ts:
            try:
                return float(end_ts.state)
            except (ValueError, TypeError):
                pass
        return 0


class ZoneControllerStatsSensor(SensorEntity):
    """Sensor for Smart Vent Controller statistics."""
    
    _attr_icon = "mdi:chart-line"
    
    def __init__(self, coordinator, entry):
        """Initialize the sensor."""
        self.coordinator = coordinator
        self._entry = entry
        self._attr_unique_id = "smart_vent_controller_stats"
        self._attr_name = "Smart Vent Controller Statistics"
    
    @property
    def native_value(self):
        """Return current rooms to condition."""
        rooms_to_condition = self.coordinator.hass.states.get("sensor.rooms_to_condition")
        if rooms_to_condition:
            return rooms_to_condition.state
        return "none"
    
    @property
    def extra_state_attributes(self):
        """Return additional attributes."""
        rooms_to_condition = self.coordinator.hass.states.get("sensor.rooms_to_condition")
        rooms_count = 0
        if rooms_to_condition and rooms_to_condition.state != "none":
            rooms_list = rooms_to_condition.state.split(",")
            rooms_count = len([r for r in rooms_list if r and r != "none"])
        
        return {
            "rooms_selected_count": rooms_count,
            "total_rooms": len(self._entry.data.get("rooms", [])),
            "automation_enabled": (
                self._entry.options.get("auto_vent_control", True) and
                self._entry.options.get("auto_thermostat_control", True)
            ),
        }

