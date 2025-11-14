# Pre-GitHub Upload Checklist

## ✅ Completed

- [x] Project renamed to "Smart Vent Controller"
- [x] Domain updated: `smart_vent_controller`
- [x] All code files updated
- [x] All documentation updated
- [x] All class names updated
- [x] Entity IDs updated
- [x] Service names updated
- [x] Dashboard cards updated
- [x] Git repository initialized
- [x] All changes committed
- [x] .gitignore created

## 📋 Before Uploading to GitHub

### 1. Update Repository URLs

**Files to update after creating GitHub repository:**

- [ ] `manifest.json` - Update `documentation` and `issue_tracker` URLs
- [ ] `README.md` - Update any repository references
- [ ] `hacs.json` - Verify name is correct (already done)

### 2. Consider Folder Name

**Current:** `custom_components/zone_controller/`  
**Domain:** `smart_vent_controller`

**Options:**
- [ ] Keep `zone_controller` folder (backward compatibility)
- [ ] Rename to `smart_vent_controller` folder (consistency)

**If renaming folder:**
```bash
cd zone_controller_integration/custom_components
mv zone_controller smart_vent_controller
cd ../..
git add -A
git commit -m "Rename integration folder to match domain name"
```

### 3. Final Review

- [ ] All tests pass (if applicable)
- [ ] README.md is complete and accurate
- [ ] Installation instructions are clear
- [ ] No sensitive information in code
- [ ] License file added (if needed)
- [ ] CHANGELOG.md created (optional but recommended)

### 4. GitHub Repository Setup

- [ ] Create repository on GitHub
- [ ] Add remote: `git remote add origin <your-repo-url>`
- [ ] Push: `git push -u origin main`
- [ ] Update repository URLs in code
- [ ] Create initial release (v1.0.0)
- [ ] Add repository topics/tags

## 🚀 Ready to Upload

Your project is ready! Follow the steps in `GITHUB_SETUP.md` to upload.

## 📝 Quick Commands

```bash
# Navigate to integration directory
cd zone_controller_integration

# Check status
git status

# View commit history
git log --oneline

# Add GitHub remote (after creating repo)
git remote add origin https://github.com/YOUR_USERNAME/homeassistant-smart-vent-controller.git

# Push to GitHub
git push -u origin main

# Create and push tag for release
git tag -a v1.0.0 -m "Initial release: Smart Vent Controller v1.0.0"
git push origin v1.0.0
```

