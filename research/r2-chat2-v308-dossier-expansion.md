# R2 Chat 2 — dossier-driven exact-v308 semantic expansion

The semantic dossier generator ranks exact-build classes by rare UI text, control/command
tokens and resource paths without generating English names itself. Chat 2 manually reviewed
the strongest domain-specific dossiers and retained only roles directly supported by each
class's own exact-v308 presentation evidence.

For every class below, the same raw class path in `client(5).jar` and exact v308 has an
identical name-insensitive structural fingerprint.

## Additional 23 class candidates

| Stable ID | Raw class | Semantic candidate |
| --- | --- | --- |
| `CLIENT_CLASS_000599` | `rs/n/c/aX` | `WorldTournamentInterface` |
| `CLIENT_CLASS_000584` | `rs/n/c/aI` | `DonorPanelInterface` |
| `CLIENT_CLASS_000600` | `rs/n/c/aY` | `CombatStyleInterface` |
| `CLIENT_CLASS_000661` | `rs/n/c/h` | `BankInterface` |
| `CLIENT_CLASS_000579` | `rs/n/c/aD` | `BloodFountainPerkTreeInterface` |
| `CLIENT_CLASS_000643` | `rs/n/c/c/a` | `MailboxInterface` |
| `CLIENT_CLASS_000603` | `rs/n/c/ab` | `ItemGuideInterface` |
| `CLIENT_CLASS_000573` | `rs/n/c/a` | `AchievementDiaryInterface` |
| `CLIENT_CLASS_000672` | `rs/n/c/s` | `ClanWarsSetupInterface` |
| `CLIENT_CLASS_000669` | `rs/n/c/p` | `ClanChatSetupInterface` |
| `CLIENT_CLASS_000666` | `rs/n/c/m` | `BloodcoreSynthesisInterface` |
| `CLIENT_CLASS_000561` | `rs/n/c/O` | `ActiveEventsInterface` |
| `CLIENT_CLASS_000668` | `rs/n/c/o` | `BossTeleportInterface` |
| `CLIENT_CLASS_000627` | `rs/n/c/aw` | `DonationShoppingCartInterface` |
| `CLIENT_CLASS_000605` | `rs/n/c/ad` | `ItemRepairCofferInterface` |
| `CLIENT_CLASS_000568` | `rs/n/c/V` | `GamblingInterface` |
| `CLIENT_CLASS_000578` | `rs/n/c/aC` | `ClientSettingsInterface` |
| `CLIENT_CLASS_000582` | `rs/n/c/aG` | `CursesPrayerInterface` |
| `CLIENT_CLASS_000583` | `rs/n/c/aH` | `StandardPrayerInterface` |
| `CLIENT_CLASS_000617` | `rs/n/c/ap` | `MagicSpellbookInterface` |
| `CLIENT_CLASS_000567` | `rs/n/c/U` | `PlayerIpUidMatcherInterface` |
| `CLIENT_CLASS_000662` | `rs/n/c/i` | `BloodFountainHubInterface` |
| `CLIENT_CLASS_000665` | `rs/n/c/l` | `TaskSelectionInterface` |

## Evidence examples

The candidates are anchored by exact role-specific literals/resources rather than nearby
package names. Examples include:

- `SpawnPK World Tournaments`, `Enter tournament`, `tournament/sprite`;
- `Main Donor Panel`, donor shops/zones, `misc/donor`;
- bank withdraw/deposit/tab controls and `bank/TAB`;
- `Blood Fountain Perk Tree` and `fountain/sprite`;
- mailbox subject/delete/deposit-attachment controls and `misc/mail`;
- `Official SpawnPK Item Library` and `wiki/item`;
- `SpawnPK Achievement Diary`;
- `Clan Wars Setup` and exact rules/mode controls;
- `Bloodcore Token Synthesis`;
- `Boss Teleportation Network`;
- `Donation Shopping Cart`;
- `Item repairing coffer`;
- prayer/spell names tied to `prayer/*` and `magic/*` resources;
- `Player IP / UID Matcher`;
- `Choose a Task` with Slaughter/Bounty/Monster/Boss/Blood Slayer task modes.

Two candidates (`ActiveEventsInterface` and `TaskSelectionInterface`) lack a dedicated
resource-family signal but retain exact role-specific text plus stable cross-build
structure, so they use the lower semantic confidence tier.

## R2C2 result

After combining this slice with the earlier semantic seed:

```text
class candidates   32
field candidates    3
method candidates   4
total candidates   45
resolved proposals 39
unresolved          0
review_id           SEMREVIEW_E471CA15CA95C7CD00A7
```

No proposal is accepted by this research pass.
