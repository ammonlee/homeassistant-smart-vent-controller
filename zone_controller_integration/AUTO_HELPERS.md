# Automatic Helper Entity Creation

## Overview

The Smart Vent Controller integration attempts to automatically create all required helper entities (input_number, input_boolean, input_text) when the integration is installed.

## How It Works

When you add the integration via the UI, the integration will:

1. **Check for existing entities** - Skips creation if entities already exist
2. **Attempt to create via storage collections** - Uses Home Assistant's internal APIs
3. **Fall back gracefully** - If auto-creation fails, logs instructions for manual creation

## What Gets Created

### Input Numbers (15+ entities)
- Configuration settings (min_other_room_open_pct, hysteresis, etc.)
- HVAC protection settings (min_runtime, min_off_time)
- Internal tracking (cycle timestamps, setpoint tracking)
- Room priorities (one per configured room)

### Input Booleans (5 entities)
- Control toggles (auto_vent_control, auto_thermostat_control)
- Feature toggles (require_occupancy, heat_boost_enabled, debug_mode)

### Input Text (1 entity)
- Internal tracking (hvac_last_action)

## Verification

After installation, check if helpers were created:

1. **Go to Settings** → **Devices & Services** → **Helpers**
2. **Look for Smart Vent Controller helpers:**
   - Input Numbers: `min_other_room_open_pct`, `occupancy_linger_min`, etc.
   - Input Booleans: `auto_vent_control`, `debug_mode`, etc.
   - Input Text: `hvac_last_action`

## If Auto-Creation Fails

If helpers weren't created automatically:

1. **Check logs:**
   - Settings → System → Logs
   - Look for Smart Vent Controller messages

2. **Create manually:**
   - See `HELPER_ENTITIES.md` for complete YAML configuration
   - Or create via UI: Settings → Devices & Services → Helpers → Create Helper

3. **Restart Home Assistant** after creating helpers

## Troubleshooting

### Helpers Not Created

**Possible causes:**
- Home Assistant version doesn't support storage collection API
- Permissions issue
- Storage collection not initialized yet

**Solution:**
- Create helpers manually via YAML (see `HELPER_ENTITIES.md`)
- Or create via UI

### Some Helpers Created, Others Not

**Possible causes:**
- Some entities already existed
- Storage collection API limitations

**Solution:**
- Check which ones exist
- Create missing ones manually
- Integration will skip existing ones

### Room Priorities Not Created

**Possible causes:**
- Rooms not configured yet
- Room names don't match expected format

**Solution:**
- Room priorities are created when rooms are added
- If missing, create manually or re-add rooms

## Manual Creation (Fallback)

If auto-creation doesn't work, use the YAML configuration from `HELPER_ENTITIES.md`:

1. **Copy the YAML** from `HELPER_ENTITIES.md`
2. **Add to `configuration.yaml`** or `packages/smart_vent_controller_helpers.yaml`
3. **Restart Home Assistant**
4. **Verify** in Settings → Devices & Services → Helpers

## Future Improvements

The integration may be updated to:
- Use more reliable creation methods
- Support more Home Assistant versions
- Provide better error messages
- Create helpers during config flow instead of after

## Notes

- **Existing entities are preserved** - Auto-creation skips entities that already exist
- **No data loss** - If helpers exist with different values, they're not modified
- **Graceful degradation** - Integration works even if some helpers aren't created
- **Logging** - Check logs to see what was created and what failed

