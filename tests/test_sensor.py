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
