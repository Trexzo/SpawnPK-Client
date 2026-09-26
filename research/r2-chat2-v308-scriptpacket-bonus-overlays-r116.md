# Chat 2 — exact-v308 ScriptPacket-backed bonus overlays R116

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R116 is a separate non-canonical class-only review for three live overlays whose otherwise
ambiguous updater siblings become exact once R115 establishes the ScriptPacket registry.

## Deterministic review result

- candidate classes: **6**
- resolved proposals: **6**
- unresolved: **0**
- review ID: `SEMREVIEW_409A524C63012E32F91D`
- field/method proposals: **0**

## Stable IDs and exact ScriptPacket IDs

- `rs/l/e/a/a` -> `CLIENT_CLASS_000399` -> `EssenceBonusStatsOverlay`
- `rs/l/e/a/b` -> `CLIENT_CLASS_000400` -> `EssenceBonusStatsPacketHandler` — ScriptPacket **11**
- `rs/l/e/a/f` -> `CLIENT_CLASS_000404` -> `IngredientSaveChanceOverlay`
- `rs/l/e/a/g` -> `CLIENT_CLASS_000405` -> `IngredientSaveChancePacketHandler` — ScriptPacket **25**
- `rs/l/e/a/v` -> `CLIENT_CLASS_000420` -> `TicketBonusStatsOverlay`
- `rs/l/e/a/w` -> `CLIENT_CLASS_000421` -> `TicketBonusStatsPacketHandler` — ScriptPacket **18**

## Essence bonus stats

The first overlay renders exactly:

- `Killcount: @yel@<n>`
- `Drop rate: @gre@+<n>%`
- `Essence bonus: @gre@+<n>%`

Its ScriptPacket 11 handler uses a four-way selector:

1. visibility;
2. killcount;
3. drop-rate bonus;
4. essence bonus.

The packet handler also rebuilds the three lines using exact icons 121, 130 and 275.

## Ingredient-save chance

This HIGH-layer overlay displays:

`You have a @gre@<n>% @whi@chance to save ingredients`

followed by:

`on failed attempts @or2@(consumes on save!)`

It renders the associated ItemDefinition icon/name.

ScriptPacket 25 writes the save-chance value and, while positive, the associated item ID.
The handler clears the cached item name after each update so the overlay re-resolves the
current definition.

## Ticket bonus stats

The ScriptPacket 18 handler has the same four-selector shape as packet 11 but emits:

- icon 121 — Killcount;
- icon 130 — Drop rate;
- icon 281 — **Ticket bonus**.

The live overlay renders those packet-populated lines while active.

One historical/local inconsistency survives: the overlay's generic `b()` reset/rebuild
formatter still contains the older `Essence bonus` text. Live packet selector 4 overwrites
the third line with `Ticket bonus`.

R116 therefore gives the overlay confidence **0.997**, while the packet handler remains
0.999. The discrepancy is retained as evidence rather than silently normalized away.

## Naming boundary

These names are descriptive exact-behavior recovery names. R115 supplies exact ScriptPacket
identity and IDs; the visible text and packet payloads supply the domain.

R116 remains class-only.

## Acceptance boundary

Chat 2 does not promote R116. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_409A524C63012E32F91D`.
