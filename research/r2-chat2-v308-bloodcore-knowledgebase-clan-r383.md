# Chat 2 — Bloodcore, Knowledgebase and clan interfaces R383

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/n/c/m` -> `CLIENT_CLASS_000666` -> `BloodcoreTokenSynthesisInterface`
- `rs/n/c/n` -> `CLIENT_CLASS_000667` -> `BloodcoreTokenLotteryInterface`
- `rs/n/c/ba` -> `CLIENT_CLASS_000639` -> `KnowledgebaseInterface`
- `rs/n/c/p` -> `CLIENT_CLASS_000669` -> `ClanSetupInterface`
- `rs/n/c/q` -> `CLIENT_CLASS_000670` -> `ClanChatInterface`
- review: `SEMREVIEW_3FA2A4EF82660A938581`

### BloodcoreTokenSynthesisInterface
Preserves the exact title `Bloodcore Token Synthesis` plus synthesis/shop/guide and Remove 1/5/10/All/X controls.

### BloodcoreTokenLotteryInterface
Preserves `Bloodcore Token Lottery`, participant count, current pot, countdown, entry action and latest-winner presentation.

### KnowledgebaseInterface
Preserves `Official SpawnPK Knowledgebase`, Category List, selected article title, category/description rendering and wiki/guide resources.

### ClanSetupInterface
Owns clan naming, rank/permission thresholds and right-click configuration help.

### ClanChatInterface
Preserves `Clan Chat (0/100)`, Join Chat, Clan Setup, Manage clan member, owner and active-chat status.

## Boundary
The proposals describe exact client UI responsibilities only. Synthesis, lottery, guide content and clan authorization rules remain external/server authority. R383 is non-canonical.
