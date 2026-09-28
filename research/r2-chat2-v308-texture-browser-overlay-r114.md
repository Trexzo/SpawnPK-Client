# Chat 2 — exact-v308 Texture Browser overlay R114

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R114 is a separate non-canonical class-only review for the live texture ID grid opened by
the R110 Editor Kit utility commands.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_966D74C50FB581DF0BB0`
- field/method proposals: **0**
- confidence: **0.999**

## Stable ID

- `rs/l/e/a/u` -> `CLIENT_CLASS_000419` -> `TextureBrowserOverlay`

## Exact command activation

R110 `EditorKitUtilityCommandHandler` handles both:

- `texture`
- `textures`

by enabling the live `rs/l/e/a/u` singleton, resetting its start texture ID to zero and
emitting:

`Textures opened`

through the Editor Kit notification surface.

A separate ordinary client command path also enables the same browser state.

## Exact grid renderer

The overlay renders only outside the LOW pass, therefore on R111's HIGH layer.

It walks the global texture array:

`rs/l/E.y`

from its current start texture ID.

The default grid is exactly:

- **8 columns**
- **5 rows**

Editor Kit/resizable mode recomputes the grid dimensions from the live client width/height.

For every visible texture ID the overlay:

1. for IDs >= 40, attempts `Client.a(id, 50L)` first;
2. obtains the matching texture sprite from the global texture array;
3. draws the sprite into the current grid cell;
4. labels the cell with exact text:

`@gre@ID <id>`

## Keyboard paging

While the browser is active, the exact keyboard handler consumes left/right arrows.

It moves the starting texture ID by one complete page:

`columns * rows`

then:

- clamps negative starts to zero;
- refuses starts beyond the texture array length.

ESC, key code **27**, disables the browser.

Another editor-side navigation branch retains a 43-entry paging step, but the primary
browser paging contract is the live grid-page calculation above.

## Interaction contract

The class extends R112 `InteractiveClientOverlay`.

Its interaction hook returns true for input codes:

- 1
- 2

while its visibility predicate returns the browser's active flag directly.

## Naming boundary

No surviving original source noun was found.

`TextureBrowserOverlay` is descriptive exact-behavior recovery. Confidence is 0.999
because the activation commands, texture-array domain, grid labels and keyboard navigation
all survive directly.

## Acceptance boundary

Chat 2 does not promote R114. Main/Core may accept the proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_966D74C50FB581DF0BB0`.
