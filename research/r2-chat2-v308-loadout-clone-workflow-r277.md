# Chat 2 — exact-v308 loadout clone workflow R277

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic result

- `rs/gui/b/a/b` -> `CLIENT_CLASS_000211` -> `LoadoutCloneConfirmationAction`
- `rs/gui/b/a/c` -> `CLIENT_CLASS_000212` -> `LoadoutCloneCurrentEquipmentAction`
- `rs/gui/b/a/d` -> `CLIENT_CLASS_000213` -> `LoadoutCloneCancelAction`
- `rs/gui/b/a/e` -> `CLIENT_CLASS_000214` -> `LoadoutColorListCellRenderer`
- review: `SEMREVIEW_BB147E24A24F9E143572`
- unresolved: **0**
- field/method proposals: **0**

## Exact-v308 evidence

R276 recovered the Clone button factory and loadout-properties frame. R277 follows only their direct exact-v308 dependencies.

### Clone confirmation

`rs/gui/b/a/b` resolves the current loadout. With no selection it shows **You don't have a loadout selected!**. Otherwise it opens **Clone to <loadout>?**, creates **Yes** and **No** buttons, and installs `rs/gui/b/a/c` and `rs/gui/b/a/d` respectively. This makes the class the clone-confirmation action, not the mutation itself.

### Clone current equipment

`rs/gui/b/a/c` is the Yes listener. It clears the selected loadout's prior equipment state and copies live character state from the client, including inventory/equipment widget contents at **3214** and **1688**, combat/appearance selections, and the loadout skill set. Skill values are copied through the loadout skill-index table and clamped to **1..99**. It refreshes/persists the loadout views, writes `Client.ap = "::cldt"`, and closes the dialog. If no character is logged in it displays the exact retry message telling the player to log in, wear what they want to clone, and try again.

### Cancel

`rs/gui/b/a/d` is the No listener and only hides/disposes the confirmation frame.

### Color renderer

`rs/gui/b/a/e` extends `DefaultListCellRenderer`, owns parallel `Color[]` and `String[]` values, validates matching lengths, and paints the label foreground with the matching color. R276 `LoadoutPropertiesFrame` directly constructs it for the loadout **Color:** combo box.

## Boundary

R277 is non-canonical research only. The batch does not accept semantic names or rewrite the client. Its regression check includes **R2** as well as every later retained Chat 2 review.
