# Chat 2 — exact-v308 GPU compute mode / OS type R88

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R88 is a separate non-canonical enum-only semantic review batch for two types directly
consumed by R87 `GpuRenderer`.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_E36234AB09C85C8F04D8`
- field/method proposals: **0**

## Stable-ID verification

Core's exact `seed_lineage()` ordering gives:

- `rs/k/e$a` -> `CLIENT_CLASS_000334`
- `rs/k/j` -> `CLIENT_CLASS_000339`

R87 independently fixes:

- `rs/k/e` -> `GpuRenderer`
- `CLIENT_CLASS_000333`

## `rs/k/e$a` -> `ComputeMode`

The nested enum preserves exactly:

- `NONE`
- `OPENGL`
- `OPENCL`

R87 GpuRenderer initializes its mode to `NONE`.

During renderer startup it chooses:

- `OPENCL` on macOS;
- `OPENGL` on other supported platforms.

If OpenGL 4.3 is unavailable while the mode is `OPENGL`, exact v308 logs:

`disabling compute shaders because OpenGL 4.3 is not available`

and switches the mode back to `NONE`.

The enum then controls materially different renderer execution paths:

- `NONE` -> CPU-side scene processing;
- `OPENGL` -> OpenGL compute shaders / shader-storage and uniform-buffer path;
- `OPENCL` -> the dedicated OpenCL runtime path.

Historical corroboration is unusually strong: a public RuneLite-derived GPU implementation
preserves an enum literally named `ComputeMode` with the identical `NONE`, `OPENGL`,
`OPENCL` constants.

Exact v308 remains the semantic authority; the historical source strengthens the recovered
identifier rather than replacing binary evidence.

## `rs/k/j` -> `OSType`

The enum preserves exactly:

- `Windows`
- `MacOS`
- `Linux`
- `Other`

Its static initializer reads:

`System.getProperty("os.name", "generic")`

lowercases the result and maps:

- `mac` / `darwin` -> `MacOS`
- `win` -> `Windows`
- `nux` -> `Linux`
- otherwise -> `Other`

The public static accessor returns the detected singleton value.

R87 GpuRenderer and its OpenCL support consume this type directly when selecting
platform-specific rendering/compute behavior.

RuneLite preserves `net.runelite.client.util.OSType` with the same four enum constants and
the same `os.name` detection algorithm, giving exact historical-name corroboration in
addition to the v308 behavior.

## Naming boundary

These two names are stronger than ordinary descriptive semantic names because historical
RuneLite lineage independently preserves the same identifiers/enum identities.

R88 still does not assert source-code byte identity or promote either proposal canonically.

## Acceptance boundary

Chat 2 does not promote R88. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_E36234AB09C85C8F04D8`.
