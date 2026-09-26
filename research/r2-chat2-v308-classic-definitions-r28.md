# Chat 2 — exact-v308 classic definition semantics R28

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R28 is a separate non-canonical class-only semantic review batch. It does not alter
Main/Core's accepted R2 semantic authority or prior R3-R27 review batches.

## Deterministic review result

- candidate classes: **8**
- resolved proposals: **8**
- unresolved: **0**
- review ID: `SEMREVIEW_4276DC989C3E027F83A1`
- field/method proposals: **0**

## Classic cache/config definitions

| Raw class | Stable ID | Candidate semantic | Exact authority |
| --- | --- | --- | --- |
| `rs/d/a` | `CLIENT_CLASS_000110` | `SequenceDefinition` | `seq.dat` + seq decoder diagnostics |
| `rs/d/d` | `CLIENT_CLASS_000113` | `NpcDefinition` | `npc.dat` + NPC model/action/morph surface |
| `rs/d/h` | `CLIENT_CLASS_000118` | `FloorDefinition` | `flo.dat` / OSRS floor variants + `[FLO]` decoder diagnostic |
| `rs/d/j` | `CLIENT_CLASS_000121` | `IdentityKitDefinition` | `idk.dat` + `[IDK]` decoder diagnostic + appearance models |
| `rs/d/k` | `CLIENT_CLASS_000122` | `ItemDefinition` | `obj.dat/obj.idx` + Wear/Wield/Drop/Destroy/Take + item models |
| `rs/d/r` | `CLIENT_CLASS_000131` | `ObjectDefinition` | `loc.dat/loc.idx` + exact `Object definition data/index length mismatch` |
| `rs/d/x` | `CLIENT_CLASS_000140` | `SpotAnimationDefinition` | `spotanim.dat` + spotanim decoder diagnostic |
| `rs/d/y` | `CLIENT_CLASS_000141` | `VarbitDefinition` | `varbit.dat` + `[VARB]` decoder diagnostic |

## Structural corroboration

`SequenceDefinition` owns frame/duration arrays and animation/model transform methods.

`NpcDefinition` owns NPC name/actions, model ids, recolor/retexture/config data, morph
selection and NPC model/head construction.

`ItemDefinition` owns item names/actions, stack variants, equip/chathead models,
recolor/retexture data, note/copy transforms and sprite/model generation.

`ObjectDefinition` owns object names/actions, model/type arrays, size/collision flags,
morphing and world-object model construction.

`SpotAnimationDefinition` links a model to a sequence definition and owns recolor/retexture,
scale, rotation and lighting metadata.

`VarbitDefinition` is the compact base-variable + start/end-bit range record expected from
the classic `varbit.dat` format.

R28 intentionally does not name adjacent loader/helper classes merely because they reference
these definitions. The proposal boundary is the definition objects themselves.

## Acceptance boundary

Chat 2 does not promote R28. Main/Core may accept any desired subset only through an
explicit `semantic_acceptance_spec` bound to
`SEMREVIEW_4276DC989C3E027F83A1`.
