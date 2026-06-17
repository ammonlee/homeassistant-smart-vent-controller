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
