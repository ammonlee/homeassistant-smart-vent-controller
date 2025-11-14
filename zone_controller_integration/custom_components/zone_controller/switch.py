"""Switch platform for Zone Controller."""

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import ZoneControllerCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Zone Controller switch entities."""
    coordinator: ZoneControllerCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = [
        ConfigSwitch(
            coordinator,
            entry,
            "require_occupancy",
            "Condition Only When Occupied",
            "mdi:account-eye",
            True
        ),
        ConfigSwitch(
            coordinator,
            entry,
            "heat_boost_enabled",
            "Heat Boost Enabled",
            "mdi:fire",
            True
        ),
        ConfigSwitch(
            coordinator,
            entry,
            "auto_thermostat_control",
            "Auto Thermostat Control",
            "mdi:thermostat-auto",
            True
        ),
        ConfigSwitch(
            coordinator,
            entry,
            "auto_vent_control",
            "Auto Vent Control",
            "mdi:air-conditioner",
            True
        ),
        ConfigSwitch(
            coordinator,
            entry,
            "debug_mode",
            "Debug Mode (Enhanced Logging)",
            "mdi:bug",
            False
        ),
    ]
    
    async_add_entities(entities)


class ConfigSwitch(SwitchEntity):
    """Configuration switch entity."""
    
    def __init__(self, coordinator, entry, key, name, icon, default):
        """Initialize the switch."""
        self.coordinator = coordinator
        self._entry = entry
        self._key = key
        self._attr_unique_id = key
        self._attr_name = name
        self._attr_icon = icon
        self._default = default
    
    @property
    def is_on(self):
        """Return True if switch is on."""
        # Try options first, then fallback to default
        return self._entry.options.get(self._key, self._default) if self._entry.options else self._default
    
    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        await self._async_set_state(True)
    
    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        await self._async_set_state(False)
    
    async def _async_set_state(self, state: bool):
        """Update the switch state."""
        options = dict(self._entry.options or {})
        options[self._key] = state
        
        self.coordinator.hass.config_entries.async_update_entry(
            self._entry, options=options
        )
        self.async_write_ha_state()

