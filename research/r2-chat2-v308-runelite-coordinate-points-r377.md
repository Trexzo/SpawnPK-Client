# Chat 2 — RuneLite local/world coordinate points R377

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/runelite/a/f` -> `CLIENT_CLASS_000814` -> `LocalPoint`
- `rs/runelite/a/p` -> `CLIENT_CLASS_000832` -> `WorldPoint`
- review: `SEMREVIEW_66B9F28EFC744B92EAC5`

LocalPoint uses the exact 104*128 local-scene range and converts tile centers with `(tile << 7) + 64`. World-to-local conversion subtracts the current Client world base before applying that scale.

WorldPoint stores x/y/plane, converts from LocalPoint using the Client base, performs same-plane distance and scene membership checks, and preserves the literal class-file string `WorldPoint(x=..., y=..., plane=...)`.

Nearby generic geometry/vector helpers remain intentionally unnamed.

R377 is non-canonical semantic research only.
