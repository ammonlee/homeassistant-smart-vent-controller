"""Config flow for Smart Vent Controller integration."""

from typing import Any
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector

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
    
    async def async_step_import(self, import_info: dict[str, Any] | None = None) -> FlowResult:
        """Handle import from YAML configuration.
        
        Args:
            import_info: Imported configuration data
        
        Returns:
            Flow result
        """
        if import_info is None:
            return self.async_abort(reason="no_import_data")
        
        # Check if already configured
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        
        # Validate imported data
        main_thermostat = import_info.get("main_thermostat")
        if not main_thermostat:
            return self.async_abort(reason="invalid_import_data")
        
        # Validate thermostat exists
        if main_thermostat not in self.hass.states.async_entity_ids("climate"):
            return self.async_abort(reason="invalid_thermostat")
        
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
            # Validate thermostat exists
            if user_input[CONF_MAIN_THERMOSTAT] not in self.hass.states.async_entity_ids("climate"):
                return self.async_show_form(
                    step_id="user",
                    errors={CONF_MAIN_THERMOSTAT: "invalid_thermostat"},
                )
            
            self.data[CONF_MAIN_THERMOSTAT] = user_input[CONF_MAIN_THERMOSTAT]
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
                # Add room and continue
                self.rooms.append({
                    "name": room_name,
                    "climate_entity": climate_entity,
                    "temp_sensor": temp_sensor,
                    "occupancy_sensor": occupancy_sensor,
                    "vent_entities": vent_entities if isinstance(vent_entities, list) else [vent_entities] if vent_entities else [],
                    "priority": int(priority) if priority else DEFAULT_ROOM_PRIORITY,
                })
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

        schema_dict = {
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
            # Store settings in options, not data
            options = {}
            options.update(user_input)
            self.data.update(user_input)  # Keep in data for initial setup
            
            return self.async_create_entry(
                title=f"Smart Vent Controller ({self.data[CONF_MAIN_THERMOSTAT]})",
                data=self.data,
                options=options,
            )

        return self.async_show_form(
            step_id="settings",
            data_schema=vol.Schema({
                vol.Optional(
                    "min_other_room_open_pct",
                    default=DEFAULT_MIN_OTHER_ROOM_OPEN_PCT
                ): vol.All(int, vol.Range(min=0, max=100)),
                vol.Optional(
                    "closed_threshold_pct",
                    default=DEFAULT_CLOSED_THRESHOLD_PCT
                ): vol.All(int, vol.Range(min=0, max=100)),
                vol.Optional(
                    "relief_open_pct",
                    default=DEFAULT_RELIEF_OPEN_PCT
                ): vol.All(int, vol.Range(min=0, max=100)),
                vol.Optional(
                    "max_relief_rooms",
                    default=DEFAULT_MAX_RELIEF_ROOMS
                ): vol.All(int, vol.Range(min=1, max=10)),
                vol.Optional(
                    "room_hysteresis_f",
                    default=DEFAULT_ROOM_HYSTERESIS_F
                ): vol.All(float, vol.Range(min=0, max=5)),
                vol.Optional(
                    "hvac_min_runtime_min",
                    default=DEFAULT_HVAC_MIN_RUNTIME_MIN
                ): vol.All(int, vol.Range(min=0, max=30)),
                vol.Optional(
                    "hvac_min_off_time_min",
                    default=DEFAULT_HVAC_MIN_OFF_TIME_MIN
                ): vol.All(int, vol.Range(min=0, max=30)),
                vol.Optional(
                    "occupancy_linger_min",
                    default=DEFAULT_OCCUPANCY_LINGER_MIN
                ): vol.All(int, vol.Range(min=0, max=300)),
                vol.Optional(
                    "occupancy_linger_night_min",
                    default=DEFAULT_OCCUPANCY_LINGER_NIGHT_MIN
                ): vol.All(int, vol.Range(min=0, max=300)),
                vol.Optional(
                    "heat_boost_f",
                    default=DEFAULT_HEAT_BOOST_F
                ): vol.All(float, vol.Range(min=0, max=3)),
                vol.Optional(
                    "default_thermostat_temp",
                    default=DEFAULT_DEFAULT_THERMOSTAT_TEMP
                ): vol.All(int, vol.Range(min=65, max=80)),
                vol.Optional(
                    "automation_cooldown_sec",
                    default=30
                ): vol.All(int, vol.Range(min=0, max=300)),
                vol.Optional(
                    "require_occupancy",
                    default=True
                ): bool,
                vol.Optional(
                    "heat_boost_enabled",
                    default=True
                ): bool,
                vol.Optional(
                    "auto_thermostat_control",
                    default=True
                ): bool,
                vol.Optional(
                    "auto_vent_control",
                    default=True
                ): bool,
                vol.Optional(
                    "debug_mode",
                    default=False
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
            # Update options
            return self.async_create_entry(title="", data=user_input)
        
        # Get current options
        current_options = self.config_entry.options or {}
        
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    "min_other_room_open_pct",
                    default=current_options.get("min_other_room_open_pct", DEFAULT_MIN_OTHER_ROOM_OPEN_PCT)
                ): vol.All(int, vol.Range(min=0, max=100)),
                vol.Optional(
                    "closed_threshold_pct",
                    default=current_options.get("closed_threshold_pct", DEFAULT_CLOSED_THRESHOLD_PCT)
                ): vol.All(int, vol.Range(min=0, max=100)),
                vol.Optional(
                    "relief_open_pct",
                    default=current_options.get("relief_open_pct", DEFAULT_RELIEF_OPEN_PCT)
                ): vol.All(int, vol.Range(min=0, max=100)),
                vol.Optional(
                    "max_relief_rooms",
                    default=current_options.get("max_relief_rooms", DEFAULT_MAX_RELIEF_ROOMS)
                ): vol.All(int, vol.Range(min=1, max=10)),
                vol.Optional(
                    "room_hysteresis_f",
                    default=current_options.get("room_hysteresis_f", DEFAULT_ROOM_HYSTERESIS_F)
                ): vol.All(float, vol.Range(min=0, max=5)),
                vol.Optional(
                    "hvac_min_runtime_min",
                    default=current_options.get("hvac_min_runtime_min", DEFAULT_HVAC_MIN_RUNTIME_MIN)
                ): vol.All(int, vol.Range(min=0, max=30)),
                vol.Optional(
                    "hvac_min_off_time_min",
                    default=current_options.get("hvac_min_off_time_min", DEFAULT_HVAC_MIN_OFF_TIME_MIN)
                ): vol.All(int, vol.Range(min=0, max=30)),
                vol.Optional(
                    "occupancy_linger_min",
                    default=current_options.get("occupancy_linger_min", DEFAULT_OCCUPANCY_LINGER_MIN)
                ): vol.All(int, vol.Range(min=0, max=300)),
                vol.Optional(
                    "occupancy_linger_night_min",
                    default=current_options.get("occupancy_linger_night_min", DEFAULT_OCCUPANCY_LINGER_NIGHT_MIN)
                ): vol.All(int, vol.Range(min=0, max=300)),
                vol.Optional(
                    "heat_boost_f",
                    default=current_options.get("heat_boost_f", DEFAULT_HEAT_BOOST_F)
                ): vol.All(float, vol.Range(min=0, max=3)),
                vol.Optional(
                    "default_thermostat_temp",
                    default=current_options.get("default_thermostat_temp", DEFAULT_DEFAULT_THERMOSTAT_TEMP)
                ): vol.All(int, vol.Range(min=65, max=80)),
                vol.Optional(
                    "automation_cooldown_sec",
                    default=current_options.get("automation_cooldown_sec", 30)
                ): vol.All(int, vol.Range(min=0, max=300)),
                vol.Optional(
                    "require_occupancy",
                    default=current_options.get("require_occupancy", True)
                ): bool,
                vol.Optional(
                    "heat_boost_enabled",
                    default=current_options.get("heat_boost_enabled", True)
                ): bool,
                vol.Optional(
                    "auto_thermostat_control",
                    default=current_options.get("auto_thermostat_control", True)
                ): bool,
                vol.Optional(
                    "auto_vent_control",
                    default=current_options.get("auto_vent_control", True)
                ): bool,
                vol.Optional(
                    "debug_mode",
                    default=current_options.get("debug_mode", False)
                ): bool,
            }),
        )
