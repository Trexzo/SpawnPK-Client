# Chat 2 — exact-v308 GameOptionsInterface R270

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic review result

- `rs/n/c/aC` -> `CLIENT_CLASS_000578` -> `GameOptionsInterface`
- review: `SEMREVIEW_D778A6CE6774A91AA5F9`
- unresolved: **0**
- field/method proposals: **0**

## Exact-v308 behavior

The class extends the interface-builder base and owns the client options/settings surface.

Exact controls include:

- brightness presets from Dark through Very Bright;
- resizable mode;
- split private chat;
- multiplied/x10 hits;
- new HP bar / new hit marks;
- Oldschool 07 graphics / ticks;
- roofs and fog distance;
- extended zoom/draw distance;
- left-click attack and target-only attack;
- left-click magic target-only behavior;
- shift dropping;
- particles/glow effects;
- player lighting;
- news broadcasts;
- combat overlay;
- desktop notifications;
- pet visibility/bank-all behavior;
- spawnable-item drop locking;
- prayer adjustments including Rigour/Augury swap.

The resource surface is equally bounded to options assets:
`/Options/SPRITE`, `/options/SPRITE`, `/options2/SPRITE` and `options/sprite`.

## Naming boundary

`GameOptionsInterface` is a descriptive exact-behavior name. It does not claim recovery of
the original obfuscated-away source identifier.

A full retained-review scan found no prior owner or semantic-name collision.

## Acceptance boundary

R270 remains class-only and non-canonical. Chat 2 performs no semantic acceptance.
