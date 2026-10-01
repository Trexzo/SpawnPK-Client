# Chat 2 — launcher client panel R374

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/gui/E` -> `CLIENT_CLASS_000188` -> `LauncherClientPanel`
- proposal: `SEMPROP_8815ED7E28F14D3E24D9`
- review: `SEMREVIEW_4606D0C64492811B1F89`

## Exact role

Launcher constructs one `rs/gui/E`, sizes it to the client viewport and configures it as a
black BorderLayout panel.

After the live `rs/Client` is initialized and started, Launcher inserts that Client
component directly into this panel at `BorderLayout.CENTER`.

The panel is then mounted in the launcher window beside R373 `LauncherSidePanel`.

No second responsibility survives in exact v308.

## Rejected neighbor

`rs/gui/F` remains unnamed. It is a blank JPanel owned by the loadout panel and its
paintComponent override only delegates to JPanel; the class does not preserve enough semantic
behavior to justify a useful name.

R374 remains non-canonical semantic research only.
