# Helper Entities Setup

The Zone Controller integration requires several helper entities (input_number, input_boolean, input_text) to function properly. These can be created via YAML or through the Home Assistant UI.

## Required Helper Entities

### Input Numbers

Create these in `configuration.yaml` or via the UI:

```yaml
input_number:
  min_other_room_open_pct:
    name: "Minimum Other Room Open %"
    initial: 20
    min: 0
    max: 100
    step: 1
    unit_of_measurement: "%"
  
  occupancy_linger_min:
    name: "Occupancy Linger (day, min)"
    initial: 30
    min: 0
    max: 300
    step: 1
    unit_of_measurement: "min"
  
  occupancy_linger_night_min:
    name: "Occupancy Linger (night, min)"
    initial: 60
    min: 0
    max: 300
    step: 1
    unit_of_measurement: "min"
  
  room_hysteresis_f:
    name: "Room Hysteresis (°F)"
    initial: 1.0
    min: 0
    max: 5
    step: 0.1
    unit_of_measurement: "°F"
  
  closed_threshold_pct:
    name: "Closed Threshold %"
    initial: 10
    min: 0
    max: 100
    step: 1
    unit_of_measurement: "%"
  
  relief_open_pct:
    name: "Relief Open %"
    initial: 60
    min: 0
    max: 100
    step: 1
    unit_of_measurement: "%"
  
  heat_boost_f:
    name: "Heat Boost (°F)"
    initial: 1.0
    min: 0
    max: 3
    step: 0.5
    unit_of_measurement: "°F"
  
  automation_cooldown_sec:
    name: "Automation Cooldown (sec)"
    initial: 30
    min: 0
    max: 300
    step: 5
    unit_of_measurement: "s"
  
  max_relief_rooms:
    name: "Max Relief Rooms"
    initial: 3
    min: 1
    max: 10
    step: 1
    unit_of_measurement: "rooms"
  
  default_thermostat_temp:
    name: "Default Thermostat Temp (°F)"
    initial: 72
    min: 65
    max: 80
    step: 1
    unit_of_measurement: "°F"
  
  hvac_min_runtime_min:
    name: "HVAC Minimum Runtime (min)"
    initial: 10
    min: 0
    max: 30
    step: 1
    unit_of_measurement: "min"
  
  hvac_min_off_time_min:
    name: "HVAC Minimum Off Time (min)"
    initial: 5
    min: 0
    max: 30
    step: 1
    unit_of_measurement: "min"
  
  hvac_cycle_start_timestamp:
    name: "HVAC Cycle Start Timestamp (Internal)"
    initial: 0
    min: 0
    max: 9999999999
    step: 1
  
  hvac_cycle_end_timestamp:
    name: "HVAC Cycle End Timestamp (Internal)"
    initial: 0
    min: 0
    max: 9999999999
    step: 1
  
  last_thermostat_setpoint:
    name: "Last Thermostat Setpoint (Internal)"
    initial: 72
    min: 40
    max: 100
    step: 0.5
    unit_of_measurement: "°F"
  
  # Room priorities (adjust room names as needed)
  master_priority:
    name: "Master Priority"
    initial: 5
    min: 0
    max: 10
    step: 1
  
  blue_priority:
    name: "Blue Priority"
    initial: 5
    min: 0
    max: 10
    step: 1
  
  gold_priority:
    name: "Gold Priority"
    initial: 5
    min: 0
    max: 10
    step: 1
  
  green_priority:
    name: "Green Priority"
    initial: 5
    min: 0
    max: 10
    step: 1
  
  grey_priority:
    name: "Grey Priority"
    initial: 5
    min: 0
    max: 10
    step: 1
  
  guest_priority:
    name: "Guest Priority"
    initial: 5
    min: 0
    max: 10
    step: 1
  
  family_priority:
    name: "Family Priority"
    initial: 5
    min: 0
    max: 10
    step: 1
  
  kitchen_priority:
    name: "Kitchen Priority"
    initial: 5
    min: 0
    max: 10
    step: 1
  
  basement_priority:
    name: "Basement Priority"
    initial: 5
    min: 0
    max: 10
    step: 1
  
  piano_priority:
    name: "Piano Priority"
    initial: 5
    min: 0
    max: 10
    step: 1
```

### Input Booleans

```yaml
input_boolean:
  require_occupancy:
    name: "Condition Only When Occupied"
    initial: true
    icon: mdi:account-eye
  
  heat_boost_enabled:
    name: "Heat Boost Enabled"
    initial: true
    icon: mdi:fire
  
  auto_thermostat_control:
    name: "Auto Thermostat Control"
    initial: true
    icon: mdi:thermostat-auto
  
  auto_vent_control:
    name: "Auto Vent Control"
    initial: true
    icon: mdi:air-conditioner
  
  debug_mode:
    name: "Debug Mode (Enhanced Logging)"
    initial: false
    icon: mdi:bug
```

### Input Text

```yaml
input_text:
  hvac_last_action:
    name: "HVAC Last Action (Internal)"
    initial: "idle"
    min: 0
    max: 20
```

## Alternative: Use Integration's Number/Switch Platforms

The integration provides Number and Switch platforms that create these entities automatically. However, some internal tracking entities (like `hvac_cycle_start_timestamp`, `hvac_last_action`) may still need to be created manually or will be handled by the integration's internal storage.

## Notes

- These entities are used by the scripts and automations
- The integration's Number and Switch platforms will create most of these automatically
- Internal tracking entities may use coordinator storage instead of input entities
- Adjust room priority entity names to match your room names

