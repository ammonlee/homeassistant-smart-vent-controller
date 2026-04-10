"""Tests for the SmartVentStore persistence layer."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.smart_vent_controller.store import SmartVentStore


@pytest.fixture
def mock_hass():
    hass = MagicMock()
    hass.config.path.return_value = "/tmp/ha_test"
    return hass


@pytest.fixture
def store(mock_hass):
    return SmartVentStore(mock_hass, "test_entry_123")


class TestStoreProperties:
    def test_defaults(self, store):
        assert store.cycle_start_ts == 0
        assert store.cycle_end_ts == 0
        assert store.last_thermostat_setpoint == 0
        assert store.hvac_last_action == "idle"
        assert store.max_running_minutes == 60.0

    def test_set_and_get_cycle_timestamps(self, store):
        store.cycle_start_ts = 1000.0
        store.cycle_end_ts = 2000.0
        assert store.cycle_start_ts == 1000.0
        assert store.cycle_end_ts == 2000.0

    def test_set_and_get_last_setpoint(self, store):
        store.last_thermostat_setpoint = 72.5
        assert store.last_thermostat_setpoint == 72.5

    def test_set_and_get_hvac_action(self, store):
        store.hvac_last_action = "heating"
        assert store.hvac_last_action == "heating"


class TestEfficiencyRates:
    def test_default_zero(self, store):
        assert store.get_heating_rate("bedroom") == 0
        assert store.get_cooling_rate("bedroom") == 0

    def test_set_and_get(self, store):
        store.set_heating_rate("bedroom", 0.15)
        store.set_cooling_rate("bedroom", 0.12)
        assert store.get_heating_rate("bedroom") == 0.15
        assert store.get_cooling_rate("bedroom") == 0.12

    def test_effective_rate_heating(self, store):
        store.set_heating_rate("room_a", 0.2)
        assert store.get_effective_rate("room_a", "heating") == 0.2
        assert store.get_effective_rate("room_a", "heat") == 0.2

    def test_effective_rate_cooling(self, store):
        store.set_cooling_rate("room_a", 0.18)
        assert store.get_effective_rate("room_a", "cooling") == 0.18
        assert store.get_effective_rate("room_a", "cool") == 0.18


class TestCycleStartTemps:
    def test_set_and_get(self, store):
        store.set_cycle_start_temp("bedroom", 68.5)
        assert store.get_cycle_start_temp("bedroom") == 68.5

    def test_clear(self, store):
        store.set_cycle_start_temp("bedroom", 68.5)
        store.clear_cycle_start_temps()
        assert store.get_cycle_start_temp("bedroom") is None


class TestVentLastAdjusted:
    def test_default_zero(self, store):
        assert store.get_vent_last_adjusted("cover.vent_1") == 0

    def test_set_and_get(self, store):
        store.set_vent_last_adjusted("cover.vent_1", 12345.0)
        assert store.get_vent_last_adjusted("cover.vent_1") == 12345.0


class TestExportImport:
    def test_export_empty(self, store):
        data = store.export_efficiency()
        assert data == {
            "heating_rates": {},
            "cooling_rates": {},
            "max_running_minutes": 60.0,
        }

    def test_roundtrip(self, store):
        store.set_heating_rate("a", 0.1)
        store.set_cooling_rate("b", 0.2)
        store.max_running_minutes = 45.0

        exported = store.export_efficiency()

        store2 = SmartVentStore(MagicMock(), "other")
        store2.import_efficiency(exported)

        assert store2.get_heating_rate("a") == 0.1
        assert store2.get_cooling_rate("b") == 0.2
        assert store2.max_running_minutes == 45.0
