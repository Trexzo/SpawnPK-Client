# Chat 2 — Loadout clone/create/editor flow R375

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

R375 recovers the remaining clone/create/editor core beneath the R374 LoadoutSidebarPanel:

- `rs/gui/b/a/a` -> `CLIENT_CLASS_000210` -> `LoadoutCloneButtonFactory`
- `rs/gui/b/a/b` -> `CLIENT_CLASS_000211` -> `LoadoutCloneAction`
- `rs/gui/b/a/c` -> `CLIENT_CLASS_000212` -> `LoadoutCloneConfirmAction`
- `rs/gui/b/a/d` -> `CLIENT_CLASS_000213` -> `LoadoutCloneCancelAction`
- `rs/gui/b/a/e` -> `CLIENT_CLASS_000214` -> `LoadoutColorListCellRenderer`
- `rs/gui/b/a/g` -> `CLIENT_CLASS_000216` -> `LoadoutCreateButton`
- `rs/gui/b/a/h` -> `CLIENT_CLASS_000217` -> `LoadoutCreateAction`
- `rs/gui/b/a/i` -> `CLIENT_CLASS_000218` -> `LoadoutCreateCommitAction`
- `rs/gui/b/a/j` -> `CLIENT_CLASS_000219` -> `LoadoutIconListCellRenderer`
- `rs/gui/b/a/y` -> `CLIENT_CLASS_000234` -> `LoadoutEditorWindow`
- `rs/gui/b/a/z` -> `CLIENT_CLASS_000235` -> `LoadoutEditorCloseAction`

Review: `SEMREVIEW_413065558FE8CA44F4EB`

The exact clone path copies the live character's equipment/inventory state into the active
LoadoutDefinition and persists it. The create path opens the exact 'Name Your Loadout'
editor with name/color/icon fields and persists a newly created definition in the current
folder.

The editor is also reused by R374 rename flow, so it is named generically rather than
CreateLoadoutWindow.

R375 remains non-canonical semantic research only.
