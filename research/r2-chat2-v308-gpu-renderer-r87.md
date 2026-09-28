# Chat 2 — exact-v308 GPU renderer R87

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R87 is a separate non-canonical class-only semantic review batch for the live LWJGL/OpenGL
rendering engine activated by R86 `GpuRuntimeSettings`.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_2974461D01463567714E`
- field/method proposals: **0**
- confidence: **0.998**

## Stable-ID verification

Core's exact `seed_lineage()` ordering gives:

- `rs/k/e` -> `CLIENT_CLASS_000333`

## `rs/k/e` -> `GpuRenderer`

R86's exact GPU-enable path constructs this class directly and stores it on Client as the
active GPU object.

The class owns:

- `org.lwjgl.opengl.GLCapabilities`;
- an OpenGL debug callback;
- RuneLite's AWT/OpenGL context;
- shader/program state;
- GPU texture and vertex-array state;
- scene, temporary, output and uniform buffers;
- projection/uniform state used by the live scene renderer.

Exact diagnostic/capability strings include:

- `OpenGL 3.1 is required but not available`
- `disabling compute shaders because OpenGL 4.3 is not available`
- `Error starting GPU plugin`

The class directly calls the OpenGL rendering API, including:

- `glBindTexture`
- `glBindVertexArray`
- `glDispatchCompute`
- `glUniform*`
- `glVertexAttrib*`
- texture/buffer/VAO creation and deletion paths.

Surviving resource/debug labels include:

- `scene vertex buffer`
- `scene tex buffer`
- `out vertex buffer`
- `tmp vertex buffer`
- `uniform buffer`
- `uniforms`

This is the renderer itself, not merely GPU preferences or the R15 plugin/config UI.

## Boundary with R15/R86

- R15 owns the public GPU plugin/config semantics.
- R86 owns the static runtime settings and GPU enable/disable bridge.
- R87 owns the actual LWJGL/OpenGL rendering engine.

R87 deliberately stops at the outer engine. Its nested state object and the adjacent
shader/buffer/scene helpers are not named merely because their owner is now understood.

## Naming boundary

`GpuRenderer` is a conservative semantic recovery name derived from exact runtime
activation and rendering behavior.

Confidence is **0.998** because the renderer role is exceptionally strong while the exact
original developer class identifier does not survive.

## Acceptance boundary

Chat 2 does not promote R87. Main/Core may accept the proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_2974461D01463567714E`.
