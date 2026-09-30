# Chat 2 — PvP tracker sidebar update tasks R400

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R145 already owns `rs/gui/c/a` as `PvPTrackerSidebarPanel`.

R400 recovers only the two unowned EDT helpers:

- `rs/gui/c/b` -> `CLIENT_CLASS_000261` -> `UpdateMostRecentPvpFightTask`
- `rs/gui/c/c` -> `CLIENT_CLASS_000262` -> `UpdatePreviousPvpFightTask`

Review: `SEMREVIEW_072FAE4B42A5A66C56A1`

## Exact section split

The panel renders two explicit headers:

- `Most Recent 1v1 Fight`
- `Previous 1v1 Fight`

Its public method `a(int,String,String,String,String)` wraps the first helper in
`EventQueue.invokeLater`.

Its public method `b(int,String,String,String,String)` wraps the second helper in
`EventQueue.invokeLater`.

Each task selects one of the two fighter columns and updates:

- fight result/name text;
- Correct overheads;
- Spell casts;
- Damage Dealt;
- win/death icon state.

## Boundary

`rs/gui/c/d` is an empty class and remains unnamed.

Top-level `rs/gui/c` is a generic zero-corner-radius button shaper with no sufficiently
specific product-domain identity, so it also remains withheld.

R400 is non-canonical semantic research only.
