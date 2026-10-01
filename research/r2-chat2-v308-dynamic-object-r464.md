# Chat 2 — exact-v308 dynamic scene object R464

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

`rs/a/m` -> `CLIENT_CLASS_000076` -> `DynamicObject`

- proposal: `SEMPROP_8F8E78193D1FA2791867`
- review: `SEMREVIEW_2CEDCB4AF982E7296103`

## Stable-ID gap

The surrounding core-renderable lineage is already owned:

- 000075 / `rs/a/l` -> R31 `Projectile`
- 000077 / `rs/b` -> R54 `RSCanvas`

The exact v308 class-order gap fixes `rs/a/m` as `CLIENT_CLASS_000076`.

## Exact behavior

`rs/a/m` extends R30 `Renderable`.

Its constructor stores:

- object definition id;
- object shape/type;
- orientation;
- four tile-height samples;
- optional animation/Sequence id;
- optional random-start flag;
- optional prior Renderable.

Its render-model method resolves the ObjectDefinition and, when present, advances the
Sequence from the global client cycle before requesting the object's current Model.

R53 `ObjectManager` makes the decisive semantic split:

- static object definition with no animation/morph table -> build static Model directly;
- animated or morphable object -> construct `rs/a/m`.

Client's runtime scene-object animation path also replaces existing wall, decoration,
game-object and floor-decoration renderables with fresh `rs/a/m` instances.

When the previous Renderable is another `rs/a/m` using the same compatible Sequence, the
new object can inherit frame/tick state instead of restarting.

## Withheld neighboring gaps

- `CLIENT_CLASS_000056` / `rs/a/a/b` is a compiler-generated synthetic enum-switch
  table only.
- `CLIENT_CLASS_000066` / `rs/a/c$a` is an otherwise-unused inner integer container;
  exact v308 has no live owner/caller beyond InnerClasses metadata.

Neither receives a semantic proposal.

R464 remains non-canonical semantic research only.
