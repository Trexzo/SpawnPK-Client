# Chat 2 — exact-v308 interface layout engine R284

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic result

- `rs/n/d/a` -> `CLIENT_CLASS_000681` -> `InterfaceRelativeLayoutConstraint`
- `rs/n/d/b` -> `CLIENT_CLASS_000682` -> `InterfaceLayoutEntry`
- `rs/n/d/c` -> `CLIENT_CLASS_000683` -> `InterfaceLayoutManager`
- review: `SEMREVIEW_F31A3D4D3DC87ECB8DC2`
- unresolved: **0**
- member proposals: **0**

## Exact layout contract

`InterfaceLayoutManager` is bound to one owning `RSInterface`. It owns an ordered child-entry list, an id-indexed entry map and a map of resolved `java.awt.Point` positions.

Its layout pass resolves each child from:

- direct x/y coordinates;
- another layout entry's resolved position plus offsets;
- a previously resolved point anchor plus offsets;
- or an `InterfaceRelativeLayoutConstraint` referencing another child.

The relative constraint stores a referenced interface id, x/y integer offsets, two proportional-placement booleans, x/y float factors and integer width/height caps. The manager reads the referenced child's dimensions, applies those factors/caps when enabled, and derives the dependent child's final coordinates.

The final position is written into the owner with the exact `RSInterface.b(index, childId, x, y)` path. The manager also recognizes `DropDownComponent` children and places the shared `DropDownMenuPanel` beneath them, joining R284 directly to the retained R283 dropdown family.

## Boundary

These are descriptive exact-v308 layout roles. R284 claims no lost source identifiers, performs no member naming, semantic acceptance or source rewrite.
