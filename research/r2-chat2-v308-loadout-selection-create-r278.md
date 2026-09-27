# Chat 2 — exact-v308 loadout selection/create UI family R278

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic result

R278 fills the previously unowned exact-v308 loadout GUI coordinates between the already-reviewed R277 clone workflow and R274 folder-context family, plus the shared close handler owned by R276 `LoadoutPropertiesFrame`.

- `rs/gui/b/a/f` -> `CLIENT_CLASS_000215` -> `LoadoutSelectionListCellRenderer`
- `rs/gui/b/a/g` -> `CLIENT_CLASS_000216` -> `CreateLoadoutButton`
- `rs/gui/b/a/h` -> `CLIENT_CLASS_000217` -> `OpenCreateLoadoutAction`
- `rs/gui/b/a/i` -> `CLIENT_CLASS_000218` -> `CreateLoadoutAction`
- `rs/gui/b/a/j` -> `CLIENT_CLASS_000219` -> `LoadoutIconListCellRenderer`
- `rs/gui/b/a/k` -> `CLIENT_CLASS_000220` -> `LoadoutSelectionComboBox`
- `rs/gui/b/a/l` -> `CLIENT_CLASS_000221` -> `LoadoutSelectionPopupListener`
- `rs/gui/b/a/m` -> `CLIENT_CLASS_000222` -> `LoadoutSelectionAction`
- `rs/gui/b/a/z` -> `CLIENT_CLASS_000235` -> `LoadoutPropertiesCloseAction`
- review: `SEMREVIEW_6802ABD5B5A7B7C30CF7`
- unresolved: **0**
- field/method proposals: **0**

## Exact-v308 evidence

### Loadout selection renderer/control

`rs/gui/b/a/k` is a `JComboBox<String>` constructed by the loadout window from the current loadout-name array. It installs `rs/gui/b/a/f` as its list renderer, has preferred size **150x25**, and installs `rs/gui/b/a/l` plus `rs/gui/b/a/m` as its popup/action listeners.

`rs/gui/b/a/f` resolves the corresponding loadout record from the active loadout collection (or the current combo-box selection while rendering the selected value) and applies that loadout's stored `Color` and optional loadout icon to the Swing label.

`rs/gui/b/a/m` writes the combo-box selected index into the loadout manager for the manager's currently selected folder, then repaints the loadout window.

`rs/gui/b/a/l` owns the popup lifecycle: opening/canceling repaints the loadout window and closing invokes the window's refresh/rebuild method.

### Create-loadout flow

`rs/gui/b/a/g` is itself a `JButton`; the loadout window gives it the exact tooltip **Create a new loadout**. Its action path opens R276 `LoadoutPropertiesFrame` with exact title **Name Your Loadout** and action label **Create**.

`rs/gui/b/a/h` is the button's direct listener and delegates only to that create-frame opening method.

`rs/gui/b/a/i` is the properties-frame create listener. It asks the loadout manager to create a loadout in the current folder using the entered name, copies the selected loadout icon and color into the new record, and persists/refreshes the active folder collection.

### Loadout properties icon renderer/close handler

`rs/gui/b/a/j` is the renderer created directly by R276 `LoadoutPropertiesFrame` for its **Icon:** selector. The first exact entry is **None (Default)**; all later indices map to the loadout-icon enum and render its Swing icon.

`rs/gui/b/a/z` is appended by `LoadoutPropertiesFrame` after the caller-supplied create/rename listener. It performs no model mutation; it only hides and disposes the shared properties frame, so the same close-after-action behavior serves both create and rename flows.

## Duplicate/ownership boundary

R278 intentionally excludes:

- `rs/gui/b/a/B` and `C`, already owned by R181 as `SpawnLoadoutButtonFactory` and `SpawnLoadoutAction`;
- `rs/gui/b/a/n..x`, already owned by R274 as the loadout-folder context-menu family;
- `A/a..e/y`, already owned by R276/R277.

The branch-level uniqueness regression includes R2 through the latest retained batch, and R278's own test additionally asserts no prior owner/name overlap.

## Stable-ID boundary

Stable IDs use the canonical one-based deterministic sorted v308 `rs/**/*.class` inventory. The neighboring retained mappings (`B` -> `CLIENT_CLASS_000208`, `C` -> `...209`, `a..e` -> `...210..214`, `n` -> `...223`, `y` -> `...234`) independently bracket every R278 coordinate.

## Acceptance boundary

R278 is non-canonical research only. These names describe exact-v308 responsibilities and wiring; no stripped original source identifiers are claimed and Chat 2 performs no semantic acceptance or rewrite.
