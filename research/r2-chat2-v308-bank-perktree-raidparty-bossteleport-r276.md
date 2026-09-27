# Chat 2 — exact-v308 bank, perk-tree, raid-party and boss-teleport interfaces R276

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic result

- `rs/n/c/h` -> `CLIENT_CLASS_000661` -> `BankInterface`
- `rs/n/c/aD` -> `CLIENT_CLASS_000579` -> `BloodFountainPerkTreeInterface`
- `rs/n/c/aL` -> `CLIENT_CLASS_000587` -> `RaidingPartySetupInterface`
- `rs/n/c/o` -> `CLIENT_CLASS_000668` -> `BossTeleportInterface`
- review: `SEMREVIEW_E2C581A7745DC71B7A08`
- unresolved: **0**
- field/method proposals: **0**

## Exact-v308 evidence

### BankInterface

`rs/n/c/h` constructs the SpawnPK bank presentation directly. Its bytecode contains the title **The Bank of SpawnPK**, the `bank/BANK` and `bank/TAB` resource families, and bank-only controls including **Search for item**, **Swap Withdraw Mode**, note/item withdrawal switching, carried-item deposit, worn-item deposit, pet deposit, potion decanting and repair. Its static Client helper also enters item-search mode with the exact prompt **Enter name of item to search**.

### BloodFountainPerkTreeInterface

`rs/n/c/aD` renders **<img=186> Blood Fountain Perk Tree <img=186>**, uses `fountain/sprite` resources, exposes **Purchase** and **Close**, and embeds the perk catalog itself. Exact literals include Blood vengeance, Blood whip, Bloodlust, Archaeologist I/II/III, Bloodthirsty I/II, Vampiric accuracy/damage/defence, Treasure hunter I/II, Mercenary I/II, Killjoy I/II and other Blood Fountain perks.

### RaidingPartySetupInterface

`rs/n/c/aL` renders **Raiding Party Set-up** and direct party controls including **Start raid**, **Invite member**, **Remove member**, **Re-invite last players**, **Refresh** and **Leave/disband party**. The same surface explicitly selects **Chambers of Xeric** or **Theatre of Blood** and exposes Normal, Adept, Expert, Master and Grandmaster difficulty choices, so the whole-class noun is the raid-party setup rather than either individual raid.

### BossTeleportInterface

`rs/n/c/o` renders **Boss Teleportation Network** / **Bosses**, thirteen selectable teleport entries, and boss-detail fields for name, combat level, combat zone, wilderness level, possible drops/rewards, achievements and the full drop table. Exact actions include **Select this teleport** and **Teleport to boss**.

## Stable-ID check

The four class IDs are the exact positions of their v308 internal names in the deterministic sorted `rs/**/*.class` project-class inventory. This is the same stable ordering that yields retained R275 identities such as `rs/n/c/I -> CLIENT_CLASS_000554` and `rs/n/c/aQ -> CLIENT_CLASS_000592`.

## Boundary

R276 is non-canonical research only. The names are descriptive identities proved by exact-v308 behavior and literals; no stripped original source identifier is claimed. Chat 2 performs no semantic acceptance or rewrite.
