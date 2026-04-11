"""Automation implementations for Smart Vent Controller.

All runtime state is read from the coordinator / store rather than
hard-coded entity IDs.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import (
    async_track_state_change,
    async_track_time_interval,
)

from .const import DOMAIN
from .scripts import VentControlScript, ThermostatControlScript

if TYPE_CHECKING:
    from .coordinator import SmartVentControllerCoordinator

_LOGGER = logging.getLogger(__name__)


class SmartVentConditionerAutomation:
    """Main zone conditioner: reads coordinator state, drives vent + thermostat scripts."""

    def __init__(self, hass: HomeAssistant, entry) -> None:
        self.hass = hass
        self.entry = entry
        self.vent_script = VentControlScript(hass, entry)
        self.thermostat_script = ThermostatControlScript(hass, entry)
        self._last_trigger_time: datetime | None = None
        self._unsubscribers: list = []
        self._pending_task = None

    async def async_setup(self) -> None:
        rooms = self.entry.data.get("rooms", [])
        main_thermostat = self.entry.data.get("main_thermostat")

        tracked: list[str] = []
        for room in rooms:
            if ce := room.get("climate_entity"):
                tracked.append(ce)
            if occ := room.get("occupancy_sensor"):
                tracked.append(occ)
            if ts := room.get("temp_sensor"):
                tracked.append(ts)
        if main_thermostat:
            tracked.append(main_thermostat)

        if tracked:
            self._unsubscribers.append(
                async_track_state_change(
                    self.hass, tracked, self._handle_state_change, to_state=None
                )
            )

        self._unsubscribers.append(
            async_track_time_interval(
                self.hass, self._handle_periodic, timedelta(seconds=300)
            )
        )
        _LOGGER.info("Smart Vent Controller automation set up and running")

    async def async_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()

    @callback
    def _handle_state_change(self, entity_id, old_state, new_state):
        if new_state is None:
            return
        cooldown_sec = self.entry.options.get("automation_cooldown_sec", 30)
        if self._last_trigger_time:
            elapsed = (datetime.now() - self._last_trigger_time).total_seconds()
            if elapsed < cooldown_sec:
                return
        if self._pending_task:
            self._pending_task.cancel()
        self._pending_task = self.hass.async_create_task(
            self._debounced_run_automation()
        )

    async def _debounced_run_automation(self):
        await asyncio.sleep(0.5)
        await self._run_automation()

    @callback
    def _handle_periodic(self, now):
        self.hass.async_create_task(self._run_automation())

    async def _run_automation(self):
        self._last_trigger_time = datetime.now()

        coordinator: SmartVentControllerCoordinator = self.hass.data.get(
            DOMAIN, {}
        ).get(self.entry.entry_id)
        if coordinator is None:
            return

        rooms_csv = coordinator.get_rooms_to_condition_value()
        if rooms_csv in ("", "none", "unknown", "unavailable"):
            rooms_csv = ""

        auto_vent = self.entry.options.get("auto_vent_control", True)
        if auto_vent:
            try:
                await self.vent_script.async_run(rooms_csv)
            except Exception as exc:
                _LOGGER.error("Error in vent control: %s", exc, exc_info=True)

        auto_thermo = self.entry.options.get("auto_thermostat_control", True)
        if auto_thermo and rooms_csv:
            try:
                await self.thermostat_script.async_run(rooms_csv)
            except Exception as exc:
                _LOGGER.error("Error in thermostat control: %s", exc, exc_info=True)


class HVACCycleTrackingAutomation:
    """Track HVAC cycle start/end via coordinator store (no input_number)."""

    def __init__(self, hass: HomeAssistant, entry) -> None:
        self.hass = hass
        self.entry = entry
        self._unsubscribers: list = []

    async def async_setup(self) -> None:
        main_thermostat = self.entry.data.get("main_thermostat")
        if not main_thermostat:
            return
        self._unsubscribers.append(
            async_track_state_change(
                self.hass,
                main_thermostat,
                self._handle_hvac_action_change,
                to_state=None,
            )
        )
        _LOGGER.info("HVAC cycle tracking automation set up")

    async def async_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()

    @callback
    def _handle_hvac_action_change(self, entity_id, old_state, new_state):
        """Detect transitions and persist via the coordinator's store."""
        if new_state is None:
            return
        old_action = (
            old_state.attributes.get("hvac_action", "idle") if old_state else "idle"
        )
        new_action = new_state.attributes.get("hvac_action", "idle")
        if old_action == new_action:
            return
        # The coordinator already handles start/end in _async_update_data,
        # but this listener catches it faster between polls.
        coordinator = self.hass.data.get(DOMAIN, {}).get(self.entry.entry_id)
        if coordinator is None:
            return
        if old_action == "idle" and new_action in ("heating", "cooling"):
            self.hass.async_create_task(coordinator._handle_cycle_start(new_action))
        elif old_action in ("heating", "cooling") and new_action == "idle":
            self.hass.async_create_task(coordinator._handle_cycle_end())


class ClearManualOverrideAutomation:
    """Clear manual-override flag when an HVAC cycle completes."""

    def __init__(self, hass: HomeAssistant, entry) -> None:
        self.hass = hass
        self.entry = entry
        self._unsubscribers: list = []

    async def async_setup(self) -> None:
        main_thermostat = self.entry.data.get("main_thermostat")
        if not main_thermostat:
            return
        self._unsubscribers.append(
            async_track_state_change(
                self.hass,
                main_thermostat,
                self._handle_idle_transition,
                to_state=None,
            )
        )
        _LOGGER.info("Clear manual override automation set up")

    async def async_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()

    @callback
    def _handle_idle_transition(self, entity_id, old_state, new_state):
        if new_state is None:
            return
        old_action = (
            old_state.attributes.get("hvac_action", "idle") if old_state else "idle"
        )
        new_action = new_state.attributes.get("hvac_action", "idle")
        if old_action in ("heating", "cooling") and new_action == "idle":
            self.hass.async_create_task(self._clear_override())

    async def _clear_override(self):
        main_thermostat = self.entry.data.get("main_thermostat")
        thermostat = self.hass.states.get(main_thermostat)
        if not thermostat:
            return
        current_setpoint = thermostat.attributes.get("temperature")
        if current_setpoint is None:
            return

        coordinator = self.hass.data.get(DOMAIN, {}).get(self.entry.entry_id)
        if coordinator is None:
            return

        coordinator.store.last_thermostat_setpoint = float(current_setpoint)
        await coordinator.store.async_save()
        _LOGGER.info(
            "Manual override cleared after cycle completion. Resuming auto control."
        )
