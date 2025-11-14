# Installation Checklist - Integration Not Showing Up

## Quick Fix Steps

### 1. Verify File Location ✅

**Check that files are in the EXACT location:**

```bash
# On your Home Assistant server (via SSH or Samba)
ls -la /config/custom_components/zone_controller/
```

**You should see:**
- `__init__.py`
- `manifest.json`
- `config_flow.py`
- And ~15 other Python files

**Common mistake:** Files might be in:
- ❌ `/config/custom_components/zone_controller_integration/zone_controller/` (WRONG - too nested)
- ✅ `/config/custom_components/zone_controller/` (CORRECT)

### 2. Fix manifest.json ✅

The `integration_type: "system"` might cause issues. I've updated it. Make sure your `manifest.json` looks like this:

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
  "dependencies": []
}
```

**Note:** Removed `"integration_type": "system"` - this can prevent discovery.

### 3. Restart Home Assistant ✅

**Full restart required:**

1. Go to **Settings** → **System** → **Restart**
2. Wait 1-2 minutes for full restart
3. Check logs for errors

### 4. Check Logs for Errors ✅

**Look for errors:**

1. Go to **Settings** → **System** → **Logs**
2. Search for: `zone_controller` or `custom_components`
3. Look for any red errors

**Common errors:**
- `ModuleNotFoundError` - Missing file
- `SyntaxError` - Python error
- `ImportError` - Import issue

### 5. Try Direct URL Method ✅

**If search doesn't work, try direct access:**

1. Open this URL in your browser (replace with your HA IP):
   ```
   http://YOUR_HA_IP:8123/config/integrations/config_flow?domain=zone_controller
   ```

2. This should open the config flow directly

### 6. Check Integration Discovery ✅

**Sometimes integrations appear in a different way:**

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration** (bottom right)
3. **Don't search** - just scroll down the list
4. Look for "Zone Controller" in the list

### 7. Verify Python Syntax ✅

**Check for Python errors:**

```bash
# On Home Assistant server
python3 -m py_compile /config/custom_components/zone_controller/__init__.py
python3 -m py_compile /config/custom_components/zone_controller/config_flow.py
```

**No output = success. Errors = fix them.**

## Step-by-Step Debugging

### Step 1: Copy Files Correctly

```bash
# On your development machine, copy the integration folder
# Make sure you copy the zone_controller folder, not zone_controller_integration

# Correct:
cp -r zone_controller_integration/custom_components/zone_controller /path/to/ha/config/custom_components/

# Wrong:
cp -r zone_controller_integration /path/to/ha/config/custom_components/
```

### Step 2: Verify Structure

```bash
# On Home Assistant server
cd /config/custom_components/zone_controller
ls -la
```

**Should see ~20 files including:**
- `__init__.py` (MUST exist)
- `manifest.json` (MUST exist)
- `config_flow.py`
- All other Python files

### Step 3: Check File Permissions

```bash
# Make sure files are readable
chmod 644 /config/custom_components/zone_controller/*.py
chmod 644 /config/custom_components/zone_controller/*.json
```

### Step 4: Restart and Check Logs

```bash
# Restart Home Assistant
ha core restart

# Wait for restart, then check logs
tail -50 /config/home-assistant.log | grep -i zone
```

## Still Not Working?

### Enable Debug Logging

Add to `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.zone_controller: debug
```

Then restart and check logs again.

### Manual Import Test

```bash
# On Home Assistant server
cd /config
python3 -c "import sys; sys.path.insert(0, 'custom_components'); import zone_controller; print('SUCCESS')"
```

**If this fails, there's a Python error to fix.**

### Check Home Assistant Version

- Go to **Settings** → **System** → **About**
- Should be **2024.1 or later**
- Older versions may not support custom integrations properly

## Alternative: Manual Configuration

If the UI integration doesn't work, you can try configuring via YAML (though the integration is designed for UI config):

1. Add to `configuration.yaml`:
```yaml
zone_controller:
  main_thermostat: climate.main_floor_thermostat
  rooms:
    - name: "Master Bedroom"
      climate_entity: climate.master_bedroom_room
      vent_entities:
        - cover.master_bedroom_v1
        - cover.master_bedroom_v2
```

**Note:** This may not work if config_flow is required. The UI method is preferred.

## Quick Checklist

Run through this checklist:

- [ ] Files copied to `/config/custom_components/zone_controller/`
- [ ] `__init__.py` exists
- [ ] `manifest.json` exists and is valid JSON
- [ ] `manifest.json` does NOT have `"integration_type": "system"`
- [ ] All Python files present (~20 files)
- [ ] Home Assistant restarted after copying
- [ ] No errors in logs
- [ ] Tried direct URL method
- [ ] Checked integration list (not just search)
- [ ] Home Assistant version 2024.1+

## What to Share for Help

If still stuck, share:

1. **File location:** Output of `ls -la /config/custom_components/zone_controller/`
2. **Log errors:** Any errors from logs
3. **HA version:** From Settings → System → About
4. **manifest.json contents:** Copy the file contents
5. **Python test:** Output of manual import test

