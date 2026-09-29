# Chat 2 — Notes source identities R380

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/s/m/a` -> `CLIENT_CLASS_000929` -> `NotesConfig`
- `rs/s/m/b` -> `CLIENT_CLASS_000930` -> `NotesPanel`
- `rs/s/m/f` -> `CLIENT_CLASS_000934` -> `NotesPlugin`
- review: `SEMREVIEW_F2346DC79BA8B5C8C11E`

## Exact/source join

RuneLite source and exact v308 share the complete Notes identity:

- config group `notes`;
- hidden `notesData` getter/setter;
- JTextArea + UndoManager panel;
- Ctrl+Z / Ctrl+Y bindings;
- exact warning strings for undo, redo and bad document location;
- save-on-focus-loss behavior;
- plugin name `Notes`;
- descriptor `Enable the Notes panel`;
- `notes_icon.png` toolbar resource.

## Withheld synthetic helpers

`rs/s/m/c`, `rs/s/m/d`, and `rs/s/m/e` are flattened compiled forms of the NotesPanel inline undo/redo/focus listeners. They do not have independent durable top-level source identities and remain unnamed.

R380 remains non-canonical semantic research only.
