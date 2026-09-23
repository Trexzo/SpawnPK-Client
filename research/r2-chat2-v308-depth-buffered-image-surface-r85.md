# Chat 2 — exact-v308 depth BufferedImage surface R85

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R85 is a separate non-canonical class-only semantic review batch for the live
depth-aware BufferedImage framebuffer previously withheld by R55.

R55 correctly left the class unnamed because its exact historical noun was unresolved.
R85 does **not** overturn that caveat. It uses a deliberately descriptive semantic name
grounded only in exact-v308 behavior.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_E90B9897A7720ADF272D`
- field/method proposals: **0**
- confidence: **0.995**

## Stable-ID verification

Core's exact `seed_lineage()` ordering gives:

- `rs/l/C` -> `CLIENT_CLASS_000352`

## `rs/l/C` -> `DepthBufferedImageSurface`

The constructor allocates:

- an `int[]` pixel buffer sized `width * height`;
- a parallel `float[]` depth buffer of the same size;
- a `BufferedImage` whose `DataBufferInt` is backed directly by the exact pixel array;
- width, height and owning AWT `Component`.

Its zero-argument bind method passes:

- width;
- height;
- pixel buffer;
- depth buffer

directly into R55 `DrawingArea` through the exact descriptor:

`rs/l/c.a(II[I[F)V`

The draw method then blits the backing `BufferedImage` into a supplied
`java.awt.Graphics` using the owning component as the image observer.

## Live runtime wiring

R48 `RSApplet` owns two fields of this exact type and constructs them as live client
surfaces. `Client` also recreates and rebinds the surface during rendering/layout
transitions and repeatedly calls its DrawingArea-binding method.

This is therefore active renderer plumbing rather than a dormant image helper.

## Distinction from R55 `RSImageProducer`

R55 separately identifies `rs/l/e` as `RSImageProducer`.

That type owns a BufferedImage-backed integer framebuffer and binds only:

`DrawingArea.a(II[I)`

By contrast, `rs/l/C` binds the additional parallel `float[]` depth plane and is used
by the live applet/client surface.

R85 therefore does not alias the two classes.

## Naming boundary

`DepthBufferedImageSurface` is deliberately descriptive, not historical. The confidence
is **0.995**, not 0.999, because exact behavior fixes the role but does not recover the
original developer's class noun.

No claim is made that this is a verbatim original SpawnPK or classic-client identifier.

## Acceptance boundary

Chat 2 does not promote R85. Main/Core may accept the proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_E90B9897A7720ADF272D`.
