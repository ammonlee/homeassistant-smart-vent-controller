# Smart Vent Controller

A Home Assistant custom integration for intelligent multi-room HVAC zone control. Automatically positions smart vents based on per-room temperature targets, occupancy, and learned efficiency — with built-in HVAC cycle protection and airflow safety.

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

## Features

- **Per-Room Climate Control**: Each room gets its own climate entity with an independent target temperature
- **Smart Vent Positioning**: Three control strategies — simple, learned (exponential model), and hybrid
- **Occupancy Awareness**: Day and night linger timers keep rooms comfortable after vacancy
- **Heat & Cool Boost**: Extra degrees added/subtracted during heating/cooling for faster response
- **HVAC Cycle Protection**: Minimum runtime and off-time guards prevent short-cycling
- **Manual Override Detection**: Detects and respects manual thermostat adjustments
- **Relief Vent Scoring**: Selects relief rooms by occupancy, priority, and temperature proximity
- **Room Priorities**: Configurable 0-10 priority per room for conditioning and relief selection
- **Airflow Safety**: Minimum vent flow enforcement prevents HVAC back-pressure issues
- **Vent Proxy Controls**: Room devices include vent covers for direct open/close/position control
- **Room Management**: Add, edit, rename, or remove rooms after initial setup via reconfigure flow
- **Skip-to-Defaults**: First-time setup can skip all settings and use sensible defaults
- **Efficiency Learning**: Learns per-room heating/cooling rates over time with import/export support

## Installation

### HACS (Recommended)

1. Open HACS > Integrations
2. Click the three dots > Custom repositories
3. Add: `https://github.com/ammonlee/homeassistant-smart-vent-controller`
4. Category: Integration
5. Click Install
6. Restart Home Assistant
7. Go to Settings > Devices & Services > Add Integration > Smart Vent Controller

### Manual Installation

1. Copy `custom_components/smart_vent_controller` to your HA `custom_components` directory
2. Restart Home Assistant
3. Go to Settings > Devices & Services > Add Integration > Smart Vent Controller

## Quick Start

You need:
- A main thermostat (any `climate` entity — Ecobee, Nest, Z-Wave, etc.)
- Smart vents (any `cover` entity — Flair, Keen, ESPHome, etc.)
- Optional: per-room temperature sensors, occupancy sensors

### Setup Wizard

1. **Select Thermostat**: Pick your main HVAC thermostat
2. **Add Rooms**: For each room, provide:
   - Room name (e.g. "Master Bedroom")
   - Climate entity (optional — if omitted, the integration creates one)
   - Temperature sensor (optional — falls back to climate entity)
   - Occupancy sensor (optional)
   - Vent entities (one or more cover entities)
   - Priority (0-10, default 5)
3. **Settings**: Choose "Use Recommended Defaults" to get started quickly, or customize across 4 categories:
   - Algorithm & Vent Positioning
   - Temperature & Setpoint Control
   - HVAC Protection & Timing
   - Occupancy & Automation

## Entities Created

### Per Room

| Entity | Type | Description |
|--------|------|-------------|
| `{Room} Zone` | Climate | Independent target temperature for this room |
| `{Room} Temp` | Sensor | Current temperature |
| `{Room} Target` | Sensor | Target setpoint |
| `{Room} Delta` | Sensor | Target minus current (disabled by default) |
| `{Room} Efficiency` | Sensor | Learned efficiency rate (disabled by default) |
| `{Room} Occupied Recent` | Binary Sensor | Occupancy with day/night linger |
| `{Room} Conditioning Active` | Binary Sensor | Whether room is currently being conditioned |
| `{Room} Override Active` | Binary Sensor | Whether room is in manual override |
| `{Room} Priority` | Number | Priority slider (0-10) |
| Vent covers | Cover | Proxy controls for each vent in the room |

### Global

| Entity | Type | Description |
|--------|------|-------------|
| Rooms To Condition | Sensor | List of rooms currently selected for conditioning |
| HVAC Cycle Protection | Sensor | Whether cycle protection is active |
| System Health | Sensor | Integration health status with error details |
| Auto Vent Control | Switch | Enable/disable automatic vent positioning |
| Auto Thermostat Control | Switch | Enable/disable automatic thermostat adjustment |
| Require Occupancy | Switch | Only condition occupied rooms |
| Heat/Cool Boost Enabled | Switch | Toggle heating/cooling boost |
| Debug Mode | Switch | Verbose logging |

## Services

| Service | Description |
|---------|-------------|
| `smart_vent_controller.set_room_priority` | Change a room's priority (0-10) |
| `smart_vent_controller.override_room` | Temporarily exclude a room from conditioning |
| `smart_vent_controller.reset_to_defaults` | Reset all settings to defaults |
| `smart_vent_controller.export_efficiency` | Export learned efficiency rates to JSON |
| `smart_vent_controller.import_efficiency` | Import efficiency rates from JSON |

### Examples

```yaml
# Set master bedroom to highest priority
service: smart_vent_controller.set_room_priority
data:
  room: master_bedroom
  priority: 10

# Exclude guest room for 2 hours
service: smart_vent_controller.override_room
data:
  room: guest_room
  enabled: true
  duration_min: 120
```

## Options

After setup, adjust settings anytime via Settings > Devices & Services > Smart Vent Controller > Options. The options menu is organized into 4 categories:

- **Algorithm & Vent Positioning**: Control strategy, vent granularity, relief vent settings
- **Temperature & Setpoint Control**: Hysteresis, heat/cool boost, default temperature
- **HVAC Protection & Timing**: Min runtime/off-time, adjustment throttling, polling intervals
- **Occupancy & Automation**: Linger timers, feature toggles, debug mode

## Room Management

After initial setup, click **Reconfigure** on the integration to add, edit, rename, or remove rooms without deleting the integration.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "No climate entities found" during setup | Set up a climate integration first (Ecobee, Nest, Z-Wave thermostat, etc.) |
| Vents not moving | Check that Auto Vent Control switch is on. Enable Debug Mode for detailed logs. |
| Room shows 0 temperature | Verify the room's temperature sensor or climate entity is available |
| Occupancy not detected | Check that the binary sensor entity is working and the Require Occupancy switch is on |
| Settings not taking effect | Changes to number/switch entities take effect on the next poll cycle (30s active, 120s idle) |

## Requirements

- Home Assistant 2024.1 or later
- Main thermostat (any climate entity)
- Smart vents (any cover entity with position support)
- Optional: temperature sensors, occupancy binary sensors

## Support

- [GitHub Issues](https://github.com/ammonlee/homeassistant-smart-vent-controller/issues)
- Enable Debug Mode in integration options for detailed logging

## License

MIT License - see [LICENSE](LICENSE) for details.
