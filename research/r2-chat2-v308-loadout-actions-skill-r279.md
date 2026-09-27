# Chat 2 — exact-v308 loadout actions and skill editor R279

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic result

R279 recovers the eight still-unowned exact-v308 helpers immediately following the already-reviewed `LoadoutFolderPanel` (`rs/gui/b/h` / `CLIENT_CLASS_000250`).

- `rs/gui/b/i` -> `CLIENT_CLASS_000251` -> `OpenLoadoutFolderContextMenuMouseAdapter`
- `rs/gui/b/j` -> `CLIENT_CLASS_000252` -> `DeleteLoadoutConfirmAction`
- `rs/gui/b/k` -> `CLIENT_CLASS_000253` -> `DeleteLoadoutCancelAction`
- `rs/gui/b/l` -> `CLIENT_CLASS_000254` -> `RenameLoadoutAction`
- `rs/gui/b/m` -> `CLIENT_CLASS_000255` -> `RenameLoadoutConfirmAction`
- `rs/gui/b/n` -> `CLIENT_CLASS_000256` -> `MoveLoadoutUpAction`
- `rs/gui/b/o` -> `CLIENT_CLASS_000257` -> `MoveLoadoutDownAction`
- `rs/gui/b/p` -> `CLIENT_CLASS_000258` -> `LoadoutSkillLevelMouseListener`
- review: `SEMREVIEW_B22A3A1170133143FD11`
- unresolved: **0**
- field/method proposals: **0**

## Exact-v308 evidence

### Folder-menu mouse adapter

`rs/gui/b/i` extends `MouseAdapter`. On a left-button `mouseReleased`, it fetches the folder popup menu owned by `LoadoutFolderPanel` and shows it on the clicked component at `(1, 1)`.

`LoadoutFolderPanel` installs this adapter directly on the button whose exact tooltip is `<html>Loadout folders</html>`. The menu it opens is the already-reviewed R274 `LoadoutFolderContextMenu`.

### Delete-current-loadout confirmation

The delete-current-loadout flow in `LoadoutFolderPanel` creates a confirmation frame with an affirmative delete button and the exact cancellation text `No, Nevermind.`

`rs/gui/b/j` is the affirmative listener. It invokes the loadout manager delete operation with the current folder name and active loadout name, then hides and disposes the frame.

`rs/gui/b/k` is the cancellation listener. It performs no model mutation and only hides/disposes the frame.

The originating button in `LoadoutFolderPanel` has exact tooltip `Delete this loadout`.

### Rename-current-loadout flow

`rs/gui/b/l` resolves the current loadout and folder, then constructs the already-reviewed R276 `LoadoutPropertiesFrame` using exact action label `Rename`. It preloads the existing loadout name, color and icon before display.

`LoadoutFolderPanel` installs this listener on the button whose exact tooltip is `Rename the active loadout`.

`rs/gui/b/m` is the properties-frame confirm listener. It reads the replacement name, color and icon, applies color/icon to the loadout record, then invokes the manager rename operation for the current folder.

### Active-loadout ordering

`rs/gui/b/n` and `rs/gui/b/o` both first require an active loadout, then read the current loadout-selection combo-box index.

- `n` asks the manager to move that entry to `selectedIndex - 1`.
- `o` asks the manager to move that entry to `selectedIndex + 1`.

Their exact owning-button tooltips are respectively `Move loadout up in the list` and `Move loadout down in the list`.

### Seven-skill editor hit regions

`rs/gui/b/p` implements `MouseListener`. Its `mouseClicked` method maps seven fixed hit regions to indices `0..6`:

- left column: `0`, `2`, `4`, `6`;
- right column: `1`, `3`, `5`.

For a matched region it disposes any existing skill editor, creates the already-reviewed R276 `LoadoutSkillLevelEditor` with the loadout manager and selected skill index, then opens it.

`LoadoutSkillLevelEditor` exposes the exact seven labels `Attack`, `Range`, `Strength`, `Prayer`, `Defence`, `Magic`, and `Hitpoints`, independently corroborating the seven-index contract.

## Duplicate/ownership boundary

R279 intentionally does not rename:

- `rs/gui/b/h`, already owned by R3 as `LoadoutFolderPanel`;
- `rs/gui/b/a/A`, already owned by R276 as `LoadoutSkillLevelEditor`;
- the `rs/gui/b/a/*` loadout helper families already owned by R181/R274/R276/R277/R278;
- the still-weak `rs/gui/b/b` wrapper.

The branch-level uniqueness regression scans R2 through R278 and requires all eight R279 owner coordinates and proposed names to remain disjoint from prior reviewed class proposals.

## Stable-ID boundary

Stable IDs use the canonical one-based deterministic sorted exact-v308 `rs/**/*.class` inventory. `rs/gui/b/h` is `CLIENT_CLASS_000250`; the eight following classes `i..p` therefore resolve contiguously to `CLIENT_CLASS_000251..000258`.

## Acceptance boundary

R279 is non-canonical research only. These names describe exact-v308 responsibilities and wiring; no stripped original source identifiers are claimed and Chat 2 performs no semantic acceptance or rewrite.
