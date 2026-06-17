"""Coordinator behavioral tests."""
import pytest
from datetime import timedelta

from freezegun import freeze_time
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smart_vent_controller.const import DOMAIN
from custom_components.smart_vent_controller.coordinator import (
    SmartVentControllerCoordinator,
)


def _make_entry(rooms):
    return MockConfigEntry(
        domain=DOMAIN,
        data={"main_thermostat": "climate.main", "rooms": rooms},
        options={},
    )


async def test_one_bad_room_does_not_blank_others(hass):
    rooms = [
        {"name": "Good Room", "temp_sensor": "sensor.good", "vent_entities": []},
        {"name": "Bad Room", "temp_sensor": "sensor.bad", "vent_entities": []},
    ]
    entry = _make_entry(rooms)
    entry.add_to_hass(hass)
    coordinator = SmartVentControllerCoordinator(hass, entry)
    await coordinator.async_initialize()

    hass.states.async_set("sensor.good", "70.0")

    # Force the bad room's read to raise; the good room must still be collected.
    original = coordinator._read_room_into

    def explode(room, data):
        if room.get("name") == "Bad Room":
            raise ValueError("sensor exploded")
        return original(room, data)

    coordinator._read_room_into = explode

    data = await coordinator._async_update_data()

    assert data["good_room_temp"] == 70.0
    assert "bad_room_temp" not in data or data["bad_room_temp"] is None


async def test_rooms_to_condition_selects_rooms_below_target_in_heat(hass):
    rooms = [
        {"name": "Cold Room", "temp_sensor": "sensor.cold",
         "climate_entity": "climate.cold", "vent_entities": []},
    ]
    entry = _make_entry(rooms)
    entry.add_to_hass(hass)
    coordinator = SmartVentControllerCoordinator(hass, entry)
    await coordinator.async_initialize()

    hass.states.async_set("climate.main", "heat")
    hass.states.async_set("sensor.cold", "66.0")
    hass.states.async_set("climate.cold", "heat", {"temperature": 72.0})

    hass.config_entries.async_update_entry(
        entry, options={"require_occupancy": False, "room_hysteresis_f": 1.0}
    )

    result = coordinator.get_rooms_to_condition_value()
    assert "cold_room" in result.split(",")


async def test_override_expires_after_duration(hass):
    entry = _make_entry([])
    entry.add_to_hass(hass)
    coordinator = SmartVentControllerCoordinator(hass, entry)
    await coordinator.async_initialize()

    with freeze_time("2026-06-16 12:00:00") as frozen:
        coordinator.set_room_override("guest_room", enabled=True, duration_min=60)
        assert coordinator.is_room_overridden("guest_room") is True

        frozen.tick(timedelta(minutes=61))
        assert coordinator.is_room_overridden("guest_room") is False
