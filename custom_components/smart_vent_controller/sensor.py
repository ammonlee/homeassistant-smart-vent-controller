"""Sensor platform for Smart Vent Controller."""

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.const import UnitOfTemperature

from .const import DOMAIN
from .coordinator import SmartVentControllerCoordinator
from .device import get_room_device_id


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Smart Vent Controller sensors."""
    coordinator: SmartVentControllerCoordinator = hass.data[DOMAIN][entry.entry_id]
    rooms = entry.data.get("rooms", [])

    entities: list[SensorEntity] = []

    for room in rooms:
        room_name = room.get("name", "")
        room_key = room_name.lower().replace(" ", "_")
        climate_entity = room.get("climate_entity")
        temp_sensor = room.get("temp_sensor", "")

        entities.append(
            RoomTemperatureSensor(
                coordinator, entry, room_key, room_name, climate_entity, temp_sensor
            )
        )
        entities.append(
            RoomTargetSensor(coordinator, entry, room_key, room_name, climate_entity)
        )
        entities.append(
            RoomDeltaSensor(
                coordinator, entry, room_key, room_name, climate_entity, temp_sensor
            )
        )
        entities.append(
            RoomEfficiencySensor(coordinator, entry, room_key, room_name)
        )

    entities.append(RoomsToConditionSensor(coordinator, entry))
    entities.append(HVACCycleProtectionSensor(coordinator, entry))
    entities.append(HVACCycleStartTimeSensor(coordinator, entry))
    entities.append(HVACCycleEndTimeSensor(coordinator, entry))
    entities.append(SmartVentControllerStatsSensor(coordinator, entry))

    async_add_entities(entities)


# ---------------------------------------------------------------------------
# Per-room sensors
# ---------------------------------------------------------------------------

class RoomTemperatureSensor(SensorEntity):
    """Current temperature for a room."""

    _attr_device_class = "temperature"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.FAHRENHEIT

    def __init__(self, coordinator, entry, room_key, room_name, climate_entity, temp_sensor):
        self.coordinator = coordinator
        self._entry = entry
        self._room_key = room_key
        self._room_name = room_name
        self._climate_entity = climate_entity
        self._temp_sensor = temp_sensor
        self._attr_unique_id = f"{entry.entry_id}_{room_key}_temp_degf"
        self._attr_name = f"{room_name} Temp (°F)"
        self._attr_icon = "mdi:thermometer"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={get_room_device_id(self._entry, self._room_key)},
            name=f"{self._room_name} Zone",
            manufacturer="Smart Vent Controller",
            model="Room Controller",
        )

    @property
    def native_value(self):
        if self._temp_sensor:
            state = self.coordinator.hass.states.get(self._temp_sensor)
            if state and state.state not in ("unknown", "unavailable", "None", "none"):
                try:
                    return float(state.state)
                except (ValueError, TypeError):
                    pass
        if self._climate_entity:
            climate = self.coordinator.hass.states.get(self._climate_entity)
            if climate:
                temp = climate.attributes.get("current_temperature")
                if temp is not None:
                    return float(temp)
        return None


class RoomTargetSensor(SensorEntity):
    """Target temperature for a room."""

    _attr_device_class = "temperature"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.FAHRENHEIT

    def __init__(self, coordinator, entry, room_key, room_name, climate_entity):
        self.coordinator = coordinator
        self._entry = entry
        self._room_key = room_key
        self._room_name = room_name
        self._climate_entity = climate_entity
        self._attr_unique_id = f"{entry.entry_id}_{room_key}_target_degf"
        self._attr_name = f"{room_name} Target (°F)"
        self._attr_icon = "mdi:target"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={get_room_device_id(self._entry, self._room_key)},
            name=f"{self._room_name} Zone",
            manufacturer="Smart Vent Controller",
            model="Room Controller",
        )

    @property
    def native_value(self):
        if self._climate_entity:
            climate = self.coordinator.hass.states.get(self._climate_entity)
            if climate:
                temp = climate.attributes.get("temperature")
                if temp is not None:
                    return float(temp)
                lo = climate.attributes.get("target_temp_low")
                hi = climate.attributes.get("target_temp_high")
                if lo is not None and hi is not None:
                    return (float(lo) + float(hi)) / 2
        return None


class RoomDeltaSensor(SensorEntity):
    """Temperature delta (target - current) for a room."""

    _attr_device_class = "temperature"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.FAHRENHEIT

    def __init__(self, coordinator, entry, room_key, room_name, climate_entity, temp_sensor):
        self.coordinator = coordinator
        self._entry = entry
        self._room_key = room_key
        self._room_name = room_name
        self._climate_entity = climate_entity
        self._temp_sensor = temp_sensor
        self._attr_unique_id = f"{entry.entry_id}_{room_key}_delta_degf"
        self._attr_name = f"{room_name} Delta (°F)"
        self._attr_icon = "mdi:delta"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={get_room_device_id(self._entry, self._room_key)},
            name=f"{self._room_name} Zone",
            manufacturer="Smart Vent Controller",
            model="Room Controller",
        )

    @property
    def native_value(self):
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

        current = None
        if self._temp_sensor:
            state = self.coordinator.hass.states.get(self._temp_sensor)
            if state and state.state not in ("unknown", "unavailable", "None", "none"):
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


class RoomEfficiencySensor(SensorEntity):
    """Learned heating/cooling efficiency rate for a room."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:chart-timeline-variant"

    def __init__(self, coordinator, entry, room_key, room_name):
        self.coordinator = coordinator
        self._entry = entry
        self._room_key = room_key
        self._room_name = room_name
        self._attr_unique_id = f"{entry.entry_id}_{room_key}_efficiency"
        self._attr_name = f"{room_name} Efficiency"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={get_room_device_id(self._entry, self._room_key)},
            name=f"{self._room_name} Zone",
            manufacturer="Smart Vent Controller",
            model="Room Controller",
        )

    @property
    def native_value(self):
        heat = self.coordinator.store.get_heating_rate(self._room_key)
        cool = self.coordinator.store.get_cooling_rate(self._room_key)
        best = max(heat, cool)
        if best <= 0:
            return None
        return round(best, 4)

    @property
    def extra_state_attributes(self):
        return {
            "heating_rate": round(
                self.coordinator.store.get_heating_rate(self._room_key), 4
            ),
            "cooling_rate": round(
                self.coordinator.store.get_cooling_rate(self._room_key), 4
            ),
        }


# ---------------------------------------------------------------------------
# Global sensors
# ---------------------------------------------------------------------------

class RoomsToConditionSensor(SensorEntity):
    """Which rooms currently need conditioning (reads from coordinator)."""

    _attr_icon = "mdi:home-thermometer-outline"

    def __init__(self, coordinator, entry):
        self.coordinator = coordinator
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_rooms_to_condition"
        self._attr_name = "Rooms To Condition"

    @property
    def native_value(self):
        return self.coordinator.get_rooms_to_condition_value()


class HVACCycleProtectionSensor(SensorEntity):
    """Whether cycle protection is currently blocking changes."""

    _attr_icon = "mdi:shield-check"

    def __init__(self, coordinator, entry):
        self.coordinator = coordinator
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_hvac_cycle_protection"
        self._attr_name = "HVAC Cycle Protection Status"

    @property
    def native_value(self):
        main = self._entry.data.get("main_thermostat")
        if not main:
            return "allowed"
        thermo = self.coordinator.hass.states.get(main)
        if not thermo:
            return "allowed"

        action = thermo.attributes.get("hvac_action", "idle")
        min_runtime = self._entry.options.get("hvac_min_runtime_min", 10) * 60
        min_off = self._entry.options.get("hvac_min_off_time_min", 5) * 60
        from datetime import datetime

        now = datetime.now().timestamp()

        if action in ("heating", "cooling"):
            start = self.coordinator.store.cycle_start_ts
            if start > 0 and (now - start) < min_runtime:
                return "protected"
        elif action == "idle":
            end = self.coordinator.store.cycle_end_ts
            if end > 0 and (now - end) < min_off:
                return "protected"
        return "allowed"


class HVACCycleStartTimeSensor(SensorEntity):
    """Timestamp of last HVAC cycle start."""

    _attr_icon = "mdi:clock-start"

    def __init__(self, coordinator, entry):
        self.coordinator = coordinator
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_hvac_cycle_start"
        self._attr_name = "HVAC Cycle Start Time"

    @property
    def native_value(self):
        return self.coordinator.store.cycle_start_ts


class HVACCycleEndTimeSensor(SensorEntity):
    """Timestamp of last HVAC cycle end."""

    _attr_icon = "mdi:clock-end"

    def __init__(self, coordinator, entry):
        self.coordinator = coordinator
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_hvac_cycle_end"
        self._attr_name = "HVAC Cycle End Time"

    @property
    def native_value(self):
        return self.coordinator.store.cycle_end_ts


class SmartVentControllerStatsSensor(SensorEntity):
    """Aggregated statistics sensor."""

    _attr_icon = "mdi:chart-line"

    def __init__(self, coordinator, entry):
        self.coordinator = coordinator
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_stats"
        self._attr_name = "Smart Vent Controller Statistics"

    @property
    def native_value(self):
        return self.coordinator.get_rooms_to_condition_value()

    @property
    def extra_state_attributes(self):
        csv = self.coordinator.get_rooms_to_condition_value()
        count = 0
        if csv and csv != "none":
            parts = [r for r in csv.split(",") if r and r != "none"]
            count = len(parts)
        return {
            "rooms_selected_count": count,
            "total_rooms": len(self._entry.data.get("rooms", [])),
            "automation_enabled": (
                self._entry.options.get("auto_vent_control", True)
                and self._entry.options.get("auto_thermostat_control", True)
            ),
            "control_strategy": self._entry.options.get("control_strategy", "simple"),
        }
