"""Config flow for Smart Vent Controller integration."""

from typing import Any
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector
from homeassistant.helpers.translation import async_get_translations

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
)


class SmartVentControllerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Smart Vent Controller."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self.data = {}
        self.rooms = []
    
    async def _get_description(self, step: str, key: str) -> str:
        """Get description for a config field from translations."""
        try:
            translations = await async_get_translations(
                self.hass, self.hass.config.language, "config", [DOMAIN]
            )
            desc_key = f"config.step.{step}.data.{key}_description"
            return translations.get(desc_key, "")
        except Exception:
            return ""
    
    async def async_step_import(self, import_info: dict[str, Any] | None = None) -> FlowResult:
        """Handle import from YAML configuration.
        
        Args:
            import_info: Imported configuration data
        
        Returns:
            Flow result
        """
        if import_info is None:
            return self.async_abort(reason="no_import_data")
        
        # Validate imported data
        main_thermostat = import_info.get("main_thermostat")
        if not main_thermostat:
            return self.async_abort(reason="invalid_import_data")
        
        # Validate thermostat exists
        if main_thermostat not in self.hass.states.async_entity_ids("climate"):
            return self.async_abort(reason="invalid_thermostat")
        
        # Check if this thermostat is already configured
        # Use thermostat entity ID as unique identifier to allow multiple thermostats
        await self.async_set_unique_id(main_thermostat)
        self._abort_if_unique_id_configured()
        
        # Set up data
        self.data[CONF_MAIN_THERMOSTAT] = main_thermostat
        self.data[CONF_ROOMS] = import_info.get("rooms", [])
        
        # Set up options
        options = import_info.get("options", {})
        
        # Create entry
        return self.async_create_entry(
            title=f"Smart Vent Controller ({main_thermostat})",
            data=self.data,
            options=options,
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            main_thermostat = user_input[CONF_MAIN_THERMOSTAT]
            
            # Validate thermostat exists
            if main_thermostat not in self.hass.states.async_entity_ids("climate"):
                return self.async_show_form(
                    step_id="user",
                    errors={CONF_MAIN_THERMOSTAT: "invalid_thermostat"},
                )
            
            # Check if this thermostat is already configured
            # Use thermostat entity ID as unique identifier to allow multiple thermostats
            await self.async_set_unique_id(main_thermostat)
            self._abort_if_unique_id_configured()
            
            self.data[CONF_MAIN_THERMOSTAT] = main_thermostat
            return await self.async_step_rooms()

        # Get available climate entities
        climate_entities = sorted([
            entity_id for entity_id in self.hass.states.async_entity_ids("climate")
        ])

        if not climate_entities:
            return self.async_abort(reason="no_climate_entities")

        # Check for YAML config
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
        self, yaml_config: dict[str, Any] | None = None, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle migration from YAML configuration."""
        from .migration import detect_yaml_config, validate_migration_config
        
        if yaml_config is None:
            yaml_config = await detect_yaml_config(self.hass)
        
        if yaml_config is None:
            return self.async_abort(reason="no_yaml_config")
        
        if user_input is None:
            # Validate configuration
            is_valid, warnings = await validate_migration_config(self.hass, yaml_config)
            
            # Show migration form
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
        
        # Import configuration
        return await self.async_step_import(yaml_config)

    async def async_step_rooms(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle room configuration step."""
        if user_input is not None:
            # Handle both "name" and "room_name" for compatibility
            room_name = user_input.get("name") or user_input.get("room_name") or user_input.get(CONF_ROOM_NAME)
            climate_entity = user_input.get("climate_entity") or user_input.get(CONF_ROOM_CLIMATE)
            temp_sensor = user_input.get("temp_sensor") or user_input.get(CONF_ROOM_TEMP_SENSOR) or ""
            occupancy_sensor = user_input.get("occupancy_sensor") or user_input.get(CONF_ROOM_OCCUPANCY_SENSOR) or ""
            vent_entities = user_input.get("vent_entities") or user_input.get(CONF_ROOM_VENTS) or []
            priority = user_input.get("priority") or user_input.get(CONF_ROOM_PRIORITY) or DEFAULT_ROOM_PRIORITY
            
            _LOGGER.debug(
                "Room configuration received: name=%s, climate=%s, vents=%s, add_another=%s",
                room_name,
                climate_entity,
                len(vent_entities) if isinstance(vent_entities, list) else 0,
                user_input.get("add_another", False)
            )
            
            # Validate required fields
            if not room_name or not climate_entity:
                return self.async_show_form(
                    step_id="rooms",
                    data_schema=vol.Schema({
                        vol.Required(CONF_ROOM_NAME): str,
                        vol.Required(CONF_ROOM_CLIMATE): selector.EntitySelector(
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
                        vol.Optional(
                            CONF_ROOM_PRIORITY,
                            default=DEFAULT_ROOM_PRIORITY
                        ): selector.NumberSelector(
                            selector.NumberSelectorConfig(
                                min=0,
                                max=10,
                                step=1,
                                mode=selector.NumberSelectorMode.SLIDER
                            )
                        ),
                        vol.Optional("add_another", default=False): bool,
                    }),
                    errors={"base": "name_and_climate_required"},
                )
            
            if user_input.get("add_another"):
                # Add room and continue to add another
                room_data = {
                    "name": room_name,
                    "climate_entity": climate_entity,
                    "temp_sensor": temp_sensor,
                    "occupancy_sensor": occupancy_sensor,
                    "vent_entities": vent_entities if isinstance(vent_entities, list) else [vent_entities] if vent_entities else [],
                    "priority": int(priority) if priority else DEFAULT_ROOM_PRIORITY,
                }
                self.rooms.append(room_data)
                _LOGGER.info("Added room '%s', total rooms: %d", room_name, len(self.rooms))
                # Show form again to add another room (with empty form)
                return await self.async_step_rooms()
            else:
                # Done adding rooms, move to settings
                if room_name:
                    self.rooms.append({
                        "name": room_name,
                        "climate_entity": climate_entity,
                        "temp_sensor": temp_sensor,
                        "occupancy_sensor": occupancy_sensor,
                        "vent_entities": vent_entities if isinstance(vent_entities, list) else [vent_entities] if vent_entities else [],
                        "priority": int(priority) if priority else DEFAULT_ROOM_PRIORITY,
                    })
                self.data[CONF_ROOMS] = self.rooms
                return await self.async_step_settings()

        # Get available entities for dropdowns
        climate_entities = sorted([
            entity_id for entity_id in self.hass.states.async_entity_ids("climate")
        ])
        temp_sensors = sorted([
            entity_id for entity_id in self.hass.states.async_entity_ids("sensor")
            if "temp" in entity_id.lower()
        ])
        occupancy_sensors = sorted([
            entity_id for entity_id in self.hass.states.async_entity_ids("binary_sensor")
            if "occup" in entity_id.lower()
        ])
        vent_entities = sorted([
            entity_id for entity_id in self.hass.states.async_entity_ids("cover")
        ])

        # Get descriptions from translations
        room_name_desc = await self._get_description("rooms", "room_name")
        climate_desc = await self._get_description("rooms", "climate_entity")
        temp_sensor_desc = await self._get_description("rooms", "temp_sensor")
        occupancy_desc = await self._get_description("rooms", "occupancy_sensor")
        vents_desc = await self._get_description("rooms", "vent_entities")
        priority_desc = await self._get_description("rooms", "priority")
        add_another_desc = await self._get_description("rooms", "add_another")
        
        schema_dict = {
            vol.Optional(CONF_ROOM_NAME, description=room_name_desc): str,
            vol.Optional(CONF_ROOM_CLIMATE, description=climate_desc): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="climate")
            ),
            vol.Optional(CONF_ROOM_TEMP_SENSOR, description=temp_sensor_desc): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(CONF_ROOM_OCCUPANCY_SENSOR, description=occupancy_desc): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="binary_sensor")
            ),
            vol.Optional(CONF_ROOM_VENTS, description=vents_desc): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="cover", multiple=True)
            ),
            vol.Optional(
                CONF_ROOM_PRIORITY,
                default=DEFAULT_ROOM_PRIORITY,
                description=priority_desc
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=10,
                    step=1,
                    mode=selector.NumberSelectorMode.SLIDER
                )
            ),
            vol.Optional("add_another", default=False, description=add_another_desc): bool,
        }
        
        return self.async_show_form(
            step_id="rooms",
            data_schema=vol.Schema(schema_dict),
        )

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle settings configuration step."""
        if user_input is not None:
            # Ensure float fields are actually floats
            if "heat_boost_f" in user_input:
                user_input["heat_boost_f"] = float(user_input["heat_boost_f"])
            if "room_hysteresis_f" in user_input:
                user_input["room_hysteresis_f"] = float(user_input["room_hysteresis_f"])
            
            # Store settings in options, not data
            options = {}
            options.update(user_input)
            self.data.update(user_input)  # Keep in data for initial setup
            
            return self.async_create_entry(
                title=f"Smart Vent Controller ({self.data[CONF_MAIN_THERMOSTAT]})",
                data=self.data,
                options=options,
            )

        # Get descriptions from translations
        min_other_desc = await self._get_description("settings", "min_other_room_open_pct")
        closed_threshold_desc = await self._get_description("settings", "closed_threshold_pct")
        relief_open_desc = await self._get_description("settings", "relief_open_pct")
        max_relief_desc = await self._get_description("settings", "max_relief_rooms")
        hysteresis_desc = await self._get_description("settings", "room_hysteresis_f")
        runtime_desc = await self._get_description("settings", "hvac_min_runtime_min")
        off_time_desc = await self._get_description("settings", "hvac_min_off_time_min")
        linger_day_desc = await self._get_description("settings", "occupancy_linger_min")
        linger_night_desc = await self._get_description("settings", "occupancy_linger_night_min")
        heat_boost_desc = await self._get_description("settings", "heat_boost_f")
        default_temp_desc = await self._get_description("settings", "default_thermostat_temp")
        cooldown_desc = await self._get_description("settings", "automation_cooldown_sec")
        require_occ_desc = await self._get_description("settings", "require_occupancy")
        boost_enabled_desc = await self._get_description("settings", "heat_boost_enabled")
        auto_thermo_desc = await self._get_description("settings", "auto_thermostat_control")
        auto_vent_desc = await self._get_description("settings", "auto_vent_control")
        debug_desc = await self._get_description("settings", "debug_mode")
        
        return self.async_show_form(
            step_id="settings",
            data_schema=vol.Schema({
                vol.Optional(
                    "min_other_room_open_pct",
                    default=DEFAULT_MIN_OTHER_ROOM_OPEN_PCT,
                    description=min_other_desc
                ): vol.All(int, vol.Range(min=0, max=100)),
                vol.Optional(
                    "closed_threshold_pct",
                    default=DEFAULT_CLOSED_THRESHOLD_PCT,
                    description=closed_threshold_desc
                ): vol.All(int, vol.Range(min=0, max=100)),
                vol.Optional(
                    "relief_open_pct",
                    default=DEFAULT_RELIEF_OPEN_PCT,
                    description=relief_open_desc
                ): vol.All(int, vol.Range(min=0, max=100)),
                vol.Optional(
                    "max_relief_rooms",
                    default=DEFAULT_MAX_RELIEF_ROOMS,
                    description=max_relief_desc
                ): vol.All(int, vol.Range(min=1, max=10)),
                vol.Optional(
                    "room_hysteresis_f",
                    default=DEFAULT_ROOM_HYSTERESIS_F,
                    description=hysteresis_desc
                ): vol.All(float, vol.Range(min=0, max=5)),
                vol.Optional(
                    "hvac_min_runtime_min",
                    default=DEFAULT_HVAC_MIN_RUNTIME_MIN,
                    description=runtime_desc
                ): vol.All(int, vol.Range(min=0, max=30)),
                vol.Optional(
                    "hvac_min_off_time_min",
                    default=DEFAULT_HVAC_MIN_OFF_TIME_MIN,
                    description=off_time_desc
                ): vol.All(int, vol.Range(min=0, max=30)),
                vol.Optional(
                    "occupancy_linger_min",
                    default=DEFAULT_OCCUPANCY_LINGER_MIN,
                    description=linger_day_desc
                ): vol.All(int, vol.Range(min=0, max=300)),
                vol.Optional(
                    "occupancy_linger_night_min",
                    default=DEFAULT_OCCUPANCY_LINGER_NIGHT_MIN,
                    description=linger_night_desc
                ): vol.All(int, vol.Range(min=0, max=300)),
                vol.Optional(
                    "heat_boost_f",
                    default=DEFAULT_HEAT_BOOST_F,
                    description=heat_boost_desc
                ): vol.All(float, vol.Range(min=0, max=3)),
                vol.Optional(
                    "default_thermostat_temp",
                    default=DEFAULT_DEFAULT_THERMOSTAT_TEMP,
                    description=default_temp_desc
                ): vol.All(int, vol.Range(min=65, max=80)),
                vol.Optional(
                    "automation_cooldown_sec",
                    default=30,
                    description=cooldown_desc
                ): vol.All(int, vol.Range(min=0, max=300)),
                vol.Optional(
                    "require_occupancy",
                    default=True,
                    description=require_occ_desc
                ): bool,
                vol.Optional(
                    "heat_boost_enabled",
                    default=True,
                    description=boost_enabled_desc
                ): bool,
                vol.Optional(
                    "auto_thermostat_control",
                    default=True,
                    description=auto_thermo_desc
                ): bool,
                vol.Optional(
                    "auto_vent_control",
                    default=True,
                    description=auto_vent_desc
                ): bool,
                vol.Optional(
                    "debug_mode",
                    default=False,
                    description=debug_desc
                ): bool,
            }),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        """Return options flow handler."""
        return SmartVentControllerOptionsFlowHandler(config_entry)


class SmartVentControllerOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Smart Vent Controller."""
    
    def __init__(self, config_entry: config_entries.ConfigEntry):
        """Initialize options flow."""
        self.config_entry = config_entry
    
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            # Ensure heat_boost_f is a float
            if "heat_boost_f" in user_input:
                user_input["heat_boost_f"] = float(user_input["heat_boost_f"])
            # Ensure room_hysteresis_f is a float
            if "room_hysteresis_f" in user_input:
                user_input["room_hysteresis_f"] = float(user_input["room_hysteresis_f"])
            # Update options
            return self.async_create_entry(title="", data=user_input)
        
        # Get current options
        current_options = self.config_entry.options or {}
        
        # Convert integer values to floats for float fields
        if "heat_boost_f" in current_options and isinstance(current_options["heat_boost_f"], int):
            current_options["heat_boost_f"] = float(current_options["heat_boost_f"])
        if "room_hysteresis_f" in current_options and isinstance(current_options["room_hysteresis_f"], int):
            current_options["room_hysteresis_f"] = float(current_options["room_hysteresis_f"])
        
        # Get descriptions from translations
        min_other_desc = await self._get_description("min_other_room_open_pct")
        closed_threshold_desc = await self._get_description("closed_threshold_pct")
        relief_open_desc = await self._get_description("relief_open_pct")
        max_relief_desc = await self._get_description("max_relief_rooms")
        hysteresis_desc = await self._get_description("room_hysteresis_f")
        runtime_desc = await self._get_description("hvac_min_runtime_min")
        off_time_desc = await self._get_description("hvac_min_off_time_min")
        linger_day_desc = await self._get_description("occupancy_linger_min")
        linger_night_desc = await self._get_description("occupancy_linger_night_min")
        heat_boost_desc = await self._get_description("heat_boost_f")
        default_temp_desc = await self._get_description("default_thermostat_temp")
        cooldown_desc = await self._get_description("automation_cooldown_sec")
        require_occ_desc = await self._get_description("require_occupancy")
        boost_enabled_desc = await self._get_description("heat_boost_enabled")
        auto_thermo_desc = await self._get_description("auto_thermostat_control")
        auto_vent_desc = await self._get_description("auto_vent_control")
        debug_desc = await self._get_description("debug_mode")
        
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    "min_other_room_open_pct",
                    default=current_options.get("min_other_room_open_pct", DEFAULT_MIN_OTHER_ROOM_OPEN_PCT),
                    description=min_other_desc
                ): vol.All(int, vol.Range(min=0, max=100)),
                vol.Optional(
                    "closed_threshold_pct",
                    default=current_options.get("closed_threshold_pct", DEFAULT_CLOSED_THRESHOLD_PCT),
                    description=closed_threshold_desc
                ): vol.All(int, vol.Range(min=0, max=100)),
                vol.Optional(
                    "relief_open_pct",
                    default=current_options.get("relief_open_pct", DEFAULT_RELIEF_OPEN_PCT),
                    description=relief_open_desc
                ): vol.All(int, vol.Range(min=0, max=100)),
                vol.Optional(
                    "max_relief_rooms",
                    default=current_options.get("max_relief_rooms", DEFAULT_MAX_RELIEF_ROOMS),
                    description=max_relief_desc
                ): vol.All(int, vol.Range(min=1, max=10)),
                vol.Optional(
                    "room_hysteresis_f",
                    default=current_options.get("room_hysteresis_f", DEFAULT_ROOM_HYSTERESIS_F),
                    description=hysteresis_desc
                ): vol.All(float, vol.Range(min=0, max=5)),
                vol.Optional(
                    "hvac_min_runtime_min",
                    default=current_options.get("hvac_min_runtime_min", DEFAULT_HVAC_MIN_RUNTIME_MIN),
                    description=runtime_desc
                ): vol.All(int, vol.Range(min=0, max=30)),
                vol.Optional(
                    "hvac_min_off_time_min",
                    default=current_options.get("hvac_min_off_time_min", DEFAULT_HVAC_MIN_OFF_TIME_MIN),
                    description=off_time_desc
                ): vol.All(int, vol.Range(min=0, max=30)),
                vol.Optional(
                    "occupancy_linger_min",
                    default=current_options.get("occupancy_linger_min", DEFAULT_OCCUPANCY_LINGER_MIN),
                    description=linger_day_desc
                ): vol.All(int, vol.Range(min=0, max=300)),
                vol.Optional(
                    "occupancy_linger_night_min",
                    default=current_options.get("occupancy_linger_night_min", DEFAULT_OCCUPANCY_LINGER_NIGHT_MIN),
                    description=linger_night_desc
                ): vol.All(int, vol.Range(min=0, max=300)),
                vol.Optional(
                    "heat_boost_f",
                    default=current_options.get("heat_boost_f", DEFAULT_HEAT_BOOST_F),
                    description=heat_boost_desc
                ): vol.All(float, vol.Range(min=0, max=3)),
                vol.Optional(
                    "default_thermostat_temp",
                    default=current_options.get("default_thermostat_temp", DEFAULT_DEFAULT_THERMOSTAT_TEMP),
                    description=default_temp_desc
                ): vol.All(int, vol.Range(min=65, max=80)),
                vol.Optional(
                    "automation_cooldown_sec",
                    default=current_options.get("automation_cooldown_sec", 30),
                    description=cooldown_desc
                ): vol.All(int, vol.Range(min=0, max=300)),
                vol.Optional(
                    "require_occupancy",
                    default=current_options.get("require_occupancy", True),
                    description=require_occ_desc
                ): bool,
                vol.Optional(
                    "heat_boost_enabled",
                    default=current_options.get("heat_boost_enabled", True),
                    description=boost_enabled_desc
                ): bool,
                vol.Optional(
                    "auto_thermostat_control",
                    default=current_options.get("auto_thermostat_control", True),
                    description=auto_thermo_desc
                ): bool,
                vol.Optional(
                    "auto_vent_control",
                    default=current_options.get("auto_vent_control", True),
                    description=auto_vent_desc
                ): bool,
                vol.Optional(
                    "debug_mode",
                    default=current_options.get("debug_mode", False),
                    description=debug_desc
                ): bool,
            }),
        )
