# Chat 2 — exact-v308 GPU runtime settings/control R86

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R86 is a separate non-canonical class-only semantic review batch for the static runtime
bridge between R15 `GpuConfig` and the actual client renderer.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_D1F558732D8E7A698664`
- field/method proposals: **0**
- confidence: **0.997**

## Stable-ID verification

Core's exact `seed_lineage()` ordering gives:

- `rs/k/b` -> `CLIENT_CLASS_000318`

## `rs/k/b` -> `GpuRuntimeSettings`

R15 already identifies the public GPU configuration layer:

- `AntiAliasingMode`
- `ColorBlindMode`
- `VsyncMode`
- `UiScalingMode`
- `GpuPlugin`

The exact R15 GpuPlugin writes those current configuration values directly into
`rs/k/b` static fields. That includes the typed anti-aliasing, color-blind and vsync enum
values as well as scaling and feature flags.

This class is also where those settings cross into live renderer state.

Exact runtime transition strings include:

- `Initializing GPU - please wait.`
- `Disabling GPU - please wait.`
- `::gpuflagon`
- `::gpuflagoff`

The enable path creates/initializes the GPU renderer objects through Client. The disable
path tears the GPU path down and returns the client to the software-rendered state.

## Persistence identity

The class owns the exact file:

`gpu.properties`

and schedules the exact task:

`SaveGpuSettings`

The file-backed portion stores and restores:

- `stretch_width`
- `stretch_height`

through `java.util.Properties`.

## Consumer boundary

Direct consumers include:

- `Client`;
- R48 `RSApplet`;
- R15 `GpuPlugin`;
- the live GPU renderer stack.

GpuPlugin configuration-change handling copies its current config values into this class and
uses its transition methods when GPU mode changes.

## Naming boundary

`GpuRuntimeSettings` is deliberately descriptive. It is distinct from the R15
configuration interface/plugin layer and expresses the exact static settings + renderer
transition role.

Confidence is **0.997** rather than 0.999 because the behavior is exact while the English
class noun is semantic recovery rather than a surviving original identifier.

## Acceptance boundary

Chat 2 does not promote R86. Main/Core may accept the proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_D1F558732D8E7A698664`.
