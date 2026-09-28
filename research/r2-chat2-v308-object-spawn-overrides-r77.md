# Chat 2 — exact-v308 object spawn override semantics R77

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R77 is a separate non-canonical class-only semantic review batch for the exact built-in and
packet-driven object-spawn override registry.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_BD18FEB5E201CDAFAD5D`
- field/method proposals: **0**

## Stable-ID verification

Core's exact `seed_lineage()` ordering over the complete `rs/` baseline gives:

- `rs/d/s` -> `CLIENT_CLASS_000133`
- `rs/d/s$a` -> `CLIENT_CLASS_000134`

## `rs/d/s$a` -> `ObjectSpawnOverride`

This nested class is a six-int record populated directly by the object-update packet.

The packet stores the record in a global map under the exact key shape:

`x,y,plane`

and then applies the record through the client's six-argument world-object spawn/update
method as:

`Client.a(x, y, objectId, rotation, type, plane)`

The same record coordinates are reused for removal with object id `-1`.

## `rs/d/s` -> `ObjectSpawnOverrideManager`

The class owns the coordinate-keyed map and participates directly in all three packet
actions:

1. remove one override at an exact x/y/plane coordinate and clear its scene object;
2. add/update one override record and immediately apply it to the scene;
3. find every tracked override for a requested object id, clear each from the scene, and
   remove its registry entry.

The class also contains the client's large built-in table of fixed-coordinate object
additions, replacements and removals. Those entries use the same Client object-spawn API,
including `-1` object ids for removals.

That common registry + packet + built-in application path fixes the role as an object-spawn
override manager rather than a generic coordinate map.

## Naming boundary

Both names are semantic recovery names. R77 does not claim they are verbatim original
SpawnPK developer identifiers.

## Acceptance boundary

Chat 2 does not promote R77. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_BD18FEB5E201CDAFAD5D`.
