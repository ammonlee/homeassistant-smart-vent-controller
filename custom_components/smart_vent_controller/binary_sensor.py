"""Binary sensor platform for Smart Vent Controller."""

from datetime import datetime, time, timezone
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN
from .coordinator import SmartVentControllerCoordinator
from .device import get_room_device_id


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Smart Vent Controller binary sensors."""
    coordinator: SmartVentControllerCoordinator = hass.data[DOMAIN][entry.entry_id]
    rooms = entry.data.get("rooms", [])

    entities: list[BinarySensorEntity] = []

    for room in rooms:
        room_name = room.get("name", "")
        room_key = room_name.lower().replace(" ", "_")
        occ_sensor = room.get("occupancy_sensor", "")

        if occ_sensor:
            entities.append(
                RoomOccupiedRecentSensor(
                    coordinator, entry, room_key, room_name, occ_sensor
                )
            )
        entities.append(
            RoomConditioningActiveSensor(coordinator, entry, room_key, room_name)
        )
        entities.append(
            RoomOverrideActiveSensor(coordinator, entry, room_key, room_name)
        )

    entities.append(ThermostatManualOverrideSensor(coordinator, entry))

    async_add_entities(entities)


class RoomOccupiedRecentSensor(BinarySensorEntity):
    """Recent room occupancy with day/night linger."""

    _attr_icon = "mdi:account-eye"

    def __init__(self, coordinator, entry, room_key, room_name, occ_sensor):
        self.coordinator = coordinator
        self._entry = entry
        self._room_key = room_key
        self._room_name = room_name
        self._occ_sensor = occ_sensor
        self._attr_unique_id = f"{entry.entry_id}_{room_key}_occupied_recent"
        self._attr_name = f"{room_name} Occupied Recent"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={get_room_device_id(self._entry, self._room_key)},
            name=f"{self._room_name} Zone",
            manufacturer="Smart Vent Controller",
            model="Room Controller",
        )

    @property
    def is_on(self):
        occ_state = self.coordinator.hass.states.get(self._occ_sensor)
        if not occ_state or occ_state.state != "on":
            return False

        now_utc = datetime.now(tz=timezone.utc)
        now_local = now_utc.time()
        is_night = time(22, 0) <= now_local or now_local <= time(6, 0)
        linger_min = self._entry.options.get(
            "occupancy_linger_night_min" if is_night else "occupancy_linger_min",
            60 if is_night else 30,
        )

        last_changed = occ_state.last_changed
        if last_changed:
            elapsed = (now_utc - last_changed).total_seconds() / 60
            return elapsed <= linger_min
        return False


class RoomConditioningActiveSensor(BinarySensorEntity):
    """Whether a room is currently being conditioned."""

    _attr_icon = "mdi:hvac"

    def __init__(self, coordinator, entry, room_key, room_name):
        self.coordinator = coordinator
        self._entry = entry
        self._room_key = room_key
        self._room_name = room_name
        self._attr_unique_id = f"{entry.entry_id}_{room_key}_conditioning_active"
        self._attr_name = f"{room_name} Conditioning Active"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={get_room_device_id(self._entry, self._room_key)},
            name=f"{self._room_name} Zone",
            manufacturer="Smart Vent Controller",
            model="Room Controller",
        )

    @property
    def is_on(self):
        csv = self.coordinator.get_rooms_to_condition_value()
        if csv in ("none", ""):
            return False
        return self._room_key in csv.split(",")


class RoomOverrideActiveSensor(BinarySensorEntity):
    """Whether a room is currently in manual override (excluded from conditioning)."""

    _attr_icon = "mdi:hand-back-left"

    def __init__(self, coordinator, entry, room_key, room_name):
        self.coordinator = coordinator
        self._entry = entry
        self._room_key = room_key
        self._room_name = room_name
        self._attr_unique_id = f"{entry.entry_id}_{room_key}_override_active"
        self._attr_name = f"{room_name} Override Active"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={get_room_device_id(self._entry, self._room_key)},
            name=f"{self._room_name} Zone",
            manufacturer="Smart Vent Controller",
            model="Room Controller",
        )

    @property
    def is_on(self):
        return self.coordinator.is_room_overridden(self._room_key)

    @property
    def extra_state_attributes(self):
        overrides = self.coordinator.store._data.get("room_overrides", {})
        info = overrides.get(self._room_key)
        if info:
            until_ts = info.get("until", 0)
            remaining = max(0, (until_ts - datetime.now(tz=timezone.utc).timestamp()) / 60)
            return {"remaining_minutes": round(remaining, 1)}
        return {}


class ThermostatManualOverrideSensor(BinarySensorEntity):
    """Detects manual thermostat override by comparing current setpoint to last automation setpoint."""

    _attr_icon = "mdi:hand-back-left"

    def __init__(self, coordinator, entry):
        self.coordinator: SmartVentControllerCoordinator = coordinator
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_thermostat_manual_override"
        self._attr_name = "Thermostat Manual Override Detected"

    @property
    def is_on(self):
        main = self._entry.data.get("main_thermostat")
        if not main or not self._entry.options.get("auto_thermostat_control", True):
            return False
        thermo = self.coordinator.hass.states.get(main)
        if not thermo:
            return False
        current = thermo.attributes.get("temperature")
        if current is None:
            return False
        last = self.coordinator.store.last_thermostat_setpoint
        if last <= 0:
            return False
        try:
            return abs(float(current) - last) > 0.5
        except (ValueError, TypeError):
            return False

    @property
    def extra_state_attributes(self):
        main = self._entry.data.get("main_thermostat")
        if not main:
            return {}
        thermo = self.coordinator.hass.states.get(main)
        if not thermo:
            return {}
        current = thermo.attributes.get("temperature", 0)
        last = self.coordinator.store.last_thermostat_setpoint
        try:
            diff = abs(float(current) - last) if current else 0
        except (ValueError, TypeError):
            diff = 0
        return {
            "current_setpoint": current,
            "last_automation_setpoint": last,
            "difference": round(diff, 1),
        }
