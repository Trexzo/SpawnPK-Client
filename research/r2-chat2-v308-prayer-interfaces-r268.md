# Chat 2 — exact-v308 prayer interface family R268

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic review result

- `rs/n/c/aG` -> `CLIENT_CLASS_000582` -> `AncientCursesInterface`
- `rs/n/c/aH` -> `CLIENT_CLASS_000583` -> `StandardPrayerInterface`
- review: `SEMREVIEW_C2C7E9D99596A4B6B883`
- unresolved: **0**
- field/method proposals: **0**

## Ancient Curses

`rs/n/c/aG` extends the exact interface-builder base and constructs the dedicated curses
widget tree rooted in the 22500 range.

Its literal/resource surface is exclusive:

- `prayer/curses/ICON`
- Protect Item
- Sap Warrior / Ranger / Mage / Spirit
- Berserker
- Deflect Summoning / Magic / Missiles / Melee
- Leech Attack / Ranged / Magic / Defence / Strength / Energy / Special Attack
- Wrath
- Soul Split
- Turmoil plus ranged/magic variants

The class therefore has a precise curses-interface role rather than a generic prayer helper.

## Standard Prayer interface

`rs/n/c/aH` owns the standard prayer tree and its dynamic presentation updates.

Exact v308 preserves:

- `prayer/PRAYER` and `prayer/sprite` resources;
- Thick Skin through the protection prayers;
- Eagle Eye / Mystic Might;
- Chivalry / Piety;
- Rigour / Augury;
- `Show stat adjustments` / `Hide stat adjustments`;
- exact alternate placement/tooltip updates for Rigour, Augury, Eagle Eye and Mystic Might.

This is separate from the curses builder and contains no unrelated interface domain.

## Naming boundary

Both names are descriptive exact-behavior identifiers. R268 does not claim the original
developer source identifiers survived ProGuard.

A full prior-review scan before commit found no existing owner or proposed-name collision
for either class.

## Acceptance boundary

R268 remains class-only and non-canonical. Chat 2 performs no semantic acceptance.
