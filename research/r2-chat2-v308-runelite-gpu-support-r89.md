# Chat 2 — exact-v308 RuneLite GPU support identities R89

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R89 is a separate non-canonical class-only review batch for seven R87-adjacent GPU support
classes whose exact-v308 structure and consumers match named public RuneLite-derived
implementations unusually closely.

## Deterministic review result

- candidate classes: **7**
- resolved proposals: **7**
- unresolved: **0**
- review ID: `SEMREVIEW_F22C6BABB296DE445092`
- field/method proposals: **0**

## Stable IDs

- `rs/k/a` -> `CLIENT_CLASS_000314` -> `GLBuffer`
- `rs/k/c` -> `CLIENT_CLASS_000326` -> `GpuFloatBuffer`
- `rs/k/d` -> `CLIENT_CLASS_000331` -> `GpuIntBuffer`
- `rs/k/d/a` -> `CLIENT_CLASS_000332` -> `Template`
- `rs/k/k` -> `CLIENT_CLASS_000340` -> `OpenCLManager`
- `rs/k/l` -> `CLIENT_CLASS_000341` -> `SceneUploader`
- `rs/k/m` -> `CLIENT_CLASS_000342` -> `Shader`

## Evidence summary

### GLBuffer

Exact v308 has the same compact four-field record as the public RuneLite-derived
`GLBuffer`: buffer name, OpenGL id, allocated size and OpenCL shared-buffer handle, with
the same `-1` defaults. R87 uses multiple instances with surviving names such as
`scene vertex buffer`, `scene tex buffer`, `tmp vertex buffer` and `uniform buffer`.

### GpuFloatBuffer / GpuIntBuffer

The two classes reproduce the named GPU upload-buffer contracts:

- native-order direct NIO buffers;
- initial capacity 65536;
- typed put helpers;
- clear / flip;
- capacity growth by doubling;
- direct buffer access.

R87 and SceneUploader use them as the paired float UV/texture and integer
vertex/model-info staging buffers.

### Template

The exact class owns a list of `Function<String,String>` resource loaders, expands
`#include` lines recursively, loads UTF-8 class resources and supports arbitrary include
providers. Shader, GpuRenderer and OpenCLManager consume it directly.

That matches the public RuneLite-derived
`net.runelite.client.plugins.gpu.template.Template` contract.

### OpenCLManager

Exact v308 owns the complete OpenCL interop lifecycle: CL context/device/queue, programs,
kernels, AWT/OpenGL sharing and the exact kernel identities `computeUnordered` and
`computeLarge`. R87 delegates its OPENCL ComputeMode path to this object.

The corresponding public GPU implementation names the same role `OpenCLManager`.

### SceneUploader

Exact v308 traverses the scene tile grid, uploads tile paints/models and world models into
GpuIntBuffer/GpuFloatBuffer, writes buffer offsets and lengths back onto scene/renderable
objects, deduplicates models and owns the CPU-side sorting buffers.

That behavior closely matches the named public `SceneUploader`.

### Shader

Exact v308 stores shader units as type/resource pairs, exposes the same
`add(int, String)` builder shape and compiles/links/validates OpenGL programs from sources
resolved by Template.

That contract matches the public RuneLite-derived `Shader`.

## Naming boundary

These names have stronger provenance than ordinary role-based names because the exact-v308
structures and consumers line up with named public RuneLite-derived GPU sources.

Exact v308 remains the authority. R89 does not claim whole-source equivalence, and it does
not name nested `Shader.Unit` or other helpers simply because their enclosing classes are
now identified.

## Acceptance boundary

Chat 2 does not promote R89. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_F22C6BABB296DE445092`.
