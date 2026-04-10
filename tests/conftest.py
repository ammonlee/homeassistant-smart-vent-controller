"""Shared fixtures for tests.

The algorithm and store modules have minimal HA dependencies (algorithm has
none, store only needs homeassistant.helpers.storage.Store).  We stub just
enough so ``importlib.import_module`` succeeds without HA installed.
"""
import importlib
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))


def _ensure_stub(name):
    """Create an empty module stub and wire it into sys.modules."""
    if name in sys.modules:
        return sys.modules[name]
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    parts = name.split(".")
    if len(parts) > 1:
        parent = ".".join(parts[:-1])
        _ensure_stub(parent)
        setattr(sys.modules[parent], parts[-1], mod)
    return mod


# Create stubs for every homeassistant submodule our code imports at top-level.
_HA_STUBS = [
    "homeassistant",
    "homeassistant.config_entries",
    "homeassistant.const",
    "homeassistant.core",
    "homeassistant.data_entry_flow",
    "homeassistant.exceptions",
    "homeassistant.helpers",
    "homeassistant.helpers.device_registry",
    "homeassistant.helpers.entity_platform",
    "homeassistant.helpers.entity_registry",
    "homeassistant.helpers.event",
    "homeassistant.helpers.restore_state",
    "homeassistant.helpers.selector",
    "homeassistant.helpers.service",
    "homeassistant.helpers.storage",
    "homeassistant.helpers.template",
    "homeassistant.helpers.translation",
    "homeassistant.helpers.update_coordinator",
    "homeassistant.components",
    "homeassistant.components.binary_sensor",
    "homeassistant.components.number",
    "homeassistant.components.sensor",
    "homeassistant.components.switch",
]
for _name in _HA_STUBS:
    _ensure_stub(_name)

# Populate names that are imported at module level.
_const = sys.modules["homeassistant.const"]
_const.Platform = type("Platform", (), {
    "SENSOR": "sensor", "BINARY_SENSOR": "binary_sensor",
    "NUMBER": "number", "SWITCH": "switch",
})
_const.UnitOfTemperature = type("UnitOfTemperature", (), {"FAHRENHEIT": "°F"})
_const.EVENT_STATE_CHANGED = "state_changed"

# Core stubs
_core = sys.modules["homeassistant.core"]
_core.HomeAssistant = type("HomeAssistant", (), {})
_core.callback = lambda f: f

# Config entries
_ce = sys.modules["homeassistant.config_entries"]
_ce.ConfigEntry = type("ConfigEntry", (), {})
_ce.OptionsFlow = type("OptionsFlow", (), {})

class _FakeConfigFlow:
    class ConfigFlow:
        pass
    @staticmethod
    def __init_subclass__(**kw):
        pass
_ce.ConfigFlow = type("ConfigFlow", (), {"__init_subclass__": lambda **kw: None})

# Exceptions
sys.modules["homeassistant.exceptions"].HomeAssistantError = Exception

# data_entry_flow
sys.modules["homeassistant.data_entry_flow"].FlowResult = dict

# Storage
class _StoreStub:
    def __init__(self, *a, **kw):
        self._data = {}
    async def async_load(self):
        return self._data
    async def async_save(self, data):
        self._data = data
sys.modules["homeassistant.helpers.storage"].Store = _StoreStub

# Update coordinator
class _CoordStub:
    def __init__(self, *a, **kw):
        self.update_interval = None
_CoordStub.__init_subclass__ = classmethod(lambda cls, **kw: None)
sys.modules["homeassistant.helpers.update_coordinator"].DataUpdateCoordinator = _CoordStub
sys.modules["homeassistant.helpers.update_coordinator"].UpdateFailed = Exception

# Event helpers
_ev = sys.modules["homeassistant.helpers.event"]
_ev.async_track_state_change = lambda *a, **kw: lambda: None
_ev.async_track_time_interval = lambda *a, **kw: lambda: None

# Sensor / binary_sensor / number / switch platform base classes
sys.modules["homeassistant.components.sensor"].SensorEntity = type("SensorEntity", (), {})
sys.modules["homeassistant.components.sensor"].SensorStateClass = type(
    "SensorStateClass", (), {"MEASUREMENT": "measurement"}
)
sys.modules["homeassistant.components.binary_sensor"].BinarySensorEntity = type(
    "BinarySensorEntity", (), {}
)
sys.modules["homeassistant.components.number"].NumberEntity = type("NumberEntity", (), {})
sys.modules["homeassistant.components.number"].NumberMode = type(
    "NumberMode", (), {"BOX": "box", "SLIDER": "slider"}
)
sys.modules["homeassistant.components.switch"].SwitchEntity = type("SwitchEntity", (), {})

# Restore state, device registry, entity platform, selector
sys.modules["homeassistant.helpers.restore_state"].RestoreEntity = type("RestoreEntity", (), {})
sys.modules["homeassistant.helpers.device_registry"].DeviceInfo = dict
sys.modules["homeassistant.helpers.device_registry"].async_get = lambda hass: MagicMock()
sys.modules["homeassistant.helpers.entity_platform"].AddEntitiesCallback = None
sys.modules["homeassistant.helpers.entity_registry"].async_get = lambda hass: MagicMock()

# Selector stubs
_sel = sys.modules["homeassistant.helpers.selector"]
_sel.EntitySelector = lambda *a, **kw: None
_sel.EntitySelectorConfig = lambda *a, **kw: {}
_sel.NumberSelector = lambda *a, **kw: None
_sel.NumberSelectorConfig = lambda *a, **kw: {}
_sel.NumberSelectorMode = type("NumberSelectorMode", (), {"SLIDER": "slider"})

# Voluptuous
if "voluptuous" not in sys.modules:
    _vol = types.ModuleType("voluptuous")
    _vol.Schema = lambda *a, **kw: None
    _vol.Required = lambda *a, **kw: a[0]
    _vol.Optional = lambda *a, **kw: a[0]
    _vol.All = lambda *a: a[0]
    _vol.Range = lambda **kw: None
    _vol.In = lambda x: x
    sys.modules["voluptuous"] = _vol
