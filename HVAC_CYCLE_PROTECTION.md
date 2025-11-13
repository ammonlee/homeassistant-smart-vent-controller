# HVAC Cycle Protection - Short-Cycle Prevention

## Overview

This feature prevents short cycling of your HVAC system, which can:
- **Damage equipment** - Rapid on/off cycles stress compressors, motors, and other components
- **Reduce efficiency** - Systems need time to reach optimal operating conditions
- **Increase energy costs** - Starting up uses more energy than maintaining operation
- **Shorten equipment lifespan** - Excessive cycling causes premature wear

## How It Works

The system tracks when your HVAC starts and stops, then enforces minimum runtime and off-time periods before allowing thermostat setpoint changes.

### Minimum Runtime Protection
- **Default**: 10 minutes
- **Purpose**: Ensures HVAC runs for a minimum duration before allowing setpoint changes
- **Benefit**: Prevents premature shutdowns that could cause rapid re-starts

### Minimum Off-Time Protection  
- **Default**: 5 minutes
- **Purpose**: Ensures HVAC stays off for a minimum duration before allowing new cycles
- **Benefit**: Prevents rapid cycling when conditions change quickly

## Configuration

### Input Numbers (Sliders)

**`hvac_min_runtime_min`**
- **Range**: 0-30 minutes
- **Default**: 10 minutes
- **Description**: Minimum time HVAC must run before allowing setpoint changes
- **Recommendation**: 
  - Furnaces: 5-15 minutes
  - Heat pumps: 10-20 minutes
  - Set to 0 to disable runtime protection

**`hvac_min_off_time_min`**
- **Range**: 0-30 minutes  
- **Default**: 5 minutes
- **Description**: Minimum time HVAC must be off before allowing new cycle
- **Recommendation**:
  - Standard systems: 5-10 minutes
  - High-efficiency systems: 3-5 minutes
  - Set to 0 to disable off-time protection

## How It Protects

### Scenario 1: HVAC Just Started
```
Time: 10:00 AM - HVAC starts heating
Time: 10:05 AM - Automation wants to change setpoint
Result: BLOCKED - Only 5 minutes elapsed, need 10 minutes minimum
Time: 10:10 AM - Automation tries again
Result: ALLOWED - 10 minutes elapsed, minimum runtime satisfied
```

### Scenario 2: HVAC Just Stopped
```
Time: 10:30 AM - HVAC stops (reached setpoint)
Time: 10:32 AM - Room temp drops, automation wants to start heating
Result: BLOCKED - Only 2 minutes off, need 5 minutes minimum
Time: 10:35 AM - Automation tries again  
Result: ALLOWED - 5 minutes elapsed, minimum off-time satisfied
```

## Monitoring

### Template Sensors

**`sensor.hvac_cycle_protection_status`**
- **State**: `protected` or `allowed`
- **Attributes**:
  - `can_change_setpoint`: Boolean indicating if setpoint changes are allowed
  - `runtime_remaining`: Minutes remaining before runtime protection expires (when running)
  - `off_time_remaining`: Minutes remaining before off-time protection expires (when idle)

**`sensor.hvac_cycle_start_time`**
- Shows timestamp when current cycle started
- Attributes show formatted time and elapsed runtime

**`sensor.hvac_cycle_end_time`**
- Shows timestamp when last cycle ended
- Attributes show formatted time and elapsed off-time

## Behavior Details

### When Protection is Active

1. **During Runtime Protection** (HVAC running < minimum runtime):
   - Setpoint changes are **blocked**
   - Vents can still adjust (vent control is independent)
   - Protection expires automatically after minimum runtime

2. **During Off-Time Protection** (HVAC off < minimum off-time):
   - Setpoint changes are **blocked**
   - Vents can still adjust
   - Protection expires automatically after minimum off-time

### When Protection is Not Active

- Setpoint changes proceed normally
- All automation functions normally
- No delays or restrictions

## Debugging

Enable `input_boolean.debug_mode` to see detailed logs:

```
HVAC Cycle: Started heating at 10:00:00. Minimum runtime: 10 minutes
Thermostat Control: BLOCKED by cycle protection. Action=heating, Can Change=false
HVAC Cycle: Stopped heating at 10:15:00. Minimum off time: 5 minutes
Thermostat Control: Mode=heat, Cycle Protection=true, Can Change=true, Should Set=true
```

## Recommendations

### For Standard Gas Furnaces
- **Minimum Runtime**: 10-15 minutes
- **Minimum Off-Time**: 5-7 minutes
- **Rationale**: Furnaces need time to heat up and cool down properly

### For Heat Pumps
- **Minimum Runtime**: 15-20 minutes  
- **Minimum Off-Time**: 5-10 minutes
- **Rationale**: Heat pumps are more efficient with longer cycles

### For High-Efficiency Systems
- **Minimum Runtime**: 5-10 minutes
- **Minimum Off-Time**: 3-5 minutes
- **Rationale**: Modern systems can handle shorter cycles better

### To Disable Protection
Set both `hvac_min_runtime_min` and `hvac_min_off_time_min` to `0`

## Technical Details

- Protection is enforced in `script.apply_ecobee_hold_for_rooms`
- Cycle timing is tracked by `automation.track_hvac_cycle_timing`
- Timestamps stored in `input_number.hvac_cycle_start_timestamp` and `input_number.hvac_cycle_end_timestamp`
- State transitions tracked in `input_text.hvac_last_action`

## Notes

- Protection only affects **setpoint changes**, not vent adjustments
- Manual thermostat overrides bypass cycle protection (user intent takes priority)
- Protection automatically expires - no manual intervention needed
- If timestamps are missing (0), protection allows changes (failsafe)

