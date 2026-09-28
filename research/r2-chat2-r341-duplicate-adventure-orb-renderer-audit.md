# Chat 2 — R341 duplicate AdventureOrbRenderer audit

R341 retains **no semantic proposal**.

The attempted `rs/i/b -> GameframeRenderer` recovery duplicated accepted R2 ownership:

- owner: `rs/i/b`
- stable id: `CLIENT_CLASS_000297`
- accepted R2 name: `AdventureOrbRenderer`
- R2 proposal: `SEMPROP_A8CC480C3293E2CB6A8E`

R2 also owns two exact fields in this class:

- `adventureOrbSprite`
- `adventureOrbHoverSprite`

## New corroborating evidence

The later exact-v308 audit showed that the class is broader than the original R2 evidence:
it owns/renderers HP, prayer, run, special-attack, adventure/event/promo/bank orb assets,
chat-channel button state, sidebar/gameframe presentation and layout state.

That evidence strengthens the understanding of the accepted class but Chat 2 does not
rename or supersede an already accepted R2 semantic identity.

The attempted R341 candidate/review/test artifacts were removed. R341 is therefore a
zero-retained duplicate/corroboration audit only.
