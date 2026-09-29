# Chat 2 — exact-v308 Loadouts create workflow R393

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/gui/b/a/g` -> `CLIENT_CLASS_000216` -> `CreateLoadoutButton`
- `rs/gui/b/a/h` -> `CLIENT_CLASS_000217` -> `OpenCreateLoadoutAction`
- `rs/gui/b/a/i` -> `CLIENT_CLASS_000218` -> `CreateLoadoutCommitAction`
- review: `SEMREVIEW_069F232B0089C0EE81A0`

The create button opens R392 `LoadoutMetadataEditorDialog` with exact strings
`Name Your Loadout` and `Create`.

Its commit listener reads the new name, creates the loadout through LoadoutManager, copies the
selected icon/color into the new LoadoutDefinition and refreshes the active folder.

The intermediate ActionListener only opens that create dialog and has no second responsibility.

R393 remains non-canonical semantic research only.
