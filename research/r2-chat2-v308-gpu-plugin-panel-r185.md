# Chat 2 — exact-v308 GPU plugin navigation panel R185

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R185 is a separate non-canonical class-only review for the live GPU Mode navigation/sidebar
panel.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_ED3BC2D9B327E06C3564`
- field/method proposals: **0**

## Stable ID

`rs/s/e/b` -> `CLIENT_CLASS_000901` -> `GpuPluginPanel`

## Exact runtime role

The class directly extends the reviewed R148 `PluginPanel` base.

It stores only:

- reviewed `GpuPlugin` (`rs/s/e/c`);
- the plugin/config UI component factory dependency.

Reviewed `GpuPlugin` obtains this panel from the injector and constructs a navigation button
with:

- exact title `GPU Mode`;
- exact icon `gpu_icon.png`;
- this `rs/s/e/b` instance as the button's `PluginPanel`.

That button is then registered into the live client UI.

## Activation/rebuild behavior

`GpuPluginPanel` overrides the shared PluginPanel activation hook `J_()`.

On activation it:

1. removes all existing children;
2. asks the plugin/config UI factory to build the component for the reviewed `GpuPlugin`;
3. adds that generated component as the panel's sole content.

This fixes the class as the live navigation/sidebar panel for the GPU plugin.

## Important distinction

R9 already reviews `rs/gui/a/a` as `GpuSettingsPanel`.

That class is the separate desktop settings surface with explicit GPU Settings / Stretched Mode
controls.

R185 does **not** rename or duplicate that class. `GpuPluginPanel` is specifically the
RuneLite-style navigation panel bound to the `GPU Mode` navigation button.

## Dead enum boundary

The same package contains duplicate/orphan enum artifacts such as `rs/s/e/a` with
NONE/PROTANOPE/DEUTERANOPE/TRITANOPE. Exact dependency inspection shows no inbound runtime
use for that duplicate, while the live GpuConfig color-blind setting uses `rs/k/a/b`.

R185 therefore leaves those dead duplicate enum artifacts unnamed.

## Confidence boundary

`GpuPluginPanel` is **0.999**.

The name is descriptive exact-behavior recovery grounded in the live navigation registration,
PluginPanel inheritance and complete one-purpose rebuild surface.

## Acceptance boundary

R185 remains class-only and non-canonical. Main/Core may accept this proposal only through an
explicit `semantic_acceptance_spec` bound to `SEMREVIEW_ED3BC2D9B327E06C3564`.
