# Chat 2 — exact-v308 loadout-folder context-menu family R274

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic result

The exact contiguous family `rs/gui/b/a/n..x` is recovered as the loadout-folder popup and its action handlers:

- `n` -> `CLIENT_CLASS_000223` -> `LoadoutFolderContextMenu`
- `o` -> `CLIENT_CLASS_000224` -> `LoadoutFolderSelectAction`
- `p` -> `CLIENT_CLASS_000225` -> `CreateLoadoutFolderAction`
- `q` -> `CLIENT_CLASS_000226` -> `CreateLoadoutFolderConfirmAction`
- `r` -> `CLIENT_CLASS_000227` -> `RenameLoadoutFolderAction`
- `s` -> `CLIENT_CLASS_000228` -> `RenameLoadoutFolderConfirmAction`
- `t` -> `CLIENT_CLASS_000229` -> `MoveLoadoutFolderUpAction`
- `u` -> `CLIENT_CLASS_000230` -> `MoveLoadoutFolderDownAction`
- `v` -> `CLIENT_CLASS_000231` -> `DeleteLoadoutFolderAction`
- `w` -> `CLIENT_CLASS_000232` -> `DeleteLoadoutFolderConfirmAction`
- `x` -> `CLIENT_CLASS_000233` -> `DeleteLoadoutFolderCancelAction`

Review: `SEMREVIEW_50670910A3BA6ACA99FE`

## Exact evidence

The already-reviewed `LoadoutFolderPanel` directly calls `rs/gui/b/a/n.a(panel)` to install its popup.

The popup is titled **Loadout folders** and creates exact actions **Create new folder**, **Rename**, **Move up**, **Move down**, and **Delete**. It loads matching folder/create/delete/edit/up/down icon assets.

The attached listeners are structurally exact:

- selection highlights the chosen menu item and selects the corresponding model folder;
- creation opens **Name Your Folder** and its confirmation handler inserts the text-field value;
- rename opens **Re-name Your Folder** and its confirmation handler renames the selected model key;
- move-up and move-down locate the preceding/following key and reorder the selected folder;
- delete opens a confirmation UI, with one handler deleting the selected folder and the other only closing the dialog.

These are descriptive semantic names backed by exact behavior. R274 does **not** claim recovery of stripped original source identifiers.

## Boundary

R274 remains non-canonical. Chat 2 performs no semantic acceptance or rewrite.
