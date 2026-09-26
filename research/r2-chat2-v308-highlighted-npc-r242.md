# Chat 2 — exact-v308 HighlightedNpc recovery R242

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic result

- `rs/s/o/a` -> `CLIENT_CLASS_000940` -> `HighlightedNpc`
- `rs/s/o/a$a` -> `CLIENT_CLASS_000941` -> `HighlightedNpcBuilder`
- review: `SEMREVIEW_F2B9678512AAB9EE7CC2`
- unresolved: **0**
- field/method proposals: **0**

## Exact identity

This pair is self-identifying in exact v308:

- the value object emits `HighlightedNpc(npc=...)`
- the nested builder emits `HighlightedNpc.HighlightedNpcBuilder(npc=...)`

The fields cover NPC, highlight/fill colors, hull/tile/true-tile variants, outline, name/minimap name, border width, outline feather and a render predicate.

Current RuneLite `net.runelite.client.game.npcoverlay.HighlightedNpc` independently matches that full Lombok value/builder field set, including the fill-color and border-width defaults.

## Acceptance boundary

R242 remains non-canonical. Chat 2 performs no semantic acceptance.
