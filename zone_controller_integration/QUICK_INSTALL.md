# Quick Installation Guide

## Prerequisites

- Home Assistant 2024.1 or later
- Access to your Home Assistant configuration directory
- SSH or Samba access (for manual installation)

## Installation Methods

### Method 1: Manual Installation (Recommended for Testing)

1. **Copy the integration folder:**
   ```bash
   # On your Home Assistant server
   cd /config
   mkdir -p custom_components
   # Copy the zone_controller folder to custom_components/
   cp -r zone_controller_integration/custom_components/zone_controller custom_components/
   ```

2. **Restart Home Assistant:**
   - Go to Settings → System → Restart
   - Or restart via SSH: `ha core restart`

3. **Add Integration:**
   - Go to Settings → Devices & Services
   - Click "Add Integration"
   - Search for "Zone Controller"
   - Click on it and follow the setup wizard

### Method 2: HACS Installation (Future)

Once published to HACS:

1. **Install HACS** (if not already installed)
   - Follow: https://hacs.xyz/docs/setup/download

2. **Add Custom Repository:**
   - Go to HACS → Integrations
   - Click the three dots (⋮) → Custom repositories
   - Add repository URL
   - Category: Integration

3. **Install:**
   - Find "Zone Controller" in HACS
   - Click Install
   - Restart Home Assistant

4. **Configure:**
   - Go to Settings → Devices & Services
   - Add Integration → Zone Controller

## Initial Setup

### Step 1: Main Thermostat

1. Click "Add Integration" → "Zone Controller"
2. Select your main HVAC thermostat from the dropdown
3. Click "Submit"

### Step 2: Add Rooms

For each room you want to control:

1. **Room Name:** Enter a friendly name (e.g., "Master Bedroom")
2. **Climate Entity:** Select the room's climate entity (e.g., `climate.master_bedroom_room`)
3. **Temperature Sensor:** (Optional) Select temperature sensor if different from climate entity
4. **Occupancy Sensor:** (Optional) Select binary sensor for occupancy
5. **Vent Entities:** Select one or more vent entities (e.g., `cover.master_bedroom_v1`)
6. **Priority:** Set priority 0-10 (higher = more important for relief vents)
7. Click "Add Another Room" to add more rooms, or "Continue" when done

### Step 3: Configure Settings

Adjust these settings as needed:

- **Minimum Other Room Open %:** Default 20% (minimum vent position for non-conditioned rooms)
- **Closed Threshold %:** Default 10% (considered "closed" for 1/3 rule)
- **Relief Open %:** Default 60% (position for relief vents)
- **Max Relief Rooms:** Default 3 (maximum rooms to open for relief)
- **Room Hysteresis:** Default 1.0°F (temperature threshold)
- **Occupancy Linger (day):** Default 30 min
- **Occupancy Linger (night):** Default 60 min
- **Heat Boost:** Default 1.0°F (temperature boost during heating)
- **HVAC Minimum Runtime:** Default 10 min (prevents short cycling)
- **HVAC Minimum Off Time:** Default 5 min (prevents rapid cycling)
- **Default Thermostat Temp:** Default 72°F (when no rooms need conditioning)
- **Automation Cooldown:** Default 30 sec (prevents rapid automation triggers)

**Toggles:**
- **Require Occupancy:** Only condition occupied rooms
- **Heat Boost Enabled:** Enable heat boost feature
- **Auto Thermostat Control:** Enable automatic thermostat control
- **Auto Vent Control:** Enable automatic vent control
- **Debug Mode:** Enable detailed logging

### Step 4: Review and Confirm

Review your configuration and click "Submit" to create the integration.

## Migration from YAML

If you have an existing YAML configuration:

1. **Keep your YAML file** in place (don't delete it yet)
2. **Start the integration setup** as described above
3. **If YAML detected:** You'll see an option to "Migrate from YAML Configuration"
4. **Select migration:** The wizard will detect your rooms and settings
5. **Review and confirm:** Check that all rooms and settings were imported correctly
6. **Test the integration:** Verify it works before removing YAML

## Post-Installation

### Verify Installation

1. **Check Entities:**
   - Go to Settings → Devices & Services → Zone Controller
   - Verify all rooms are listed
   - Check that sensors are created (temperature, target, delta, occupancy)

2. **Check Automations:**
   - Go to Settings → Automations & Scenes → Automations
   - Look for "Zone Conditioner Multi-Room" automation
   - Verify it's enabled

3. **Check Scripts:**
   - Go to Developer Tools → Services
   - Look for `zone_controller.set_multi_room_vents` and `zone_controller.apply_ecobee_hold_for_rooms`

### Testing

1. **Manual Test:**
   - Change a room's target temperature
   - Wait for automation to trigger
   - Verify vents adjust correctly
   - Check thermostat setpoint changes

2. **Enable Debug Mode:**
   - Go to Settings → Devices & Services → Zone Controller → Options
   - Enable "Debug Mode"
   - Check logs: Settings → System → Logs
   - Look for "Zone Controller" entries

### Troubleshooting

**Integration not showing:**
- Check that `custom_components/zone_controller/` exists
- Verify `manifest.json` is present
- Restart Home Assistant
- Check logs for errors

**Entities not created:**
- Check that rooms were configured correctly
- Verify entity IDs exist in Home Assistant
- Check logs for errors

**Automation not triggering:**
- Verify automation is enabled
- Check trigger entities (temperature sensors, thermostat)
- Enable debug mode and check logs

**Vents not adjusting:**
- Verify vent entities are correct
- Check that "Auto Vent Control" is enabled
- Verify vents are not manually locked
- Check logs for service call errors

## Next Steps

- **Configure Dashboard:** See `dashboard/` folder for example cards
- **Adjust Settings:** Use Options Flow to fine-tune settings
- **Monitor Performance:** Check diagnostics for system status
- **Read Documentation:** See `README.md` for full documentation

## Support

For issues or questions:
1. Check logs (Settings → System → Logs)
2. Enable debug mode for detailed logging
3. Check diagnostics (Settings → Devices & Services → Zone Controller → Diagnostics)
4. Review documentation in `README.md` and other `.md` files

