"""Number platform for Zone Controller."""

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN
from .coordinator import ZoneControllerCoordinator
from .device import get_room_device_id


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Zone Controller number entities."""
    coordinator: ZoneControllerCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = []
    
    # Configuration numbers
    entities.extend([
        ConfigNumber(
            coordinator,
            entry,
            "min_other_room_open_pct",
            "Minimum Other Room Open %",
            "mdi:air-conditioner",
            0, 100, 1, 20, "%"
        ),
        ConfigNumber(
            coordinator,
            entry,
            "closed_threshold_pct",
            "Closed Threshold %",
            "mdi:air-conditioner",
            0, 100, 1, 10, "%"
        ),
        ConfigNumber(
            coordinator,
            entry,
            "relief_open_pct",
            "Relief Open %",
            "mdi:fan",
            0, 100, 1, 60, "%"
        ),
        ConfigNumber(
            coordinator,
            entry,
            "max_relief_rooms",
            "Max Relief Rooms",
            "mdi:fan-alert",
            1, 10, 1, 3, "rooms"
        ),
        ConfigNumber(
            coordinator,
            entry,
            "room_hysteresis_f",
            "Room Hysteresis (°F)",
            "mdi:thermometer",
            0, 5, 0.1, 1.0, "°F"
        ),
        ConfigNumber(
            coordinator,
            entry,
            "occupancy_linger_min",
            "Occupancy Linger (day, min)",
            "mdi:timer",
            0, 300, 1, 30, "min"
        ),
        ConfigNumber(
            coordinator,
            entry,
            "occupancy_linger_night_min",
            "Occupancy Linger (night, min)",
            "mdi:timer-sand",
            0, 300, 1, 60, "min"
        ),
        ConfigNumber(
            coordinator,
            entry,
            "heat_boost_f",
            "Heat Boost (°F)",
            "mdi:thermometer-plus",
            0, 3, 0.5, 1.0, "°F"
        ),
        ConfigNumber(
            coordinator,
            entry,
            "hvac_min_runtime_min",
            "HVAC Minimum Runtime (min)",
            "mdi:timer-play-outline",
            0, 30, 1, 10, "min"
        ),
        ConfigNumber(
            coordinator,
            entry,
            "hvac_min_off_time_min",
            "HVAC Minimum Off Time (min)",
            "mdi:timer-off-outline",
            0, 30, 1, 5, "min"
        ),
        ConfigNumber(
            coordinator,
            entry,
            "default_thermostat_temp",
            "Default Thermostat Temp (°F)",
            "mdi:thermometer",
            65, 80, 1, 72, "°F"
        ),
        ConfigNumber(
            coordinator,
            entry,
            "automation_cooldown_sec",
            "Automation Cooldown (sec)",
            "mdi:timer-outline",
            0, 300, 5, 30, "s"
        ),
    ])
    
    # Room priority numbers
    rooms = entry.data.get("rooms", [])
    for room in rooms:
        room_name = room.get("name", "")
        room_key = room_name.lower().replace(" ", "_")
        entities.append(
            RoomPriorityNumber(
                coordinator,
                entry,
                room_key,
                room_name,
                room.get("priority", 5)
            )
        )
    
    # Internal tracking numbers
    entities.extend([
        InternalNumber(
            coordinator,
            entry,
            "last_thermostat_setpoint",
            "Last Thermostat Setpoint (Internal)",
            "mdi:thermostat",
            40, 100, 0.5, 72, "°F"
        ),
        InternalNumber(
            coordinator,
            entry,
            "hvac_cycle_start_timestamp",
            "HVAC Cycle Start Timestamp (Internal)",
            "mdi:clock-start",
            0, 9999999999, 1, 0, None
        ),
        InternalNumber(
            coordinator,
            entry,
            "hvac_cycle_end_timestamp",
            "HVAC Cycle End Timestamp (Internal)",
            "mdi:clock-end",
            0, 9999999999, 1, 0, None
        ),
    ])
    
    async_add_entities(entities)


class ConfigNumber(NumberEntity, RestoreEntity):
    """Configuration number entity."""
    
    _attr_mode = NumberMode.BOX
    
    def __init__(self, coordinator, entry, key, name, icon, min_val, max_val, step, default, unit):
        """Initialize the number."""
        self.coordinator = coordinator
        self._entry = entry
        self._key = key
        self._attr_unique_id = key
        self._attr_name = name
        self._attr_icon = icon
        self._attr_native_min_value = min_val
        self._attr_native_max_value = max_val
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit
        self._default = default
    
    @property
    def native_value(self):
        """Return the current value."""
        # Try options first, then fallback to default
        return self._entry.options.get(self._key, self._default)
    
    async def async_set_native_value(self, value: float) -> None:
        """Update the value."""
        # Update options
        options = dict(self._entry.options or {})
        options[self._key] = value
        
        self.coordinator.hass.config_entries.async_update_entry(
            self._entry, options=options
        )
        self.async_write_ha_state()


class RoomPriorityNumber(NumberEntity, RestoreEntity):
    """Room priority number entity."""
    
    _attr_mode = NumberMode.SLIDER
    _attr_native_min_value = 0
    _attr_native_max_value = 10
    _attr_native_step = 1
    
    def __init__(self, coordinator, entry, room_key, room_name, default_priority):
        """Initialize the number."""
        self.coordinator = coordinator
        self._entry = entry
        self._room_key = room_key
        self._room_name = room_name
        self._attr_unique_id = f"{room_key}_priority"
        self._attr_name = f"{room_name} Priority"
        self._attr_icon = "mdi:star"
        self._default = default_priority
    
    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={get_room_device_id(self._entry, self._room_key)},
            name=f"{self._room_name} Zone",
            manufacturer="Zone Controller",
            model="Room Controller",
        )
    
    @property
    def native_value(self):
        """Return the current priority."""
        # Get from room config or options
        rooms = self._entry.data.get("rooms", [])
        for room in rooms:
            if room.get("name", "").lower().replace(" ", "_") == self._room_key:
                return room.get("priority", self._default)
        return self._default
    
    async def async_set_native_value(self, value: float) -> None:
        """Update the priority."""
        # Update room config
        rooms = list(self._entry.data.get("rooms", []))
        for i, room in enumerate(rooms):
            if room.get("name", "").lower().replace(" ", "_") == self._room_key:
                rooms[i] = {**room, "priority": int(value)}
                break
        
        data = dict(self._entry.data)
        data["rooms"] = rooms
        
        self.coordinator.hass.config_entries.async_update_entry(
            self._entry, data=data
        )
        self.async_write_ha_state()


class InternalNumber(NumberEntity, RestoreEntity):
    """Internal tracking number entity."""
    
    _attr_mode = NumberMode.BOX
    
    def __init__(self, coordinator, entry, key, name, icon, min_val, max_val, step, default, unit):
        """Initialize the number."""
        self.coordinator = coordinator
        self._entry = entry
        self._key = key
        self._attr_unique_id = key
        self._attr_name = name
        self._attr_icon = icon
        self._attr_native_min_value = min_val
        self._attr_native_max_value = max_val
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit
        self._default = default
        self._state = default
    
    async def async_added_to_hass(self):
        """Restore state."""
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) is not None:
            self._state = last_state.state
    
    @property
    def native_value(self):
        """Return the current value."""
        return self._state
    
    async def async_set_native_value(self, value: float) -> None:
        """Update the value."""
        self._state = value
        self.async_write_ha_state()

