# Chat 2 — exact-v308 Item Search and Development sidebar pages R146

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R146 resolves the two mutually exclusive final pages in the R145
`ClientSidebarPanel`.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_08BBF1DCA1080D2650C2`
- field/method proposals: **0**

## Stable IDs

- `rs/gui/G` -> `CLIENT_CLASS_000190` -> `ItemSearchSidebarPanel`
- `rs/s/c/d` -> `CLIENT_CLASS_000890` -> `DeveloperToolsSidebarPanel`

## Complementary sidebar placement

R145 `ClientSidebarPanel` owns one final conditional tab slot.

When the developer-tools predicate is true:

`Development` -> `rs/s/c/d`

Otherwise:

`Item Search` -> `rs/gui/G`

This exact parent placement independently fixes both classes as sidebar pages rather than
generic helpers.

## ItemSearchSidebarPanel

The page owns:

- one search text field;
- one Search button;
- one result text area;
- one result scroll pane.

Before searching it requires the item-definition database to be loaded. Exact warning:

`Please wait until the client has loaded the item database!`

It also requires at least three characters:

`Please have at least 3 letters in your search term!`

The search iterates the exact cached item-definition table, matches item names
case-insensitively, excludes item id 11283, strips client color tags for output and renders:

- item id;
- item name;
- exact `(noted)` state.

That is a complete Item Search responsibility.

## DeveloperToolsSidebarPanel

The Development page exposes exact maintenance actions:

- `Reset Item Defs` -> `::itemdef reset`;
- `Reset NPC Defs` -> `::resetnpcdefs`;
- `Repack cache` -> `::repack`.

Its editor/recolor state uses exact labels:

- `Recoloring N/A`;
- `Recoloring NPC`;
- `Recoloring Item`;
- `Recoloring Object`.

Exact controls include:

- `Color inverse`;
- `Hide modified`;
- `Copy selected`.

It also emits Development-specific feedback:

`Color string added to keyboard!`

The class's static availability predicate is the same predicate used by
`ClientSidebarPanel` to choose Development over Item Search.

## Naming boundary

The `SidebarPanel` suffix follows exact parent placement established in R145.
Neither name is claimed as an original developer identifier.

## Acceptance boundary

Chat 2 does not promote R146. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_08BBF1DCA1080D2650C2`.
