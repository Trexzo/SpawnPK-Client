# Chat 2 R3 — exact-v308 RuneScape font registry R353

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

- `rs/gui/w` -> `CLIENT_CLASS_000284` -> `RuneScapeFontRegistry`
- proposal: `SEMPROP_EE5B014E6CFE1786864D`
- review: `SEMREVIEW_9C0972F81DFD627DC287`

Static initialization loads and registers exactly `runescape.ttf`,
`runescape_small.ttf`, and `runescape_bold.ttf`. Each is normalized at 16pt. The class
also retains plain/bold 16pt Dialog fallbacks and exposes all five Font objects through
zero-argument static getters.

Initialization fails explicitly with `Font loaded, but format incorrect.` or
`Font file not found.`.

R353 is descriptive non-canonical semantic research only.
