# R2 Chat 2 — initial exact-v308 semantic seed

This seed is derived directly from the supplied exact v308 JAR. Private `SpawnPK-Src`
research was used only to identify promising areas to independently re-check; its private
content is not copied into this public repository.

Exact authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Re-proved method intents

Static bytecode inspection of `rs.Client` establishes:

| Raw member | Exact client behavior | Candidate |
| --- | --- | --- |
| `a(J)V` | friend-list preflight/state append; opcode 188 + i64 key | `addFriend` |
| `f(J)V` | removes/compacts friend state; opcode 215 + i64 key | `removeFriend` |
| `h(J)V` | ignore-list preflight/state append; opcode 133 + i64 key | `addIgnore` |
| `i(J)V` | removes/compacts ignore state; opcode 74 + i64 key | `removeIgnore` |

These are semantic behavior labels, not recovered original source identifiers.

## Re-proved login-reward field

`LOGIN_REWARD_IDX` parsing stores its integer directly into:

`rs/Client.P:I`

The renderer `rs/l/b/d` reads the same field specifically in the interface-root/container
join:

- root `50600`
- item container `50615`

and compares rendered slot indices against it. The deliberately conservative candidate is:

`loginRewardContainerIndex`

No claim is made that this is a server-side streak day, claim day, eligibility index, or
other stronger gameplay concept.

## Re-proved Adventure orb role

`rs/i/b` directly constructs:

- `orbs/adventure_orb`
- `orbs/adventure_orb_hover`

and renders the Adventure Book hover text. R1 also uniquely correlates the alternate client
class `rs/j/b.class` to v308 `rs/i/b.class`.

Candidate class role:

`AdventureOrbRenderer`

Two direct resource-backed field candidates are also emitted:

- `f:Lrs/l/F;` -> `adventureOrbSprite`
- `g:Lrs/l/F;` -> `adventureOrbHoverSprite`

## Boundary

All names remain `CANDIDATE`, non-canonical, and outside remap state. The core/integration
lane must define the eventual semantic-promotion boundary before any candidate becomes an
accepted remap.
