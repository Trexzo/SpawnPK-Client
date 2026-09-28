# Chat 2 — exact-v308 InfoBox core R162

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R162 fills the missing core between the already-reviewed InfoBoxManager, InfoBoxPacketHandler,
and concrete Boost/Counter/Status/Timer InfoBox subclasses.

## Deterministic review result

- candidate classes: **4**
- resolved proposals: **4**
- unresolved: **0**
- review ID: `SEMREVIEW_495BB30E145BAAA19582`
- field/method proposals: **0**

## Stable IDs

- `rs/ui/a/c` -> `CLIENT_CLASS_001019` -> `InfoBox`
- `rs/ui/a/e` -> `CLIENT_CLASS_001021` -> `InfoBoxSpriteType`
- `rs/ui/a/g` -> `CLIENT_CLASS_001023` -> `InfoBoxOverlay`
- `rs/ui/a/h` -> `CLIENT_CLASS_001024` -> `InfoBoxPriority`

## Core joins

`InfoBox` is the shared abstract base used directly by R11 `InfoBoxManager` and extended
by the already-reviewed concrete InfoBox classes.

`InfoBoxSpriteType` preserves exact `ITEM_SPRITE` / `CACHE_SPRITE`; packet creation and
image scaling branch on this source contract.

`InfoBoxOverlay` extends the shared overlay base, is constructed by InfoBoxManager per group,
and is joined by the exact default group literal `InfoBoxOverlay` plus persisted
`infoboxoverlay` settings.

`InfoBoxPriority` preserves exact `HIGH`, `MED`, `NONE`, `LOW` and is the first key
in InfoBoxManager's ordering comparator.

## Acceptance boundary

Chat 2 does not promote R162. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_495BB30E145BAAA19582`.
