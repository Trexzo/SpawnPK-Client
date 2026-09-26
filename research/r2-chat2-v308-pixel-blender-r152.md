# Chat 2 — exact-v308 shared pixel blending R152

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R152 resolves the thin rendering superclass deliberately withheld by R55.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_4D081ABE7A8E9C4DCC3C`
- field/method proposals: **0**

## Stable ID

`rs/l/B` -> `CLIENT_CLASS_000351` -> `PixelBlender`

## Exact class surface

The class has no instance fields.

Beyond its constructor, it has one substantive static method taking:

- an `int[]` destination pixel buffer;
- one destination index;
- one direct/software pixel value;
- one RGB source color;
- one alpha value.

When the recovered R87 `GpuRenderer` path is inactive, the method writes the direct
software pixel value.

When that GPU-aware path is active, the method:

1. validates alpha/index bounds;
2. preserves the incoming RGB color with an ARGB alpha byte when the destination has no
   meaningful alpha or source alpha is fully opaque;
3. preserves special fully-alpha destination semantics where applicable;
4. otherwise combines source and destination alpha;
5. blends red/blue and green channel groups by the normalized source/destination weights;
6. writes the resulting ARGB pixel back into the destination buffer.

This is a pixel compositing primitive, not a framebuffer owner or triangle engine.

## Rendering hierarchy

The only direct subclasses are already-reviewed rendering/image classes:

- R55 `IndexedImage`;
- R55 `DrawingArea`;
- R55 `Rasterizer3D`;
- R55 `Sprite`.

Exact inherited calls are used repeatedly from IndexedImage and Sprite drawing/copy paths.

The class itself owns no:

- clipping state;
- raster dimensions;
- sprite/image data;
- texture state;
- triangle state;
- geometry.

That makes a broad name such as `RasterizerBase` less precise than the recovered behavior.

## Naming boundary

`PixelBlender` is descriptive at **0.998**.

The noun is deliberately narrow: it names the only behavior the class contributes to its
rendering subclasses. It is not claimed as the historical/original SpawnPK identifier.

## Acceptance boundary

Chat 2 does not promote R152. Main/Core may accept this proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_4D081ABE7A8E9C4DCC3C`.
