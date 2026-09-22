# Chat 2 — exact-v308 semantic expansion: 20 additional self-describing interfaces

Exact v308 authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

This pass keeps the evidence threshold high: each class has direct role-specific exact-v308
text plus a matching resource family. No original developer identifier is claimed.

| Stable ID | Raw class | Candidate | Exact evidence |
| --- | --- | --- | --- |
| `CLIENT_CLASS_000555` | `rs/n/c/J` | `EventActivityViewerInterface` | `Event Activity Viewer`, activity token limits/timers, `popups/activities` |
| `CLIENT_CLASS_000613` | `rs/n/c/al` | `ItemLoadoutModificationInterface` | exact interface title, Save/Set default, `equipment/loadout` |
| `CLIENT_CLASS_000594` | `rs/n/c/aS` | `TaskScrollInterface` | Task Scroll Title/Information/Progress/Rewards, `tasks/SPRITE` |
| `CLIENT_CLASS_000566` | `rs/n/c/T` | `MonsterSpawnerInterface` | `Monster Spawner`, Spawn this NPC, Toggle spawner, `factory/SPRITE` |
| `CLIENT_CLASS_000623` | `rs/n/c/as` | `MarketplaceInterface` | `SpawnPK Marketplace`, listings/sales/search controls, `pos/*` |
| `CLIENT_CLASS_000551` | `rs/n/c/F` | `EmotesInterface` | named emotes, `emotes/EMOTE` |
| `CLIENT_CLASS_000553` | `rs/n/c/H` | `EquipmentStatsInterface` | Equip Your Character, attack/defence/other bonuses, `equipment/CUSTOM` |
| `CLIENT_CLASS_000592` | `rs/n/c/aQ` | `SkillsInterface` | Total Level, View skill Guide, XP/level presentation, `skills/*` |
| `CLIENT_CLASS_000639` | `rs/n/c/ba` | `KnowledgebaseInterface` | `Official SpawnPK Knowledgebase`, article/category UI, `wiki/*` |
| `CLIENT_CLASS_000652` | `rs/n/c/d/b` | `RaidPartyBrowserInterface` | Party/Size/Raid Type & Difficulty, Join/Refresh, `raids/list` |
| `CLIENT_CLASS_000598` | `rs/n/c/aW` | `WorldTournamentLeaderboardsInterface` | exact title, weekly/all-time, Top Players/Clans, `misc/hs` |
| `CLIENT_CLASS_000608` | `rs/n/c/ag` | `ItemsKeptOnDeathInterface` | exact title, keep/lose/red-skull guidance, `icons/death` |
| `CLIENT_CLASS_000625` | `rs/n/c/au` | `MarketplaceListingInterface` | exact listing title, quantity/price/currency/history, `pos/*` |
| `CLIENT_CLASS_000631` | `rs/n/c/az` | `MonsterDropSearchInterface` | exact drop-search title, item/monster search, `drops/*` |
| `CLIENT_CLASS_000572` | `rs/n/c/Z` | `LeaderboardSelectionInterface` | exact selection title, tournament/daily PK leaderboards, `misc/hs` |
| `CLIENT_CLASS_000548` | `rs/n/c/C` | `DonationCheckoutInterface` | Donation Shopping Cart Interface, PayPal/OSRS GP checkout, `misc/donor` |
| `CLIENT_CLASS_000601` | `rs/n/c/aZ` | `WellOfGoodwillInterface` | `Well of Good Will`, contribution/progress/rewards, `fountain/sprite` |
| `CLIENT_CLASS_000560` | `rs/n/c/N` | `EventChestInterface` | Event Chest tiers, prize/roll/reset controls, `fountain/event` |
| `CLIENT_CLASS_000655` | `rs/n/c/d/e` | `RaidAfflictionTomesInterface` | Affliction Tomes, modifier-tome guide/deposits/rolls, `raids/tomes*` |
| `CLIENT_CLASS_000653` | `rs/n/c/d/c` | `RaidPartyLobbyInterface` | create/join/ready/leave/enter, Raid Selection/Difficulty, raid resources |

## Updated semantic review

```text
class candidates   58
field candidates    3
method candidates   4
total candidates   65
resolved proposals 65
unresolved          0
review_id           SEMREVIEW_1D05C99BCABD6CB508EF
```

All remain non-canonical. R4A still emits zero readable remaps until explicit semantic
acceptance updates canonical lineage.
