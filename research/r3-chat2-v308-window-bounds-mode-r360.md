# Chat 2 R3 — launcher window bounds constraint mode R360

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

- `rs/gui/u$a` -> `CLIENT_CLASS_000282` -> `WindowBoundsConstraintMode`
- proposal: `SEMPROP_E2223B217B614818EB9E`
- review: `SEMREVIEW_E123BF4BBAC74B4920B0`

The enum contains exactly:

- `ALWAYS`
- `RESIZING`
- `NEVER`

R354 `LauncherWindowFrame` stores this enum and consults it in window location/bounds and
resize paths to decide when geometry must be constrained to the active monitor bounds.

R360 is descriptive non-canonical semantic research only.
