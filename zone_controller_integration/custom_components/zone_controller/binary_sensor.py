"""Binary sensor platform for Smart Vent Controller."""

from datetime import datetime, time
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import SmartVentControllerCoordinator
from .device import get_room_device_id
from homeassistant.helpers.device_registry import DeviceInfo


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Smart Vent Controller binary sensors."""
    coordinator: SmartVentControllerCoordinator = hass.data[DOMAIN][entry.entry_id]
    rooms = entry.data.get("rooms", [])
    
    entities = []
    
    # Create occupancy sensors for each room
    for room in rooms:
        room_name = room.get("name", "")
        room_key = room_name.lower().replace(" ", "_")
        occ_sensor = room.get("occupancy_sensor", "")
        
        if occ_sensor:
            entities.append(
                RoomOccupiedRecentSensor(
                    coordinator, 
                    entry,
                    room_key, 
                    room_name, 
                    occ_sensor
                )
            )
    
    # Manual override sensor
    entities.append(ThermostatManualOverrideSensor(coordinator, entry))
    
    async_add_entities(entities)


class RoomOccupiedRecentSensor(BinarySensorEntity):
    """Binary sensor for recent room occupancy."""
    
    _attr_icon = "mdi:account-eye"
    
    def __init__(self, coordinator, entry, room_key, room_name, occ_sensor):
        """Initialize the sensor."""
        self.coordinator = coordinator
        self._entry = entry
        self._room_key = room_key
        self._room_name = room_name
        self._occ_sensor = occ_sensor
        self._attr_unique_id = f"{room_key}_occupied_recent"
        self._attr_name = f"{room_name} Occupied Recent"
    
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
    def is_on(self):
        """Return True if room was recently occupied."""
        occ_state = self.coordinator.hass.states.get(self._occ_sensor)
        if not occ_state or occ_state.state != "on":
            return False
        
        # Check if we're in night hours (22:00 - 06:00)
        now = datetime.now().time()
        is_night = time(22, 0) <= now or now <= time(6, 0)
        
        # Get linger time
        if is_night:
            linger_min = self._entry.options.get("occupancy_linger_night_min", 60)
        else:
            linger_min = self._entry.options.get("occupancy_linger_min", 30)
        
        # Check last changed time
        last_changed = occ_state.last_changed
        if last_changed:
            elapsed = (datetime.now() - last_changed).total_seconds() / 60
            return elapsed <= linger_min
        
        return False


class ThermostatManualOverrideSensor(BinarySensorEntity):
    """Binary sensor for manual thermostat override detection."""
    
    _attr_icon = "mdi:hand-back-left"
    
    def __init__(self, coordinator, entry):
        """Initialize the sensor."""
        self.coordinator = coordinator
        self._entry = entry
        self._attr_unique_id = "thermostat_manual_override"
        self._attr_name = "Thermostat Manual Override Detected"
    
    @property
    def is_on(self):
        """Return True if manual override detected."""
        main_thermostat = self._entry.data.get("main_thermostat")
        if not main_thermostat:
            return False
        
        auto_enabled = self._entry.options.get("auto_thermostat_control", True)
        if not auto_enabled:
            return False
        
        thermostat = self.coordinator.hass.states.get(main_thermostat)
        if not thermostat:
            return False
        
        current_temp = thermostat.attributes.get("temperature")
        if current_temp is None:
            return False
        
        last_setpoint = self.coordinator.hass.states.get("input_number.last_thermostat_setpoint")
        if not last_setpoint:
            return False
        
        try:
            current = float(current_temp)
            last = float(last_setpoint.state)
            diff = abs(current - last)
            return diff > 0.5  # Tolerance for floating point
        except (ValueError, TypeError):
            return False
    
    @property
    def extra_state_attributes(self):
        """Return additional attributes."""
        main_thermostat = self._entry.data.get("main_thermostat")
        if not main_thermostat:
            return {}
        
        thermostat = self.coordinator.hass.states.get(main_thermostat)
        if not thermostat:
            return {}
        
        current_temp = thermostat.attributes.get("temperature", 0)
        last_setpoint = self.coordinator.hass.states.get("input_number.last_thermostat_setpoint")
        last = float(last_setpoint.state) if last_setpoint else 0
        
        return {
            "current_setpoint": current_temp,
            "last_automation_setpoint": last,
            "difference": abs(float(current_temp) - last) if current_temp else 0,
        }

