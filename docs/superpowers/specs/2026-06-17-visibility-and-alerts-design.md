# Smart Vent Controller — Slice B: "Visibility & Alerts"

**Date:** 2026-06-17
**Status:** Approved (design)
**Baseline branch:** `claude/slice-b-visibility-alerts`, stacked on Slice A (`e052794`).
Slice A is in review as PR #2; this slice is a separate branch/PR built on top of it.

## Roadmap context

Slice **B** of the five-slice feature-improvement effort (audience: maintainer's
own setup). Order: A (make features honest — done, PR #2) → **B (visibility &
alerts — this spec)** → C (comfort modes) → D (quick controls & UX) → E
(scheduling). Each slice ships as its own spec → plan → PR.

## Goal

Make the integration's state and health legible and proactive: a per-room comfort
indicator, useful sensors visible by default, actionable health alerts via Home
Assistant's Repairs UI, and inspectable/manageable efficiency learning.

## Current-State Findings (evidence)

1. **No at-a-glance per-room comfort signal.** `{Room} Conditioning Active`
   (`binary_sensor.py:92`) tells you the room is *selected for conditioning*
   (directional, mode/occupancy/override-gated) — not whether it is actually
   *comfortable*. The `{Room} Delta` sensor that would show this is disabled by
   default (see #2).
2. **The most useful sensors are hidden.** `RoomDeltaSensor` and
   `RoomEfficiencySensor` set `_attr_entity_registry_enabled_default = False`
   (`sensor.py:159`, `sensor.py:223`), so a fresh install shows neither without the
   user hunting through disabled entities.
3. **Health is passive.** `SystemHealthSensor` (`sensor.py:391`) computes
   `healthy` / `degraded` / `error` (missing thermostat, unavailable vents) but
   nothing surfaces it — the user must build their own automation to notice. There
   is no use of `homeassistant.helpers.issue_registry` anywhere in the codebase.
4. **Efficiency learning is opaque.** Learned rates are exposed (when enabled) but
   there is no indication of how many samples back them (confidence) and no way to
   reset a bad learned rate short of the JSON import/export round-trip.

## Scope & Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Components | A (comfort sensor) + B (default sensors) + C (health→repairs) + D (efficiency UX) | User selected all four; each is an independent, separately-committable unit. |
| "Comfortable" meaning | `abs(target − current) <= room_hysteresis_f`, mode-independent; `None` if temp/target missing | Pure "is this room comfortable now"; works even when the system is idle. |
| Comfort logic location | One public coordinator method `get_room_comfort(room_config)` | DRY + unit-testable; the sensor is a thin view. |
| Default-enabled | Enable `Delta` + `Efficiency`; keep cycle-timestamp sensors disabled | Delta/Efficiency are the genuinely useful ones; timestamps are diagnostic. |
| Repair debounce | Fixed 5 minutes, no new config knob | Robust to restart/blip flapping without growing the options list. |
| Repair severity | thermostat → ERROR; vents → WARNING (aggregate) | Missing thermostat is fatal; a vent or two is degraded. |
| Repair multi-entry | issue ids suffixed with `entry_id` | The integration supports multiple config entries. |
| Confidence | `heating_samples` / `cooling_samples` counts + derived `confidence` level | Inspectable for power users, glanceable for everyone. |
| Reset scope | `reset_efficiency` with optional `room` (default all); clears rates **and** samples | Simple, matches the existing service style. |

## Plan (by component — each an independent commit)

### A. Room "Comfortable" binary sensor

- **Coordinator:** add public `get_room_comfort(room_config: dict) -> bool | None`:
  read current via existing `_get_room_temp(room_config)`, target via existing
  `_get_room_target(room_config)`, hysteresis from
  `options.get("room_hysteresis_f", 1.0)`; return `None` if current or target is
  `None`, else `abs(target - current) <= hysteresis`.
- **binary_sensor.py:** new `RoomComfortableSensor`, one per room (always created).
  `is_on` returns `coordinator.get_room_comfort(<room_config>)`; the sensor is
  constructed with the room's config dict so it can call the coordinator method.
  Name `{Room} Comfortable`, icon `mdi:thermometer-check`, no `device_class`,
  enabled by default. Standard room `device_info` like the sibling sensors.

### B. Better default-enabled sensors

- Remove `_attr_entity_registry_enabled_default = False` from `RoomDeltaSensor`
  (`sensor.py:159`) and `RoomEfficiencySensor` (`sensor.py:223`). Leave it on
  `HVACCycleStartTimeSensor` / `HVACCycleEndTimeSensor`.
- **Documented caveat:** HA applies `enabled_default` only at first registration,
  so this affects new installs and newly-added rooms; pre-existing entities keep
  their current enabled/disabled state. Noted in the CHANGELOG.

### C. Health → HA Repairs

- **New `health.py`:**
  - `compute_unavailable_entities(hass, entry) -> tuple[str | None, list[str]]` —
    returns `(unavailable_thermostat_or_None, [unavailable_vent_ids])`. "Unavailable"
    = state is `None` or `unavailable`.
  - `evaluate_health_issues(hass, entry, unavailable_since: dict[str, float], now_ts: float)`
    — given the debounce-tracking dict (entity_id → first-seen-unavailable ts),
    raise/clear issues via `homeassistant.helpers.issue_registry` (`ir`):
    - For the thermostat: if unavailable and `now - since >= 300`, `ir.async_create_issue(..., translation_key="thermostat_unavailable", severity=ERROR, is_fixable=False, translation_placeholders={"entity_id": ...})` with issue id `f"thermostat_unavailable_{entry.entry_id}"`; when available, `ir.async_delete_issue(...)` and drop from the dict.
    - For vents: aggregate issue id `f"vents_unavailable_{entry.entry_id}"`,
      `severity=WARNING`, raised when any vent has been unavailable `>= 300s`,
      placeholders `{"count": n, "entities": "a, b"}`; cleared when none are
      unavailable.
  - The function mutates `unavailable_since` (adds newly-unavailable entities with
    `now_ts`, removes recovered ones) so debounce state persists across cycles.
- **Coordinator:** hold `self._unavailable_since: dict[str, float] = {}` (in-memory;
  resets on restart — acceptable). At the end of `_async_update_data`, call a small
  `self._evaluate_health()` wrapper inside its own `try/except` so health
  evaluation can never blank room data.
- **Unload:** in `async_unload_entry`, delete both issue ids for the entry so a
  removed integration leaves no stale repairs.
- **Strings:** add an `issues` section to `strings.json` and `translations/en.json`
  with `title` + `description` for `thermostat_unavailable` and `vents_unavailable`
  (descriptions reference the placeholders).
- `SystemHealthSensor` is left unchanged (minor, pre-existing duplication of the
  unavailable-entity computation; not worth refactoring this slice).

### D. Efficiency UX

- **store.py:** add `get_heating_samples` / `increment_heating_samples` /
  `get_cooling_samples` / `increment_cooling_samples` (backed by
  `heating_samples` / `cooling_samples` dicts), a `reset_efficiency(room_key=None)`
  that clears rates **and** sample counts (one room, or all when `None`), and
  include the sample dicts in `export_efficiency()` / `import_efficiency()`
  (import tolerates their absence — backward compatible with existing exports).
- **coordinator.py:** in `_learn_efficiency`, after a rate is stored, increment the
  matching mode's sample counter for that room.
- **sensor.py:** `RoomEfficiencySensor.extra_state_attributes` gains
  `heating_samples`, `cooling_samples`, and `confidence`. Confidence is derived
  from the sample count of the mode that currently provides the sensor's value (the
  higher of heat/cool rate): `0 → "none"`, `1–2 → "low"`, `3–5 → "medium"`,
  `>=6 → "high"`. Thresholds defined as named constants in `const.py`.
- **__init__.py:** new `reset_efficiency(call)` service handler — optional `room`
  (case-insensitive, normalized to room_key); calls `store.reset_efficiency(...)`,
  then `await store.async_save()`. Registered alongside the existing services.
- **services.yaml:** add a `reset_efficiency` entry with an optional `room` field;
  add matching strings if the other services have them.

## Testing

- **A:** coordinator test `test_get_room_comfort_*` — within band → `True`, outside →
  `False`, missing temp/target → `None`. (Mirrors existing `test_coordinator.py`
  setup with `hass.states.async_set`.)
- **C:** `test_health.py` — with `freezegun`: a vent unavailable for < 5 min raises
  no issue; crossing 5 min raises the aggregate `vents_unavailable` issue; recovery
  clears it; an unavailable thermostat raises the ERROR issue. Assert via
  `homeassistant.helpers.issue_registry.async_get(hass).issues`.
- **D:** store test for `reset_efficiency` (per-room and all) and sample
  export/import round-trip; coordinator test that `_learn_efficiency` increments the
  sample count; a service-level `reset_efficiency` test (like the Slice-A efficiency
  round-trip test, using `tmp_path` if it touches files — it does not).
- **B:** assert `RoomDeltaSensor` / `RoomEfficiencySensor` have
  `entity_registry_enabled_default` truthy (and the timestamp sensors still false).
- Full suite stays green; CI (HACS validate, hassfest, pytest) green.

## Non-Goals

- A starter dashboard or knob-tiering (Slice D).
- Refactoring `SystemHealthSensor` to share `health.py` (acceptable duplication).
- Celsius/i18n beyond the new English issue strings.
- The Slice-A review follow-ups (pure-predicate `is_room_overridden`,
  `import_efficiency` error handling), unless trivially adjacent.

## Success Criteria

- Each room exposes a `{Room} Comfortable` binary sensor that is `on` within the
  hysteresis band, `off` outside it, and unknown when data is missing.
- `Delta` and `Efficiency` sensors are enabled by default on new installs/rooms.
- A vent or thermostat that stays unavailable for 5 minutes produces an actionable
  Repairs issue that auto-clears on recovery and is removed on unload; brief blips
  raise nothing.
- The Efficiency sensor exposes sample counts and a confidence level; a
  `reset_efficiency` service clears learned rates (and samples) for one room or all.
- New tests cover each component and CI is green.

## Risks & Mitigations

- **Repairs flapping / noise.** Mitigated by the fixed 5-min debounce and auto-clear.
- **Health eval breaking the update loop.** Mitigated by wrapping `_evaluate_health`
  in its own try/except inside `_async_update_data`.
- **enabled_default surprises existing users.** It only affects new
  registrations; documented in the CHANGELOG so expectations are set.
- **Confidence threshold bikeshedding.** Thresholds are named constants, trivial to
  tune later.
