# UI Configuration Guide

## How the Configuration Wizard Works

The Zone Controller integration uses Home Assistant's **Config Flow** system, which provides a step-by-step UI wizard. No YAML editing required!

## Step-by-Step Process

### Step 1: Select Main Thermostat

**What you see:**
- A dropdown list of all available climate entities
- The first available thermostat is pre-selected

**What happens:**
- The integration scans your Home Assistant instance for all `climate.*` entities
- Displays them in a searchable dropdown (Entity Selector)
- Validates that the selected entity exists before proceeding

**Code behind it:**
```python
# Scans for climate entities
climate_entities = sorted([
    entity_id for entity_id in self.hass.states.async_entity_ids("climate")
])

# Shows entity selector dropdown
selector.EntitySelector(
    selector.EntitySelectorConfig(domain="climate")
)
```

**User Experience:**
```
┌─────────────────────────────────────┐
│ Zone Controller Setup               │
├─────────────────────────────────────┤
│                                     │
│ Main Thermostat:                    │
│ ┌─────────────────────────────────┐ │
│ │ climate.main_floor_thermostat ▼ │ │  ← Dropdown with search
│ └─────────────────────────────────┘ │
│                                     │
│        [ SUBMIT ]                   │
└─────────────────────────────────────┘
```

### Step 2: Add Rooms (Repeatable)

**What you see:**
- Form fields for each room configuration:
  - Room Name (text input)
  - Climate Entity (dropdown - filtered to climate entities)
  - Temperature Sensor (dropdown - filtered to sensor entities, optional)
  - Occupancy Sensor (dropdown - filtered to binary_sensor entities, optional)
  - Vent Entities (multi-select dropdown - filtered to cover entities)
  - Priority (slider 0-10)
  - "Add Another Room" checkbox

**What happens:**
- Each field uses **Entity Selectors** which:
  - Filter entities by domain (climate, sensor, binary_sensor, cover)
  - Provide search/filter functionality
  - Show friendly names when available
  - Validate entity IDs automatically

**Code behind it:**
```python
# Climate entity selector
selector.EntitySelector(
    selector.EntitySelectorConfig(domain="climate")
)

# Temperature sensor selector
selector.EntitySelector(
    selector.EntitySelectorConfig(domain="sensor")
)

# Occupancy sensor selector
selector.EntitySelector(
    selector.EntitySelectorConfig(domain="binary_sensor")
)

# Vent entities (multiple selection)
selector.EntitySelector(
    selector.EntitySelectorConfig(domain="cover", multiple=True)
)

# Priority slider
selector.NumberSelector(
    selector.NumberSelectorConfig(
        min=0, max=10, step=1,
        mode=selector.NumberSelectorMode.SLIDER
    )
)
```

**User Experience:**
```
┌─────────────────────────────────────┐
│ Configure Rooms                     │
├─────────────────────────────────────┤
│                                     │
│ Room Name:                          │
│ ┌─────────────────────────────────┐ │
│ │ Master Bedroom                  │ │  ← Text input
│ └─────────────────────────────────┘ │
│                                     │
│ Climate Entity:                     │
│ ┌─────────────────────────────────┐ │
│ │ climate.master_bedroom_room  ▼  │ │  ← Dropdown
│ └─────────────────────────────────┘ │
│                                     │
│ Temperature Sensor (optional):       │
│ ┌─────────────────────────────────┐ │
│ │ sensor.master_bedroom_temp_degf │ │  ← Dropdown
│ └─────────────────────────────────┘ │
│                                     │
│ Occupancy Sensor (optional):         │
│ ┌─────────────────────────────────┐ │
│ │ binary_sensor.master_occupied ▼ │ │  ← Dropdown
│ └─────────────────────────────────┘ │
│                                     │
│ Vent Entities:                       │
│ ┌─────────────────────────────────┐ │
│ │ ☑ cover.master_v1              │ │  ← Multi-select
│ │ ☑ cover.master_v2              │ │
│ │ ☐ cover.master_v3              │ │
│ └─────────────────────────────────┘ │
│                                     │
│ Priority: [━━━━━━━━━━━━━━━━━━] 5   │  ← Slider
│           0                   10    │
│                                     │
│ ☐ Add Another Room                  │  ← Checkbox
│                                     │
│        [ SUBMIT ]                   │
└─────────────────────────────────────┘
```

**Repeating the Step:**
- If "Add Another Room" is checked, the form clears and shows again
- Previously added rooms are stored in memory
- You can add as many rooms as needed
- When unchecked and submitted, moves to next step

### Step 3: Configure Settings

**What you see:**
- Number inputs for all configuration values:
  - Minimum Other Room Open %
  - Closed Threshold %
  - Relief Open %
  - Max Relief Rooms
  - Room Hysteresis (°F)
  - HVAC Minimum Runtime (min)
  - HVAC Minimum Off Time (min)

**What happens:**
- Each field has:
  - Default value pre-filled
  - Min/max validation
  - Appropriate step size
  - Unit labels

**Code behind it:**
```python
vol.Optional(
    "min_other_room_open_pct",
    default=DEFAULT_MIN_OTHER_ROOM_OPEN_PCT  # 20
): vol.All(int, vol.Range(min=0, max=100))
```

**User Experience:**
```
┌─────────────────────────────────────┐
│ Configure Settings                   │
├─────────────────────────────────────┤
│                                     │
│ Minimum Other Room Open %:          │
│ ┌─────────────────────────────────┐ │
│ │ 20                               │ │  ← Number input
│ └─────────────────────────────────┘ │
│                                     │
│ Closed Threshold %:                 │
│ ┌─────────────────────────────────┐ │
│ │ 10                               │ │
│ └─────────────────────────────────┘ │
│                                     │
│ Relief Open %:                      │
│ ┌─────────────────────────────────┐ │
│ │ 60                               │ │
│ └─────────────────────────────────┘ │
│                                     │
│ ... (more settings)                 │
│                                     │
│        [ SUBMIT ]                   │
└─────────────────────────────────────┘
```

### Step 4: Completion

**What happens:**
- Creates the config entry
- Stores all data in `entry.data` and `entry.options`
- Integration starts loading
- Platforms create entities

**Data Structure:**
```python
{
    "main_thermostat": "climate.main_floor_thermostat",
    "rooms": [
        {
            "name": "Master Bedroom",
            "climate_entity": "climate.master_bedroom_room",
            "temp_sensor": "sensor.master_bedroom_temp_degf",
            "occupancy_sensor": "binary_sensor.master_occupied",
            "vent_entities": ["cover.master_v1", "cover.master_v2"],
            "priority": 5
        },
        # ... more rooms
    ],
    "options": {
        "min_other_room_open_pct": 20,
        "closed_threshold_pct": 10,
        # ... more options
    }
}
```

## Entity Selectors Explained

### What are Entity Selectors?

Entity Selectors are Home Assistant UI components that provide:
- **Search**: Type to filter entities
- **Filtering**: Only shows entities of the specified domain
- **Validation**: Ensures entity IDs are valid
- **Friendly Names**: Shows entity friendly_name when available

### Types Used

1. **EntitySelector** (single selection):
   ```python
   selector.EntitySelector(
       selector.EntitySelectorConfig(domain="climate")
   )
   ```
   - Shows dropdown with search
   - Filters to climate entities only
   - Returns single entity ID string

2. **EntitySelector** (multiple selection):
   ```python
   selector.EntitySelector(
       selector.EntitySelectorConfig(domain="cover", multiple=True)
   )
   ```
   - Shows multi-select dropdown
   - Allows selecting multiple entities
   - Returns list of entity IDs

3. **NumberSelector** (slider):
   ```python
   selector.NumberSelector(
       selector.NumberSelectorConfig(
           min=0, max=10, step=1,
           mode=selector.NumberSelectorMode.SLIDER
       )
   )
   ```
   - Shows slider control
   - Visual feedback
   - Returns number value

## Options Flow (Updating Settings)

After initial setup, you can update settings via:

**Settings → Devices & Services → Zone Controller → Options**

This shows the same settings form (Step 3) but updates existing values.

**Code:**
```python
@staticmethod
@callback
def async_get_options_flow(config_entry):
    """Return options flow handler."""
    return ZoneControllerOptionsFlowHandler(config_entry)
```

## Advantages Over YAML

### Before (YAML):
```yaml
# Had to manually type entity IDs
climate_entity: climate.master_bedroom_room  # Typo? No validation!
temp_sensor: sensor.master_temp  # Wrong entity? No way to know!
vent_entities:
  - cover.master_v1  # Misspelled? Breaks silently!
```

### After (UI):
- ✅ Dropdown shows all available entities
- ✅ Search to find entities quickly
- ✅ Validation ensures entities exist
- ✅ Friendly names make selection easier
- ✅ No typos possible
- ✅ Visual feedback

## Behind the Scenes

### Flow State Management

The config flow maintains state between steps:

```python
def __init__(self):
    self.data = {}      # Stores main thermostat
    self.rooms = []      # Stores rooms as they're added
```

### Validation

Each step validates input:

```python
# Validates thermostat exists
if user_input[CONF_MAIN_THERMOSTAT] not in self.hass.states.async_entity_ids("climate"):
    return self.async_show_form(
        step_id="user",
        errors={CONF_MAIN_THERMOSTAT: "invalid_thermostat"},
    )
```

### Error Handling

Errors are displayed in the form:

```python
errors={CONF_MAIN_THERMOSTAT: "invalid_thermostat"}
```

This shows an error message below the field.

## Customization

### Adding More Steps

To add more configuration steps:

```python
async def async_step_custom_step(self, user_input=None):
    if user_input is not None:
        self.data.update(user_input)
        return await self.async_step_next_step()
    
    return self.async_show_form(
        step_id="custom_step",
        data_schema=vol.Schema({...}),
    )
```

### Adding More Fields

To add fields to existing steps:

```python
schema_dict = {
    vol.Optional("new_field"): selector.EntitySelector(...),
    # ... existing fields
}
```

## Summary

The UI configuration provides:

1. **Step 1**: Select thermostat (entity selector dropdown)
2. **Step 2**: Add rooms (repeatable form with entity selectors)
3. **Step 3**: Configure settings (number inputs with defaults)
4. **Completion**: Integration loads with your configuration

**Key Benefits:**
- No YAML editing required
- Entity selectors prevent typos
- Validation ensures correctness
- Visual feedback throughout
- Easy to update via Options flow

The entire configuration is stored in Home Assistant's config entry system and can be updated anytime via the UI!

