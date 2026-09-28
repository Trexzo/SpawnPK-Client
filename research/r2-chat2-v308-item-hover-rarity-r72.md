# Chat 2 — exact-v308 item hover / rarity semantics R72

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R72 is a separate non-canonical class-only semantic review batch for two item-display
configuration tables and the exact rarity enum consumed by one of them.

## Deterministic review result

- candidate classes: **3**
- resolved proposals: **3**
- unresolved: **0**
- review ID: `SEMREVIEW_F28F6DE6F955C01B4848`
- field/method proposals: **0**

## Stable-ID verification

Core's exact `seed_lineage()` ordering over the complete `rs/` baseline gives:

- `rs/d/m` -> `CLIENT_CLASS_000124`
- `rs/d/p` -> `CLIENT_CLASS_000128`
- `rs/d/p$a` -> `CLIENT_CLASS_000129`

## `rs/d/m` -> `ItemHoverDescriptionConfig`

This class owns an item-id keyed string table loaded from the exact surviving file:

`configs/hovers.yaml`

SnakeYAML decodes the file as a `Map<Integer,String>`; every entry is copied into the
class's Trove map.

The lookup path accepts an existing hover string plus an item id and appends the configured
text when that id is present. The Client's item-hover rendering path calls this lookup
directly.

There are two additional exact ownership signals:

- the runtime reload path emits `<img=2> Item hover descriptions reloaded!`;
- the item-definition update path can insert per-item hover text into the same table.

That fixes the class as `ItemHoverDescriptionConfig`.

## `rs/d/p` -> `ItemRarityConfig`

This class loads the exact surviving file:

`configs/rarities.yaml`

The YAML keys are item ids. The values are matched case-insensitively against exactly:

- `uncommon`
- `rare`
- `legendary`

and the result is stored in an item-id keyed map of the nested rarity enum.

R28 `ItemDefinition` consumes this table directly. When an item id has a rarity mapping
and the item name still carries the default `@gre@` prefix, ItemDefinition replaces that
prefix with the selected rarity's formatting tag.

That fixes the class as `ItemRarityConfig`.

## `rs/d/p$a` -> `ItemRarity`

The nested enum preserves exact constant names:

- `UNCOMMON`
- `RARE`
- `LEGENDARY`

and each owns the exact display-format string applied to item names:

- `<col=65BFFF>`
- `<col=BD73FF><shad=773494>`
- `<col=FFC81A><shad=9A7705>`

The enum is therefore the exact rarity value type consumed by `ItemRarityConfig` and
`ItemDefinition`.

## Naming boundary

All three names are semantic recovery names. R72 does not claim they are verbatim original
SpawnPK developer identifiers.

## Acceptance boundary

Chat 2 does not promote R72. Main/Core may accept any proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_F28F6DE6F955C01B4848`.
