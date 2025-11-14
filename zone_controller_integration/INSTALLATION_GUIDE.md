# Zone Controller Integration - Installation Guide

## Prerequisites

- Home Assistant installed and running
- Access to Home Assistant's `custom_components` directory
- Your HVAC system with:
  - Main thermostat (climate entity)
  - Room climate entities (e.g., `climate.master_bedroom_room`)
  - Vent entities (cover entities, e.g., `cover.master_v1`)
  - Optional: Temperature sensors, occupancy sensors

## Step 1: Install the Integration

### Option A: Manual Installation (Recommended for Development)

1. **Locate your Home Assistant config directory:**
   - Standard installation: `~/.homeassistant/` or `/config/`
   - Docker: Usually `/config/` inside container
   - Home Assistant OS: `/config/`

2. **Create custom_components directory (if it doesn't exist):**
   ```bash
   mkdir -p /config/custom_components
   ```

3. **Copy the integration:**
   ```bash
   # From your development directory
   cp -r zone_controller_integration/custom_components/zone_controller \
     /config/custom_components/
   ```

4. **Verify the structure:**
   ```
   /config/custom_components/zone_controller/
   ├── __init__.py
   ├── manifest.json
   ├── const.py
   ├── coordinator.py
   ├── config_flow.py
   ├── sensor.py
   ├── binary_sensor.py
   ├── number.py
   ├── switch.py
   ├── script.py
   ├── automation.py
   ├── scripts.py
   ├── automations.py
   ├── services.yaml
   └── strings.json
   ```

5. **Restart Home Assistant:**
   - Go to **Settings** → **System** → **Hardware**
   - Click **Restart** or use the restart button

### Option B: HACS Installation (Future)

Once submitted to HACS:
1. Open HACS
2. Go to **Integrations**
3. Click **Explore & Download Repositories**
4. Search for "Zone Controller"
5. Click **Download**
6. Restart Home Assistant

## Step 2: Create Helper Entities

The integration requires helper entities. You can create them via YAML or UI.

### Option A: YAML Configuration (Recommended)

1. **Open `configuration.yaml`** (or create a `packages/zone_controller_helpers.yaml`)

2. **Add the helper entities:**

```yaml
# Add to configuration.yaml or packages/zone_controller_helpers.yaml

input_number:
  min_other_room_open_pct:
    name: "Minimum Other Room Open %"
    initial: 20
    min: 0
    max: 100
    step: 1
    unit_of_measurement: "%"
    icon: mdi:weather-windy

  occupancy_linger_min:
    name: "Occupancy Linger (day, min)"
    initial: 30
    min: 0
    max: 300
    step: 1
    unit_of_measurement: "min"
    icon: mdi:timer-sand

  occupancy_linger_night_min:
    name: "Occupancy Linger (night, min)"
    initial: 60
    min: 0
    max: 300
    step: 1
    unit_of_measurement: "min"
    icon: mdi:weather-night

  room_hysteresis_f:
    name: "Room Hysteresis (°F)"
    initial: 1.0
    min: 0
    max: 5
    step: 0.1
    unit_of_measurement: "°F"
    icon: mdi:tune

  closed_threshold_pct:
    name: "Closed Threshold %"
    initial: 10
    min: 0
    max: 100
    step: 1
    unit_of_measurement: "%"
    icon: mdi:percent

  relief_open_pct:
    name: "Relief Open %"
    initial: 60
    min: 0
    max: 100
    step: 1
    unit_of_measurement: "%"
    icon: mdi:fan

  heat_boost_f:
    name: "Heat Boost (°F)"
    initial: 1.0
    min: 0
    max: 3
    step: 0.5
    unit_of_measurement: "°F"
    icon: mdi:thermometer-plus

  automation_cooldown_sec:
    name: "Automation Cooldown (sec)"
    initial: 30
    min: 0
    max: 300
    step: 5
    unit_of_measurement: "s"
    icon: mdi:timer-outline

  max_relief_rooms:
    name: "Max Relief Rooms"
    initial: 3
    min: 1
    max: 10
    step: 1
    unit_of_measurement: "rooms"
    icon: mdi:fan-alert

  default_thermostat_temp:
    name: "Default Thermostat Temp (°F)"
    initial: 72
    min: 65
    max: 80
    step: 1
    unit_of_measurement: "°F"
    icon: mdi:thermometer

  hvac_min_runtime_min:
    name: "HVAC Minimum Runtime (min)"
    initial: 10
    min: 0
    max: 30
    step: 1
    unit_of_measurement: "min"
    icon: mdi:timer-play-outline

  hvac_min_off_time_min:
    name: "HVAC Minimum Off Time (min)"
    initial: 5
    min: 0
    max: 30
    step: 1
    unit_of_measurement: "min"
    icon: mdi:timer-off-outline

  hvac_cycle_start_timestamp:
    name: "HVAC Cycle Start Timestamp (Internal)"
    initial: 0
    min: 0
    max: 9999999999
    step: 1
    icon: mdi:clock-start
    mode: box

  hvac_cycle_end_timestamp:
    name: "HVAC Cycle End Timestamp (Internal)"
    initial: 0
    min: 0
    max: 9999999999
    step: 1
    icon: mdi:clock-end
    mode: box

  last_thermostat_setpoint:
    name: "Last Thermostat Setpoint (Internal)"
    initial: 72
    min: 40
    max: 100
    step: 0.5
    unit_of_measurement: "°F"
    icon: mdi:thermostat

  # Room priorities (adjust room names as needed)
  master_priority:
    name: "Master Bedroom Priority"
    initial: 5
    min: 0
    max: 10
    step: 1
    icon: mdi:star

  blue_priority:
    name: "Blue Room Priority"
    initial: 5
    min: 0
    max: 10
    step: 1
    icon: mdi:star

  gold_priority:
    name: "Gold Room Priority"
    initial: 5
    min: 0
    max: 10
    step: 1
    icon: mdi:star

  green_priority:
    name: "Green Room Priority"
    initial: 5
    min: 0
    max: 10
    step: 1
    icon: mdi:star

  grey_priority:
    name: "Grey Room Priority"
    initial: 5
    min: 0
    max: 10
    step: 1
    icon: mdi:star

  guest_priority:
    name: "Guest Room Priority"
    initial: 5
    min: 0
    max: 10
    step: 1
    icon: mdi:star

  family_priority:
    name: "Family Room Priority"
    initial: 5
    min: 0
    max: 10
    step: 1
    icon: mdi:star

  kitchen_priority:
    name: "Kitchen Priority"
    initial: 5
    min: 0
    max: 10
    step: 1
    icon: mdi:star

  basement_priority:
    name: "Basement Priority"
    initial: 5
    min: 0
    max: 10
    step: 1
    icon: mdi:star

  piano_priority:
    name: "Piano Room Priority"
    initial: 5
    min: 0
    max: 10
    step: 1
    icon: mdi:star

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

input_text:
  hvac_last_action:
    name: "HVAC Last Action (Internal)"
    initial: idle
    max: 20
```

3. **If using packages**, add to `configuration.yaml`:
   ```yaml
   homeassistant:
     packages: !include_dir_named packages
   ```

4. **Check configuration:**
   - Go to **Settings** → **Devices & Services** → **Helpers**
   - Verify all helpers are created

### Option B: UI Creation

1. Go to **Settings** → **Devices & Services** → **Helpers**
2. Click **Create Helper**
3. Create each helper manually (time-consuming but possible)

**Note:** The integration's Number and Switch platforms will create most configuration entities automatically, but you still need the internal tracking entities (`hvac_cycle_start_timestamp`, `hvac_cycle_end_timestamp`, `last_thermostat_setpoint`, `hvac_last_action`).

## Step 3: Add Integration via UI

1. **Go to Settings:**
   - **Settings** → **Devices & Services**

2. **Add Integration:**
   - Click **Add Integration** (bottom right)
   - Search for **"Zone Controller"**
   - Click on it

3. **Step 1: Select Main Thermostat**
   - Choose your main HVAC thermostat from the dropdown
   - Click **Submit**

4. **Step 2: Add Rooms**
   For each room:
   - **Room Name**: Enter friendly name (e.g., "Master Bedroom")
   - **Climate Entity**: Select from dropdown (e.g., `climate.master_bedroom_room`)
   - **Temperature Sensor**: (Optional) Select sensor if available
   - **Occupancy Sensor**: (Optional) Select occupancy sensor if available
   - **Vent Entities**: Select all vent entities for this room (multi-select)
   - **Priority**: Adjust slider (0-10, default 5)
   - **Add Another Room**: Check if adding more rooms
   - Click **Submit**

   Repeat until all rooms are added, then uncheck "Add Another Room" and submit.

5. **Step 3: Configure Settings**
   - Adjust all settings to your preferences
   - Defaults are pre-filled
   - Click **Submit**

6. **Integration Created:**
   - You'll see "Zone Controller" in your integrations list
   - Entities will start appearing

## Step 4: Verify Installation

### Check Entities

1. **Go to Developer Tools** → **States**
2. **Search for `zone_controller`** or room names
3. **Verify sensors exist:**
   - `sensor.{room}_temp_degf`
   - `sensor.{room}_target_degf`
   - `sensor.{room}_delta_degf`
   - `binary_sensor.{room}_occupied_recent`
   - `sensor.rooms_to_condition`
   - `sensor.zone_controller_statistics`

### Check Services

1. **Go to Developer Tools** → **Services**
2. **Search for `zone_controller`**
3. **Verify services exist:**
   - `zone_controller.set_multi_room_vents`
   - `zone_controller.apply_ecobee_hold_for_rooms`
   - `zone_controller.set_room_priority`
   - `zone_controller.reset_to_defaults`

### Check Automations

1. **Go to Settings** → **Automations & Scenes**
2. **Look for automations:**
   - Zone Controller automations should be running
   - They're managed by the integration (not visible in UI)

## Step 5: Test the Integration

### Test 1: Check Room Selection

1. **Go to Developer Tools** → **States**
2. **Check `sensor.rooms_to_condition`:**
   - Should show rooms needing conditioning
   - Format: `"master,blue"` or `"none"`

### Test 2: Manual Service Call

1. **Go to Developer Tools** → **Services**
2. **Select `zone_controller.set_multi_room_vents`**
3. **Service Data:**
   ```yaml
   rooms_csv: "master,blue"
   ```
4. **Click Call Service**
5. **Check vent positions** - Master and Blue vents should open to 100%

### Test 3: Enable Debug Mode

1. **Go to Settings** → **Devices & Services** → **Zone Controller** → **Options**
2. **Enable Debug Mode**
3. **Check Logs:**
   - **Settings** → **System** → **Logs**
   - Look for Zone Controller messages

## Step 6: Add Dashboard Cards (Optional)

1. **Copy dashboard card YAML** from `dashboard/zone_controller_complete_dashboard.yaml`
2. **In Home Assistant:**
   - Go to your dashboard
   - Click **Add Card** → **Manual**
   - Paste YAML
   - Adjust entity IDs if needed (especially `climate.main_floor_thermostat`)
   - Save

See `dashboard/README.md` for more dashboard options.

## Step 7: Configure Room Targets

The integration uses each room's climate entity target temperature. To set targets:

1. **Go to each room's climate entity** (e.g., `climate.master_bedroom_room`)
2. **Set the target temperature** via the climate card or service call
3. **The integration will automatically use these targets**

## Troubleshooting

### Integration Not Appearing

- **Check file structure:** Verify `custom_components/zone_controller/` exists
- **Check `manifest.json`:** Ensure it's valid JSON
- **Restart Home Assistant:** Full restart required
- **Check logs:** Look for errors in Home Assistant logs

### Entities Not Creating

- **Verify config entry:** Check Settings → Devices & Services → Zone Controller
- **Check coordinator:** Look for errors in logs
- **Verify helper entities:** Ensure all required helpers exist
- **Enable debug logging:**
  ```yaml
  logger:
    default: info
    logs:
      custom_components.zone_controller: debug
  ```

### Scripts Not Working

- **Check helper entities:** Verify all `input_number` and `input_boolean` exist
- **Check service calls:** Test in Developer Tools → Services
- **Enable debug mode:** Check logs for errors
- **Verify vent entities:** Ensure vent entity IDs are correct

### Vents Not Adjusting

- **Check `auto_vent_control`:** Ensure toggle is ON
- **Verify vent entities:** Check entity IDs in room configuration
- **Check service:** Test `zone_controller.set_multi_room_vents` manually
- **Check logs:** Enable debug mode and check for errors

### Thermostat Not Adjusting

- **Check `auto_thermostat_control`:** Ensure toggle is ON
- **Check manual override:** Verify override detection is working
- **Check cycle protection:** Verify protection status
- **Check thermostat entity:** Ensure main thermostat entity ID is correct

## Next Steps

1. **Fine-tune settings:** Adjust thresholds, priorities, and protection settings
2. **Monitor performance:** Watch logs and dashboard for a few days
3. **Adjust priorities:** Set room priorities based on usage
4. **Create dashboard:** Add dashboard cards for monitoring
5. **Test edge cases:** Test with different scenarios (heating, cooling, multiple rooms)

## Support

- **Check logs:** Settings → System → Logs
- **Enable debug mode:** Integration options
- **Check entity states:** Developer Tools → States
- **Test services:** Developer Tools → Services

## Migration from YAML

If you're migrating from the YAML script:

1. **Keep YAML script disabled** initially
2. **Set up integration** as above
3. **Test thoroughly** before removing YAML
4. **Compare behavior** between YAML and integration
5. **Remove YAML** once confident

The integration provides 100% feature parity with the YAML script.

