# Chat 2 — exact-v308 shared overlay particle core R204

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R204 is a separate non-canonical class-only review for the generic UI-overlay particle
record, direction enum and live manager/emitter.

It deliberately uses `OverlayParticle*` names because R50 already owns the distinct generic
name `Particle` for the world/scene particle engine under `rs/r/*`.

## Deterministic review result

- candidate classes: **3**
- resolved proposals: **3**
- unresolved: **0**
- review ID: `SEMREVIEW_8523ED886552313C398D`
- field/method proposals: **0**

## Stable IDs

- `rs/l/f/a/f/a` -> `CLIENT_CLASS_000461` -> `OverlayParticle`
- `rs/l/f/a/f/b` -> `CLIENT_CLASS_000462` -> `OverlayParticleDirection`
- `rs/l/f/a/f/c` -> `CLIENT_CLASS_000463` -> `OverlayParticleManager`

## Independent particle noun

The exact client developer command:

`particle`

resolves through the command processor to the live overlay manager:

`rs/l/f/e.g()`

which returns `rs/l/f/a/f/c`.

The command invokes its emission helper twice with explicit particle count, position and
color arguments.

That fixes this family as particles independently of the Donation Cart analysis.

## OverlayParticle

Each `rs/l/f/a/f/a` record owns the complete transient render state for one colored
overlay particle:

- current x/y;
- original x/y;
- width/height;
- packed color;
- alpha;
- randomized finite lifetime;
- horizontal direction;
- movement/curve parameters;
- creation timestamp.

Its draw method renders one alpha-blended rectangle.

Its update method:

- moves x according to LEFT/RIGHT;
- updates y from its movement curve;
- fades alpha over elapsed lifetime;
- exposes expiry once elapsed time reaches its lifetime.

The same class is emitted by multiple already-reviewed UI surfaces, including Donation
Shopping Cart, raid UI effects, item dialogue and mailbox presentation.

## OverlayParticleDirection

The enum literals survive exactly:

- `RIGHT`;
- `LEFT`.

The particle update path increases x for RIGHT and decreases x for LEFT. The manager assigns
those directions when creating mirrored groups.

## OverlayParticleManager

`rs/l/f/a/f/c` extends the live overlay renderer base.

It owns:

- the active particle list;
- a per-frame removal list.

Each frame it draws/updates active particles, identifies expired entries, removes them and
clears the removal staging list.

Its emission method:

- creates four groups for each request;
- alternates LEFT/RIGHT motion;
- assigns vertical motion/curve parameters;
- applies size/color/alpha;
- caps the active list at **1000**.

Exact consumers include the client `particle` developer command plus several independent UI
subsystems. This establishes a reusable overlay particle manager rather than a domain-specific
cart/raid class.

## Naming boundary

`OverlayParticle` and `OverlayParticleManager` are descriptive at **0.998**.

`OverlayParticleDirection` is **0.999** because its RIGHT/LEFT identity survives exactly.

R204 does not reuse R50's `Particle` name and does not claim these are the game's
world/scene particle simulation classes.

## Acceptance boundary

Chat 2 does not promote R204. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_8523ED886552313C398D`.
