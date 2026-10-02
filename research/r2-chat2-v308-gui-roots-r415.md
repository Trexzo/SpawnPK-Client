# Chat 2 — source-proven GUI roots R415

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

Recovered:

- `rs/gui/M` / 000196 -> `UiUtils`
- `rs/gui/N` / 000197 -> `TrayMouseListener`
- `rs/gui/d` / 000263 -> `ColorScheme`
- `rs/gui/u` / 000280 -> `ClientFrame`
- `rs/gui/u$a` / 000281 -> `ContainMode`
- `rs/gui/v` / 000282 -> `ResizeType`

Review: `SEMREVIEW_25C30BA83850CAF48CA4`.

The exact-v308 structures independently match the source names: Swing utility helpers,
tray mouse handling, shared colors, JFrame geometry/mode control and the two frame-policy enums.

R415 remains non-canonical semantic research only.
