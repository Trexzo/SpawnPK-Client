# Chat 2 — Loadout sidebar control surface R374

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/gui/b/a/A` -> `CLIENT_CLASS_000207` -> `LoadoutSkillLevelEditor`
- `rs/gui/b/h` -> `CLIENT_CLASS_000250` -> `LoadoutSidebarPanel`
- `rs/gui/b/i` -> `CLIENT_CLASS_000251` -> `LoadoutFolderPopupMouseHandler`
- `rs/gui/b/j` -> `CLIENT_CLASS_000252` -> `LoadoutDeleteConfirmAction`
- `rs/gui/b/k` -> `CLIENT_CLASS_000253` -> `LoadoutDeleteCancelAction`
- `rs/gui/b/l` -> `CLIENT_CLASS_000254` -> `LoadoutRenameAction`
- `rs/gui/b/m` -> `CLIENT_CLASS_000255` -> `LoadoutRenameCommitAction`
- `rs/gui/b/n` -> `CLIENT_CLASS_000256` -> `LoadoutMoveUpAction`
- `rs/gui/b/o` -> `CLIENT_CLASS_000257` -> `LoadoutMoveDownAction`
- `rs/gui/b/p` -> `CLIENT_CLASS_000258` -> `LoadoutSkillLevelMouseHandler`

Review: `SEMREVIEW_79704318FC6BB5F6D955`

R145 already fixes the parent sidebar shell; R143/R144/R345/R373 fix the manager,
persistence, definition, preview, item-entry and icon pipeline used by this panel.

The exact UI exposes folder management, loadout create/delete/rename/reorder controls and a
seven-skill level editor. Skill values are clamped to 1..99 and map exactly to Attack,
Range, Strength, Prayer, Defence, Magic and Hitpoints.

R374 remains non-canonical semantic research only.
