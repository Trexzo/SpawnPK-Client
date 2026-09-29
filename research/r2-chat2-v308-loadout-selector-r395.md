# Chat 2 — exact-v308 Loadout selector widget R395

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

Recovered selector family:

- `rs/gui/b/a/f` -> `CLIENT_CLASS_000215` -> `LoadoutSelectorRenderer`
- `rs/gui/b/a/k` -> `CLIENT_CLASS_000220` -> `LoadoutSelectorComboBox`
- `rs/gui/b/a/l` -> `CLIENT_CLASS_000221` -> `LoadoutSelectorPopupListener`
- `rs/gui/b/a/m` -> `CLIENT_CLASS_000222` -> `LoadoutSelectionAction`

The combo box is embedded only by R390 `LoadoutsPanel`. Its renderer decorates each loadout
with the reviewed LoadoutDefinition color/icon state. The action listener changes the active
loadout index inside the current folder, while the popup listener synchronizes/repaints the
panel around popup visibility changes.

R395 remains non-canonical semantic research only.
