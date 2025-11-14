# Diagnostics Support - Implementation Complete ✅

## Status: **FULLY IMPLEMENTED**

Diagnostics support has been added to the Zone Controller integration, providing comprehensive information for troubleshooting and support.

## What's Implemented

### ✅ Diagnostics Module (`diagnostics.py`)

**Function:**
- `async_get_config_entry_diagnostics()` - Returns comprehensive diagnostic data

**Information Collected:**
- Configuration (main thermostat, room count, options)
- Room states (temperatures, targets, deltas, occupancy, vent positions)
- Main thermostat state (mode, action, temperatures)
- Automation status (enabled/disabled features)
- Cycle protection status
- Manual override detection
- Statistics
- Device registry information

### ✅ Integration Registration

**In `__init__.py`:**
- Diagnostics function registered
- Accessible via Home Assistant UI

## How to Access Diagnostics

### Via Home Assistant UI

1. **Go to Settings:**
   - Settings → Devices & Services

2. **Find Zone Controller:**
   - Click on "Zone Controller" integration

3. **Download Diagnostics:**
   - Click the three dots menu (⋮)
   - Select "Download diagnostics"
   - JSON file will be downloaded

### Via Developer Tools

1. **Go to Developer Tools:**
   - Developer Tools → Services

2. **Call Diagnostics Service:**
   ```yaml
   service: system_health.download_diagnostics
   data:
     config_entry_id: <your_entry_id>
   ```

## Diagnostic Data Structure

### Configuration

```json
{
  "config": {
    "main_thermostat": "climate.main_thermostat",
    "rooms_count": 2,
    "options": {
      "min_other_room_open_pct": 20,
      "heat_boost_f": 1.0,
      ...
    }
  }
}
```

### Main Thermostat

```json
{
  "main_thermostat": {
    "entity": "climate.main_thermostat",
    "state": "heat",
    "available": true,
    "hvac_action": "heating",
    "temperature": 75.0,
    "current_temperature": 70.0
  }
}
```

### Rooms

```json
{
  "rooms": [
    {
      "name": "Master Bedroom",
      "key": "master_bedroom",
      "climate_entity": "climate.master_bedroom_room",
      "climate_available": true,
      "current_temperature": 69.0,
      "target_temperature": 73.0,
      "delta": 4.0,
      "occupied": true,
      "vent_positions": [
        {
          "entity": "cover.master_v1",
          "position": 100,
          "available": true
        }
      ]
    }
  ]
}
```

### Automation Status

```json
{
  "automation_status": {
    "auto_vent_control": true,
    "auto_thermostat_control": true,
    "require_occupancy": true,
    "debug_mode": false
  }
}
```

### Cycle Protection

```json
{
  "cycle_protection": {
    "enabled": true,
    "min_runtime_min": 10,
    "min_off_time_min": 5
  }
}
```

## Use Cases

### Troubleshooting

**Problem:** Room not being conditioned

**Check Diagnostics:**
1. Room `climate_available` = true?
2. Room `current_temperature` present?
3. Room `delta` calculated correctly?
4. Room `occupied` = true (if require_occupancy enabled)?
5. Vents `available` and positioned correctly?

**Problem:** Thermostat not responding

**Check Diagnostics:**
1. `main_thermostat.available` = true?
2. `main_thermostat.state` correct?
3. `manual_override` = false?
4. `cycle_protection.enabled` blocking?

### Support

**When Reporting Issues:**
1. Download diagnostics
2. Include in bug report
3. Provides complete system state

**For Support Requests:**
- Share diagnostics file
- Shows all configuration
- Shows current state
- Shows entity availability

### Monitoring

**Track System Health:**
- Monitor `rooms_to_condition`
- Check `statistics` for trends
- Verify `automation_status`
- Review `cycle_protection` status

## Benefits

### ✅ Troubleshooting
- **Complete State:** All information in one place
- **Entity Availability:** Know which entities are unavailable
- **Configuration:** See all settings at a glance
- **Current Values:** Real-time state information

### ✅ Support
- **Easy Sharing:** Download and share diagnostics file
- **Complete Context:** Support has all needed information
- **No Manual Collection:** Automatic data gathering

### ✅ Monitoring
- **System Health:** Track integration status
- **Performance:** Monitor statistics
- **Configuration:** Verify settings

## Example Diagnostic Output

```json
{
  "config": {
    "main_thermostat": "climate.main_thermostat",
    "rooms_count": 2,
    "options": {...}
  },
  "main_thermostat": {
    "entity": "climate.main_thermostat",
    "state": "heat",
    "available": true,
    "hvac_action": "heating",
    "temperature": 75.0,
    "current_temperature": 70.0
  },
  "rooms": [
    {
      "name": "Master Bedroom",
      "current_temperature": 69.0,
      "target_temperature": 73.0,
      "delta": 4.0,
      "occupied": true,
      "vent_positions": [...]
    }
  ],
  "rooms_to_condition": "master_bedroom",
  "automation_status": {
    "auto_vent_control": true,
    "auto_thermostat_control": true
  },
  "cycle_protection": {
    "enabled": true,
    "min_runtime_min": 10
  },
  "manual_override": false,
  "statistics": {...},
  "devices": [...],
  "timestamp": "2024-01-15T10:30:00"
}
```

## Summary

Diagnostics support is **complete and functional**:

✅ **Comprehensive data** - All integration information  
✅ **Easy access** - Via UI download  
✅ **Troubleshooting** - Complete system state  
✅ **Support** - Easy to share diagnostics  
✅ **Monitoring** - Track system health  

The integration now provides **excellent diagnostics** for troubleshooting and support!

