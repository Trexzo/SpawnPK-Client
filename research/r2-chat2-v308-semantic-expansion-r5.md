# Chat 2 — exact-v308 semantic expansion R5

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R5 is a separate non-canonical class-only review batch. It does not reopen or alter Main's
accepted 39-name R2 semantic authority, nor the R3/R4 review batches.

## Deterministic review result

- candidate classes: **17**
- resolved proposals: **17**
- unresolved: **0**
- review ID: `SEMREVIEW_C74696DD26C13B1CC8D4`
- fields/methods proposed: **0**

## Candidates

| Raw class | Stable ID | Candidate semantic |
| --- | --- | --- |
| `rs/n/c/F` | `CLIENT_CLASS_000551` | `EmoteInterface` |
| `rs/n/c/H` | `CLIENT_CLASS_000553` | `EquipmentStatsInterface` |
| `rs/n/c/J` | `CLIENT_CLASS_000555` | `EventActivityViewerInterface` |
| `rs/n/c/T` | `CLIENT_CLASS_000566` | `MonsterSpawnerInterface` |
| `rs/n/c/aF` | `CLIENT_CLASS_000581` | `PlankMakeInterface` |
| `rs/n/c/aS` | `CLIENT_CLASS_000594` | `TaskScrollInterface` |
| `rs/n/c/aZ` | `CLIENT_CLASS_000601` | `WellOfGoodWillInterface` |
| `rs/n/c/ag` | `CLIENT_CLASS_000608` | `ItemsKeptOnDeathInterface` |
| `rs/n/c/ai` | `CLIENT_CLASS_000610` | `ControlOptionsInterface` |
| `rs/n/c/an` | `CLIENT_CLASS_000615` | `LootingBagInterface` |
| `rs/n/c/ao` | `CLIENT_CLASS_000616` | `RaffleInterface` |
| `rs/n/c/aq` | `CLIENT_CLASS_000621` | `MakeQuantityInterface` |
| `rs/n/c/az` | `CLIENT_CLASS_000631` | `MonsterDropSearchInterface` |
| `rs/n/c/ba` | `CLIENT_CLASS_000639` | `KnowledgebaseInterface` |
| `rs/n/c/j` | `CLIENT_CLASS_000663` | `BloodDiamondFuserInterface` |
| `rs/n/c/k` | `CLIENT_CLASS_000664` | `BloodShardSalvagingInterface` |
| `rs/n/c/n` | `CLIENT_CLASS_000667` | `BloodcoreTokenLotteryInterface` |

## Evidence boundary

R5 remains restricted to exact-current self-identifying text and dedicated resources.

Representative evidence:

- `Items kept on death` with kept/auto-kept/lost lists and death icons;
- `Control Options Menu` with player/NPC attack options, key bindings and item drag;
- `Event Activity Viewer` plus token-limit timers;
- `Monster Spawner` plus spawn/activate controls;
- `Official SpawnPK Knowledgebase` plus wiki resources;
- `Monster item drop search` plus drops resources;
- `Well of Good Will` plus server-wide contribution progress;
- `Bloodcore Token Lottery`;
- `Looting bag`;
- `Blood Diamond Fuser`;
- `Blood Shard Salvaging Kit`;
- task-scroll, emote, equipment-stat, make-quantity and plank-making presentation.

Where the exact UI has no formal title, the candidate deliberately uses a conservative role
name rather than claiming an original developer identifier.

## Acceptance boundary

Chat 2 does not promote R5. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_C74696DD26C13B1CC8D4`.
