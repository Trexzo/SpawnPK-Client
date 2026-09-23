# Chat 2 — exact-v308 floor overlay / varp semantics R71

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R71 is a separate non-canonical class-only semantic review batch for two exact classic
configuration structures that remained unclaimed after R70.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_0DF83AB9E51DD7DACE67`
- field/method proposals: **0**

## Stable-ID verification

Core's exact `seed_lineage()` ordering over the complete `rs/` baseline gives:

- `rs/d/t` -> `CLIENT_CLASS_000135`
- `rs/d/z` -> `CLIENT_CLASS_000142`

## `rs/d/t` -> `FloorOverlayDefinition`

This is the exact floor-overlay definition used by terrain construction.

The loader is selected by the same REGULAR / OLDSCHOOL / OSRS floor-definition mode already
visible in the exact client and loads the overlay table from the surviving flo2 asset paths,
including `flo2.dat` and `osrs_flo2.dat`.

The class has exact surviving overlay diagnostics, including:

- `[OverlayFloor] Missing AttributeId:`
- `Error unrecognised overlay code:`

Its decoders populate the color/texture/render state expected for a floor overlay, including
primary and secondary RGB values, texture ids, visibility/occlusion state, and derived
hue/saturation/lightness values.

R53 `ObjectManager` directly indexes the static `rs/d/t[]` definition table from terrain
overlay ids and consumes these fields while constructing scene tile paint/model geometry.

That fixes the semantic role as `FloorOverlayDefinition`.

## `rs/d/z` -> `VarpDefinition`

This class loads exact `varp.dat` bytes from R29 `StreamLoader`, decodes a counted table,
and reports the surviving diagnostic:

`varptype load mismatch`

The opcode decoder stores the client-setting type integer used by the runtime, tracks the
classic flagged-varp index list, and sets its boolean marker for the relevant opcodes.

The relationship to R28 `VarbitDefinition` is direct: while varbits are loaded, their base
variable index is used to index `rs/d/z.a`, and flagged varbits mark the referenced
definition.

The runtime relationship is also exact. `Client.B(varpId)` reads
`rs/d/z.a[varpId].b` together with the current varp value and dispatches the corresponding
client setting behavior.

That fixes the class as `VarpDefinition`, not a generic integer configuration object.

## Naming boundary

Both names are semantic recovery names. R71 does not claim they are verbatim original
SpawnPK developer identifiers.

## Acceptance boundary

Chat 2 does not promote R71. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_0DF83AB9E51DD7DACE67`.
