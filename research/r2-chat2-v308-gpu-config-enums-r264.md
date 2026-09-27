# Chat 2 — exact-v308 GPU config enums R264

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic review result

- `rs/s/e/a` -> `CLIENT_CLASS_000900` -> `ColorBlindMode`
- `rs/s/e/d$a` -> `CLIENT_CLASS_000904` -> `SyncMode`
- review: `SEMREVIEW_42E27EE38C3DD116543F`
- unresolved: **0**
- field/method proposals: **0**

## Exact bytecode evidence

`rs/s/e/a` is a four-value enum whose constant names survive verbatim:

- `NONE`
- `PROTANOPE`
- `DEUTERANOPE`
- `TRITANOPE`

RuneLite's GPU config source contains `ColorBlindMode` with exactly those values and order.

`rs/s/e/d$a` is nested directly under the already reviewed `GpuPluginConfig` class and preserves:

- `OFF`
- `ON`
- `ADAPTIVE`

RuneLite `GpuPluginConfig` declares nested `SyncMode` with exactly those values, and the GPU runtime maps them to swap intervals 0, 1 and -1.

## Deliberate exclusions

The remaining nearby unowned classes were not promoted:

- `rs/s/f/e` is an anonymous Gson `TypeToken<List<GroundMarkerPoint>>` helper;
- `rs/s/n/d` is a compiler-generated enum switch map;
- `rs/s/t/k` is a compiler-generated enum switch map.

R264 therefore adds only the two source-level enums whose identities are directly recoverable.

## Acceptance boundary

R264 remains class-only and non-canonical. Chat 2 performs no semantic acceptance.
