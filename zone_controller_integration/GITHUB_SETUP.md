# GitHub Setup Guide

## Repository Setup

### 1. Create GitHub Repository

1. Go to [GitHub](https://github.com/new)
2. Repository name: `homeassistant-smart-vent-controller` (or your preferred name)
3. Description: `Smart Vent Controller - Intelligent multi-room HVAC zone control for Home Assistant`
4. Visibility: Public (for HACS) or Private
5. **Do NOT** initialize with README, .gitignore, or license (we already have these)
6. Click "Create repository"

### 2. Connect Local Repository to GitHub

```bash
cd "/Users/ammon/Development/Home Assistant/zone_controller_integration"

# Add GitHub remote (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/homeassistant-smart-vent-controller.git

# Or if using SSH:
# git remote add origin git@github.com:YOUR_USERNAME/homeassistant-smart-vent-controller.git

# Push to GitHub
git branch -M main
git push -u origin main
```

### 3. Update Repository URLs

After pushing, update these files with your actual repository URL:

1. **`manifest.json`**:
   ```json
   "documentation": "https://github.com/YOUR_USERNAME/homeassistant-smart-vent-controller",
   "issue_tracker": "https://github.com/YOUR_USERNAME/homeassistant-smart-vent-controller/issues"
   ```

2. **`hacs.json`**:
   ```json
   {
     "name": "Smart Vent Controller",
     "hacs": "1.6.0",
     "domains": ["sensor", "binary_sensor", "number", "switch", "script", "automation"],
     "iot_class": "Local Polling",
     "homeassistant": "2023.1.0"
   }
   ```

3. **`README.md`**: Update any repository URLs

### 4. Create GitHub Release (Optional)

For HACS compatibility, create a release:

```bash
# Tag the current version
git tag -a v1.0.0 -m "Initial release: Smart Vent Controller v1.0.0"
git push origin v1.0.0
```

Or create via GitHub UI:
1. Go to Releases → "Create a new release"
2. Tag: `v1.0.0`
3. Title: `Smart Vent Controller v1.0.0`
4. Description: Copy from `CHANGELOG.md` or `COMPLETE_FEATURES_SUMMARY.md`
5. Publish release

## HACS Submission (Future)

Once on GitHub, you can submit to HACS:

1. **Requirements:**
   - Public repository
   - Proper `hacs.json` file
   - `README.md` with installation instructions
   - Releases/tags for versioning

2. **Submit:**
   - Go to [HACS Default Repositories](https://github.com/hacs/default)
   - Open an issue or PR to add your repository
   - Follow HACS submission guidelines

## Repository Structure

Your repository structure should look like:

```
homeassistant-smart-vent-controller/
├── custom_components/
│   └── smart_vent_controller/  # Note: Consider renaming folder
│       ├── __init__.py
│       ├── manifest.json
│       ├── config_flow.py
│       └── ... (all other files)
├── dashboard/
│   └── ... (dashboard cards)
├── tests/
│   └── ... (test files)
├── README.md
├── hacs.json
├── .gitignore
└── ... (documentation files)
```

## Important Notes

### Folder Name Consideration

The integration folder is currently named `zone_controller` but the domain is `smart_vent_controller`. Consider:

1. **Option A:** Keep folder as `zone_controller` (backward compatibility)
2. **Option B:** Rename folder to `smart_vent_controller` (consistency)

If renaming the folder:
```bash
cd custom_components
mv zone_controller smart_vent_controller
git add -A
git commit -m "Rename integration folder to match domain"
```

### First Push Checklist

- [ ] Repository created on GitHub
- [ ] Remote added and pushed
- [ ] Repository URLs updated in `manifest.json`
- [ ] `README.md` updated with correct URLs
- [ ] `.gitignore` includes all necessary patterns
- [ ] Initial release/tag created (optional)
- [ ] Repository description and topics set on GitHub

### GitHub Topics (Recommended)

Add these topics to your repository:
- `home-assistant`
- `homeassistant`
- `home-assistant-custom-components`
- `hacs`
- `hvac`
- `vent-control`
- `smart-home`
- `automation`

## Next Steps

1. **Push to GitHub** (commands above)
2. **Update URLs** in manifest.json and README.md
3. **Create initial release** (v1.0.0)
4. **Test installation** from GitHub
5. **Submit to HACS** (when ready)

## Testing Installation from GitHub

Users can install directly from GitHub:

```bash
cd /config/custom_components
git clone https://github.com/YOUR_USERNAME/homeassistant-smart-vent-controller.git
mv homeassistant-smart-vent-controller/smart_vent_controller smart_vent_controller
# Or if folder is still zone_controller:
mv homeassistant-smart-vent-controller/zone_controller smart_vent_controller
```

Or via HACS (once submitted):
- HACS → Integrations → Custom Repositories
- Add repository URL
- Install

