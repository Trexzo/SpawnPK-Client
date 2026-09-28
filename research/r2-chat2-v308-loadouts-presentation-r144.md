# Chat 2 — exact-v308 Loadouts presentation model R144

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R144 extends the exact Loadouts model recovered in R143 with the three remaining
high-confidence presentation/model records. Async image-cache workers remain excluded.

## Deterministic review result

- candidate classes: **3**
- resolved proposals: **3**
- unresolved: **0**
- review ID: `SEMREVIEW_568CA6267E68D9EB80D7`
- field/method proposals: **0**

## Stable IDs

- `rs/gui/b/c/b` -> `CLIENT_CLASS_000244` -> `LoadoutPreviewRenderer`
- `rs/gui/b/e` -> `CLIENT_CLASS_000247` -> `LoadoutIcon`
- `rs/gui/b/f` -> `CLIENT_CLASS_000248` -> `LoadoutItemEntry`

## LoadoutPreviewRenderer

This class owns one current R143 `LoadoutDefinition` and renders only that record.

Exact assets include:

- `/assets/gui/loadout_bg.png`;
- `/assets/gui/normal.png`;
- `/assets/gui/curses.png`;
- `/assets/gui/booktag.png`;
- `/assets/gui/skills.png`;
- `/assets/gui/outline.png`;
- pet/cosmetic slot resources.

Its render path consumes:

- spellbook;
- prayer state;
- seven skill values;
- 28 backpack `LoadoutItemEntry` values;
- the `LoadoutEquipmentSlot` map.

It draws item images and quantities for both backpack and equipment state.

The live Loadouts panel/manager swaps this renderer to the active definition as selection
changes.

## LoadoutIcon

`rs/gui/b/e` is a 29-value enum used directly as presentation metadata on
`LoadoutDefinition`.

Exact constants/labels include:

- `MELEE` / Melee;
- `RANGE` / Range;
- `MAGIC` / Magic;
- `PURE` / Pure;
- `WELFARE` / Welfare;
- `SKULL` / Skull;
- `RED_SKULL` / Red Skull;
- `HOTSPOT` / Hotspot;
- `SLAYER` / Slayer;
- `BLOOD_SLAYER` / Blood Slayer;
- `RAIDS` / Raids;
- `EVENT` / Event;
- `BARRAGE` / Barrage;
- `FUN` / Fun;
- multiple Cash / Orb / Enchant / Emoji variants.

Each value carries a matching `/assets/gui/icons/*.png` resource.

That makes the enum role exact as the selectable loadout icon/category.

## LoadoutItemEntry

`rs/gui/b/f` is an immutable two-integer record.

Constructors are:

- `(itemId, quantity)`;
- `(itemId)`, defaulting quantity to **1**.

Exact consumers establish the field meanings:

- `LoadoutDefinition` stores these in its backpack array and equipment map;
- `LoadoutPersistence` serializes/deserializes both integers;
- the exact `::item_loadout` spawn path writes item id + quantity;
- `LoadoutPreviewRenderer` resolves the first value to the item image and renders the
  second as quantity/count.

The conservative name `LoadoutItemEntry` avoids imposing a broader engine-level
`ItemStack` abstraction that exact v308 does not establish.

## Deliberate exclusion

The async image lookup/cache classes (`rs/gui/b/g` and worker helpers) remain unnamed.
Their implementation role is clear, but naming them adds little semantic value compared with
the exact model/presentation records above.

## Acceptance boundary

Chat 2 does not promote R144. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_568CA6267E68D9EB80D7`.
