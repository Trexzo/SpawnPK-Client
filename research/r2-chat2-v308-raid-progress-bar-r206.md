# Chat 2 — exact-v308 raid progress bar R206

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R206 resolves the one intentionally unnamed sibling left behind by R203 after obtaining
independent exact-v308 consumer and state evidence.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_2EB868EB5DFC9004D925`
- field/method proposals: **0**

## Stable ID

- `rs/l/f/a/g/b` -> `CLIENT_CLASS_000465` -> `RaidProgressBar`

The stable ID is fixed by the exact v308 sorted `rs/**.class` seed-lineage order and sits
between the independently verified R203 siblings:

- `rs/l/f/a/g/a` -> `CLIENT_CLASS_000464` -> `RaidPartyOverlay`
- `rs/l/f/a/g/c` -> `CLIENT_CLASS_000466` -> `RaidTheatreBar`

The semantic identity is **not** inferred from adjacency.

## Exact raids-only consumer

An exact class-reference scan over the pinned v308 JAR finds the class consumed externally
only by `rs/n/c/d/d`.

That handler:

- contains the exact literal `raids`;
- owns the R203 `RaidPartyOverlay`;
- owns this component;
- owns the R203 `RaidTheatreBar`.

This independently fixes the owning subsystem as raids.

## Exact progress state

The component's two-integer update method stores:

- current value;
- total value.

It computes:

`current / total * 100.0`

and formats its centered display as:

`current / total @yel@(percent%)`

using the exact surviving concat recipe:

`\u0001 / \u0001 @yel@(\u0001%)`

The component therefore has explicit progress-bar state rather than generic text-overlay
state.

## Exact rendering behavior

The draw path uses a fixed:

- width: **500**
- height: **18**

It converts its percentage to a fraction, calculates:

`ceil(500 * fraction)`

for the filled width, draws the background and filled regions, then draws the
current/total/percent text centered over the bar.

A boolean state toggles the bar's presentation/color mode.

## Exact packet/update join

Within `rs/n/c/d/d`:

- operation **15** registers this component alongside the raid theatre bar;
- operation **17** reads two integers and calls the component's current/total update method;
- the same operation then reads a state selector and applies the component's boolean
  presentation mode.

The raids handler, packet-fed current/total state and fixed progress-bar rendering form a
closed exact-v308 evidence chain.

## Why R203 withheld it

R203 deliberately left `rs/l/f/a/g/b` unnamed because package adjacency alone did not
prove a defensible domain noun.

R206 supplies the missing independent evidence:

- raids-only external consumer;
- explicit current/total percentage semantics;
- fixed bar-fill rendering;
- direct registration/update operations inside the raids handler.

The prior withholding was therefore correct and is now resolved without lowering the
evidence standard.

## Naming boundary

`RaidProgressBar` is descriptive exact-behavior recovery at **0.999** confidence.

It does not claim an original source identifier. It combines only independently fixed
facts:

- subsystem: raids;
- behavior: progress bar.

R206 adds no field or method proposals.

## Acceptance boundary

Chat 2 does not promote R206. Main/Core may accept it only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_2EB868EB5DFC9004D925`.
