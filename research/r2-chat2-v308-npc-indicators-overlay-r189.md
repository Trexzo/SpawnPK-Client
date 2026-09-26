# Chat 2 — exact-v308 NPC Indicators overlay R189

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R189 is a separate non-canonical class-only review for the live overlay owned by the
reviewed NPC Indicators plugin.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_235A3BDCAF9E0F68D3A5`
- field/method proposals: **0**

## Stable ID

`rs/s/o/c` -> `CLIENT_CLASS_000942` -> `NpcIndicatorsOverlay`

## Exact plugin ownership

Reviewed `NpcIndicatorsPlugin` stores exactly one `rs/s/o/c` overlay instance.

Its lifecycle registers and unregisters that instance through the live overlay manager and
clears/rebuilds the plugin's NPC highlight state around the same transitions.

## Exact render responsibility

The overlay target is `rs/a/j`, independently recovered in R30 as `Npc`.

For the current NPC it asks `NpcIndicatorsPlugin` for the reviewed R26
`HighlightedNpc` value. If no definition exists, it renders nothing.

The `HighlightedNpc` flags control the complete rendering surface:

- model hull;
- tile;
- true tile;
- south-west tile variants;
- outline;
- overhead name;
- minimap name.

Colors, border width, feather and render predicate come from that same reviewed value.

No non-NPC subsystem is touched.

## Excluded sibling

`rs/s/o/b` is a separate NPC snapshot/cache-like record storing name/id/coordinate and
WorldPoint-list state. Its higher-level identity is not yet specific enough for a semantic
proposal, so R189 deliberately leaves it unnamed.

## Confidence boundary

`NpcIndicatorsOverlay` is **0.999**.

The name is descriptive exact-behavior recovery grounded in plugin lifecycle, target type and
the reviewed `HighlightedNpc` render model.

## Acceptance boundary

R189 remains class-only and non-canonical. Main/Core may accept the proposal only through an
explicit `semantic_acceptance_spec` bound to `SEMREVIEW_235A3BDCAF9E0F68D3A5`.
