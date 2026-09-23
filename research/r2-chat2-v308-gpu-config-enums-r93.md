# Chat 2 — exact-v308 GPU configuration enums R93

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R93 is a separate non-canonical class-only review batch for the three GPU configuration
enums directly owned by the exact-v308 GPU settings/renderer stack.

## Deterministic review result

- candidate classes: **3**
- resolved proposals: **3**
- unresolved: **0**
- review ID: `SEMREVIEW_161E3E5F88A625FE06BD`
- field/method proposals: **0**

## Stable IDs

Core's exact `seed_lineage()` ordering gives:

- `rs/k/a/a` -> `CLIENT_CLASS_000315`
- `rs/k/a/b` -> `CLIENT_CLASS_000316`
- `rs/k/a/c` -> `CLIENT_CLASS_000317`

## `rs/k/a/a` -> `AntiAliasingMode`

Exact v308 preserves:

- `DISABLED("Disabled", 0)`
- `MSAA_2("MSAA x2", 2)`
- `MSAA_4("MSAA x4", 4)`
- `MSAA_8("MSAA x8", 8)`
- `MSAA_16("MSAA x16", 16)`

The enum stores the display string and sample count, returns the display value from
`toString()`, and exposes the sample count through its integer accessor.

The exact-v308 GPU settings holder defaults to `DISABLED`. R87 `GpuRenderer` consumes
the selected value, tests it against `DISABLED`, reads the requested sample count,
clamps it against the GL-supported maximum and preserves the diagnostic:

`AA samples: {}, max samples: {}, forced samples: {}`

RuneLite preserves `net.runelite.client.plugins.gpu.config.AntiAliasingMode` with the
same five constants, display strings and sample-count contract.

## `rs/k/a/b` -> `ColorBlindMode`

Exact v308 preserves exactly:

- `NONE`
- `PROTANOPE`
- `DEUTERANOPE`
- `TRITANOPE`

The GPU settings holder owns this enum and R87 `GpuRenderer` uploads its ordinal to the
renderer color-blindness uniform.

RuneLite preserves `ColorBlindMode` with the same four values and exposes it through the
GPU configuration as `colorBlindMode`.

## `rs/k/a/c` -> `SyncMode`

Exact v308 preserves exactly:

- `OFF`
- `ON`
- `ADAPTIVE`

The GPU settings holder owns this enum as the frame/swap synchronization mode. R87
`GpuRenderer` switches on its ordinal to derive the active synchronization behavior.

RuneLite `GpuPluginConfig` preserves a nested enum literally named `SyncMode` with the
same `OFF`, `ON`, `ADAPTIVE` values for the GPU plugin's vsync configuration.

## Naming boundary

The three names are supported independently by exact-v308 enum values and live renderer
consumers, then strengthened by matching RuneLite identifiers.

R93 does not name the surrounding SpawnPK settings holder simply because its fields now have
identified types, and it does not introduce any post-R2 field/method proposals.

## Acceptance boundary

Chat 2 does not promote R93. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_161E3E5F88A625FE06BD`.
