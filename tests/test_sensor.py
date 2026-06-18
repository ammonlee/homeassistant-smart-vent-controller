"""Tests for sensor entity registry defaults and attributes."""
from custom_components.smart_vent_controller.sensor import (
    RoomDeltaSensor,
    RoomEfficiencySensor,
    HVACCycleStartTimeSensor,
    HVACCycleEndTimeSensor,
)

# Home Assistant's Entity metaclass stores `_attr_entity_registry_enabled_default = X`
# as the literal key `__attr_entity_registry_enabled_default` in the class __dict__.
# When the line is absent the key is missing and the entity is enabled by default.
_ENABLED_KEY = "__attr_entity_registry_enabled_default"


def test_delta_and_efficiency_enabled_by_default():
    # Neither class should carry an explicit disable flag.
    assert _ENABLED_KEY not in RoomDeltaSensor.__dict__, (
        "RoomDeltaSensor has _attr_entity_registry_enabled_default set — "
        "remove it so the sensor is enabled by default"
    )
    assert _ENABLED_KEY not in RoomEfficiencySensor.__dict__, (
        "RoomEfficiencySensor has _attr_entity_registry_enabled_default set — "
        "remove it so the sensor is enabled by default"
    )


def test_cycle_timestamp_sensors_disabled_by_default():
    assert HVACCycleStartTimeSensor.__dict__.get(_ENABLED_KEY) is False
    assert HVACCycleEndTimeSensor.__dict__.get(_ENABLED_KEY) is False


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
