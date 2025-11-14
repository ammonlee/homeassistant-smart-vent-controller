"""Tests for error handling utilities."""

import pytest
from unittest.mock import MagicMock, AsyncMock

from custom_components.zone_controller.error_handling import (
    safe_float,
    safe_int,
    validate_entity_state,
    get_safe_state,
    get_safe_attribute,
    validate_temperature,
    validate_vent_position,
    ErrorRecovery,
    EntityUnavailableError,
)


def test_safe_float_valid():
    """Test safe_float with valid values."""
    assert safe_float("72.5") == 72.5
    assert safe_float(72.5) == 72.5
    assert safe_float(72) == 72.0


def test_safe_float_invalid():
    """Test safe_float with invalid values."""
    assert safe_float("invalid") == 0.0
    assert safe_float(None) == 0.0
    assert safe_float("invalid", default=72.0) == 72.0


def test_safe_float_range():
    """Test safe_float with range validation."""
    assert safe_float(75.0, min_val=40.0, max_val=100.0) == 75.0
    assert safe_float(35.0, default=72.0, min_val=40.0, max_val=100.0) == 72.0
    assert safe_float(105.0, default=72.0, min_val=40.0, max_val=100.0) == 72.0


def test_safe_int_valid():
    """Test safe_int with valid values."""
    assert safe_int("72") == 72
    assert safe_int(72) == 72
    assert safe_int(72.5) == 72


def test_safe_int_invalid():
    """Test safe_int with invalid values."""
    assert safe_int("invalid") == 0
    assert safe_int(None) == 0
    assert safe_int("invalid", default=72) == 72


def test_safe_int_range():
    """Test safe_int with range validation."""
    assert safe_int(75, min_val=0, max_val=100) == 75
    assert safe_int(-5, default=20, min_val=0, max_val=100) == 20
    assert safe_int(105, default=20, min_val=0, max_val=100) == 20


def test_validate_entity_state(mock_hass):
    """Test validate_entity_state."""
    # Entity doesn't exist
    mock_hass.states.async_entity_ids.return_value = []
    assert validate_entity_state(mock_hass, "climate.test", "climate") is False
    
    # Entity exists and available
    mock_hass.states.async_entity_ids.return_value = ["climate.test"]
    state = MagicMock()
    state.state = "heat"
    mock_hass.states.get.return_value = state
    assert validate_entity_state(mock_hass, "climate.test", "climate") is True
    
    # Entity unavailable
    state.state = "unavailable"
    assert validate_entity_state(mock_hass, "climate.test", "climate") is False


def test_get_safe_state(mock_hass):
    """Test get_safe_state."""
    state = MagicMock()
    state.state = "72.5"
    mock_hass.states.get.return_value = state
    mock_hass.states.async_entity_ids.return_value = ["sensor.test"]
    
    assert get_safe_state(mock_hass, "sensor.test") == "72.5"
    assert get_safe_state(mock_hass, "sensor.nonexistent", default="default") == "default"


def test_get_safe_attribute(mock_hass):
    """Test get_safe_attribute."""
    state = MagicMock()
    state.attributes = {"temperature": 72.5}
    mock_hass.states.get.return_value = state
    mock_hass.states.async_entity_ids.return_value = ["climate.test"]
    
    assert get_safe_attribute(mock_hass, "climate.test", "temperature") == 72.5
    assert get_safe_attribute(mock_hass, "climate.test", "nonexistent", default=0) == 0


def test_validate_temperature():
    """Test validate_temperature."""
    assert validate_temperature(72.0) is True
    assert validate_temperature(75.5) is True
    assert validate_temperature(35.0) is False  # Below min (40)
    assert validate_temperature(105.0) is False  # Above max (100)
    assert validate_temperature("invalid") is False


def test_validate_vent_position():
    """Test validate_vent_position."""
    assert validate_vent_position(50) is True
    assert validate_vent_position(0) is True
    assert validate_vent_position(100) is True
    assert validate_vent_position(-5) is False
    assert validate_vent_position(105) is False
    assert validate_vent_position("invalid") is False


def test_error_recovery(mock_hass, mock_entry):
    """Test ErrorRecovery class."""
    recovery = ErrorRecovery(mock_hass, mock_entry)
    
    # No errors initially
    assert recovery.should_disable_component("vent_control") is False
    
    # Record errors
    for i in range(5):
        recovery.record_error("vent_control", Exception(f"Error {i}"))
    
    # Should disable after 5 errors
    assert recovery.should_disable_component("vent_control") is True
    
    # Reset errors
    recovery.reset_errors("vent_control")
    assert recovery.should_disable_component("vent_control") is False

