# Chat 2 — R464 duplicate DynamicObject corroboration audit

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

R464 retains **no semantic proposal**.

The attempted recovery:

- `rs/a/m`
- `CLIENT_CLASS_000076`
- `DynamicObject`
- proposal `SEMPROP_8F8E78193D1FA2791867`

is exactly the existing R31 authority, including the same deterministic proposal ID.

R31 therefore remains the sole semantic owner.

## Additional corroboration found during R464

Direct exact-v308 bytecode analysis strengthened the existing R31 interpretation:

- R53 ObjectManager constructs `rs/a/m` specifically when a placed object definition has
  animation or morph/child-definition state; otherwise it constructs the static Model directly.
- Client runtime object-animation handling replaces existing wall objects, wall decorations,
  game objects and floor decorations with `rs/a/m` wrappers while preserving object
  id/type/orientation state.
- the constructor can inherit animation frame/tick state from a prior `rs/a/m` using the
  same compatible Sequence rather than restarting it.

These findings corroborate R31 `DynamicObject`; they do not create a second proposal.

## Nearby withheld gaps

- `rs/a/a/b` is a compiler-generated enum-switch table.
- `rs/a/c$a` is an otherwise-unused four-int inner container with no live exact-v308
  caller/owner beyond metadata.

Neither receives a semantic proposal.

R464 is correction/corroboration research only.
