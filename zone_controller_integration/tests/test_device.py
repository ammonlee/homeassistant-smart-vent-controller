"""Tests for device registry helpers."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from custom_components.zone_controller.device import (
    get_room_device_id,
    async_create_room_devices,
    async_remove_room_devices,
)


def test_get_room_device_id(mock_entry):
    """Test get_room_device_id."""
    device_id = get_room_device_id(mock_entry, "master_bedroom")
    assert device_id == ("zone_controller", f"{mock_entry.entry_id}_master_bedroom")


@pytest.mark.asyncio
async def test_async_create_room_devices(mock_hass, mock_entry):
    """Test async_create_room_devices."""
    device_registry = MagicMock()
    device_registry.async_get_or_create = AsyncMock()
    
    with patch("custom_components.zone_controller.device.dr.async_get", return_value=device_registry):
        await async_create_room_devices(mock_hass, mock_entry)
    
    # Should create devices for each room
    assert device_registry.async_get_or_create.call_count == len(mock_entry.data["rooms"])


@pytest.mark.asyncio
async def test_async_remove_room_devices(mock_hass, mock_entry):
    """Test async_remove_room_devices."""
    device_registry = MagicMock()
    device = MagicMock()
    device.id = "device_id"
    device_registry.async_get_device = MagicMock(return_value=device)
    device_registry.async_remove_device = AsyncMock()
    
    with patch("custom_components.zone_controller.device.dr.async_get", return_value=device_registry):
        await async_remove_room_devices(mock_hass, mock_entry)
    
    # Should attempt to remove devices for each room
    assert device_registry.async_get_device.call_count == len(mock_entry.data["rooms"])

