# Chat 2 — exact-v308 TextPopupWindow helper family R254

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic review result

- `rs/tools/TextPopupWindow$b` -> `CLIENT_CLASS_000997` -> `HorizontallyScrollableTextPane`
- `rs/tools/a` -> `CLIENT_CLASS_000998` -> `TextAppender`
- `rs/tools/b` -> `CLIENT_CLASS_000999` -> `PlainTextAppender`
- `rs/tools/c` -> `CLIENT_CLASS_001000` -> `SessionLogTextAppender`
- `rs/tools/d` -> `CLIENT_CLASS_001001` -> `TextSearchToggleAction`
- `rs/tools/e` -> `CLIENT_CLASS_001002` -> `CaretVisibilityFocusListener`
- `rs/tools/f` -> `CLIENT_CLASS_001003` -> `TextSearchCloseAction`
- `rs/tools/g` -> `CLIENT_CLASS_001004` -> `TextSearchNextAction`
- review: `SEMREVIEW_AC0105ECA04611C86458`
- unresolved: **0**
- field/method proposals: **0**

## Exact family boundary

The already-reviewed `TextPopupWindow` owns a custom `JTextPane`, takes a three-argument
text-append strategy, binds Ctrl+F to the reviewed `TextSearchWindow`, and installs a
focus listener on the text pane.

The eight R254 classes are exactly that helper surface.

### Text pane

`TextPopupWindow$b` extends `JTextPane`. It stops tracking viewport width when its
preferred content width exceeds the parent width, allowing horizontal scrolling, and returns
the UI-computed preferred size directly.

### Append strategy

`rs/tools/a` is the single-method append strategy:
`(Document, SimpleAttributeSet, String) -> void`.

`rs/tools/b` is the default implementation and simply inserts the string at
`Document.getLength()`.

`rs/tools/c` is the specialized session-log formatter. Exact surviving literals include
`Logged in`, `IP address`, `Unregistered`, and `Logout`; it applies Swing styling,
tracks login state, parses the IP-address segment, and appends formatted text.

### Search/focus actions

`rs/tools/d` is the Ctrl+F action that creates/shows or toggles the reviewed search window.

`rs/tools/e` is a `FocusAdapter` whose only focus action makes the text-pane caret visible.

`rs/tools/f` is an `AbstractAction` whose only action disposes the search window.

`rs/tools/g` implements find-next behavior: lower-case query matching, offset advancement,
wrap to zero at document end, scrolling the hit into view, and selecting the matched range.

## Naming boundary

These are descriptive recovery names fixed by exact behavior. No R254 name is presented as
a verbatim original identifier.

## Acceptance boundary

R254 remains class-only and non-canonical. Chat 2 performs no semantic acceptance.
