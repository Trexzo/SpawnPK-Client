# Chat 2 — exact-v308 semantic expansion R6

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R6 is a fourth separate non-canonical class-only review batch after R3/R4/R5. It does not
alter Main/Core's accepted 39-name R2 authority.

## Deterministic review result

- candidate classes: **10**
- resolved proposals: **10**
- unresolved: **0**
- review ID: `SEMREVIEW_3E29870ADC1A4856A558`
- fields/methods proposed: **0**

## Candidates

| Raw class | Stable ID | Candidate semantic |
| --- | --- | --- |
| `rs/n/c/E` | `CLIENT_CLASS_000550` | `DuelTypeSelectionInterface` |
| `rs/n/c/M` | `CLIENT_CLASS_000559` | `VotingInterface` |
| `rs/n/c/Q` | `CLIENT_CLASS_000563` | `EventBrawlStatusInterface` |
| `rs/n/c/aO` | `CLIENT_CLASS_000590` | `ShopTabInterface` |
| `rs/n/c/aU` | `CLIENT_CLASS_000596` | `TeleportSelectionInterface` |
| `rs/n/c/ae` | `CLIENT_CLASS_000606` | `VotePointShopInterface` |
| `rs/n/c/af` | `CLIENT_CLASS_000607` | `ItemSpawnSearchInterface` |
| `rs/n/c/aj` | `CLIENT_CLASS_000611` | `FeaturesToolsInterface` |
| `rs/n/c/d` | `CLIENT_CLASS_000650` | `AdventureBookInterfacePacketHandler` |
| `rs/n/c/g` | `CLIENT_CLASS_000660` | `StandardCombatSpellsInterface` |

## Exact evidence

- `Features / Tools` plus vote/mail/donate/collection/drop/item-guide/community shortcuts;
- exact item-spawn search text including `Spawn this item`;
- teleport selection text plus `teleport/SPRITE`;
- shop tab selection with `Main stock` and five tabs;
- exact voting-site actions;
- `Select a duel type..` with Standard/Whip variants;
- `Event Brawl` active/start countdown status;
- VP-priced item listings with vote resources;
- ScriptPacket 22 registration plus Adventure Book reset/populate/finalize, chapter claim/reward state and progress updates;
- standard combat spell content plus `magic/on*` and `magic/off*` assets.

Where a class has no formal title, the proposed name remains deliberately role-based and
conservative.

## R135 audit correction

A later exact ScriptPacket audit found that the original R6 proposal for
`CLIENT_CLASS_000650` / `rs/n/c/d` was misclassified.

The class itself extends the ScriptPacket handler base and is registered as exact
ScriptPacket **22** through `rs/n/c/c.bL`. Its selector surface drives the already-reviewed
R2 `AdventureBookInterface` (`rs/n/c/c`): reset/finalize, chapter/task population,
chapter-reward claim state, progress state and same-screen presentation effects.

Therefore:

- old non-canonical proposal: `ChapterRewardClaimInterface`;
- old review ID: `SEMREVIEW_F4BDFF8D5BAB20E1AD4B`;
- corrected proposal: `AdventureBookInterfacePacketHandler`;
- corrected review ID: `SEMREVIEW_3E29870ADC1A4856A558`;
- old R6 review/proposal identity is superseded and must not be used for acceptance.

This correction does not promote the class; it repairs only Chat 2's non-canonical research
artifact before any Main/Core acceptance.

## Acceptance boundary

Chat 2 does not promote R6. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_F4BDFF8D5BAB20E1AD4B`.
