# R2 Chat 2 — v308 semantic class risk preflight

All **58 current Chat 2 class semantic candidates** were checked against the exact-build
risk categories introduced by R2A.

Exact v308 authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

For every current semantic class coordinate:

- exact class-name literal hits elsewhere in the JAR: **0**
- non-class resources under the source class package: **0**

Combined R2A-style summary:

```text
mapped_classes                  58
literal_class_name_hit_count     0
package_resource_hit_count       0
service_descriptor_count         2
manifest_requires_review         true
```

The two service descriptors are global JAR entries:

- `META-INF/services/com.fasterxml.jackson.core.JsonFactory`
- `META-INF/services/com.fasterxml.jackson.core.ObjectCodec`

The manifest-review flag is the generic R2A rule for any non-empty class remap. No current
candidate source class appears as an exact surviving class-name string literal, and none
sits in a source package containing a non-class resource.

## Current class candidate set

- `rs/i/b` -> `AdventureOrbRenderer`
- `rs/n/c/a` -> `AchievementDiaryInterface`
- `rs/n/c/A` -> `ConfirmationDialogInterface`
- `rs/n/c/ab` -> `ItemGuideInterface`
- `rs/n/c/aC` -> `ClientSettingsInterface`
- `rs/n/c/ad` -> `ItemRepairCofferInterface`
- `rs/n/c/aD` -> `BloodFountainPerkTreeInterface`
- `rs/n/c/ag` -> `ItemsKeptOnDeathInterface`
- `rs/n/c/aG` -> `CursesPrayerInterface`
- `rs/n/c/aH` -> `StandardPrayerInterface`
- `rs/n/c/aI` -> `DonorPanelInterface`
- `rs/n/c/al` -> `ItemLoadoutModificationInterface`
- `rs/n/c/aL` -> `RaidPartySetupInterface`
- `rs/n/c/am` -> `WelcomeBackInterface`
- `rs/n/c/ap` -> `MagicSpellbookInterface`
- `rs/n/c/aQ` -> `SkillsInterface`
- `rs/n/c/as` -> `MarketplaceInterface`
- `rs/n/c/aS` -> `TaskScrollInterface`
- `rs/n/c/au` -> `MarketplaceListingInterface`
- `rs/n/c/av` -> `DailyMoneyMakingInterface`
- `rs/n/c/aw` -> `DonationShoppingCartInterface`
- `rs/n/c/aW` -> `WorldTournamentLeaderboardsInterface`
- `rs/n/c/aX` -> `WorldTournamentInterface`
- `rs/n/c/aY` -> `CombatStyleInterface`
- `rs/n/c/az` -> `MonsterDropSearchInterface`
- `rs/n/c/aZ` -> `WellOfGoodwillInterface`
- `rs/n/c/b` -> `DailyChallengesInterface`
- `rs/n/c/ba` -> `KnowledgebaseInterface`
- `rs/n/c/c/a` -> `MailboxInterface`
- `rs/n/c/c` -> `AdventureBookInterface`
- `rs/n/c/C` -> `DonationCheckoutInterface`
- `rs/n/c/d/b` -> `RaidPartyBrowserInterface`
- `rs/n/c/d/c` -> `RaidPartyLobbyInterface`
- `rs/n/c/d/e` -> `RaidAfflictionTomesInterface`
- `rs/n/c/F` -> `EmotesInterface`
- `rs/n/c/G` -> `ItemEnchantmentInterface`
- `rs/n/c/h` -> `BankInterface`
- `rs/n/c/H` -> `EquipmentStatsInterface`
- `rs/n/c/i` -> `BloodFountainHubInterface`
- `rs/n/c/j` -> `BloodDiamondFuserInterface`
- `rs/n/c/J` -> `EventActivityViewerInterface`
- `rs/n/c/k` -> `BloodShardSalvagingInterface`
- `rs/n/c/l` -> `TaskSelectionInterface`
- `rs/n/c/m` -> `BloodcoreSynthesisInterface`
- `rs/n/c/n` -> `BloodcoreLotteryInterface`
- `rs/n/c/N` -> `EventChestInterface`
- `rs/n/c/o` -> `BossTeleportInterface`
- `rs/n/c/O` -> `ActiveEventsInterface`
- `rs/n/c/p` -> `ClanChatSetupInterface`
- `rs/n/c/q` -> `ClanChatInterface`
- `rs/n/c/s` -> `ClanWarsSetupInterface`
- `rs/n/c/T` -> `MonsterSpawnerInterface`
- `rs/n/c/u` -> `UnclaimedRewardsCofferInterface`
- `rs/n/c/U` -> `PlayerIpUidMatcherInterface`
- `rs/n/c/v` -> `CollectionLogInterface`
- `rs/n/c/V` -> `GamblingInterface`
- `rs/n/c/z` -> `ConstructionRoomSelectionInterface`
- `rs/n/c/Z` -> `LeaderboardSelectionInterface`

## Consequence

R2C2 may resolve and explicitly accept these semantic names without mutating bytecode.
If R4A later uses accepted class names to build the readable namespace, the existing R2A /
R2B fail-closed checks do not currently require:

- `rewrite_class_name_strings`
- `allow_package_resource_risk`

for these 58 class mappings based on the exact-v308 risk categories.

This is a preflight finding only. Chat 2 does not authorize semantic acceptance or execute
a remap.
