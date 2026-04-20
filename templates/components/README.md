# Template components

Reusable partials, included via `{% include "components/<name>.html" with ... %}`.

Each file owns one UI concern and reads only from `with` kwargs — no direct access
to request or user unless explicitly documented. Populated in Phase 2.
