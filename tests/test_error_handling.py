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
