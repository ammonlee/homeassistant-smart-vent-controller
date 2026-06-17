# Slice B: "Visibility & Alerts" Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a per-room comfort sensor, enable the useful sensors by default, surface health via Home Assistant Repairs, and make efficiency learning inspectable (confidence) and resettable.

**Architecture:** Comfort logic is centralized as one coordinator method consumed by a thin binary sensor. Health-issue evaluation lives in a new pure-ish `health.py` module, driven once per coordinator update with in-memory debounce state, raising/clearing `issue_registry` issues. Efficiency confidence is sample counts tracked in the store, incremented on learning, displayed as sensor attributes; a new service resets learned data.

**Tech Stack:** Python 3.13, Home Assistant custom integration, `homeassistant.helpers.issue_registry`, `pytest` + `pytest-homeassistant-custom-component`.

---

## Spec

Implements `docs/superpowers/specs/2026-06-17-visibility-and-alerts-design.md`.

## Conventions for every task

- **Working directory (cwd for all commands):** the worktree root
  `/Users/ammon/Development/Home Assistant/homeassistant-smart-vent-controller/.claude/worktrees/angry-solomon-72bff5`.
- **Branch:** `claude/slice-b-visibility-alerts` (already checked out; stacked on Slice A). Commit here.
- **Python interpreter** (venv at the MAIN repo root; keep the path quoted — it has spaces):

  ```bash
  PY="/Users/ammon/Development/Home Assistant/homeassistant-smart-vent-controller/.venv/bin/python"
  ```

- **Baseline:** `"$PY" -m pytest -q` currently reports `64 passed`.
- After each task: run the new test(s) (red→green where applicable) and then the full suite — it must stay green with the new tests added.
- TDD: write the failing test first unless a step says otherwise.

## Files touched

- Modify: `custom_components/smart_vent_controller/coordinator.py` — `get_room_comfort`, `_evaluate_health`, sample increments (Tasks 1, 3, 5)
- Modify: `custom_components/smart_vent_controller/binary_sensor.py` — `RoomComfortableSensor` (Task 1)
- Modify: `custom_components/smart_vent_controller/sensor.py` — default-enable flags, efficiency confidence attrs (Tasks 2, 5)
- Create: `custom_components/smart_vent_controller/health.py` — health-issue evaluation (Task 3)
- Modify: `custom_components/smart_vent_controller/__init__.py` — health unload cleanup, `reset_efficiency` service (Tasks 3, 6)
- Modify: `custom_components/smart_vent_controller/store.py` — sample counters, reset, export/import (Task 4)
- Modify: `custom_components/smart_vent_controller/algorithm.py` — `efficiency_confidence` (Task 5)
- Modify: `custom_components/smart_vent_controller/const.py` — (none required; thresholds live in algorithm.py)
- Modify: `custom_components/smart_vent_controller/services.yaml` — `reset_efficiency` (Task 6)
- Modify: `custom_components/smart_vent_controller/strings.json` + `translations/en.json` — `issues` section (Task 3)
- Create: `tests/test_health.py` (Task 3); `tests/test_sensor.py` (Tasks 2, 5)
- Modify: `tests/test_coordinator.py` (Tasks 1, 5, 6); `tests/test_store.py` (Task 4); `tests/test_algorithm.py` (Task 5)
- Modify: `CHANGELOG.md` (Task 7)

---

### Task 1: Component A — Room "Comfortable" binary sensor

**Files:**
- Modify: `custom_components/smart_vent_controller/coordinator.py` (add `get_room_comfort`)
- Modify: `custom_components/smart_vent_controller/binary_sensor.py` (add `RoomComfortableSensor` + register it)
- Test: `tests/test_coordinator.py`

- [ ] **Step 1: Write the failing test** — append to `tests/test_coordinator.py`:

```python
async def test_get_room_comfort(hass):
    rooms = [{"name": "Den", "temp_sensor": "sensor.den",
              "climate_entity": "climate.den", "vent_entities": []}]
    entry = _make_entry(rooms)
    entry.add_to_hass(hass)
    coordinator = SmartVentControllerCoordinator(hass, entry)
    await coordinator.async_initialize()
    hass.config_entries.async_update_entry(entry, options={"room_hysteresis_f": 1.0})

    hass.states.async_set("climate.den", "heat", {"temperature": 70.0})

    # Within band: |70 - 70.5| = 0.5 <= 1.0
    hass.states.async_set("sensor.den", "70.5")
    assert coordinator.get_room_comfort(rooms[0]) is True

    # Outside band: |70 - 66| = 4 > 1.0
    hass.states.async_set("sensor.den", "66.0")
    assert coordinator.get_room_comfort(rooms[0]) is False

    # Missing current temp -> None
    hass.states.async_set("sensor.den", "unavailable")
    assert coordinator.get_room_comfort(rooms[0]) is None
```

- [ ] **Step 2: Run it and verify it fails**

```bash
"$PY" -m pytest tests/test_coordinator.py::test_get_room_comfort -q
```
Expected: FAIL with `AttributeError: 'SmartVentControllerCoordinator' object has no attribute 'get_room_comfort'`.

- [ ] **Step 3: Implement `get_room_comfort`** — in `coordinator.py`, add this method to the `SmartVentControllerCoordinator` class (put it right after `_get_room_target`, near line 362):

```python
    def get_room_comfort(self, room_config: dict) -> bool | None:
        """Return True if the room is within its comfort band, None if unknown.

        Comfortable means abs(target - current) <= room_hysteresis_f, independent
        of HVAC mode. Target resolves store setpoint first, then the room's climate
        entity (same precedence as the Target sensor).
        """
        current = self._get_room_temp(room_config)
        room_key = room_config.get("name", "").lower().replace(" ", "_")
        target = self.store.get_room_setpoint(room_key)
        if target is None:
            target = self._get_room_target(room_config)
        if current is None or target is None:
            return None
        hysteresis = self.config_entry.options.get("room_hysteresis_f", 1.0)
        return abs(float(target) - float(current)) <= hysteresis
```

- [ ] **Step 4: Run it and verify it passes**

```bash
"$PY" -m pytest tests/test_coordinator.py::test_get_room_comfort -q
```
Expected: PASS.

- [ ] **Step 5: Add the `RoomComfortableSensor`** — in `binary_sensor.py`, register it in the per-room loop of `async_setup_entry` (after the `RoomConditioningActiveSensor` append, around line 40):

```python
        entities.append(
            RoomComfortableSensor(coordinator, entry, room_key, room_name, room)
        )
```

Then add the class (place it after `RoomConditioningActiveSensor`, before `RoomOverrideActiveSensor`):

```python
class RoomComfortableSensor(BinarySensorEntity):
    """Whether a room is currently within its comfort band."""

    _attr_icon = "mdi:thermometer-check"

    def __init__(self, coordinator, entry, room_key, room_name, room_config):
        self.coordinator = coordinator
        self._entry = entry
        self._room_key = room_key
        self._room_name = room_name
        self._room_config = room_config
        self._attr_unique_id = f"{entry.entry_id}_{room_key}_comfortable"
        self._attr_name = f"{room_name} Comfortable"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={get_room_device_id(self._entry, self._room_key)},
            name=f"{self._room_name} Zone",
            manufacturer="Smart Vent Controller",
            model="Room Controller",
        )

    @property
    def is_on(self):
        return self.coordinator.get_room_comfort(self._room_config)
```

- [ ] **Step 6: Run the full suite**

```bash
"$PY" -m pytest -q
```
Expected: all pass (65 total — baseline 64 + this task's 1 new test).

- [ ] **Step 7: Commit**

```bash
git add custom_components/smart_vent_controller/coordinator.py custom_components/smart_vent_controller/binary_sensor.py tests/test_coordinator.py
git commit -m "feat: add per-room Comfortable binary sensor

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Component B — enable Delta and Efficiency sensors by default

**Files:**
- Modify: `custom_components/smart_vent_controller/sensor.py` (remove two `_attr_entity_registry_enabled_default = False` lines)
- Test: `tests/test_sensor.py` (new)

- [ ] **Step 1: Write the failing test** — create `tests/test_sensor.py`:

```python
"""Tests for sensor entity registry defaults and attributes."""
from custom_components.smart_vent_controller.sensor import (
    RoomDeltaSensor,
    RoomEfficiencySensor,
    HVACCycleStartTimeSensor,
    HVACCycleEndTimeSensor,
)


def test_delta_and_efficiency_enabled_by_default():
    assert getattr(RoomDeltaSensor, "_attr_entity_registry_enabled_default", True) is True
    assert getattr(RoomEfficiencySensor, "_attr_entity_registry_enabled_default", True) is True


def test_cycle_timestamp_sensors_disabled_by_default():
    assert getattr(HVACCycleStartTimeSensor, "_attr_entity_registry_enabled_default", True) is False
    assert getattr(HVACCycleEndTimeSensor, "_attr_entity_registry_enabled_default", True) is False
```

- [ ] **Step 2: Run it and verify it fails**

```bash
"$PY" -m pytest tests/test_sensor.py::test_delta_and_efficiency_enabled_by_default -q
```
Expected: FAIL — both classes currently set the attribute to `False`.

- [ ] **Step 3: Remove the disable flags** — in `sensor.py`:
  - In `RoomDeltaSensor` (around line 159) delete the line `_attr_entity_registry_enabled_default = False`.
  - In `RoomEfficiencySensor` (around line 223) delete the line `_attr_entity_registry_enabled_default = False`.
  - Leave the same line intact in `HVACCycleStartTimeSensor` (line 328) and `HVACCycleEndTimeSensor` (line 345).

- [ ] **Step 4: Run both tests and the full suite**

```bash
"$PY" -m pytest tests/test_sensor.py -q
"$PY" -m pytest -q
```
Expected: `tests/test_sensor.py` passes (2 tests); full suite all green (67 total — 65 + 2 new).

- [ ] **Step 5: Commit**

```bash
git add custom_components/smart_vent_controller/sensor.py tests/test_sensor.py
git commit -m "feat: enable Delta and Efficiency sensors by default

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Component C — health surfaced via HA Repairs

**Files:**
- Create: `custom_components/smart_vent_controller/health.py`
- Modify: `custom_components/smart_vent_controller/coordinator.py` (debounce state + `_evaluate_health`, call in `_async_update_data`)
- Modify: `custom_components/smart_vent_controller/__init__.py` (clear issues on unload)
- Modify: `custom_components/smart_vent_controller/strings.json` and `translations/en.json` (`issues` section)
- Test: `tests/test_health.py` (new)

- [ ] **Step 1: Write the failing test** — create `tests/test_health.py`:

```python
"""Tests for health repair-issue evaluation."""
from pytest_homeassistant_custom_component.common import MockConfigEntry
from homeassistant.helpers import issue_registry as ir

from custom_components.smart_vent_controller.const import DOMAIN
from custom_components.smart_vent_controller.health import evaluate_health_issues


def _entry(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "main_thermostat": "climate.main",
            "rooms": [{"name": "Den", "vent_entities": ["cover.den_vent"]}],
        },
        options={},
    )
    entry.add_to_hass(hass)
    return entry


async def test_no_issue_when_all_available(hass):
    entry = _entry(hass)
    hass.states.async_set("climate.main", "heat")
    hass.states.async_set("cover.den_vent", "open")
    evaluate_health_issues(hass, entry, {}, 1000.0)
    reg = ir.async_get(hass)
    assert (DOMAIN, f"vents_unavailable_{entry.entry_id}") not in reg.issues
    assert (DOMAIN, f"thermostat_unavailable_{entry.entry_id}") not in reg.issues


async def test_vent_issue_only_after_debounce(hass):
    entry = _entry(hass)
    hass.states.async_set("climate.main", "heat")
    hass.states.async_set("cover.den_vent", "unavailable")
    since = {}
    evaluate_health_issues(hass, entry, since, 1000.0)          # just went bad
    reg = ir.async_get(hass)
    key = (DOMAIN, f"vents_unavailable_{entry.entry_id}")
    assert key not in reg.issues
    evaluate_health_issues(hass, entry, since, 1000.0 + 240)    # 4 min
    assert key not in reg.issues
    evaluate_health_issues(hass, entry, since, 1000.0 + 300)    # 5 min
    assert key in reg.issues


async def test_vent_issue_clears_on_recovery(hass):
    entry = _entry(hass)
    hass.states.async_set("climate.main", "heat")
    hass.states.async_set("cover.den_vent", "unavailable")
    since = {}
    evaluate_health_issues(hass, entry, since, 1000.0)
    evaluate_health_issues(hass, entry, since, 1000.0 + 300)
    reg = ir.async_get(hass)
    key = (DOMAIN, f"vents_unavailable_{entry.entry_id}")
    assert key in reg.issues
    hass.states.async_set("cover.den_vent", "open")
    evaluate_health_issues(hass, entry, since, 1000.0 + 360)
    assert key not in reg.issues


async def test_thermostat_issue_is_error(hass):
    entry = _entry(hass)
    hass.states.async_set("climate.main", "unavailable")
    hass.states.async_set("cover.den_vent", "open")
    since = {}
    evaluate_health_issues(hass, entry, since, 1000.0)
    evaluate_health_issues(hass, entry, since, 1000.0 + 300)
    reg = ir.async_get(hass)
    issue = reg.async_get_issue(DOMAIN, f"thermostat_unavailable_{entry.entry_id}")
    assert issue is not None
    assert issue.severity == ir.IssueSeverity.ERROR
```

- [ ] **Step 2: Run it and verify it fails**

```bash
"$PY" -m pytest tests/test_health.py -q
```
Expected: FAIL at import (`No module named '...health'`).

- [ ] **Step 3: Create `health.py`**:

```python
"""Health evaluation and Home Assistant Repairs issue management."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN

HEALTH_DEBOUNCE_SEC = 300.0


def _is_unavailable(hass: HomeAssistant, entity_id: str) -> bool:
    state = hass.states.get(entity_id)
    return state is None or state.state == "unavailable"


def compute_unavailable_entities(
    hass: HomeAssistant, entry: ConfigEntry
) -> tuple[str | None, list[str]]:
    """Return (unavailable_thermostat_or_None, [unavailable_vent_ids])."""
    main = entry.data.get("main_thermostat")
    bad_thermo = main if (main and _is_unavailable(hass, main)) else None

    bad_vents: list[str] = []
    for room in entry.data.get("rooms", []):
        for vent in room.get("vent_entities", []):
            if _is_unavailable(hass, vent):
                bad_vents.append(vent)
    return bad_thermo, bad_vents


def evaluate_health_issues(
    hass: HomeAssistant,
    entry: ConfigEntry,
    unavailable_since: dict[str, float],
    now_ts: float,
    debounce_sec: float = HEALTH_DEBOUNCE_SEC,
) -> None:
    """Raise/clear Repairs issues for unavailable entities, with debounce.

    *unavailable_since* maps entity_id -> first-seen-unavailable timestamp and is
    mutated in place so debounce state persists across calls.
    """
    bad_thermo, bad_vents = compute_unavailable_entities(hass, entry)
    eid = entry.entry_id

    # -- thermostat (ERROR) --
    thermo_issue = f"thermostat_unavailable_{eid}"
    main = entry.data.get("main_thermostat")
    if bad_thermo:
        since = unavailable_since.setdefault(bad_thermo, now_ts)
        if now_ts - since >= debounce_sec:
            ir.async_create_issue(
                hass, DOMAIN, thermo_issue,
                is_fixable=False,
                severity=ir.IssueSeverity.ERROR,
                translation_key="thermostat_unavailable",
                translation_placeholders={"entity_id": bad_thermo},
            )
    else:
        if main:
            unavailable_since.pop(main, None)
        ir.async_delete_issue(hass, DOMAIN, thermo_issue)

    # -- vents (WARNING, aggregate) --
    vents_issue = f"vents_unavailable_{eid}"
    all_vents = [
        v for room in entry.data.get("rooms", [])
        for v in room.get("vent_entities", [])
    ]
    bad_set = set(bad_vents)
    for v in all_vents:
        if v in bad_set:
            unavailable_since.setdefault(v, now_ts)
        else:
            unavailable_since.pop(v, None)

    aged = sorted(
        v for v in bad_vents
        if now_ts - unavailable_since.get(v, now_ts) >= debounce_sec
    )
    if aged:
        ir.async_create_issue(
            hass, DOMAIN, vents_issue,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="vents_unavailable",
            translation_placeholders={
                "count": str(len(aged)),
                "entities": ", ".join(aged),
            },
        )
    else:
        ir.async_delete_issue(hass, DOMAIN, vents_issue)
```

- [ ] **Step 4: Run the health tests and verify they pass**

```bash
"$PY" -m pytest tests/test_health.py -q
```
Expected: PASS (4 tests).

- [ ] **Step 5: Wire health evaluation into the coordinator** — in `coordinator.py`:

  In `__init__`, after `self._is_hvac_active = False` (around line 61), add:

```python
        self._unavailable_since: dict[str, float] = {}
```

  Add this method to the class (place it near `_get_room_temp`):

```python
    def _evaluate_health(self) -> None:
        """Raise/clear Repairs issues for unavailable entities (best-effort)."""
        from .health import evaluate_health_issues
        evaluate_health_issues(
            self.hass,
            self.config_entry,
            self._unavailable_since,
            dt_util.utcnow().timestamp(),
        )
```

  In `_async_update_data`, after the `for room in self.rooms:` loop and before `return data` (around line 110), add an isolated call so health never breaks the data cycle:

```python
            try:
                self._evaluate_health()
            except Exception as health_err:  # noqa: BLE001 - never fail the cycle
                _LOGGER.debug("Health evaluation skipped: %s", health_err)

            return data
```

  (`dt_util` is already imported at the top of `coordinator.py`.)

- [ ] **Step 6: Clear issues on unload** — in `__init__.py`, at the start of `async_unload_entry` (right after the docstring, before the device-removal try block), add:

```python
    from homeassistant.helpers import issue_registry as ir
    ir.async_delete_issue(hass, DOMAIN, f"thermostat_unavailable_{entry.entry_id}")
    ir.async_delete_issue(hass, DOMAIN, f"vents_unavailable_{entry.entry_id}")
```

- [ ] **Step 7: Add issue translation strings** — in `strings.json`, add a top-level `"issues"` key (sibling of `"config"` and `"options"`). Insert it after the closing brace of the `"options"` block and before the final closing brace of the file:

```json
  ,
  "issues": {
    "thermostat_unavailable": {
      "title": "Smart Vent Controller: thermostat unavailable",
      "description": "The main thermostat `{entity_id}` has been unavailable for several minutes. Smart Vent Controller cannot read the HVAC state or adjust the setpoint until it returns."
    },
    "vents_unavailable": {
      "title": "Smart Vent Controller: vents unavailable",
      "description": "{count} vent(s) have been unavailable for several minutes: {entities}. Their positions cannot be controlled until they return."
    }
  }
```

  Apply the identical `"issues"` block to `translations/en.json` the same way (sibling of `config`/`options`).

  Verify both files are valid JSON:

```bash
"$PY" -c "import json; json.load(open('custom_components/smart_vent_controller/strings.json')); json.load(open('custom_components/smart_vent_controller/translations/en.json')); print('valid')"
```
Expected: `valid`.

- [ ] **Step 8: Run the full suite**

```bash
"$PY" -m pytest -q
```
Expected: all green (71 total — 67 + 4 new health tests).

- [ ] **Step 9: Commit**

```bash
git add custom_components/smart_vent_controller/health.py custom_components/smart_vent_controller/coordinator.py custom_components/smart_vent_controller/__init__.py custom_components/smart_vent_controller/strings.json custom_components/smart_vent_controller/translations/en.json tests/test_health.py
git commit -m "feat: surface unavailable thermostat/vents as HA Repairs issues

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Component D (store) — sample counts, reset, export/import

**Files:**
- Modify: `custom_components/smart_vent_controller/store.py`
- Test: `tests/test_store.py`

- [ ] **Step 1: Write the failing tests** — in `tests/test_store.py`, (a) UPDATE the existing `test_export_empty` to expect the new keys, and (b) append two new test classes. Replace the existing `test_export_empty` body with:

```python
    def test_export_empty(self, store):
        data = store.export_efficiency()
        assert data == {
            "heating_rates": {},
            "cooling_rates": {},
            "heating_samples": {},
            "cooling_samples": {},
            "max_running_minutes": 60.0,
        }
```

Append at the end of the file:

```python
class TestEfficiencySamples:
    def test_default_zero(self, store):
        assert store.get_heating_samples("den") == 0
        assert store.get_cooling_samples("den") == 0

    def test_increment(self, store):
        store.increment_heating_samples("den")
        store.increment_heating_samples("den")
        store.increment_cooling_samples("den")
        assert store.get_heating_samples("den") == 2
        assert store.get_cooling_samples("den") == 1

    def test_samples_roundtrip(self, store, hass):
        store.increment_heating_samples("a")
        exported = store.export_efficiency()
        store2 = SmartVentStore(hass, "other")
        store2.import_efficiency(exported)
        assert store2.get_heating_samples("a") == 1


class TestResetEfficiency:
    def test_reset_one_room(self, store):
        store.set_heating_rate("a", 0.1)
        store.increment_heating_samples("a")
        store.set_heating_rate("b", 0.2)
        store.reset_efficiency("a")
        assert store.get_heating_rate("a") == 0
        assert store.get_heating_samples("a") == 0
        assert store.get_heating_rate("b") == 0.2

    def test_reset_all(self, store):
        store.set_heating_rate("a", 0.1)
        store.set_cooling_rate("b", 0.2)
        store.increment_cooling_samples("b")
        store.reset_efficiency()
        assert store.get_heating_rate("a") == 0
        assert store.get_cooling_rate("b") == 0
        assert store.get_cooling_samples("b") == 0
```

- [ ] **Step 2: Run them and verify failure**

```bash
"$PY" -m pytest tests/test_store.py -q
```
Expected: FAIL — `test_export_empty` mismatches and the new tests hit missing methods.

- [ ] **Step 3: Implement the store changes** — in `store.py`:

  Add sample-count + reset methods (place after the efficiency-rate methods, before `get_effective_rate` is fine, but simplest: add right after `set_cooling_rate`):

```python
    # -- per-room learning sample counts ------------------------------------

    def get_heating_samples(self, room_key: str) -> int:
        return int(self._data.get("heating_samples", {}).get(room_key, 0))

    def increment_heating_samples(self, room_key: str) -> None:
        d = self._data.setdefault("heating_samples", {})
        d[room_key] = int(d.get(room_key, 0)) + 1

    def get_cooling_samples(self, room_key: str) -> int:
        return int(self._data.get("cooling_samples", {}).get(room_key, 0))

    def increment_cooling_samples(self, room_key: str) -> None:
        d = self._data.setdefault("cooling_samples", {})
        d[room_key] = int(d.get(room_key, 0)) + 1

    def reset_efficiency(self, room_key: str | None = None) -> None:
        """Clear learned rates and sample counts for one room, or all rooms."""
        keys = ("heating_rates", "cooling_rates", "heating_samples", "cooling_samples")
        if room_key is None:
            for k in keys:
                self._data[k] = {}
        else:
            for k in keys:
                self._data.get(k, {}).pop(room_key, None)
```

  Replace `export_efficiency` / `import_efficiency` with:

```python
    def export_efficiency(self) -> dict[str, Any]:
        return {
            "heating_rates": dict(self._data.get("heating_rates", {})),
            "cooling_rates": dict(self._data.get("cooling_rates", {})),
            "heating_samples": dict(self._data.get("heating_samples", {})),
            "cooling_samples": dict(self._data.get("cooling_samples", {})),
            "max_running_minutes": self.max_running_minutes,
        }

    def import_efficiency(self, payload: dict[str, Any]) -> None:
        if "heating_rates" in payload:
            self._data["heating_rates"] = dict(payload["heating_rates"])
        if "cooling_rates" in payload:
            self._data["cooling_rates"] = dict(payload["cooling_rates"])
        if "heating_samples" in payload:
            self._data["heating_samples"] = dict(payload["heating_samples"])
        if "cooling_samples" in payload:
            self._data["cooling_samples"] = dict(payload["cooling_samples"])
        if "max_running_minutes" in payload:
            self._data["max_running_minutes"] = float(payload["max_running_minutes"])
```

- [ ] **Step 4: Run the store tests and the full suite**

```bash
"$PY" -m pytest tests/test_store.py -q
"$PY" -m pytest -q
```
Expected: store tests pass; full suite green (76 total — 71 + 5 net-new store tests; `test_export_empty` was modified, not added).

- [ ] **Step 5: Commit**

```bash
git add custom_components/smart_vent_controller/store.py tests/test_store.py
git commit -m "feat: track per-room learning sample counts; add reset_efficiency to store

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Component D (coordinator + sensor) — increment samples, confidence display

**Files:**
- Modify: `custom_components/smart_vent_controller/algorithm.py` (add `efficiency_confidence`)
- Modify: `custom_components/smart_vent_controller/coordinator.py` (`_learn_efficiency` increments samples)
- Modify: `custom_components/smart_vent_controller/sensor.py` (efficiency confidence attributes)
- Test: `tests/test_algorithm.py`, `tests/test_coordinator.py`, `tests/test_sensor.py`

- [ ] **Step 1: Write the failing tests**

  In `tests/test_algorithm.py`, add the import `from custom_components.smart_vent_controller.algorithm import efficiency_confidence` (alongside the existing algorithm imports) and append:

```python
def test_efficiency_confidence_levels():
    assert efficiency_confidence(0) == "none"
    assert efficiency_confidence(1) == "low"
    assert efficiency_confidence(2) == "low"
    assert efficiency_confidence(3) == "medium"
    assert efficiency_confidence(5) == "medium"
    assert efficiency_confidence(6) == "high"
    assert efficiency_confidence(99) == "high"
```

  In `tests/test_coordinator.py`, append:

```python
async def test_learn_efficiency_increments_samples(hass):
    rooms = [{"name": "Den", "temp_sensor": "sensor.den", "vent_entities": ["cover.den"]}]
    entry = _make_entry(rooms)
    entry.add_to_hass(hass)
    coordinator = SmartVentControllerCoordinator(hass, entry)
    await coordinator.async_initialize()

    coordinator.store.set_cycle_start_temp("den", 60.0)
    coordinator.store.set_cycle_avg_aperture("den", 100.0)
    hass.states.async_set("sensor.den", "66.0")  # rose 6 F during a heating cycle

    await coordinator._learn_efficiency(30.0, "heating")

    assert coordinator.store.get_heating_samples("den") == 1
    assert coordinator.store.get_heating_rate("den") > 0
```

  In `tests/test_sensor.py`, append:

```python
async def test_efficiency_sensor_confidence_attributes(hass):
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from custom_components.smart_vent_controller.const import DOMAIN
    from custom_components.smart_vent_controller.coordinator import (
        SmartVentControllerCoordinator,
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"main_thermostat": "climate.main", "rooms": []},
        options={},
    )
    entry.add_to_hass(hass)
    coordinator = SmartVentControllerCoordinator(hass, entry)
    await coordinator.async_initialize()
    coordinator.store.set_heating_rate("den", 0.2)
    for _ in range(3):
        coordinator.store.increment_heating_samples("den")

    sensor = RoomEfficiencySensor(coordinator, entry, "den", "Den")
    attrs = sensor.extra_state_attributes
    assert attrs["heating_samples"] == 3
    assert attrs["cooling_samples"] == 0
    assert attrs["confidence"] == "medium"
```

- [ ] **Step 2: Run them and verify failure**

```bash
"$PY" -m pytest tests/test_algorithm.py::test_efficiency_confidence_levels tests/test_coordinator.py::test_learn_efficiency_increments_samples tests/test_sensor.py::test_efficiency_sensor_confidence_attributes -q
```
Expected: FAIL — `efficiency_confidence` undefined, samples not incremented, sensor attrs missing.

- [ ] **Step 3: Add `efficiency_confidence` to `algorithm.py`** — append at the end of the file:

```python
EFFICIENCY_SAMPLES_LOW = 1
EFFICIENCY_SAMPLES_MEDIUM = 3
EFFICIENCY_SAMPLES_HIGH = 6


def efficiency_confidence(samples: int) -> str:
    """Map a learning sample count to a qualitative confidence level."""
    if samples >= EFFICIENCY_SAMPLES_HIGH:
        return "high"
    if samples >= EFFICIENCY_SAMPLES_MEDIUM:
        return "medium"
    if samples >= EFFICIENCY_SAMPLES_LOW:
        return "low"
    return "none"
```

- [ ] **Step 4: Increment samples in `_learn_efficiency`** — in `coordinator.py`, replace this block (around lines 260-263):

```python
            if hvac_mode in ("cool", "cooling"):
                self.store.set_cooling_rate(room_key, blended)
            else:
                self.store.set_heating_rate(room_key, blended)
```

  with:

```python
            if hvac_mode in ("cool", "cooling"):
                self.store.set_cooling_rate(room_key, blended)
                self.store.increment_cooling_samples(room_key)
            else:
                self.store.set_heating_rate(room_key, blended)
                self.store.increment_heating_samples(room_key)
```

- [ ] **Step 5: Add confidence attributes to `RoomEfficiencySensor`** — in `sensor.py`, add the import near the top (after `from .device import get_room_device_id`):

```python
from .algorithm import efficiency_confidence
```

  Replace `RoomEfficiencySensor.extra_state_attributes` (around lines 254-263) with:

```python
    @property
    def extra_state_attributes(self):
        heat = self.coordinator.store.get_heating_rate(self._room_key)
        cool = self.coordinator.store.get_cooling_rate(self._room_key)
        heat_n = self.coordinator.store.get_heating_samples(self._room_key)
        cool_n = self.coordinator.store.get_cooling_samples(self._room_key)
        dominant_samples = cool_n if cool > heat else heat_n
        return {
            "heating_rate": round(heat, 4),
            "cooling_rate": round(cool, 4),
            "heating_samples": heat_n,
            "cooling_samples": cool_n,
            "confidence": efficiency_confidence(dominant_samples),
        }
```

- [ ] **Step 6: Run the targeted tests and the full suite**

```bash
"$PY" -m pytest tests/test_algorithm.py::test_efficiency_confidence_levels tests/test_coordinator.py::test_learn_efficiency_increments_samples tests/test_sensor.py::test_efficiency_sensor_confidence_attributes -q
"$PY" -m pytest -q
```
Expected: targeted tests pass; full suite green (79 total — 76 + 3 new).

- [ ] **Step 7: Commit**

```bash
git add custom_components/smart_vent_controller/algorithm.py custom_components/smart_vent_controller/coordinator.py custom_components/smart_vent_controller/sensor.py tests/test_algorithm.py tests/test_coordinator.py tests/test_sensor.py
git commit -m "feat: efficiency learning confidence (sample counts + level)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Component D (service) — `reset_efficiency`

**Files:**
- Modify: `custom_components/smart_vent_controller/__init__.py` (handler + registration)
- Modify: `custom_components/smart_vent_controller/services.yaml`
- Test: `tests/test_coordinator.py`

- [ ] **Step 1: Write the failing test** — append to `tests/test_coordinator.py`:

```python
async def test_reset_efficiency_service(hass):
    from custom_components.smart_vent_controller import _async_register_services

    entry = _make_entry([])
    entry.add_to_hass(hass)
    coordinator = SmartVentControllerCoordinator(hass, entry)
    await coordinator.async_initialize()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await _async_register_services(hass, entry)

    coordinator.store.set_heating_rate("den", 0.3)
    coordinator.store.increment_heating_samples("den")

    await hass.services.async_call(
        DOMAIN, "reset_efficiency", {"room": "Den"}, blocking=True
    )

    assert coordinator.store.get_heating_rate("den") == 0
    assert coordinator.store.get_heating_samples("den") == 0
```

- [ ] **Step 2: Run it and verify it fails**

```bash
"$PY" -m pytest tests/test_coordinator.py::test_reset_efficiency_service -q
```
Expected: FAIL — service `reset_efficiency` not registered (`ServiceNotFound`).

- [ ] **Step 3: Add the service handler** — in `__init__.py`, inside `_async_register_services`, add this handler next to the other handlers (after `import_efficiency`):

```python
    async def reset_efficiency(call):
        coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
        if coordinator is None:
            return
        room = call.data.get("room", "")
        room_key = room.lower().replace(" ", "_") if room else None
        coordinator.store.reset_efficiency(room_key)
        await coordinator.store.async_save()
        _LOGGER.info("Efficiency data reset for %s", room_key or "all rooms")
```

  And register it next to the other `async_register` calls:

```python
    hass.services.async_register(DOMAIN, "reset_efficiency", reset_efficiency)
```

- [ ] **Step 4: Add the service to `services.yaml`** — append:

```yaml

reset_efficiency:
  name: Reset Efficiency Data
  description: Clear learned efficiency rates and sample counts for one room or all rooms
  fields:
    room:
      name: Room
      description: Room name or key (leave blank to reset all rooms)
      required: false
      selector:
        text:
```

- [ ] **Step 5: Run the test and the full suite**

```bash
"$PY" -m pytest tests/test_coordinator.py::test_reset_efficiency_service -q
"$PY" -m pytest -q
```
Expected: test passes; full suite green (80 total — 79 + 1 new).

- [ ] **Step 6: Commit**

```bash
git add custom_components/smart_vent_controller/__init__.py custom_components/smart_vent_controller/services.yaml tests/test_coordinator.py
git commit -m "feat: add reset_efficiency service

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Document Slice B in the CHANGELOG

**Files:**
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Update the CHANGELOG** — the file currently has an `## Unreleased` section with `### Fixed` and `### Changed` (from Slice A). Add an `### Added` subsection (place it directly under `## Unreleased`, above `### Fixed`):

```markdown
### Added
- Per-room **Comfortable** binary sensor — on when the room is within its
  hysteresis band (mode-independent), unknown when temperature/target is missing.
- Learning **confidence** on the Efficiency sensor: `heating_samples` /
  `cooling_samples` counts plus a `confidence` level (none / low / medium / high).
- `reset_efficiency` service to clear learned rates and sample counts for one room
  or all rooms.
- Home Assistant **Repairs** issues when the main thermostat (error) or one or more
  vents (warning) stay unavailable for 5+ minutes; they auto-clear on recovery and
  are removed when the integration is unloaded.
```

  And append this bullet to the existing `### Changed` list:

```markdown
- The Delta and Efficiency sensors are now enabled by default. (Home Assistant only
  applies this at first registration, so it affects new installs and newly-added
  rooms; existing entities keep their current enabled/disabled state.)
```

- [ ] **Step 2: Verify the suite is still green**

```bash
"$PY" -m pytest -q
```
Expected: `80 passed` (no test changes in this task).

- [ ] **Step 3: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs: changelog for Slice B visibility & alerts

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Final verification

- [ ] Full suite from the worktree root: `"$PY" -m pytest -q` → `80 passed`.
- [ ] `git log --oneline main..HEAD` shows the spec commit plus seven task commits.
- [ ] JSON validity: `"$PY" -c "import json; json.load(open('custom_components/smart_vent_controller/strings.json')); json.load(open('custom_components/smart_vent_controller/translations/en.json')); print('ok')"`.
- [ ] Optional manual check in a running HA: unplug a vent for >5 min → a Repair appears under Settings → System → Repairs; plug back in → it clears.
