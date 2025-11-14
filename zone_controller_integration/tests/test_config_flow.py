"""Tests for config flow."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.zone_controller.config_flow import (
    ZoneControllerConfigFlow,
    ZoneControllerOptionsFlowHandler,
)


@pytest.mark.asyncio
async def test_config_flow_user_step(mock_hass):
    """Test config flow user step."""
    flow = ZoneControllerConfigFlow()
    flow.hass = mock_hass
    
    # Mock climate entities
    mock_hass.states.async_entity_ids.return_value = [
        "climate.main_thermostat",
        "climate.other_thermostat",
    ]
    
    # Test initial form
    result = await flow.async_step_user()
    assert result["type"] == FlowResultType.FORM
    assert "data_schema" in result
    
    # Test with user input
    user_input = {"main_thermostat": "climate.main_thermostat"}
    result = await flow.async_step_user(user_input)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "rooms"


@pytest.mark.asyncio
async def test_config_flow_rooms_step(mock_hass):
    """Test config flow rooms step."""
    flow = ZoneControllerConfigFlow()
    flow.hass = mock_hass
    flow.data = {"main_thermostat": "climate.main_thermostat"}
    flow.rooms = []
    
    # Mock entities
    mock_hass.states.async_entity_ids.side_effect = lambda domain: {
        "climate": ["climate.master_bedroom_room"],
        "sensor": ["sensor.master_bedroom_temp"],
        "binary_sensor": ["binary_sensor.master_bedroom_occupancy"],
        "cover": ["cover.master_v1"],
    }.get(domain, [])
    
    # Test with room input
    user_input = {
        "room_name": "Master Bedroom",
        "climate_entity": "climate.master_bedroom_room",
        "temp_sensor": "sensor.master_bedroom_temp",
        "occupancy_sensor": "binary_sensor.master_bedroom_occupancy",
        "vent_entities": ["cover.master_v1"],
        "priority": 5,
        "add_another": False,
    }
    
    result = await flow.async_step_rooms(user_input)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "settings"


@pytest.mark.asyncio
async def test_options_flow(mock_entry):
    """Test options flow."""
    handler = ZoneControllerOptionsFlowHandler(mock_entry)
    
    # Test initial form
    result = await handler.async_step_init()
    assert result["type"] == FlowResultType.FORM
    assert "data_schema" in result
    
    # Test with user input
    user_input = {
        "min_other_room_open_pct": 25,
        "heat_boost_f": 2.0,
    }
    
    result = await handler.async_step_init(user_input)
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"] == user_input

