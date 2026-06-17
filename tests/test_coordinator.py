"""Coordinator behavioral tests."""
import pytest
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
