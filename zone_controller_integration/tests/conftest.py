"""Pytest configuration for Zone Controller tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_registry import EntityRegistry
from homeassistant.helpers.device_registry import DeviceRegistry

from custom_components.zone_controller.const import DOMAIN
from custom_components.zone_controller.coordinator import ZoneControllerCoordinator


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.states = MagicMock()
    hass.states.async_entity_ids = MagicMock(return_value=[])
    hass.states.get = MagicMock(return_value=None)
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.services.async_register = AsyncMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_update_entry = AsyncMock()
    hass.async_block_till_done = AsyncMock()
    hass.data = {}
    return hass


@pytest.fixture
def mock_entry():
    """Create a mock config entry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.data = {
        "main_thermostat": "climate.main_thermostat",
        "rooms": [
            {
                "name": "Master Bedroom",
                "climate_entity": "climate.master_bedroom_room",
                "temp_sensor": "sensor.master_bedroom_temp_degf",
                "occupancy_sensor": "binary_sensor.master_bedroom_occupancy",
                "vent_entities": ["cover.master_v1", "cover.master_v2"],
                "priority": 5,
            },
            {
                "name": "Blue Room",
                "climate_entity": "climate.blue_room_room",
                "temp_sensor": "",
                "occupancy_sensor": "binary_sensor.blue_room_occupancy",
                "vent_entities": ["cover.blue_v1"],
                "priority": 5,
            },
        ],
    }
    entry.options = {
        "min_other_room_open_pct": 20,
        "closed_threshold_pct": 10,
        "relief_open_pct": 60,
        "max_relief_rooms": 3,
        "room_hysteresis_f": 1.0,
        "occupancy_linger_min": 30,
        "occupancy_linger_night_min": 60,
        "heat_boost_f": 1.0,
        "hvac_min_runtime_min": 10,
        "hvac_min_off_time_min": 5,
        "default_thermostat_temp": 72,
        "automation_cooldown_sec": 30,
        "require_occupancy": True,
        "heat_boost_enabled": True,
        "auto_thermostat_control": True,
        "auto_vent_control": True,
        "debug_mode": False,
    }
    return entry


@pytest.fixture
def mock_coordinator(mock_hass, mock_entry):
    """Create a mock coordinator."""
    coordinator = MagicMock(spec=ZoneControllerCoordinator)
    coordinator.hass = mock_hass
    coordinator.entry = mock_entry
    return coordinator


@pytest.fixture
def mock_thermostat_state():
    """Create a mock thermostat state."""
    state = MagicMock()
    state.state = "heat"
    state.attributes = {
        "hvac_action": "heating",
        "temperature": 75.0,
        "current_temperature": 70.0,
    }
    return state


@pytest.fixture
def mock_room_climate_state():
    """Create a mock room climate state."""
    state = MagicMock()
    state.state = "heat"
    state.attributes = {
        "temperature": 73.0,
        "current_temperature": 69.0,
    }
    return state


@pytest.fixture
def mock_vent_state():
    """Create a mock vent state."""
    state = MagicMock()
    state.state = "open"
    state.attributes = {
        "current_position": 50,
    }
    return state


@pytest.fixture
def mock_occupancy_state():
    """Create a mock occupancy state."""
    state = MagicMock()
    state.state = "on"
    state.last_changed = None
    return state

