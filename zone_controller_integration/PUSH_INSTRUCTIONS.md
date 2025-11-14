# Push Instructions - HACS Compliance Fix

## ✅ What Was Fixed

The integration folder has been renamed to match the domain:
- **Before:** `custom_components/zone_controller/`
- **After:** `custom_components/smart_vent_controller/`

This is required for HACS compliance - the folder name must match the domain name in `manifest.json`.

## 📤 Push to GitHub

The changes are committed locally but need to be pushed. Choose one method:

### Method 1: Using GitHub CLI (Recommended)

```bash
cd "/Users/ammon/Development/Home Assistant/zone_controller_integration"
gh auth login
git push origin main
```

### Method 2: Using SSH (If SSH key is set up)

```bash
cd "/Users/ammon/Development/Home Assistant/zone_controller_integration"
git remote set-url origin git@github.com:ammonlee/homeassistant-smart-vent-controller.git
git push origin main
```

### Method 3: Using Personal Access Token (Create New Token)

1. Create a new token: https://github.com/settings/tokens
2. Give it `repo` permissions
3. Push:
   ```bash
   cd "/Users/ammon/Development/Home Assistant/zone_controller_integration"
   git push https://YOUR_NEW_TOKEN@github.com/ammonlee/homeassistant-smart-vent-controller.git main
   ```

### Method 4: Manual Push via GitHub Web UI

If you can't push via command line:
1. Go to https://github.com/ammonlee/homeassistant-smart-vent-controller
2. The changes will show as unpushed commits
3. You can manually update files via web UI if needed

## ✅ Verification

After pushing, verify the structure:
- Repository should have: `custom_components/smart_vent_controller/`
- Folder name matches domain: `smart_vent_controller`
- HACS should now accept the repository structure

## 📋 Commits Ready to Push

- `16c6bc8` - Fix HACS compliance: Rename integration folder to match domain
- `1b88f04` - Update README.md with correct GitHub username

