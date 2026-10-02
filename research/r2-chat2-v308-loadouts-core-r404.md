# Chat 2 — source-identified Loadouts core R404

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/gui/b/a` -> `CLIENT_CLASS_000205` -> `Loadout`
- `rs/gui/b/a$a` -> `CLIENT_CLASS_000206` -> `Spellbook`
- `rs/gui/b/b/c` -> `CLIENT_CLASS_000239` -> `LoadoutSerializer`
- `rs/gui/b/b/d` -> `CLIENT_CLASS_000240` -> `LoadoutStore`
- `rs/gui/b/b/e` -> `CLIENT_CLASS_000241` -> `LoadoutVersion`
- `rs/gui/b/c` -> `CLIENT_CLASS_000242` -> `LoadoutList`
- `rs/gui/b/c/a` -> `CLIENT_CLASS_000243` -> `DefaultLoadout`
- `rs/gui/b/c/b` -> `CLIENT_CLASS_000244` -> `EquipmentPanel`
- `rs/gui/b/c/c` -> `CLIENT_CLASS_000245` -> `EquipmentSlot`
- `rs/gui/b/h` -> `CLIENT_CLASS_000250` -> `LoadoutsPanel`

Review: `SEMREVIEW_35EACC9BFA2DE859EEC5`.

All ten identities come from the recovered semantic source map and are independently
corroborated by exact-v308 contracts. The batch intentionally anchors only the core model,
persistence, equipment and main-panel layer. The many loadout action/dialog classes remain a
follow-on family.

R404 remains non-canonical semantic research only.
