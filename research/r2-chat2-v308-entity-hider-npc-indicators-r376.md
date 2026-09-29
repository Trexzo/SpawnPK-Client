# Chat 2 — Entity Hider + NPC Indicators source identities R376

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/s/d/a` -> `CLIENT_CLASS_000897` -> `EntityHiderConfig`
- `rs/s/d/b` -> `CLIENT_CLASS_000898` -> `EntityHiderPlugin`
- `rs/s/o/d` -> `CLIENT_CLASS_000944` -> `NpcIndicatorsConfig`
- `rs/s/o/e` -> `CLIENT_CLASS_000945` -> `NpcIndicatorsPlugin`
- review: `SEMREVIEW_2CE46E466A87FDF7C6D2`

## Entity Hider

Exact v308 preserves the `entityhider` configuration group plus the inherited RuneLite
hide-player/local-player/projectile semantics. SpawnPK extends the config with additional
pet, mini-pet, PK-bot and wilderness-context toggles.

The sibling plugin consumes this exact config and performs the live entity-hiding decisions.

Historical RuneLite-derived sources preserve the names `EntityHiderConfig` and
`EntityHiderPlugin`.

## NPC Indicators

Exact v308 `rs/s/o/d` exposes border/fill colors and hull/tile/true-tile/outline/name
options. One exact description survives verbatim:

`Configures whether or not NPC names should be drawn above the NPC`

Historical RuneLite sources preserve that text in `NpcIndicatorsConfig`.

R189 already owns sibling `rs/s/o/c` as `NpcIndicatorsOverlay`; the live plugin
`rs/s/o/e` consumes the config, reacts to `npcindicators` config changes, tracks NPC
spawns and owns indicator/tag behavior.

## Boundary

These are source-lineage/source-name recoveries. Exact-v308 custom extensions remain primary
authority. R376 remains non-canonical research only.
