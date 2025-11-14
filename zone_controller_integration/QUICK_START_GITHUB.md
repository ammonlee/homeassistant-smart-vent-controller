# Quick Start: Upload to GitHub

## Step 1: Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `homeassistant-smart-vent-controller`
3. Description: `Smart Vent Controller - Intelligent multi-room HVAC zone control for Home Assistant`
4. Public (for HACS) or Private
5. **Don't** initialize with README/gitignore/license
6. Click "Create repository"

## Step 2: Push to GitHub

```bash
cd "/Users/ammon/Development/Home Assistant/zone_controller_integration"

# Add remote (replace YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/homeassistant-smart-vent-controller.git

# Push
git push -u origin main
```

## Step 3: Update URLs

After pushing, update these files with your actual GitHub URL:

1. **`custom_components/zone_controller/manifest.json`**:
   - Update `documentation` URL
   - Update `issue_tracker` URL

2. **Commit and push:**
   ```bash
   git add custom_components/zone_controller/manifest.json
   git commit -m "Update repository URLs"
   git push
   ```

## Step 4: Create Release (Optional)

```bash
git tag -a v1.0.0 -m "Initial release: Smart Vent Controller v1.0.0"
git push origin v1.0.0
```

Or via GitHub UI: Releases → Create a new release

## Done! 🎉

Your integration is now on GitHub and ready for:
- Manual installation
- HACS submission (when ready)
- Sharing with others

See `GITHUB_SETUP.md` for detailed instructions.

