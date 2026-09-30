# Chat 2 — exact-v308 Notes undo/redo actions R416

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/s/m/c` -> `CLIENT_CLASS_000931` -> `NotesUndoAction`
- `rs/s/m/d` -> `CLIENT_CLASS_000932` -> `NotesRedoAction`
- review: `SEMREVIEW_F4E8B003BCBDC7AC92F0`

R380 already recovered the source-proven Notes roots:

- `NotesConfig`
- `NotesPanel`
- `NotesPlugin`

R193 separately recovered `NotesSaveFocusListener`.

## Undo

NotesPanel installs `rs/s/m/c` under exact ActionMap key `Undo` and binds the matching
InputMap entry to `control Z`.

The action:

1. checks `UndoManager.canUndo()`;
2. calls `UndoManager.undo()`;
3. catches `CannotUndoException` and follows the Notes-specific warning path.

## Redo

NotesPanel installs `rs/s/m/d` under exact ActionMap key `Redo` and binds it to
`control Y`.

The action:

1. checks `UndoManager.canRedo()`;
2. calls `UndoManager.redo()`;
3. catches `CannotUndoException` through the same Notes warning path.

## Naming boundary

These are descriptive names for exact-v308 flattened anonymous-style Swing action classes.
R416 does not claim that `NotesUndoAction` or `NotesRedoAction` were original standalone
RuneLite source class identifiers.

R416 remains non-canonical semantic research only.
