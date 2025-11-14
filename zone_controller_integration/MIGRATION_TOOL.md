# Migration Tool - YAML to Integration

## Overview

This document outlines the implementation of a migration tool to help users transition from the YAML-based configuration to the new UI-based integration.

## Current State

- **YAML Configuration:** Users have `vent_smart_vent_controller.yaml` with room definitions
- **Integration:** New UI-based integration with config flow
- **Gap:** Manual migration required, which can be error-prone

## Migration Tool Design

### Detection Phase

1. **Scan for YAML Configuration:**
   - Check for `vent_smart_vent_controller.yaml` in packages directory
   - Parse YAML to extract configuration
   - Identify rooms, thermostat, settings

2. **Validate Configuration:**
   - Check entity availability
   - Verify room configurations
   - Validate settings

### Import Phase

1. **Create Config Entry:**
   - Extract main thermostat
   - Extract room configurations
   - Extract settings/options
   - Create config entry via config flow

2. **Preserve Settings:**
   - Map YAML settings to integration options
   - Maintain room priorities
   - Preserve custom thresholds

### Migration Wizard

1. **Step 1: Detection**
   - Show detected YAML configuration
   - Display rooms found
   - Show settings detected

2. **Step 2: Validation**
   - Check entity availability
   - Show warnings for unavailable entities
   - Allow entity corrections

3. **Step 3: Import**
   - Create config entry
   - Import rooms
   - Import settings
   - Show success/errors

## Implementation Plan

### Phase 1: YAML Parser

```python
# migration/yaml_parser.py
async def parse_yaml_config(hass: HomeAssistant, yaml_path: str) -> dict:
    """Parse YAML configuration file."""
    # Load and parse YAML
    # Extract rooms, thermostat, settings
    # Return structured data
```

### Phase 2: Config Flow Import Step

```python
# config_flow.py
async def async_step_import(self, import_info: dict) -> FlowResult:
    """Handle import from YAML."""
    # Validate imported data
    # Create config entry
    # Return success
```

### Phase 3: Migration Wizard

```python
# migration/wizard.py
class MigrationWizard:
    """Wizard to guide users through migration."""
    async def detect_yaml_config(self):
        """Detect existing YAML configuration."""
    
    async def validate_entities(self):
        """Validate entities from YAML."""
    
    async def import_config(self):
        """Import configuration to integration."""
```

## Benefits

- ✅ **Easy Transition:** Automated migration process
- ✅ **Error Prevention:** Validation before import
- ✅ **Settings Preservation:** Maintains existing configuration
- ✅ **User-Friendly:** Guided wizard interface

## Status

**Status:** Not yet implemented  
**Priority:** Medium  
**Estimated Effort:** 2-3 hours

