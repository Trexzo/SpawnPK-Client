# Chat 2 — exact-v308 Notes save focus listener R193

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R193 is a separate non-canonical class-only review for the final unreviewed helper in the
already-recovered Notes plugin package.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_F96D5656110D072AF7CE`
- field/method proposals: **0**

## Stable ID

`rs/s/m/e` -> `CLIENT_CLASS_000933` -> `NotesSaveFocusListener`

## Existing Notes authority

Earlier reviews already recover:

- `rs/s/m/a` -> `NotesConfig`;
- `rs/s/m/b` -> `NotesPanel`;
- `rs/s/m/c` -> `NotesUndoAction`;
- `rs/s/m/d` -> `NotesRedoAction`;
- `rs/s/m/f` -> `NotesPlugin`.

This leaves `rs/s/m/e` as the only previously unnamed class in the package.

## Exact panel ownership

`NotesPanel` constructs one `rs/s/m/e` instance and attaches it directly to the Notes
text area's focus-listener list.

The target class stores only:

- reviewed `NotesConfig`;
- reviewed `NotesPanel`.

It implements `java.awt.event.FocusListener`.

## Exact focus lifecycle

`focusGained` is a no-op.

`focusLost` performs the complete class responsibility:

1. obtain the Notes text area's Swing Document;
2. read the entire document with `getText(0, getLength())`;
3. pass that String to the reviewed `NotesConfig` notes-data setter.

The exceptional path catches `BadLocationException` and logs the exact Notes-specific text:

`Notes Document Bad Location: `

No unrelated UI or persistence behavior exists in the class.

## Naming boundary

`NotesSaveFocusListener` is **0.999**.

The readable noun is descriptive rather than a claim about stripped original source naming.
The class is exclusively a FocusListener attached to the Notes editor, and its only
substantive callback persists the complete Notes document.

R193 remains class-only and non-canonical.

## Acceptance boundary

Chat 2 does not promote R193. Main/Core may accept it only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_F96D5656110D072AF7CE`.
