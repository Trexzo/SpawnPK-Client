# Chat 2 — exact-v308 interface arrow subsystem R211

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R211 is a non-canonical class-only review for the server-driven blinking interface-arrow
subsystem.

It was prepared after R206, then renumbered onto the live branch after concurrent Chat 2
work advanced the same branch through R207-R210. No concurrent commit was overwritten.

## Deterministic review result

- candidate classes: **4**
- resolved proposals: **4**
- unresolved: **0**
- review ID: `SEMREVIEW_172D2E1C9E486A022AD0`
- field/method proposals: **0**

## Stable IDs

- `rs/l/f/a/i/b` -> `CLIENT_CLASS_000470` -> `InterfaceArrowOverlay`
- `rs/l/f/a/i/d` -> `CLIENT_CLASS_000472` -> `InterfaceArrowPacketHandler`
- `rs/l/f/a/i/e` -> `CLIENT_CLASS_000473` -> `InterfaceArrowDirection`
- `rs/l/f/a/i/g` -> `CLIENT_CLASS_000475` -> `InterfaceArrowTarget`

The IDs come from the exact v308 sorted `rs/**.class` seed-lineage ordering. R211 does not
name the synthetic enum-switch helpers or the currently unreferenced small value record.

## Exact arrow resource identity

The exact client initializes four sprites:

- `orbs/arrow`
- `orbs/arrow 2`
- `orbs/arrow 3`
- `orbs/arrow 4`

`InterfaceArrowDirection` preserves exactly:

- `LEFT`
- `RIGHT`
- `UP`
- `DOWN`

and maps those enum values to the four arrow sprites.

`InterfaceArrowOverlay` stores one direction plus x/y offsets and draws the selected arrow
sprite at the live widget-render position plus those offsets.

## Exact blinking overlay behavior

`InterfaceArrowOverlay` extends the live render-component base `rs/l/f/b/d`.

It is registered through `rs/l/f/e` against a widget id.

Its draw path checks:

`Client.ff % 20 < 10`

before drawing, so the pointer is visible for half of every 20-tick cycle and hidden for
the other half.

The subsystem has explicit create, active, clear and auto-dismiss state.

## Exact Adventure Book consumer

The exact `AdventureBookInterfacePacketHandler` uses this subsystem when a chapter reward
becomes claimable.

It creates an arrow on widget `30390` with:

- direction: `DOWN`
- x offset: `35`
- y offset: `-30`

and marks it auto-dismissable.

This independently proves the class is a UI guidance/pointer overlay, not a decorative
arrow sprite abstraction.

## Exact ScriptPacket 24 handler

The exact ScriptPacket registry `rs/q/a/a/b` registers:

`rs/l/f/a/i/d`

at packet id **24**.

Its operations control only this subsystem:

- op **0** — clear the live interface arrow;
- op **1** — create an arrow from widget id, direction and offsets;
- op **3** — select an `InterfaceArrowTarget`;
- op **4** — derive a default pointer placement from a widget and create the arrow.

That fixes `rs/l/f/a/i/d` as `InterfaceArrowPacketHandler`.

## Exact target enum

`InterfaceArrowTarget` preserves exactly six enum literals:

- `ACHIEVEMENT`
- `INVENTORY`
- `EQUIPMENT`
- `MAGIC`
- `SETTINGS`
- `MISC`

ScriptPacket 24 op 3 maps selectors onto these values.

The main client gameframe renderer consumes the selected target while the arrow blink phase
is active and draws the RIGHT arrow sprite beside the corresponding sidebar/gameframe
location when that target is not already selected.

This is target UI-area state, separate from the arrow's geometric direction.

## Developer-command corroboration

The exact client command processor also accepts a widget id plus
`InterfaceArrowDirection.valueOf(...)`, derives offsets from widget dimensions, creates
the overlay and marks it auto-dismissable.

This is corroborating evidence only; the ScriptPacket and Adventure Book consumers already
fix the runtime semantics.

## Naming boundary

All four R211 names are descriptive exact-behavior recovery at **0.999** confidence.

They do not claim original source identifiers.

R211 deliberately withholds:

- `rs/l/f/a/i/a` — small currently unreferenced direction/int value record;
- `rs/l/f/a/i/c` and `rs/l/f/a/i/f` — compiler-generated enum switch helpers.

No field or method proposals are added.

## Acceptance boundary

Chat 2 does not promote R211. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_172D2E1C9E486A022AD0`.
