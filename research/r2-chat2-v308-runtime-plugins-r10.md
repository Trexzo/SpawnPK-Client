# Chat 2 — exact-v308 runtime plugin semantics R10

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R10 pairs exact runtime plugin classes with the configuration semantics already reviewed in
R4. It remains a separate non-canonical class-only review batch.

## Deterministic review result

- candidate classes: **8**
- resolved proposals: **8**
- unresolved: **0**
- review ID: `SEMREVIEW_0A7899AD6B7C9AC5BE83`

## Candidates

| Runtime class | Stable ID | Candidate semantic | Config evidence |
| --- | --- | --- | --- |
| `rs/s/a/b` | `CLIENT_CLASS_000856` | `CombatOverlaysPlugin` | R4 `CombatOverlayConfig` |
| `rs/s/c/c` | `CLIENT_CLASS_000889` | `DeveloperToolsPlugin` | R4 `InterfaceDeveloperToolsConfig` |
| `rs/s/d/b` | `CLIENT_CLASS_000898` | `EntityHiderPlugin` | R4 `EntityHiderConfig` |
| `rs/s/h/a` | `CLIENT_CLASS_000917` | `TimersInfoboxPlugin` | R4 `StatusInfoboxConfig` |
| `rs/s/i/c` | `CLIENT_CLASS_000921` | `InteractHighlightPlugin` | R4 `InteractionHighlightConfig` |
| `rs/s/j/c` | `CLIENT_CLASS_000924` | `KeyRemappingPlugin` | R4 `KeyRemappingConfig` |
| `rs/s/r/c` | `CLIENT_CLASS_000960` | `TileIndicatorsPlugin` | R4 `TileIndicatorConfig` |
| `rs/s/s/b` | `CLIENT_CLASS_000962` | `HoverDescriptionsPlugin` | R4 `TooltipConfig` |

## Exact evidence

Each runtime class directly references the corresponding config class. In addition, exact
descriptor/runtime strings self-identify the plugin roles:

- `Entity Hider` — hides players, NPCs and/or projectiles;
- `Hover Descriptions`;
- `Timers / Info Boxes` plus combat/task timer names;
- `Key Remapping`;
- `Tile Indicators`;
- `Interact Highlight`;
- `Combat overlays`;
- `Developer Tools`.

This pairing is stronger than package-neighbor inference because both the runtime->config
reference and the runtime descriptor are present in exact-v308.

## Acceptance boundary

Chat 2 does not promote R10. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_0A7899AD6B7C9AC5BE83`.
