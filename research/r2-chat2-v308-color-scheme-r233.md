# Chat 2 — exact-v308 RuneLite ColorScheme source recovery R233

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R233 resolves one previously-unreviewed desktop UI class directly from the pinned v308 JAR.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_E9514DAB12076DBACF0A`
- field/method proposals: **0**

## Stable ID

- `rs/gui/d` -> `CLIENT_CLASS_000264` -> `ColorScheme`

## Exact-v308 bytecode

The pinned `client(6).jar` was independently materialized from the user's Library and
verified SHA-256-identical to the exact v308 authority.

`rs/gui/d` has exactly fifteen public static `java.awt.Color` fields. Its class initializer
constructs these values, in exact order:

- `220,138,0`
- `220,138,0,120`
- `30,30,30`
- `40,40,40`
- `77,77,77`
- `165,165,165`
- `60,60,60`
- `35,35,35`
- `55,240,70`
- `230,30,30`
- `230,150,30`
- `110,225,110`
- `240,207,123`
- `50,160,250`
- `25,25,25`.

RuneLite `net.runelite.client.ui.ColorScheme` contains the same fifteen colors in the same
order and values: brand orange / transparent orange, the gray palette and hover colors,
progress complete/error/in-progress, GE price/alch/limit, and scroll-track color.

This is a whole-class value match rather than package adjacency.

## Naming boundary

`ColorScheme` is recovered at confidence **0.999**. RuneLite source supplies source-name
provenance; pinned exact-v308 bytecode remains runtime authority.

## Acceptance boundary

Chat 2 does not promote R233. Main/Core may accept it only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_E9514DAB12076DBACF0A`.
