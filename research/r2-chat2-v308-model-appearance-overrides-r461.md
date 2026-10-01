# Chat 2 — exact-v308 model appearance overrides R461

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/a/b/a` -> `CLIENT_CLASS_000059` -> `ModelRecolorOverride`
- `rs/a/b/b` -> `CLIENT_CLASS_000061` -> `ModelFaceOverride`
- `rs/a/b/c` -> `CLIENT_CLASS_000062` -> `ModelAppearanceOverride`
- `rs/a/b/d` -> `CLIENT_CLASS_000063` -> `ModelReshadeOverride`
- `rs/a/b/e` -> `CLIENT_CLASS_000064` -> `ModelRetextureOverride`

Review: `SEMREVIEW_490B707BC919B4D20469`

## Surviving config vocabulary

Exact-v308 definition config loaders route these literal keys into this family:

- `opacity`
- `recolor` / `recolors`
- `retexture` / `retextures`
- `textures`
- `reshade`

The aggregate is stored directly on NPC, Item and SpotAnimation definition/model paths.

## Recolor

`rs/a/b/a` receives grouped source/destination color arrays. It indexes the source ids
and rewrites matching Model face-color entries to configured destination values. Per-group
destination selection cycles deterministically.

## Retexture

`rs/a/b/e` receives grouped retexture mappings and direct texture maps. It prepares the
affected-face masks/texture support arrays and rewrites matching face presentation state,
while preserving the source face vertex triplets into the Model texture-coordinate arrays.

R209 ModelRecoloringOverlay independently consumes these mappings and labels them as
`(texture)` / `(texturized)`.

## Reshade

`rs/a/b/d` is constructed only from the literal `reshade` key. It stores one integer and
writes that value to eligible Model face presentation entries.

## Aggregate/base

`rs/a/b/c` composes recolor, retexture and reshade plus a scalar opacity override and
applies the enabled pieces to a Model.

`rs/a/b/b` is the shared whole-model/per-face override base implemented only by the three
specialized helpers above.

## Boundary

Names describe exact config-driven Model appearance behavior. They do not claim verbatim
original developer identifiers. R461 remains non-canonical semantic research only.
