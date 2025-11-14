# Options Flow Guide

## Overview

The Zone Controller integration includes a complete **Options Flow** that allows you to update settings without reconfiguring rooms. This makes it easy to fine-tune the system after initial setup.

## How to Access Options Flow

1. **Go to Settings:**
   - **Settings** → **Devices & Services**

2. **Find Zone Controller:**
   - Look for "Zone Controller" in your integrations list
   - Click on it

3. **Open Options:**
   - Click the **Options** button (or three dots menu → **Configure**)
   - This opens the options flow

## What Can Be Changed

### Vent Control Settings
- **Minimum Other Room Open %** (0-100, default: 20)
  - Minimum vent position for rooms not being conditioned
  
- **Closed Threshold %** (0-100, default: 10)
  - Position below which a vent is considered "closed"
  
- **Relief Open %** (0-100, default: 60)
  - Position for relief vents when enforcing ≤1/3 closed rule
  
- **Max Relief Rooms** (1-10, default: 3)
  - Maximum number of rooms to use for relief

### Temperature Settings
- **Room Hysteresis (°F)** (0-5, default: 1.0)
  - Temperature difference threshold before conditioning
  
- **Heat Boost (°F)** (0-3, default: 1.0)
  - Temperature boost applied during heating cycles
  
- **Default Thermostat Temp (°F)** (65-80, default: 72)
  - Default temperature when no rooms need conditioning

### Occupancy Settings
- **Occupancy Linger (day, min)** (0-300, default: 30)
  - How long to consider room occupied during day hours
  
- **Occupancy Linger (night, min)** (0-300, default: 60)
  - How long to consider room occupied during night hours (22:00-06:00)

### HVAC Protection Settings
- **HVAC Minimum Runtime (min)** (0-30, default: 10)
  - Minimum runtime before allowing setpoint changes
  
- **HVAC Minimum Off Time (min)** (0-30, default: 5)
  - Minimum off time before allowing new cycle

### Automation Settings
- **Automation Cooldown (sec)** (0-300, default: 30)
  - Minimum time between automation triggers

### Control Toggles
- **Require Occupancy** (default: True)
  - Only condition rooms when recently occupied
  
- **Heat Boost Enabled** (default: True)
  - Enable/disable heat boost feature
  
- **Auto Thermostat Control** (default: True)
  - Enable/disable automatic thermostat control
  
- **Auto Vent Control** (default: True)
  - Enable/disable automatic vent control
  
- **Debug Mode** (default: False)
  - Enable enhanced logging for troubleshooting

## How It Works

### Options Storage

Settings are stored in `entry.options`:
- **Initial Setup**: Settings stored in both `entry.data` and `entry.options`
- **Options Flow**: Only updates `entry.options`
- **Scripts/Automations**: Read from `entry.options` (with fallback to defaults)

### Immediate Effect

Changes take effect immediately:
- No restart required
- Scripts and automations read updated values on next run
- Number/Switch platform entities update automatically

### Validation

All values are validated:
- Range checks (min/max)
- Type validation (int/float/bool)
- Invalid values show error messages

## Usage Example

### Scenario: Adjust Heat Boost

1. **Open Options:**
   - Settings → Devices & Services → Zone Controller → Options

2. **Change Heat Boost:**
   - Find "Heat Boost (°F)"
   - Change from 1.0 to 2.0
   - Click **Submit**

3. **Verify:**
   - Check `input_number.heat_boost_f` entity
   - Should show 2.0
   - Next heating cycle will use new value

### Scenario: Disable Vent Control Temporarily

1. **Open Options:**
   - Settings → Devices & Services → Zone Controller → Options

2. **Disable Vent Control:**
   - Find "Auto Vent Control"
   - Uncheck the toggle
   - Click **Submit**

3. **Effect:**
   - Vent control script will skip execution
   - Vents remain at current positions
   - Thermostat control continues normally

## Technical Details

### Options Flow Handler

```python
class ZoneControllerOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Zone Controller."""
    
    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            # Update options
            return self.async_create_entry(title="", data=user_input)
        
        # Show form with current values
        current_options = self.config_entry.options or {}
        # ... show form with defaults from current_options
```

### Reading Options in Scripts

```python
# In scripts.py
min_other = self.entry.options.get("min_other_room_open_pct", 20)
debug_mode = self.entry.options.get("debug_mode", False)
```

### Updating Number/Switch Entities

The Number and Switch platforms automatically sync with options:
- When options change, platform entities update
- When platform entities change, options update
- Bidirectional sync ensures consistency

## Best Practices

### When to Use Options Flow

✅ **Use Options Flow for:**
- Adjusting thresholds and settings
- Enabling/disabling features
- Fine-tuning protection settings
- Temporary changes (debug mode, etc.)

❌ **Don't Use Options Flow for:**
- Adding/removing rooms (use reconfiguration)
- Changing main thermostat (use reconfiguration)
- Changing room entities (use reconfiguration)

### Testing Changes

1. **Make small changes first**
2. **Monitor logs** (enable debug mode)
3. **Watch automation behavior**
4. **Verify expected results**

### Reverting Changes

1. **Open Options Flow**
2. **Change values back**
3. **Or use "Reset to Defaults" service:**
   ```yaml
   service: zone_controller.reset_to_defaults
   ```

## Troubleshooting

### Options Not Saving

- Check for validation errors
- Verify all required fields
- Check Home Assistant logs

### Changes Not Taking Effect

- Verify options were saved (check `entry.options`)
- Check if scripts are reading from options
- Restart Home Assistant if needed

### Options Flow Not Appearing

- Verify integration is properly installed
- Check `config_flow.py` has `async_get_options_flow`
- Restart Home Assistant

## Advanced Usage

### Programmatic Updates

You can update options programmatically:

```python
# In a script or automation
hass.config_entries.async_update_entry(
    entry,
    options={
        **entry.options,
        "heat_boost_f": 2.0,
    }
)
```

### Reading Current Options

```python
# In a script
current_options = entry.options
heat_boost = current_options.get("heat_boost_f", 1.0)
```

## Summary

The Options Flow provides a convenient way to:
- ✅ Update settings without reconfiguring rooms
- ✅ Fine-tune system behavior
- ✅ Enable/disable features
- ✅ Adjust protection settings
- ✅ Make changes take effect immediately

All changes are validated and take effect immediately without requiring a restart!

