# Chat 2 — exact-v308 ModelPusher R96

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R96 is a separate non-canonical class-only semantic review for the model-to-GPU staging
component split out from R89 `SceneUploader`.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_962C7EAC6598F1713A81`
- field/method proposals: **0**

## Stable ID

- `rs/k/i` -> `CLIENT_CLASS_000338` -> `ModelPusher`

## Exact-v308 separation from SceneUploader

R87 `GpuRenderer` constructs two distinct objects:

- `rs/k/l`, already R89 `SceneUploader`;
- `rs/k/i`, the R96 candidate.

The renderer then calls `rs/k/i` directly when a live model must be converted into GPU
staging data.

This matters because older RuneLite source historically kept the core `pushModel` method
inside `SceneUploader`. Exact v308 has explicitly split that concern into its own class.

## Exact model-push behavior

`rs/k/i` accepts the exact-v308 model class together with R89:

- `GpuIntBuffer`;
- `GpuFloatBuffer`.

Its bytecode:

- caps processed faces at **6144**;
- walks model face/vertex/index/color/texture data;
- packs vertex/color information into the integer staging buffer;
- writes UV/texture information into the float staging path;
- handles flat-shaded/hidden faces;
- applies the same byte-based HSL override interpolation family;
- returns the number of staged vertices/data units.

Those responsibilities are the model-pushing portion of the GPU renderer rather than scene
traversal.

## Historical architecture corroboration

117 HD source preserves a dedicated class literally named `ModelPusher`, owned separately
from its scene uploader and responsible for converting Model data into
`GpuIntBuffer` / `GpuFloatBuffer` staging buffers.

Earlier RuneLite GPU source preserves the same core push logic as
`SceneUploader.pushModel(Model, GpuIntBuffer, GpuFloatBuffer)`.

The combined lineage explains exact v308: SpawnPK retains the old low-level push behavior,
but uses the later architectural split where model pushing is its own component.

## Acceptance boundary

Chat 2 does not promote R96. Main/Core may accept the proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_962C7EAC6598F1713A81`.
