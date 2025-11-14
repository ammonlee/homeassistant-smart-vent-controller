"""Automation platform for Smart Vent Controller."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .automations import (
    SmartVentConditionerAutomation,
    HVACCycleTrackingAutomation,
    ClearManualOverrideAutomation,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Set up Smart Vent Controller automations."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    # Create automation instances
    zone_automation = SmartVentConditionerAutomation(hass, entry)
    cycle_automation = HVACCycleTrackingAutomation(hass, entry)
    override_automation = ClearManualOverrideAutomation(hass, entry)
    
    # Set up automations
    await zone_automation.async_setup()
    await cycle_automation.async_setup()
    await override_automation.async_setup()
    
    # Store for cleanup
    coordinator.automations = [
        zone_automation,
        cycle_automation,
        override_automation,
    ]


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Unload Smart Vent Controller automations."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    if hasattr(coordinator, "automations"):
        for automation in coordinator.automations:
            await automation.async_unload()
        coordinator.automations = []

