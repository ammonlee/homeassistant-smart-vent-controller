"""Cover platform for Smart Vent Controller.

Creates a proxy cover entity per vent per room so that vent controls
appear on the room's device page. Each proxy forwards state reads and
position commands to the underlying cover entity (ESPHome, Flair, etc.).
"""
from __future__ import annotations

import logging

from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import DOMAIN
from .device import get_room_device_id

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up proxy cover entities for room vents."""
    rooms = entry.data.get("rooms", [])
    entities: list[CoverEntity] = []

    for room in rooms:
        room_name = room.get("name", "")
        room_key = room_name.lower().replace(" ", "_")
        vent_entities = room.get("vent_entities", [])

        for vent_id in vent_entities:
            entities.append(
                RoomVentCover(hass, entry, room_key, room_name, vent_id)
            )

    async_add_entities(entities)


class RoomVentCover(CoverEntity):
    """Proxy cover entity that mirrors and controls an underlying vent."""

    _attr_device_class = CoverDeviceClass.DAMPER
    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.SET_POSITION
    )

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        room_key: str,
        room_name: str,
        source_entity_id: str,
    ) -> None:
        self.hass = hass
        self._entry = entry
        self._room_key = room_key
        self._room_name = room_name
        self._source_entity_id = source_entity_id
        self._unsub_listener = None

        # Derive a friendly name from the source entity id
        # e.g. "cover.master_bedroom_v1_vent" -> "Master Bedroom V1 Vent"
        short = source_entity_id.removeprefix("cover.")
        friendly = short.replace("_", " ").title()

        self._attr_unique_id = f"{entry.entry_id}_{room_key}_{short}"
        self._attr_name = friendly

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={get_room_device_id(self._entry, self._room_key)},
            name=f"{self._room_name} Zone",
            manufacturer="Smart Vent Controller",
            model="Room Controller",
        )

    async def async_added_to_hass(self) -> None:
        """Track state changes on the source entity."""
        @callback
        def _state_changed(event):
            self.async_write_ha_state()

        self._unsub_listener = async_track_state_change_event(
            self.hass, [self._source_entity_id], _state_changed
        )

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub_listener:
            self._unsub_listener()

    # -- State from source entity ------------------------------------------

    def _source_state(self):
        return self.hass.states.get(self._source_entity_id)

    @property
    def available(self) -> bool:
        state = self._source_state()
        return state is not None and state.state != "unavailable"

    @property
    def is_closed(self) -> bool | None:
        state = self._source_state()
        if state is None:
            return None
        return state.state == "closed"

    @property
    def current_cover_position(self) -> int | None:
        state = self._source_state()
        if state is None:
            return None
        pos = state.attributes.get("current_position")
        if pos is not None:
            try:
                return int(pos)
            except (ValueError, TypeError):
                pass
        return None

    # -- Commands forwarded to source entity --------------------------------

    async def async_open_cover(self, **kwargs) -> None:
        await self.hass.services.async_call(
            "cover", "open_cover",
            {"entity_id": self._source_entity_id},
            blocking=True,
        )

    async def async_close_cover(self, **kwargs) -> None:
        await self.hass.services.async_call(
            "cover", "close_cover",
            {"entity_id": self._source_entity_id},
            blocking=True,
        )

    async def async_set_cover_position(self, **kwargs) -> None:
        position = kwargs.get("position")
        if position is not None:
            await self.hass.services.async_call(
                "cover", "set_cover_position",
                {"entity_id": self._source_entity_id, "position": position},
                blocking=True,
            )
