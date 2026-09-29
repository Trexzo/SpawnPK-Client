# Chat 2 — exact-v308 Loadouts panel helpers R391

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R390 fixes `rs/gui/b/h` as `LoadoutsPanel`. R391 recovers six single-purpose helpers attached directly to that panel:

- `rs/gui/b/i` -> `CLIENT_CLASS_000251` -> `LoadoutFolderPopupMouseHandler`
- `rs/gui/b/l` -> `CLIENT_CLASS_000254` -> `RenameLoadoutAction`
- `rs/gui/b/m` -> `CLIENT_CLASS_000255` -> `RenameLoadoutCommitAction`
- `rs/gui/b/n` -> `CLIENT_CLASS_000256` -> `MoveLoadoutUpAction`
- `rs/gui/b/o` -> `CLIENT_CLASS_000257` -> `MoveLoadoutDownAction`
- `rs/gui/b/p` -> `CLIENT_CLASS_000258` -> `LoadoutEquipmentSlotMouseHandler`

## Exact attachment strings

The parent panel binds these helpers to exact UI vocabulary:

- `<html>Loadout folders</html>`
- `Rename the active loadout`
- `Move loadout up in the list`
- `Move loadout down in the list`

The rename launcher opens the exact `Rename` dialog; its paired commit action writes the edited name/color/icon through LoadoutManager.

The equipment-slot mouse handler maps seven fixed panel regions to slot indexes 0..6 and opens the owned slot editor for the clicked index.

## Withheld adjacent helpers

`rs/gui/b/j` and `rs/gui/b/k` are not included here. They are generic confirm/cancel listeners for a secondary frame and do not retain enough standalone semantic context to justify stronger names.

R391 remains non-canonical semantic research only.
