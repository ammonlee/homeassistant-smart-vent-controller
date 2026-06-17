# Smart Vent Controller — Publish-Quality Hardening

**Date:** 2026-06-16
**Status:** Approved (design)
**Baseline commit:** `da8080c7589fc511a279fb2bc0a2f13f3ee2ffdf` (branch `main`)

## Goal

Make the Smart Vent Controller a clean, validated, trustworthy **HACS custom
repository** that other users can install with confidence. This means CI and
validation as the trust signal, repo hygiene, accurate metadata, a real test
foundation, and a set of correctness/robustness fixes made under CI protection.

Out of scope for this effort: submission to the HACS **default** list (brand
icons, `hacs/default` PR), and pursuing Home Assistant **core quality-scale**
tiers. These remain possible future directions but are not pursued here.

## Scope Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Distribution target | Polish the HACS **custom** repo | Lowest friction; CI + validation is the trust signal |
| Legacy root YAMLs | Move to `examples/` | Preserve as reference/migration aids; remove from installer's path |
| Test foundation | Migrate to `pytest-homeassistant-custom-component` | Kills the brittle hand-rolled stubs; unlocks real behavioral tests |
| Sequencing | Validate-first | CI guards every subsequent fix; the riskiest change (datetime) lands under CI |

## Approach

**Validate-first.** Land the CI/validation safety net before touching behavior,
so every correctness fix is guarded against regression and the public-facing
trust signals (passing checks, badges) appear early. Each phase is its own
commit/PR to stay reviewable; phases 2–4 all run green under the phase-1 CI.

Rejected alternatives:
- **Correctness-first** — makes the riskiest change (datetime migration) with no
  CI safety net.
- **Big-bang refactor** — large diff, high regression risk, slow to ship;
  overkill for polishing a custom repo.

## Current-State Findings (evidence)

These are the concrete issues this effort addresses.

1. **Test suite does not collect.** `pytest` fails immediately:
   `tests/conftest.py`'s fake `Platform` stub lacks `CLIMATE`, but
   `custom_components/smart_vent_controller/__init__.py` references
   `Platform.CLIMATE`. The 157-line hand-rolled HA stub has drifted out of sync
   with the code, and no CI catches it.
2. **Inconsistent datetime handling.** `binary_sensor.py` uses timezone-aware
   `datetime.now(tz=timezone.utc)` (lines 78, 155), while seven modules use
   naive `datetime.now()`:
   - `coordinator.py` (158, 191, 363, 373)
   - `automations.py` (80, 98)
   - `cache.py` (37, 50)
   - `scripts.py` (231, 565)
   - `sensor.py` (311)
   - `error_handling.py` (297)
   - `diagnostics.py` (189)

   This is not crashing today because comparisons route through `.timestamp()`,
   but it is the same fragility class as the already-fixed bug in commit
   `5eae6af`, and it blocks clean time-freezing in tests. HA convention is
   `homeassistant.util.dt`.

   Related active bug found while planning: `binary_sensor.py:78-80` derives
   `now_local = now_utc.time()` from a UTC datetime and checks the 22:00-06:00
   night window against it, so the day/night occupancy-linger window is
   evaluated in UTC rather than the user's local timezone (off by hours for most
   users). The datetime task fixes this with `dt_util.now()` (local) for the
   time-of-day check while keeping `dt_util.utcnow()` for elapsed-vs-`last_changed`.
3. **Coarse coordinator error handling.** `_async_update_data` wraps the entire
   room loop in a single `try/except Exception` → `UpdateFailed`, so one
   unexpected error blanks every room's data for that cycle.
4. **Leaky abstraction.** `coordinator.set_room_override` / `is_room_overridden`
   reach into the store's private `_data` dict (`store._data.setdefault(...)`,
   lines 360, 369) to manage `room_overrides`. `binary_sensor.py:151`
   (`RoomOverrideActiveSensor.extra_state_attributes`) does the same
   (`coordinator.store._data.get("room_overrides", {})`); both must move to a
   public store API.
5. **Git hygiene.** No `.gitignore`; `.DS_Store` and the binary
   `keypad_esp32.zip` are tracked (zip is also in history). `keypad_esp32.zip`
   is already staged for deletion at baseline.
6. **Metadata gaps.** `manifest.json` lacks `integration_type`. `hacs.json`
   should be verified for completeness.
7. **File/doc sprawl at repo root.** `TESTING_GUIDE.md`, `UPGRADE_NOTES.md`,
   `HVAC_CYCLE_PROTECTION.md`, plus two large legacy YAMLs
   (`vent_zone_controller_updated.yaml` ~77 KB,
   `room_comfort_dashboard_fixed.yaml` ~13 KB) that the integration supersedes.

The architecture itself is sound: `algorithm.py` is pure/stateless and testable,
the coordinator owns runtime state, and persistence goes through a `Store`. This
effort hardens and packages that foundation — it does not restructure it.

## Plan

### Phase 1 — Repo hygiene & validation (the trust layer)

- Add `.gitignore` covering Python, Home Assistant, and macOS artifacts.
- Stop tracking `.DS_Store`; confirm `keypad_esp32.zip` removal (already staged).
  Do **not** rewrite git history to purge the zip (would change every commit
  hash on a published repo); removing it going forward is sufficient.
- Add GitHub Actions workflows:
  - **HACS validation** (`hacs/action`) — category: integration.
  - **hassfest** (`home-assistant/actions/hassfest`) — manifest/structure.
  - **pytest** — runs the suite on push and PR.
- Add CI/HACS badges to `README.md`.
- `manifest.json`: add `"integration_type": "hub"`. Verify `hacs.json` fields.
- Move `TESTING_GUIDE.md`, `UPGRADE_NOTES.md`, `HVAC_CYCLE_PROTECTION.md` into
  `docs/`. Update any links in `README.md`.
- Move `vent_zone_controller_updated.yaml` and `room_comfort_dashboard_fixed.yaml`
  into `examples/`, with a short `examples/README.md` noting they are the legacy
  package/dashboard the integration was ported from and now supersedes.

**Done when:** the three workflows exist and run; hygiene files are no longer
tracked; docs and legacy YAMLs are relocated; README reflects the new layout.

### Phase 2 — Real test foundation

- Add `requirements_test.txt` pinning `pytest-homeassistant-custom-component`
  (which transitively pins a compatible `homeassistant`/Python), plus `pytest`.
- Add pytest configuration (e.g. `[tool:pytest]` / `pyproject.toml`) with
  `asyncio_mode` and the custom-component test conventions.
- Delete the hand-rolled stub `tests/conftest.py`; replace with a minimal
  conftest using the framework's fixtures (`enable_custom_integrations`, etc.).
- Port the existing `test_algorithm.py` and `test_store.py` to run under the real
  harness with minimal change (algorithm tests are pure and should be unchanged;
  store tests use the real `Store` via `hass`).
- Wire the suite into the Phase-1 pytest workflow; achieve a green run.

**Done when:** `pytest` collects and passes locally and in CI against a real
`homeassistant` install, with the stub conftest gone.

### Phase 3 — Correctness / hardening (under CI)

- **Datetime consistency:** replace naive `datetime.now()` with HA's `dt_util`
  (`dt_util.utcnow()` / `dt_util.now()` as appropriate) across the seven modules
  listed in Findings #2. Preserve existing epoch-second semantics where values
  are persisted, to avoid migrating stored timestamps.
- **Per-room failure isolation:** in `coordinator._async_update_data`, wrap each
  room's processing so a failure on one entity logs and skips that room rather
  than raising `UpdateFailed` for the whole cycle. Keep an outer guard only for
  truly unexpected, non-room errors.
- **Public override API:** add methods to `SmartVentStore` (e.g.
  `set_room_override` / `get_room_override` / `clear_expired_overrides`) that own
  the `room_overrides` structure; refactor the coordinator to call them instead
  of touching `store._data`.
- Add/extend tests covering each change (enabled by Phase 2).

**Done when:** no naive `datetime.now()` remains in the seven modules; a single
bad room no longer fails the whole update; the coordinator no longer accesses
`store._data`; new tests cover these paths and CI is green.

### Phase 4 — Coverage depth

- Add behavioral tests for the coordinator: update cycle, HVAC cycle start/end,
  efficiency learning blend, and room-override expiry.
- Flag broader `config_flow.py` (857 lines) and `scripts.py` (609 lines) coverage
  as explicit follow-on work (tracked, not required for this effort).

**Done when:** coordinator behavior has meaningful test coverage; follow-on
coverage gaps are documented.

## Non-Goals

- HACS default-list submission (brand icons, `hacs/default` PR).
- Home Assistant core quality-scale certification.
- Rewriting git history to purge the committed zip.
- Restructuring `config_flow.py` / `scripts.py` (only test coverage is in scope
  here; refactors are future work).
- New end-user features.

## Success Criteria

- A fresh clone shows passing CI: HACS validate, hassfest, and pytest all green.
- `pytest` runs against a real `homeassistant` install with no hand-rolled stubs.
- No naive-`datetime` inconsistency remains in the identified modules.
- The coordinator tolerates a single bad room without blanking all data and no
  longer reaches into `store._data`.
- Repo root contains only product-relevant files; dev docs under `docs/`, legacy
  YAMLs under `examples/`, hygiene files untracked.
- `README.md` reflects the new layout and shows CI/HACS badges.

## Risks & Mitigations

- **HA version pin churn:** `pytest-homeassistant-custom-component` pins a
  specific HA/Python pair; CI must match. Mitigation: pin explicitly in
  `requirements_test.txt` and the workflow's Python version.
- **Datetime migration regressions:** changing time handling can shift persisted
  timestamp semantics. Mitigation: keep epoch-second storage format; land under
  Phase-1 CI; add targeted tests in Phase 3.
- **Test-harness porting friction:** real HA fixtures behave differently from the
  stubs. Mitigation: port the pure algorithm tests first (lowest risk) to prove
  the harness, then the store tests.
