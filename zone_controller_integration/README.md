# Zone Controller Integration

A comprehensive Home Assistant custom integration for intelligent multi-room HVAC zone control with vent management, occupancy awareness, and cycle protection.

## Features

- **Multi-Room Control**: Automatically condition multiple rooms based on individual temperature targets
- **Smart Vent Control**: Opens/closes vents based on room needs with ≤1/3 closed enforcement
- **Occupancy Awareness**: Dynamic day/night linger times for occupancy detection
- **Heat Boost**: Configurable temperature boost for heating cycles
- **Cycle Protection**: Prevents short cycling of HVAC equipment
- **Manual Override Detection**: Detects and respects manual thermostat adjustments
- **Temperature/Occupancy-Aware Relief**: Intelligent relief vent selection based on room conditions
- **Room Priorities**: Configurable priorities for relief vent selection
- **Comprehensive Logging**: Debug mode for troubleshooting

## Installation

### Method 1: Manual Installation

1. Copy the `custom_components/zone_controller` folder to your Home Assistant `custom_components` directory:
   ```bash
   cp -r zone_controller_integration/custom_components/zone_controller \
     ~/.homeassistant/custom_components/
   ```

2. Restart Home Assistant

3. Go to **Settings** → **Devices & Services** → **Add Integration**

4. Search for **"Zone Controller"** and follow the setup wizard

### Method 2: HACS (Future)

Once submitted to HACS, you'll be able to install via the HACS UI.

## Configuration

### Initial Setup

The integration uses a multi-step configuration wizard:

1. **Select Main Thermostat**: Choose your primary HVAC thermostat
2. **Add Rooms**: For each room, configure:
   - Room name
   - Climate entity (e.g., `climate.master_bedroom_room`)
   - Temperature sensor (optional, falls back to climate entity)
   - Occupancy sensor (optional)
   - Vent entities (list of cover entities)
   - Priority (0-10, default 5)
3. **Configure Settings**: Adjust thresholds and protection settings

### Required Helper Entities

The integration requires several helper entities. See `HELPER_ENTITIES.md` for the complete list and YAML configuration.

**Quick Setup** (add to `configuration.yaml`):

```yaml
input_number:
  min_other_room_open_pct:
    name: "Minimum Other Room Open %"
    initial: 20
    min: 0
    max: 100
    step: 1
  
  # ... (see HELPER_ENTITIES.md for complete list)

input_boolean:
  require_occupancy:
    name: "Condition Only When Occupied"
    initial: true
  
  auto_vent_control:
    name: "Auto Vent Control"
    initial: true
  
  auto_thermostat_control:
    name: "Auto Thermostat Control"
    initial: true
  
  # ... (see HELPER_ENTITIES.md for complete list)
```

**Note**: The integration's Number and Switch platforms will create most configuration entities automatically. You may only need to create the internal tracking entities manually.

## Usage

### Services

The integration provides two main services:

#### `zone_controller.set_multi_room_vents`

Adjusts vent positions for multiple rooms.

**Service Data**:
- `rooms_csv` (string, optional): Comma-separated list of room keys to fully open (e.g., `"master,blue"`)

**Example**:
```yaml
service: zone_controller.set_multi_room_vents
data:
  rooms_csv: "master,blue,guest"
```

#### `zone_controller.apply_ecobee_hold_for_rooms`

Adjusts thermostat setpoint based on selected rooms' targets.

**Service Data**:
- `rooms_csv` (string, optional): Comma-separated list of room keys

**Example**:
```yaml
service: zone_controller.apply_ecobee_hold_for_rooms
data:
  rooms_csv: "master,blue"
```

### Automations

The integration automatically sets up three automations:

1. **Zone Conditioner Multi-Room**: Main control loop that triggers on:
   - Room temperature changes
   - Occupancy changes
   - Thermostat state changes
   - Periodic (every 5 minutes)

2. **Track HVAC Cycle Timing**: Tracks HVAC cycle start/end times for cycle protection

3. **Clear Manual Override**: Clears manual override when HVAC cycle completes

### Sensors

The integration creates sensors for each room:

- `sensor.{room}_temp_degf`: Current room temperature
- `sensor.{room}_target_degf`: Room target temperature
- `sensor.{room}_delta_degf`: Temperature delta (target - current)
- `binary_sensor.{room}_occupied_recent`: Recent occupancy (with dynamic linger)
- `sensor.rooms_to_condition`: Comma-separated list of rooms needing conditioning
- `binary_sensor.thermostat_manual_override`: Manual override detection
- `sensor.hvac_cycle_protection_status`: Cycle protection status
- `sensor.zone_controller_statistics`: System statistics

### Configuration Options

Access via **Settings** → **Devices & Services** → **Zone Controller** → **Options**:

- **Minimum Other Room Open %**: Minimum vent position for non-conditioned rooms (default: 20%)
- **Closed Threshold %**: Position below which a vent is considered closed (default: 10%)
- **Relief Open %**: Position for relief vents (default: 60%)
- **Max Relief Rooms**: Maximum number of rooms to use for relief (default: 3)
- **Room Hysteresis (°F)**: Temperature difference threshold (default: 1.0°F)
- **Occupancy Linger (day, min)**: How long to consider room occupied during day (default: 30 min)
- **Occupancy Linger (night, min)**: How long to consider room occupied at night (default: 60 min)
- **Heat Boost (°F)**: Temperature boost for heating cycles (default: 1.0°F)
- **HVAC Minimum Runtime (min)**: Minimum runtime before allowing setpoint change (default: 10 min)
- **HVAC Minimum Off Time (min)**: Minimum off time before allowing setpoint change (default: 5 min)
- **Default Thermostat Temp (°F)**: Default temperature when no rooms need conditioning (default: 72°F)
- **Automation Cooldown (sec)**: Minimum time between automation triggers (default: 30 sec)

### Switches

- **Condition Only When Occupied**: Only condition rooms when recently occupied
- **Heat Boost Enabled**: Enable heat boost feature
- **Auto Thermostat Control**: Enable automatic thermostat control
- **Auto Vent Control**: Enable automatic vent control
- **Debug Mode**: Enable enhanced logging

## How It Works

1. **Room Selection**: The integration continuously monitors room temperatures and determines which rooms need conditioning based on:
   - Temperature delta (target - current)
   - Hysteresis threshold
   - Occupancy (if required)
   - HVAC mode (heat/cool/auto)

2. **Vent Control**: 
   - Opens selected rooms' vents to 100%
   - Sets other rooms to minimum
   - Enforces ≤1/3 closed rule by opening relief vents
   - Selects relief vents based on temperature, occupancy, and priority

3. **Thermostat Control**:
   - Calculates setpoint based on selected rooms' targets
   - Applies heat boost for heating cycles
   - Respects cycle protection (minimum runtime/off time)
   - Detects and respects manual overrides

4. **Cycle Protection**:
   - Tracks HVAC cycle start/end times
   - Prevents setpoint changes during minimum runtime
   - Prevents setpoint changes during minimum off time

## Troubleshooting

### Integration Not Appearing

- Verify `custom_components/zone_controller` exists
- Check `manifest.json` is valid
- Restart Home Assistant
- Check logs for errors

### Entities Not Creating

- Verify config entry was created successfully
- Check coordinator is running
- Enable debug logging:
  ```yaml
  logger:
    default: info
    logs:
      custom_components.zone_controller: debug
  ```

### Scripts Not Working

- Verify helper entities exist (see `HELPER_ENTITIES.md`)
- Check service calls in Developer Tools
- Enable debug mode switch
- Check Home Assistant logs

### Vents Not Adjusting

- Verify `auto_vent_control` switch is on
- Check vent entities are valid
- Verify vent entities are in room configuration
- Check for errors in logs

### Thermostat Not Adjusting

- Verify `auto_thermostat_control` switch is on
- Check manual override detection
- Verify cycle protection settings
- Check thermostat entity is correct

## Development

See `QUICK_START.md` for development setup and testing instructions.

## License

[Your License Here]

## Support

[Your Support Information Here]
