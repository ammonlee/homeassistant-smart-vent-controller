# Smart Vent Controller

A comprehensive Home Assistant custom integration for intelligent multi-room HVAC zone control with vent management, occupancy awareness, and cycle protection.

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

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

### Method 1: HACS (Recommended)

1. Open HACS → Integrations
2. Click the three dots (⋮) → Custom repositories
3. Add repository: `https://github.com/YOUR_USERNAME/homeassistant-smart-vent-controller`
4. Category: Integration
5. Click Install
6. Restart Home Assistant
7. Go to Settings → Devices & Services → Add Integration → Smart Vent Controller

### Method 2: Manual Installation

1. Copy the `custom_components/smart_vent_controller` folder to your Home Assistant `custom_components` directory:
   ```bash
   cd /config/custom_components
   git clone https://github.com/ammonlee/homeassistant-smart-vent-controller.git
   mv homeassistant-smart-vent-controller/custom_components/smart_vent_controller smart_vent_controller
   ```

2. Restart Home Assistant

3. Go to **Settings** → **Devices & Services** → **Add Integration**

4. Search for **"Smart Vent Controller"** and follow the setup wizard

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

### Options Flow

After installation, you can update settings without reconfiguring rooms:

1. Go to **Settings** → **Devices & Services** → **Smart Vent Controller** → **Options**
2. Adjust any settings
3. Changes take effect immediately

## Usage

### Services

The integration provides custom services:

- `smart_vent_controller.set_multi_room_vents`: Adjust vent positions for multiple rooms
- `smart_vent_controller.apply_ecobee_hold_for_rooms`: Set thermostat for multiple rooms
- `smart_vent_controller.set_room_priority`: Change room priority
- `smart_vent_controller.reset_to_defaults`: Reset all settings to defaults

### Dashboard Cards

Example dashboard cards are available in the `dashboard/` folder. See `dashboard/README.md` for details.

## Documentation

- **[Installation Guide](INSTALLATION_GUIDE.md)** - Detailed installation instructions
- **[Quick Install](QUICK_INSTALL.md)** - Quick reference guide
- **[UI Configuration Guide](UI_CONFIGURATION_GUIDE.md)** - Step-by-step UI setup
- **[Feature Parity](FEATURE_PARITY.md)** - Comparison with YAML script
- **[Testing Guide](TESTING_GUIDE.md)** - Testing and validation
- **[Troubleshooting](TROUBLESHOOTING.md)** - Common issues and solutions
- **[Complete Features Summary](COMPLETE_FEATURES_SUMMARY.md)** - All features documented

## Requirements

- Home Assistant 2024.1 or later
- HVAC system with:
  - Main thermostat (climate entity)
  - Room climate entities (e.g., Flair room controllers)
  - Vent entities (cover entities, e.g., Flair vents)
  - Optional: Temperature sensors, occupancy sensors

## Support

- **Issues**: [GitHub Issues](https://github.com/YOUR_USERNAME/homeassistant-smart-vent-controller/issues)
- **Documentation**: See the `docs/` folder
- **Logs**: Enable debug mode in integration options for detailed logging

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

[Add your license here]

## Credits

Developed for intelligent multi-room HVAC control with Flair vents and Home Assistant.
