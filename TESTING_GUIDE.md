# Testing Guide for Vent Zone Controller

This guide will walk you through deploying and testing your multi-room vent controller configuration.

---

## 📋 Pre-Deployment Checklist

Before deploying, verify these entity IDs match your Home Assistant setup:

### Climate Entities (Ecobee/Flair Rooms)
- `climate.main_floor_thermostat` - Main thermostat
- `climate.master_bedroom_room` - Master bedroom climate
- `climate.bella_room` - Blue room climate
- `climate.julia_room` - Gold room climate
- `climate.gabriel_room` - Green room climate
- `climate.bunk_room_room` - Grey room climate
- `climate.guest_room_room` - Guest room climate
- `climate.family_room_room` - Family room climate
- `climate.kitchen_room_2` - Kitchen climate
- `climate.basement_room` - Basement climate

### Temperature Sensors
- `sensor.master_bedroom_temperature`
- `sensor.blue_room_temperature`
- `sensor.gold_room_sensor_temperature`
- `sensor.green_room_temperature`
- `sensor.grey_room_temperature`
- `sensor.guest_room_temperature`
- `sensor.family_room_temperature`
- `sensor.kitchen_temperature`
- `sensor.basement_temperature`

### Occupancy Sensors
- `binary_sensor.master_bedroom_occupancy`
- `binary_sensor.blue_room_occupancy`
- `binary_sensor.gold_room_occupancy`
- `binary_sensor.green_room_occupancy`
- `binary_sensor.grey_room_occupancy`
- `binary_sensor.guest_room_occupancy`
- `binary_sensor.family_room_occupancy`
- `binary_sensor.kitchen_occupancy`
- `binary_sensor.basement_occupancy`

### Flair Vent Covers
- `cover.master_bedroom_v1`, `cover.master_bedroom_v2`
- `cover.blue_v1`, `cover.blue_v2`
- `cover.gold_v1`, `cover.gold_v2`
- `cover.green_v1`, `cover.green_v2`
- `cover.grey_v1`, `cover.grey_v2`
- `cover.guest_room_v1`, `cover.guest_room_v2`
- `cover.family_room_v1`, `cover.family_room_v2`
- `cover.kitchen_v1`, `cover.kitchen_v2`
- `cover.piano_room_v1`
- `cover.basement_v1`, `cover.basement_v2`, `cover.basement_v3`

---

## 🚀 Step 1: Deploy the Configuration

### Option A: Using Packages (Recommended)

1. **Ensure packages are enabled** in `configuration.yaml`:
   ```yaml
   homeassistant:
     packages: !include_dir_named packages
   ```

2. **Create packages directory** (if it doesn't exist):
   ```bash
   mkdir -p /config/packages
   ```

3. **Copy the file**:
   ```bash
   cp vent_zone_controller_updated.yaml /config/packages/vent_zone_controller.yaml
   ```

### Option B: Direct Include

Add to your `configuration.yaml`:
```yaml
# At the end of configuration.yaml
<<: !include vent_zone_controller_updated.yaml
```

---

## ✅ Step 2: Validate Configuration

### In Home Assistant UI:

1. Go to: **Developer Tools** → **YAML**
2. Click: **Check Configuration**
3. Wait for validation...
4. Look for: ✅ **"Configuration valid!"**

### If You Get Errors:

Check the error message carefully. Common issues:
- **Entity not found**: Update entity IDs in the YAML file
- **Duplicate entity**: You may have conflicting entity names
- **Syntax error**: Double-check YAML indentation

---

## 🔄 Step 3: Reload Configuration

**Don't restart Home Assistant yet!** Use selective reloads:

1. **Developer Tools** → **YAML**
2. Reload these in order:
   - ✅ **Template Entities** (loads all sensors)
   - ✅ **Scripts** (loads vent control scripts)
   - ✅ **Automations** (loads main control loop)

3. Wait 10-15 seconds for entities to populate

---

## 🔍 Step 4: Verify Entities Were Created

### Check Template Sensors

Go to: **Developer Tools** → **States**, search for:

**Occupancy Sensors (should show "on" or "off"):**
- `binary_sensor.master_occupied_recent`
- `binary_sensor.blue_occupied_recent`
- `binary_sensor.gold_occupied_recent`
- ... (all 9 rooms)

**Target Temperature Sensors (should show numbers like "72.0"):**
- `sensor.master_target_f`
- `sensor.blue_target_f`
- `sensor.gold_target_f`
- ... (all 9 rooms)

**Current Temperature Sensors (should show current temps):**
- `sensor.master_temp_f`
- `sensor.blue_temp_f`
- ... (all 9 rooms)

**Delta Sensors (should show positive/negative numbers):**
- `sensor.master_delta_f` (target minus current temp)
- `sensor.blue_delta_f`
- ... (all 9 rooms)

**Multi-Room Selector (the "brain"):**
- `sensor.rooms_to_condition` - Should show: "none", "master", "blue,gold", etc.

### Check Input Helpers

Go to: **Settings** → **Devices & Services** → **Helpers**

You should see:
- Min Other-Room Vent Open (%)
- Occupancy Linger (min)
- Occupancy Linger at Night (min)
- Room Hysteresis (°F)
- Closed Threshold (%)
- Relief Open (%)
- Heat Boost (°F)
- Condition Only When Occupied (toggle)
- Heat Boost Enabled (toggle)

### Check Groups

Go to: **Developer Tools** → **States**, search for `group.vents_`

You should see:
- `group.vents_master_bedroom`
- `group.vents_blue_room`
- `group.vents_gold_room`
- ... (all rooms)
- `group.vent_groups_all`

### Check Scripts

Go to: **Developer Tools** → **Services**

Search for these scripts:
- `script.set_multi_room_vents`
- `script.apply_ecobee_hold_for_rooms`

### Check Automation

Go to: **Settings** → **Automations**

Look for:
- **"Zone Controller – Multi-Room (Per-Room Targets / Delta)"**
- Should be **enabled** (blue toggle)

---

## 🧪 Step 5: Test Individual Components

### Test 1: Check Sensor Values

1. Go to: **Developer Tools** → **States**
2. Find: `sensor.rooms_to_condition`
3. Check the value:
   - **"none"** = No rooms need conditioning (all at target)
   - **"master"** = Master bedroom needs heating/cooling
   - **"master,blue,gold"** = Multiple rooms need conditioning

### Test 2: Manually Run the Script

1. Go to: **Developer Tools** → **Services**
2. Select service: `script.set_multi_room_vents`
3. Enter YAML data:
   ```yaml
   rooms_csv: "master"
   ```
4. Click: **Call Service**
5. **Expected result**: 
   - Master bedroom vents open to 100%
   - All other vents set to minimum (default 25%)

### Test 3: Check Vent Positions

1. Go to: **Developer Tools** → **States**
2. Search for your vent entities (e.g., `cover.master_bedroom_v1`)
3. Check `current_position` attribute
   - Should be 0-100 (percentage open)

### Test 4: Trigger the Automation Manually

1. Go to: **Settings** → **Automations**
2. Find: **"Zone Controller – Multi-Room"**
3. Click: **⋮** (three dots) → **Run**
4. Check the **Logbook** for activity

---

## 📊 Step 6: Monitor Live Operation

### Watch the Logbook

1. Go to: **Settings** → **System** → **Logs**
2. Or: **History** → Select your automation
3. Watch for:
   - Automation triggers (every 5 minutes, or on temp/occupancy changes)
   - Script executions
   - Vent position changes

### Enable Debug Logging (Optional)

Add to `configuration.yaml`:
```yaml
logger:
  default: info
  logs:
    homeassistant.components.automation: debug
    homeassistant.components.script: debug
```

Restart Home Assistant, then check: **Settings** → **System** → **Logs**

### Create a Test Dashboard

Create a new dashboard to monitor everything:

```yaml
type: vertical-stack
cards:
  # Control Panel
  - type: entities
    title: Vent Controller Settings
    entities:
      - input_number.min_other_room_open_pct
      - input_number.room_hysteresis_f
      - input_number.occupancy_linger_min
      - input_boolean.require_occupancy
      - input_boolean.heat_boost_enabled
      - input_number.heat_boost_f
      
  # Current Status
  - type: entities
    title: System Status
    entities:
      - sensor.rooms_to_condition
      - climate.main_floor_thermostat
      
  # Room Temperatures
  - type: entities
    title: Room Temperatures & Deltas
    entities:
      - sensor.master_temp_f
      - sensor.master_target_f
      - sensor.master_delta_f
      - sensor.blue_temp_f
      - sensor.blue_target_f
      - sensor.blue_delta_f
      - sensor.gold_temp_f
      - sensor.gold_target_f
      - sensor.gold_delta_f
      
  # Occupancy
  - type: entities
    title: Room Occupancy
    entities:
      - binary_sensor.master_occupied_recent
      - binary_sensor.blue_occupied_recent
      - binary_sensor.gold_occupied_recent
      - binary_sensor.green_occupied_recent
      - binary_sensor.grey_occupied_recent
      
  # Vent Positions
  - type: entities
    title: Vent Positions
    entities:
      - cover.master_bedroom_v1
      - cover.master_bedroom_v2
      - cover.blue_v1
      - cover.blue_v2
```

---

## 🧪 Step 7: Real-World Testing Scenarios

### Scenario 1: Single Room Too Cold (Heat Mode)

1. **Setup**:
   - Set thermostat to **Heat** mode
   - Make sure one room is 2°F+ below its target
   - Ensure room is occupied (or disable occupancy requirement)

2. **Expected Behavior**:
   - `sensor.rooms_to_condition` shows the cold room
   - That room's vents open to 100%
   - Other room vents set to minimum (25%)
   - Thermostat setpoint adjusts to that room's target (+ heat boost if enabled)

3. **Verify**:
   - Check vent positions in States
   - Check thermostat setpoint changed
   - Watch for automation execution in Logbook

### Scenario 2: Multiple Rooms Too Hot (Cool Mode)

1. **Setup**:
   - Set thermostat to **Cool** mode
   - Make multiple rooms 2°F+ above their targets
   - Ensure rooms are occupied

2. **Expected Behavior**:
   - `sensor.rooms_to_condition` shows multiple rooms (comma-separated)
   - Those rooms' vents open to 100%
   - Other rooms set to minimum
   - If >1/3 vents would close, relief vents open intelligently (unoccupied rooms first, then rooms closest to target)

### Scenario 3: Unoccupied Room

1. **Setup**:
   - Enable: `input_boolean.require_occupancy`
   - Make a room need conditioning but unoccupied

2. **Expected Behavior**:
   - Room is **NOT** added to `sensor.rooms_to_condition`
   - Vents remain at minimum
   - System focuses on occupied rooms

### Scenario 4: Night Linger Test

1. **Setup**:
   - Wait until after 10 PM
   - Walk into a room, then leave
   - Check occupancy sensor (should show "off")

2. **Expected Behavior**:
   - `binary_sensor.[room]_occupied_recent` stays **"on"** for 90 minutes (night linger)
   - Room continues to be conditioned during linger period
   - After 90 minutes, switches to "off"

### Scenario 5: 1/3 Closed Limit Protection

1. **Setup**:
   - Only select 1-2 rooms to condition (most vents will be at minimum)

2. **Expected Behavior**:
   - System calculates how many vents are below "closed threshold" (default 10%)
   - If more than 1/3 of total vents are closed, opens relief vents
   - Relief vents opened in priority order:
     - Unoccupied rooms first
     - Rooms closest to target temperature
   - Stops opening relief when ≤1/3 closed

3. **Verify**:
   - Count vents at minimum (25%)
   - Count total vents
   - Check if relief vents opened to "relief open" percentage (default 60%)

---

## 🐛 Step 8: Troubleshooting

### Problem: Entities Not Created

**Symptoms**: Can't find `sensor.master_temp_f` or other sensors

**Solutions**:
1. Check: **Developer Tools** → **YAML** → **Check Configuration**
2. Look for entity ID mismatches (sensor doesn't exist)
3. Reload: **Template Entities** again
4. Restart Home Assistant if needed

### Problem: Automation Not Triggering

**Symptoms**: Nothing happens when temps change

**Solutions**:
1. Check automation is **enabled**: Settings → Automations
2. Verify triggers are working: Check if delta sensors are changing
3. Check conditions: Is thermostat in heat/cool/auto mode?
4. Enable trace: Settings → Automations → Select automation → Traces

### Problem: Vents Not Moving

**Symptoms**: Script runs but vents stay put

**Solutions**:
1. Test vent control manually: Developer Tools → Services → `cover.set_cover_position`
2. Check Flair integration is working
3. Check vent battery levels (low battery = unresponsive)
4. Check group membership: Do groups contain correct vent entities?

### Problem: Thermostat Setpoint Changing Unexpectedly

**Symptoms**: Ecobee keeps adjusting

**Solutions**:
1. Check `input_boolean.auto_ecobee_hold` - set to "off" to disable
2. Check heat boost value (might be too high)
3. Look at `sensor.rooms_to_condition` - what rooms are being selected?
4. Check target temperatures from climate entities

### Problem: Too Many Rooms Conditioning at Once

**Symptoms**: All vents open, no relief

**Solutions**:
1. Increase `input_number.room_hysteresis_f` (default 1.0 → try 1.5 or 2.0)
2. Check room target temperatures - are they realistic?
3. Check if occupancy detection is working
4. Enable `input_boolean.require_occupancy` to limit to occupied rooms only

### Problem: Not Enough Rooms Conditioning

**Symptoms**: Cold/hot rooms being ignored

**Solutions**:
1. Decrease `input_number.room_hysteresis_f` (more sensitive)
2. Check occupancy: Is `input_boolean.require_occupancy` on?
3. Verify occupancy sensors are detecting properly
4. Check `sensor.[room]_delta_f` values - are they large enough?

---

## 📈 Step 9: Optimization Tips

### Tune Hysteresis

Start with 1.0°F and adjust based on results:
- **Too aggressive** (vents change too often): Increase to 1.5-2.0°F
- **Too slow** (rooms uncomfortable): Decrease to 0.5-0.8°F

### Adjust Occupancy Linger

Default: 30 minutes day, 90 minutes night
- **Too short**: Rooms stop conditioning while still in use
- **Too long**: Wastes energy on unoccupied rooms

### Set Min Vent Opening

Default: 25%
- **Too low**: Risk of HVAC pressure issues
- **Too high**: Less effective zoning

**Rule of thumb**: Never close more than 1/3 of vents

### Configure Relief Opening

Default: 60%
- Adjust based on how quickly pressure builds up
- Higher = more airflow when relief is needed

### Heat Boost

Default: 1.0°F
- Useful in cold climates to overcome thermal lag
- Set to 0 if causing overshooting

---

## ✅ Success Indicators

Your system is working correctly when:

1. ✅ `sensor.rooms_to_condition` updates when temps drift
2. ✅ Vents open/close automatically based on room needs
3. ✅ No more than 1/3 of vents are closed at once
4. ✅ Unoccupied rooms are deprioritized (when enabled)
5. ✅ Room temperatures stabilize around targets
6. ✅ Automation runs every 5 minutes (check Logbook)
7. ✅ Thermostat adjusts when rooms need conditioning
8. ✅ Night linger works (occupancy stays "recent" longer at night)

---

## 📞 Getting Help

If you're still having issues:

1. **Check the Logs**: Settings → System → Logs
2. **Enable Traces**: Settings → Automations → [Your automation] → Traces
3. **Capture the Data**: Take screenshots of:
   - `sensor.rooms_to_condition` value
   - Room delta values
   - Vent positions
   - Automation trace
4. **Share**: Post on Home Assistant Community Forums or Reddit

---

## 🎯 Quick Testing Checklist

Use this for a fast sanity check:

- [ ] Configuration validates without errors
- [ ] All template sensors created (check States)
- [ ] All input helpers visible (check Helpers)
- [ ] Automation appears in Automations list
- [ ] Scripts appear in Services
- [ ] `sensor.rooms_to_condition` shows a value (even "none")
- [ ] Can manually run `script.set_multi_room_vents`
- [ ] Vents respond to manual script calls
- [ ] Automation triggers on temperature change
- [ ] Vent positions change when automation runs
- [ ] Thermostat setpoint adjusts (if enabled)
- [ ] Occupancy sensors update properly
- [ ] Night linger extends occupancy after 10 PM

---

Happy testing! 🎉

Your multi-room vent controller should now provide intelligent, occupancy-aware zoning for your entire home!

