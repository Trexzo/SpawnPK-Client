# Chat 2 — exact-v308 tooltip content + overlay R207

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R207 is a separate non-canonical class-only review for the generic client tooltip
presentation payload and its global hover renderer.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_AC7EFCB00B7B58248530`
- field/method proposals: **0**

## Stable IDs

- `rs/l/f/a/j/a` -> `CLIENT_CLASS_000476` -> `TooltipContent`
- `rs/l/f/a/j/b` -> `CLIENT_CLASS_000477` -> `TooltipOverlay`

The stable IDs are fixed by the exact v308 sorted `rs/**.class` seed-lineage order.
They are immediately before R205's independently verified
`CLIENT_CLASS_000478` / `rs/l/f/a/k/a`, but no semantic identity is inferred from
adjacency.

## Exact tooltip noun

The exact overlay-position enum `rs/l/f/l` preserves the literal:

`TOOLTIP`

The tooltip settings interface `rs/s/s/a` also contains exact descriptions including:

- background color for tooltip overlays;
- inner/outer border colors for tooltip overlays;
- item tooltip visibility;
- entity hover tooltip visibility;
- equipment/inventory/bank tooltip visibility.

The live tooltip settings/producer `rs/s/s/b` consumes that configuration and routes
tooltip records into `rs/l/f/a/j/b`.

This provides an independent exact noun rather than naming the classes only from geometry.

## TooltipContent

The exact hover-region helper `rs/l/q$a` owns a rectangular hit region plus an
`rs/l/f/a/j/a` payload.

When its displayed text/range changes, it constructs the payload from the hovered substring.
When the mouse lies inside the region, `rs/l/q` passes that exact payload to
`rs/l/f/a/j/b`.

The record stores:

- primary tooltip text;
- presentation booleans;
- an optional item-id array;
- an optional supplemental string array;
- an optional integer selector;
- an additional presentation flag.

Those fields are consumed by the centralized renderer for plain text and richer
item/icon/stat-line layouts.

The class is therefore presentation content/state rather than a renderer or domain object.

## TooltipOverlay

`rs/l/f/e` constructs exactly one `rs/l/f/a/j/b` instance, registers it globally with the
overlay system and exposes it through `f()`.

Independent consumers feed it hover content, including:

- generic rectangular hover regions;
- combat-overlay controls;
- entity/item hover handling;
- sidebar/UI entries.

Exact combat-overlay tooltip strings include:

- `Maximize`;
- `Minimize`;
- `Hide/show task`;
- `Receive task`;
- `Task info`;
- `Skip target`;
- `Skip bounty hunter task`.

Its render path:

- anchors from live mouse coordinates `Client.hP` / `Client.hQ`;
- measures multiline text;
- computes a tooltip box;
- clamps placement to the visible client viewport;
- draws configured background/border/text;
- supports optional item sprites and richer stat lines from `TooltipContent`.

This is the shared tooltip overlay rather than a domain-specific interface renderer.

## Naming boundary

Both names are descriptive exact-behavior recovery at **0.999** confidence.

`TooltipContent` does not assert that the original source called the payload “Content”; it
states only that the class is the data/presentation object consumed by the exact tooltip
renderer.

`TooltipOverlay` is fixed by the exact tooltip noun, global overlay registration,
mouse-relative rendering and independent hover consumers.

R207 adds no field or method proposals.

## Acceptance boundary

Chat 2 does not promote R207. Main/Core may accept either class only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_AC7EFCB00B7B58248530`.
