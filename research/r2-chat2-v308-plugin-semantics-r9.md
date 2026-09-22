# Chat 2 — exact-v308 plugin/config semantics R9

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R9 broadens semantic recovery beyond SpawnPK content interfaces into client plugin/config
infrastructure. It remains a separate non-canonical class-only review batch.

## Deterministic review result

- candidate classes: **9**
- resolved proposals: **9**
- unresolved: **0**
- review ID: `SEMREVIEW_45033AF6496AE782988D`

## Candidates

| Raw class | Stable ID | Candidate semantic |
| --- | --- | --- |
| `rs/gui/a/a` | `CLIENT_CLASS_000203` | `GpuSettingsPanel` |
| `rs/s/e/d` | `CLIENT_CLASS_000903` | `GpuConfig` |
| `rs/s/f/b` | `CLIENT_CLASS_000908` | `GroundMarkersConfig` |
| `rs/s/f/d` | `CLIENT_CLASS_000910` | `GroundMarkersPlugin` |
| `rs/s/l/b` | `CLIENT_CLASS_000927` | `MenuEntrySwapperConfig` |
| `rs/s/l/c` | `CLIENT_CLASS_000928` | `MenuEntrySwapperPlugin` |
| `rs/s/n/a` | `CLIENT_CLASS_000935` | `NotificationAlertsConfig` |
| `rs/s/n/b` | `CLIENT_CLASS_000936` | `NotificationAlertsPlugin` |
| `rs/s/o/e` | `CLIENT_CLASS_000945` | `NpcIndicatorsPlugin` |

## Exact pairing evidence

The runtime->config relationship is directly present in exact-v308 constant-pool/bytecode
references for four groups:

- `rs/s/n/b` -> `rs/s/n/a`
- `rs/s/f/d` -> `rs/s/f/b`
- `rs/s/l/c` -> `rs/s/l/b`
- `rs/s/o/e` -> R4 `rs/s/o/d` / `NpcHighlightConfig`

This means the Plugin/Config distinction is not inferred solely from nearby package names.

## Exact self-identifying text

- Ground Markers: tile mark/unmark/label, minimap drawing, marker color and reset.
- Menu Entry Swapper: exact plugin title plus left/shift-click swapping.
- NPC Indicators: exact title plus tag/tag-all, highlight and tile-style actions.
- Notification alerts: private messages, superior spawns, de-aggro, tray/focus/flash/sound.
- GPU configuration: anti-aliasing, anisotropic filtering, colorblind correction, stretched
  mode, UI scaling and VSync.
- GPU Settings Panel: exact rendered headings `GPU Settings` and
  `Stretched Mode Settings`.

## Acceptance boundary

Chat 2 does not promote R9. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_45033AF6496AE782988D`.
