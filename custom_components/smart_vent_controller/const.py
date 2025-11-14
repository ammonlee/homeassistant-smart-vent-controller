"""Constants for Smart Vent Controller integration."""

DOMAIN = "smart_vent_controller"

# Default configuration values
DEFAULT_MIN_OTHER_ROOM_OPEN_PCT = 20
DEFAULT_CLOSED_THRESHOLD_PCT = 10
DEFAULT_RELIEF_OPEN_PCT = 60
DEFAULT_MAX_RELIEF_ROOMS = 3
DEFAULT_ROOM_HYSTERESIS_F = 1.0
DEFAULT_OCCUPANCY_LINGER_MIN = 30
DEFAULT_OCCUPANCY_LINGER_NIGHT_MIN = 60
DEFAULT_HEAT_BOOST_F = 1.0
DEFAULT_HVAC_MIN_RUNTIME_MIN = 10
DEFAULT_HVAC_MIN_OFF_TIME_MIN = 5
DEFAULT_DEFAULT_THERMOSTAT_TEMP = 72
DEFAULT_ROOM_PRIORITY = 5

# Configuration keys
CONF_MAIN_THERMOSTAT = "main_thermostat"
CONF_ROOMS = "rooms"
CONF_ROOM_NAME = "name"
CONF_ROOM_CLIMATE = "climate_entity"
CONF_ROOM_TEMP_SENSOR = "temp_sensor"
CONF_ROOM_OCCUPANCY_SENSOR = "occupancy_sensor"
CONF_ROOM_VENTS = "vent_entities"
CONF_ROOM_PRIORITY = "priority"

# Options keys
CONF_MIN_OTHER_ROOM_OPEN_PCT = "min_other_room_open_pct"
CONF_CLOSED_THRESHOLD_PCT = "closed_threshold_pct"
CONF_RELIEF_OPEN_PCT = "relief_open_pct"
CONF_MAX_RELIEF_ROOMS = "max_relief_rooms"
CONF_ROOM_HYSTERESIS_F = "room_hysteresis_f"
CONF_OCCUPANCY_LINGER_MIN = "occupancy_linger_min"
CONF_OCCUPANCY_LINGER_NIGHT_MIN = "occupancy_linger_night_min"
CONF_REQUIRE_OCCUPANCY = "require_occupancy"
CONF_HEAT_BOOST_ENABLED = "heat_boost_enabled"
CONF_HEAT_BOOST_F = "heat_boost_f"
CONF_AUTO_THERMOSTAT_CONTROL = "auto_thermostat_control"
CONF_AUTO_VENT_CONTROL = "auto_vent_control"
CONF_DEBUG_MODE = "debug_mode"
CONF_HVAC_MIN_RUNTIME_MIN = "hvac_min_runtime_min"
CONF_HVAC_MIN_OFF_TIME_MIN = "hvac_min_off_time_min"
CONF_DEFAULT_THERMOSTAT_TEMP = "default_thermostat_temp"
CONF_AUTOMATION_COOLDOWN_SEC = "automation_cooldown_sec"

