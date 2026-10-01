# Chat 2 — exact-v308 CustomMenuEntry R480

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/j/b/b`
- `CLIENT_CLASS_000309`
- `CustomMenuEntry`
- proposal: `SEMPROP_77482C7309BA1D0538C2`
- review: `SEMREVIEW_C6895C7C5121445A234D`

## Exact identity

The class is a two-field value object:

- String text
- `rs/h/b` event/action object

It exposes getters/setters plus value-style `equals`, `hashCode` and `toString`.

The exact `toString` template leaks the source-style identity:

`CustomMenuEntry(text=..., event=...)`

## Menu-family join

Sibling `rs/j/b/a` owns an array of ten `CustomMenuEntry` objects. Its builder method
accepts the exact pair:

- display String
- `rs/h/b` event/action

It creates a new entry, appends it to the custom-menu option array, measures the text through
the live client font renderer, recomputes menu geometry and exposes the currently selected
entry.

The surrounding manager family also integrates these custom entries into live Client menu
rows, but R480 intentionally names only the self-identifying value object.

## Stable ID

Exact-v308 sorted `rs/**` class order puts `rs/j/b/b` at zero-based index 308.
The canonical lineage convention therefore fixes it as:

`CLIENT_CLASS_000309`

R480 remains non-canonical semantic research only.
