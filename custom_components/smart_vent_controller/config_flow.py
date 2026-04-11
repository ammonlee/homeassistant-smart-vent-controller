"""Config flow for Smart Vent Controller integration."""

from typing import Any
import copy
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import (
    device_registry as dr,
    entity_registry as er,
    selector,
)

_LOGGER = logging.getLogger(__name__)

from .const import (
    DOMAIN,
    CONF_MAIN_THERMOSTAT,
    CONF_ROOMS,
    CONF_ROOM_NAME,
    CONF_ROOM_CLIMATE,
    CONF_ROOM_TEMP_SENSOR,
    CONF_ROOM_OCCUPANCY_SENSOR,
    CONF_ROOM_VENTS,
    CONF_ROOM_PRIORITY,
    DEFAULT_MIN_OTHER_ROOM_OPEN_PCT,
    DEFAULT_CLOSED_THRESHOLD_PCT,
    DEFAULT_RELIEF_OPEN_PCT,
    DEFAULT_MAX_RELIEF_ROOMS,
    DEFAULT_ROOM_HYSTERESIS_F,
    DEFAULT_OCCUPANCY_LINGER_MIN,
    DEFAULT_OCCUPANCY_LINGER_NIGHT_MIN,
    DEFAULT_HEAT_BOOST_F,
    DEFAULT_HVAC_MIN_RUNTIME_MIN,
    DEFAULT_HVAC_MIN_OFF_TIME_MIN,
    DEFAULT_DEFAULT_THERMOSTAT_TEMP,
    DEFAULT_ROOM_PRIORITY,
    DEFAULT_VENT_GRANULARITY,
    DEFAULT_MIN_ADJUSTMENT_PCT,
    DEFAULT_MIN_ADJUSTMENT_INTERVAL_MIN,
    DEFAULT_TEMP_ERROR_OVERRIDE_F,
    DEFAULT_CONVENTIONAL_VENT_COUNT,
    DEFAULT_CONTROL_STRATEGY,
    DEFAULT_POLL_INTERVAL_ACTIVE_SEC,
    DEFAULT_POLL_INTERVAL_IDLE_SEC,
    DEFAULT_AUTOMATION_COOLDOWN_SEC,
    CONTROL_STRATEGIES,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _num(
    min_val: float,
    max_val: float,
    step: float = 1,
    mode: str = "box",
    unit: str | None = None,
) -> selector.NumberSelector:
    """Build a NumberSelector with common defaults."""
    cfg = selector.NumberSelectorConfig(
        min=min_val,
        max=max_val,
        step=step,
        mode=selector.NumberSelectorMode(mode),
        **({"unit_of_measurement": unit} if unit else {}),
    )
    return selector.NumberSelector(cfg)


def _all_settings_defaults() -> dict[str, Any]:
    """Return a dict of every settings key with its default value."""
    return {
        "control_strategy": DEFAULT_CONTROL_STRATEGY,
        "vent_granularity": DEFAULT_VENT_GRANULARITY,
        "min_other_room_open_pct": DEFAULT_MIN_OTHER_ROOM_OPEN_PCT,
        "closed_threshold_pct": DEFAULT_CLOSED_THRESHOLD_PCT,
        "relief_open_pct": DEFAULT_RELIEF_OPEN_PCT,
        "max_relief_rooms": DEFAULT_MAX_RELIEF_ROOMS,
        "conventional_vent_count": DEFAULT_CONVENTIONAL_VENT_COUNT,
        "room_hysteresis_f": DEFAULT_ROOM_HYSTERESIS_F,
        "heat_boost_f": DEFAULT_HEAT_BOOST_F,
        "default_thermostat_temp": DEFAULT_DEFAULT_THERMOSTAT_TEMP,
        "temp_error_override_f": DEFAULT_TEMP_ERROR_OVERRIDE_F,
        "min_adjustment_pct": DEFAULT_MIN_ADJUSTMENT_PCT,
        "min_adjustment_interval_min": DEFAULT_MIN_ADJUSTMENT_INTERVAL_MIN,
        "hvac_min_runtime_min": DEFAULT_HVAC_MIN_RUNTIME_MIN,
        "hvac_min_off_time_min": DEFAULT_HVAC_MIN_OFF_TIME_MIN,
        "poll_interval_active_sec": DEFAULT_POLL_INTERVAL_ACTIVE_SEC,
        "poll_interval_idle_sec": DEFAULT_POLL_INTERVAL_IDLE_SEC,
        "automation_cooldown_sec": DEFAULT_AUTOMATION_COOLDOWN_SEC,
        "occupancy_linger_min": DEFAULT_OCCUPANCY_LINGER_MIN,
        "occupancy_linger_night_min": DEFAULT_OCCUPANCY_LINGER_NIGHT_MIN,
        "require_occupancy": True,
        "heat_boost_enabled": True,
        "auto_thermostat_control": True,
        "auto_vent_control": True,
        "debug_mode": False,
    }


# ---------------------------------------------------------------------------
# Per-step settings schemas
# ---------------------------------------------------------------------------

def _settings_algorithm_schema(defaults: dict | None = None) -> vol.Schema:
    d = defaults or {}
    return vol.Schema({
        vol.Optional("control_strategy",
                     default=d.get("control_strategy", DEFAULT_CONTROL_STRATEGY)):
            selector.SelectSelector(selector.SelectSelectorConfig(
                options=CONTROL_STRATEGIES,
                mode=selector.SelectSelectorMode.DROPDOWN,
                translation_key="control_strategy",
            )),
        vol.Optional("vent_granularity",
                     default=d.get("vent_granularity", DEFAULT_VENT_GRANULARITY)):
            _num(1, 50, step=1, unit="%"),
        vol.Optional("min_other_room_open_pct",
                     default=d.get("min_other_room_open_pct", DEFAULT_MIN_OTHER_ROOM_OPEN_PCT)):
            _num(0, 100, step=5, unit="%"),
        vol.Optional("closed_threshold_pct",
                     default=d.get("closed_threshold_pct", DEFAULT_CLOSED_THRESHOLD_PCT)):
            _num(0, 100, step=5, unit="%"),
        vol.Optional("relief_open_pct",
                     default=d.get("relief_open_pct", DEFAULT_RELIEF_OPEN_PCT)):
            _num(0, 100, step=5, unit="%"),
        vol.Optional("max_relief_rooms",
                     default=d.get("max_relief_rooms", DEFAULT_MAX_RELIEF_ROOMS)):
            _num(1, 10, step=1),
        vol.Optional("conventional_vent_count",
                     default=d.get("conventional_vent_count", DEFAULT_CONVENTIONAL_VENT_COUNT)):
            _num(0, 30, step=1),
    })


def _settings_temperature_schema(defaults: dict | None = None) -> vol.Schema:
    d = defaults or {}
    return vol.Schema({
        vol.Optional("room_hysteresis_f",
                     default=d.get("room_hysteresis_f", DEFAULT_ROOM_HYSTERESIS_F)):
            _num(0, 5, step=0.5, unit="°F"),
        vol.Optional("heat_boost_f",
                     default=d.get("heat_boost_f", DEFAULT_HEAT_BOOST_F)):
            _num(0, 5, step=0.5, unit="°F"),
        vol.Optional("default_thermostat_temp",
                     default=d.get("default_thermostat_temp", DEFAULT_DEFAULT_THERMOSTAT_TEMP)):
            _num(50, 90, step=1, unit="°F"),
        vol.Optional("temp_error_override_f",
                     default=d.get("temp_error_override_f", DEFAULT_TEMP_ERROR_OVERRIDE_F)):
            _num(0, 10, step=0.5, unit="°F"),
    })


def _settings_hvac_schema(defaults: dict | None = None) -> vol.Schema:
    d = defaults or {}
    return vol.Schema({
        vol.Optional("min_adjustment_pct",
                     default=d.get("min_adjustment_pct", DEFAULT_MIN_ADJUSTMENT_PCT)):
            _num(0, 50, step=5, unit="%"),
        vol.Optional("min_adjustment_interval_min",
                     default=d.get("min_adjustment_interval_min", DEFAULT_MIN_ADJUSTMENT_INTERVAL_MIN)):
            _num(0, 120, step=1, unit="min"),
        vol.Optional("hvac_min_runtime_min",
                     default=d.get("hvac_min_runtime_min", DEFAULT_HVAC_MIN_RUNTIME_MIN)):
            _num(0, 30, step=1, unit="min"),
        vol.Optional("hvac_min_off_time_min",
                     default=d.get("hvac_min_off_time_min", DEFAULT_HVAC_MIN_OFF_TIME_MIN)):
            _num(0, 30, step=1, unit="min"),
        vol.Optional("poll_interval_active_sec",
                     default=d.get("poll_interval_active_sec", DEFAULT_POLL_INTERVAL_ACTIVE_SEC)):
            _num(10, 300, step=5, unit="sec"),
        vol.Optional("poll_interval_idle_sec",
                     default=d.get("poll_interval_idle_sec", DEFAULT_POLL_INTERVAL_IDLE_SEC)):
            _num(30, 600, step=10, unit="sec"),
        vol.Optional("automation_cooldown_sec",
                     default=d.get("automation_cooldown_sec", DEFAULT_AUTOMATION_COOLDOWN_SEC)):
            _num(0, 300, step=5, unit="sec"),
    })


def _settings_behavior_schema(defaults: dict | None = None) -> vol.Schema:
    d = defaults or {}
    return vol.Schema({
        vol.Optional("occupancy_linger_min",
                     default=d.get("occupancy_linger_min", DEFAULT_OCCUPANCY_LINGER_MIN)):
            _num(0, 300, step=5, unit="min"),
        vol.Optional("occupancy_linger_night_min",
                     default=d.get("occupancy_linger_night_min", DEFAULT_OCCUPANCY_LINGER_NIGHT_MIN)):
            _num(0, 300, step=5, unit="min"),
        vol.Optional("require_occupancy", default=d.get("require_occupancy", True)):
            selector.BooleanSelector(),
        vol.Optional("heat_boost_enabled", default=d.get("heat_boost_enabled", True)):
            selector.BooleanSelector(),
        vol.Optional("auto_thermostat_control", default=d.get("auto_thermostat_control", True)):
            selector.BooleanSelector(),
        vol.Optional("auto_vent_control", default=d.get("auto_vent_control", True)):
            selector.BooleanSelector(),
        vol.Optional("debug_mode", default=d.get("debug_mode", False)):
            selector.BooleanSelector(),
    })


# ---------------------------------------------------------------------------
# Config flow
# ---------------------------------------------------------------------------

class SmartVentControllerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Smart Vent Controller."""

    VERSION = 1

    def __init__(self):
        self.data: dict[str, Any] = {}
        self.rooms: list[dict[str, Any]] = []
        self._settings: dict[str, Any] = {}
        # Reconfigure state
        self._reconfigure_rooms: list[dict[str, Any]] = []
        self._selected_room_index: int | None = None

    # ------------------------------------------------------------------
    # Import (programmatic / YAML migration)
    # ------------------------------------------------------------------

    async def async_step_import(self, import_info: dict[str, Any] | None = None) -> FlowResult:
        if import_info is None:
            return self.async_abort(reason="no_import_data")
        main_thermostat = import_info.get("main_thermostat")
        if not main_thermostat:
            return self.async_abort(reason="invalid_import_data")
        if main_thermostat not in self.hass.states.async_entity_ids("climate"):
            return self.async_abort(reason="invalid_thermostat")
        await self.async_set_unique_id(main_thermostat)
        self._abort_if_unique_id_configured()
        self.data[CONF_MAIN_THERMOSTAT] = main_thermostat
        self.data[CONF_ROOMS] = import_info.get("rooms", [])
        options = import_info.get("options", {})
        return self.async_create_entry(
            title=f"Smart Vent Controller ({main_thermostat})",
            data=self.data, options=options,
        )

    # ------------------------------------------------------------------
    # Step 1: Select thermostat
    # ------------------------------------------------------------------

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            main_thermostat = user_input[CONF_MAIN_THERMOSTAT]
            if main_thermostat not in self.hass.states.async_entity_ids("climate"):
                return self.async_show_form(
                    step_id="user",
                    errors={CONF_MAIN_THERMOSTAT: "invalid_thermostat"},
                )
            await self.async_set_unique_id(main_thermostat)
            self._abort_if_unique_id_configured()
            self.data[CONF_MAIN_THERMOSTAT] = main_thermostat
            return await self.async_step_rooms()

        climate_entities = sorted(self.hass.states.async_entity_ids("climate"))
        if not climate_entities:
            return self.async_abort(reason="no_climate_entities")

        from .migration import detect_yaml_config
        yaml_config = await detect_yaml_config(self.hass)
        has_yaml = yaml_config is not None

        schema_dict = {
            vol.Required(
                CONF_MAIN_THERMOSTAT,
                default=climate_entities[0] if climate_entities else None
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="climate")
            ),
        }
        if has_yaml:
            schema_dict[vol.Optional("migrate_from_yaml", default=False)] = bool

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(schema_dict),
            description_placeholders={
                "migration_note": "\n\nWe found an existing YAML configuration. You can migrate it or start fresh."
            } if has_yaml else {"migration_note": ""},
        )

    # ------------------------------------------------------------------
    # YAML migration
    # ------------------------------------------------------------------

    async def async_step_migrate(
        self, yaml_config=None, user_input=None
    ) -> FlowResult:
        from .migration import detect_yaml_config, validate_migration_config
        if yaml_config is None:
            yaml_config = await detect_yaml_config(self.hass)
        if yaml_config is None:
            return self.async_abort(reason="no_yaml_config")
        if user_input is None:
            is_valid, warnings = await validate_migration_config(self.hass, yaml_config)
            return self.async_show_form(
                step_id="migrate",
                data_schema=vol.Schema({
                    vol.Required("confirm_migration", default=True): bool,
                }),
                description_placeholders={
                    "rooms_count": str(len(yaml_config.get("rooms", []))),
                    "main_thermostat": yaml_config.get("main_thermostat", "Unknown"),
                    "warnings": "\n".join(f"- {w}" for w in warnings) if warnings else "None",
                },
                errors={} if is_valid else {"base": "validation_warnings"},
            )
        if not user_input.get("confirm_migration"):
            return await self.async_step_user()
        return await self.async_step_import(yaml_config)

    # ------------------------------------------------------------------
    # Step 2: Add rooms
    # ------------------------------------------------------------------

    async def async_step_rooms(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            room_name = (
                user_input.get("name")
                or user_input.get("room_name")
                or user_input.get(CONF_ROOM_NAME)
            )
            climate_entity = (
                user_input.get("climate_entity")
                or user_input.get(CONF_ROOM_CLIMATE)
            )
            temp_sensor = user_input.get("temp_sensor") or user_input.get(CONF_ROOM_TEMP_SENSOR) or ""
            occ_sensor = user_input.get("occupancy_sensor") or user_input.get(CONF_ROOM_OCCUPANCY_SENSOR) or ""
            vents = user_input.get("vent_entities") or user_input.get(CONF_ROOM_VENTS) or []
            priority = user_input.get("priority") or user_input.get(CONF_ROOM_PRIORITY) or DEFAULT_ROOM_PRIORITY

            if not room_name:
                return self.async_show_form(
                    step_id="rooms",
                    data_schema=self._rooms_schema(),
                    errors={"base": "name_required"},
                )

            room_data = {
                "name": room_name,
                "climate_entity": climate_entity,
                "temp_sensor": temp_sensor,
                "occupancy_sensor": occ_sensor,
                "vent_entities": vents if isinstance(vents, list) else [vents] if vents else [],
                "priority": int(priority) if priority else DEFAULT_ROOM_PRIORITY,
            }

            if user_input.get("add_another"):
                self.rooms.append(room_data)
                return await self.async_step_rooms()
            else:
                if room_name:
                    self.rooms.append(room_data)
                self.data[CONF_ROOMS] = self.rooms
                return await self.async_step_settings_intro()

        return self.async_show_form(
            step_id="rooms",
            data_schema=self._rooms_schema(),
        )

    def _rooms_schema(self) -> vol.Schema:
        return vol.Schema({
            vol.Optional(CONF_ROOM_NAME): str,
            vol.Optional(CONF_ROOM_CLIMATE): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="climate")
            ),
            vol.Optional(CONF_ROOM_TEMP_SENSOR): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(CONF_ROOM_OCCUPANCY_SENSOR): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="binary_sensor")
            ),
            vol.Optional(CONF_ROOM_VENTS): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="cover", multiple=True)
            ),
            vol.Optional(CONF_ROOM_PRIORITY, default=DEFAULT_ROOM_PRIORITY):
                selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0, max=10, step=1,
                        mode=selector.NumberSelectorMode.SLIDER,
                    )
                ),
            vol.Optional("add_another", default=False): bool,
        })

    # ------------------------------------------------------------------
    # Step 3: Settings intro (skip or customize)
    # ------------------------------------------------------------------

    async def async_step_settings_intro(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            if user_input.get("use_defaults", False):
                options = _all_settings_defaults()
                self.data.update(options)
                return self.async_create_entry(
                    title=f"Smart Vent Controller ({self.data[CONF_MAIN_THERMOSTAT]})",
                    data=self.data, options=options,
                )
            return await self.async_step_settings_algorithm()

        return self.async_show_form(
            step_id="settings_intro",
            data_schema=vol.Schema({
                vol.Optional("use_defaults", default=True):
                    selector.BooleanSelector(),
            }),
        )

    # ------------------------------------------------------------------
    # Step 3a: Algorithm & Vent Positioning
    # ------------------------------------------------------------------

    async def async_step_settings_algorithm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            self._settings.update(user_input)
            return await self.async_step_settings_temperature()
        return self.async_show_form(
            step_id="settings_algorithm",
            data_schema=_settings_algorithm_schema(),
        )

    # ------------------------------------------------------------------
    # Step 3b: Temperature & Setpoint Control
    # ------------------------------------------------------------------

    async def async_step_settings_temperature(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            self._settings.update(user_input)
            return await self.async_step_settings_hvac()
        return self.async_show_form(
            step_id="settings_temperature",
            data_schema=_settings_temperature_schema(),
        )

    # ------------------------------------------------------------------
    # Step 3c: HVAC Protection & Timing
    # ------------------------------------------------------------------

    async def async_step_settings_hvac(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            self._settings.update(user_input)
            return await self.async_step_settings_behavior()
        return self.async_show_form(
            step_id="settings_hvac",
            data_schema=_settings_hvac_schema(),
        )

    # ------------------------------------------------------------------
    # Step 3d: Occupancy & Automation
    # ------------------------------------------------------------------

    async def async_step_settings_behavior(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            self._settings.update(user_input)
            self.data.update(self._settings)
            return self.async_create_entry(
                title=f"Smart Vent Controller ({self.data[CONF_MAIN_THERMOSTAT]})",
                data=self.data, options=self._settings,
            )
        return self.async_show_form(
            step_id="settings_behavior",
            data_schema=_settings_behavior_schema(),
        )

    # ------------------------------------------------------------------
    # Reconfigure: Room Management
    # ------------------------------------------------------------------

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])

        if not self._reconfigure_rooms:
            self._reconfigure_rooms = copy.deepcopy(entry.data.get(CONF_ROOMS, []))

        if user_input is not None:
            action = user_input.get("action")
            if action == "add":
                return await self.async_step_add_room()
            elif action == "edit":
                return await self.async_step_select_room()
            elif action == "remove":
                return await self.async_step_remove_room()
            else:
                return self.async_abort(reason="reconfigure_successful")

        room_count = len(self._reconfigure_rooms)
        room_names = ", ".join(
            r.get("name", "Unknown") for r in self._reconfigure_rooms
        ) or "None"

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema({
                vol.Required("action", default="edit"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value="edit", label="Edit a Room"),
                            selector.SelectOptionDict(value="add", label="Add a New Room"),
                            selector.SelectOptionDict(value="remove", label="Remove a Room"),
                            selector.SelectOptionDict(value="done", label="Done"),
                        ],
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
            }),
            description_placeholders={
                "room_count": str(room_count),
                "room_names": room_names,
            },
        )

    async def async_step_select_room(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            self._selected_room_index = int(user_input["room_index"])
            return await self.async_step_edit_room()

        if not self._reconfigure_rooms:
            return self.async_show_form(
                step_id="select_room",
                data_schema=vol.Schema({}),
                errors={"base": "no_rooms"},
            )

        room_options = [
            selector.SelectOptionDict(
                value=str(i),
                label=room.get("name", f"Room {i + 1}"),
            )
            for i, room in enumerate(self._reconfigure_rooms)
        ]

        return self.async_show_form(
            step_id="select_room",
            data_schema=vol.Schema({
                vol.Required("room_index"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=room_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }),
        )

    async def async_step_edit_room(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        idx = self._selected_room_index
        room = self._reconfigure_rooms[idx]

        if user_input is not None:
            room_name = user_input.get(CONF_ROOM_NAME)
            climate_entity = user_input.get(CONF_ROOM_CLIMATE)

            if not room_name:
                return self.async_show_form(
                    step_id="edit_room",
                    data_schema=self._room_edit_schema(room),
                    errors={"base": "name_required"},
                    description_placeholders={"room_name": room.get("name", "")},
                )

            old_name = room.get("name", "")
            updated_room = {
                "name": room_name,
                "climate_entity": climate_entity,
                "temp_sensor": user_input.get(CONF_ROOM_TEMP_SENSOR, ""),
                "occupancy_sensor": user_input.get(CONF_ROOM_OCCUPANCY_SENSOR, ""),
                "vent_entities": user_input.get(CONF_ROOM_VENTS, []),
                "priority": int(user_input.get(CONF_ROOM_PRIORITY, DEFAULT_ROOM_PRIORITY)),
            }
            self._reconfigure_rooms[idx] = updated_room

            return await self._async_save_rooms_and_reload(
                old_room_names=[old_name] if old_name != room_name else []
            )

        return self.async_show_form(
            step_id="edit_room",
            data_schema=self._room_edit_schema(room),
            description_placeholders={"room_name": room.get("name", "")},
        )

    async def async_step_add_room(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            room_name = user_input.get(CONF_ROOM_NAME)
            climate_entity = user_input.get(CONF_ROOM_CLIMATE)

            if not room_name:
                return self.async_show_form(
                    step_id="add_room",
                    data_schema=self._room_edit_schema({}),
                    errors={"base": "name_required"},
                )

            existing_keys = [
                r.get("name", "").lower().replace(" ", "_")
                for r in self._reconfigure_rooms
            ]
            if room_name.lower().replace(" ", "_") in existing_keys:
                return self.async_show_form(
                    step_id="add_room",
                    data_schema=self._room_edit_schema({}),
                    errors={"base": "duplicate_room_name"},
                )

            new_room = {
                "name": room_name,
                "climate_entity": climate_entity,
                "temp_sensor": user_input.get(CONF_ROOM_TEMP_SENSOR, ""),
                "occupancy_sensor": user_input.get(CONF_ROOM_OCCUPANCY_SENSOR, ""),
                "vent_entities": user_input.get(CONF_ROOM_VENTS, []),
                "priority": int(user_input.get(CONF_ROOM_PRIORITY, DEFAULT_ROOM_PRIORITY)),
            }
            self._reconfigure_rooms.append(new_room)
            return await self._async_save_rooms_and_reload()

        return self.async_show_form(
            step_id="add_room",
            data_schema=self._room_edit_schema({}),
        )

    async def async_step_remove_room(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            self._selected_room_index = int(user_input["room_index"])
            return await self.async_step_confirm_remove()

        if not self._reconfigure_rooms:
            return self.async_show_form(
                step_id="remove_room",
                data_schema=vol.Schema({}),
                errors={"base": "no_rooms"},
            )

        room_options = [
            selector.SelectOptionDict(
                value=str(i),
                label=room.get("name", f"Room {i + 1}"),
            )
            for i, room in enumerate(self._reconfigure_rooms)
        ]

        return self.async_show_form(
            step_id="remove_room",
            data_schema=vol.Schema({
                vol.Required("room_index"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=room_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }),
        )

    async def async_step_confirm_remove(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        idx = self._selected_room_index
        room = self._reconfigure_rooms[idx]
        room_name = room.get("name", "Unknown")

        if user_input is not None:
            if user_input.get("confirm"):
                removed = self._reconfigure_rooms.pop(idx)
                return await self._async_save_rooms_and_reload(
                    old_room_names=[removed.get("name", "")]
                )
            return await self.async_step_reconfigure()

        return self.async_show_form(
            step_id="confirm_remove",
            data_schema=vol.Schema({
                vol.Required("confirm", default=False): selector.BooleanSelector(),
            }),
            description_placeholders={"room_name": room_name},
        )

    # ------------------------------------------------------------------
    # Reconfigure helpers
    # ------------------------------------------------------------------

    def _room_edit_schema(self, room: dict) -> vol.Schema:
        """Build a room edit schema pre-filled with existing data."""
        return vol.Schema({
            vol.Required(CONF_ROOM_NAME, default=room.get("name", "")): str,
            vol.Optional(CONF_ROOM_CLIMATE, default=room.get("climate_entity", "")):
                selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="climate")
                ),
            vol.Optional(CONF_ROOM_TEMP_SENSOR, default=room.get("temp_sensor", "")):
                selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
            vol.Optional(CONF_ROOM_OCCUPANCY_SENSOR, default=room.get("occupancy_sensor", "")):
                selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="binary_sensor")
                ),
            vol.Optional(CONF_ROOM_VENTS, default=room.get("vent_entities", [])):
                selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="cover", multiple=True)
                ),
            vol.Optional(CONF_ROOM_PRIORITY, default=room.get("priority", DEFAULT_ROOM_PRIORITY)):
                selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0, max=10, step=1,
                        mode=selector.NumberSelectorMode.SLIDER,
                    )
                ),
        })

    async def _async_save_rooms_and_reload(
        self, old_room_names: list[str] | None = None
    ) -> FlowResult:
        """Save updated rooms and reload the integration."""
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])

        if old_room_names:
            device_registry = dr.async_get(self.hass)
            entity_registry = er.async_get(self.hass)
            for name in old_room_names:
                room_key = name.lower().replace(" ", "_")
                device_id = (DOMAIN, f"{entry.entry_id}_{room_key}")
                device = device_registry.async_get_device(identifiers={device_id})
                if device:
                    entities = er.async_entries_for_device(
                        entity_registry, device.id, include_disabled_entities=True
                    )
                    for entity_entry in entities:
                        entity_registry.async_remove(entity_entry.entity_id)
                    device_registry.async_remove_device(device.id)

        new_data = dict(entry.data)
        new_data[CONF_ROOMS] = self._reconfigure_rooms

        return self.async_update_reload_and_abort(
            entry,
            data=new_data,
            reason="reconfigure_successful",
        )

    # ------------------------------------------------------------------
    # Options flow registration
    # ------------------------------------------------------------------

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return SmartVentControllerOptionsFlowHandler(config_entry)


# ---------------------------------------------------------------------------
# Options flow
# ---------------------------------------------------------------------------

class SmartVentControllerOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Smart Vent Controller."""

    def __init__(self, config_entry):
        self._options: dict[str, Any] = {}

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        self._options = dict(self.config_entry.options or {})
        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "settings_algorithm",
                "settings_temperature",
                "settings_hvac",
                "settings_behavior",
            ],
        )

    async def async_step_settings_algorithm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            self._options.update(user_input)
            return self.async_create_entry(title="", data=self._options)
        return self.async_show_form(
            step_id="settings_algorithm",
            data_schema=_settings_algorithm_schema(self._options),
        )

    async def async_step_settings_temperature(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            self._options.update(user_input)
            return self.async_create_entry(title="", data=self._options)
        return self.async_show_form(
            step_id="settings_temperature",
            data_schema=_settings_temperature_schema(self._options),
        )

    async def async_step_settings_hvac(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            self._options.update(user_input)
            return self.async_create_entry(title="", data=self._options)
        return self.async_show_form(
            step_id="settings_hvac",
            data_schema=_settings_hvac_schema(self._options),
        )

    async def async_step_settings_behavior(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            self._options.update(user_input)
            return self.async_create_entry(title="", data=self._options)
        return self.async_show_form(
            step_id="settings_behavior",
            data_schema=_settings_behavior_schema(self._options),
        )
