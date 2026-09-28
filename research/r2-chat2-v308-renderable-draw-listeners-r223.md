# Chat 2 — exact-v308 renderable draw listener hooks R223

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R223 reviews the two-class draw-suppression hook family used directly by exact Renderable
and Client rendering and by the Entity Hider plugin.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_5A82D8014F00A60B0954`
- field/method proposals: **0**

## Stable IDs

- `rs/runelite/b/a` -> `CLIENT_CLASS_000833` -> `RenderableDrawListenerRegistry`
- `rs/runelite/b/a$a` -> `CLIENT_CLASS_000834` -> `RenderableDrawListener`

## RenderableDrawListener

The exact interface has one method:

`boolean draw(rs.a.a renderable, boolean ui)`

The base Renderable draw method calls listeners before rendering and returns immediately when
one listener returns false. Client performs the same suppression test through the second
listener list in its secondary entity/presentation path.

The exact Entity Hider plugin creates two invokedynamic `draw` lambdas implementing this
interface and returns false for configured hidden categories.

RuneLite source at `6e74752caa80fe9cb96cd9b37207e171fa525f07` retains the compatibility API name
`RenderableDrawListener` with the same semantic method
`boolean draw(Renderable renderable, boolean ui)`. SpawnPK's stripped class is standalone,
so R223 uses confidence **0.998** rather than claiming byte-for-byte source-class identity.

## RenderableDrawListenerRegistry

The companion class owns exactly two static CopyOnWriteArrayList-backed listener lists and
one accessor for each. Entity Hider registers/removes one listener in each list, while the two
render paths consume them.

No original upstream name for this registry container survives in the evidence used here.
`RenderableDrawListenerRegistry` is therefore a descriptive exact-behavior name at
confidence **0.997**.

## Acceptance boundary

Chat 2 does not promote R223. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_5A82D8014F00A60B0954`.
