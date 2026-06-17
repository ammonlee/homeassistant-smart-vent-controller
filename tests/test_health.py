"""Tests for health repair-issue evaluation."""
from pytest_homeassistant_custom_component.common import MockConfigEntry
from homeassistant.helpers import issue_registry as ir

from custom_components.smart_vent_controller.const import DOMAIN
from custom_components.smart_vent_controller.health import evaluate_health_issues


def _entry(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "main_thermostat": "climate.main",
            "rooms": [{"name": "Den", "vent_entities": ["cover.den_vent"]}],
        },
        options={},
    )
    entry.add_to_hass(hass)
    return entry


async def test_no_issue_when_all_available(hass):
    entry = _entry(hass)
    hass.states.async_set("climate.main", "heat")
    hass.states.async_set("cover.den_vent", "open")
    evaluate_health_issues(hass, entry, {}, 1000.0)
    reg = ir.async_get(hass)
    assert (DOMAIN, f"vents_unavailable_{entry.entry_id}") not in reg.issues
    assert (DOMAIN, f"thermostat_unavailable_{entry.entry_id}") not in reg.issues


async def test_vent_issue_only_after_debounce(hass):
    entry = _entry(hass)
    hass.states.async_set("climate.main", "heat")
    hass.states.async_set("cover.den_vent", "unavailable")
    since = {}
    evaluate_health_issues(hass, entry, since, 1000.0)
    reg = ir.async_get(hass)
    key = (DOMAIN, f"vents_unavailable_{entry.entry_id}")
    assert key not in reg.issues
    evaluate_health_issues(hass, entry, since, 1000.0 + 240)
    assert key not in reg.issues
    evaluate_health_issues(hass, entry, since, 1000.0 + 300)
    assert key in reg.issues


async def test_vent_issue_clears_on_recovery(hass):
    entry = _entry(hass)
    hass.states.async_set("climate.main", "heat")
    hass.states.async_set("cover.den_vent", "unavailable")
    since = {}
    evaluate_health_issues(hass, entry, since, 1000.0)
    evaluate_health_issues(hass, entry, since, 1000.0 + 300)
    reg = ir.async_get(hass)
    key = (DOMAIN, f"vents_unavailable_{entry.entry_id}")
    assert key in reg.issues
    hass.states.async_set("cover.den_vent", "open")
    evaluate_health_issues(hass, entry, since, 1000.0 + 360)
    assert key not in reg.issues


async def test_thermostat_issue_is_error(hass):
    entry = _entry(hass)
    hass.states.async_set("climate.main", "unavailable")
    hass.states.async_set("cover.den_vent", "open")
    since = {}
    evaluate_health_issues(hass, entry, since, 1000.0)
    evaluate_health_issues(hass, entry, since, 1000.0 + 300)
    reg = ir.async_get(hass)
    issue = reg.async_get_issue(DOMAIN, f"thermostat_unavailable_{entry.entry_id}")
    assert issue is not None
    assert issue.severity == ir.IssueSeverity.ERROR
