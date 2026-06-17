# Slice A: "Make Features Honest" Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `override_room` actually exclude a room from conditioning, widen the current-temperature plausibility band so genuinely cold/hot rooms aren't silently dropped, and move efficiency export/import file I/O off the event loop.

**Architecture:** Three small, independent edits to existing modules plus characterization/behavioral tests. No new files in the integration, no new entities/services, no public-API changes. The override fix is a single guard in the one canonical conditioning-selection method; the temp-band fix is a numeric-bound change at the current-temperature read sites; the I/O fix wraps blocking file calls in `hass.async_add_executor_job`.

**Tech Stack:** Python 3.13, Home Assistant custom integration, `pytest` + `pytest-homeassistant-custom-component` (real HA harness), `freezegun`.

---

## Spec

Implements `docs/superpowers/specs/2026-06-17-make-features-honest-design.md`.

## Conventions for every task

- **Working directory:** the worktree root
  `/Users/ammon/Development/Home Assistant/homeassistant-smart-vent-controller/.claude/worktrees/angry-solomon-72bff5`.
  Run all commands from there so `pythonpath = ["."]` imports the worktree's copy of the integration.
- **Python interpreter:** the venv lives at the **main repo root** (not the worktree):
  `/Users/ammon/Development/Home Assistant/homeassistant-smart-vent-controller/.venv/bin/python`.
  For brevity below this is written as `$PY`. Set it once per shell:

  ```bash
  PY="/Users/ammon/Development/Home Assistant/homeassistant-smart-vent-controller/.venv/bin/python"
  ```

- **Baseline:** `"$PY" -m pytest -q` currently reports `61 passed`. After this plan it should report `64 passed`.

## Files touched by this plan

- Modify: `custom_components/smart_vent_controller/coordinator.py` — override guard + temp band (Tasks 1 & 2)
- Modify: `custom_components/smart_vent_controller/scripts.py` — temp band, two current-temp reads (Task 2)
- Modify: `custom_components/smart_vent_controller/__init__.py` — executor-wrapped efficiency I/O (Task 3)
- Modify: `tests/test_coordinator.py` — three new tests (Tasks 1, 2, 3)
- Create: `CHANGELOG.md` — behavior-change note (Task 4)

---

### Task 1: Override actually excludes a room from conditioning

**Files:**
- Test: `tests/test_coordinator.py`
- Modify: `custom_components/smart_vent_controller/coordinator.py` (inside `get_rooms_to_condition_value`, around line 316-319)

- [ ] **Step 1: Write the failing test**

Append this test to `tests/test_coordinator.py` (the imports `pytest`, `DOMAIN`, `SmartVentControllerCoordinator`, and the `_make_entry` helper already exist at the top of that file):

```python
async def test_overridden_room_excluded_from_conditioning(hass):
    rooms = [
        {"name": "Cold Room", "temp_sensor": "sensor.cold",
         "climate_entity": "climate.cold", "vent_entities": []},
    ]
    entry = _make_entry(rooms)
    entry.add_to_hass(hass)
    coordinator = SmartVentControllerCoordinator(hass, entry)
    await coordinator.async_initialize()

    hass.states.async_set("climate.main", "heat")
    hass.states.async_set("sensor.cold", "66.0")
    hass.states.async_set("climate.cold", "heat", {"temperature": 72.0})

    hass.config_entries.async_update_entry(
        entry, options={"require_occupancy": False, "room_hysteresis_f": 1.0}
    )

    # Baseline: the cold room is selected for conditioning.
    assert "cold_room" in coordinator.get_rooms_to_condition_value().split(",")

    # Override excludes it.
    coordinator.set_room_override("cold_room", enabled=True, duration_min=60)
    assert "cold_room" not in coordinator.get_rooms_to_condition_value().split(",")

    # Clearing the override restores it.
    coordinator.set_room_override("cold_room", enabled=False)
    assert "cold_room" in coordinator.get_rooms_to_condition_value().split(",")
```

This test exercises the guard in both directions (set and clear). Time-based
expiry of an override is already covered by the existing
`test_override_expires_after_duration`, so it is not duplicated here.

- [ ] **Step 2: Run the test and verify it fails**

```bash
"$PY" -m pytest tests/test_coordinator.py::test_overridden_room_excluded_from_conditioning -q
```

Expected: FAIL on the second assertion — the overridden room is still returned because `get_rooms_to_condition_value` does not consult the override.

- [ ] **Step 3: Add the override guard**

In `custom_components/smart_vent_controller/coordinator.py`, find the loop in `get_rooms_to_condition_value` (around line 316):

```python
        for room in rooms:
            room_key = room.get("name", "").lower().replace(" ", "_")
            current_temp = self._get_room_temp(room)
```

Insert the override guard immediately after `room_key` is computed:

```python
        for room in rooms:
            room_key = room.get("name", "").lower().replace(" ", "_")
            if self.is_room_overridden(room_key):
                continue
            current_temp = self._get_room_temp(room)
```

- [ ] **Step 4: Run the test and verify it passes**

```bash
"$PY" -m pytest tests/test_coordinator.py::test_overridden_room_excluded_from_conditioning -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_coordinator.py custom_components/smart_vent_controller/coordinator.py
git commit -m "fix: override_room now excludes a room from conditioning

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Widen the current-temperature plausibility band to 32–110 °F

**Files:**
- Test: `tests/test_coordinator.py`
- Modify: `custom_components/smart_vent_controller/coordinator.py` (the band check in `get_rooms_to_condition_value`, around line 319)
- Modify: `custom_components/smart_vent_controller/scripts.py` (the two current-temperature reads in `_collect_rooms_data`, around lines 307 and 311)

- [ ] **Step 1: Write the failing test**

Append this test to `tests/test_coordinator.py`:

```python
async def test_cold_room_below_old_band_is_conditioned(hass):
    rooms = [
        {"name": "Garage", "temp_sensor": "sensor.garage",
         "climate_entity": "climate.garage", "vent_entities": []},
    ]
    entry = _make_entry(rooms)
    entry.add_to_hass(hass)
    coordinator = SmartVentControllerCoordinator(hass, entry)
    await coordinator.async_initialize()

    hass.states.async_set("climate.main", "heat")
    hass.states.async_set("sensor.garage", "38.0")  # below the old 40 °F floor
    hass.states.async_set("climate.garage", "heat", {"temperature": 60.0})

    hass.config_entries.async_update_entry(
        entry, options={"require_occupancy": False, "room_hysteresis_f": 1.0}
    )

    assert "garage" in coordinator.get_rooms_to_condition_value().split(",")
```

- [ ] **Step 2: Run the test and verify it fails**

```bash
"$PY" -m pytest tests/test_coordinator.py::test_cold_room_below_old_band_is_conditioned -q
```

Expected: FAIL — at 38 °F the room hits `current_temp < 40` and is skipped, so `"garage"` is absent from the result.

- [ ] **Step 3: Widen the band in the coordinator**

In `custom_components/smart_vent_controller/coordinator.py`, in `get_rooms_to_condition_value` (around line 319), change:

```python
            if current_temp is None or current_temp < 40 or current_temp > 100:
                continue
```

to:

```python
            if current_temp is None or current_temp < 32 or current_temp > 110:
                continue
```

- [ ] **Step 4: Widen the band in scripts.py (consistency)**

In `custom_components/smart_vent_controller/scripts.py`, in `_collect_rooms_data`, update **only the two current-temperature reads** (around lines 307 and 311). Change:

```python
            current = None
            if temp_sensor and validate_entity_state(self.hass, temp_sensor, "sensor"):
                v = get_safe_state(self.hass, temp_sensor)
                if v:
                    current = safe_float(v, min_val=40.0, max_val=100.0) or None
            if current is None and climate and validate_entity_state(self.hass, climate, "climate"):
                t = get_safe_attribute(self.hass, climate, "current_temperature")
                if t is not None:
                    current = safe_float(t, min_val=40.0, max_val=100.0) or None
```

to:

```python
            current = None
            if temp_sensor and validate_entity_state(self.hass, temp_sensor, "sensor"):
                v = get_safe_state(self.hass, temp_sensor)
                if v:
                    current = safe_float(v, min_val=32.0, max_val=110.0) or None
            if current is None and climate and validate_entity_state(self.hass, climate, "climate"):
                t = get_safe_attribute(self.hass, climate, "current_temperature")
                if t is not None:
                    current = safe_float(t, min_val=32.0, max_val=110.0) or None
```

**Do NOT change** the target/setpoint `safe_float(..., 40.0, 100.0)` calls elsewhere in `_collect_rooms_data` or in `_gather_room_targets` — those are comfort-target clamps, not sensor-plausibility checks, and stay at 40–100.

- [ ] **Step 5: Run the new test and the full suite**

```bash
"$PY" -m pytest tests/test_coordinator.py::test_cold_room_below_old_band_is_conditioned -q
"$PY" -m pytest -q
```

Expected: the targeted test PASSES; the full suite reports `63 passed` (61 baseline + Task 1 + Task 2).

- [ ] **Step 6: Commit**

```bash
git add tests/test_coordinator.py custom_components/smart_vent_controller/coordinator.py custom_components/smart_vent_controller/scripts.py
git commit -m "fix: widen current-temp plausibility band to 32-110F

Stops silently discarding genuinely cold/hot room readings (e.g. a 38F
garage in a cold snap) so they can still be selected for conditioning.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Move efficiency export/import file I/O off the event loop

This task is a behavior-preserving refactor, so it uses a **characterization test**
(written first, expected to pass before and after) rather than a red-first test.
The test exercises the exact handlers being changed by registering the services
against a minimal coordinator and round-tripping data through a file.

**Files:**
- Test: `tests/test_coordinator.py`
- Modify: `custom_components/smart_vent_controller/__init__.py` (`export_efficiency` / `import_efficiency` handlers, around lines 111-140)

- [ ] **Step 1: Write the characterization test**

Append this test to `tests/test_coordinator.py`:

```python
async def test_efficiency_export_import_roundtrip_via_services(hass):
    from custom_components.smart_vent_controller import _async_register_services

    entry = _make_entry([])
    entry.add_to_hass(hass)
    coordinator = SmartVentControllerCoordinator(hass, entry)
    await coordinator.async_initialize()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await _async_register_services(hass, entry)

    coordinator.store.set_heating_rate("office", 0.0123)

    await hass.services.async_call(
        DOMAIN, "export_efficiency", {"path": "sv_eff_test.json"}, blocking=True
    )

    # Corrupt the in-memory value; importing from disk must restore it.
    coordinator.store.set_heating_rate("office", 0.0)
    await hass.services.async_call(
        DOMAIN, "import_efficiency", {"path": "sv_eff_test.json"}, blocking=True
    )

    assert coordinator.store.get_heating_rate("office") == pytest.approx(0.0123)
```

- [ ] **Step 2: Run the test**

```bash
"$PY" -m pytest tests/test_coordinator.py::test_efficiency_export_import_roundtrip_via_services -q
```

Expected: PASS (it characterizes the current round-trip behavior). If instead it
errors with a blocking-call detection from the HA test harness, that is HA flagging
the very `open()`-in-the-event-loop bug this task fixes — proceed to Step 3 either
way.

- [ ] **Step 3: Wrap the file I/O in an executor job**

In `custom_components/smart_vent_controller/__init__.py`, replace the
`export_efficiency` and `import_efficiency` handlers (around lines 111-140) with:

```python
    async def export_efficiency(call):
        coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
        if coordinator is None:
            return
        data = coordinator.store.export_efficiency()
        path = call.data.get("path", "")
        if path:
            full = hass.config.path(path)

            def _write():
                with open(full, "w") as f:
                    json.dump(data, f, indent=2)

            await hass.async_add_executor_job(_write)
            _LOGGER.info("Efficiency data exported to %s", full)
        else:
            _LOGGER.info("Efficiency data: %s", json.dumps(data))

    async def import_efficiency(call):
        coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
        if coordinator is None:
            return
        payload = call.data.get("payload")
        path = call.data.get("path", "")
        if path:
            full = hass.config.path(path)

            def _read():
                with open(full) as f:
                    return json.load(f)

            payload = await hass.async_add_executor_job(_read)
        if payload:
            coordinator.store.import_efficiency(payload)
            await coordinator.store.async_save()
            _LOGGER.info("Efficiency data imported")
```

Notes:
- `hass.config.path(path)` replaces the manual `f"{config_dir}/{path}"` join (same result, cleaner).
- The in-memory `store.export_efficiency()` / `import_efficiency()` calls stay on the loop — only the blocking file work moves to the executor.

- [ ] **Step 4: Run the test and the full suite**

```bash
"$PY" -m pytest tests/test_coordinator.py::test_efficiency_export_import_roundtrip_via_services -q
"$PY" -m pytest -q
```

Expected: the targeted test PASSES; the full suite reports `64 passed`.

- [ ] **Step 5: Commit**

```bash
git add tests/test_coordinator.py custom_components/smart_vent_controller/__init__.py
git commit -m "perf: move efficiency export/import file I/O off the event loop

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Record the behavior change in a CHANGELOG

The override fix changes observable behavior (overridden rooms now actually stop
being conditioned), so record it. There is no existing changelog; create one.

**Files:**
- Create: `CHANGELOG.md`

- [ ] **Step 1: Create `CHANGELOG.md`**

```markdown
# Changelog

## Unreleased

### Fixed
- **`override_room` now actually excludes a room from conditioning.** Previously
  the service stored the override and updated the `{Room} Override Active` sensor
  but had no effect on control — overridden rooms were still targeted by the
  thermostat and still had their vents driven. They are now excluded from
  conditioning selection (and `{Room} Conditioning Active` reports correctly).
  If you relied on the old no-op behavior, overridden rooms will now stop being
  conditioned as documented.
- **Genuinely cold/hot room readings are no longer silently discarded.** The
  current-temperature plausibility band widened from 40–100 °F to 32–110 °F, so a
  room reading (for example) 38 °F during a cold snap can still be selected for
  heating. User-chosen setpoint limits are unchanged.

### Changed
- Efficiency `export_efficiency` / `import_efficiency` services now perform file
  I/O in an executor instead of on the event loop.
```

- [ ] **Step 2: Verify the full suite is still green**

```bash
"$PY" -m pytest -q
```

Expected: `64 passed` (no test changes in this task).

- [ ] **Step 3: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs: add CHANGELOG noting Slice A behavior changes

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Final verification

- [ ] Run the full suite from the worktree root: `"$PY" -m pytest -q` → `64 passed`.
- [ ] `git log --oneline -4` shows the four commits (override fix, temp band, I/O, changelog).
- [ ] Manual spot check (optional, in a running HA): call `smart_vent_controller.override_room` for an actively-conditioned room and confirm it drops out of the `Rooms To Condition` sensor and its `{Room} Conditioning Active` flips off.
