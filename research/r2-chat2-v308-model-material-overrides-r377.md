# Chat 2 successor — exact-v308 model material overrides R377

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/a/b/a` -> `CLIENT_CLASS_000059` -> `ModelRecolorOverride`
- `rs/a/b/b` -> `CLIENT_CLASS_000061` -> `ModelFaceOverride`
- `rs/a/b/c` -> `CLIENT_CLASS_000062` -> `ModelMaterialOverrides`
- `rs/a/b/d` -> `CLIENT_CLASS_000063` -> `ModelReshadeOverride`
- `rs/a/b/e` -> `CLIENT_CLASS_000064` -> `ModelRetextureOverride`

Review: `SEMREVIEW_5C688CD64AA078A6D414`

## Parser authority

The exact item-definition config parser maps:

- `opacity` -> the aggregate override integer;
- `recolor` / `recolors` -> `rs/a/b/a`;
- `retexture` / `retextures` -> `rs/a/b/e`;
- `reshade` -> `rs/a/b/d`.

Those operations are stored together in `rs/a/b/c`.

## Runtime Model application

R30 already fixes `rs/a/h` as `Model`.

The aggregate applies the configured operations to Model faces before item/NPC/model consumers
render the model:

- recolor maps source face colors to configured destination colors;
- retexture converts matching faces and constructs the corresponding texture-triangle metadata;
- reshade replaces the face shade/color integer when the face has not already been retextured;
- opacity allocates/populates the Model opacity array.

The abstract `rs/a/b/b` contract exists solely to apply whole-model and per-face transforms.

## Boundary

These names describe exact client-side Model material/face transformation. They do not claim
server item semantics or original stripped identifiers.

R377 remains non-canonical semantic research only.
