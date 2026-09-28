# Chat 2 — exact-v308 raid list row-background overlay R313

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R313 resolves the final previously withheld concrete helper inside the `rs/n/c/d` raid-interface package.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_7C8BFB0495B431AF01EE`
- proposal ID: `SEMPROP_2AB9BC55B8F9C03632D0`
- field/method proposals: **0**

## Stable ID

`rs/n/c/d/g` -> `CLIENT_CLASS_000657` -> `RaidListRowBackgroundOverlay`

The stable slot follows directly after R300
`rs/n/c/d/f` -> `CLIENT_CLASS_000656` in the exact v308 baseline ordering.

## Sole exact owner

The only exact-v308 class that references `rs/n/c/d/g` is the already-reviewed
`rs/n/c/d/a` -> `RaidNavigationInterface`.

Its static initialization constructs exactly two instances:

- `new rs/n/c/d/g(32316, 20)`;
- `new rs/n/c/d/g(32481, 30)`.

During raid-interface initialization those are registered through `OverlayManager` on:

- widget **32317**;
- widget **32486**.

The same owner registers the R300 `RaidAfflictionTomeProgressOverlay` on widget **32465**.
There is no second-domain or non-raid caller.

## First list: raid party member/status surface

The already-reviewed `RaidPartyHubInterface` builds scrolling container **32316**.

Immediately surrounding that container are the exact labels:

- `Members (1/5)`;
- `Current Status`;
- the active raid description.

The container constructs twenty row slots. Their y positions advance in exact **18-pixel**
steps. The first row also carries the exact raid-owner sprite, while later rows populate the
member/status cells used by the party interface.

R313's first overlay instance uses this exact container id and the same row count: **20**.

## Second list: public raid-party surface

The already-reviewed `RaidPartyListInterface` builds scrolling container **32481**.

Its exact presentation includes:

- `Party<tab=150>Size<tab=225>Raid Type & Difficulty`;
- `Refresh party list`;
- `Join party`;
- resource `raids/list`.

The container creates **30** list rows.

R313's second overlay instance uses this exact container id and the same row count: **30**.

## Exact renderer behavior

`rs/n/c/d/g` extends the widget-overlay base `rs/l/f/b/d`.

Its complete render method:

1. resolves the constructor-supplied backing widget;
2. derives drawing geometry from that widget;
3. iterates exactly the constructor-supplied row count;
4. alternates only between colors **3814187** and **4274480**;
5. advances the row origin by exactly **18 pixels** each iteration;
6. emits the colored fills through the shared raster rectangle routine.

It has no packet parser, text rendering, input handling, list mutation or unrelated behavior.

## Why the earlier hold is now cleared

The earlier frontier correctly withheld this class because its body alone looked like a
generic alternating-row painter.

The missing evidence is now the complete owner/consumer join: the only two constructed
instances are attached to the two exact raid list containers, and their constructor row
counts exactly match those containers' row materialization counts.

Therefore `RaidListRowBackgroundOverlay` is narrower than a generic stripe painter while
remaining conservative about whether a row belongs to a specific raid subtype.

Confidence is **0.998**. The name is descriptive exact-behavior recovery; no surviving
original Java identifier is claimed.

## Acceptance boundary

R313 remains class-only and non-canonical. Chat 2 performs no semantic acceptance.
