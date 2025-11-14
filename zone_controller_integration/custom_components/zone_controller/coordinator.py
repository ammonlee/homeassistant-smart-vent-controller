"""Data coordinator for Zone Controller."""

from datetime import timedelta
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .cache import RoomDataCache, EntityStateCache


class ZoneControllerCoordinator(DataUpdateCoordinator):
    """Class to manage Zone Controller data updates."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            logger=__name__,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
        )
        self.config_entry = entry
        self.rooms = entry.data.get("rooms", [])
        # Initialize caches for performance
        self.room_cache = RoomDataCache(ttl_seconds=5)
        self.entity_cache = EntityStateCache(ttl_seconds=2)

    async def _async_update_data(self):
        """Fetch data from Zone Controller."""
        try:
            # Update room temperatures, vent positions, occupancy states
            # This would coordinate updates across all platforms
            data = {}
            
            for room in self.rooms:
                room_name = room.get("name", "").lower().replace(" ", "_")
                
                # Get current temperature
                temp_sensor = room.get("temp_sensor")
                if temp_sensor and temp_sensor in self.hass.states.async_entity_ids():
                    temp = self.hass.states.get(temp_sensor)
                    data[f"{room_name}_temp"] = float(temp.state) if temp else None
                else:
                    # Fallback to climate entity
                    climate_entity = room.get("climate_entity")
                    if climate_entity:
                        climate = self.hass.states.get(climate_entity)
                        if climate:
                            data[f"{room_name}_temp"] = climate.attributes.get("current_temperature")
                
                # Get vent positions
                vent_entities = room.get("vent_entities", [])
                vent_positions = []
                for vent in vent_entities:
                    if vent in self.hass.states.async_entity_ids():
                        vent_state = self.hass.states.get(vent)
                        if vent_state:
                            pos = vent_state.attributes.get("current_position", 0)
                            vent_positions.append(pos)
                data[f"{room_name}_vent_avg"] = (
                    sum(vent_positions) / len(vent_positions) 
                    if vent_positions else 0
                )
                
                # Get occupancy
                occ_sensor = room.get("occupancy_sensor")
                if occ_sensor and occ_sensor in self.hass.states.async_entity_ids():
                    occ_state = self.hass.states.get(occ_sensor)
                    data[f"{room_name}_occupied"] = occ_state.state == "on" if occ_state else False
            
            return data
            
        except Exception as err:
            raise UpdateFailed(f"Error communicating with Zone Controller: {err}") from err

