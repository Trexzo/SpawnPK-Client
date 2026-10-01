# Chat 2 — exact-v308 construction and prayer interfaces R449

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/n/c/aF` -> `CLIENT_CLASS_000581` -> `ConstructionPlankInterface`
- `rs/n/c/aG` -> `CLIENT_CLASS_000582` -> `CursesInterface`
- `rs/n/c/aH` -> `CLIENT_CLASS_000583` -> `PrayerInterface`
- review: `SEMREVIEW_5FCA05F69BFA66975AB7`

## ConstructionPlankInterface

Exact text/resources include:

- `construction/sprite`
- Wood / Oak / Teak / Mahogony price labels
- `Make-all @cya@Wood`
- `Make-all @cya@Oak`
- `Make-all @cya@Teak`
- `Make-all @cya@Mahogony`

## CursesInterface

Exact resources and prayer names include:

- `prayer/curses/ICON`
- Sap Warrior / Ranger / Mage / Spirit
- Deflect Magic / Missiles / Melee / Summoning
- Leech family
- Soul Split
- Turmoil and range/magic variants
- Wrath and Berserker

## PrayerInterface

Exact resources and names include:

- `prayer/PRAYER`
- `prayer/sprite 1`
- `prayer/sprite 2`
- Thick Skin through Smite
- Preserve
- Chivalry
- Piety
- Rigour
- Augury

## Boundary

R449 recovers client presentation builders only. Construction pricing authority, prayer drain,
combat effects and server eligibility remain outside this semantic layer.

R449 remains non-canonical Chat 2 research only.
