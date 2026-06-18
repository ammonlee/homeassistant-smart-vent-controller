# Changelog

## Unreleased

### Added
- Per-room **Comfortable** binary sensor — on when the room is within its
  hysteresis band (mode-independent), unknown when temperature/target is missing.
- Learning **confidence** on the Efficiency sensor: `heating_samples` /
  `cooling_samples` counts plus a `confidence` level (none / low / medium / high).
- `reset_efficiency` service to clear learned rates and sample counts for one room
  or all rooms.
- Home Assistant **Repairs** issues when the main thermostat (error) or one or more
  vents (warning) stay unavailable for 5+ minutes; they auto-clear on recovery and
  are removed when the integration is unloaded.

### Fixed
- **`override_room` now actually excludes a room from conditioning.** Previously
  the service stored the override and updated the `{Room} Override Active` sensor
  but had no effect on control — overridden rooms were still targeted by the
  thermostat and still had their vents driven. They are now excluded from
  conditioning selection (and `{Room} Conditioning Active` reports correctly).
  If you relied on the old no-op behavior, overridden rooms will now stop being
  conditioned as documented.
- **Genuinely cold/hot room readings are no longer silently discarded.** The
  current-temperature plausibility band widened from 40–100 °F to 32–110 °F, so a
  room reading (for example) 38 °F during a cold snap can still be selected for
  heating. User-chosen setpoint limits are unchanged.

### Changed
- Efficiency `export_efficiency` / `import_efficiency` services now perform file
  I/O in an executor instead of on the event loop.
- The Delta and Efficiency sensors are now enabled by default. (Home Assistant only
  applies this at first registration, so it affects new installs and newly-added
  rooms; existing entities keep their current enabled/disabled state.)
