# Chat 2 — exact-v308 BountyOverlay R210

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R210 is a separate non-canonical class-only review for the exact bounty-hunter overlay.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_CDC6A4C7D7DF2EF2A443`
- field/method proposals: **0**

## Stable ID

- `rs/l/f/a/c/c` -> `CLIENT_CLASS_000452` -> `BountyOverlay`

The stable ID was recomputed from the exact v308 sorted `rs/**.class` seed-lineage order.

## Exact self-label

The strongest evidence is inside the constructor itself.

Immediately after the base overlay constructor and initial state setup, the exact class
passes:

`BountyOverlay`

to its overlay-name setter.

The semantic proposal therefore reuses a surviving exact class-facing label rather than
inventing a name from neighboring packages.

## Exact bounty-hunter assets

The same class directly owns the bounty-hunter popup sprite family:

- `popups/bh record bg`
- `popups/bh target bg`
- `popups/bh target bg cursed`
- `popups/bhcompact1`
- `popups/bhcompact2`
- `popups/bh maximimize`
- `popups/bh combat`
- dynamic `popups/bh skull{n}`.

This independently corroborates the self-label.

## Exact actions

The class sends exact bounty command strings:

- `::bhtask`
- `::bhtaskinfo`
- `::bhtaskskip`
- `::skipbh`.

Its hover/interaction text includes:

- `Receive task`
- `Task info`
- `Skip target`
- `Skip bounty hunter task`
- `Maximize`
- `Minimize`
- `Hide/show task`.

These are native interactions of this class, not strings recovered from a separate
configuration file.

## Exact presentation state

The renderer owns exact presentation labels/state including:

- `Target:`
- `Kills: @whi@{n}`
- `Time Left: @whi@{value}`
- `Risk: {value}`
- `None`
- `Searching`
- `Searching.`
- `Searching..`
- `Searching...`.

It implements compact/maximized presentation and direct hover controls over that state.

## Naming boundary

`BountyOverlay` is proposed at **0.999** confidence.

Unlike most Chat 2 semantic names, the noun is preserved literally by the exact class
itself. The 0.999 value still preserves the workflow distinction between exact binary
evidence and canonical semantic acceptance.

R210 adds no field or method proposals.

## Acceptance boundary

Chat 2 does not promote R210. Main/Core may accept it only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_CDC6A4C7D7DF2EF2A443`.
