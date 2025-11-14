# Project Name Options

## Current Name: "Smart Vent Controller"

**Pros:**
- Short and simple
- Clearly indicates zone control functionality
- Generic enough for various HVAC systems

**Cons:**
- Generic (could be confused with other zone controllers)
- Doesn't emphasize the smart/intelligent features
- Doesn't highlight vent control specifically

## Alternative Name Suggestions

### 1. **Smart Vent Controller** ⭐
- **Pros:** Emphasizes intelligence, clearly about vents
- **Cons:** Doesn't mention thermostat control
- **Domain:** `smart_vent_controller`

### 2. **Multi-Room Comfort Controller**
- **Pros:** Emphasizes multi-room, comfort-focused
- **Cons:** Longer name, "comfort" is vague
- **Domain:** `multi_room_comfort_controller`

### 3. **Intelligent Vent Smart Vent Controller**
- **Pros:** Emphasizes intelligence, mentions vents and zones
- **Cons:** Longer name
- **Domain:** `intelligent_vent_smart_vent_controller`

### 4. **Room Comfort Manager**
- **Pros:** Simple, emphasizes room-level control
- **Cons:** Doesn't mention HVAC/vent specifics
- **Domain:** `room_comfort_manager`

### 5. **Smart Zone HVAC**
- **Pros:** Short, emphasizes intelligence and HVAC
- **Cons:** Less descriptive about vents
- **Domain:** `smart_zone_hvac`

### 6. **Vent Zone Manager**
- **Pros:** Clear about vents and zones
- **Cons:** Doesn't emphasize intelligence
- **Domain:** `vent_zone_manager`

### 7. **Multi-Zone Vent Controller**
- **Pros:** Clear about multi-zone and vents
- **Cons:** Doesn't mention thermostat control
- **Domain:** `multi_zone_vent_controller`

### 8. **Comfort Smart Vent Controller**
- **Pros:** Emphasizes comfort, keeps "zone controller"
- **Cons:** Similar to current name
- **Domain:** `comfort_smart_vent_controller`

### 9. **Room Vent Controller**
- **Pros:** Simple, clear about room-level vent control
- **Cons:** Doesn't mention thermostat or intelligence
- **Domain:** `room_vent_controller`

### 10. **Smart Room Climate**
- **Pros:** Emphasizes intelligence and climate control
- **Cons:** Less specific about vents
- **Domain:** `smart_room_climate`

## Top Recommendations

### 🥇 **Smart Vent Controller** (Recommended)
- **Why:** Clear, emphasizes intelligence, focuses on vent control (the unique feature)
- **Domain:** `smart_vent_controller`
- **Display Name:** "Smart Vent Controller"

### 🥈 **Multi-Room Comfort Controller**
- **Why:** Emphasizes multi-room capability and comfort focus
- **Domain:** `multi_room_comfort_controller`
- **Display Name:** "Multi-Room Comfort Controller"

### 🥉 **Intelligent Vent Smart Vent Controller**
- **Why:** Comprehensive - mentions intelligence, vents, and zones
- **Domain:** `intelligent_vent_smart_vent_controller`
- **Display Name:** "Intelligent Vent Smart Vent Controller"

## Considerations

### What Makes This Integration Unique?
1. **Intelligent vent control** with ≤1/3 closed rule
2. **Multi-room focus** (not just single room)
3. **Occupancy-aware** conditioning
4. **Temperature/occupancy-aware relief** vent selection
5. **Thermostat automation** with cycle protection

### Target Audience
- Home Assistant users with Flair vents (or similar)
- Users wanting intelligent multi-room HVAC control
- Users wanting occupancy-aware conditioning

### SEO/Discoverability
- "Smart Vent" - people search for this
- "Multi-Room" - common search term
- "Smart Vent Controller" - HVAC term, but generic

## Recommendation

**"Smart Vent Controller"** is the best choice because:
1. ✅ Emphasizes the unique intelligent features
2. ✅ Clearly indicates vent control (the main differentiator)
3. ✅ Short and memorable
4. ✅ Good for SEO/discoverability
5. ✅ Professional sounding

**Alternative if you want to emphasize multi-room:**
**"Multi-Room Vent Controller"**

## Renaming Process

If you decide to rename, here's what needs to change:

1. **Domain name** (in `manifest.json` and all Python files)
2. **Display name** (in `manifest.json` and `strings.json`)
3. **All imports** (`from .const import DOMAIN`)
4. **All entity IDs** (`smart_vent_controller.*` → `new_name.*`)
5. **Documentation** (all `.md` files)
6. **Service names** (`smart_vent_controller.set_multi_room_vents` → `new_name.set_multi_room_vents`)

This is a significant refactor but doable. I can help with the renaming if you choose a new name.

