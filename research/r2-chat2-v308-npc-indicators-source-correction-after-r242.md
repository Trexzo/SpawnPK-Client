# Chat 2 — NPC Indicators source-identity correction after R242

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

Historical RuneLite source at `68c819924cfd6bfb4848c71f74c121109f289d5a`, plus the exact-v308 `npcindicators` config group and direct plugin pairing, resolves the older descriptive R4 label:

- `rs/s/o/d` / `CLIENT_CLASS_000944`: `NpcHighlightConfig` -> `NpcIndicatorsConfig`

R9 already had the source-correct runtime identity `NpcIndicatorsPlugin`; its pairing evidence is updated to reference `NpcIndicatorsConfig`. The NPC Indicators proposal itself is unchanged; after later source corrections elsewhere in R9, the current R9 review is `SEMREVIEW_F015AA6B979CF43ECBE6`.

The corrected R4 review is `SEMREVIEW_DE8D18FF905B89D02488`. R4 proposal count remains **9**. No semantic acceptance is performed.
