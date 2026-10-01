# Chat 2 — exact-v308 model surface transforms R399

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/a/b/a` -> `CLIENT_CLASS_000059` -> `ModelRecolorTransform`
- `rs/a/b/b` -> `CLIENT_CLASS_000061` -> `ModelFaceTransform`
- `rs/a/b/c` -> `CLIENT_CLASS_000062` -> `ModelSurfaceTransform`
- `rs/a/b/d` -> `CLIENT_CLASS_000063` -> `ModelReshadeTransform`
- `rs/a/b/e` -> `CLIENT_CLASS_000064` -> `ModelRetextureTransform`
- review: `SEMREVIEW_5A0C370F5807A65B918A`

Nested `rs/a/b/a$a` / `CLIENT_CLASS_000060` remains unnamed because it is an internal
cursor/set implementation detail of ModelRecolorTransform rather than an independently
meaningful model subsystem.

## Surviving config vocabulary

The exact YAML config loaders for NPC, Item and SpotAnimation definitions preserve the
surface-transform nouns directly:

- `recolor` / `recolors`
- `retexture` / `retextures`
- `textures`
- `reshade`
- item `opacity`

Those keys lazily create and configure one `rs/a/b/c` composite on the definition.

## ModelRecolorTransform

The recolor transform owns source face/color-id sets plus per-group destination sequences.
When a Model face's `ar` value belongs to one configured source group, the value is
replaced by the next configured destination value for that group.

R209 ModelRecoloringOverlay consumes the same source-id set when presenting exact
item/NPC/object recoloring diagnostics.

## ModelRetextureTransform

The retexture transform is configured by `retexture(s)` and `textures`.

It owns source-id sets and int-to-int source/destination maps. Before per-face processing it
allocates texture-related Model arrays for matching faces. Per matching face it:

- marks the face as processed;
- rewrites the face/color id to the mapped destination id;
- creates texture-face metadata;
- copies the original face vertex indices into the texture-coordinate arrays.

R209 labels these ids with exact `(texture)` / `(texturized)` diagnostics.

## ModelReshadeTransform

The exact `reshade` key constructs one integer-valued transform. For each non-excluded
face it overwrites the Model face/color-id entry with that configured value.

## ModelSurfaceTransform

The composite is stored directly by NpcDefinition, ItemDefinition and SpotAnimationDefinition
and applied to newly constructed Models.

It combines:

- recolor transform;
- retexture transform;
- reshade transform;
- opacity scalar.

The opacity path initializes the Model per-face opacity array and fills it with
`100 - configuredOpacity`.

## Boundary

These names describe exact-v308 Model surface/material mutation behavior. They do not claim
server-side rendering authority or original stripped developer identifiers.

R399 remains non-canonical semantic research only.
