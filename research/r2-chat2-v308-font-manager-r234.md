# Chat 2 — exact-v308 RuneLite FontManager source recovery R234

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_EDD457452DF995D41667`
- field/method proposals: **0**

## Stable ID

- `rs/gui/w` -> `CLIENT_CLASS_000284` -> `FontManager`

## Exact-v308 surface

The pinned v308 class owns five static fonts with five getters.

Its class initializer loads:

- `runescape.ttf`;
- `runescape_small.ttf`;
- `runescape_bold.ttf`.

Each resource is created as a TrueType `Font`, derived at 16px, registered with the local
`GraphicsEnvironment`, and resolved through `StyleContext`. The class also creates:

- `new Font("Dialog", PLAIN, 16)`;
- `new Font("Dialog", BOLD, 16)`.

The exception paths preserve the exact strings:

- `Font loaded, but format incorrect.`
- `Font file not found.`

## RuneLite source lineage

RuneLite `net.runelite.client.ui.FontManager` owns the same resource trio, registration
pipeline, RuneScape/default font roles, getters, and exact failure literals.

Historical source immediately before RuneLite's 2020 bold-style fix
(`593c8102f66cffcb8b55678aa59f2a36dfcf64ff`) preserves the v308-style plain treatment of
`runescape_bold.ttf`. Later RuneLite revisions add default/custom-font behavior. Exact v308
contains a fork-combined surface, so R234 claims the source class identity but does not claim
one byte-identical upstream revision.

## Acceptance boundary

Chat 2 does not promote R234. Main/Core may accept it only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_EDD457452DF995D41667`.
