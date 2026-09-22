# Chat 2 — exact-v308 semantic expansion to 86 reviewed proposals

This pass adds 18 exact-v308 class-role candidates after the earlier 32-class semantic set.

All roles are derived from each class's own exact-v308 literals and resource-family
references. No candidate is accepted by this pass.

| Stable ID | Raw class | Candidate |
| --- | --- | --- |
| `CLIENT_CLASS_000566` | `rs/n/c/T` | `MonsterSpawnerInterface` |
| `CLIENT_CLASS_000610` | `rs/n/c/ai` | `ControlOptionsInterface` |
| `CLIENT_CLASS_000639` | `rs/n/c/ba` | `KnowledgebaseInterface` |
| `CLIENT_CLASS_000608` | `rs/n/c/ag` | `ItemsKeptOnDeathInterface` |
| `CLIENT_CLASS_000594` | `rs/n/c/aS` | `TaskScrollInterface` |
| `CLIENT_CLASS_000674` | `rs/n/c/u` | `UnclaimedRewardsCofferInterface` |
| `CLIENT_CLASS_000571` | `rs/n/c/Y` | `AccountNavigationInterface` |
| `CLIENT_CLASS_000607` | `rs/n/c/af` | `ItemSpawnerSearchInterface` |
| `CLIENT_CLASS_000613` | `rs/n/c/al` | `LoadoutEditorInterface` |
| `CLIENT_CLASS_000667` | `rs/n/c/n` | `BloodcoreLotteryInterface` |
| `CLIENT_CLASS_000625` | `rs/n/c/au` | `MarketplaceListingInterface` |
| `CLIENT_CLASS_000624` | `rs/n/c/at` | `MarketplaceSearchResultsInterface` |
| `CLIENT_CLASS_000670` | `rs/n/c/q` | `ClanChatInterface` |
| `CLIENT_CLASS_000592` | `rs/n/c/aQ` | `SkillsTabInterface` |
| `CLIENT_CLASS_000664` | `rs/n/c/k` | `BloodShardSalvagingInterface` |
| `CLIENT_CLASS_000623` | `rs/n/c/as` | `MarketplaceHubInterface` |
| `CLIENT_CLASS_000596` | `rs/n/c/aU` | `TeleportSelectionInterface` |
| `CLIENT_CLASS_000652` | `rs/n/c/d/b` | `RaidPartyBrowserInterface` |

Representative exact evidence includes:

- `Monster Spawner`, `Spawn this NPC`, `factory/SPRITE`;
- `Control Options Menu`, keybind and attack-option controls, `options/keybind`;
- `Official SpawnPK Knowledgebase`, `WIKI_SELECTED_`, `wiki/guide`;
- `Items kept on death`, keep/lose lists, `icons/death`;
- `Task Information`, `Completion Progress`, `tasks/SPRITE`;
- `Coffer of Unclaimed Rewards & Prizes`;
- `Item Loadout Modification Interface`, `Save loadout`, `equipment/loadout`;
- marketplace listing/search/hub labels tied to `pos/*` assets;
- `Clan Chat`, `Clan Setup`, `Join Chat`, `clan/sprite`;
- `Total Level`, `View Guide`, `skills/*`;
- raid party list columns and `raids/list` / refresh / close assets.

## Current semantic review

```text
class proposals   73
field proposals    6
method proposals   7
total proposals   86
unresolved         0
review_id          SEMREVIEW_799C2D52A4528B4A66D0
```

The full 73-class set also passes the R2A class-name-literal and source-package-resource
risk categories with zero hits.

Explicit semantic acceptance remains a separate human/integration decision.
\n\nA later high-certainty pass added seven further class roles: DonationPurchaseOptionsInterface, ColorSelectionInterface, FeaturesToolsInterface, HalloweenEventChestInterface, VoteShopInterface, RaffleLotteryInterface, and WorldEventTaskInterface.\n

## Later exact-v308 high-certainty expansion

A further pass added 16 class roles backed by explicit UI titles/controls and, where
available, resource-family evidence:

- WellOfGoodwillInterface
- MonsterDropSearchInterface
- LegendaryPetFusionInterface
- EquipmentStatsInterface
- LootingBagInterface
- PlankMakeInterface
- BloodDiamondFuserInterface
- EmoteInterface
- DuelTypeSelectionInterface
- WorldTournamentLeaderboardsInterface
- EquipmentTabInterface
- QuickPrayerSelectionInterface
- LeaderboardSelectionInterface
- EventActivityViewerInterface
- MakeQuantityInterface
- AfflictionTomesInterface

The current review therefore contains **73 classes + 6 fields + 7 methods = 86 proposals**.
