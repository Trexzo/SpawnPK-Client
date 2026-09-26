# Chat 2 — exact-v308 BossBarOverlay ScriptPacket 7 R125

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R125 is a separate non-canonical class-only review for the direct ScriptPacket handler
whose complete implemented selector surface exclusively controls the exact
`BossBarOverlay`.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_589B61E23E23DCA823B1`
- field/method proposals: **0**

## Stable ID

`rs/l/f/a/c/b` -> `CLIENT_CLASS_000451` -> `BossBarOverlayPacketHandler`

R115 registers this class directly as ScriptPacket **7**.

## Exact overlay identity

The handler owns one `rs/l/f/a/c/a` instance.

That class preserves the exact literal:

`BossBarOverlay`

and the default percentage String:

`100%`

The packet handler lazily constructs this exact overlay when needed and attaches it through
the live overlay manager before applying packet state.

## Complete selector surface

The implemented selector branches are **1, 2, 4, 5, 6 and 7**.
Selector **3** has no branch.

Every implemented branch writes only the owned `BossBarOverlay`:

- selector 1 resets overlay state and toggles its packet-controlled visibility/state flag;
- selector 2 writes two integer overlay-state values;
- selector 4 reads current and maximum integers, derives a percentage, and updates the
  current/max/percentage display state;
- selector 5 writes a packet-provided String;
- selector 6 writes an icon-prefixed numeric String using the surviving
  `<img=381>...` format;
- selector 7 reads current and maximum integers, derives the same percentage state, and
  writes one packet-provided String into the paired progress display fields.

For the ratio selectors, exact v308 handles the boundary cases directly:

- current == max -> 100%;
- current == 0 -> 0%;
- otherwise -> current / max * 100.

There is no write into an unrelated Client subsystem.

## Naming boundary

`BossBarOverlayPacketHandler` is **0.999**.

The exact ScriptPacket registration and surviving `BossBarOverlay` identity literal agree,
and the whole-class selector surface targets only that overlay. This is stronger than a
descriptive domain guess, while remaining a non-canonical Chat 2 proposal.

R125 remains class-only.

## Deliberate exclusion remains

ScriptPacket 32 (`rs/q/a/a/a/a`) remains unnamed. R125 does not relax the whole-class
coherence rule.

## Acceptance boundary

Chat 2 does not promote R125. Main/Core may accept this proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_589B61E23E23DCA823B1`.
