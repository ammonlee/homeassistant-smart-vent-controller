# Troubleshooting - Integration Not Showing Up

## Common Issues and Solutions

### Issue: Integration Not Appearing in Search

If "Zone Controller" doesn't show up when searching for integrations:

#### 1. Check File Location

**Verify the integration folder is in the correct location:**

```bash
# On your Home Assistant server
ls -la /config/custom_components/zone_controller/
```

**Should see:**
```
__init__.py
manifest.json
config_flow.py
const.py
coordinator.py
... (all other files)
```

**Common mistakes:**
- ❌ `/config/custom_components/zone_controller_integration/zone_controller/` (wrong - nested too deep)
- ❌ `/config/custom_components/zone_controller/custom_components/zone_controller/` (wrong - double nested)
- ✅ `/config/custom_components/zone_controller/` (correct)

#### 2. Verify manifest.json

**Check that manifest.json exists and is valid:**

```bash
cat /config/custom_components/zone_controller/manifest.json
```

**Should contain:**
```json
{
  "domain": "zone_controller",
  "name": "Zone Controller",
  "codeowners": ["@yourusername"],
  "config_flow": true,
  "dependencies": [],
  "documentation": "https://github.com/yourusername/homeassistant-zone-controller",
  "integration_type": "hub",
  "iot_class": "local_polling",
  "requirements": [],
  "version": "1.0.0"
}
```

#### 3. Check Home Assistant Logs

**Look for errors in the logs:**

1. Go to **Settings** → **System** → **Logs**
2. Look for errors related to `zone_controller` or `custom_components`
3. Common errors:
   - `ModuleNotFoundError` - Missing files
   - `SyntaxError` - Python syntax error
   - `ImportError` - Import issues

**Or check via SSH:**
```bash
tail -f /config/home-assistant.log | grep -i zone_controller
```

#### 4. Verify Python Files Are Present

**Check that all required Python files exist:**

```bash
ls -la /config/custom_components/zone_controller/*.py
```

**Required files:**
- `__init__.py` (MUST exist)
- `manifest.json` (MUST exist)
- `config_flow.py` (required for config flow)
- `const.py`
- `coordinator.py`
- `sensor.py`
- `binary_sensor.py`
- `number.py`
- `switch.py`
- `script.py`
- `automation.py`
- `scripts.py`
- `automations.py`

#### 5. Restart Home Assistant Properly

**Full restart required:**

1. **Settings** → **System** → **Restart**
2. Wait for full restart (can take 1-2 minutes)
3. Check logs for any startup errors

**Or via SSH:**
```bash
ha core restart
# Wait for restart to complete
ha core check
```

#### 6. Check Integration Discovery

**Custom integrations sometimes need to be discovered manually:**

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration** (bottom right)
3. Scroll down to see if "Zone Controller" appears in the list
4. If not, try typing the domain name: `zone_controller`

#### 7. Verify Integration Type

**Check that the integration is set up correctly:**

The integration should appear as a "hub" type integration. If it's not showing:

1. Check `manifest.json` has `"integration_type": "hub"`
2. Verify `config_flow: true` is set
3. Ensure `__init__.py` has proper async_setup_entry

#### 8. Check File Permissions

**Ensure files are readable:**

```bash
chmod -R 644 /config/custom_components/zone_controller/*.py
chmod -R 644 /config/custom_components/zone_controller/*.json
chmod 755 /config/custom_components/zone_controller/
```

#### 9. Validate Python Syntax

**Check for syntax errors:**

```bash
python3 -m py_compile /config/custom_components/zone_controller/__init__.py
python3 -m py_compile /config/custom_components/zone_controller/config_flow.py
```

**If errors, fix them before restarting.**

#### 10. Check Home Assistant Version

**Verify Home Assistant version:**

- Go to **Settings** → **System** → **About**
- Should be **2024.1 or later**
- Custom integrations require recent versions

## Step-by-Step Debugging

### Step 1: Verify Installation

```bash
# On Home Assistant server
cd /config
ls -la custom_components/zone_controller/ | head -20
```

**Expected output:**
```
total 120
drwxr-xr-x 1 root root  4096 Jan 1 12:00 .
drwxr-xr-x 1 root root  4096 Jan 1 12:00 ..
-rw-r--r-- 1 root root  1234 Jan 1 12:00 __init__.py
-rw-r--r-- 1 root root   456 Jan 1 12:00 manifest.json
-rw-r--r-- 1 root root  5678 Jan 1 12:00 config_flow.py
...
```

### Step 2: Check Logs

```bash
# Check for zone_controller in logs
grep -i "zone_controller" /config/home-assistant.log | tail -20
```

**Look for:**
- `Successfully set up zone_controller` (good)
- `Error setting up zone_controller` (bad - check error message)
- No mention (integration not loading)

### Step 3: Test Import

**Test if Python can import the module:**

```bash
# On Home Assistant server
cd /config
python3 -c "import sys; sys.path.insert(0, 'custom_components'); import zone_controller; print('Import successful')"
```

**If error, fix the Python issue first.**

### Step 4: Check Config Flow

**Verify config_flow.py is valid:**

```bash
python3 -m py_compile /config/custom_components/zone_controller/config_flow.py
```

**No output = success, errors = fix them**

## Alternative: Manual Discovery

If the integration still doesn't appear:

1. **Check Developer Tools:**
   - Go to **Developer Tools** → **Services**
   - Look for `zone_controller.*` services
   - If services exist, integration is loaded but not discoverable

2. **Try Direct URL:**
   - Navigate to: `http://your-ha-ip:8123/config/integrations/config_flow?domain=zone_controller`
   - This should open the config flow directly

3. **Check Integration Registry:**
   - Go to **Developer Tools** → **States**
   - Search for `zone_controller`
   - If entities exist, integration is working

## Still Not Working?

If none of the above works:

1. **Check Home Assistant Core Logs:**
   ```bash
   tail -100 /config/home-assistant.log
   ```

2. **Enable Debug Logging:**
   Add to `configuration.yaml`:
   ```yaml
   logger:
     default: info
     logs:
       custom_components.zone_controller: debug
   ```
   Then restart and check logs again.

3. **Verify All Files Copied:**
   ```bash
   # Count files
   find /config/custom_components/zone_controller -type f | wc -l
   # Should be ~20+ files
   ```

4. **Check for Missing Dependencies:**
   - Verify `manifest.json` doesn't require unavailable packages
   - Check that all imports in `__init__.py` are available

5. **Try Fresh Install:**
   - Remove the integration folder
   - Restart Home Assistant
   - Copy files again
   - Restart again

## Quick Checklist

- [ ] Files in `/config/custom_components/zone_controller/`
- [ ] `__init__.py` exists and is valid
- [ ] `manifest.json` exists and is valid JSON
- [ ] All Python files present
- [ ] Home Assistant restarted after copying files
- [ ] No errors in logs
- [ ] Home Assistant version 2024.1+
- [ ] File permissions correct
- [ ] Python syntax valid

## Getting Help

If still stuck, provide:
1. Home Assistant version
2. Full error from logs
3. Output of `ls -la /config/custom_components/zone_controller/`
4. Contents of `manifest.json`
5. Any Python import errors

