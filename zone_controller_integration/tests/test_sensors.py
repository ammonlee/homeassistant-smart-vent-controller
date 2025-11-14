"""Tests for sensor platform."""

import pytest
from unittest.mock import MagicMock

from custom_components.zone_controller.sensor import (
    RoomTemperatureSensor,
    RoomTargetSensor,
    RoomDeltaSensor,
)


def test_room_temperature_sensor(mock_coordinator, mock_entry):
    """Test RoomTemperatureSensor."""
    # Mock temp sensor state
    temp_state = MagicMock()
    temp_state.state = "72.5"
    mock_coordinator.hass.states.get.return_value = temp_state
    
    sensor = RoomTemperatureSensor(
        mock_coordinator,
        mock_entry,
        "master_bedroom",
        "Master Bedroom",
        "climate.master_bedroom_room",
        "sensor.master_bedroom_temp_degf",
    )
    
    # Test device info
    device_info = sensor.device_info
    assert device_info["name"] == "Master Bedroom Zone"
    assert device_info["manufacturer"] == "Zone Controller"
    
    # Test value from temp sensor
    assert sensor.native_value == 72.5
    
    # Test fallback to climate entity
    mock_coordinator.hass.states.get.return_value = None
    climate_state = MagicMock()
    climate_state.attributes = {"current_temperature": 71.0}
    mock_coordinator.hass.states.get.side_effect = lambda e: {
        "sensor.master_bedroom_temp_degf": None,
        "climate.master_bedroom_room": climate_state,
    }.get(e)
    
    sensor = RoomTemperatureSensor(
        mock_coordinator,
        mock_entry,
        "master_bedroom",
        "Master Bedroom",
        "climate.master_bedroom_room",
        "sensor.master_bedroom_temp_degf",
    )
    assert sensor.native_value == 71.0


def test_room_target_sensor(mock_coordinator, mock_entry):
    """Test RoomTargetSensor."""
    climate_state = MagicMock()
    climate_state.attributes = {"temperature": 73.0}
    mock_coordinator.hass.states.get.return_value = climate_state
    
    sensor = RoomTargetSensor(
        mock_coordinator,
        mock_entry,
        "master_bedroom",
        "Master Bedroom",
        "climate.master_bedroom_room",
    )
    
    assert sensor.native_value == 73.0
    
    # Test device info
    device_info = sensor.device_info
    assert device_info["name"] == "Master Bedroom Zone"


def test_room_delta_sensor(mock_coordinator, mock_entry):
    """Test RoomDeltaSensor."""
    # Mock states
    temp_state = MagicMock()
    temp_state.state = "69.0"
    climate_state = MagicMock()
    climate_state.attributes = {"temperature": 73.0}
    
    mock_coordinator.hass.states.get.side_effect = lambda e: {
        "sensor.master_bedroom_temp_degf": temp_state,
        "climate.master_bedroom_room": climate_state,
    }.get(e)
    
    sensor = RoomDeltaSensor(
        mock_coordinator,
        mock_entry,
        "master_bedroom",
        "Master Bedroom",
        "climate.master_bedroom_room",
        "sensor.master_bedroom_temp_degf",
    )
    
    # Delta = target - current = 73.0 - 69.0 = 4.0
    assert sensor.native_value == 4.0
    
    # Test device info
    device_info = sensor.device_info
    assert device_info["name"] == "Master Bedroom Zone"

