"""Script platform for Zone Controller."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import service

from .const import DOMAIN
from .scripts import VentControlScript, ThermostatControlScript


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Set up Zone Controller scripts as services."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    vent_script = VentControlScript(hass, entry)
    thermostat_script = ThermostatControlScript(hass, entry)
    
    async def handle_set_multi_room_vents(call):
        """Handle set_multi_room_vents service call."""
        rooms_csv = call.data.get("rooms_csv", "")
        await vent_script.async_run(rooms_csv)
    
    async def handle_apply_ecobee_hold_for_rooms(call):
        """Handle apply_ecobee_hold_for_rooms service call."""
        rooms_csv = call.data.get("rooms_csv", "")
        await thermostat_script.async_run(rooms_csv)
    
    # Register as services
    from voluptuous import Schema, Optional
    
    hass.services.async_register(
        DOMAIN,
        "set_multi_room_vents",
        handle_set_multi_room_vents,
        schema=Schema({
            Optional("rooms_csv", default=""): str,
        })
    )
    
    hass.services.async_register(
        DOMAIN,
        "apply_ecobee_hold_for_rooms",
        handle_apply_ecobee_hold_for_rooms,
        schema=Schema({
            Optional("rooms_csv", default=""): str,
        })
    )

