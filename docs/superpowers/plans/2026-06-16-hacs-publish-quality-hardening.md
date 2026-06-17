# HACS Publish-Quality Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Smart Vent Controller a clean, validated, trustworthy HACS custom repository by adding CI/validation, fixing repo hygiene, replacing the brittle test stubs with the official HA test harness, and landing a set of correctness fixes under CI protection.

**Architecture:** A Home Assistant custom integration under `custom_components/smart_vent_controller/`. A pure, stateless `algorithm.py` does vent math; `SmartVentControllerCoordinator` owns runtime state and persists it through `SmartVentStore` (an HA `Store`). Work proceeds in four phases — hygiene/validation, test foundation, correctness fixes, coverage — each phase its own set of commits, with phases 2-4 running green under the phase-1 CI.

**Tech Stack:** Python 3.13, Home Assistant, `pytest`, `pytest-homeassistant-custom-component`, `freezegun` (bundled), GitHub Actions, HACS.

**Spec:** `docs/superpowers/specs/2026-06-16-hacs-publish-quality-hardening-design.md`

**Branch:** `hardening/hacs-publish-quality` (already created off `main`).

---

## Conventions for every task

- Run all commands from the repo root: `/Users/ammon/Development/Home Assistant/homeassistant-smart-vent-controller`.
- Commit messages end with the trailer:
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`
- After Phase 2, `pytest` must stay green; run it before every commit in Phases 3-4.
- **Test environment:** system `python3` is 3.9 and CANNOT run Home Assistant. A
  Python 3.13 venv with the HA test harness is already provisioned at `.venv/`
  (via `uv`). Wherever this plan shows `python3 -m pytest` or `python3 ...`, run
  it through the venv instead: **`.venv/bin/python -m pytest`** /
  `.venv/bin/python ...`. Never `git add` the `.venv/` directory.

---

## Phase 1 — Repo hygiene & validation

### Task 1: Add `.gitignore` and untrack junk files

**Files:**
- Create: `.gitignore`
- Untrack: `.DS_Store`, `keypad_esp32.zip`

- [ ] **Step 1: Create `.gitignore`**

Create `.gitignore` with:

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
.eggs/
build/
dist/

# Test / tooling
.pytest_cache/
.coverage
htmlcov/
.mypy_cache/
.ruff_cache/

# Virtual envs
.venv/
venv/
env/

# macOS
.DS_Store

# Editors
.idea/
.vscode/
```

- [ ] **Step 2: Stop tracking junk that is already committed**

Run:
```bash
git rm --cached .DS_Store
git rm --cached --ignore-unmatch keypad_esp32.zip
```
Expected: `.DS_Store` removed from index; zip removed if still tracked (it is already staged-deleted at baseline, so `--ignore-unmatch` makes this safe).

- [ ] **Step 3: Verify nothing junky remains tracked**

Run:
```bash
git ls-files | grep -iE 'DS_Store|\.zip|\.pyc|pytest_cache' || echo "CLEAN"
```
Expected: `CLEAN`

- [ ] **Step 4: Commit**

```bash
git add .gitignore
git commit -m "chore: add .gitignore and stop tracking .DS_Store and firmware zip

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Relocate dev docs and legacy YAMLs

**Files:**
- Move: `TESTING_GUIDE.md`, `UPGRADE_NOTES.md`, `HVAC_CYCLE_PROTECTION.md` → `docs/`
- Move: `vent_zone_controller_updated.yaml`, `room_comfort_dashboard_fixed.yaml` → `examples/`
- Create: `examples/README.md`
- Modify: `README.md` (fix any links to moved docs)

- [ ] **Step 1: Move the dev docs**

Run:
```bash
mkdir -p docs examples
git mv TESTING_GUIDE.md docs/TESTING_GUIDE.md
git mv UPGRADE_NOTES.md docs/UPGRADE_NOTES.md
git mv HVAC_CYCLE_PROTECTION.md docs/HVAC_CYCLE_PROTECTION.md
```

- [ ] **Step 2: Move the legacy YAMLs**

Run:
```bash
git mv vent_zone_controller_updated.yaml examples/vent_zone_controller_updated.yaml
git mv room_comfort_dashboard_fixed.yaml examples/room_comfort_dashboard_fixed.yaml
```

- [ ] **Step 3: Add `examples/README.md`**

Create `examples/README.md`:

```markdown
# Examples (legacy reference)

These files are the original Home Assistant **package** and **dashboard** the
Smart Vent Controller integration was ported from. The integration now replaces
them — you do **not** need them for a normal install.

They are kept only as a reference for users migrating from the old YAML-package
approach.

| File | What it was |
|------|-------------|
| `vent_zone_controller_updated.yaml` | The original `packages/` HA config (input_number/input_boolean helpers + template logic) that the integration supersedes. |
| `room_comfort_dashboard_fixed.yaml` | A Lovelace dashboard built against the old package's entities. |
```

- [ ] **Step 4: Fix links in `README.md`**

Run this to find any references to the moved files:
```bash
grep -nE 'TESTING_GUIDE|UPGRADE_NOTES|HVAC_CYCLE_PROTECTION|vent_zone_controller_updated|room_comfort_dashboard_fixed' README.md || echo "NO LINKS"
```
If any line is printed, update it to point at the new `docs/` or `examples/` path. If `NO LINKS`, skip.

- [ ] **Step 5: Verify root is tidy**

Run:
```bash
ls *.md *.yaml 2>/dev/null
```
Expected: only `README.md` remains at root (no `*.yaml`, no other `*.md`).

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "docs: move dev docs to docs/ and legacy YAMLs to examples/

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Tighten integration metadata

**Files:**
- Modify: `custom_components/smart_vent_controller/manifest.json`
- Modify: `hacs.json`

- [ ] **Step 1: Add `integration_type` to the manifest**

In `custom_components/smart_vent_controller/manifest.json`, add `"integration_type": "hub"` after the `"name"` line. Resulting file:

```json
{
  "domain": "smart_vent_controller",
  "name": "Smart Vent Controller",
  "integration_type": "hub",
  "version": "1.1.0",
  "documentation": "https://github.com/ammonlee/homeassistant-smart-vent-controller",
  "issue_tracker": "https://github.com/ammonlee/homeassistant-smart-vent-controller/issues",
  "codeowners": ["@ammonlee"],
  "requirements": [],
  "config_flow": true,
  "iot_class": "local_polling",
  "dependencies": []
}
```

- [ ] **Step 2: Drop the non-standard `domains` key from `hacs.json`**

`hacs.json` currently carries a `domains` key, which is not part of the HACS
manifest schema (HACS reads the integration domain from `manifest.json`). Replace
`hacs.json` with:

```json
{
  "name": "Smart Vent Controller",
  "render_readme": true,
  "homeassistant": "2024.1.0"
}
```

- [ ] **Step 3: Validate JSON syntax**

Run:
```bash
python3 -c "import json; json.load(open('custom_components/smart_vent_controller/manifest.json')); json.load(open('hacs.json')); print('JSON OK')"
```
Expected: `JSON OK`

- [ ] **Step 4: Commit**

```bash
git add custom_components/smart_vent_controller/manifest.json hacs.json
git commit -m "chore: set integration_type=hub and clean up hacs.json

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Add hassfest + HACS validation workflows

**Files:**
- Create: `.github/workflows/validate.yml`

(The pytest CI job is added in Task 8, once the suite is green.)

- [ ] **Step 1: Create the validation workflow**

Create `.github/workflows/validate.yml`:

```yaml
name: Validate

on:
  push:
    branches: [main]
  pull_request:
  workflow_dispatch:
  schedule:
    - cron: "0 6 * * 1"

jobs:
  hassfest:
    name: hassfest
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: home-assistant/actions/hassfest@master

  hacs:
    name: HACS
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: hacs/action@main
        with:
          category: integration
```

- [ ] **Step 2: Confirm the workflow file is valid YAML**

Run:
```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/validate.yml')); print('YAML OK')"
```
Expected: `YAML OK` (if `yaml` is missing, run `pip install pyyaml` first).

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/validate.yml
git commit -m "ci: add hassfest and HACS validation workflows

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Phase 2 — Real test foundation

### Task 5: Add the test harness and pytest config

**Files:**
- Create: `requirements_test.txt`
- Create: `pyproject.toml`

- [ ] **Step 1: Confirm the harness is installed in the venv**

The `.venv/` (Python 3.13) was provisioned via `uv` with
`pytest-homeassistant-custom-component` already installed. Confirm the pin:
```bash
.venv/bin/python -c "import importlib.metadata as m; print('pytest-homeassistant-custom-component==' + m.version('pytest-homeassistant-custom-component')); print('homeassistant==' + m.version('homeassistant'))"
```
Expected: `pytest-homeassistant-custom-component==0.13.316` and `homeassistant==2026.2.3` (or whatever is installed — use the printed harness version verbatim in the next step).

- [ ] **Step 2: Write `requirements_test.txt`**

Create `requirements_test.txt` with the pinned harness (only this line — `pytest`, `freezegun`, and a matching `homeassistant` are pulled in transitively and pinned by it):

```text
pytest-homeassistant-custom-component==0.13.316
```

- [ ] **Step 3: Write `pyproject.toml` pytest config**

Create `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
pythonpath = ["."]
```

`pythonpath = ["."]` makes `custom_components.smart_vent_controller` importable; `asyncio_mode = "auto"` lets async tests run without per-test decorators.

- [ ] **Step 4: Commit**

```bash
git add requirements_test.txt pyproject.toml
git commit -m "test: add pytest-homeassistant-custom-component harness and config

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Replace the hand-rolled stub conftest

**Files:**
- Rewrite: `tests/conftest.py`

- [ ] **Step 1: Replace `tests/conftest.py` with the framework conftest**

Overwrite `tests/conftest.py` entirely with:

```python
"""Shared test fixtures.

Uses the official Home Assistant custom-component test harness instead of
hand-rolled module stubs, so tests run against real HA APIs.
"""
import pytest

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Allow Home Assistant to load this custom integration during tests."""
    yield
```

- [ ] **Step 2: Verify the old stub code is gone**

Run:
```bash
grep -c "_ensure_stub\|_HA_STUBS\|_StoreStub" tests/conftest.py || echo "STUBS GONE"
```
Expected: `STUBS GONE`

- [ ] **Step 3: Commit**

```bash
git add tests/conftest.py
git commit -m "test: replace hand-rolled HA stubs with official test harness

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Get the existing tests green under the real harness

**Files:**
- Modify (if needed): `tests/test_algorithm.py`
- Modify: `tests/test_store.py`

- [ ] **Step 1: Run the algorithm tests against real HA**

Run:
```bash
python3 -m pytest tests/test_algorithm.py -v
```
Expected: all tests PASS. (With real `homeassistant` installed, importing `custom_components.smart_vent_controller.algorithm` now succeeds because `Platform.CLIMATE` and every other HA symbol resolve.) If any fail purely on import path, confirm `pyproject.toml`'s `pythonpath = ["."]` from Task 5 is present.

- [ ] **Step 2: Make the store tests use the real `hass` fixture**

The store tests previously constructed `SmartVentStore(MagicMock(), ...)`. Under
the real harness, give it the real `hass`. Replace the two fixtures at the top of
`tests/test_store.py`:

```python
"""Tests for the SmartVentStore persistence layer."""
import pytest

from custom_components.smart_vent_controller.store import SmartVentStore


@pytest.fixture
def store(hass):
    return SmartVentStore(hass, "test_entry_123")
```

(Delete the old `mock_hass` fixture and the `unittest.mock` import. All test
methods keep their bodies — they only exercise in-memory `_data` via the public
properties/methods.)

- [ ] **Step 3: Fix the one test that builds a second store**

In `tests/test_store.py`, `test_roundtrip` builds `SmartVentStore(MagicMock(), "other")`. Change that line to reuse `hass`:

```python
    def test_roundtrip(self, store, hass):
        store.set_heating_rate("a", 0.1)
        store.set_cooling_rate("b", 0.2)
        store.max_running_minutes = 45.0

        exported = store.export_efficiency()

        store2 = SmartVentStore(hass, "other")
        store2.import_efficiency(exported)

        assert store2.get_heating_rate("a") == 0.1
        assert store2.get_cooling_rate("b") == 0.2
        assert store2.max_running_minutes == 45.0
```

- [ ] **Step 4: Run the full suite**

Run:
```bash
python3 -m pytest -v
```
Expected: every test in `tests/test_algorithm.py` and `tests/test_store.py` PASSES, zero collection errors.

- [ ] **Step 5: Commit**

```bash
git add tests/test_store.py tests/test_algorithm.py
git commit -m "test: port store/algorithm tests to the real HA harness

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: Add the pytest CI job and README badges

**Files:**
- Create: `.github/workflows/test.yml`
- Modify: `README.md`

- [ ] **Step 1: Create the test workflow**

Create `.github/workflows/test.yml`:

```yaml
name: Tests

on:
  push:
    branches: [main]
  pull_request:
  workflow_dispatch:

jobs:
  pytest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - name: Install test requirements
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements_test.txt
      - name: Run tests
        run: pytest -v
```

If CI reports that the pinned `homeassistant` needs a different Python, set
`python-version` to the version that HA pin requires and re-push.

- [ ] **Step 2: Validate the workflow YAML**

Run:
```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/test.yml')); print('YAML OK')"
```
Expected: `YAML OK`

- [ ] **Step 3: Add badges to `README.md`**

Directly under the title line `# Smart Vent Controller`, add the badges (the HACS badge already exists below — leave it):

```markdown
[![Validate](https://github.com/ammonlee/homeassistant-smart-vent-controller/actions/workflows/validate.yml/badge.svg)](https://github.com/ammonlee/homeassistant-smart-vent-controller/actions/workflows/validate.yml)
[![Tests](https://github.com/ammonlee/homeassistant-smart-vent-controller/actions/workflows/test.yml/badge.svg)](https://github.com/ammonlee/homeassistant-smart-vent-controller/actions/workflows/test.yml)
```

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/test.yml README.md
git commit -m "ci: run pytest on push/PR and add status badges

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Phase 3 — Correctness / hardening

> All Phase 3 tasks: run `python3 -m pytest -v` before each commit and confirm green.

### Task 9: Migrate naive `datetime.now()` to `dt_util` (non-binary_sensor modules)

**Files:**
- Modify: `custom_components/smart_vent_controller/cache.py:4,37,50`
- Modify: `custom_components/smart_vent_controller/automations.py:10,80,98`
- Modify: `custom_components/smart_vent_controller/coordinator.py:158,191`
- Modify: `custom_components/smart_vent_controller/scripts.py:10,231,565`
- Modify: `custom_components/smart_vent_controller/sensor.py:309-311`
- Modify: `custom_components/smart_vent_controller/error_handling.py:6,297`
- Modify: `custom_components/smart_vent_controller/diagnostics.py:4,189`
- Test: `tests/test_error_handling.py` (create)

`dt_util.utcnow()` returns a timezone-aware UTC datetime; `.timestamp()` on it yields the same epoch seconds the naive calls produced, so persisted timestamps stay compatible.

- [ ] **Step 1: Write a failing test for the error window using frozen time**

Create `tests/test_error_handling.py`:

```python
"""Tests for ErrorRecovery's rolling error window."""
from datetime import timedelta

from freezegun import freeze_time

from custom_components.smart_vent_controller.error_handling import ErrorRecovery


def test_errors_outside_window_are_pruned(hass):
    rec = ErrorRecovery(hass, entry=None)

    with freeze_time("2026-06-16 12:00:00") as frozen:
        rec.record_error("vent_control", RuntimeError("boom"))
        assert rec._error_counts["vent_control"] == 1

        # Advance past the 5-minute window; the old error should be pruned.
        frozen.tick(timedelta(minutes=6))
        rec.record_error("vent_control", RuntimeError("boom2"))
        assert rec._error_counts["vent_control"] == 1
```

- [ ] **Step 2: Run it and watch it fail**

Run:
```bash
python3 -m pytest tests/test_error_handling.py -v
```
Expected: FAIL — `freeze_time` patches `datetime`, but `error_handling.py` still calls naive `datetime.now()`, which freezegun *does* patch, so this may actually pass already. If it passes, that is fine; the test still locks in behavior. The real point of the change is consistency — proceed to migrate.

- [ ] **Step 3: Migrate `error_handling.py`**

In `error_handling.py`, add the import near the top (after the existing `from datetime import datetime, timedelta`):

```python
from homeassistant.util import dt as dt_util
```

Change line 297 from:

```python
        now = datetime.now()
```
to:
```python
        now = dt_util.utcnow()
```

- [ ] **Step 4: Migrate `cache.py`**

In `cache.py`, add after line 4 (`from datetime import datetime, timedelta`):

```python
from homeassistant.util import dt as dt_util
```

Change line 37 from `if datetime.now() - timestamp > self._ttl:` to:
```python
        if dt_util.utcnow() - timestamp > self._ttl:
```
Change line 50 from `self._cache[key] = (value, datetime.now())` to:
```python
        self._cache[key] = (value, dt_util.utcnow())
```

- [ ] **Step 5: Migrate `automations.py`**

In `automations.py`, add after line 10 (`from datetime import datetime, timedelta`):

```python
from homeassistant.util import dt as dt_util
```

Change line 80 from `elapsed = (datetime.now() - self._last_trigger_time).total_seconds()` to:
```python
            elapsed = (dt_util.utcnow() - self._last_trigger_time).total_seconds()
```
Change line 98 from `self._last_trigger_time = datetime.now()` to:
```python
        self._last_trigger_time = dt_util.utcnow()
```

- [ ] **Step 6: Migrate `coordinator.py` cycle timestamps**

In `coordinator.py`, add to the imports block (near `from datetime import datetime, timedelta`):

```python
from homeassistant.util import dt as dt_util
```

Change line 158 (`now = datetime.now().timestamp()` in `_handle_cycle_start`) and line 191 (same in `_handle_cycle_end`) to:
```python
        now = dt_util.utcnow().timestamp()
```
(Leave lines 363/373 — the override timestamps — for Task 12, which removes them.)

- [ ] **Step 7: Migrate `scripts.py`**

In `scripts.py`, add after line 10 (`from datetime import datetime`):

```python
from homeassistant.util import dt as dt_util
```

Change line 231 (`now_ts = datetime.now().timestamp()`) to:
```python
            now_ts = dt_util.utcnow().timestamp()
```
Change line 565 (`now = datetime.now().timestamp()`) to:
```python
        now = dt_util.utcnow().timestamp()
```

- [ ] **Step 8: Migrate `sensor.py`**

In `sensor.py`, replace the in-function local import at line 309 (`from datetime import datetime`) with:
```python
        from homeassistant.util import dt as dt_util
```
and change line 311 (`now = datetime.now().timestamp()`) to:
```python
        now = dt_util.utcnow().timestamp()
```

- [ ] **Step 9: Migrate `diagnostics.py`**

In `diagnostics.py`, add after line 4 (`from datetime import datetime`):

```python
from homeassistant.util import dt as dt_util
```
Change line 189 (`"timestamp": datetime.now().isoformat(),`) to:
```python
        "timestamp": dt_util.utcnow().isoformat(),
```

- [ ] **Step 10: Confirm no naive `datetime.now()` remains in these modules**

Run:
```bash
grep -rn "datetime.now()" custom_components/smart_vent_controller/cache.py custom_components/smart_vent_controller/automations.py custom_components/smart_vent_controller/scripts.py custom_components/smart_vent_controller/sensor.py custom_components/smart_vent_controller/error_handling.py custom_components/smart_vent_controller/diagnostics.py && echo "STILL PRESENT" || echo "ALL MIGRATED"
```
Expected: `ALL MIGRATED`

- [ ] **Step 11: Run tests**

Run:
```bash
python3 -m pytest -v
```
Expected: all PASS (including the new `tests/test_error_handling.py`).

- [ ] **Step 12: Commit**

```bash
git add custom_components/smart_vent_controller/ tests/test_error_handling.py
git commit -m "fix: use dt_util for time across modules (consistent, tz-aware)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 10: Fix the day/night UTC bug and migrate `binary_sensor.py` time handling

**Files:**
- Modify: `custom_components/smart_vent_controller/algorithm.py` (add pure `is_night_time`)
- Modify: `custom_components/smart_vent_controller/binary_sensor.py:3,78-80,88,155`
- Test: `tests/test_algorithm.py` (add cases)

The night window must be evaluated in the user's **local** timezone. We extract the decision into a pure function so it is unit-testable, then have `binary_sensor` call it with `dt_util.now()` (HA local time).

- [ ] **Step 1: Write failing tests for `is_night_time`**

Add to `tests/test_algorithm.py` — extend the import block to include `is_night_time`:

```python
from custom_components.smart_vent_controller.algorithm import (
    AlgorithmSettings,
    round_to_granularity,
    has_reached_setpoint,
    should_pre_adjust,
    compute_efficiency_sample,
    calculate_vent_target,
    calculate_linear_target,
    calculate_longest_time_to_target,
    calculate_all_vent_targets,
    adjust_for_minimum_airflow,
    compute_simple_targets,
    is_night_time,
)
```

and append this test class:

```python
from datetime import time


class TestIsNightTime:
    def test_late_evening_is_night(self):
        assert is_night_time(time(23, 0)) is True

    def test_early_morning_is_night(self):
        assert is_night_time(time(5, 0)) is True

    def test_boundaries_inclusive(self):
        assert is_night_time(time(22, 0)) is True
        assert is_night_time(time(6, 0)) is True

    def test_midday_is_day(self):
        assert is_night_time(time(12, 0)) is False

    def test_custom_window(self):
        assert is_night_time(time(20, 30), night_start=time(20, 0), night_end=time(7, 0)) is True
```

- [ ] **Step 2: Run it and watch it fail**

Run:
```bash
python3 -m pytest tests/test_algorithm.py::TestIsNightTime -v
```
Expected: FAIL with `ImportError: cannot import name 'is_night_time'`.

- [ ] **Step 3: Implement `is_night_time` in `algorithm.py`**

Add to the top of `algorithm.py` (the `from datetime import` line — there is currently no `datetime` import, so add one) and the function. After the existing `import math` line, add:

```python
from datetime import time as dt_time
```

Then add this function (e.g. right after `round_to_granularity`):

```python
def is_night_time(
    now: "dt_time",
    night_start: "dt_time" = dt_time(22, 0),
    night_end: "dt_time" = dt_time(6, 0),
) -> bool:
    """Return True if a local time-of-day falls in the overnight window.

    The window wraps midnight: night is ``>= night_start`` OR ``<= night_end``.
    """
    return now >= night_start or now <= night_end
```

- [ ] **Step 4: Run the tests to confirm they pass**

Run:
```bash
python3 -m pytest tests/test_algorithm.py::TestIsNightTime -v
```
Expected: all PASS.

- [ ] **Step 5: Use local time + the pure helper in `binary_sensor.py`**

In `binary_sensor.py`, update the import on line 3 from:
```python
from datetime import datetime, time, timezone
```
to:
```python
from homeassistant.util import dt as dt_util

from .algorithm import is_night_time
```
(Remove the now-unused `datetime`/`time`/`timezone` import. Keep any other existing imports in the file untouched.)

Replace lines 78-84 (the night calc) from:
```python
        now_utc = datetime.now(tz=timezone.utc)
        now_local = now_utc.time()
        is_night = time(22, 0) <= now_local or now_local <= time(6, 0)
        linger_min = self._entry.options.get(
            "occupancy_linger_night_min" if is_night else "occupancy_linger_min",
            60 if is_night else 30,
        )
```
to:
```python
        is_night = is_night_time(dt_util.now().time())
        linger_min = self._entry.options.get(
            "occupancy_linger_night_min" if is_night else "occupancy_linger_min",
            60 if is_night else 30,
        )
```

Replace line 88 (the elapsed calc, which compares against the aware `last_changed`) from:
```python
            elapsed = (now_utc - last_changed).total_seconds() / 60
```
to:
```python
            elapsed = (dt_util.utcnow() - last_changed).total_seconds() / 60
```

Replace line 155 (`RoomOverrideActiveSensor.extra_state_attributes`) from:
```python
            remaining = max(0, (until_ts - datetime.now(tz=timezone.utc).timestamp()) / 60)
```
to:
```python
            remaining = max(0, (until_ts - dt_util.utcnow().timestamp()) / 60)
```

- [ ] **Step 6: Confirm no naive/aware `datetime.now` remains in the file**

Run:
```bash
grep -n "datetime.now" custom_components/smart_vent_controller/binary_sensor.py && echo "STILL PRESENT" || echo "MIGRATED"
```
Expected: `MIGRATED`

- [ ] **Step 7: Run the full suite**

Run:
```bash
python3 -m pytest -v
```
Expected: all PASS.

- [ ] **Step 8: Commit**

```bash
git add custom_components/smart_vent_controller/algorithm.py custom_components/smart_vent_controller/binary_sensor.py tests/test_algorithm.py
git commit -m "fix: evaluate day/night occupancy window in local time

Was comparing the 22:00-06:00 night window against a UTC time-of-day,
shifting the window by the user's UTC offset. Extract is_night_time as a
pure, tested helper and feed it dt_util.now() (local).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 11: Isolate per-room failures in the coordinator update

**Files:**
- Modify: `custom_components/smart_vent_controller/coordinator.py:76-153`
- Test: `tests/test_coordinator.py` (create)

Extract the per-room read into a helper and wrap each room in try/except so one bad entity logs-and-skips instead of failing the whole refresh.

- [ ] **Step 1: Write a failing test for per-room isolation**

Create `tests/test_coordinator.py`:

```python
"""Coordinator behavioral tests."""
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smart_vent_controller.const import DOMAIN
from custom_components.smart_vent_controller.coordinator import (
    SmartVentControllerCoordinator,
)


def _make_entry(rooms):
    return MockConfigEntry(
        domain=DOMAIN,
        data={"main_thermostat": "climate.main", "rooms": rooms},
        options={},
    )


async def test_one_bad_room_does_not_blank_others(hass):
    rooms = [
        {"name": "Good Room", "temp_sensor": "sensor.good", "vent_entities": []},
        {"name": "Bad Room", "temp_sensor": "sensor.bad", "vent_entities": []},
    ]
    entry = _make_entry(rooms)
    entry.add_to_hass(hass)
    coordinator = SmartVentControllerCoordinator(hass, entry)
    await coordinator.async_initialize()

    hass.states.async_set("sensor.good", "70.0")

    # Force the bad room's read to raise; the good room must still be collected.
    original = coordinator._read_room_into

    def explode(room, data):
        if room.get("name") == "Bad Room":
            raise ValueError("sensor exploded")
        return original(room, data)

    coordinator._read_room_into = explode

    data = await coordinator._async_update_data()

    assert data["good_room_temp"] == 70.0
    assert "bad_room_temp" not in data or data["bad_room_temp"] is None
```

- [ ] **Step 2: Run it and watch it fail**

Run:
```bash
python3 -m pytest tests/test_coordinator.py::test_one_bad_room_does_not_blank_others -v
```
Expected: FAIL — `_read_room_into` does not exist yet (AttributeError).

- [ ] **Step 3: Extract `_read_room_into` and wrap the loop**

In `coordinator.py`, replace the per-room body inside `_async_update_data` (the `for room in self.rooms:` block, lines ~99-147) with a guarded call:

```python
            for room in self.rooms:
                try:
                    self._read_room_into(room, data)
                except Exception as room_err:  # noqa: BLE001 - isolate one room
                    _LOGGER.warning(
                        "Skipping room %s this cycle: %s",
                        room.get("name", "?"),
                        room_err,
                    )

            return data
```

Then add this new method to the coordinator (place it just after `_async_update_data`):

```python
    def _read_room_into(self, room: dict, data: dict[str, Any]) -> None:
        """Read one room's temp/vent/occupancy into *data*. Raises on bad input."""
        room_name = room.get("name", "").lower().replace(" ", "_")
        temp_sensor = room.get("temp_sensor")
        climate_entity = room.get("climate_entity")

        current_temp = None
        if temp_sensor:
            state = self.hass.states.get(temp_sensor)
            if state and state.state not in ("unknown", "unavailable", "None", "none"):
                try:
                    current_temp = float(state.state)
                except (ValueError, TypeError):
                    pass

        if current_temp is None and climate_entity:
            climate = self.hass.states.get(climate_entity)
            if climate:
                temp = climate.attributes.get("current_temperature")
                if temp is not None:
                    try:
                        current_temp = float(temp)
                    except (ValueError, TypeError):
                        pass

        data[f"{room_name}_temp"] = current_temp

        vent_entities = room.get("vent_entities", [])
        positions = []
        for vent in vent_entities:
            vent_state = self.hass.states.get(vent)
            if vent_state:
                pos = vent_state.attributes.get("current_position", 0)
                try:
                    positions.append(float(pos))
                except (ValueError, TypeError):
                    pass
        data[f"{room_name}_vent_avg"] = (
            sum(positions) / len(positions) if positions else 0
        )

        occ_sensor = room.get("occupancy_sensor")
        if occ_sensor:
            occ_state = self.hass.states.get(occ_sensor)
            data[f"{room_name}_occupied"] = (
                occ_state.state == "on" if occ_state else False
            )
```

Keep the surrounding HVAC-action logic and the outer `try/except ... raise UpdateFailed` for genuinely unexpected, non-room failures.

- [ ] **Step 4: Run the test to confirm it passes**

Run:
```bash
python3 -m pytest tests/test_coordinator.py -v
```
Expected: PASS.

- [ ] **Step 5: Run the full suite**

Run:
```bash
python3 -m pytest -v
```
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add custom_components/smart_vent_controller/coordinator.py tests/test_coordinator.py
git commit -m "fix: isolate per-room read failures in coordinator update

One unavailable entity no longer blanks every room's data for the cycle.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 12: Add a public store override API; remove `store._data` reach-ins

**Files:**
- Modify: `custom_components/smart_vent_controller/store.py` (add methods)
- Modify: `custom_components/smart_vent_controller/coordinator.py:356-376`
- Modify: `custom_components/smart_vent_controller/binary_sensor.py:151`
- Test: `tests/test_store.py` (add cases)

- [ ] **Step 1: Write failing tests for the new store API**

Add to `tests/test_store.py`:

```python
class TestRoomOverrides:
    def test_no_override_by_default(self, store):
        assert store.get_room_override_until("bedroom") is None

    def test_set_and_get_override(self, store):
        store.set_room_override("bedroom", 5000.0)
        assert store.get_room_override_until("bedroom") == 5000.0

    def test_clear_override(self, store):
        store.set_room_override("bedroom", 5000.0)
        store.clear_room_override("bedroom")
        assert store.get_room_override_until("bedroom") is None

    def test_clear_missing_override_is_noop(self, store):
        store.clear_room_override("nope")  # must not raise
        assert store.get_room_override_until("nope") is None
```

- [ ] **Step 2: Run them and watch them fail**

Run:
```bash
python3 -m pytest tests/test_store.py::TestRoomOverrides -v
```
Expected: FAIL — `AttributeError: 'SmartVentStore' object has no attribute 'set_room_override'`.

- [ ] **Step 3: Add the override API to `SmartVentStore`**

Append to `store.py` inside the `SmartVentStore` class (e.g. after the room-setpoint section):

```python
    # -- per-room conditioning overrides ------------------------------------

    def set_room_override(self, room_key: str, until_ts: float) -> None:
        self._data.setdefault("room_overrides", {})[room_key] = {"until": until_ts}

    def clear_room_override(self, room_key: str) -> None:
        self._data.setdefault("room_overrides", {}).pop(room_key, None)

    def get_room_override_until(self, room_key: str) -> float | None:
        info = self._data.get("room_overrides", {}).get(room_key)
        if not info:
            return None
        until = info.get("until")
        return float(until) if until is not None else None
```

- [ ] **Step 4: Run the store tests to confirm they pass**

Run:
```bash
python3 -m pytest tests/test_store.py::TestRoomOverrides -v
```
Expected: PASS.

- [ ] **Step 5: Refactor the coordinator to use the API**

In `coordinator.py`, replace `set_room_override` and `is_room_overridden` (lines ~356-376) with:

```python
    def set_room_override(
        self, room_key: str, enabled: bool, duration_min: int = 60
    ) -> None:
        """Override (or clear) a room's conditioning for *duration_min* minutes."""
        if enabled:
            until = dt_util.utcnow().timestamp() + duration_min * 60
            self.store.set_room_override(room_key, until)
        else:
            self.store.clear_room_override(room_key)

    def is_room_overridden(self, room_key: str) -> bool:
        until = self.store.get_room_override_until(room_key)
        if until is None:
            return False
        if dt_util.utcnow().timestamp() > until:
            self.store.clear_room_override(room_key)
            return False
        return True
```

(`dt_util` was imported in Task 9, Step 6.)

- [ ] **Step 6: Refactor `binary_sensor.py` to use the API**

In `binary_sensor.py`, replace `RoomOverrideActiveSensor.extra_state_attributes` (lines ~150-157) with:

```python
    @property
    def extra_state_attributes(self):
        until_ts = self.coordinator.store.get_room_override_until(self._room_key)
        if until_ts is not None:
            remaining = max(0, (until_ts - dt_util.utcnow().timestamp()) / 60)
            return {"remaining_minutes": round(remaining, 1)}
        return {}
```

- [ ] **Step 7: Confirm no `store._data` access remains outside `store.py`**

Run:
```bash
grep -rn "store._data\|\.store\._data" custom_components/smart_vent_controller --include='*.py' | grep -v '/store.py:' && echo "STILL LEAKING" || echo "ENCAPSULATED"
```
Expected: `ENCAPSULATED`

- [ ] **Step 8: Run the full suite**

Run:
```bash
python3 -m pytest -v
```
Expected: all PASS.

- [ ] **Step 9: Commit**

```bash
git add custom_components/smart_vent_controller/store.py custom_components/smart_vent_controller/coordinator.py custom_components/smart_vent_controller/binary_sensor.py tests/test_store.py
git commit -m "refactor: encapsulate room overrides behind a store API

Coordinator and binary_sensor no longer reach into store._data.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Phase 4 — Coverage depth

### Task 13: Behavioral coordinator tests

**Files:**
- Modify: `tests/test_coordinator.py` (add cases)

- [ ] **Step 1: Write rooms-to-condition and override-expiry tests**

Append to `tests/test_coordinator.py`:

```python
from freezegun import freeze_time
from datetime import timedelta


async def test_rooms_to_condition_selects_rooms_below_target_in_heat(hass):
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

    # require_occupancy defaults True in options-less entry path; set it off here.
    coordinator.config_entry.options = {"require_occupancy": False, "room_hysteresis_f": 1.0}

    result = coordinator.get_rooms_to_condition_value()
    assert "cold_room" in result.split(",")


async def test_override_expires_after_duration(hass):
    entry = _make_entry([])
    entry.add_to_hass(hass)
    coordinator = SmartVentControllerCoordinator(hass, entry)
    await coordinator.async_initialize()

    with freeze_time("2026-06-16 12:00:00") as frozen:
        coordinator.set_room_override("guest_room", enabled=True, duration_min=60)
        assert coordinator.is_room_overridden("guest_room") is True

        frozen.tick(timedelta(minutes=61))
        assert coordinator.is_room_overridden("guest_room") is False
```

- [ ] **Step 2: Run the coordinator tests**

Run:
```bash
python3 -m pytest tests/test_coordinator.py -v
```
Expected: all PASS. If `get_rooms_to_condition_value` reads options via `config_entry.options.get(...)` and the assignment in the test does not take effect, set the options through `hass.config_entries.async_update_entry(entry, options={...})` instead and re-run.

- [ ] **Step 3: Run the full suite**

Run:
```bash
python3 -m pytest -v
```
Expected: all PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/test_coordinator.py
git commit -m "test: cover rooms-to-condition selection and override expiry

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 14: Document follow-on coverage gaps

**Files:**
- Modify: `docs/TESTING_GUIDE.md`

- [ ] **Step 1: Add a "Coverage status & gaps" section**

Append to `docs/TESTING_GUIDE.md`:

```markdown
## Coverage status & gaps (2026-06-16)

Covered by automated tests:
- `algorithm.py` — pure vent-math functions, including `is_night_time`.
- `store.py` — persistence properties, efficiency rates, room overrides.
- `error_handling.py` — rolling error window.
- `coordinator.py` — per-room failure isolation, rooms-to-condition selection,
  room-override expiry.

Known follow-on gaps (not yet covered, tracked for future work):
- `config_flow.py` (~857 lines): the setup wizard, reconfigure, and options
  menus have no automated tests.
- `scripts.py` (~609 lines): the vent and thermostat control execution paths.

These are the highest-value next targets for behavioral coverage.
```

- [ ] **Step 2: Commit**

```bash
git add docs/TESTING_GUIDE.md
git commit -m "docs: record test coverage status and remaining gaps

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Final verification

- [ ] **Run the whole suite one last time**

Run:
```bash
python3 -m pytest -v
```
Expected: all tests PASS, zero collection errors.

- [ ] **Confirm no naive datetime or store leak remains**

Run:
```bash
grep -rn "datetime.now()" custom_components/smart_vent_controller --include='*.py' || echo "NO NAIVE NOW"
grep -rn "store._data" custom_components/smart_vent_controller --include='*.py' | grep -v '/store.py:' || echo "NO STORE LEAK"
```
Expected: `NO NAIVE NOW` and `NO STORE LEAK`.

- [ ] **Push the branch and open a PR** (only when the user asks)

```bash
git push -u origin hardening/hacs-publish-quality
```
Then confirm GitHub Actions (Validate + Tests) go green on the PR.

---

## Self-review notes (author)

- **Spec coverage:** Phase 1 → Tasks 1-4 (hygiene, docs/examples move, manifest/hacs, hassfest+HACS CI). Phase 2 → Tasks 5-8 (harness, conftest, port tests, pytest CI+badges). Phase 3 → Tasks 9-12 (datetime incl. day/night bug, per-room isolation, store override API incl. binary_sensor leak). Phase 4 → Tasks 13-14 (coordinator tests, documented gaps). All spec findings #1-#7 map to a task.
- **No placeholders:** the only intentional fill-in is the exact harness version in Task 5, which is captured mechanically via `pip install` + version print rather than guessed.
- **Type/name consistency:** `is_night_time`, `_read_room_into`, `set_room_override`/`clear_room_override`/`get_room_override_until` are used with identical signatures across their defining and consuming tasks.
