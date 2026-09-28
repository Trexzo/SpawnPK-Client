# Chat 2 — exact-v308 server-information / PK-command Swing panel R178

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R178 is a separate non-canonical class-only review for the complete `rs/gui/e` Swing panel
and its fifteen dedicated button ActionListeners.

## Deterministic review result

- candidate classes: **16**
- resolved proposals: **16**
- unresolved: **0**
- review ID: `SEMREVIEW_01E3E3766F0412107582`
- field/method proposals: **0**

## Stable IDs

| Raw class | Stable ID | Candidate semantic |
| --- | --- | --- |
| `rs/gui/e` | `CLIENT_CLASS_000265` | `ServerInformationAndPkCommandsPanel` |
| `rs/gui/f` | `CLIENT_CLASS_000266` | `ServerRulesButtonAction` |
| `rs/gui/g` | `CLIENT_CLASS_000267` | `EntangleRunesCommandAction` |
| `rs/gui/h` | `CLIENT_CLASS_000268` | `MeleePotsCommandAction` |
| `rs/gui/i` | `CLIENT_CLASS_000269` | `BrewCommandAction` |
| `rs/gui/j` | `CLIENT_CLASS_000270` | `RestoreCommandAction` |
| `rs/gui/k` | `CLIENT_CLASS_000271` | `RangePotCommandAction` |
| `rs/gui/l` | `CLIENT_CLASS_000272` | `MagePotCommandAction` |
| `rs/gui/m` | `CLIENT_CLASS_000273` | `ForumsCommunityLinkAction` |
| `rs/gui/n` | `CLIENT_CLASS_000274` | `LatestUpdatesLinkAction` |
| `rs/gui/o` | `CLIENT_CLASS_000275` | `PriceGuideLinkAction` |
| `rs/gui/p` | `CLIENT_CLASS_000276` | `SwitchSpellbookCommandAction` |
| `rs/gui/q` | `CLIENT_CLASS_000277` | `FoodCommandAction` |
| `rs/gui/r` | `CLIENT_CLASS_000278` | `VengeanceRunesCommandAction` |
| `rs/gui/s` | `CLIENT_CLASS_000279` | `BarrageRunesCommandAction` |
| `rs/gui/t` | `CLIENT_CLASS_000280` | `TeleblockRunesCommandAction` |

## Panel identity

`rs/gui/e` directly extends `JPanel` and is constructed by the recovered
`ClientSidebarPanel`.

Its first exact section heading is:

`Check these pages out for server information!`

with exact buttons:

- `Server rules`
- `Forums/Community`
- `Latest updates`
- `Price guide`

Its second exact heading is:

`These commands will aid your PKing needs!`

with eleven exact command buttons.

This makes `ServerInformationAndPkCommandsPanel` a complete whole-class description rather
than a name inferred from one control.

## Exact resource-link actions

- `rs/gui/m` — Forums/Community — `http://spawnpk.net/forums/` — `ForumsCommunityLinkAction`
- `rs/gui/n` — Latest updates — `https://spawnpk.net/forums/index.php?/forum/10-updates/` — `LatestUpdatesLinkAction`
- `rs/gui/o` — Price guide — `https://spawnpk.net/forums/index.php?/topic/5710-the-official-spawnpk-price-guide-for-2017/` — `PriceGuideLinkAction`

Each link listener calls the client's external-link opener with exactly the URL above.

The `Server rules` button is wired to `rs/gui/f`; exact v308
`actionPerformed(ActionEvent)` immediately returns. R178 therefore names the button-owned
listener but explicitly preserves its current no-op behavior.

## Exact PK command actions

- `rs/gui/g` — `::entangle` — `EntangleRunesCommandAction`
- `rs/gui/h` — `::pots` — `MeleePotsCommandAction`
- `rs/gui/i` — `::brew` — `BrewCommandAction`
- `rs/gui/j` — `::rest` — `RestoreCommandAction`
- `rs/gui/k` — `::range` — `RangePotCommandAction`
- `rs/gui/l` — `::mage` — `MagePotCommandAction`
- `rs/gui/p` — `::switch` — `SwitchSpellbookCommandAction`
- `rs/gui/q` — `::food` — `FoodCommandAction`
- `rs/gui/r` — `::veng` — `VengeanceRunesCommandAction`
- `rs/gui/s` — `::barrage` — `BarrageRunesCommandAction`
- `rs/gui/t` — `::tb` — `TeleblockRunesCommandAction`

Each command listener:

1. obtains the live client through `Launcher`;
2. verifies the client exists and its ready/login-state flag is set;
3. writes only the exact command shown above to `Client.ap`.

No command listener mutates an unrelated subsystem.

## Naming boundary

The panel section headings, button labels, URLs and command literals all survive exactly.

The English class names are readable semantic replacements; they are not claimed as lost
original developer identifiers. The no-op `ServerRulesButtonAction` is lower at **0.997**
only because the current bytecode proves ownership but contains no active navigation body.

R178 remains class-only and non-canonical.

## Acceptance boundary

Chat 2 does not promote R178. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_01E3E3766F0412107582`.
