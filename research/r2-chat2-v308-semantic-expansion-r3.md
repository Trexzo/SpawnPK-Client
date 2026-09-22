# Chat 2 — exact-v308 semantic expansion R3

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

This research continues after Main/Core explicitly accepted the original 39-proposal R2 semantic seed.
R3 is a **new, separate, non-canonical class-only review batch**. It does not replace or reopen
Main's accepted R2 semantics.

## Deterministic review result

- candidate classes: **20**
- resolved proposals: **20**
- unresolved: **0**
- review ID: `SEMREVIEW_1948F58DF9A849992F1A`
- fields/methods proposed by this batch: **0**

A cross-platform regression test re-runs `resolve_semantic_candidates()` and requires
object-for-object equality with the committed review.

## Exact-v308 class candidates

| Raw class | Stable ID | Candidate semantic |
| --- | --- | --- |
| `rs/gui/b/h` | `CLIENT_CLASS_000250` | `LoadoutFolderPanel` |
| `rs/l/e/a/o` | `CLIENT_CLASS_000413` | `HalloweenHungerGamesOverlay` |
| `rs/l/f/a/c/c` | `CLIENT_CLASS_000452` | `BountyHunterOverlay` |
| `rs/n/c/N` | `CLIENT_CLASS_000560` | `HalloweenEventChestInterface` |
| `rs/n/c/Z` | `CLIENT_CLASS_000572` | `LeaderboardSelectionInterface` |
| `rs/n/c/aE` | `CLIENT_CLASS_000580` | `LegendaryPetFusingInterface` |
| `rs/n/c/aJ` | `CLIENT_CLASS_000585` | `QuickPrayerSetupInterface` |
| `rs/n/c/aK` | `CLIENT_CLASS_000586` | `RaidPartyInvitationsInterface` |
| `rs/n/c/aW` | `CLIENT_CLASS_000598` | `WorldTournamentLeaderboardInterface` |
| `rs/n/c/al` | `CLIENT_CLASS_000613` | `ItemLoadoutModificationInterface` |
| `rs/n/c/as` | `CLIENT_CLASS_000623` | `MarketplaceInterface` |
| `rs/n/c/at` | `CLIENT_CLASS_000624` | `MarketplaceSearchResultsInterface` |
| `rs/n/c/au` | `CLIENT_CLASS_000625` | `MarketplaceListingInterface` |
| `rs/n/c/b/a` | `CLIENT_CLASS_000634` | `GladiatorsVindicationWorldEventInterface` |
| `rs/n/c/d/b` | `CLIENT_CLASS_000652` | `RaidPartyListInterface` |
| `rs/n/c/d/c` | `CLIENT_CLASS_000653` | `RaidPartyHubInterface` |
| `rs/n/c/d/e` | `CLIENT_CLASS_000655` | `AfflictionTomesInterface` |
| `rs/n/c/q` | `CLIENT_CLASS_000670` | `ClanChatInterface` |
| `rs/n/c/u` | `CLIENT_CLASS_000674` | `UnclaimedRewardsCofferInterface` |
| `rs/n/c/w` | `CLIENT_CLASS_000676` | `ComponentColorSelectionInterface` |

## Evidence boundary

The batch is deliberately restricted to classes with strong exact-current self-identifying
presentation evidence: explicit interface/overlay titles, command labels, action text and/or
dedicated resource paths.

Examples include:

- `SpawnPK Marketplace`, `SpawnPK Marketplace Search Results`, and
  `SpawnPK Marketplace Listing`;
- `Affliction Tomes` plus `raids/tomes*` resources;
- `BountyOverlay` plus bounty-target assets/actions;
- `Item Loadout Modification Interface`;
- `World Tournament Leaderboards`;
- `Coffer of Unclaimed Rewards & Prizes`;
- `Legendary Pet Fusing`;
- `H'ween Hunger Games Lobby`.

The proposed English identifiers are semantic roles inferred from exact-v308 behavior. They
are not claimed as original developer class names.

## Acceptance boundary

Chat 2 does not accept this batch.

Main/Core may later select any subset through an explicit `semantic_acceptance_spec` bound to
`SEMREVIEW_1948F58DF9A849992F1A`. Until that happens, these 20 names remain non-canonical
review proposals.
