# Chat 2 R3 — remaining LauncherSidePanel tab roots R364

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/gui/a/a` -> `CLIENT_CLASS_000203` -> `GpuSettingsSidebarPanel`
- `rs/gui/b/h` -> `CLIENT_CLASS_000250` -> `LoadoutsSidebarPanel`
- `rs/s/c/d` -> `CLIENT_CLASS_000890` -> `DevelopmentSidebarPanel`
- review: `SEMREVIEW_4974355101B93BA6C28F`

R357 fixes all three as direct roots of LauncherSidePanel tabs.

### GPU Settings

The GPU tab contains the literal GPU Settings and Stretched Mode Settings sections, including
GPU mode, AA, VSync, colorblind mode, anisotropic filtering, smooth banding, stretched mode,
aspect-ratio and UI-scaling controls.

### Loadouts

The Loadouts tab owns the visible folder/loadout management surface and joins directly to the
already-reviewed LoadoutDefinition / LoadoutFolder / LoadoutManager / LoadoutPersistence /
LoadoutBinaryCodec graph.

### Development

The developer-only tab exposes definition reset/repack commands plus NPC/item/object
recoloring controls, color-list tooling and Copy selected behavior.

R364 is descriptive non-canonical semantic research only.
