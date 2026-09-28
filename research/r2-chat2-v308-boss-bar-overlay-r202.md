# Chat 2 — exact-v308 BossBarOverlay R202

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R202 is a separate non-canonical class-only review for the client-native boss-bar overlay
owned by the R125 ScriptPacket 7 handler.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_614FACE224251DF0BFE0`
- field/method proposals: **0**

## Stable ID

`rs/l/f/a/c/a`
-> `CLIENT_CLASS_000450`
-> `BossBarOverlay`

The R1 stable ID is re-derived from the exact v308 seed ordering used by
`seed_lineage`: classes sort by internal name under the `rs/` prefix, placing this class
immediately before the already-reviewed `CLIENT_CLASS_000451`
`BossBarOverlayPacketHandler`.

## Exact surviving identity

The constructor writes the exact identity literal:

`BossBarOverlay`

into the shared positioned-overlay base.

It also configures one positioned/layered overlay surface and fixed presentation bounds.

## Reset lifecycle

The class has one explicit reset method that restores:

- progress to **0**;
- exact default foreground/background bar colors;
- both percentage display strings to `100%`;
- both auxiliary display strings to empty.

That reset is the same one invoked by R125 ScriptPacket 7.

## Progress rendering

The renderer treats the integer progress field as a percentage:

- divides by **100.0**;
- uses a fixed **220-pixel** bar width;
- derives the foreground width from that ratio;
- draws the bar and border;
- renders the packet-fed percentage/display strings on the same surface.

Compact/default presentation branches change layout only; they consume the same boss-bar
state and do not introduce a second responsibility.

## Independent packet ownership

R125 already fixed:

`rs/l/f/a/c/b`
-> `CLIENT_CLASS_000451`
-> `BossBarOverlayPacketHandler`

as exact ScriptPacket **7**.

That handler exclusively creates and mutates this `BossBarOverlay` instance, including
progress, colors and display strings.

## Naming boundary

`BossBarOverlay` is **0.999**.

The class noun survives literally, the whole class is one boss-bar render/reset lifecycle,
and R125 independently fixes the exclusive packet owner. No inferred narrower boss type is
introduced.

## Acceptance boundary

Chat 2 does not promote R202. Main/Core may accept this proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_614FACE224251DF0BFE0`.
