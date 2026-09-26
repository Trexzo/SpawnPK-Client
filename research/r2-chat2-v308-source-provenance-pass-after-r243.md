# Chat 2 — RuneLite source-provenance correction pass after R243

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

Historical RuneLite source at `68c819924cfd6bfb4848c71f74c121109f289d5a`, checked against exact-v308 bytecode/config surfaces, tightens four already-reviewed descriptive labels:

- R4 `rs/s/r/a` / `CLIENT_CLASS_000958`: `TileIndicatorConfig` -> `TileIndicatorsConfig`
- R9 `rs/s/f/b` / `CLIENT_CLASS_000908`: `GroundMarkersConfig` -> `GroundMarkerConfig`
- R9 `rs/s/f/d` / `CLIENT_CLASS_000910`: `GroundMarkersPlugin` -> `GroundMarkerPlugin`
- R9 `rs/s/e/d` / `CLIENT_CLASS_000903`: `GpuConfig` -> `GpuPluginConfig`

Current deterministic reviews:

- R4: `SEMREVIEW_DE8D18FF905B89D02488`
- R9: `SEMREVIEW_F015AA6B979CF43ECBE6`

R188/R190 and earlier correction notes are updated to point at the source-correct identities. Proposal counts are unchanged. No semantic acceptance is performed.
