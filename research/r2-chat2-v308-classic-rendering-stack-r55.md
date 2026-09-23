# Chat 2 — exact-v308 classic rendering stack semantics R55

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R55 is a separate non-canonical class-only semantic review batch recovering the core
software-rendering/image stack used by Scene, Model, UI and the client shell.

## Deterministic review result

- candidate classes: **6**
- resolved proposals: **6**
- unresolved: **0**
- review ID: `SEMREVIEW_36C5AEB28D03D1D5DBEB`
- field/method proposals: **0**

## Stable-ID verification

Core's exact `seed_lineage()` ordering over the complete `rs/` baseline gives:

- `rs/l/E` -> `CLIENT_CLASS_000354`
- `rs/l/F` -> `CLIENT_CLASS_000355`
- `rs/l/a` -> `CLIENT_CLASS_000363`
- `rs/l/c` -> `CLIENT_CLASS_000383`
- `rs/l/e` -> `CLIENT_CLASS_000397`
- `rs/l/h` -> `CLIENT_CLASS_000497`

## `rs/l/c` -> `DrawingArea`

This is the shared 2D framebuffer layer. It owns the global integer pixel buffer, float
depth buffer, width/height and clipping bounds. Its static surface initializes/clears that
buffer and draws filled/outlined rectangles, lines and alpha-blended primitives.

The exact font renderer `rs/l/h` extends this class, matching the classic client
`DrawingArea` hierarchy.

## `rs/l/E` -> `Rasterizer3D`

This is the software triangle engine. It owns:

- flat/Gouraud/textured triangle entry points;
- scanline helpers;
- texture image/cache state;
- HSL/RGB palette and brightness transforms;
- sine/cosine/projection lookup tables;
- depth-aware triangle paths.

Scene and Model consume this surface for projected geometry.

## `rs/l/h` -> `TextDrawingArea`

The class decodes per-glyph masks, dimensions, offsets and advances from font/archive
data. It measures text and provides the broad classic drawing surface for aligned,
shadowed, alpha and effect-oriented text.

It extends R55 `DrawingArea` directly.

## `rs/l/F` -> `Sprite`

The class owns full-color image pixels, dimensions and offsets. Constructors load from
archive entries, raw image bytes, AWT Images and named resources. Its rendering surface
supports clipping, scaling, transforms, alpha blending, rotation and masked drawing.

## `rs/l/a` -> `IndexedImage`

This class decodes a byte-indexed pixel plane plus integer palette, dimensions and offsets
from archive sprite data and `index.dat`. It draws through the shared DrawingArea and is
also the texture-image type stored by Rasterizer3D.

## `rs/l/e` -> `RSImageProducer`

This object owns a BufferedImage-backed integer framebuffer and width/height. Its
initialization binds that backing array into DrawingArea; its AWT method blits the image
to a Graphics target.

## Deliberately withheld superclass

`rs/l/B` is the thin common superclass used by several rendering/image classes and owns
an alpha-aware pixel-write helper, but its standalone semantic identity is less unique than
the concrete six classes above. R55 leaves it unnamed.

## Naming boundary

These are semantic/historical recovery names grounded in exact v308 behavior. R55 does not
promote them to canonical source authority.

## Acceptance boundary

Chat 2 does not promote R55. Main/Core may accept any desired subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_36C5AEB28D03D1D5DBEB`.
