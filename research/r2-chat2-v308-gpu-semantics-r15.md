# Chat 2 — exact-v308 GPU semantics R15

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R15 is a separate non-canonical class-only semantic review batch. It does not alter
Main/Core's accepted R2 semantic authority or prior R3-R14 review batches.

## Deterministic review result

- candidate classes: **5**
- resolved proposals: **5**
- unresolved: **0**
- review ID: `SEMREVIEW_ED182A9515E49F3482BC`
- field/method proposals: **0**

## GPU plugin

- `rs/s/e/c` -> `GpuPlugin`

The class extends the plugin base `rs/s/a`, injects the GPU configuration/client/UI
dependencies, owns GPU navigation/panel state and reacts to `ConfigChanged`. Exact runtime
metadata includes `GPU Mode`, `GPU Mode (Beta)`, group `gpu`, description
`Enhance the graphics and performance of the game`, panel metadata and
`gpu_icon.png`.

## GPU configuration enums

The live `GpuConfig` interface provides exact return-type bindings:

- `antiAliasingMode` / `Anti Aliasing` -> `rs/k/a/a` -> `AntiAliasingMode`
- `colorBlindMode` / `Colorblindness Correction` -> `rs/k/a/b` -> `ColorBlindMode`
- `vsyncMode` / `Vsync Mode` -> `rs/k/a/c` -> `VsyncMode`
- `uiScalingMode` / `UI scaling mode` -> `rs/s/e/e` -> `UiScalingMode`

Exact enum constants further corroborate the roles:

- AntiAliasingMode: `DISABLED`, `MSAA_2`, `MSAA_4`, `MSAA_8`, `MSAA_16`
- ColorBlindMode: `NONE`, `PROTANOPE`, `DEUTERANOPE`, `TRITANOPE`
- UiScalingMode: `NEAREST`, `LINEAR`, `CATMULL_ROM`, `MITCHELL`
- VsyncMode includes `ADAPTIVE` and is bound directly by the config method.

The duplicate-looking `rs/s/e/a` colorblind enum is deliberately not proposed here because
the live `GpuConfig` return type for `colorBlindMode` is `rs/k/a/b`, not that class.

## Acceptance boundary

Chat 2 does not promote R15. Main/Core may accept any desired subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_ED182A9515E49F3482BC`.
