# Zone Controller - Home Assistant Integration Plan

## Overview

Converting the YAML-based zone controller into a proper Home Assistant custom integration would provide:
- **UI-based configuration** (no YAML editing required)
- **HACS compatibility** (easy installation and updates)
- **Better user experience** (guided setup, validation)
- **Easier maintenance** (versioned releases)
- **Professional appearance** (appears as native integration)

## Directory Structure

```
homeassistant-zone-controller/
├── custom_components/
│   └── zone_controller/
│       ├── __init__.py                 # Main integration entry point
│       ├── manifest.json               # Integration metadata
│       ├── config_flow.py             # UI configuration flow
│       ├── const.py                   # Constants and defaults
│       ├── coordinator.py             # Data update coordinator
│       ├── sensor.py                   # Template sensors
│       ├── binary_sensor.py           # Occupancy sensors
│       ├── number.py                  # Input number helpers
│       ├── switch.py                   # Input boolean helpers
│       ├── script.py                   # Script entities
│       ├── automation.py               # Automation entities
│       ├── strings.json                # UI strings (i18n)
│       └── services.yaml               # Custom services
├── .github/
│   └── workflows/
│       └── validate.yml                # CI/CD validation
├── .gitignore
├── LICENSE
├── README.md
└── hacs.json                           # HACS metadata
```

## Key Components

### 1. `manifest.json`
```json
{
  "domain": "zone_controller",
  "name": "Zone Controller",
  "version": "1.0.0",
  "documentation": "https://github.com/yourusername/homeassistant-zone-controller",
  "issue_tracker": "https://github.com/yourusername/homeassistant-zone-controller/issues",
  "codeowners": ["@yourusername"],
  "requirements": [],
  "config_flow": true,
  "iot_class": "local_polling",
  "integration_type": "system"
}
```

### 2. `config_flow.py` - UI Configuration

**Step 1: Select Main Thermostat**
- Dropdown of available climate entities
- User selects `climate.main_floor_thermostat`

**Step 2: Configure Rooms**
- Dynamic form to add rooms
- For each room:
  - Room name
  - Climate entity (dropdown)
  - Temperature sensor (optional, dropdown)
  - Occupancy sensor (optional, dropdown)
  - Vent group entities (multi-select)
  - Priority (slider 0-10)

**Step 3: Configure Settings**
- Minimum other room open %
- Closed threshold %
- Relief open %
- Max relief rooms
- Room hysteresis
- Occupancy linger times (day/night)
- Heat boost settings
- HVAC cycle protection settings

**Step 4: Review & Confirm**
- Summary of all settings
- Option to test configuration

### 3. `__init__.py` - Main Integration

```python
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Zone Controller from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    # Create coordinator for data updates
    coordinator = ZoneControllerCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    
    hass.data[DOMAIN][entry.entry_id] = coordinator
    
    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(
        entry, ["sensor", "binary_sensor", "number", "switch", "script", "automation"]
    )
    
    return True
```

### 4. `coordinator.py` - Data Coordinator

Handles:
- Periodic updates of room temperatures
- Vent position monitoring
- Occupancy state tracking
- Thermostat state monitoring
- Coordinates all platform updates

### 5. Platform Files

**`sensor.py`**: Creates template sensors for:
- Room temperatures
- Room targets
- Room deltas
- Rooms to condition
- HVAC cycle status
- Statistics

**`binary_sensor.py`**: Creates occupancy sensors with dynamic linger times

**`number.py`**: Creates input_number helpers for all configuration

**`switch.py`**: Creates input_boolean helpers for toggles

**`script.py`**: Registers the vent and thermostat control scripts

**`automation.py`**: Registers the main automation

## Configuration Storage

Instead of YAML, configuration stored in:
- **Config Entry**: Main settings (thermostat, rooms list)
- **Options Flow**: User-configurable settings (hysteresis, thresholds, etc.)
- **Entity Registry**: Room-specific entities

## User Experience Flow

1. **Installation** (via HACS or manual)
   ```
   HACS → Integrations → Custom Repositories → Add
   Repository: yourusername/homeassistant-zone-controller
   Category: Integration
   ```

2. **Setup** (via UI)
   ```
   Settings → Devices & Services → Add Integration
   → Search "Zone Controller" → Configure
   ```

3. **Configuration Wizard**
   - Step 1: Select main thermostat
   - Step 2: Add rooms (with entity pickers)
   - Step 3: Configure thresholds and settings
   - Step 4: Review and confirm

4. **Ongoing Management**
   - Settings → Zone Controller → Options
   - Adjust thresholds, priorities, etc.
   - Add/remove rooms
   - Enable/disable features

## Advantages Over YAML

| Feature | YAML | Integration |
|---------|------|-------------|
| Setup | Manual YAML editing | UI wizard |
| Room config | Edit YAML | Add via UI |
| Entity selection | Type entity IDs | Dropdown picker |
| Validation | Runtime errors | Pre-submit validation |
| Updates | Manual copy/paste | HACS update button |
| User-friendly | Technical users | All users |
| Error handling | YAML syntax errors | Friendly error messages |

## Implementation Steps

### Phase 1: Basic Structure
1. Create directory structure
2. Implement `manifest.json`
3. Create basic `__init__.py`
4. Implement `config_flow.py` (basic version)

### Phase 2: Core Functionality
1. Port template sensors to `sensor.py`
2. Port binary sensors to `binary_sensor.py`
3. Create coordinator for data updates
4. Port scripts to `script.py`

### Phase 3: Configuration UI
1. Complete `config_flow.py` with all steps
2. Add options flow for settings
3. Implement validation
4. Add `strings.json` for UI text

### Phase 4: Advanced Features
1. Port automations
2. Add custom services
3. Implement device/entity registry
4. Add diagnostics support

### Phase 5: Polish & Distribution
1. Add comprehensive error handling
2. Write documentation
3. Create HACS metadata
4. Set up CI/CD
5. Submit to HACS (optional)

## Migration Path

For existing YAML users:
1. Integration can detect existing YAML config
2. Offer to migrate automatically
3. Or allow manual import
4. Keep YAML as fallback option

## Example: Config Flow Step

```python
class ZoneControllerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, user_input=None):
        if user_input is not None:
            # Validate thermostat exists
            if user_input["thermostat"] not in self.hass.states.async_entity_ids("climate"):
                return self.async_show_form(
                    step_id="user",
                    errors={"thermostat": "invalid_thermostat"}
                )
            
            return self.async_create_entry(
                title=f"Zone Controller ({user_input['thermostat']})",
                data=user_input
            )
        
        # Get available climate entities
        climate_entities = [
            entity_id for entity_id in self.hass.states.async_entity_ids("climate")
        ]
        
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("thermostat"): vol.In(climate_entities),
            })
        )
```

## Services Provided

The integration would expose custom services:
- `zone_controller.set_room_priority`
- `zone_controller.override_room`
- `zone_controller.reset_to_defaults`
- `zone_controller.test_vent_control`

## Device Representation

Each room could appear as a "device" in Home Assistant:
- Device: "Master Bedroom Zone"
  - Entities:
    - Temperature sensor
    - Target sensor
    - Delta sensor
    - Occupancy sensor
    - Vent positions

## Next Steps

1. **Start Small**: Begin with basic config flow and one sensor
2. **Iterate**: Add features incrementally
3. **Test**: Use Home Assistant dev container for testing
4. **Document**: Keep README updated
5. **Share**: Consider HACS submission when ready

## Resources

- [Home Assistant Integration Documentation](https://developers.home-assistant.io/docs/creating_integration_manifest)
- [Config Flow Guide](https://developers.home-assistant.io/docs/config_entries_config_flow_handler)
- [HACS Integration Guidelines](https://hacs.xyz/docs/publish/integration)
- [Home Assistant Developer Docs](https://developers.home-assistant.io/)

