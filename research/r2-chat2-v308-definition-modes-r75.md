# Chat 2 — exact-v308 definition mode semantics R75

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R75 is a separate non-canonical class-only semantic review batch for two exact definition
source/decoder mode enums already consumed by accepted definition classes.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_A2B10461C7E511AE5FFA`
- field/method proposals: **0**

## Stable-ID verification

Core's exact `seed_lineage()` ordering over the complete `rs/` baseline gives:

- `rs/d/h$a` -> `CLIENT_CLASS_000119`
- `rs/d/r$a` -> `CLIENT_CLASS_000132`

## `rs/d/h$a` -> `FloorDefinitionMode`

This exact enum preserves three constant names:

- `REGULAR`
- `OLDSCHOOL`
- `OSRS`

R28 `FloorDefinition` stores the active enum value and switches its floor-definition
source/decoder when the mode changes.

R71 `FloorOverlayDefinition` accepts the same enum and changes its overlay-definition
source in lockstep.

The Client's region/map loading code actively changes both classes together: OSRS data
selects OSRS, the old-school path selects OLDSCHOOL, and ordinary loading returns to
REGULAR.

That fixes the role as `FloorDefinitionMode`.

## `rs/d/r$a` -> `ObjectDefinitionMode`

This exact enum preserves four constant names:

- `STANDARD`
- `OLDSCHOOL`
- `NEW`
- `OSRS`

R28 `ObjectDefinition` stores the active enum value. Its mode switch reloads the
object-definition data/index pair and selects different decoding paths according to that
value.

Client region/map loading explicitly selects OSRS, OLDSCHOOL, NEW or STANDARD according to
the map/object-definition source being processed. OSRS cache/map dependency tooling also
inspects the same mode-backed ObjectDefinition surface.

That fixes the role as `ObjectDefinitionMode`.

## Naming boundary

Both names are semantic recovery names. R75 does not claim they are verbatim original
SpawnPK developer identifiers.

## Acceptance boundary

Chat 2 does not promote R75. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_A2B10461C7E511AE5FFA`.
