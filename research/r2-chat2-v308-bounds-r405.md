# Chat 2 — RuneScape Bounds R405

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

- `rs/g/a` -> `CLIENT_CLASS_000177` -> `Bounds`
- review: `SEMREVIEW_4E74912844D1F6296FC4`

## Exact shape

The class owns four public ints and exposes:

- four-int constructor;
- two-int constructor delegating to low=(0,0);
- one setter for the first coordinate pair;
- one setter for the second pair;
- the distinctive legacy `toString() -> null`.

## Exact game-shell use

`rs/C.aZ()` obtains the active AWT container dimensions, subtracts frame insets when
present, and returns `new rs/g/a(width, height)`.

The game-shell resize path then reads the record's high-dimension pair to update the live
client dimensions/canvas rebuild state.

The structure is the long-standing RuneScape `Bounds` record, so R405 uses the historical
identity rather than inventing `CanvasBounds` or `GameContainerBounds`.

R405 remains non-canonical semantic research only.
