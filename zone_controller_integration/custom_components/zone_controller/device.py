"""Device registry helpers for Smart Vent Controller."""

from homeassistant.helpers import device_registry as dr
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN


def get_room_device_id(entry: ConfigEntry, room_key: str) -> str:
    """Get device identifier for a room.
    
    Args:
        entry: Config entry
        room_key: Room key (e.g., 'master_bedroom')
    
    Returns:
        Device identifier tuple
    """
    return (DOMAIN, f"{entry.entry_id}_{room_key}")


async def async_create_room_devices(hass: HomeAssistant, entry: ConfigEntry):
    """Create device registry entries for all configured rooms.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
    """
    device_registry = dr.async_get(hass)
    rooms = entry.data.get("rooms", [])
    
    for room in rooms:
        room_name = room.get("name", "")
        room_key = room_name.lower().replace(" ", "_")
        
        # Create or get device for this room
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={get_room_device_id(entry, room_key)},
            name=f"{room_name} Zone",
            manufacturer="Smart Vent Controller",
            model="Room Controller",
            via_device=None,  # No parent device
        )


async def async_remove_room_devices(hass: HomeAssistant, entry: ConfigEntry):
    """Remove device registry entries for rooms.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
    """
    device_registry = dr.async_get(hass)
    rooms = entry.data.get("rooms", [])
    
    for room in rooms:
        room_name = room.get("name", "")
        room_key = room_name.lower().replace(" ", "_")
        
        device_id = get_room_device_id(entry, room_key)
        device = device_registry.async_get_device(identifiers={device_id})
        
        if device:
            device_registry.async_remove_device(device.id)

