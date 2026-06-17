# Smart Vent Controller — Slice A: "Make Features Honest"

**Date:** 2026-06-17
**Status:** Approved (design)
**Baseline branch:** `claude/angry-solomon-72bff5` (off `main` @ `7c7df55`)

## Roadmap context

This is **Slice A** of a five-slice feature-improvement effort (audience: the
maintainer's own setup; broad-adoption polish deprioritized). The slices, in the
agreed incremental order:

- **A. Make features honest** *(this spec)* — fix features that don't behave as
  documented. Foundation; lowest risk.
- **B. Visibility & alerts** — "room satisfied" sensor, sensible default-enabled
  sensors, System Health surfaced via HA repairs/notifications, efficiency UX.
- **C. Comfort modes** — `preset_modes` (eco/comfort/sleep/away) on room climates
  plus a global away/vacation setback.
- **D. Quick controls & UX** — per-room boost button + manual-mode switch, starter
  dashboard, tiering the 30+ tuning knobs.
- **E. Scheduling** — time-of-day setback (build vs. lean on HA's native scheduler).

Each slice ships as its own spec → plan → PR. This spec covers **only Slice A**.

## Goal

Make two documented, user-facing features actually behave as their
documentation/UI claims, and fix one latent "feature silently does nothing"
edge case. No new UX surface is added in this slice.

## Current-State Findings (evidence)

1. **`override_room` is a no-op for conditioning.** `services.yaml` and the README
   describe it as "Temporarily exclude a room from conditioning." The service
   stores the override and surfaces it on the `{Room} Override Active` binary
   sensor — but **nothing in the selection or control path reads it**:
   - `coordinator.is_room_overridden()` is consumed only by
     `binary_sensor.py:146` (display).
   - `coordinator.get_rooms_to_condition_value()` (`coordinator.py:294-340`) never
     checks it, so an overridden room is still selected, still has its setpoint
     fed to the main thermostat, and still has its vents driven.
   - As a side effect, the `{Room} Conditioning Active` binary sensor (which reads
     the same conditioning list) also reports the wrong state for an overridden
     room.

2. **Blocking file I/O on the event loop.** The `export_efficiency` /
   `import_efficiency` service handlers (`__init__.py:111-140`) call `open()` plus
   `json.dump` / `json.load` directly inside the async handler, which can stall
   the Home Assistant event loop on slow storage. HA convention is to run blocking
   file work in an executor.

3. **Real temperatures silently discarded.** Current-temperature reads are
   rejected outside a 40–100 °F band:
   - `coordinator.py:319` — `if current_temp is None or current_temp < 40 or
     current_temp > 100: continue` skips the room from conditioning selection.
   - `scripts.py` `_collect_rooms_data` — `safe_float(v, min_val=40.0,
     max_val=100.0)` returns its default (`0.0`) for out-of-band values, which the
     `or None` then turns into `None`.

   `safe_float` **rejects** (returns default), it does not clamp. Net effect: a
   genuinely cold room (e.g. a 38 °F garage during a cold snap) is treated as
   no-data and is never selected for heating — the feature silently does nothing
   for the one case where it matters most.

## Scope & Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Override semantics | **"Just stop targeting it"** | Smallest correct change; vent behaves like any non-selected room (min-open %, still relief-eligible). Chosen over "shut off" / "make relief vent." |
| Override implementation | Single guard in `get_rooms_to_condition_value()` | One canonical selection path; fixes the conditioning sensor for free; no vent-math or store-API changes. |
| Temp band (Change 3) | Widen **current-temp** plausibility to **32–110 °F** | Stops discarding real extremes; still rejects garbage (0 / 999). User **setpoint** clamps stay at 40–100 °F (those are comfort targets, not sensor noise). |
| I/O fix | `hass.async_add_executor_job` for file work only | Pure in-memory `store.export_efficiency()` / `import_efficiency()` stay on the loop. |

## Plan

### Change 1 — Override actually excludes a room

In `coordinator.get_rooms_to_condition_value()`, inside the per-room loop (after
`room_key` is computed, `coordinator.py:317`), skip overridden rooms:

```python
if self.is_room_overridden(room_key):
    continue
```

Consequences (no other code changes needed):

- The overridden room is absent from the returned CSV.
- `ThermostatControlScript._gather_room_targets` only iterates `selected_keys`, so
  the room's setpoint no longer influences the main thermostat.
- `VentControlScript` treats it as a non-selected room → vent driven to
  `min_other_room_open_pct`, and it remains eligible as a relief vent (matches the
  chosen "just stop targeting it" semantics).
- `{Room} Conditioning Active` reads the same list → now reports `off` correctly.

Note: `is_room_overridden()` lazily clears an expired override in memory and
returns `False`; the clear is persisted on the next `store.async_save()`. This is
acceptable — an unexpired override is never lost, and an expired one re-clears
harmlessly on the next read after a restart.

### Change 2 — Non-blocking efficiency I/O

In the `export_efficiency` / `import_efficiency` handlers (`__init__.py`), wrap the
file operations in an executor job, leaving the in-memory store calls on the loop.
Shape:

```python
# export
data = coordinator.store.export_efficiency()          # in-memory, stays on loop
if path:
    def _write():
        with open(full, "w") as f:
            json.dump(data, f, indent=2)
    await hass.async_add_executor_job(_write)

# import
if path:
    def _read():
        with open(full) as f:
            return json.load(f)
    payload = await hass.async_add_executor_job(_read)
if payload:
    coordinator.store.import_efficiency(payload)        # in-memory, stays on loop
    await coordinator.store.async_save()
```

Behavior (what data is exported/imported, log messages) is unchanged.

### Change 3 — Widen current-temperature plausibility band

Widen the **current-temperature** acceptance band from 40–100 °F to **32–110 °F**
in exactly the two current-temp read sites; do **not** touch user-setpoint clamps.

- `coordinator.py:319` — change `current_temp < 40 or current_temp > 100` to
  `current_temp < 32 or current_temp > 110`.
- `scripts.py` `_collect_rooms_data` — the two current-temperature reads
  (temp-sensor read and climate-entity fallback) change `min_val=40.0,
  max_val=100.0` to `min_val=32.0, max_val=110.0`.

Leave unchanged: the target/setpoint `safe_float(..., 40.0, 100.0)` calls in
`_collect_rooms_data` and `_gather_room_targets` — these are comfort targets, not
sensor plausibility checks.

## Testing

Extend `tests/test_coordinator.py` (real HA harness already in place):

1. `test_overridden_room_excluded_from_conditioning` — mirror the existing
   `test_rooms_to_condition_selects_rooms_below_target_in_heat` setup, then
   `coordinator.set_room_override(room_key, enabled=True, duration_min=60)` and
   assert the room is **absent** from `get_rooms_to_condition_value()`; advance time
   past expiry and assert it **returns**.
2. `test_cold_room_below_old_band_is_conditioned` — room at 38 °F in heat mode with
   a higher setpoint is selected for conditioning (would have been dropped under
   the old 40 °F floor).

Efficiency export/import round-trip remains covered by the pure
`store.export_efficiency()` / `import_efficiency()` paths; the executor wrapping is
mechanical and changes no data.

## Non-Goals (deferred to later slices)

- "Full manual mode" that also freezes an overridden room's vents (Slice D).
- Making overridden rooms *preferred* relief vents (the "make it relief" option was
  rejected in favor of minimal semantics).
- Celsius / metric handling (deprioritized — maintainer's setup is °F).
- Any new entities, services, presets, schedules, or dashboards.

## Success Criteria

- An overridden room is excluded from `get_rooms_to_condition_value()`, is not
  targeted by the main thermostat, and reports `{Room} Conditioning Active = off`;
  the override still expires after its duration.
- `export_efficiency` / `import_efficiency` perform no blocking file I/O on the
  event loop; exported/imported data is unchanged.
- A current temperature of 32–110 °F is accepted; a 38 °F room in heat mode is
  selected for conditioning. Garbage (0, 999) is still rejected. User setpoint
  clamps are unchanged.
- New tests pass and CI (HACS validate, hassfest, pytest) stays green.

## Risks & Mitigations

- **Override now changes real behavior.** Users who relied on the (broken) no-op
  may see overridden rooms stop being conditioned — which is the documented,
  expected behavior. Mitigation: this is a correctness fix; note it in release
  notes / `UPGRADE_NOTES.md`.
- **Wider temp band admits a previously-rejected reading.** A 32–110 °F value now
  flows into selection and the algorithm. Mitigation: band still rejects clearly
  invalid values; algorithm already guards against `None`/zero rates.
