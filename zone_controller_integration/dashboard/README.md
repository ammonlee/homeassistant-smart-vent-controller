# Smart Vent Controller Dashboard Cards

This directory contains dashboard card configurations for the Smart Vent Controller integration.

## Available Cards

### 1. `smart_vent_controller_complete_dashboard.yaml`
**Complete dashboard** - Full dashboard with all features in one file.

**Usage:**
- Copy the entire file content
- Add as a new dashboard view in Lovelace
- Or add individual cards to existing dashboard

### 2. `smart_vent_controller_overview.yaml`
**Overview card** - System status, control toggles, and quick stats.

**Features:**
- System status header
- Control toggles (vent control, thermostat control, debug mode, etc.)
- Rooms being conditioned list
- System statistics
- Quick actions

### 3. `smart_vent_controller_all_rooms.yaml`
**All rooms grid** - Grid view of all rooms with temperature, target, and delta.

**Features:**
- Color-coded status (red=needs heat, blue=needs cool, green=at target)
- Temperature, target, and delta display
- Tap to see more info

### 4. `smart_vent_controller_room_card.yaml`
**Individual room card template** - Template for creating room-specific cards.

**Usage:**
- Replace `{room}` with room key (e.g., `master`, `blue`, `gold`)
- Replace `{Room Name}` with friendly name (e.g., `Master Bedroom`)
- Copy and customize for each room

### 5. `smart_vent_controller_room_detailed.yaml`
**Detailed room card** - Comprehensive room card with all details.

**Features:**
- Temperature gauge
- Occupancy status
- Vent positions
- Room priority
- Status indicators

### 6. `smart_vent_controller_controls.yaml`
**Controls panel** - Configuration and control settings.

**Features:**
- Vent control settings
- Temperature settings
- Occupancy settings
- HVAC protection settings
- Room priorities

### 7. `smart_vent_controller_thermostat.yaml`
**Thermostat card** - Main thermostat control and status.

**Features:**
- Thermostat control widget
- Current status display
- Manual override detection
- Cycle protection status

## Installation

### Method 1: Complete Dashboard

1. Copy `smart_vent_controller_complete_dashboard.yaml`
2. In Home Assistant, go to **Settings** → **Dashboards**
3. Click **Add Dashboard** → **New Dashboard**
4. Click the three dots menu → **Edit Dashboard**
5. Click **Add Card** → **Manual**
6. Paste the YAML content
7. Save

### Method 2: Individual Cards

1. Choose cards you want to add
2. Copy the card YAML
3. In your dashboard, click **Add Card**
4. Select **Manual**
5. Paste the YAML
6. Adjust entity IDs if needed
7. Save

## Customization

### Entity IDs

The cards use these entity patterns:
- Temperature: `sensor.{room}_temp_degf`
- Target: `sensor.{room}_target_degf`
- Delta: `sensor.{room}_delta_degf`
- Occupancy: `binary_sensor.{room}_occupied_recent`
- Thermostat: `climate.main_floor_thermostat` (adjust if different)

### Room Keys

Replace `{room}` with your room keys:
- `master` → Master Bedroom
- `blue` → Blue Room
- `gold` → Gold Room
- `green` → Green Room
- `grey` → Grey Room
- `guest` → Guest Room
- `family` → Family Room
- `kitchen` → Kitchen
- `basement` → Basement
- `piano` → Piano Room

### Mushroom Cards

Some cards use `custom:mushroom-entity-card`. If you don't have Mushroom Cards installed:

1. Install via HACS: Search for "Mushroom Cards"
2. Or replace with standard `entity` cards:
   ```yaml
   type: entity
   entity: sensor.master_temp_degf
   name: Master Bedroom
   ```

### Color Coding

Cards use color coding based on delta:
- **Red**: Delta > 2°F (needs heating)
- **Orange**: Delta > 0°F (slightly cold)
- **Green**: Delta = 0°F (at target)
- **Light Blue**: Delta < 0°F (slightly warm)
- **Blue**: Delta < -2°F (needs cooling)

## Examples

### Minimal Dashboard

```yaml
type: vertical-stack
cards:
  - type: markdown
    content: |
      # Smart Vent Controller
      **Status:** {{ states('sensor.rooms_to_condition') }}
  
  - type: grid
    square: false
    columns: 3
    cards:
      - type: entity
        entity: sensor.master_temp_degf
        name: Master Bedroom
      - type: entity
        entity: sensor.blue_temp_degf
        name: Blue Room
      # ... more rooms
```

### Single Room Card

```yaml
type: vertical-stack
cards:
  - type: gauge
    entity: sensor.master_temp_degf
    name: Master Bedroom
    min: 60
    max: 80
  
  - type: entity
    entity: binary_sensor.master_occupied_recent
    name: Occupancy
```

## Troubleshooting

### Cards Not Showing

1. Check entity IDs match your configuration
2. Verify entities exist: **Developer Tools** → **States**
3. Check YAML syntax: **Developer Tools** → **Template**

### Mushroom Cards Not Working

1. Install Mushroom Cards via HACS
2. Or replace with standard `entity` cards
3. Remove `icon_color` and `secondary_info` attributes

### Colors Not Updating

1. Check delta sensor exists: `sensor.{room}_delta_degf`
2. Verify template syntax
3. Check Home Assistant logs for errors

## Support

For issues or questions:
1. Check integration logs
2. Verify entity IDs
3. Test templates in Developer Tools
4. Review Home Assistant documentation

