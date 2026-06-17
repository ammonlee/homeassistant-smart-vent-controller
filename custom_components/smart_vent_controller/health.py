"""Health evaluation and Home Assistant Repairs issue management."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN

HEALTH_DEBOUNCE_SEC = 300.0


def _is_unavailable(hass: HomeAssistant, entity_id: str) -> bool:
    state = hass.states.get(entity_id)
    return state is None or state.state == "unavailable"


def compute_unavailable_entities(
    hass: HomeAssistant, entry: ConfigEntry
) -> tuple[str | None, list[str]]:
    """Return (unavailable_thermostat_or_None, [unavailable_vent_ids])."""
    main = entry.data.get("main_thermostat")
    bad_thermo = main if (main and _is_unavailable(hass, main)) else None

    bad_vents: list[str] = []
    for room in entry.data.get("rooms", []):
        for vent in room.get("vent_entities", []):
            if _is_unavailable(hass, vent):
                bad_vents.append(vent)
    return bad_thermo, bad_vents


def evaluate_health_issues(
    hass: HomeAssistant,
    entry: ConfigEntry,
    unavailable_since: dict[str, float],
    now_ts: float,
    debounce_sec: float = HEALTH_DEBOUNCE_SEC,
) -> None:
    """Raise/clear Repairs issues for unavailable entities, with debounce.

    *unavailable_since* maps entity_id -> first-seen-unavailable timestamp and is
    mutated in place so debounce state persists across calls.
    """
    bad_thermo, bad_vents = compute_unavailable_entities(hass, entry)
    eid = entry.entry_id

    # -- thermostat (ERROR) --
    thermo_issue = f"thermostat_unavailable_{eid}"
    main = entry.data.get("main_thermostat")
    if bad_thermo:
        since = unavailable_since.setdefault(bad_thermo, now_ts)
        if now_ts - since >= debounce_sec:
            ir.async_create_issue(
                hass, DOMAIN, thermo_issue,
                is_fixable=False,
                severity=ir.IssueSeverity.ERROR,
                translation_key="thermostat_unavailable",
                translation_placeholders={"entity_id": bad_thermo},
            )
    else:
        if main:
            unavailable_since.pop(main, None)
        ir.async_delete_issue(hass, DOMAIN, thermo_issue)

    # -- vents (WARNING, aggregate) --
    vents_issue = f"vents_unavailable_{eid}"
    all_vents = [
        v for room in entry.data.get("rooms", [])
        for v in room.get("vent_entities", [])
    ]
    bad_set = set(bad_vents)
    for v in all_vents:
        if v in bad_set:
            unavailable_since.setdefault(v, now_ts)
        else:
            unavailable_since.pop(v, None)

    aged = sorted(
        v for v in bad_vents
        if now_ts - unavailable_since.get(v, now_ts) >= debounce_sec
    )
    if aged:
        ir.async_create_issue(
            hass, DOMAIN, vents_issue,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="vents_unavailable",
            translation_placeholders={
                "count": str(len(aged)),
                "entities": ", ".join(aged),
            },
        )
    else:
        ir.async_delete_issue(hass, DOMAIN, vents_issue)
