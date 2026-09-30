# Chat 2 — graphics settings sidebar panel R403

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/gui/a/a` -> `CLIENT_CLASS_000202` -> `GraphicsSettingsSidebarPanel`
- review: `SEMREVIEW_821440EC84606494912B`

## Ownership

R145 `ClientSidebarPanel` is the only live exact-v308 dependency on this class.

This is not the R185 `GpuPluginPanel`; it is the built-in sidebar settings surface.

## Exact GPU settings

The panel exposes:

- GPU Mode
- Anti Aliasing
- VSync Mode
- Colorblind Mode
- Anisotropic filtering
- Smooth banding

and binds those controls to the exact GPU/runtime configuration enums and flags.

It also warns explicitly when a 32-bit Java runtime is used on a 64-bit machine.

## Exact stretched-mode settings

The second section is exactly:

`Stretched Mode Settings`

with controls for:

- Stretched Mode
- Maintain aspect ratio
- UI Scaling
- Bilinear
- Bicubic (Mitchell)
- Bicubic (Catmull-Rom)
- xBR

The live listeners apply/persist the selected values and include the exact
`::stretchflagoff` / `::stretchflagon` command path.

## Boundary

The name is intentionally `GraphicsSettingsSidebarPanel`, covering both GPU and stretched
rendering controls without conflating it with the plugin-specific GPU panel.

R403 remains non-canonical semantic research only.
