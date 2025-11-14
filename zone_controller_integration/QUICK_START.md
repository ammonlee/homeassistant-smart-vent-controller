# Smart Vent Controller Integration - Quick Start Guide

## Installation for Development

### 1. Copy Integration to Home Assistant

```bash
# Copy the integration folder to your Home Assistant custom_components directory
cp -r smart_vent_controller_integration/custom_components/smart_vent_controller \
  ~/.homeassistant/custom_components/
```

Or if using Docker/container:
```bash
# Mount the directory or copy into the container
docker cp smart_vent_controller_integration/custom_components/smart_vent_controller \
  homeassistant:/config/custom_components/
```

### 2. Restart Home Assistant

Restart Home Assistant to load the new integration.

### 3. Add Integration via UI

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for **"Smart Vent Controller"**
4. Follow the setup wizard

## Testing the Integration

### Manual Testing Steps

1. **Config Flow Test**
   - Start setup wizard
   - Select main thermostat
   - Add a test room
   - Configure settings
   - Verify entities are created

2. **Sensor Test**
   - Check that room temperature sensors appear
   - Verify "Rooms To Condition" sensor updates
   - Check HVAC cycle protection sensor

3. **Script Test**
   - Manually trigger vent control script
   - Check logs for errors
   - Verify vents adjust correctly

4. **Automation Test**
   - Trigger automation manually
   - Change room temperature
   - Verify automation responds

### Debugging

Enable debug logging in `configuration.yaml`:
```yaml
logger:
  default: info
  logs:
    custom_components.smart_vent_controller: debug
```

## Current Status

### ✅ Working
- Basic integration structure
- Config flow (basic version)
- Sensor platform (temperature, target, delta)
- Binary sensor platform (occupancy)
- Number platform (configuration helpers)
- Switch platform (toggles)

### 🚧 Needs Implementation
- Script platform (currently references YAML scripts)
- Automation platform (needs complete trigger/action logic)
- Config flow (needs refinement for multi-room setup)
- Coordinator (needs actual update logic)
- Services (handlers not implemented)

## Next Development Steps

1. **Complete Script Platform**
   - Port vent control logic to Python
   - Port thermostat control logic to Python
   - Handle all edge cases

2. **Complete Automation Platform**
   - Implement proper triggers
   - Port condition checks
   - Handle state management

3. **Refine Config Flow**
   - Better room configuration UI
   - Entity pickers with search
   - Validation and error handling

4. **Add Testing**
   - Unit tests for core logic
   - Integration tests
   - End-to-end tests

## Hybrid Approach (Recommended)

For now, you can use a **hybrid approach**:

1. **Use Integration for**:
   - Configuration (UI-based)
   - Sensors (Python-based)
   - Switches/Numbers (Python-based)

2. **Keep YAML for**:
   - Scripts (until fully ported)
   - Automations (until fully ported)

This allows you to:
- Get UI-based configuration immediately
- Keep existing scripts/automations working
- Migrate gradually

## Migration Path

### Phase 1: Current (Hybrid)
- Integration handles config and sensors
- YAML scripts/automations still work
- Gradual migration

### Phase 2: Full Integration
- All logic in Python
- No YAML dependencies
- Complete UI control

## Troubleshooting

### Integration Not Appearing
- Check `custom_components/smart_vent_controller/` exists
- Verify `manifest.json` is valid
- Check Home Assistant logs for errors
- Restart Home Assistant

### Entities Not Creating
- Check config entry was created successfully
- Verify coordinator is running
- Check platform files for errors
- Enable debug logging

### Scripts Not Working
- Verify YAML scripts still exist
- Check script entity references
- Test scripts directly via Developer Tools

## Resources

- [Home Assistant Integration Docs](https://developers.home-assistant.io/docs/creating_integration_manifest)
- [Config Flow Guide](https://developers.home-assistant.io/docs/config_entries_config_flow_handler)
- [Platform Examples](https://github.com/home-assistant/core/tree/dev/homeassistant/components)

