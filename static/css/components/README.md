# Component stylesheets

Each file owns one concern and uses BEM-ish class names (`.btn`, `.btn--primary`, `.btn--ghost`).
All values must come from tokens in `../tokens.css` — never hardcode colors, spacing, radii or shadows here.

Load order in `base.html`:
1. `tokens.css`
2. component files from this folder
3. `style.css` (legacy, being drained over time)

Populated in Phase 2. Stub files exist so imports resolve without 404s.
