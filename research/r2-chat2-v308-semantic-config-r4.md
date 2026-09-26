# Chat 2 — exact-v308 configuration semantics R4

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R4 is a separate non-canonical class-only review batch following:

- Main/Core accepted R2 semantic seed: 39 names;
- Chat 2 R3 review batch: 20 additional interface/overlay classes.

R4 concentrates on client-side configuration/plugin classes whose exact option text is
self-identifying enough to support conservative semantic names.

## Deterministic review result

- candidate classes: **9**
- resolved proposals: **9**
- unresolved: **0**
- review ID: `SEMREVIEW_0D067AB471D25E575699`
- field/method proposals: **0**

## Candidates

| Raw class | Stable ID | Candidate semantic |
| --- | --- | --- |
| `rs/s/a/a` | `CLIENT_CLASS_000855` | `CombatOverlayConfig` |
| `rs/s/c/a` | `CLIENT_CLASS_000887` | `InterfaceDeveloperToolsConfig` |
| `rs/s/d/a` | `CLIENT_CLASS_000897` | `EntityHiderConfig` |
| `rs/s/h/b` | `CLIENT_CLASS_000918` | `StatusInfoboxConfig` |
| `rs/s/i/a` | `CLIENT_CLASS_000919` | `InteractionHighlightConfig` |
| `rs/s/j/a` | `CLIENT_CLASS_000922` | `KeyRemappingConfig` |
| `rs/s/o/d` | `CLIENT_CLASS_000944` | `NpcHighlightConfig` |
| `rs/s/r/a` | `CLIENT_CLASS_000958` | `TileIndicatorConfig` |
| `rs/s/s/a` | `CLIENT_CLASS_000961` | `TooltipConfig` |

## Exact evidence examples

- `rs/s/j/a`: "Camera Remapping", "F-key remapping", replacement keys for F1-F12
  and camera directions.
- `rs/s/d/a`: repeated "Hide ..." options for players, pets, projectiles, bots and
  player-state overlays.
- `rs/s/c/a`: "Dev settings for interfaces", "Dev tools for interfaces",
  "Interface Builder", widget IDs/types and scene info.
- `rs/s/o/d`: "NPCs to Highlight", hull/outline/tile/true-tile modes, colors,
  feather and border width.
- `rs/s/r/a`: Current Tile, Destination Tile and Hovered Tile configuration.
- `rs/s/i/a`: NPC/Object hover/interact/attack outline settings.
- `rs/s/s/a`: entity/item tooltip hovers, tooltip overlay colors and description options.
- `rs/s/h/b`: counter/status/timer infoboxes and exact combat/task timers.
- `rs/s/a/a`: opponent, boss and bounty-hunter overlay style plus hit/health display.

Names are semantic configuration roles inferred from exact-v308 text. They are not claimed
as original developer class identifiers.

## Review boundary

Chat 2 does not promote these proposals. Main/Core must explicitly accept any desired subset
through a `semantic_acceptance_spec` tied to
`SEMREVIEW_0D067AB471D25E575699`.
