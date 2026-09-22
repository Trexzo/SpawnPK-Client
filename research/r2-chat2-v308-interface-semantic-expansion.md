# R2 Chat 2 — exact-v308 native interface semantic expansion

This file records the first interface-expansion slice after the initial semantic seed.
A later dossier-driven slice expands the inventory further.

Exact v308 SHA-256:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

No private research text is copied into this public repository.

## First expansion class role candidates

The stable IDs below were re-derived from the canonical R1 v308 seed ordering and resolved
through the R2C2 semantic-review boundary.

| Logical ID | Raw v308 class | Candidate | Direct v308 evidence |
| --- | --- | --- | --- |
| `CLIENT_CLASS_000640` | `rs/n/c/c` | `AdventureBookInterface` | Next/Previous chapter, Chapter Progress, Claim rewards, Tips & Information, Teleport to Task, Claim reward |
| `CLIENT_CLASS_000587` | `rs/n/c/aL` | `RaidPartySetupInterface` | Raiding Party Set-up, Chambers of Xeric, Theatre of Blood, raid difficulties, invite/remove/start/leave controls, `raids/sprite` |
| `CLIENT_CLASS_000626` | `rs/n/c/av` | `DailyMoneyMakingInterface` | Daily Money Making Activities, reward bonus, Easy/Medium/Hard task labels, Track and Teleport |
| `CLIENT_CLASS_000632` | `rs/n/c/b` | `DailyChallengesInterface` | Daily Challenges, Collect reward, View information and challenge task text |
| `CLIENT_CLASS_000552` | `rs/n/c/G` | `ItemEnchantmentInterface` | Item Enchantment Chest, Enchantments, Select enchantment/item/category, Attempt Enchantment, success/failure presentation |
| `CLIENT_CLASS_000679` | `rs/n/c/z` | `ConstructionRoomSelectionInterface` | exact room/level list from Parlour through Treasure room plus `construction/sprite` |
| `CLIENT_CLASS_000675` | `rs/n/c/v` | `CollectionLogInterface` | Collection Log, category labels, Select collection log, Collection name, Obtained, Kill count, `drops/collection` assets |
| `CLIENT_CLASS_000614` | `rs/n/c/am` | `WelcomeBackInterface` | Welcome back, Play now, daily-login reward copy and `misc/login` assets |

The initial `GameframeRenderer` candidate resolves separately to
`CLIENT_CLASS_000297` / `rs/i/b`.

Each class also has a unique R1 structural lineage relationship between the alternate
lineage and exact v308.

## Confidence stance

Candidates backed by exact domain-specific literals + stable structural lineage are
scored `0.9604`.

Candidates additionally backed by a domain-specific resource family are scored
`0.992872`.

These values express confidence in the proposed semantic role, not recovery of the
developer's original source identifier.

## Current repository-wide semantic inventory

After the later dossier-driven expansion, the current candidate set is:

- class semantic candidates: **73**
- member semantic candidates: **7**
- total semantic candidates: **64**
- R2C2 resolved proposals: **64**
- R2C2 unresolved candidates: **0**
- semantic review ID: `SEMREVIEW_799C2D52A4528B4A66D0`

All remain non-canonical. R2C2 requires a separate explicit acceptance specification before
any proposal becomes `ACCEPTED`.
