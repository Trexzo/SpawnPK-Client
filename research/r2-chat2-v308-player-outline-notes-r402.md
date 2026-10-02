# Chat 2 — Player Outline + Notes source identities R402

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Player Outline

- `rs/s/p/a` -> `CLIENT_CLASS_000946` -> `PlayerOutlineConfig`
- `rs/s/p/d` -> `CLIENT_CLASS_000949` -> `PlayerOutlinePlugin`

The recovered source map supplies the exact source identities.

Exact v308 corroborates them:

- config group `playeroutline`;
- outline color, pet-outline, border-width and feather settings;
- plugin startup registers the player overlay;
- pet overlay registration follows `petOutline`;
- `ConfigChanged("petOutline")` dynamically adds/removes that overlay.

## Notes

- `rs/s/m/a` -> `CLIENT_CLASS_000929` -> `NotesConfig`
- `rs/s/m/f` -> `CLIENT_CLASS_000934` -> `NotesPlugin`

Exact v308 config exposes `notesData` plus its setter.

The plugin resolves the Notes panel, supplies the config, loads `notes_icon.png`, builds a
navigation entry titled `Notes`, attaches it to the UI on startup and removes it on shutdown.

## Boundary

Only source-mapped config/plugin entry points are recovered here. Their subordinate overlay,
panel and helper classes remain separate candidates unless independently identified.

R402 remains non-canonical semantic research only.
