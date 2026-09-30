# Chat 2 — exact-v308 CollisionMap R413

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/f` -> `CLIENT_CLASS_000166` -> `CollisionMap`
- proposal: `SEMPROP_F6DC28793F0CE1517C28`
- review: `SEMREVIEW_BC5E6AB3E6207F6BD98B`

## Exact v308 contract

The class owns the classic clipping grid:

- one `int[][]` adjacency/flags array;
- local/base offsets and dimensions;
- reset/open-border initialization;
- wall and rectangular-object clipping mutation;
- blocked-tile mutation;
- wall/object/decor reachability queries.

The directional bit-mask behavior and the reachability routines match the historical
RuneScape collision-map algorithms.

## Historical identity

Public refactored RuneScape clients preserve the same class as `CollisionMap`, including
the classic grid representation and method219-style reachability logic.

R413 therefore uses the inherited source identity rather than a new descriptive name.

## Boundary

R413 is class-only, non-canonical Chat 2 semantic research.
