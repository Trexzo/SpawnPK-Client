# Chat 2 — source-identified GUI window core R403

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/gui/d` -> `CLIENT_CLASS_000264` -> `ColorScheme`
- `rs/gui/u` -> `CLIENT_CLASS_000281` -> `ClientFrame`
- `rs/gui/u$a` -> `CLIENT_CLASS_000282` -> `ContainMode`
- `rs/gui/v` -> `CLIENT_CLASS_000283` -> `ResizeType`
- `rs/gui/N` -> `CLIENT_CLASS_000198` -> `TrayMouseListener`

Review: `SEMREVIEW_D3BE7752E2F6CDEDE22F`.

The recovered semantic source map supplies all five source identities. Exact v308 independently
corroborates them:

- ColorScheme is a static java.awt.Color palette.
- ClientFrame directly extends JFrame and owns monitor/bounds/scale/resize/contain logic.
- ContainMode constants are ALWAYS, RESIZING and NEVER.
- ResizeType constants are KEEP_WINDOW_SIZE and KEEP_GAME_SIZE with matching labels.
- TrayMouseListener extends MouseAdapter and restores/shows its captured Frame on click.

R403 remains non-canonical semantic research only.
