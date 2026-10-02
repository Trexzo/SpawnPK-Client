# Chat 2 — PvP Tracker config/plugin R401

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/s/q/a` -> `CLIENT_CLASS_000950` -> `PvpTrackerConfig`
- `rs/s/q/d` -> `CLIENT_CLASS_000957` -> `PvpTrackerPlugin`
- review: `SEMREVIEW_E369C36671257B9D8572`

## Source identities

The recovered semantic source map identifies:

- `rs/s/q/a` as `rs.plugins.pvptracker.PvpTrackerConfig`
- `rs/s/q/d` as `rs.plugins.pvptracker.PvpTrackerPlugin`

The recovered source workspace still carried the config as
`Recovered_CLIENT_CLASS_000950`, so this source identity materially improves the generated
workspace rather than duplicating a readable recovered class.

## Exact config behavior

Config group:

`pvptracker`

Exact items:

- `fightHistoryRenderLimit`
  - title: `Max Rendered Fights`
  - range: 1..1000
  - default: 10
- `exactNameFilter`
- hidden `nameFilter`

## Exact plugin behavior

Runtime plugin descriptor:

- title: `PvP Tracker`
- config key: `pvptracker`

Startup:

- builds the configured Gson instance used for tracker state;
- creates current-fight and history containers;
- resolves the tracker panel;
- loads `pvp_icon.png`;
- installs a `PvP Tracker` side-panel navigation entry.

The plugin maintains one current fight plus a list of prior fights. Its completion path copies
the participant/combat state into a history entry, appends it, updates the panel, creates a
fresh current fight and refreshes the active display.

It also persists a normalized `nameFilter` through ConfigManager.

## Boundary

Only the config/plugin pair is recovered here. The subordinate PvP fight/player model and
panel/helper classes remain separate future candidates unless their source identities and
ownership are independently established.

R401 remains non-canonical semantic research only.
