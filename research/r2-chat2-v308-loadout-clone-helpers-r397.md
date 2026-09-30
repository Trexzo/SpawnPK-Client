# Chat 2 — loadout clone and editor-close helpers R397

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/gui/b/a/a` -> `CLIENT_CLASS_000210` -> `CloneLoadoutButtonFactory`
- `rs/gui/b/a/b` -> `CLIENT_CLASS_000211` -> `OpenCloneLoadoutConfirmationAction`
- `rs/gui/b/a/c` -> `CLIENT_CLASS_000212` -> `CloneCurrentCharacterStateToLoadoutAction`
- `rs/gui/b/a/d` -> `CLIENT_CLASS_000213` -> `CloneLoadoutCancelAction`
- `rs/gui/b/a/z` -> `CLIENT_CLASS_000235` -> `CloseLoadoutMetadataEditorAction`

Review: `SEMREVIEW_9C4DA4D11355DB50047F`

## Duplicate audit

The neighboring loadout classes were checked before this batch:

- R143 already owns `rs/gui/b/a` as `LoadoutDefinition`;
- R143 already owns `rs/gui/b/a$a` as `LoadoutSpellbook`;
- R181 already owns `rs/gui/b/a/B` as `SpawnLoadoutButtonFactory`;
- R181 already owns `rs/gui/b/a/C` as `SpawnLoadoutAction`;
- R392-R396 own the later metadata/selector/render/action surface.

R397 therefore fills only genuinely unowned exact-v308 classes.

## Clone button factory

`rs/gui/b/a/a` builds the exact **Clone** button, loading `clone.png`, installing the
tooltip about taking the currently equipped in-game items, and wiring one listener:
`rs/gui/b/a/b`.

## Confirmation action

`rs/gui/b/a/b` requires an active loadout and opens a small Yes/No confirmation JFrame.
It wires:

- Yes -> `rs/gui/b/a/c`
- No -> `rs/gui/b/a/d`

It does not itself mutate the loadout.

## Clone commit action

The Yes action is broader than the button tooltip.

It updates the active `LoadoutDefinition` from live client character state by:

- clearing/rebuilding stored inventory/equipment entries;
- reading live item ids and quantities from the relevant client widgets;
- capturing current spellbook;
- capturing current prayer-book mode;
- capturing seven skill levels;
- refreshing the loadout manager/panel state;
- issuing the exact `::cldt` clone-flow command.

If a live character is unavailable it displays the exact guidance dialog instead.

The descriptive name therefore uses **CharacterState**, not only Equipment.

## Cancel + metadata close

`rs/gui/b/a/d` only hides/disposes the clone confirmation window.

`rs/gui/b/a/z` only hides/disposes the R392 `LoadoutMetadataEditorDialog`.

## Boundary

R397 is non-canonical semantic research only.
