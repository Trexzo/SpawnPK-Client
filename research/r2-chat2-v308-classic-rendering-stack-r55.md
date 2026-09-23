# Chat 2 — exact-v308 classic rendering stack semantics R55

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R55 is a separate non-canonical class-only semantic review batch recovering the core
software-rendering/image/font stack used by Scene, Model, UI and the client shell.

This revision corrects the font-engine split after exact-v308 constructor/consumer
inspection showed that the original R55 attached `TextDrawingArea` to the wrong parallel
font engine.

## Deterministic review result

- candidate classes: **7**
- resolved proposals: **7**
- unresolved: **0**
- review ID: `SEMREVIEW_B14A4F72F6EC3A5BCF9E`
- field/method proposals: **0**

## Stable-ID verification

Core's exact `seed_lineage()` ordering over the complete `rs/` baseline gives:

- `rs/l/E` -> `CLIENT_CLASS_000354`
- `rs/l/F` -> `CLIENT_CLASS_000355`
- `rs/l/K` -> `CLIENT_CLASS_000360`
- `rs/l/a` -> `CLIENT_CLASS_000363`
- `rs/l/c` -> `CLIENT_CLASS_000383`
- `rs/l/e` -> `CLIENT_CLASS_000397`
- `rs/l/h` -> `CLIENT_CLASS_000497`

## `rs/l/c` -> `DrawingArea`

This is the shared 2D framebuffer layer. It owns the global integer pixel buffer, float
depth buffer, width/height and clipping bounds. Its static surface initializes/clears that
buffer and draws filled/outlined rectangles, lines and alpha-blended primitives.

Both recovered font engines extend this exact DrawingArea layer.

## `rs/l/E` -> `Rasterizer3D`

This is the software triangle engine. It owns flat/Gouraud/textured triangle entry points,
scanline helpers, texture image/cache state, HSL/RGB palette/brightness transforms and
sine/cosine/projection lookup tables used by Scene and Model.

## `rs/l/K` -> `TextDrawingArea`

This is the classic client font engine.

Its constructor `(boolean, String, StreamLoader)` allocates the characteristic 256 glyph
masks and parallel width/height/X-offset/Y-offset/advance arrays, owns Random/effect state,
then decodes `<font>.dat` plus `index.dat` using the classic font-header offset and
per-glyph storage layout.

Client constructs this exact type for `p11_full`, `p12_full` and `b12_full`, passes
an `rs/l/K[]` directly into R56 `RSInterface` loading and uses it throughout classic
chat/interface text paths.

Public 317-derived client source exposes the same field/constructor layout under
`TextDrawingArea`, and public clients commonly load it from those exact font resources.

## `rs/l/h` -> `RSFont`

v308 simultaneously constructs a second font family from the same classic resources:
`p11_full`, `p12_full`, `b12_full` and `q8_full`.

This engine has the larger rich-text surface: glyph metrics plus Sprite/icon support,
formatted/tagged rendering and broader icon-aware/effect drawing methods.

Public 317-derived clients commonly load a second `RSFont` family next to
`TextDrawingArea` using exactly this old-font/new-font split. That matches v308's
parallel construction and consumer pattern.

## `rs/l/F` -> `Sprite`

The class owns full-color image pixels, dimensions and offsets. Constructors load from
archive entries, raw image bytes, AWT Images and named resources. Its rendering surface
supports clipping, scaling, transforms, alpha blending, rotation and masked drawing.

## `rs/l/a` -> `IndexedImage`

This class decodes a byte-indexed pixel plane plus integer palette, dimensions and offsets
from archive sprite data and `index.dat`. It draws through DrawingArea and is the texture
image type stored by Rasterizer3D.

## `rs/l/e` -> `RSImageProducer`

This object owns a BufferedImage-backed integer framebuffer and width/height. Its
initialization binds that backing array into DrawingArea; its AWT method blits the image
to a Graphics target.

## Deliberately withheld helpers

`rs/l/B` remains an unnamed thin common rendering/image superclass. `rs/l/C` is a
separate depth-aware BufferedImage producer used by the live applet/client surface, but
its exact historical noun remains unresolved and it is not conflated with RSImageProducer.

## Naming boundary

These are semantic/historical recovery names grounded in exact v308 behavior. R55 does not
promote them to canonical source authority.

## Acceptance boundary

Chat 2 does not promote R55. Main/Core may accept any desired subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_B14A4F72F6EC3A5BCF9E`.
