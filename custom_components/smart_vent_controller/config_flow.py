"""Config flow for Smart Vent Controller integration."""

from typing import Any
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector

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
    CONTROL_STRATEGIES,
)


async def _get_description(hass, step: str, key: str) -> str:
    """Get description for a config field from translations."""
    try:
        from homeassistant.helpers.translation import async_get_translations
        translations = await async_get_translations(
            hass, hass.config.language, "config", [DOMAIN]
        )
        desc_key = f"config.step.{step}.data.{key}_description"
        return translations.get(desc_key, "")
    except Exception:
        return ""


class SmartVentControllerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Smart Vent Controller."""

    VERSION = 1

    def __init__(self):
        self.data = {}
        self.rooms = []

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
                "migration_note": "We found an existing YAML configuration. You can migrate it or start fresh."
            } if has_yaml else {},
        )

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

            if not room_name or not climate_entity:
                return self.async_show_form(
                    step_id="rooms",
                    data_schema=self._rooms_schema(),
                    errors={"base": "name_and_climate_required"},
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
                return await self.async_step_settings()

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

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            if "heat_boost_f" in user_input:
                user_input["heat_boost_f"] = float(user_input["heat_boost_f"])
            if "room_hysteresis_f" in user_input:
                user_input["room_hysteresis_f"] = float(user_input["room_hysteresis_f"])
            options = dict(user_input)
            self.data.update(user_input)
            return self.async_create_entry(
                title=f"Smart Vent Controller ({self.data[CONF_MAIN_THERMOSTAT]})",
                data=self.data, options=options,
            )

        return self.async_show_form(
            step_id="settings",
            data_schema=_settings_schema(),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return SmartVentControllerOptionsFlowHandler(config_entry)


class SmartVentControllerOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Smart Vent Controller."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            if "heat_boost_f" in user_input:
                user_input["heat_boost_f"] = float(user_input["heat_boost_f"])
            if "room_hysteresis_f" in user_input:
                user_input["room_hysteresis_f"] = float(user_input["room_hysteresis_f"])
            if "temp_error_override_f" in user_input:
                user_input["temp_error_override_f"] = float(user_input["temp_error_override_f"])
            return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.options or {}
        if "heat_boost_f" in current and isinstance(current["heat_boost_f"], int):
            current["heat_boost_f"] = float(current["heat_boost_f"])
        if "room_hysteresis_f" in current and isinstance(current["room_hysteresis_f"], int):
            current["room_hysteresis_f"] = float(current["room_hysteresis_f"])

        return self.async_show_form(
            step_id="init",
            data_schema=_settings_schema(current),
        )


def _settings_schema(defaults: dict | None = None) -> vol.Schema:
    """Build settings schema used by both initial config and options flow."""
    d = defaults or {}
    return vol.Schema({
        vol.Optional("min_other_room_open_pct",
                     default=d.get("min_other_room_open_pct", DEFAULT_MIN_OTHER_ROOM_OPEN_PCT)):
            vol.All(int, vol.Range(min=0, max=100)),
        vol.Optional("closed_threshold_pct",
                     default=d.get("closed_threshold_pct", DEFAULT_CLOSED_THRESHOLD_PCT)):
            vol.All(int, vol.Range(min=0, max=100)),
        vol.Optional("relief_open_pct",
                     default=d.get("relief_open_pct", DEFAULT_RELIEF_OPEN_PCT)):
            vol.All(int, vol.Range(min=0, max=100)),
        vol.Optional("max_relief_rooms",
                     default=d.get("max_relief_rooms", DEFAULT_MAX_RELIEF_ROOMS)):
            vol.All(int, vol.Range(min=1, max=10)),
        vol.Optional("room_hysteresis_f",
                     default=d.get("room_hysteresis_f", DEFAULT_ROOM_HYSTERESIS_F)):
            vol.All(float, vol.Range(min=0, max=5)),
        vol.Optional("hvac_min_runtime_min",
                     default=d.get("hvac_min_runtime_min", DEFAULT_HVAC_MIN_RUNTIME_MIN)):
            vol.All(int, vol.Range(min=0, max=30)),
        vol.Optional("hvac_min_off_time_min",
                     default=d.get("hvac_min_off_time_min", DEFAULT_HVAC_MIN_OFF_TIME_MIN)):
            vol.All(int, vol.Range(min=0, max=30)),
        vol.Optional("occupancy_linger_min",
                     default=d.get("occupancy_linger_min", DEFAULT_OCCUPANCY_LINGER_MIN)):
            vol.All(int, vol.Range(min=0, max=300)),
        vol.Optional("occupancy_linger_night_min",
                     default=d.get("occupancy_linger_night_min", DEFAULT_OCCUPANCY_LINGER_NIGHT_MIN)):
            vol.All(int, vol.Range(min=0, max=300)),
        vol.Optional("heat_boost_f",
                     default=d.get("heat_boost_f", DEFAULT_HEAT_BOOST_F)):
            vol.All(float, vol.Range(min=0, max=3)),
        vol.Optional("default_thermostat_temp",
                     default=d.get("default_thermostat_temp", DEFAULT_DEFAULT_THERMOSTAT_TEMP)):
            vol.All(int, vol.Range(min=65, max=80)),
        vol.Optional("automation_cooldown_sec",
                     default=d.get("automation_cooldown_sec", 30)):
            vol.All(int, vol.Range(min=0, max=300)),
        vol.Optional("require_occupancy", default=d.get("require_occupancy", True)): bool,
        vol.Optional("heat_boost_enabled", default=d.get("heat_boost_enabled", True)): bool,
        vol.Optional("auto_thermostat_control", default=d.get("auto_thermostat_control", True)): bool,
        vol.Optional("auto_vent_control", default=d.get("auto_vent_control", True)): bool,
        vol.Optional("debug_mode", default=d.get("debug_mode", False)): bool,
        # --- new algorithm options ---
        vol.Optional("control_strategy",
                     default=d.get("control_strategy", DEFAULT_CONTROL_STRATEGY)):
            vol.In(CONTROL_STRATEGIES),
        vol.Optional("vent_granularity",
                     default=d.get("vent_granularity", DEFAULT_VENT_GRANULARITY)):
            vol.All(int, vol.Range(min=1, max=50)),
        vol.Optional("min_adjustment_pct",
                     default=d.get("min_adjustment_pct", DEFAULT_MIN_ADJUSTMENT_PCT)):
            vol.All(int, vol.Range(min=0, max=50)),
        vol.Optional("min_adjustment_interval_min",
                     default=d.get("min_adjustment_interval_min", DEFAULT_MIN_ADJUSTMENT_INTERVAL_MIN)):
            vol.All(int, vol.Range(min=0, max=120)),
        vol.Optional("temp_error_override_f",
                     default=d.get("temp_error_override_f", DEFAULT_TEMP_ERROR_OVERRIDE_F)):
            vol.All(float, vol.Range(min=0, max=10)),
        vol.Optional("conventional_vent_count",
                     default=d.get("conventional_vent_count", DEFAULT_CONVENTIONAL_VENT_COUNT)):
            vol.All(int, vol.Range(min=0, max=30)),
        vol.Optional("poll_interval_active_sec",
                     default=d.get("poll_interval_active_sec", DEFAULT_POLL_INTERVAL_ACTIVE_SEC)):
            vol.All(int, vol.Range(min=10, max=300)),
        vol.Optional("poll_interval_idle_sec",
                     default=d.get("poll_interval_idle_sec", DEFAULT_POLL_INTERVAL_IDLE_SEC)):
            vol.All(int, vol.Range(min=30, max=600)),
    })
