# Chat 2 — exact-v308 legacy menu action opcode utility R225

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R225 reviews the remaining real utility class `rs/runelite/a/g` after the R224 historical
RuneLite value-type pass.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_267CA131DF9AF68E32CE`
- field/method proposals: **0**

## Stable ID

- `rs/runelite/a/g` -> `CLIENT_CLASS_000815` -> `LegacyMenuActionOpcode`

## Exact opcode surface

The class contains the legacy menu-action values used by the exact SpawnPK client, including:

- walk: **516**;
- NPC interactions: **20, 412, 225, 965, 478, 1025, 582, 413**;
- player interactions: **561, 779, 27, 577, 729, 491, 365**;
- object interactions: **502, 900, 113, 872, 1062**, plus object examine **1226**;
- inventory-item interactions: **74, 454, 539, 493, 847, 447**, plus item examine **1125**.

These are the classic 317-style menu opcodes retained by the SpawnPK client rather than the
modern RuneLite `MenuAction` enum IDs.

## Exact classifier behavior

The four boolean helpers form coherent action families:

- `a(int)`: NPC interaction IDs;
- `b(int)`: player interaction IDs;
- `c(int)`: object interaction IDs;
- `d(int)`: inventory-item interaction IDs.

The exact recovered plugins make those roles observable:

- NpcIndicators and InteractHighlight feed live menu IDs into the NPC classifier and then
  resolve the corresponding NPC through Client menu-index arrays;
- MenuEntrySwapper branches across NPC, object and inventory-item families;
- HoverDescriptions branches across player, NPC and object families.

The class also resolves a menu row to the associated NPC definition and definition ID.

## Naming boundary

`LegacyMenuActionOpcode` is a descriptive exact-behavior name at confidence **0.999**.
R225 does not pretend the class is the modern RuneLite `MenuAction` enum and does not assign
field or method names.

## Acceptance boundary

Chat 2 does not promote R225. Main/Core may accept it only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_267CA131DF9AF68E32CE`.
