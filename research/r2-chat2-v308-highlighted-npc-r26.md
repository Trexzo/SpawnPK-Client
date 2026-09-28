# Chat 2 — exact-v308 highlighted NPC semantics R26

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R26 is a separate non-canonical class-only semantic review batch. It does not alter
Main/Core's accepted R2 semantic authority or prior R3-R25 review batches.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_F2B9678512AAB9EE7CC2`
- field/method proposals: **0**

## NPC highlighting values

- `rs/s/o/a` -> `HighlightedNpc`
- `rs/s/o/a$a` -> `HighlightedNpcBuilder`

Both names survive directly in exact-v308 bytecode.

The immutable value has the self-identifying form:

`HighlightedNpc(npc=…, highlightColor=…, fillColor=…, hull=…, tile=…, trueTile=…, swTile=…, swTrueTile=…, outline=…, name=…, nameOnMinimap=…, borderWidth=…, outlineFeather=…, render=…)`

Its fields match those roles exactly: NPC reference, highlight/fill colors, rendering flags,
border/feather values and an NPC predicate.

The nested builder self-identifies as:

`HighlightedNpc.HighlightedNpcBuilder(npc=…, highlightColor=…, fillColor$value=…, hull=…, tile=…, trueTile=…, swTile=…, swTrueTile=…, outline=…, name=…, nameOnMinimap=…, borderWidth$value=…, outlineFeather=…, render=…)`

Its setters populate the same state and construct `rs/s/o/a` directly.

These types are consumed by the already reviewed NPC Indicators runtime/configuration
surface, but R26's names do not rely on that contextual inference: both identities are
preserved literally.

## Acceptance boundary

Chat 2 does not promote R26. Main/Core may accept any desired subset only through an
explicit `semantic_acceptance_spec` bound to
`SEMREVIEW_F2B9678512AAB9EE7CC2`.
