# Chat 2 — exact-v308 NPC-definition sprite overlay R208

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R208 is a separate non-canonical class-only review for an NPC-definition-keyed
2D sprite overlay, its mapping record and its ScriptPacket mutation handler.

## Deterministic review result

- candidate classes: **3**
- resolved proposals: **3**
- unresolved: **0**
- review ID: `SEMREVIEW_327E2DAE5E23C1568D05`
- field/method proposals: **0**

## Stable IDs

- `rs/l/f/a/e/a` -> `CLIENT_CLASS_000458` -> `NpcDefinitionSpriteOverlay`
- `rs/l/f/a/e/a$a` -> `CLIENT_CLASS_000459` -> `NpcDefinitionSpriteOverlayEntry`
- `rs/l/f/a/e/b` -> `CLIENT_CLASS_000460` -> `NpcDefinitionSpriteOverlayPacketHandler`

The IDs were recomputed from the exact v308 sorted `rs/**.class` seed-lineage order.

## Exact NPC-stage identity

`rs/l/f/a/e/a` extends the actor-bound overlay base `rs/l/f/b/b`.

Its constructor selects `rs/l/f/a.i`. The exact surviving stage enum fixes that value as:

`NPC_2D_STAGE`

The superclass is populated with the current `rs/a/j` actor and its `rs/d/d` definition
before this renderer runs.

## Exact NPC-definition key

The overlay looks up its entry using:

`currentActor.aG.x`

where `aG` is the actor's `rs/d/d` definition.

The exact `rs/d/d` class is backed by:

- `npc.dat`
- `npc.idx`

and both definition factories:

- `rs/d/d.b(int)`
- `rs/d/d.c(int)`

copy the requested integer definition index directly into `rs/d/d.x`.

That closes the mapping key as an **NPC definition id** rather than a scene index or
transient actor index.

## Exact sprite projection

For a matching definition id, the overlay entry supplies exactly four integers:

1. sprite index;
2. x offset;
3. y offset;
4. height/world-z offset.

The draw path adds the last three values to the NPC actor's world x/y/height coordinates,
projects the resulting position to screen coordinates, then draws:

`Client.fE[spriteIndex]`

at that projected point.

The parent mapping supports only:

- add/update one definition mapping;
- remove one definition mapping;
- clear all mappings.

## Exact nested entry

`rs/l/f/a/e/a$a` contains only the four payload integers plus its synthetic parent
reference.

It is created only by the parent overlay's add path and consumed only by its NPC-stage draw
path.

This fixes it as the mapping entry rather than an independent renderer.

## Exact ScriptPacket handler

`rs/l/f/a/e/b` extends the reviewed exact ScriptPacket handler base
`rs/q/a/a/a`.

Its operation grammar is:

- op **0** — clear/reset live overlay state;
- op **1** — read five integers and add/update one definition-to-sprite mapping;
- op **2** — read one integer and remove that definition mapping.

The overlay constructor places its live instance into the handler's static target slot, and
the handler mutates no unrelated subsystem.

## Naming boundary

All three names are descriptive exact-behavior recovery at **0.999** confidence.

The name does not assert an original developer identifier or a specific gameplay meaning
for the sprite. The exact evidence proves only:

- NPC 2D render stage;
- NPC-definition-id key;
- client sprite index;
- world-coordinate offsets;
- packet-driven mapping lifecycle.

Therefore R208 deliberately uses the neutral noun `NpcDefinitionSpriteOverlay` rather
than inventing a domain label such as quest marker, boss icon or status icon.

## Acceptance boundary

Chat 2 does not promote R208. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_327E2DAE5E23C1568D05`.
