# Chat 2 — corrected R404 Loadouts source-identity audit

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Retained proposal

R404 retains exactly one semantic proposal:

- `rs/gui/b/h`
- `CLIENT_CLASS_000250`
- `LoadoutsPanel`
- proposal: `SEMPROP_A804361DDF23D61A1830`
- review: `SEMREVIEW_93EC02A5042580DB5C64`

The recovered semantic source map identifies this class as
`rs.gui.loadouts.LoadoutsPanel`.

Exact v308 independently corroborates that source identity: the class is the top-level
Loadouts Swing panel and composes the loadout folder/store/equipment/list-selection/stat-edit
surfaces and related actions.

## Non-retained source-name corrections

The original R404 attempt also proposed nine names for owners that were already reviewed:

- `rs/gui/b/c/a` / 000243 — earlier R346 `DefaultLoadoutSeeder`; later source map says `DefaultLoadout`
- `rs/gui/b/a` / 000205 — earlier R143 `LoadoutDefinition`; later source map says `Loadout`
- `rs/gui/b/b/e` / 000241 — earlier R345 `LoadoutFormatVersionDetector`; later source map says `LoadoutVersion`
- `rs/gui/b/b/c` / 000239 — earlier R345 `LoadoutBinaryCodec`; later source map says `LoadoutSerializer`
- `rs/gui/b/c/c` / 000245 — earlier R143 `LoadoutEquipmentSlot`; later source map says `EquipmentSlot`
- `rs/gui/b/c` / 000242 — earlier R143 `LoadoutFolder`; later source map says `LoadoutList`
- `rs/gui/b/b/d` / 000240 — earlier R143 `LoadoutPersistence`; later source map says `LoadoutStore`
- `rs/gui/b/a$a` / 000206 — earlier R143 `LoadoutSpellbook`; later source map says `Spellbook`
- `rs/gui/b/c/b` / 000244 — earlier R144 `LoadoutPreviewRenderer`; later source map says `EquipmentPanel`

Those source-map identities are preserved here as correction evidence only. They are not
re-proposed as duplicate owners in R404.

## Boundary

R404 remains non-canonical Chat 2 semantic research only. No acceptance or source rewrite is
performed.
