# Chat 2 — Loadout folder and selector controls R376

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R376 closes the meaningful remaining `rs/gui/b/a/*` selector/folder controls:

- `f` -> `LoadoutSelectorListCellRenderer`
- `k` -> `LoadoutSelectorComboBox`
- `l` -> `LoadoutSelectorPopupListener`
- `m` -> `LoadoutSelectionAction`
- `n` -> `LoadoutFolderMenuFactory`
- `o` -> `LoadoutFolderSelectAction`
- `p/q` -> folder create + commit
- `r/s` -> folder rename + commit
- `t/u` -> folder move up/down
- `v/w/x` -> folder delete + confirm/cancel

Review: `SEMREVIEW_A2484E9A590A5C459C14`

The exact JPopupMenu is titled 'Loadout folders' and contains the visible actions
'Create new folder', 'Rename', 'Move up', 'Move down' and 'Delete'. The selector renderer
projects each LoadoutDefinition's color/icon while selection changes are committed through
LoadoutManager.

Together with R143/R144/R181/R345/R346/R373/R374/R375, this leaves the Loadout GUI family
almost entirely semantically covered.

R376 remains non-canonical semantic research only.
