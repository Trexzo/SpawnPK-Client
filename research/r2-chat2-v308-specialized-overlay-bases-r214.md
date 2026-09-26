# Chat 2 — exact-v308 specialized overlay bases R214

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R214 is a separate non-canonical class-only review for the four specialized subclasses of
the R213 Overlay root.

It is anchored to already-reviewed exact type identities rather than package adjacency:

- R30 `rs/a/h` -> `Model`;
- R30 `rs/a/j` -> `Npc`;
- R30 `rs/a/k` -> `Player`;
- R28 `rs/d/d` -> `NpcDefinition`.

## Deterministic review result

- candidate classes: **4**
- resolved proposals: **4**
- unresolved: **0**
- review ID: `SEMREVIEW_6DB640B065E4298217A3`
- field/method proposals: **0**

## Stable IDs

- `rs/l/f/b/a` -> `CLIENT_CLASS_000480` -> `ModelOverlay`
- `rs/l/f/b/b` -> `CLIENT_CLASS_000481` -> `NpcOverlay`
- `rs/l/f/b/c` -> `CLIENT_CLASS_000482` -> `PlayerOverlay`
- `rs/l/f/b/d` -> `CLIENT_CLASS_000483` -> `WidgetOverlay`

All four exact classes extend R213 `Overlay`.

## ModelOverlay

`rs/l/f/b/a` stores:

- one exact R30 `Model`;
- one associated render-context `Object`.

OverlayManager's object/model stage dispatch detects this subtype, injects both values,
binds the live Client and executes the overlay lifecycle.

Its only direct exact-v308 subclass is R209 `ModelRecoloringOverlay`.

That specialization consumes the supplied live Model in the exact item/NPC/object
pre-shade development path, independently fixing the base to model-bound rendering.

## NpcOverlay

`rs/l/f/b/b` stores:

- exact R30 `Npc`;
- exact R28 `NpcDefinition`;
- exact R30 `Model`;
- one integer render state.

Assigning an Npc immediately derives and stores its NpcDefinition.

The class exposes model/NPC geometry helpers that calculate:

- a RuneLite model hull representation;
- a projected `Polygon`.

OverlayManager's actor-stage dispatch recognizes `rs/a/j`, injects both the Npc and
current Model and executes this subtype.

Direct subclasses include R208 `NpcDefinitionSpriteOverlay` and NPC-facing plugin
overlays.

## PlayerOverlay

`rs/l/f/b/c` stores exactly one R30 `Player`.

Its protected player predicate returns true only when the stored Player is the exact
`Client.eR` local-player object.

OverlayManager's actor-stage dispatch recognizes `rs/a/k`, assigns the Player and
executes this subtype.

Its direct exact-v308 subclass is the player-facing outline overlay implementation.

This is enough to fix the base as PlayerOverlay without naming any members.

## WidgetOverlay

`rs/l/f/b/d` stores three integers.

OverlayManager proves their surrounding contract:

1. `a(WidgetOverlay, int)`
   - creates/uses an int-keyed registry;
   - stores the integer on the overlay;
   - adds the overlay under that same key.
2. `a(WidgetOverlay)`
   - retrieves the overlay's stored integer key;
   - removes it from that keyed registry.
3. `a(int, int, int)`
   - looks up overlays by the first integer;
   - writes the remaining two integers onto each overlay;
   - binds the Client;
   - executes the overlay.

The interface builders independently fix the key as a widget/interface id.

R205's Adventure Book path is exact:

- creates literal `Chapter Progress`;
- creates widget **38388**;
- registers `AdventureBookChapterProgressRenderer`, which extends this base, under
  **38388**.

Other direct subclasses are independently registered under exact ids including:

- **60065**;
- **32317**;
- **32465**;
- **32486**.

The two runtime integers are therefore the widget's draw coordinates, making WidgetOverlay
a generic widget-bound overlay base rather than a feature-specific renderer.

## Naming boundary

All four names are descriptive exact-behavior recovery at confidence **0.999**.

R214 does not assert original source identifiers and adds no field or method proposals.

## Acceptance boundary

Chat 2 does not promote R214. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_6DB640B065E4298217A3`.
