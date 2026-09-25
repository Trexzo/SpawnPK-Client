# Chat 2 — exact-v308 model recoloring overlays R209

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R209 is a separate non-canonical class-only review for the development model recoloring
overlay base and its item/NPC/object pre-shade specializations.

## Deterministic review result

- candidate classes: **4**
- resolved proposals: **4**
- unresolved: **0**
- review ID: `SEMREVIEW_F56A03A3A97AEC0E7D4E`
- field/method proposals: **0**

## Stable IDs

- `rs/l/f/a/d/a` -> `CLIENT_CLASS_000454` -> `ItemRecoloringOverlay`
- `rs/l/f/a/d/b` -> `CLIENT_CLASS_000455` -> `ModelRecoloringOverlay`
- `rs/l/f/a/d/c` -> `CLIENT_CLASS_000456` -> `NpcRecoloringOverlay`
- `rs/l/f/a/d/d` -> `CLIENT_CLASS_000457` -> `ObjectRecoloringOverlay`

All IDs were recomputed from the exact v308 sorted `rs/**.class` seed-lineage order.

## Independent recoloring noun

The development window `rs/s/c/d` exposes exact visible mode labels:

- `Recoloring N/A`
- `Recoloring NPC`
- `Recoloring Item`
- `Recoloring Object`

It keeps one active `rs/l/f/a/d/b` base reference and switches that reference to the exact
NPC/item/object overlay instances from the global overlay manager.

This fixes the family as recoloring tooling independently of class/package adjacency.

## Shared ModelRecoloringOverlay behavior

The base extends the model-bound overlay base and receives the exact model being processed
at the selected pre-shade stage.

It inventories model/definition color state into the development JList and classifies
observed ids with exact surviving suffixes:

- `(texture)`
- `(texturized)`
- `(recolored)`

The UI supports exact development controls such as:

- `Color inverse`
- `Hide modified`
- `Copy selected`.

Before shading, selected color ids can be replaced by `-1` in the active model color
array; the inverse/isolation mode can replace nonselected entries with `1`.

The implementation is therefore a developer visual-inspection/recoloring overlay, not
authoritative game-definition mutation.

## ItemRecoloringOverlay

The item specialization binds to exact stage:

`ITEM_3D_PRE_SHADE`

It resolves one `rs/d/k` item definition and supplies that definition's model ids and
recolor/texture state to the shared base.

The development window's item selection path sets exact label:

`Recoloring Item`

then selects this instance through `rs/l/f/e.k()`.

## NpcRecoloringOverlay

The NPC specialization binds to exact stage:

`NPC_3D_PRE_SHADE`

It accepts an `rs/a/j` NPC actor, tracks the actor's `rs/d/d` definition id and supplies
the corresponding NPC definition model/recolor state to the shared base.

The development window sets exact label:

`Recoloring NPC`

then selects this instance through `rs/l/f/e.j()`.

## ObjectRecoloringOverlay

The object specialization binds to exact stage:

`OBJECT_3D_PRE_SHADE`

It resolves one `rs/d/r` object definition and supplies its model/color state to the
shared base.

The development window sets exact label:

`Recoloring Object`

then selects this instance through `rs/l/f/e.l()`.

## Global overlay-manager join

The exact `rs/l/f/e` constructor creates all three concrete recoloring overlays and, when
the development feature flag is enabled, registers all three into the live render-stage
pipeline.

It exposes exact getters used by the development recoloring window:

- `j()` -> NPC recoloring overlay;
- `k()` -> item recoloring overlay;
- `l()` -> object recoloring overlay.

This is a direct component/UI join, not an inferred package grouping.

## Naming boundary

All four names are descriptive exact-behavior recovery at **0.999** confidence.

The names intentionally use `Recoloring` because that noun survives literally in the
development UI. They do not claim original Java source identifiers.

R209 adds no field or method proposals.

## Acceptance boundary

Chat 2 does not promote R209. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_F56A03A3A97AEC0E7D4E`.
