# Chat 2 — exact-v308 NPC/object icon semantics R76

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R76 is a separate non-canonical class-only semantic review batch for the exact cached
NPC-head/object icon renderer used by interface drawing.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_C5E41431CAE19B2F928A`
- field/method proposals: **0**

## Stable-ID verification

Core's exact `seed_lineage()` ordering over the complete `rs/` baseline gives:

- `rs/d/e` -> `CLIENT_CLASS_000114`
- `rs/d/e$a` -> `CLIENT_CLASS_000115`

## `rs/d/e$a` -> `NpcObjectIconType`

The nested enum preserves two exact constant names:

- `NPC_HEAD`
- `OBJECT`

The renderer uses the enum to choose both the source model and the dedicated icon cache.

## `rs/d/e` -> `NpcObjectIconRenderer`

The class owns two R47 `MruNodeCache` instances, each with capacity 20. One is used for
NPC_HEAD icons and the other for OBJECT icons.

For NPC_HEAD, the requested id is resolved through R28 `NpcDefinition` and its head model
is obtained.

For OBJECT, the requested id is resolved through R28 `ObjectDefinition` and its shape-10
model is obtained.

The model is rendered into a square R55 `Sprite` at the requested size. The routine
temporarily installs that sprite as the software raster target, configures Rasterizer3D,
renders the model, performs the icon outline pass, and restores the previous raster state.

The cache is size-aware: if a cached sprite exists for the id but its recorded size differs
from the current request (other than the sentinel size), it is discarded and regenerated.

Two exact UI consumers close the identity:

- the interface renderer has separate NPC_HEAD and OBJECT branches;
- R5 `MakeQuantityInterface` recognizes exact `npc_<id>` references and requests a
  64-pixel NPC_HEAD icon.

That fixes the role as `NpcObjectIconRenderer`.

## Naming boundary

Both names are semantic recovery names. R76 does not claim they are verbatim original
SpawnPK developer identifiers.

## Acceptance boundary

Chat 2 does not promote R76. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_C5E41431CAE19B2F928A`.
