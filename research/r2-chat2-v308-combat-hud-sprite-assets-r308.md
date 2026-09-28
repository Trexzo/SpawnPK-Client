# Chat 2 — exact-v308 combat HUD sprite assets R308

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic result

- `rs/l/J` -> `CLIENT_CLASS_000359` -> `CombatHudSpriteAssets`
- review: `SEMREVIEW_085C30D25627BE958931`
- unresolved: **0**
- member proposals: **0**

## Exact-v308 contract

The class has no mutable gameplay state or generic loader logic. It is a static bundle of eight `rs/l/F` sprites:

- `misc/singlesplus`
- `misc/singlesplushot`
- `popups/hp 0`
- `popups/hp 1`
- `popups/hp 2`
- `popups/hp 3`
- `hitmarks/old/poise`
- `popups/scope`

Its exact consumers keep the bundle entirely inside combat/HUD presentation:

- R304 `GameHudRenderer` uses the singles-plus pair for the live gameframe indicator;
- `Client` uses the HP sprite pairs while rendering actor health bars;
- the entity hitmark renderer `rs/a/f` uses the poise hitmark sprite;
- `Client` uses the scope sprite in the corresponding target/player presentation path.

That is narrow enough to recover the class as `CombatHudSpriteAssets` without claiming the stripped original class noun.

## Deliberate exclusion

The nearby `rs/l/j` class remains unnamed. It combines a 386-entry sprite registry, clan/BH/icon asset path generation, chat/right-color helpers and formatting utilities, so it does not yet have one precise semantic noun.

## Boundary

R308 is non-canonical semantic research only. No semantic acceptance, source rewrite or source materialization is performed.
