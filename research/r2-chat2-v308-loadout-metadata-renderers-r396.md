# Chat 2 — exact-v308 Loadout metadata selector renderers R396

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

- `rs/gui/b/a/e` -> `CLIENT_CLASS_000214` -> `LoadoutColorSelectorRenderer`
- `rs/gui/b/a/j` -> `CLIENT_CLASS_000219` -> `LoadoutIconSelectorRenderer`

Both are owned exclusively by R392 `LoadoutMetadataEditorDialog`.

The color renderer paints each configured label with the corresponding color. The icon renderer
maps LoadoutIcon values to their icons and preserves the exact special entry `None (Default)`
without an icon.

R396 remains non-canonical semantic research only.
